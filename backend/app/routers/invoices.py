import os
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.database import get_db
from app.deps import get_current_user, require_module
from app.email_utils import EmailNotConfigured, send_invoice_email
from app.idempotency import request_fingerprint
from app.models import (
    Client,
    CompanySettings,
    Invoice,
    InvoiceLineItem,
    InvoiceSendAttempt,
    InvoiceStatus,
    Quote,
    QuoteStatus,
    TimeEntry,
    User,
)
from app.money import line_amounts, money
from app.pdf import generate_invoice_pdf
from app.rate_limit import enforce_smtp_rate_limit
from app.schemas import (
    InvoiceCreate,
    InvoiceOut,
    InvoiceSendAttemptOut,
    InvoiceSendRequest,
    InvoiceStatusUpdate,
)
from app.time_utils import utc_now_naive

router = APIRouter(
    prefix="/api/invoices",
    tags=["invoices"],
    dependencies=[Depends(require_module("billing.invoices"))],
)


def _get_or_create_settings(
    db: Session, *, lock_for_invoice_number: bool = False
) -> CompanySettings:
    query = db.query(CompanySettings).filter(CompanySettings.id == 1)
    if lock_for_invoice_number:
        query = query.with_for_update()
    company = query.one_or_none()
    if company is None:
        company = CompanySettings(id=1)
        db.add(company)
        db.flush()
    return company


@router.get("", response_model=list[InvoiceOut])
def list_invoices(
    response: Response,
    client_id: int | None = None,
    status_filter: InvoiceStatus | None = Query(default=None, alias="status"),
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Invoice)
    if client_id is not None:
        query = query.filter(Invoice.client_id == client_id)
    if status_filter is not None:
        query = query.filter(Invoice.status == status_filter)
    if date_from is not None:
        query = query.filter(Invoice.issue_date >= date_from)
    if date_to is not None:
        query = query.filter(Invoice.issue_date <= date_to)
    response.headers["X-Total-Count"] = str(query.count())
    return query.order_by(Invoice.id.desc()).offset(offset).limit(limit).all()


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    return invoice


@router.post("", response_model=InvoiceOut)
def create_invoice(
    payload: InvoiceCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    fingerprint = request_fingerprint(payload.model_dump(mode="json"))
    if idempotency_key is not None:
        idempotency_key = idempotency_key.strip()
        if not idempotency_key or len(idempotency_key) > 128:
            raise HTTPException(status_code=400, detail="Ungültiger Idempotency-Key")
        existing = (
            db.query(Invoice).filter(Invoice.request_key == idempotency_key).first()
        )
        if existing is not None:
            if existing.request_fingerprint != fingerprint:
                raise HTTPException(
                    status_code=409,
                    detail="Idempotency-Key wurde bereits für andere Eingabedaten verwendet",
                )
            return existing
    client = db.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    if not payload.time_entry_ids:
        raise HTTPException(status_code=400, detail="Keine Zeiteinträge ausgewählt")

    entries = (
        db.query(TimeEntry)
        .filter(TimeEntry.id.in_(payload.time_entry_ids))
        .with_for_update()
        .all()
    )
    if idempotency_key is not None:
        existing = (
            db.query(Invoice).filter(Invoice.request_key == idempotency_key).first()
        )
        if existing is not None:
            if existing.request_fingerprint != fingerprint:
                raise HTTPException(
                    status_code=409,
                    detail="Idempotency-Key wurde bereits für andere Eingabedaten verwendet",
                )
            return existing
    if len(entries) != len(payload.time_entry_ids):
        raise HTTPException(status_code=404, detail="Ein Zeiteintrag wurde nicht gefunden")
    for entry in entries:
        if entry.client_id != client.id:
            raise HTTPException(
                status_code=400, detail="Zeiteintrag gehört nicht zu diesem Kunden"
            )
        if entry.billed:
            raise HTTPException(
                status_code=400, detail="Ein Zeiteintrag wurde bereits abgerechnet"
            )
        if entry.running_started_at is not None:
            raise HTTPException(
                status_code=400, detail="Ein laufender Timer kann nicht abgerechnet werden"
            )

    # Serialize invoice-number allocation on PostgreSQL. This keeps the existing
    # number series intact when two requests create an invoice concurrently.
    company = _get_or_create_settings(db, lock_for_invoice_number=True)
    today = date.today()
    due_days = (
        payload.due_in_days
        if payload.due_in_days is not None
        else company.default_payment_terms_days
    )
    invoice_number = f"{company.invoice_number_prefix}-{today.year}-{company.next_invoice_number:04d}"

    invoice = Invoice(
        client_id=client.id,
        invoice_number=invoice_number,
        issue_date=today,
        due_date=today + timedelta(days=due_days),
        status=InvoiceStatus.draft,
        notes=payload.notes,
        subtotal=Decimal("0"),
        tax_total=Decimal("0"),
        total=Decimal("0"),
        request_key=idempotency_key,
        request_fingerprint=fingerprint if idempotency_key else None,
    )
    db.add(invoice)
    db.flush()

    subtotal = Decimal("0")
    tax_total = Decimal("0")
    total = Decimal("0")
    for entry in entries:
        hours = (Decimal(entry.duration_minutes) / Decimal(60)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        rate = Decimal(entry.hourly_rate)
        net_amount, tax_amount, amount = line_amounts(hours, rate, payload.tax_rate)
        service_date = entry.date.strftime("%d.%m.%Y")
        description = (
            f"Leistung am {service_date}: {entry.description}"
            if entry.description
            else f"Leistung am {service_date}"
        )
        line_item = InvoiceLineItem(
            invoice_id=invoice.id,
            description=description,
            quantity=hours,
            unit="hours",
            unit_price=rate,
            net_amount=net_amount,
            tax_rate=payload.tax_rate,
            tax_amount=tax_amount,
            amount=amount,
            project_id=entry.project_id,
        )
        db.add(line_item)
        subtotal += net_amount
        tax_total += tax_amount
        total += amount
        entry.billed = True
        entry.invoice_id = invoice.id

    invoice.subtotal = money(subtotal)
    invoice.tax_total = money(tax_total)
    invoice.total = money(total)
    company.next_invoice_number += 1
    db.flush()
    db.refresh(invoice)

    expected_pdf_path = os.path.join(
        app_settings.pdf_storage_dir, f"{invoice.invoice_number}.pdf"
    )
    try:
        pdf_path = generate_invoice_pdf(invoice, client, company)
    except Exception as exc:
        db.rollback()
        try:
            os.remove(expected_pdf_path)
        except FileNotFoundError:
            pass
        raise HTTPException(
            status_code=500, detail=f"Rechnung konnte nicht erstellt werden (PDF-Fehler: {exc})"
        )

    invoice.pdf_path = pdf_path
    try:
        db.commit()
    except Exception:
        db.rollback()
        try:
            os.remove(pdf_path)
        except FileNotFoundError:
            pass
        raise
    db.refresh(invoice)
    return invoice


@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = (
        db.query(Invoice)
        .filter(Invoice.id == invoice_id)
        .with_for_update()
        .one_or_none()
    )
    if (
        invoice is None
        or not invoice.pdf_path
        or not os.path.isfile(invoice.pdf_path)
    ):
        raise HTTPException(status_code=404, detail="PDF nicht gefunden")
    return FileResponse(
        invoice.pdf_path,
        media_type="application/pdf",
        filename=f"{invoice.invoice_number}.pdf",
    )


@router.post(
    "/{invoice_id}/send",
    response_model=InvoiceOut,
    dependencies=[
        Depends(require_module("communication.smtp")),
        Depends(enforce_smtp_rate_limit),
    ],
)
def send_invoice(
    invoice_id: int,
    payload: InvoiceSendRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = (
        db.query(Invoice)
        .filter(Invoice.id == invoice_id)
        .with_for_update()
        .one_or_none()
    )
    if invoice is None:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    idempotency_key = idempotency_key.strip()
    if not idempotency_key or len(idempotency_key) > 128:
        raise HTTPException(status_code=400, detail="Ungültiger Idempotency-Key")
    if not invoice.pdf_path or not os.path.isfile(invoice.pdf_path):
        raise HTTPException(status_code=400, detail="Kein PDF vorhanden")
    client = db.get(Client, invoice.client_id)
    if not client.email:
        raise HTTPException(status_code=400, detail="Kunde hat keine E-Mail-Adresse hinterlegt")
    if not payload.pdf_reviewed:
        raise HTTPException(
            status_code=400,
            detail="Das Rechnungs-PDF muss vor dem Versand geprüft werden",
        )
    if (
        payload.recipient != client.email
        or payload.invoice_number != invoice.invoice_number
        or money(payload.total) != money(invoice.total)
    ):
        raise HTTPException(
            status_code=409,
            detail="Versandbestätigung stimmt nicht mehr mit der Rechnung überein",
        )

    fingerprint = request_fingerprint(
        {
            "invoice_id": invoice.id,
            "recipient": client.email,
            "invoice_number": invoice.invoice_number,
            "total": str(money(invoice.total)),
            "pdf_reviewed": payload.pdf_reviewed,
            "resend": payload.resend,
        }
    )
    existing_attempt = (
        db.query(InvoiceSendAttempt)
        .filter(InvoiceSendAttempt.idempotency_key == idempotency_key)
        .one_or_none()
    )
    if existing_attempt is not None:
        if existing_attempt.request_fingerprint != fingerprint:
            raise HTTPException(
                status_code=409,
                detail="Idempotency-Key wurde bereits für einen anderen Versand verwendet",
            )
        if existing_attempt.outcome == "sent":
            return invoice
        raise HTTPException(
            status_code=409,
            detail=(
                "Dieser Versandversuch ist fehlgeschlagen; für einen neuen bewussten "
                "Versuch ist ein neuer Idempotency-Key erforderlich"
            ),
        )

    if invoice.status not in {InvoiceStatus.draft, InvoiceStatus.sent}:
        raise HTTPException(
            status_code=400,
            detail="Nur Entwürfe und bereits versendete Rechnungen können gesendet werden",
        )
    expected_resend = invoice.status == InvoiceStatus.sent
    if payload.resend != expected_resend:
        raise HTTPException(
            status_code=409,
            detail="Erstversand und Wiederversand müssen ausdrücklich unterschieden werden",
        )
    company = _get_or_create_settings(db)

    attempt = InvoiceSendAttempt(
        invoice_id=invoice.id,
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
        recipient=client.email,
        is_resend=payload.resend,
    )
    db.add(attempt)
    db.flush()

    subject = f"Rechnung {invoice.invoice_number}"
    body = (
        f"Hallo {client.contact_person or client.name},\n\n"
        f"anbei erhalten Sie die Rechnung {invoice.invoice_number} "
        f"über {invoice.total} EUR, fällig am {invoice.due_date.strftime('%d.%m.%Y')}.\n\n"
        f"Viele Grüße\n{company.owner_name or company.company_name}"
    )
    try:
        message_id = send_invoice_email(
            client.email, subject, body, invoice.pdf_path, f"{invoice.invoice_number}.pdf"
        )
    except EmailNotConfigured as exc:
        attempt.outcome = "failed"
        attempt.failure_code = type(exc).__name__
        attempt.completed_at = utc_now_naive()
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        attempt.outcome = "failed"
        attempt.failure_code = type(exc).__name__
        attempt.completed_at = utc_now_naive()
        db.commit()
        raise HTTPException(
            status_code=502,
            detail="Versand fehlgeschlagen; die Rechnung wurde nicht als versendet markiert",
        )

    invoice.status = InvoiceStatus.sent
    invoice.sent_at = invoice.sent_at or utc_now_naive()
    attempt.outcome = "sent"
    attempt.message_id = message_id
    attempt.completed_at = utc_now_naive()
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/{invoice_id}/send-attempts", response_model=list[InvoiceSendAttemptOut])
def list_send_attempts(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if db.get(Invoice, invoice_id) is None:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    attempts = (
        db.query(InvoiceSendAttempt)
        .filter(InvoiceSendAttempt.invoice_id == invoice_id)
        .order_by(InvoiceSendAttempt.id)
        .all()
    )
    return [
        {
            "id": attempt.id,
            "recipient": attempt.recipient,
            "is_resend": attempt.is_resend,
            "outcome": attempt.outcome,
            "message_id_redacted": (
                f"sha256:{sha256(attempt.message_id.encode()).hexdigest()[:12]}"
                if attempt.message_id
                else None
            ),
            "failure_code": attempt.failure_code,
            "created_at": attempt.created_at,
            "completed_at": attempt.completed_at,
        }
        for attempt in attempts
    ]


ALLOWED_STATUS_TRANSITIONS: dict[InvoiceStatus, set[InvoiceStatus]] = {
    InvoiceStatus.draft: {InvoiceStatus.cancelled},
    InvoiceStatus.sent: {InvoiceStatus.paid, InvoiceStatus.cancelled},
    InvoiceStatus.paid: set(),
    InvoiceStatus.cancelled: set(),
}


@router.put("/{invoice_id}/status", response_model=InvoiceOut)
def update_status(
    invoice_id: int,
    payload: InvoiceStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    if payload.status not in ALLOWED_STATUS_TRANSITIONS.get(invoice.status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Statuswechsel von {invoice.status.value} zu {payload.status.value} nicht erlaubt",
        )
    invoice.status = payload.status
    if payload.status == InvoiceStatus.paid:
        invoice.paid_at = utc_now_naive()
    db.commit()
    db.refresh(invoice)
    return invoice


@router.delete("/{invoice_id}", status_code=204)
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    if invoice.status != InvoiceStatus.draft or invoice.sent_at is not None:
        raise HTTPException(
            status_code=400, detail="Nur unversendete Entwürfe können gelöscht werden"
        )
    pdf_path = invoice.pdf_path
    for entry in invoice.time_entries:
        entry.billed = False
        entry.invoice_id = None
    if invoice.quote_id is not None:
        quote = db.get(Quote, invoice.quote_id)
        if quote is not None:
            quote.status = QuoteStatus.accepted
            quote.converted_invoice_id = None
    db.delete(invoice)
    db.commit()
    if pdf_path:
        try:
            os.remove(pdf_path)
        except FileNotFoundError:
            pass

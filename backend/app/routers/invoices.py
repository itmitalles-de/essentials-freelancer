from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.email_utils import EmailNotConfigured, send_invoice_email
from app.models import (
    Client,
    CompanySettings,
    Invoice,
    InvoiceLineItem,
    InvoiceStatus,
    TimeEntry,
    User,
)
from app.pdf import generate_invoice_pdf
from app.schemas import InvoiceCreate, InvoiceOut, InvoiceStatusUpdate

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


def _get_or_create_settings(db: Session) -> CompanySettings:
    company = db.get(CompanySettings, 1)
    if company is None:
        company = CompanySettings(id=1)
        db.add(company)
        db.commit()
        db.refresh(company)
    return company


@router.get("", response_model=list[InvoiceOut])
def list_invoices(
    client_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Invoice)
    if client_id is not None:
        query = query.filter(Invoice.client_id == client_id)
    return query.order_by(Invoice.id.desc()).all()


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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = db.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    if not payload.time_entry_ids:
        raise HTTPException(status_code=400, detail="Keine Zeiteinträge ausgewählt")

    entries = (
        db.query(TimeEntry)
        .filter(TimeEntry.id.in_(payload.time_entry_ids))
        .all()
    )
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

    company = _get_or_create_settings(db)
    today = date.today()
    due_days = payload.due_in_days or company.default_payment_terms_days
    invoice_number = f"{company.invoice_number_prefix}-{today.year}-{company.next_invoice_number:04d}"

    invoice = Invoice(
        client_id=client.id,
        invoice_number=invoice_number,
        issue_date=today,
        due_date=today + timedelta(days=due_days),
        status=InvoiceStatus.draft,
        notes=payload.notes,
        total=Decimal("0"),
    )
    db.add(invoice)
    db.flush()

    total = Decimal("0")
    for entry in entries:
        hours = Decimal(entry.duration_minutes) / Decimal(60)
        rate = Decimal(entry.hourly_rate)
        amount = (hours * rate).quantize(Decimal("0.01"))
        description = entry.description or f"Leistung am {entry.date.strftime('%d.%m.%Y')}"
        line_item = InvoiceLineItem(
            invoice_id=invoice.id,
            description=description,
            quantity=hours.quantize(Decimal("0.01")),
            unit_price=rate,
            amount=amount,
        )
        db.add(line_item)
        total += amount
        entry.billed = True
        entry.invoice_id = invoice.id

    invoice.total = total
    company.next_invoice_number += 1
    db.commit()
    db.refresh(invoice)

    pdf_path = generate_invoice_pdf(invoice, client, company)
    invoice.pdf_path = pdf_path
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = db.get(Invoice, invoice_id)
    if invoice is None or not invoice.pdf_path:
        raise HTTPException(status_code=404, detail="PDF nicht gefunden")
    return FileResponse(
        invoice.pdf_path,
        media_type="application/pdf",
        filename=f"{invoice.invoice_number}.pdf",
    )


@router.post("/{invoice_id}/send", response_model=InvoiceOut)
def send_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    if not invoice.pdf_path:
        raise HTTPException(status_code=400, detail="Kein PDF vorhanden")
    client = db.get(Client, invoice.client_id)
    if not client.email:
        raise HTTPException(status_code=400, detail="Kunde hat keine E-Mail-Adresse hinterlegt")
    company = _get_or_create_settings(db)

    subject = f"Rechnung {invoice.invoice_number}"
    body = (
        f"Hallo {client.contact_person or client.name},\n\n"
        f"anbei erhalten Sie die Rechnung {invoice.invoice_number} "
        f"über {invoice.total} EUR, fällig am {invoice.due_date.strftime('%d.%m.%Y')}.\n\n"
        f"Viele Grüße\n{company.owner_name or company.company_name}"
    )
    try:
        send_invoice_email(
            client.email, subject, body, invoice.pdf_path, f"{invoice.invoice_number}.pdf"
        )
    except EmailNotConfigured as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Versand fehlgeschlagen: {exc}")

    invoice.status = InvoiceStatus.sent
    invoice.sent_at = datetime.utcnow()
    db.commit()
    db.refresh(invoice)
    return invoice


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
    invoice.status = payload.status
    if payload.status == InvoiceStatus.paid:
        invoice.paid_at = datetime.utcnow()
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
    if invoice.status != InvoiceStatus.draft:
        raise HTTPException(
            status_code=400, detail="Nur Entwürfe können gelöscht werden"
        )
    for entry in invoice.time_entries:
        entry.billed = False
        entry.invoice_id = None
    db.delete(invoice)
    db.commit()

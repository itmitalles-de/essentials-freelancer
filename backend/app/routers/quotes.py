import os
import uuid
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.database import get_db
from app.deps import get_current_user, require_module
from app.models import (
    Client,
    Invoice,
    InvoiceLineItem,
    InvoiceStatus,
    Project,
    Quote,
    QuoteLineItem,
    QuoteStatus,
    User,
)
from app.money import line_amounts, money
from app.pdf import generate_invoice_pdf, generate_quote_pdf
from app.routers.invoices import _get_or_create_settings
from app.schemas import QuoteCreate, QuoteOut, QuoteStatusUpdate

router = APIRouter(
    prefix="/api/quotes",
    tags=["quotes"],
    dependencies=[Depends(require_module("sales.quotes"))],
)


def _client_and_project(
    db: Session, client_id: int, project_id: int | None
) -> tuple[Client, Project | None]:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    project = db.get(Project, project_id) if project_id is not None else None
    if project_id is not None and project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    if project is not None and project.client_id != client.id:
        raise HTTPException(status_code=400, detail="Projekt gehört nicht zu diesem Kunden")
    return client, project


def _replace_line_items(quote: Quote, payload: QuoteCreate) -> Decimal:
    quote.line_items.clear()
    subtotal = Decimal("0")
    tax_total = Decimal("0")
    total = Decimal("0")
    for item in payload.line_items:
        net_amount, tax_amount, amount = line_amounts(
            item.quantity, item.unit_price, item.tax_rate
        )
        quote.line_items.append(
            QuoteLineItem(
                description=item.description,
                quantity=item.quantity,
                unit=item.unit,
                unit_price=item.unit_price,
                net_amount=net_amount,
                tax_rate=item.tax_rate,
                tax_amount=tax_amount,
                amount=amount,
            )
        )
        subtotal += net_amount
        tax_total += tax_amount
        total += amount
    quote.subtotal = money(subtotal)
    quote.tax_total = money(tax_total)
    quote.total = money(total)
    return total


@router.get("", response_model=list[QuoteOut])
def list_quotes(
    client_id: int | None = None,
    project_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Quote)
    if client_id is not None:
        query = query.filter(Quote.client_id == client_id)
    if project_id is not None:
        query = query.filter(Quote.project_id == project_id)
    return query.order_by(Quote.id.desc()).all()


@router.post("", response_model=QuoteOut)
def create_quote(
    payload: QuoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client, project = _client_and_project(db, payload.client_id, payload.project_id)
    if project is not None and not project.active:
        raise HTTPException(status_code=400, detail="Projekt ist archiviert")
    company = _get_or_create_settings(db, lock_for_invoice_number=True)
    today = date.today()
    quote = Quote(
        client_id=client.id,
        project_id=payload.project_id,
        quote_number=f"{company.quote_number_prefix}-{today.year}-{company.next_quote_number:04d}",
        issue_date=today,
        valid_until=today + timedelta(days=payload.valid_in_days),
        status=QuoteStatus.draft,
        notes=payload.notes,
        subtotal=Decimal("0"),
        tax_total=Decimal("0"),
        total=Decimal("0"),
    )
    db.add(quote)
    db.flush()
    _replace_line_items(quote, payload)
    company.next_quote_number += 1
    db.flush()
    db.refresh(quote)

    expected_path = os.path.join(
        app_settings.pdf_storage_dir, f"quote-{quote.quote_number}.pdf"
    )
    try:
        quote.pdf_path = generate_quote_pdf(quote, client, company)
        db.commit()
    except Exception as exc:
        db.rollback()
        try:
            os.remove(expected_path)
        except FileNotFoundError:
            pass
        raise HTTPException(
            status_code=500,
            detail=f"Angebot konnte nicht erstellt werden (PDF-Fehler: {exc})",
        )
    db.refresh(quote)
    return quote


@router.get("/{quote_id}", response_model=QuoteOut)
def get_quote(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quote = db.get(Quote, quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Angebot nicht gefunden")
    return quote


@router.put("/{quote_id}", response_model=QuoteOut)
def update_quote(
    quote_id: int,
    payload: QuoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quote = db.get(Quote, quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Angebot nicht gefunden")
    if quote.status != QuoteStatus.draft:
        raise HTTPException(status_code=400, detail="Nur Entwürfe können geändert werden")
    client, project = _client_and_project(db, payload.client_id, payload.project_id)
    if project is not None and not project.active:
        raise HTTPException(status_code=400, detail="Projekt ist archiviert")

    quote.client_id = client.id
    quote.project_id = payload.project_id
    quote.valid_until = quote.issue_date + timedelta(days=payload.valid_in_days)
    quote.notes = payload.notes
    _replace_line_items(quote, payload)
    db.flush()

    old_path = quote.pdf_path
    new_path = os.path.join(
        app_settings.pdf_storage_dir,
        f"quote-{quote.quote_number}-{uuid.uuid4().hex}.pdf",
    )
    company = _get_or_create_settings(db)
    try:
        generate_quote_pdf(quote, client, company, new_path)
        quote.pdf_path = new_path
        db.commit()
    except Exception as exc:
        db.rollback()
        try:
            os.remove(new_path)
        except FileNotFoundError:
            pass
        raise HTTPException(
            status_code=500,
            detail=f"Angebot konnte nicht geändert werden (PDF-Fehler: {exc})",
        )
    if old_path and old_path != new_path:
        try:
            os.remove(old_path)
        except FileNotFoundError:
            pass
    db.refresh(quote)
    return quote


@router.get("/{quote_id}/pdf")
def download_quote_pdf(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quote = db.get(Quote, quote_id)
    if quote is None or not quote.pdf_path or not os.path.isfile(quote.pdf_path):
        raise HTTPException(status_code=404, detail="PDF nicht gefunden")
    return FileResponse(
        quote.pdf_path,
        media_type="application/pdf",
        filename=f"{quote.quote_number}.pdf",
    )


ALLOWED_STATUS_TRANSITIONS: dict[QuoteStatus, set[QuoteStatus]] = {
    QuoteStatus.draft: {QuoteStatus.sent, QuoteStatus.rejected},
    QuoteStatus.sent: {QuoteStatus.accepted, QuoteStatus.rejected},
    QuoteStatus.accepted: set(),
    QuoteStatus.rejected: set(),
    QuoteStatus.converted: set(),
}


@router.put("/{quote_id}/status", response_model=QuoteOut)
def update_quote_status(
    quote_id: int,
    payload: QuoteStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quote = db.get(Quote, quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Angebot nicht gefunden")
    if payload.status not in ALLOWED_STATUS_TRANSITIONS[quote.status]:
        raise HTTPException(
            status_code=400,
            detail=f"Statuswechsel von {quote.status.value} zu {payload.status.value} nicht erlaubt",
        )
    quote.status = payload.status
    db.commit()
    db.refresh(quote)
    return quote


@router.post("/{quote_id}/convert", response_model=QuoteOut)
def convert_quote_to_invoice(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quote = (
        db.query(Quote).filter(Quote.id == quote_id).with_for_update().one_or_none()
    )
    if quote is None:
        raise HTTPException(status_code=404, detail="Angebot nicht gefunden")
    if quote.status != QuoteStatus.accepted:
        raise HTTPException(
            status_code=400, detail="Nur angenommene Angebote können übernommen werden"
        )
    if quote.converted_invoice_id is not None:
        raise HTTPException(status_code=400, detail="Angebot wurde bereits übernommen")

    client = db.get(Client, quote.client_id)
    company = _get_or_create_settings(db, lock_for_invoice_number=True)
    today = date.today()
    invoice = Invoice(
        client_id=quote.client_id,
        quote_id=quote.id,
        invoice_number=f"{company.invoice_number_prefix}-{today.year}-{company.next_invoice_number:04d}",
        issue_date=today,
        due_date=today + timedelta(days=company.default_payment_terms_days),
        status=InvoiceStatus.draft,
        notes=quote.notes,
        subtotal=quote.subtotal,
        tax_total=quote.tax_total,
        total=quote.total,
    )
    db.add(invoice)
    db.flush()
    for item in quote.line_items:
        invoice.line_items.append(
            InvoiceLineItem(
                description=item.description,
                quantity=item.quantity,
                unit=item.unit,
                unit_price=item.unit_price,
                net_amount=item.net_amount,
                tax_rate=item.tax_rate,
                tax_amount=item.tax_amount,
                amount=item.amount,
                project_id=quote.project_id,
            )
        )
    company.next_invoice_number += 1
    quote.status = QuoteStatus.converted
    quote.converted_invoice_id = invoice.id
    db.flush()
    db.refresh(invoice)

    expected_path = os.path.join(
        app_settings.pdf_storage_dir, f"{invoice.invoice_number}.pdf"
    )
    try:
        invoice.pdf_path = generate_invoice_pdf(invoice, client, company)
        db.commit()
    except Exception as exc:
        db.rollback()
        try:
            os.remove(expected_path)
        except FileNotFoundError:
            pass
        raise HTTPException(
            status_code=500,
            detail=f"Rechnung konnte nicht erstellt werden (PDF-Fehler: {exc})",
        )
    db.refresh(quote)
    return quote


@router.delete("/{quote_id}", status_code=204)
def delete_quote(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quote = db.get(Quote, quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Angebot nicht gefunden")
    if quote.status != QuoteStatus.draft:
        raise HTTPException(status_code=400, detail="Nur Entwürfe können gelöscht werden")
    pdf_path = quote.pdf_path
    db.delete(quote)
    db.commit()
    if pdf_path:
        try:
            os.remove(pdf_path)
        except FileNotFoundError:
            pass

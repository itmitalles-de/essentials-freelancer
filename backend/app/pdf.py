import os
import uuid
from decimal import Decimal
from xml.sax.saxutils import escape

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.config import settings
from app.models import CompanySettings, Client, Invoice, Quote

LOGO_MAX_WIDTH = 45 * mm
LOGO_MAX_HEIGHT = 25 * mm
UNIT_LABELS = {
    "hours": "Std.",
    "days": "Tage",
    "items": "Stück",
    "flat": "pauschal",
}


def _eur(value: Decimal) -> str:
    return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def _safe_text(value: object) -> str:
    return escape(str(value)).replace("\n", "<br/>")


def _paragraph(value: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_safe_text(value), style)


def _logo_flowable(logo_path: str | None) -> Image | None:
    if not logo_path or not os.path.exists(logo_path):
        return None
    with PILImage.open(logo_path) as img:
        width, height = img.size
    scale = min(LOGO_MAX_WIDTH / width, LOGO_MAX_HEIGHT / height)
    return Image(logo_path, width=width * scale, height=height * scale)


def _generate_document(
    *,
    file_path: str,
    title: str,
    date_rows: list[tuple[str, str]],
    line_items: list,
    subtotal: Decimal,
    tax_total: Decimal,
    total: Decimal,
    notes: str,
    client: Client,
    company: CompanySettings,
    include_payment_details: bool,
) -> str:
    os.makedirs(settings.pdf_storage_dir, exist_ok=True)
    temporary_path = f"{file_path}.{uuid.uuid4().hex}.tmp"
    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=9, leading=12)
    header_style = ParagraphStyle(
        "header", parent=styles["Heading1"], fontSize=18, spaceAfter=2
    )

    doc = SimpleDocTemplate(
        temporary_path,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
    )
    story = []

    sender_line = " · ".join(
        filter(None, [company.company_name, company.address_line1, company.zip_city])
    )
    logo = _logo_flowable(company.logo_path)
    if logo is not None:
        header_table = Table(
            [[_paragraph(sender_line, small), logo]],
            colWidths=[125 * mm, LOGO_MAX_WIDTH],
        )
        header_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        story.append(header_table)
    else:
        story.append(_paragraph(sender_line, small))
    story.append(Spacer(1, 10 * mm))

    client_lines = [client.name]
    client_lines.extend(
        value
        for value in (
            client.contact_person,
            client.address_line1,
            client.address_line2,
            client.zip_city,
        )
        if value
    )
    story.append(_paragraph("\n".join(client_lines), styles["Normal"]))
    story.append(Spacer(1, 12 * mm))

    story.append(_paragraph(title, header_style))
    story.append(Spacer(1, 4 * mm))

    meta_table = Table(date_rows, colWidths=[40 * mm, 60 * mm])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 8 * mm))

    table_data = [["Beschreibung", "Menge", "Einheit", "Einzelpreis netto", "Betrag brutto"]]
    for item in line_items:
        table_data.append(
            [
                _paragraph(item.description, small),
                f"{Decimal(item.quantity):.2f}",
                UNIT_LABELS.get(item.unit, item.unit),
                _eur(Decimal(item.unit_price)),
                _eur(Decimal(item.amount)),
            ]
        )

    items_table = Table(
        table_data, colWidths=[68 * mm, 22 * mm, 22 * mm, 31 * mm, 32 * mm]
    )
    items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(items_table)
    story.append(Spacer(1, 4 * mm))

    total_rows = [["Zwischensumme netto", _eur(subtotal)]]
    tax_by_rate: dict[Decimal, Decimal] = {}
    for item in line_items:
        rate = Decimal(item.tax_rate)
        tax_by_rate[rate] = tax_by_rate.get(rate, Decimal("0")) + Decimal(
            item.tax_amount
        )
    for rate in sorted(tax_by_rate):
        amount = tax_by_rate[rate]
        if amount:
            total_rows.append([f"Steuer {rate:.2f} %", _eur(amount)])
    if tax_total and not any(tax_by_rate.values()):
        total_rows.append(["Steuer", _eur(tax_total)])
    total_rows.append(["Gesamtbetrag", _eur(total)])
    total_table = Table(total_rows, colWidths=[143 * mm, 32 * mm])
    total_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("LINEABOVE", (0, 0), (-1, 0), 0.75, colors.black),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(total_table)
    story.append(Spacer(1, 10 * mm))

    if notes:
        story.append(_paragraph(notes, small))
        story.append(Spacer(1, 6 * mm))
    if company.invoice_footer_note:
        story.append(_paragraph(company.invoice_footer_note, small))
        story.append(Spacer(1, 6 * mm))

    if include_payment_details:
        payment_lines = []
        if company.iban:
            payment_lines.append(f"IBAN: {company.iban}")
        if company.bic:
            payment_lines.append(f"BIC: {company.bic}")
        if company.bank_name:
            payment_lines.append(f"Bank: {company.bank_name}")
        if company.tax_id:
            payment_lines.append(f"Steuernummer: {company.tax_id}")
        if payment_lines:
            story.append(_paragraph("\n".join(payment_lines), small))

    try:
        doc.build(story)
        with open(temporary_path, "rb") as generated:
            os.fsync(generated.fileno())
        os.replace(temporary_path, file_path)
    except Exception:
        try:
            os.remove(temporary_path)
        except FileNotFoundError:
            pass
        raise
    return file_path


def generate_invoice_pdf(
    invoice: Invoice, client: Client, company: CompanySettings
) -> str:
    file_path = os.path.join(settings.pdf_storage_dir, f"{invoice.invoice_number}.pdf")
    return _generate_document(
        file_path=file_path,
        title=f"Rechnung {invoice.invoice_number}",
        date_rows=[
            ("Rechnungsdatum:", invoice.issue_date.strftime("%d.%m.%Y")),
            ("Fällig am:", invoice.due_date.strftime("%d.%m.%Y")),
        ],
        line_items=invoice.line_items,
        subtotal=Decimal(invoice.subtotal),
        tax_total=Decimal(invoice.tax_total),
        total=Decimal(invoice.total),
        notes=invoice.notes,
        client=client,
        company=company,
        include_payment_details=True,
    )


def generate_quote_pdf(
    quote: Quote,
    client: Client,
    company: CompanySettings,
    file_path: str | None = None,
) -> str:
    if file_path is None:
        file_path = os.path.join(
            settings.pdf_storage_dir, f"quote-{quote.quote_number}.pdf"
        )
    return _generate_document(
        file_path=file_path,
        title=f"Angebot {quote.quote_number}",
        date_rows=[
            ("Angebotsdatum:", quote.issue_date.strftime("%d.%m.%Y")),
            ("Gültig bis:", quote.valid_until.strftime("%d.%m.%Y")),
        ],
        line_items=quote.line_items,
        subtotal=Decimal(quote.subtotal),
        tax_total=Decimal(quote.tax_total),
        total=Decimal(quote.total),
        notes=quote.notes,
        client=client,
        company=company,
        include_payment_details=False,
    )

import os
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

from app.config import settings
from app.models import CompanySettings, Client, Invoice


def _eur(value: Decimal) -> str:
    return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def generate_invoice_pdf(
    invoice: Invoice, client: Client, company: CompanySettings
) -> str:
    os.makedirs(settings.pdf_storage_dir, exist_ok=True)
    file_path = os.path.join(
        settings.pdf_storage_dir, f"{invoice.invoice_number}.pdf"
    )

    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=9, leading=12)
    header_style = ParagraphStyle(
        "header", parent=styles["Heading1"], fontSize=18, spaceAfter=2
    )

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
    )

    story = []

    sender_line = " · ".join(
        filter(
            None,
            [
                company.company_name,
                company.address_line1,
                company.zip_city,
            ],
        )
    )
    story.append(Paragraph(sender_line, small))
    story.append(Spacer(1, 10 * mm))

    client_lines = [client.name]
    if client.contact_person:
        client_lines.append(client.contact_person)
    if client.address_line1:
        client_lines.append(client.address_line1)
    if client.address_line2:
        client_lines.append(client.address_line2)
    if client.zip_city:
        client_lines.append(client.zip_city)
    story.append(Paragraph("<br/>".join(client_lines), styles["Normal"]))
    story.append(Spacer(1, 12 * mm))

    story.append(Paragraph(f"Rechnung {invoice.invoice_number}", header_style))
    story.append(Spacer(1, 4 * mm))

    meta_table = Table(
        [
            ["Rechnungsdatum:", invoice.issue_date.strftime("%d.%m.%Y")],
            ["Fällig am:", invoice.due_date.strftime("%d.%m.%Y")],
        ],
        colWidths=[40 * mm, 60 * mm],
    )
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

    table_data = [["Beschreibung", "Menge (Std.)", "Preis/Std.", "Betrag"]]
    for item in invoice.line_items:
        table_data.append(
            [
                Paragraph(item.description, small),
                f"{Decimal(item.quantity):.2f}",
                _eur(Decimal(item.unit_price)),
                _eur(Decimal(item.amount)),
            ]
        )

    items_table = Table(
        table_data, colWidths=[85 * mm, 30 * mm, 30 * mm, 30 * mm]
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

    total_table = Table(
        [["Gesamtbetrag", _eur(Decimal(invoice.total))]],
        colWidths=[145 * mm, 30 * mm],
    )
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

    if invoice.notes:
        story.append(Paragraph(invoice.notes, small))
        story.append(Spacer(1, 6 * mm))

    if company.invoice_footer_note:
        story.append(Paragraph(company.invoice_footer_note, small))
        story.append(Spacer(1, 6 * mm))

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
        story.append(Paragraph("<br/>".join(payment_lines), small))

    doc.build(story)
    return file_path

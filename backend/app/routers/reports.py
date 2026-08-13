import csv
from datetime import date
from decimal import Decimal
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_module
from app.models import (
    Expense,
    Invoice,
    InvoiceLineItem,
    InvoiceStatus,
    Quote,
    QuoteStatus,
    TimeEntry,
    User,
)
from app.money import money
from app.schemas import (
    ExpenseCategoryReport,
    ExpenseReport,
    InvoiceReport,
    QuoteReport,
    ReportSummary,
    TimeReport,
    TimeReportGroup,
)

router = APIRouter(
    prefix="/api/reports",
    tags=["reports"],
    dependencies=[Depends(require_module("core.reporting"))],
)


def _date_range(query, column, date_from: date | None, date_to: date | None):
    if date_from is not None:
        query = query.filter(column >= date_from)
    if date_to is not None:
        query = query.filter(column <= date_to)
    return query


def _validate_date_range(date_from: date | None, date_to: date | None) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=422, detail="Startdatum darf nicht nach dem Enddatum liegen"
        )


def _time_query(
    db: Session,
    date_from: date | None,
    date_to: date | None,
    client_id: int | None,
    project_id: int | None,
):
    query = _date_range(db.query(TimeEntry), TimeEntry.date, date_from, date_to)
    if client_id is not None:
        query = query.filter(TimeEntry.client_id == client_id)
    if project_id is not None:
        query = query.filter(TimeEntry.project_id == project_id)
    return query


def _quote_query(
    db: Session,
    date_from: date | None,
    date_to: date | None,
    client_id: int | None,
    project_id: int | None,
):
    query = _date_range(db.query(Quote), Quote.issue_date, date_from, date_to)
    if client_id is not None:
        query = query.filter(Quote.client_id == client_id)
    if project_id is not None:
        query = query.filter(Quote.project_id == project_id)
    return query


def _invoice_query(
    db: Session,
    date_from: date | None,
    date_to: date | None,
    client_id: int | None,
    project_id: int | None,
):
    query = _date_range(db.query(Invoice), Invoice.issue_date, date_from, date_to)
    if client_id is not None:
        query = query.filter(Invoice.client_id == client_id)
    if project_id is not None:
        query = (
            query.join(InvoiceLineItem)
            .filter(InvoiceLineItem.project_id == project_id)
            .distinct()
        )
    return query


def _expense_query(
    db: Session,
    date_from: date | None,
    date_to: date | None,
    category: str | None,
):
    query = _date_range(db.query(Expense), Expense.date, date_from, date_to)
    if category:
        query = query.filter(Expense.category == category)
    return query


def _hours(minutes: int) -> Decimal:
    return money(Decimal(minutes) / Decimal("60"))


@router.get("/summary", response_model=ReportSummary)
def summary(
    date_from: date | None = None,
    date_to: date | None = None,
    client_id: int | None = None,
    project_id: int | None = None,
    expense_category: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    _validate_date_range(date_from, date_to)
    entries = _time_query(db, date_from, date_to, client_id, project_id).all()
    groups: dict[tuple[int, int | None], dict[str, int]] = {}
    captured_minutes = 0
    unbilled_minutes = 0
    for entry in entries:
        captured_minutes += entry.duration_minutes
        key = (entry.client_id, entry.project_id)
        group = groups.setdefault(key, {"captured": 0, "unbilled": 0})
        group["captured"] += entry.duration_minutes
        if not entry.billed and entry.running_started_at is None:
            unbilled_minutes += entry.duration_minutes
            group["unbilled"] += entry.duration_minutes

    quotes = _quote_query(db, date_from, date_to, client_id, project_id).all()
    quote_statuses = {status.value: 0 for status in QuoteStatus}
    for quote in quotes:
        quote_statuses[quote.status.value] += 1
    resolved_quotes = quote_statuses["converted"] + quote_statuses["rejected"]
    conversion_rate = (
        money(Decimal(quote_statuses["converted"]) * Decimal("100") / resolved_quotes)
        if resolved_quotes
        else Decimal("0.00")
    )

    invoices = _invoice_query(db, date_from, date_to, client_id, project_id).all()
    invoice_statuses = {
        "draft": 0,
        "sent": 0,
        "overdue": 0,
        "paid": 0,
        "cancelled": 0,
    }
    open_amount = Decimal("0")
    paid_amount = Decimal("0")
    today = date.today()
    for invoice in invoices:
        if invoice.status == InvoiceStatus.sent and invoice.due_date < today:
            invoice_statuses["overdue"] += 1
        else:
            invoice_statuses[invoice.status.value] += 1
        if invoice.status == InvoiceStatus.sent:
            open_amount += Decimal(invoice.total)
        if invoice.status == InvoiceStatus.paid:
            paid_amount += Decimal(invoice.total)

    expenses = _expense_query(db, date_from, date_to, expense_category).all()
    expense_categories: dict[str, Decimal] = {}
    expense_total = Decimal("0")
    for expense in expenses:
        category = expense.category or "Ohne Kategorie"
        amount = Decimal(expense.amount)
        expense_categories[category] = expense_categories.get(category, Decimal("0")) + amount
        expense_total += amount

    return ReportSummary(
        date_from=date_from,
        date_to=date_to,
        client_id=client_id,
        project_id=project_id,
        time=TimeReport(
            captured_hours=_hours(captured_minutes),
            unbilled_hours=_hours(unbilled_minutes),
            groups=[
                TimeReportGroup(
                    client_id=key[0],
                    project_id=key[1],
                    captured_hours=_hours(value["captured"]),
                    unbilled_hours=_hours(value["unbilled"]),
                )
                for key, value in sorted(
                    groups.items(), key=lambda item: (item[0][0], item[0][1] or 0)
                )
            ],
        ),
        quotes=QuoteReport(
            statuses=quote_statuses,
            conversion_rate_percent=conversion_rate,
        ),
        invoices=InvoiceReport(
            statuses=invoice_statuses,
            open_amount=money(open_amount),
            paid_amount=money(paid_amount),
        ),
        expenses=ExpenseReport(
            total=money(expense_total),
            categories=[
                ExpenseCategoryReport(category=category, amount=money(amount))
                for category, amount in sorted(expense_categories.items())
            ],
        ),
    )


def _safe_csv(value: object) -> object:
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _csv_response(filename: str, header: list[str], rows: list[list[object]]):
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(header)
    writer.writerows([[_safe_csv(value) for value in row] for row in rows])
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/time.csv")
def time_csv(
    date_from: date | None = None,
    date_to: date | None = None,
    client_id: int | None = None,
    project_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    _validate_date_range(date_from, date_to)
    entries = _time_query(db, date_from, date_to, client_id, project_id).order_by(
        TimeEntry.date, TimeEntry.id
    )
    return _csv_response(
        "zeiten.csv",
        ["id", "date", "client_id", "project_id", "description", "minutes", "hourly_rate", "billed", "invoice_id"],
        [
            [entry.id, entry.date, entry.client_id, entry.project_id or "", entry.description, entry.duration_minutes, entry.hourly_rate, entry.billed, entry.invoice_id or ""]
            for entry in entries
        ],
    )


@router.get("/quotes.csv")
def quotes_csv(
    date_from: date | None = None,
    date_to: date | None = None,
    client_id: int | None = None,
    project_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    _validate_date_range(date_from, date_to)
    quotes = _quote_query(db, date_from, date_to, client_id, project_id).order_by(
        Quote.issue_date, Quote.id
    )
    return _csv_response(
        "angebote.csv",
        ["id", "quote_number", "issue_date", "valid_until", "client_id", "project_id", "status", "subtotal", "tax_total", "total"],
        [[item.id, item.quote_number, item.issue_date, item.valid_until, item.client_id, item.project_id or "", item.status.value, item.subtotal, item.tax_total, item.total] for item in quotes],
    )


@router.get("/invoices.csv")
def invoices_csv(
    date_from: date | None = None,
    date_to: date | None = None,
    client_id: int | None = None,
    project_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    _validate_date_range(date_from, date_to)
    invoices = _invoice_query(db, date_from, date_to, client_id, project_id).order_by(
        Invoice.issue_date, Invoice.id
    )
    return _csv_response(
        "rechnungen.csv",
        ["id", "invoice_number", "issue_date", "due_date", "client_id", "status", "subtotal", "tax_total", "total"],
        [[item.id, item.invoice_number, item.issue_date, item.due_date, item.client_id, item.status.value, item.subtotal, item.tax_total, item.total] for item in invoices],
    )


@router.get("/expenses.csv")
def expenses_csv(
    date_from: date | None = None,
    date_to: date | None = None,
    expense_category: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    _validate_date_range(date_from, date_to)
    expenses = _expense_query(db, date_from, date_to, expense_category).order_by(
        Expense.date, Expense.id
    )
    return _csv_response(
        "ausgaben.csv",
        ["id", "date", "description", "category", "amount", "has_receipt"],
        [[item.id, item.date, item.description, item.category, item.amount, bool(item.receipt_path)] for item in expenses],
    )

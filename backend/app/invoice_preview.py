from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal

from app.billing_policy import (
    BillingDecision,
    calculate_billing_decision,
    stored_billing_decision,
)
from app.idempotency import request_fingerprint
from app.models import Client, CompanySettings, Project, TimeEntry
from app.money import minute_line_amounts, money


@dataclass(frozen=True)
class BillingPreviewLine:
    time_entry_id: int
    line_kind: str
    description: str
    actual_minutes: int
    billable_minutes: int
    hourly_rate: Decimal
    rate_type: str
    minimum_minutes: int
    increment_minutes: int | None
    service_mode: str
    is_first_order: bool
    billing_reason: str
    billing_policy_id: str
    service_date: date
    project_id: int | None
    project_name: str | None
    net_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal

    def token_data(self) -> dict:
        values = asdict(self)
        for key in ("hourly_rate", "net_amount", "tax_amount", "total_amount"):
            values[key] = str(values[key])
        values["service_date"] = self.service_date.isoformat()
        return values


@dataclass
class BillingPreview:
    client_id: int
    lines: list[BillingPreviewLine]
    work_total: Decimal
    travel_total: Decimal
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    tax_rate: Decimal
    tax_status: str
    tax_notice: str | None
    confirmation_token: str
    decisions: dict[int, BillingDecision] = field(repr=False)

    def response_data(self) -> dict:
        return {
            "client_id": self.client_id,
            "lines": [asdict(line) for line in self.lines],
            "work_total": self.work_total,
            "travel_total": self.travel_total,
            "subtotal": self.subtotal,
            "tax_total": self.tax_total,
            "total": self.total,
            "tax_rate": self.tax_rate,
            "tax_status": self.tax_status,
            "tax_notice": self.tax_notice,
            "confirmation_token": self.confirmation_token,
        }


def _line(
    *,
    entry: TimeEntry,
    project: Project | None,
    decision: BillingDecision,
    line_kind: str,
    tax_rate: Decimal,
) -> BillingPreviewLine:
    if line_kind == "work":
        actual_minutes = decision.actual_minutes
        billable_minutes = decision.billable_minutes
        hourly_rate = decision.hourly_rate
        rate_type = decision.rate_type
        minimum_minutes = decision.minimum_minutes
        increment_minutes = decision.increment_minutes
        billing_reason = decision.billing_reason
        prefix = "Arbeitsleistung"
    else:
        actual_minutes = decision.travel_actual_minutes
        billable_minutes = decision.travel_billable_minutes
        hourly_rate = decision.travel_hourly_rate
        rate_type = "travel"
        minimum_minutes = decision.travel_minimum_minutes
        increment_minutes = decision.travel_increment_minutes
        billing_reason = decision.travel_billing_reason or "travel_actual_minutes"
        prefix = "Anfahrt"

    net_amount, tax_amount, total_amount = minute_line_amounts(
        billable_minutes, hourly_rate, tax_rate
    )
    service_date = entry.date.strftime("%d.%m.%Y")
    description = (
        f"{prefix} am {service_date}: {entry.description}"
        if entry.description
        else f"{prefix} am {service_date}"
    )
    return BillingPreviewLine(
        time_entry_id=entry.id,
        line_kind=line_kind,
        description=description,
        actual_minutes=actual_minutes,
        billable_minutes=billable_minutes,
        hourly_rate=hourly_rate,
        rate_type=rate_type,
        minimum_minutes=minimum_minutes,
        increment_minutes=increment_minutes,
        service_mode=decision.service_mode,
        is_first_order=decision.is_first_order,
        billing_reason=billing_reason,
        billing_policy_id=decision.billing_policy_id,
        service_date=entry.date,
        project_id=entry.project_id,
        project_name=project.name if project is not None else None,
        net_amount=net_amount,
        tax_amount=tax_amount,
        total_amount=total_amount,
    )


def build_billing_preview(
    *,
    client: Client,
    entries: list[TimeEntry],
    projects: dict[int, Project],
    company: CompanySettings,
    tax_rate: Decimal,
    due_in_days: int | None,
) -> BillingPreview:
    tax_rate = Decimal(tax_rate)
    if company.small_business_notice_enabled:
        if tax_rate != Decimal("0"):
            raise ValueError(
                "Das bestätigte Kleinunternehmerprofil kann nur mit 0 Prozent verwendet werden"
            )
        tax_status = "small_business_section_19"
        tax_notice = company.small_business_notice_text.strip()
        if not tax_notice:
            raise ValueError("Der bestätigte §-19-Hinweis fehlt")
    else:
        tax_status = "operator_selected"
        tax_notice = None

    lines: list[BillingPreviewLine] = []
    decisions: dict[int, BillingDecision] = {}
    for entry in entries:
        project = projects.get(entry.project_id) if entry.project_id is not None else None
        if entry.billing_policy_applied:
            decision = stored_billing_decision(entry)
        else:
            decision = calculate_billing_decision(
                actual_minutes=entry.duration_minutes,
                travel_actual_minutes=entry.travel_actual_minutes,
                is_first_order=entry.is_first_order,
                requested_service_mode=entry.service_mode,
                client=client,
                project=project,
                company=company,
            )
        decisions[entry.id] = decision
        lines.append(
            _line(
                entry=entry,
                project=project,
                decision=decision,
                line_kind="work",
                tax_rate=tax_rate,
            )
        )
        if decision.travel_billable_minutes > 0:
            lines.append(
                _line(
                    entry=entry,
                    project=project,
                    decision=decision,
                    line_kind="travel",
                    tax_rate=tax_rate,
                )
            )

    work_total = money(
        sum((line.net_amount for line in lines if line.line_kind == "work"), Decimal("0"))
    )
    travel_total = money(
        sum(
            (line.net_amount for line in lines if line.line_kind == "travel"),
            Decimal("0"),
        )
    )
    subtotal = money(sum((line.net_amount for line in lines), Decimal("0")))
    tax_total = money(sum((line.tax_amount for line in lines), Decimal("0")))
    total = money(sum((line.total_amount for line in lines), Decimal("0")))

    token_payload = {
        "client_id": client.id,
        "entry_ids": [entry.id for entry in entries],
        "lines": [line.token_data() for line in lines],
        "tax_rate": str(tax_rate),
        "tax_status": tax_status,
        "tax_notice": tax_notice,
        "effective_due_in_days": (
            due_in_days
            if due_in_days is not None
            else company.default_payment_terms_days
        ),
        "invoice_number_prefix": company.invoice_number_prefix,
        "footer_note": company.invoice_footer_note,
        "subtotal": str(subtotal),
        "tax_total": str(tax_total),
        "total": str(total),
    }
    confirmation_token = f"billing-confirm:{request_fingerprint(token_payload)}"
    return BillingPreview(
        client_id=client.id,
        lines=lines,
        work_total=work_total,
        travel_total=travel_total,
        subtotal=subtotal,
        tax_total=tax_total,
        total=total,
        tax_rate=tax_rate,
        tax_status=tax_status,
        tax_notice=tax_notice,
        confirmation_token=confirmation_token,
        decisions=decisions,
    )

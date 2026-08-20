from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
import json

from app.models import Client, CompanySettings, Project, TimeEntry


POLICY_SCHEMA = "billing-v1"


class BillingPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class BillingDecision:
    actual_minutes: int
    billable_minutes: int
    hourly_rate: Decimal
    rate_type: str
    rate_source: str
    minimum_minutes: int
    increment_minutes: int | None
    service_mode: str
    is_first_order: bool
    billing_reason: str
    billing_policy_id: str
    travel_actual_minutes: int
    travel_billable_minutes: int
    travel_hourly_rate: Decimal
    travel_minimum_minutes: int
    travel_increment_minutes: int | None
    travel_billing_reason: str | None


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _ceil_to_increment(minutes: int, increment: int) -> int:
    if minutes <= 0:
        return 0
    return ((minutes + increment - 1) // increment) * increment


def billing_policy_id(company: CompanySettings) -> str:
    values = {
        "schema": POLICY_SCHEMA,
        "private_hourly_rate": str(_decimal(company.private_hourly_rate)),
        "business_hourly_rate": str(_decimal(company.business_hourly_rate)),
        "travel_hourly_rate": str(_decimal(company.travel_hourly_rate)),
        "first_order_minimum_minutes": company.first_order_minimum_minutes,
        "onsite_minimum_minutes": company.onsite_minimum_minutes,
        "remote_increment_minutes": company.remote_increment_minutes,
        "travel_minimum_minutes": company.travel_minimum_minutes,
        "travel_increment_minutes": company.travel_increment_minutes,
    }
    encoded = json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
    return f"{POLICY_SCHEMA}:{sha256(encoded).hexdigest()[:16]}"


def _configured_rate(company: CompanySettings, rate_type: str) -> Decimal:
    if rate_type == "private":
        return _decimal(company.private_hourly_rate)
    if rate_type == "business":
        return _decimal(company.business_hourly_rate)
    raise BillingPolicyError("Für den individuellen Tarif fehlt ein Stundensatz")


def _resolve_rate(
    *,
    client: Client,
    project: Project | None,
    company: CompanySettings,
    explicit_hourly_rate: Decimal | None,
) -> tuple[Decimal, str, str]:
    if explicit_hourly_rate is not None:
        return explicit_hourly_rate, "custom", "time_entry_override"

    if project is not None and project.hourly_rate is not None:
        rate_type = project.billing_rate_type_override or "custom"
        return _decimal(project.hourly_rate), rate_type, "project_rate_override"

    if project is not None and project.billing_rate_type_override is not None:
        rate_type = project.billing_rate_type_override
        return _configured_rate(company, rate_type), rate_type, "project_tariff_override"

    if project is not None and project.is_individual_project:
        return (
            _decimal(company.business_hourly_rate),
            "business",
            "individual_project",
        )

    rate_type = client.billing_rate_type
    if client.hourly_rate is not None:
        return _decimal(client.hourly_rate), rate_type, "client_standard_rate"
    return _configured_rate(company, rate_type), rate_type, "deployment_tariff"


def _resolve_service_mode(
    *,
    client: Client,
    project: Project | None,
    requested_service_mode: str | None,
) -> str:
    mode = (
        requested_service_mode
        or (project.default_service_mode if project is not None else None)
        or client.default_service_mode
        or "remote"
    )
    if mode not in {"remote", "onsite"}:
        raise BillingPolicyError("Unbekannter Leistungsmodus")
    return mode


def calculate_billing_decision(
    *,
    actual_minutes: int,
    travel_actual_minutes: int,
    is_first_order: bool,
    requested_service_mode: str | None,
    client: Client,
    project: Project | None,
    company: CompanySettings,
    explicit_hourly_rate: Decimal | None = None,
) -> BillingDecision:
    if actual_minutes < 0 or travel_actual_minutes < 0:
        raise BillingPolicyError("Minuten dürfen nicht negativ sein")
    if not client.billing_profile_confirmed:
        raise BillingPolicyError(
            "Das Tarifprofil des Kunden muss vor der Abrechnung bestätigt werden"
        )
    if project is not None and not project.billing_profile_confirmed:
        raise BillingPolicyError(
            "Das Tarifprofil des Projekts muss vor der Abrechnung bestätigt werden"
        )

    rate, rate_type, rate_source = _resolve_rate(
        client=client,
        project=project,
        company=company,
        explicit_hourly_rate=explicit_hourly_rate,
    )
    service_mode = _resolve_service_mode(
        client=client,
        project=project,
        requested_service_mode=requested_service_mode,
    )

    onsite_or_travel = service_mode == "onsite" or travel_actual_minutes > 0
    minimum_minutes = 0
    increment_minutes: int | None = None
    if is_first_order or onsite_or_travel:
        if is_first_order:
            minimum_minutes = max(
                minimum_minutes, company.first_order_minimum_minutes
            )
        if onsite_or_travel:
            minimum_minutes = max(minimum_minutes, company.onsite_minimum_minutes)
        billable_minutes = max(actual_minutes, minimum_minutes)
        if is_first_order and onsite_or_travel:
            billing_reason = "first_order_and_onsite_minimum"
        elif is_first_order:
            billing_reason = "first_order_minimum"
        else:
            billing_reason = "onsite_or_travel_minimum"
    else:
        increment_minutes = company.remote_increment_minutes
        billable_minutes = _ceil_to_increment(actual_minutes, increment_minutes)
        billing_reason = "remote_follow_up_increment"

    travel_minimum = company.travel_minimum_minutes
    travel_increment = company.travel_increment_minutes
    if travel_actual_minutes <= 0:
        travel_billable = 0
        travel_reason = None
    else:
        travel_billable = max(travel_actual_minutes, travel_minimum)
        if travel_increment is not None:
            travel_billable = _ceil_to_increment(travel_billable, travel_increment)
        if travel_actual_minutes < travel_minimum:
            travel_reason = "travel_minimum"
        elif travel_increment is not None and travel_billable != travel_actual_minutes:
            travel_reason = "travel_configured_increment"
        else:
            travel_reason = "travel_actual_minutes"

    return BillingDecision(
        actual_minutes=actual_minutes,
        billable_minutes=billable_minutes,
        hourly_rate=rate,
        rate_type=rate_type,
        rate_source=rate_source,
        minimum_minutes=minimum_minutes,
        increment_minutes=increment_minutes,
        service_mode=service_mode,
        is_first_order=is_first_order,
        billing_reason=billing_reason,
        billing_policy_id=billing_policy_id(company),
        travel_actual_minutes=travel_actual_minutes,
        travel_billable_minutes=travel_billable,
        travel_hourly_rate=_decimal(company.travel_hourly_rate),
        travel_minimum_minutes=travel_minimum,
        travel_increment_minutes=travel_increment,
        travel_billing_reason=travel_reason,
    )


def recalculate_billable_minutes(
    *, actual_minutes: int, minimum_minutes: int, increment_minutes: int | None
) -> int:
    minutes = max(actual_minutes, minimum_minutes)
    if increment_minutes is not None:
        minutes = _ceil_to_increment(minutes, increment_minutes)
    return minutes


def apply_billing_decision(entry: TimeEntry, decision: BillingDecision) -> None:
    entry.hourly_rate = decision.hourly_rate
    entry.billable_minutes = decision.billable_minutes
    entry.billing_rate_type = decision.rate_type
    entry.billing_rate_source = decision.rate_source
    entry.applied_minimum_minutes = decision.minimum_minutes
    entry.applied_increment_minutes = decision.increment_minutes
    entry.service_mode = decision.service_mode
    entry.is_first_order = decision.is_first_order
    entry.billing_reason = decision.billing_reason
    entry.billing_policy_id = decision.billing_policy_id
    entry.billing_policy_applied = True
    entry.travel_actual_minutes = decision.travel_actual_minutes
    entry.travel_billable_minutes = decision.travel_billable_minutes
    entry.travel_hourly_rate = decision.travel_hourly_rate
    entry.travel_minimum_minutes = decision.travel_minimum_minutes
    entry.travel_increment_minutes = decision.travel_increment_minutes
    entry.travel_billing_reason = decision.travel_billing_reason


def stored_billing_decision(entry: TimeEntry) -> BillingDecision:
    required = {
        "billable_minutes": entry.billable_minutes,
        "billing_rate_type": entry.billing_rate_type,
        "billing_rate_source": entry.billing_rate_source,
        "applied_minimum_minutes": entry.applied_minimum_minutes,
        "service_mode": entry.service_mode,
        "billing_reason": entry.billing_reason,
        "billing_policy_id": entry.billing_policy_id,
        "travel_billable_minutes": entry.travel_billable_minutes,
        "travel_hourly_rate": entry.travel_hourly_rate,
        "travel_minimum_minutes": entry.travel_minimum_minutes,
    }
    if not entry.billing_policy_applied or any(value is None for value in required.values()):
        raise BillingPolicyError("Der Zeiteintrag besitzt noch keine bestätigte Billing-Policy")
    return BillingDecision(
        actual_minutes=entry.duration_minutes,
        billable_minutes=entry.billable_minutes,
        hourly_rate=_decimal(entry.hourly_rate),
        rate_type=entry.billing_rate_type,
        rate_source=entry.billing_rate_source,
        minimum_minutes=entry.applied_minimum_minutes,
        increment_minutes=entry.applied_increment_minutes,
        service_mode=entry.service_mode,
        is_first_order=entry.is_first_order,
        billing_reason=entry.billing_reason,
        billing_policy_id=entry.billing_policy_id,
        travel_actual_minutes=entry.travel_actual_minutes,
        travel_billable_minutes=entry.travel_billable_minutes,
        travel_hourly_rate=_decimal(entry.travel_hourly_rate),
        travel_minimum_minutes=entry.travel_minimum_minutes,
        travel_increment_minutes=entry.travel_increment_minutes,
        travel_billing_reason=entry.travel_billing_reason,
    )

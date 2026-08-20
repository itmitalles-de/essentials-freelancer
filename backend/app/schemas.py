import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import (
    AssistantDraftStatus,
    BillingRateType,
    CatalogItemKind,
    InvoiceStatus,
    QuoteStatus,
    ServiceMode,
)


# ---- Auth ----
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    username: str


# ---- Company settings ----
class CompanySettingsBase(BaseModel):
    company_name: str = ""
    owner_name: str = ""
    address_line1: str = ""
    address_line2: str = ""
    zip_city: str = ""
    email: str = ""
    phone: str = ""
    tax_id: str = ""
    iban: str = ""
    bic: str = ""
    bank_name: str = ""
    invoice_footer_note: str = ""
    invoice_number_prefix: str = "RE"
    quote_number_prefix: str = "AN"
    default_hourly_rate: Decimal = Field(default=Decimal("0"), ge=0)
    default_payment_terms_days: int = Field(default=14, ge=0)
    private_hourly_rate: Decimal = Field(
        default=Decimal("50.00"), ge=0, max_digits=10, decimal_places=2
    )
    business_hourly_rate: Decimal = Field(
        default=Decimal("75.00"), ge=0, max_digits=10, decimal_places=2
    )
    travel_hourly_rate: Decimal = Field(
        default=Decimal("30.00"), ge=0, max_digits=10, decimal_places=2
    )
    first_order_minimum_minutes: int = Field(default=60, ge=0)
    onsite_minimum_minutes: int = Field(default=60, ge=0)
    remote_increment_minutes: int = Field(default=15, gt=0)
    travel_minimum_minutes: int = Field(default=30, ge=0)
    travel_increment_minutes: int | None = Field(default=None, gt=0)
    default_tax_rate: Decimal = Field(
        default=Decimal("0.00"), ge=0, le=100, max_digits=5, decimal_places=2
    )
    small_business_notice_enabled: bool = False
    small_business_notice_text: str = ""

    @model_validator(mode="after")
    def validate_small_business_profile(self):
        if self.small_business_notice_enabled:
            if self.default_tax_rate != Decimal("0"):
                raise ValueError(
                    "Das Kleinunternehmerprofil erfordert einen Steuersatz von 0 Prozent"
                )
            if not self.small_business_notice_text.strip():
                raise ValueError(
                    "Der §-19-Hinweis muss ausdrücklich eingetragen und bestätigt werden"
                )
        return self


class CompanySettingsOut(CompanySettingsBase):
    model_config = ConfigDict(from_attributes=True)
    next_invoice_number: int
    next_quote_number: int
    has_logo: bool = False

    @classmethod
    def from_model(cls, company) -> "CompanySettingsOut":
        out = cls.model_validate(company)
        out.has_logo = bool(company.logo_path)
        return out


class CompanySettingsUpdate(CompanySettingsBase):
    pass


# ---- Clients ----
class ClientBase(BaseModel):
    name: str
    contact_person: str = ""
    address_line1: str = ""
    address_line2: str = ""
    zip_city: str = ""
    email: str = ""
    hourly_rate: Decimal | None = Field(
        default=None, ge=0, max_digits=10, decimal_places=2
    )
    billing_rate_type: BillingRateType = BillingRateType.private
    default_service_mode: ServiceMode | None = None
    billing_profile_confirmed: bool = True
    notes: str = ""
    active: bool = True

    @model_validator(mode="after")
    def validate_custom_rate(self):
        if (
            self.billing_profile_confirmed
            and self.billing_rate_type == BillingRateType.custom
            and self.hourly_rate is None
        ):
            raise ValueError("Für einen individuellen Kundentarif ist ein Stundensatz nötig")
        return self


class ClientCreate(ClientBase):
    pass


class ClientOut(ClientBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: dt.datetime


# ---- Projects ----
class ProjectBase(BaseModel):
    client_id: int
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    hourly_rate: Decimal | None = Field(
        default=None, ge=0, max_digits=10, decimal_places=2
    )
    billing_rate_type_override: BillingRateType | None = None
    default_service_mode: ServiceMode = ServiceMode.remote
    is_individual_project: bool = False
    billing_profile_confirmed: bool = True
    active: bool = True

    @model_validator(mode="after")
    def validate_custom_override(self):
        if (
            self.billing_profile_confirmed
            and self.billing_rate_type_override == BillingRateType.custom
            and self.hourly_rate is None
        ):
            raise ValueError("Für den individuellen Projekt-Override ist ein Stundensatz nötig")
        return self


class ProjectCreate(ProjectBase):
    pass


class ProjectOut(ProjectBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: dt.datetime


# ---- Time entries ----
class TimeEntryBase(BaseModel):
    client_id: int
    project_id: int | None = None
    date: dt.date
    description: str = ""
    duration_minutes: int = Field(ge=0)
    hourly_rate: Decimal | None = Field(
        default=None, ge=0, max_digits=10, decimal_places=2
    )
    service_mode: ServiceMode | None = None
    is_first_order: bool = False
    travel_actual_minutes: int = Field(default=0, ge=0)


class TimeEntryCreate(TimeEntryBase):
    pass


class TimeEntryUpdate(BaseModel):
    project_id: int | None = None
    date: dt.date | None = None
    description: str | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    hourly_rate: Decimal | None = Field(
        default=None, ge=0, max_digits=10, decimal_places=2
    )
    service_mode: ServiceMode | None = None
    is_first_order: bool | None = None
    travel_actual_minutes: int | None = Field(default=None, ge=0)


class TimeEntryStart(BaseModel):
    client_id: int
    project_id: int | None = None
    description: str = ""
    service_mode: ServiceMode | None = None
    is_first_order: bool = False
    travel_actual_minutes: int = Field(default=0, ge=0)


class TimeEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    client_id: int
    project_id: int | None
    date: dt.date
    description: str
    duration_minutes: int
    actual_minutes: int
    hourly_rate: Decimal
    billable_minutes: int | None
    billing_rate_type: str | None
    billing_rate_source: str | None
    applied_minimum_minutes: int | None
    applied_increment_minutes: int | None
    service_mode: str | None
    is_first_order: bool
    billing_reason: str | None
    billing_policy_id: str | None
    billing_policy_applied: bool
    travel_actual_minutes: int
    travel_billable_minutes: int | None
    travel_hourly_rate: Decimal | None
    travel_minimum_minutes: int | None
    travel_increment_minutes: int | None
    travel_billing_reason: str | None
    running_started_at: dt.datetime | None
    billed: bool
    invoice_id: int | None


# ---- Invoices ----
class InvoiceLineItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    net_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    amount: Decimal
    unit: str
    project_id: int | None
    snapshot_line_kind: str | None
    snapshot_actual_minutes: int | None
    snapshot_billable_minutes: int | None
    snapshot_hourly_rate: Decimal | None
    snapshot_rate_type: str | None
    snapshot_minimum_minutes: int | None
    snapshot_increment_minutes: int | None
    snapshot_service_mode: str | None
    snapshot_is_first_order: bool | None
    snapshot_billing_reason: str | None
    snapshot_billing_policy_id: str | None
    snapshot_service_date: dt.date | None
    snapshot_project_name: str | None


class InvoicePreviewRequest(BaseModel):
    client_id: int
    time_entry_ids: list[int] = Field(min_length=1)
    tax_rate: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    notes: str = ""
    due_in_days: int | None = Field(default=None, ge=0)

    @field_validator("time_entry_ids")
    @classmethod
    def time_entries_must_be_unique(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Zeiteinträge dürfen nicht doppelt ausgewählt werden")
        return value


class InvoiceCreate(InvoicePreviewRequest):
    billing_confirmation_token: str = Field(min_length=20, max_length=80)
    billing_confirmed: bool

    @model_validator(mode="after")
    def require_billing_confirmation(self):
        if not self.billing_confirmed:
            raise ValueError("Die angezeigte Abrechnung muss bestätigt werden")
        return self


class BillingPreviewLineOut(BaseModel):
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
    service_date: dt.date
    project_id: int | None
    project_name: str | None
    net_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal


class InvoicePreviewOut(BaseModel):
    client_id: int
    lines: list[BillingPreviewLineOut]
    work_total: Decimal
    travel_total: Decimal
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    tax_rate: Decimal
    tax_status: str
    tax_notice: str | None
    confirmation_token: str


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    client_id: int
    invoice_number: str
    issue_date: dt.date
    due_date: dt.date
    status: InvoiceStatus
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    notes: str
    sent_at: dt.datetime | None
    paid_at: dt.datetime | None
    created_at: dt.datetime
    quote_id: int | None
    tax_status_snapshot: str | None
    tax_notice_snapshot: str | None
    footer_note_snapshot: str | None
    billing_confirmation_token: str | None
    line_items: list[InvoiceLineItemOut] = []


class InvoiceStatusUpdate(BaseModel):
    status: InvoiceStatus
    pdf_reviewed: bool = False
    manual_delivery_confirmed: bool = False


class InvoiceSendRequest(BaseModel):
    recipient: str = Field(min_length=3, max_length=255)
    invoice_number: str = Field(min_length=1, max_length=64)
    total: Decimal = Field(ge=0)
    pdf_reviewed: bool
    resend: bool = False


class InvoiceSendAttemptOut(BaseModel):
    id: int
    recipient: str
    is_resend: bool
    outcome: str
    message_id_redacted: str | None
    failure_code: str | None
    created_at: dt.datetime
    completed_at: dt.datetime | None


# ---- Quotes ----
class QuoteLineItemCreate(BaseModel):
    description: str = Field(min_length=1)
    quantity: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    unit: str = Field(default="hours", min_length=1, max_length=32)
    unit_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    tax_rate: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)


class QuoteLineItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    description: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    tax_rate: Decimal
    net_amount: Decimal
    tax_amount: Decimal
    amount: Decimal


class QuoteCreate(BaseModel):
    client_id: int
    project_id: int | None = None
    valid_in_days: int = Field(default=14, ge=0)
    notes: str = ""
    line_items: list[QuoteLineItemCreate] = Field(min_length=1)


class QuoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    client_id: int
    project_id: int | None
    quote_number: str
    issue_date: dt.date
    valid_until: dt.date
    status: QuoteStatus
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    notes: str
    converted_invoice_id: int | None
    created_at: dt.datetime
    line_items: list[QuoteLineItemOut] = []


class QuoteStatusUpdate(BaseModel):
    status: QuoteStatus


class QuoteInvoicePreviewRequest(BaseModel):
    service_date: dt.date


class QuoteInvoiceConversion(QuoteInvoicePreviewRequest):
    billing_confirmation_token: str = Field(min_length=20, max_length=80)
    billing_confirmed: bool

    @model_validator(mode="after")
    def require_billing_confirmation(self):
        if not self.billing_confirmed:
            raise ValueError("Die angezeigte Abrechnung muss bestätigt werden")
        return self


class QuoteInvoicePreviewLineOut(BaseModel):
    quote_line_item_id: int
    description: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    actual_minutes: int | None
    billable_minutes: int | None
    rate_type: str
    minimum_minutes: int | None
    increment_minutes: int | None
    service_mode: str | None
    billing_reason: str
    service_date: dt.date
    project_id: int | None
    project_name: str | None
    net_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total_amount: Decimal


class QuoteInvoicePreviewOut(BaseModel):
    quote_id: int
    lines: list[QuoteInvoicePreviewLineOut]
    work_total: Decimal
    travel_total: Decimal
    fixed_total: Decimal
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    tax_status: str
    tax_notice: str | None
    service_date: dt.date
    due_date: dt.date
    confirmation_token: str


# ---- Expenses ----
class ExpenseBase(BaseModel):
    date: dt.date
    description: str
    category: str = ""
    amount: Decimal = Field(ge=0)


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseOut(ExpenseBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: dt.datetime
    has_receipt: bool = False

    @classmethod
    def from_model(cls, expense) -> "ExpenseOut":
        out = cls.model_validate(expense)
        out.has_receipt = bool(expense.receipt_path)
        return out


# ---- Deterministic quote assistant ----
class CatalogVersionCreate(BaseModel):
    description: str = Field(min_length=1)
    unit: str = Field(min_length=1, max_length=32)
    net_unit_price: Decimal = Field(ge=0)
    tax_rate: Decimal = Field(ge=0, le=100)
    valid_from: dt.date
    valid_until: dt.date | None = None

    @model_validator(mode="after")
    def validity_order(self):
        if self.valid_until is not None and self.valid_until < self.valid_from:
            raise ValueError("Gültig-bis darf nicht vor Gültig-ab liegen")
        return self


class CatalogItemCreate(BaseModel):
    stable_key: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{1,127}$")
    kind: CatalogItemKind
    name: str = Field(min_length=1, max_length=255)
    version: CatalogVersionCreate


class CatalogVersionOut(CatalogVersionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    item_id: int
    version: int
    created_at: dt.datetime


class CatalogItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    stable_key: str
    kind: CatalogItemKind
    name: str
    active: bool
    created_at: dt.datetime
    versions: list[CatalogVersionOut]


class PackageEntryCreate(BaseModel):
    catalog_version_id: int
    quantity: Decimal = Field(gt=0)


class PackageVersionCreate(BaseModel):
    description: str = Field(min_length=1)
    valid_from: dt.date
    valid_until: dt.date | None = None
    items: list[PackageEntryCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validity_order(self):
        if self.valid_until is not None and self.valid_until < self.valid_from:
            raise ValueError("Gültig-bis darf nicht vor Gültig-ab liegen")
        return self


class PackageCreate(BaseModel):
    stable_key: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{1,127}$")
    name: str = Field(min_length=1, max_length=255)
    version: PackageVersionCreate


class PackageItemOut(BaseModel):
    catalog_version_id: int
    quantity: Decimal
    sort_order: int


class PackageVersionOut(BaseModel):
    id: int
    package_id: int
    version: int
    description: str
    valid_from: dt.date
    valid_until: dt.date | None
    items: list[PackageItemOut]
    created_at: dt.datetime


class PackageOut(BaseModel):
    id: int
    stable_key: str
    name: str
    active: bool
    versions: list[PackageVersionOut]
    created_at: dt.datetime


class AssistantSelection(BaseModel):
    catalog_version_id: int | None = None
    package_version_id: int | None = None
    quantity: Decimal = Field(gt=0)

    @model_validator(mode="after")
    def exactly_one_source(self):
        if (self.catalog_version_id is None) == (self.package_version_id is None):
            raise ValueError("Genau eine Katalog- oder Paketversion ist erforderlich")
        return self


class TemplateVersionCreate(BaseModel):
    description: str = Field(min_length=1)
    questions: list[str] = Field(default_factory=list, max_length=10)
    selections: list[AssistantSelection] = Field(min_length=1)
    surcharge_percent: Decimal = Field(default=Decimal("0"), ge=0)
    discount_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)


class TemplateCreate(BaseModel):
    stable_key: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{1,127}$")
    name: str = Field(min_length=1, max_length=255)
    version: TemplateVersionCreate


class TemplateVersionOut(BaseModel):
    id: int
    template_id: int
    version: int
    description: str
    questions: list[str]
    selections: list[AssistantSelection]
    surcharge_percent: Decimal
    discount_percent: Decimal
    created_at: dt.datetime


class TemplateOut(BaseModel):
    id: int
    stable_key: str
    name: str
    active: bool
    versions: list[TemplateVersionOut]
    created_at: dt.datetime


class AssistantPreviewRequest(BaseModel):
    pricing_date: dt.date = Field(default_factory=dt.date.today)
    selections: list[AssistantSelection] = Field(min_length=1)
    surcharge_percent: Decimal = Field(default=Decimal("0"), ge=0)
    discount_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)


class AssistantLineOut(BaseModel):
    catalog_version_id: int
    package_version_id: int | None
    description: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    tax_rate: Decimal
    net_amount: Decimal
    tax_amount: Decimal
    amount: Decimal
    sort_order: int


class TaxBreakdownOut(BaseModel):
    tax_rate: Decimal
    base_net: Decimal
    surcharge: Decimal
    discount: Decimal
    taxable_net: Decimal
    tax_amount: Decimal
    gross: Decimal


class CalculationStepOut(BaseModel):
    key: str
    label: str
    expression: str
    amount: Decimal


class AssistantPreviewOut(BaseModel):
    pricing_date: dt.date
    lines: list[AssistantLineOut]
    tax_breakdown: list[TaxBreakdownOut]
    calculation_steps: list[CalculationStepOut]
    base_net_total: Decimal
    surcharge_percent: Decimal
    surcharge_amount: Decimal
    discount_percent: Decimal
    discount_amount: Decimal
    net_total: Decimal
    tax_total: Decimal
    total: Decimal


class AssistantDraftCreate(AssistantPreviewRequest):
    client_id: int
    project_id: int | None = None
    template_version_id: int | None = None
    title: str = Field(min_length=1, max_length=255)
    guided_answers: dict[str, str] = Field(default_factory=dict)
    notes: str = ""


class AssistantDraftOut(AssistantPreviewOut):
    id: int
    client_id: int
    project_id: int | None
    template_version_id: int | None
    quote_id: int | None
    title: str
    status: AssistantDraftStatus
    guided_answers: dict[str, str]
    notes: str
    approved_at: dt.datetime | None
    transferred_at: dt.datetime | None
    created_at: dt.datetime
    updated_at: dt.datetime


# ---- Operational reporting ----
class TimeReportGroup(BaseModel):
    client_id: int
    project_id: int | None
    captured_hours: Decimal
    unbilled_hours: Decimal


class TimeReport(BaseModel):
    captured_hours: Decimal
    unbilled_hours: Decimal
    groups: list[TimeReportGroup]


class QuoteReport(BaseModel):
    statuses: dict[str, int]
    conversion_rate_percent: Decimal


class InvoiceReport(BaseModel):
    statuses: dict[str, int]
    open_amount: Decimal
    paid_amount: Decimal


class ExpenseCategoryReport(BaseModel):
    category: str
    amount: Decimal


class ExpenseReport(BaseModel):
    total: Decimal
    categories: list[ExpenseCategoryReport]


class ReportSummary(BaseModel):
    date_from: dt.date | None
    date_to: dt.date | None
    client_id: int | None
    project_id: int | None
    time: TimeReport
    quotes: QuoteReport
    invoices: InvoiceReport
    expenses: ExpenseReport

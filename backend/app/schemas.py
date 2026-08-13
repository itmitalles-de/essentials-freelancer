import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import (
    AssistantDraftStatus,
    CatalogItemKind,
    InvoiceStatus,
    QuoteStatus,
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
    hourly_rate: Decimal | None = Field(default=None, ge=0)
    notes: str = ""
    active: bool = True


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
    hourly_rate: Decimal | None = Field(default=None, ge=0)
    active: bool = True


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
    hourly_rate: Decimal | None = Field(default=None, ge=0)


class TimeEntryCreate(TimeEntryBase):
    pass


class TimeEntryUpdate(BaseModel):
    project_id: int | None = None
    date: dt.date | None = None
    description: str | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    hourly_rate: Decimal | None = Field(default=None, ge=0)


class TimeEntryStart(BaseModel):
    client_id: int
    project_id: int | None = None
    description: str = ""


class TimeEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    client_id: int
    project_id: int | None
    date: dt.date
    description: str
    duration_minutes: int
    hourly_rate: Decimal
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


class InvoiceCreate(BaseModel):
    client_id: int
    time_entry_ids: list[int] = Field(min_length=1)
    notes: str = ""
    due_in_days: int | None = Field(default=None, ge=0)

    @field_validator("time_entry_ids")
    @classmethod
    def time_entries_must_be_unique(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Zeiteinträge dürfen nicht doppelt ausgewählt werden")
        return value


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
    line_items: list[InvoiceLineItemOut] = []


class InvoiceStatusUpdate(BaseModel):
    status: InvoiceStatus


# ---- Quotes ----
class QuoteLineItemCreate(BaseModel):
    description: str = Field(min_length=1)
    quantity: Decimal = Field(gt=0)
    unit: str = Field(default="hours", min_length=1, max_length=32)
    unit_price: Decimal = Field(ge=0)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100)


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

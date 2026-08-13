import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import InvoiceStatus, QuoteStatus


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


class QuoteLineItemOut(QuoteLineItemCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
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

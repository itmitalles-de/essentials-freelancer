import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import InvoiceStatus


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
    default_hourly_rate: Decimal = Field(default=Decimal("0"), ge=0)
    default_payment_terms_days: int = Field(default=14, ge=0)


class CompanySettingsOut(CompanySettingsBase):
    model_config = ConfigDict(from_attributes=True)
    next_invoice_number: int
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


# ---- Time entries ----
class TimeEntryBase(BaseModel):
    client_id: int
    date: dt.date
    description: str = ""
    duration_minutes: int = Field(ge=0)
    hourly_rate: Decimal | None = Field(default=None, ge=0)


class TimeEntryCreate(TimeEntryBase):
    pass


class TimeEntryUpdate(BaseModel):
    date: dt.date | None = None
    description: str | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    hourly_rate: Decimal | None = Field(default=None, ge=0)


class TimeEntryStart(BaseModel):
    client_id: int
    description: str = ""


class TimeEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    client_id: int
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


class InvoiceCreate(BaseModel):
    client_id: int
    time_entry_ids: list[int]
    notes: str = ""
    due_in_days: int | None = None


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
    line_items: list[InvoiceLineItemOut] = []


class InvoiceStatusUpdate(BaseModel):
    status: InvoiceStatus

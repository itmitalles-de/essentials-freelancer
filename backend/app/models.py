import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.time_utils import utc_now_naive


class InvoiceStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    paid = "paid"
    cancelled = "cancelled"


class QuoteStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    accepted = "accepted"
    rejected = "rejected"
    converted = "converted"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))


class CompanySettings(Base):
    __tablename__ = "company_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    company_name: Mapped[str] = mapped_column(String(255), default="")
    owner_name: Mapped[str] = mapped_column(String(255), default="")
    address_line1: Mapped[str] = mapped_column(String(255), default="")
    address_line2: Mapped[str] = mapped_column(String(255), default="")
    zip_city: Mapped[str] = mapped_column(String(255), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    tax_id: Mapped[str] = mapped_column(String(64), default="")
    iban: Mapped[str] = mapped_column(String(64), default="")
    bic: Mapped[str] = mapped_column(String(64), default="")
    bank_name: Mapped[str] = mapped_column(String(255), default="")
    invoice_footer_note: Mapped[str] = mapped_column(
        Text,
        default="Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.",
    )
    invoice_number_prefix: Mapped[str] = mapped_column(String(32), default="RE")
    next_invoice_number: Mapped[int] = mapped_column(Integer, default=1)
    quote_number_prefix: Mapped[str] = mapped_column(String(32), default="AN")
    next_quote_number: Mapped[int] = mapped_column(Integer, default=1)
    logo_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    default_hourly_rate: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    default_payment_terms_days: Mapped[int] = mapped_column(Integer, default=14)


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    contact_person: Mapped[str] = mapped_column(String(255), default="")
    address_line1: Mapped[str] = mapped_column(String(255), default="")
    address_line2: Mapped[str] = mapped_column(String(255), default="")
    zip_city: Mapped[str] = mapped_column(String(255), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    hourly_rate: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    time_entries: Mapped[list["TimeEntry"]] = relationship(back_populates="client")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="client")
    projects: Mapped[list["Project"]] = relationship(back_populates="client")
    quotes: Mapped[list["Quote"]] = relationship(back_populates="client")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    hourly_rate: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    client: Mapped["Client"] = relationship(back_populates="projects")
    time_entries: Mapped[list["TimeEntry"]] = relationship(back_populates="project")
    quotes: Mapped[list["Quote"]] = relationship(back_populates="project")

    __table_args__ = (
        UniqueConstraint("client_id", "name", name="uq_projects_client_name"),
    )


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True, index=True
    )
    date: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(Text, default="")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    hourly_rate: Mapped[float] = mapped_column(Numeric(10, 2))
    running_started_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    billed: Mapped[bool] = mapped_column(Boolean, default=False)
    invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey("invoices.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    client: Mapped["Client"] = relationship(back_populates="time_entries")
    project: Mapped["Project | None"] = relationship(back_populates="time_entries")
    invoice: Mapped["Invoice | None"] = relationship(back_populates="time_entries")

    __table_args__ = (
        Index(
            "ix_time_entries_single_running_timer",
            text("(1)"),
            unique=True,
            postgresql_where=text("running_started_at IS NOT NULL"),
            sqlite_where=text("running_started_at IS NOT NULL"),
        ),
    )


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    invoice_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    issue_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus), default=InvoiceStatus.draft
    )
    total: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    pdf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    quote_id: Mapped[int | None] = mapped_column(
        ForeignKey("quotes.id"), nullable=True, unique=True
    )

    client: Mapped["Client"] = relationship(back_populates="invoices")
    time_entries: Mapped[list["TimeEntry"]] = relationship(back_populates="invoice")
    line_items: Mapped[list["InvoiceLineItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"))
    description: Mapped[str] = mapped_column(Text)
    quantity: Mapped[float] = mapped_column(Numeric(10, 2))
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2))
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    unit: Mapped[str] = mapped_column(String(32), default="hours")
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True, index=True
    )

    invoice: Mapped["Invoice"] = relationship(back_populates="line_items")


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True, index=True
    )
    quote_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    issue_date: Mapped[date] = mapped_column(Date)
    valid_until: Mapped[date] = mapped_column(Date)
    status: Mapped[QuoteStatus] = mapped_column(
        Enum(QuoteStatus), default=QuoteStatus.draft
    )
    total: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    pdf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    converted_invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "invoices.id", use_alter=True, name="fk_quotes_converted_invoice_id"
        ),
        nullable=True,
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    client: Mapped["Client"] = relationship(back_populates="quotes")
    project: Mapped["Project | None"] = relationship(back_populates="quotes")
    line_items: Mapped[list["QuoteLineItem"]] = relationship(
        back_populates="quote", cascade="all, delete-orphan"
    )


class QuoteLineItem(Base):
    __tablename__ = "quote_line_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"), index=True)
    description: Mapped[str] = mapped_column(Text)
    quantity: Mapped[float] = mapped_column(Numeric(10, 2))
    unit: Mapped[str] = mapped_column(String(32), default="hours")
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2))
    amount: Mapped[float] = mapped_column(Numeric(10, 2))

    quote: Mapped["Quote"] = relationship(back_populates="line_items")


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64), default="")
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    receipt_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class ModuleInstallation(Base):
    __tablename__ = "module_installations"

    module_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    manifest_schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    configuration_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now_naive, onupdate=utc_now_naive
    )

    __table_args__ = (
        CheckConstraint(
            "state IN ('not_installed', 'needs_configuration', 'disabled', 'enabled', 'degraded')",
            name="ck_module_installations_state",
        ),
    )


class ModuleAuditEvent(Base):
    __tablename__ = "module_audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_id: Mapped[str] = mapped_column(
        ForeignKey("module_installations.module_id"), index=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_state: Mapped[str] = mapped_column(String(32), nullable=False)
    resulting_state: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

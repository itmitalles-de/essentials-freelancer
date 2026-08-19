import enum
from datetime import date, datetime
from decimal import Decimal

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


class CatalogItemKind(str, enum.Enum):
    service = "service"
    material = "material"
    travel = "travel"


class AssistantDraftStatus(str, enum.Enum):
    draft = "draft"
    approved = "approved"
    transferred = "transferred"


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
        default="",
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

    __table_args__ = (
        CheckConstraint(
            "hourly_rate IS NULL OR hourly_rate >= 0", name="ck_clients_hourly_rate"
        ),
    )


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
        CheckConstraint(
            "hourly_rate IS NULL OR hourly_rate >= 0", name="ck_projects_hourly_rate"
        ),
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
    start_request_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    start_request_fingerprint: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )

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
        Index(
            "ix_time_entries_reporting",
            "date",
            "client_id",
            "project_id",
            "billed",
        ),
        CheckConstraint("duration_minutes >= 0", name="ck_time_entries_duration"),
        CheckConstraint("hourly_rate >= 0", name="ck_time_entries_hourly_rate"),
        UniqueConstraint(
            "start_request_key", name="uq_time_entries_start_request_key"
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
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    tax_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    pdf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    quote_id: Mapped[int | None] = mapped_column(
        ForeignKey("quotes.id"), nullable=True, unique=True
    )
    request_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    request_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)

    client: Mapped["Client"] = relationship(back_populates="invoices")
    time_entries: Mapped[list["TimeEntry"]] = relationship(back_populates="invoice")
    line_items: Mapped[list["InvoiceLineItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )
    send_attempts: Mapped[list["InvoiceSendAttempt"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_invoices_reporting", "issue_date", "client_id", "status"),
        Index("ix_invoices_due_status", "due_date", "status"),
        CheckConstraint("due_date >= issue_date", name="ck_invoices_date_order"),
        CheckConstraint(
            "subtotal >= 0 AND tax_total >= 0 AND total >= 0",
            name="ck_invoices_totals",
        ),
        UniqueConstraint("request_key", name="uq_invoices_request_key"),
    )


class InvoiceSendAttempt(Base):
    __tablename__ = "invoice_send_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    is_resend: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    invoice: Mapped["Invoice"] = relationship(back_populates="send_attempts")

    __table_args__ = (
        CheckConstraint(
            "outcome IN ('pending', 'sent', 'failed')",
            name="ck_invoice_send_attempts_outcome",
        ),
        Index("ix_invoice_send_attempts_invoice_created", "invoice_id", "created_at"),
    )


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"))
    description: Mapped[str] = mapped_column(Text)
    quantity: Mapped[float] = mapped_column(Numeric(10, 2))
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
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
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    tax_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
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

    __table_args__ = (
        Index("ix_quotes_reporting", "issue_date", "client_id", "project_id", "status"),
        CheckConstraint("valid_until >= issue_date", name="ck_quotes_date_order"),
        CheckConstraint(
            "subtotal >= 0 AND tax_total >= 0 AND total >= 0",
            name="ck_quotes_totals",
        ),
    )


class QuoteLineItem(Base):
    __tablename__ = "quote_line_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"), index=True)
    description: Mapped[str] = mapped_column(Text)
    quantity: Mapped[float] = mapped_column(Numeric(10, 2))
    unit: Mapped[str] = mapped_column(String(32), default="hours")
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

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

    __table_args__ = (
        Index("ix_expenses_reporting", "date", "category"),
        CheckConstraint("amount >= 0", name="ck_expenses_amount"),
    )


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


class QuoteCatalogItem(Base):
    __tablename__ = "quote_catalog_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stable_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    kind: Mapped[CatalogItemKind] = mapped_column(Enum(CatalogItemKind), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    versions: Mapped[list["QuoteCatalogVersion"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )


class QuoteCatalogVersion(Base):
    __tablename__ = "quote_catalog_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("quote_catalog_items.id"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    net_unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    item: Mapped["QuoteCatalogItem"] = relationship(back_populates="versions")

    __table_args__ = (
        UniqueConstraint("item_id", "version", name="uq_quote_catalog_item_version"),
        CheckConstraint("tax_rate >= 0 AND tax_rate <= 100", name="ck_catalog_tax_rate"),
        CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="ck_catalog_validity",
        ),
    )


class QuotePackage(Base):
    __tablename__ = "quote_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stable_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    versions: Mapped[list["QuotePackageVersion"]] = relationship(
        back_populates="package", cascade="all, delete-orphan"
    )


class QuotePackageVersion(Base):
    __tablename__ = "quote_package_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    package_id: Mapped[int] = mapped_column(
        ForeignKey("quote_packages.id"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    package: Mapped["QuotePackage"] = relationship(back_populates="versions")
    items: Mapped[list["QuotePackageVersionItem"]] = relationship(
        back_populates="package_version", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("package_id", "version", name="uq_quote_package_version"),
        CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="ck_package_validity",
        ),
    )


class QuotePackageVersionItem(Base):
    __tablename__ = "quote_package_version_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    package_version_id: Mapped[int] = mapped_column(
        ForeignKey("quote_package_versions.id"), nullable=False, index=True
    )
    catalog_version_id: Mapped[int] = mapped_column(
        ForeignKey("quote_catalog_versions.id"), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    package_version: Mapped["QuotePackageVersion"] = relationship(back_populates="items")
    catalog_version: Mapped["QuoteCatalogVersion"] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "package_version_id",
            "catalog_version_id",
            "sort_order",
            name="uq_quote_package_version_item_order",
        ),
        CheckConstraint("quantity > 0", name="ck_package_item_quantity"),
    )


class QuoteAssistantTemplate(Base):
    __tablename__ = "quote_assistant_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stable_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    versions: Mapped[list["QuoteAssistantTemplateVersion"]] = relationship(
        back_populates="template", cascade="all, delete-orphan"
    )


class QuoteAssistantTemplateVersion(Base):
    __tablename__ = "quote_assistant_template_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("quote_assistant_templates.id"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    questions_json: Mapped[str] = mapped_column(Text, default="[]")
    surcharge_percent: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=0)
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    template: Mapped["QuoteAssistantTemplate"] = relationship(back_populates="versions")
    selections: Mapped[list["QuoteAssistantTemplateSelection"]] = relationship(
        back_populates="template_version", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "template_id", "version", name="uq_quote_assistant_template_version"
        ),
        CheckConstraint("surcharge_percent >= 0", name="ck_template_surcharge"),
        CheckConstraint(
            "discount_percent >= 0 AND discount_percent <= 100",
            name="ck_template_discount",
        ),
    )


class QuoteAssistantTemplateSelection(Base):
    __tablename__ = "quote_assistant_template_selections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_version_id: Mapped[int] = mapped_column(
        ForeignKey("quote_assistant_template_versions.id"), nullable=False, index=True
    )
    catalog_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("quote_catalog_versions.id"), nullable=True
    )
    package_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("quote_package_versions.id"), nullable=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    template_version: Mapped["QuoteAssistantTemplateVersion"] = relationship(
        back_populates="selections"
    )
    catalog_version: Mapped["QuoteCatalogVersion | None"] = relationship()
    package_version: Mapped["QuotePackageVersion | None"] = relationship()

    __table_args__ = (
        CheckConstraint(
            "(catalog_version_id IS NOT NULL AND package_version_id IS NULL) OR "
            "(catalog_version_id IS NULL AND package_version_id IS NOT NULL)",
            name="ck_template_selection_source",
        ),
        CheckConstraint("quantity > 0", name="ck_template_selection_quantity"),
    )


class QuoteAssistantDraft(Base):
    __tablename__ = "quote_assistant_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True, index=True
    )
    template_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("quote_assistant_template_versions.id"), nullable=True
    )
    quote_id: Mapped[int | None] = mapped_column(
        ForeignKey("quotes.id"), nullable=True, unique=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[AssistantDraftStatus] = mapped_column(
        Enum(AssistantDraftStatus), default=AssistantDraftStatus.draft
    )
    pricing_date: Mapped[date] = mapped_column(Date, nullable=False)
    guided_answers_json: Mapped[str] = mapped_column(Text, default="{}")
    notes: Mapped[str] = mapped_column(Text, default="")
    surcharge_percent: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=0)
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    base_net_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    surcharge_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    net_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    tax_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    transferred_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now_naive, onupdate=utc_now_naive
    )

    lines: Mapped[list["QuoteAssistantDraftLine"]] = relationship(
        back_populates="draft", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("surcharge_percent >= 0", name="ck_assistant_surcharge"),
        CheckConstraint(
            "discount_percent >= 0 AND discount_percent <= 100",
            name="ck_assistant_discount",
        ),
    )


class QuoteAssistantDraftLine(Base):
    __tablename__ = "quote_assistant_draft_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    draft_id: Mapped[int] = mapped_column(
        ForeignKey("quote_assistant_drafts.id"), nullable=False, index=True
    )
    catalog_version_id: Mapped[int] = mapped_column(
        ForeignKey("quote_catalog_versions.id"), nullable=False
    )
    package_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("quote_package_versions.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    draft: Mapped["QuoteAssistantDraft"] = relationship(back_populates="lines")

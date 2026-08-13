"""Create or baseline the existing single-user MVP schema."""

from alembic import op
import sqlalchemy as sa

revision = "0001_existing_mvp"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    legacy_tables = {
        "users",
        "company_settings",
        "clients",
        "time_entries",
        "invoices",
        "invoice_line_items",
        "expenses",
    }
    existing = set(inspector.get_table_names())
    if "users" in existing:
        missing = sorted(legacy_tables - existing)
        if missing:
            raise RuntimeError(
                "Legacy schema is incomplete; refusing to baseline missing tables: "
                + ", ".join(missing)
            )
        return

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_table(
        "company_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("owner_name", sa.String(255), nullable=False),
        sa.Column("address_line1", sa.String(255), nullable=False),
        sa.Column("address_line2", sa.String(255), nullable=False),
        sa.Column("zip_city", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(64), nullable=False),
        sa.Column("tax_id", sa.String(64), nullable=False),
        sa.Column("iban", sa.String(64), nullable=False),
        sa.Column("bic", sa.String(64), nullable=False),
        sa.Column("bank_name", sa.String(255), nullable=False),
        sa.Column("invoice_footer_note", sa.Text(), nullable=False),
        sa.Column("invoice_number_prefix", sa.String(32), nullable=False),
        sa.Column("next_invoice_number", sa.Integer(), nullable=False),
        sa.Column("logo_path", sa.String(512), nullable=True),
        sa.Column("default_hourly_rate", sa.Numeric(10, 2), nullable=False),
        sa.Column("default_payment_terms_days", sa.Integer(), nullable=False),
    )
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("contact_person", sa.String(255), nullable=False),
        sa.Column("address_line1", sa.String(255), nullable=False),
        sa.Column("address_line2", sa.String(255), nullable=False),
        sa.Column("zip_city", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hourly_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    invoice_status = sa.Enum(
        "draft", "sent", "paid", "cancelled", name="invoicestatus"
    )
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("invoice_number", sa.String(64), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", invoice_status, nullable=False),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("pdf_path", sa.String(512), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("invoice_number"),
    )
    op.create_index(
        "ix_invoices_invoice_number", "invoices", ["invoice_number"], unique=True
    )
    op.create_table(
        "invoice_line_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
    )
    op.create_table(
        "time_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("hourly_rate", sa.Numeric(10, 2), nullable=False),
        sa.Column("running_started_at", sa.DateTime(), nullable=True),
        sa.Column("billed", sa.Boolean(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_time_entries_single_running_timer",
        "time_entries",
        [sa.text("(1)")],
        unique=True,
        postgresql_where=sa.text("running_started_at IS NOT NULL"),
        sqlite_where=sa.text("running_started_at IS NOT NULL"),
    )
    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("receipt_path", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    raise RuntimeError(
        "Refusing to downgrade the legacy baseline because it could delete "
        "pre-Alembic business data; restore a verified export instead"
    )

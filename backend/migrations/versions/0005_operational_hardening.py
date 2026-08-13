"""Add command idempotency, reporting indexes, and business invariants."""

from alembic import op
import sqlalchemy as sa

revision = "0005_operational_hardening"
down_revision = "0004_quote_assistant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("time_entries", sa.Column("start_request_key", sa.String(128), nullable=True))
    op.add_column(
        "time_entries",
        sa.Column("start_request_fingerprint", sa.String(64), nullable=True),
    )
    op.create_unique_constraint(
        "uq_time_entries_start_request_key", "time_entries", ["start_request_key"]
    )
    op.add_column("invoices", sa.Column("request_key", sa.String(128), nullable=True))
    op.add_column(
        "invoices", sa.Column("request_fingerprint", sa.String(64), nullable=True)
    )
    op.create_unique_constraint("uq_invoices_request_key", "invoices", ["request_key"])

    op.create_index(
        "ix_time_entries_reporting",
        "time_entries",
        ["date", "client_id", "project_id", "billed"],
    )
    op.create_index(
        "ix_invoices_reporting", "invoices", ["issue_date", "client_id", "status"]
    )
    op.create_index(
        "ix_invoices_due_status", "invoices", ["due_date", "status"]
    )
    op.create_index(
        "ix_quotes_reporting",
        "quotes",
        ["issue_date", "client_id", "project_id", "status"],
    )
    op.create_index("ix_expenses_reporting", "expenses", ["date", "category"])

    op.create_check_constraint(
        "ck_clients_hourly_rate", "clients", "hourly_rate IS NULL OR hourly_rate >= 0"
    )
    op.create_check_constraint(
        "ck_projects_hourly_rate",
        "projects",
        "hourly_rate IS NULL OR hourly_rate >= 0",
    )
    op.create_check_constraint(
        "ck_time_entries_duration", "time_entries", "duration_minutes >= 0"
    )
    op.create_check_constraint(
        "ck_time_entries_hourly_rate", "time_entries", "hourly_rate >= 0"
    )
    op.create_check_constraint(
        "ck_invoices_date_order", "invoices", "due_date >= issue_date"
    )
    op.create_check_constraint(
        "ck_invoices_totals",
        "invoices",
        "subtotal >= 0 AND tax_total >= 0 AND total >= 0",
    )
    op.create_check_constraint(
        "ck_quotes_date_order", "quotes", "valid_until >= issue_date"
    )
    op.create_check_constraint(
        "ck_quotes_totals",
        "quotes",
        "subtotal >= 0 AND tax_total >= 0 AND total >= 0",
    )
    op.create_check_constraint("ck_expenses_amount", "expenses", "amount >= 0")


def downgrade() -> None:
    op.drop_constraint("ck_expenses_amount", "expenses", type_="check")
    op.drop_constraint("ck_quotes_totals", "quotes", type_="check")
    op.drop_constraint("ck_quotes_date_order", "quotes", type_="check")
    op.drop_constraint("ck_invoices_totals", "invoices", type_="check")
    op.drop_constraint("ck_invoices_date_order", "invoices", type_="check")
    op.drop_constraint("ck_time_entries_hourly_rate", "time_entries", type_="check")
    op.drop_constraint("ck_time_entries_duration", "time_entries", type_="check")
    op.drop_constraint("ck_projects_hourly_rate", "projects", type_="check")
    op.drop_constraint("ck_clients_hourly_rate", "clients", type_="check")
    op.drop_index("ix_expenses_reporting", table_name="expenses")
    op.drop_index("ix_quotes_reporting", table_name="quotes")
    op.drop_index("ix_invoices_due_status", table_name="invoices")
    op.drop_index("ix_invoices_reporting", table_name="invoices")
    op.drop_index("ix_time_entries_reporting", table_name="time_entries")
    op.drop_constraint("uq_invoices_request_key", "invoices", type_="unique")
    op.drop_column("invoices", "request_fingerprint")
    op.drop_column("invoices", "request_key")
    op.drop_constraint(
        "uq_time_entries_start_request_key", "time_entries", type_="unique"
    )
    op.drop_column("time_entries", "start_request_fingerprint")
    op.drop_column("time_entries", "start_request_key")

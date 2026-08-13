"""Add projects, quotes, and traceable invoice links."""

from alembic import op
import sqlalchemy as sa

revision = "0002_projects_quotes"
down_revision = "0001_existing_mvp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "company_settings",
        sa.Column("quote_number_prefix", sa.String(32), nullable=False, server_default="AN"),
    )
    op.add_column(
        "company_settings",
        sa.Column("next_quote_number", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("hourly_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("client_id", "name", name="uq_projects_client_name"),
    )
    op.create_index("ix_projects_client_id", "projects", ["client_id"])
    op.add_column("time_entries", sa.Column("project_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_time_entries_project_id", "time_entries", "projects", ["project_id"], ["id"]
    )
    op.create_index("ix_time_entries_project_id", "time_entries", ["project_id"])

    quote_status = sa.Enum(
        "draft", "sent", "accepted", "rejected", "converted", name="quotestatus"
    )
    op.create_table(
        "quotes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("quote_number", sa.String(64), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=False),
        sa.Column("status", quote_status, nullable=False),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("pdf_path", sa.String(512), nullable=True),
        sa.Column("converted_invoice_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("quote_number"),
        sa.UniqueConstraint("converted_invoice_id"),
    )
    op.create_index("ix_quotes_client_id", "quotes", ["client_id"])
    op.create_index("ix_quotes_project_id", "quotes", ["project_id"])
    op.create_index("ix_quotes_quote_number", "quotes", ["quote_number"], unique=True)
    op.create_table(
        "quote_line_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quote_id", sa.Integer(), sa.ForeignKey("quotes.id"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False, server_default="hours"),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
    )
    op.create_index("ix_quote_line_items_quote_id", "quote_line_items", ["quote_id"])

    op.add_column("invoices", sa.Column("quote_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_invoices_quote_id", "invoices", "quotes", ["quote_id"], ["id"]
    )
    op.create_unique_constraint("uq_invoices_quote_id", "invoices", ["quote_id"])
    op.create_foreign_key(
        "fk_quotes_converted_invoice_id",
        "quotes",
        "invoices",
        ["converted_invoice_id"],
        ["id"],
    )
    op.add_column(
        "invoice_line_items",
        sa.Column("unit", sa.String(32), nullable=False, server_default="hours"),
    )
    op.add_column(
        "invoice_line_items", sa.Column("project_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_invoice_line_items_project_id",
        "invoice_line_items",
        "projects",
        ["project_id"],
        ["id"],
    )
    op.create_index(
        "ix_invoice_line_items_project_id", "invoice_line_items", ["project_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_invoice_line_items_project_id", table_name="invoice_line_items")
    op.drop_constraint(
        "fk_invoice_line_items_project_id", "invoice_line_items", type_="foreignkey"
    )
    op.drop_column("invoice_line_items", "project_id")
    op.drop_column("invoice_line_items", "unit")
    op.drop_constraint("fk_quotes_converted_invoice_id", "quotes", type_="foreignkey")
    op.drop_constraint("uq_invoices_quote_id", "invoices", type_="unique")
    op.drop_constraint("fk_invoices_quote_id", "invoices", type_="foreignkey")
    op.drop_column("invoices", "quote_id")
    op.drop_index("ix_quote_line_items_quote_id", table_name="quote_line_items")
    op.drop_table("quote_line_items")
    op.drop_index("ix_quotes_quote_number", table_name="quotes")
    op.drop_index("ix_quotes_project_id", table_name="quotes")
    op.drop_index("ix_quotes_client_id", table_name="quotes")
    op.drop_table("quotes")
    op.drop_index("ix_time_entries_project_id", table_name="time_entries")
    op.drop_constraint("fk_time_entries_project_id", "time_entries", type_="foreignkey")
    op.drop_column("time_entries", "project_id")
    op.drop_index("ix_projects_client_id", table_name="projects")
    op.drop_table("projects")
    op.drop_column("company_settings", "next_quote_number")
    op.drop_column("company_settings", "quote_number_prefix")
    if op.get_bind().dialect.name == "postgresql":
        sa.Enum(name="quotestatus").drop(op.get_bind(), checkfirst=True)

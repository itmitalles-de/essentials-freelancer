"""Add deterministic quote-assistant catalogs, snapshots, and tax breakdowns."""

from alembic import op
import sqlalchemy as sa

revision = "0004_quote_assistant"
down_revision = "0003_modules"
branch_labels = None
depends_on = None


def _add_document_amount_columns(table: str, line_table: str) -> None:
    op.add_column(
        table,
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        table,
        sa.Column("tax_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )
    op.execute(sa.text(f"UPDATE {table} SET subtotal = total, tax_total = 0"))
    op.add_column(
        line_table,
        sa.Column("net_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        line_table,
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        line_table,
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )
    op.execute(sa.text(f"UPDATE {line_table} SET net_amount = amount, tax_amount = 0"))


def upgrade() -> None:
    _add_document_amount_columns("quotes", "quote_line_items")
    _add_document_amount_columns("invoices", "invoice_line_items")

    catalog_kind = sa.Enum("service", "material", "travel", name="catalogitemkind")
    draft_status = sa.Enum(
        "draft", "approved", "transferred", name="assistantdraftstatus"
    )
    op.create_table(
        "quote_catalog_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stable_key", sa.String(128), nullable=False),
        sa.Column("kind", catalog_kind, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("stable_key"),
    )
    op.create_index(
        "ix_quote_catalog_items_stable_key",
        "quote_catalog_items",
        ["stable_key"],
        unique=True,
    )
    op.create_table(
        "quote_catalog_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "item_id", sa.Integer(), sa.ForeignKey("quote_catalog_items.id"), nullable=False
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("net_unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("tax_rate >= 0 AND tax_rate <= 100", name="ck_catalog_tax_rate"),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="ck_catalog_validity",
        ),
        sa.UniqueConstraint("item_id", "version", name="uq_quote_catalog_item_version"),
    )
    op.create_index(
        "ix_quote_catalog_versions_item_id", "quote_catalog_versions", ["item_id"]
    )

    op.create_table(
        "quote_packages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stable_key", sa.String(128), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("stable_key"),
    )
    op.create_index(
        "ix_quote_packages_stable_key", "quote_packages", ["stable_key"], unique=True
    )
    op.create_table(
        "quote_package_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "package_id", sa.Integer(), sa.ForeignKey("quote_packages.id"), nullable=False
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="ck_package_validity",
        ),
        sa.UniqueConstraint("package_id", "version", name="uq_quote_package_version"),
    )
    op.create_index(
        "ix_quote_package_versions_package_id",
        "quote_package_versions",
        ["package_id"],
    )
    op.create_table(
        "quote_package_version_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "package_version_id",
            sa.Integer(),
            sa.ForeignKey("quote_package_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "catalog_version_id",
            sa.Integer(),
            sa.ForeignKey("quote_catalog_versions.id"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint("quantity > 0", name="ck_package_item_quantity"),
        sa.UniqueConstraint(
            "package_version_id",
            "catalog_version_id",
            "sort_order",
            name="uq_quote_package_version_item_order",
        ),
    )
    op.create_index(
        "ix_quote_package_version_items_package_version_id",
        "quote_package_version_items",
        ["package_version_id"],
    )
    op.create_index(
        "ix_quote_package_version_items_catalog_version_id",
        "quote_package_version_items",
        ["catalog_version_id"],
    )

    op.create_table(
        "quote_assistant_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stable_key", sa.String(128), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("stable_key"),
    )
    op.create_index(
        "ix_quote_assistant_templates_stable_key",
        "quote_assistant_templates",
        ["stable_key"],
        unique=True,
    )
    op.create_table(
        "quote_assistant_template_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("quote_assistant_templates.id"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("questions_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("surcharge_percent", sa.Numeric(7, 2), nullable=False, server_default="0"),
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("surcharge_percent >= 0", name="ck_template_surcharge"),
        sa.CheckConstraint(
            "discount_percent >= 0 AND discount_percent <= 100",
            name="ck_template_discount",
        ),
        sa.UniqueConstraint(
            "template_id", "version", name="uq_quote_assistant_template_version"
        ),
    )
    op.create_index(
        "ix_quote_assistant_template_versions_template_id",
        "quote_assistant_template_versions",
        ["template_id"],
    )
    op.create_table(
        "quote_assistant_template_selections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "template_version_id",
            sa.Integer(),
            sa.ForeignKey("quote_assistant_template_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "catalog_version_id",
            sa.Integer(),
            sa.ForeignKey("quote_catalog_versions.id"),
            nullable=True,
        ),
        sa.Column(
            "package_version_id",
            sa.Integer(),
            sa.ForeignKey("quote_package_versions.id"),
            nullable=True,
        ),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint(
            "(catalog_version_id IS NOT NULL AND package_version_id IS NULL) OR "
            "(catalog_version_id IS NULL AND package_version_id IS NOT NULL)",
            name="ck_template_selection_source",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_template_selection_quantity"),
    )
    op.create_index(
        "ix_quote_assistant_template_selections_template_version_id",
        "quote_assistant_template_selections",
        ["template_version_id"],
    )

    op.create_table(
        "quote_assistant_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column(
            "template_version_id",
            sa.Integer(),
            sa.ForeignKey("quote_assistant_template_versions.id"),
            nullable=True,
        ),
        sa.Column("quote_id", sa.Integer(), sa.ForeignKey("quotes.id"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", draft_status, nullable=False),
        sa.Column("pricing_date", sa.Date(), nullable=False),
        sa.Column("guided_answers_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("surcharge_percent", sa.Numeric(7, 2), nullable=False, server_default="0"),
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("base_net_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("surcharge_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("net_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tax_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("transferred_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("surcharge_percent >= 0", name="ck_assistant_surcharge"),
        sa.CheckConstraint(
            "discount_percent >= 0 AND discount_percent <= 100",
            name="ck_assistant_discount",
        ),
        sa.UniqueConstraint("quote_id"),
    )
    op.create_index(
        "ix_quote_assistant_drafts_client_id", "quote_assistant_drafts", ["client_id"]
    )
    op.create_index(
        "ix_quote_assistant_drafts_project_id", "quote_assistant_drafts", ["project_id"]
    )
    op.create_table(
        "quote_assistant_draft_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "draft_id",
            sa.Integer(),
            sa.ForeignKey("quote_assistant_drafts.id"),
            nullable=False,
        ),
        sa.Column(
            "catalog_version_id",
            sa.Integer(),
            sa.ForeignKey("quote_catalog_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "package_version_id",
            sa.Integer(),
            sa.ForeignKey("quote_package_versions.id"),
            nullable=True,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("net_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_quote_assistant_draft_lines_draft_id",
        "quote_assistant_draft_lines",
        ["draft_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_quote_assistant_draft_lines_draft_id",
        table_name="quote_assistant_draft_lines",
    )
    op.drop_table("quote_assistant_draft_lines")
    op.drop_index("ix_quote_assistant_drafts_project_id", table_name="quote_assistant_drafts")
    op.drop_index("ix_quote_assistant_drafts_client_id", table_name="quote_assistant_drafts")
    op.drop_table("quote_assistant_drafts")
    op.drop_index(
        "ix_quote_assistant_template_selections_template_version_id",
        table_name="quote_assistant_template_selections",
    )
    op.drop_table("quote_assistant_template_selections")
    op.drop_index(
        "ix_quote_assistant_template_versions_template_id",
        table_name="quote_assistant_template_versions",
    )
    op.drop_table("quote_assistant_template_versions")
    op.drop_index(
        "ix_quote_assistant_templates_stable_key",
        table_name="quote_assistant_templates",
    )
    op.drop_table("quote_assistant_templates")
    op.drop_index(
        "ix_quote_package_version_items_catalog_version_id",
        table_name="quote_package_version_items",
    )
    op.drop_index(
        "ix_quote_package_version_items_package_version_id",
        table_name="quote_package_version_items",
    )
    op.drop_table("quote_package_version_items")
    op.drop_index(
        "ix_quote_package_versions_package_id", table_name="quote_package_versions"
    )
    op.drop_table("quote_package_versions")
    op.drop_index("ix_quote_packages_stable_key", table_name="quote_packages")
    op.drop_table("quote_packages")
    op.drop_index(
        "ix_quote_catalog_versions_item_id", table_name="quote_catalog_versions"
    )
    op.drop_table("quote_catalog_versions")
    op.drop_index("ix_quote_catalog_items_stable_key", table_name="quote_catalog_items")
    op.drop_table("quote_catalog_items")
    for table, line_table in (
        ("invoices", "invoice_line_items"),
        ("quotes", "quote_line_items"),
    ):
        op.drop_column(line_table, "tax_amount")
        op.drop_column(line_table, "tax_rate")
        op.drop_column(line_table, "net_amount")
        op.drop_column(table, "tax_total")
        op.drop_column(table, "subtotal")
    if op.get_bind().dialect.name == "postgresql":
        sa.Enum(name="assistantdraftstatus").drop(op.get_bind(), checkfirst=True)
        sa.Enum(name="catalogitemkind").drop(op.get_bind(), checkfirst=True)

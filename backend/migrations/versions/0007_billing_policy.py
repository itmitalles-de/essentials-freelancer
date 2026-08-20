"""Add explicit billing decisions and immutable invoice snapshots."""

from alembic import op
import sqlalchemy as sa


revision = "0007_billing_policy"
down_revision = "0006_pilot_safety"
branch_labels = None
depends_on = None


def _postgresql_constraints() -> None:
    op.create_check_constraint(
        "ck_company_settings_billing_rates",
        "company_settings",
        "private_hourly_rate >= 0 AND business_hourly_rate >= 0 "
        "AND travel_hourly_rate >= 0",
    )
    op.create_check_constraint(
        "ck_company_settings_billing_minutes",
        "company_settings",
        "first_order_minimum_minutes >= 0 AND onsite_minimum_minutes >= 0 "
        "AND remote_increment_minutes > 0 AND travel_minimum_minutes >= 0 "
        "AND (travel_increment_minutes IS NULL OR travel_increment_minutes > 0)",
    )
    op.create_check_constraint(
        "ck_company_settings_default_tax_rate",
        "company_settings",
        "default_tax_rate >= 0 AND default_tax_rate <= 100",
    )
    op.create_check_constraint(
        "ck_clients_billing_rate_type",
        "clients",
        "billing_rate_type IN ('private', 'business', 'custom')",
    )
    op.create_check_constraint(
        "ck_clients_default_service_mode",
        "clients",
        "default_service_mode IS NULL OR default_service_mode IN ('remote', 'onsite')",
    )
    op.create_check_constraint(
        "ck_projects_billing_rate_type_override",
        "projects",
        "billing_rate_type_override IS NULL OR "
        "billing_rate_type_override IN ('private', 'business', 'custom')",
    )
    op.create_check_constraint(
        "ck_projects_default_service_mode",
        "projects",
        "default_service_mode IN ('remote', 'onsite')",
    )
    op.create_check_constraint(
        "ck_time_entries_billable_minutes",
        "time_entries",
        "billable_minutes IS NULL OR billable_minutes >= 0",
    )
    op.create_check_constraint(
        "ck_time_entries_billing_rate_type",
        "time_entries",
        "billing_rate_type IS NULL OR billing_rate_type IN ('private', 'business', 'custom')",
    )
    op.create_check_constraint(
        "ck_time_entries_service_mode",
        "time_entries",
        "service_mode IS NULL OR service_mode IN ('remote', 'onsite')",
    )
    op.create_check_constraint(
        "ck_time_entries_travel_minutes",
        "time_entries",
        "travel_actual_minutes >= 0 AND "
        "(travel_billable_minutes IS NULL OR travel_billable_minutes >= 0)",
    )


def upgrade() -> None:
    op.add_column(
        "company_settings",
        sa.Column(
            "private_hourly_rate",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="50.00",
        ),
    )
    op.add_column(
        "company_settings",
        sa.Column(
            "business_hourly_rate",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="75.00",
        ),
    )
    op.add_column(
        "company_settings",
        sa.Column(
            "travel_hourly_rate",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="30.00",
        ),
    )
    op.add_column(
        "company_settings",
        sa.Column(
            "first_order_minimum_minutes",
            sa.Integer(),
            nullable=False,
            server_default="60",
        ),
    )
    op.add_column(
        "company_settings",
        sa.Column(
            "onsite_minimum_minutes",
            sa.Integer(),
            nullable=False,
            server_default="60",
        ),
    )
    op.add_column(
        "company_settings",
        sa.Column(
            "remote_increment_minutes",
            sa.Integer(),
            nullable=False,
            server_default="15",
        ),
    )
    op.add_column(
        "company_settings",
        sa.Column(
            "travel_minimum_minutes",
            sa.Integer(),
            nullable=False,
            server_default="30",
        ),
    )
    op.add_column(
        "company_settings",
        sa.Column("travel_increment_minutes", sa.Integer(), nullable=True),
    )
    op.add_column(
        "company_settings",
        sa.Column(
            "default_tax_rate",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="0.00",
        ),
    )
    op.add_column(
        "company_settings",
        sa.Column(
            "small_business_notice_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "company_settings",
        sa.Column(
            "small_business_notice_text",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )

    op.add_column(
        "clients",
        sa.Column(
            "billing_rate_type",
            sa.String(16),
            nullable=False,
            server_default="custom",
        ),
    )
    op.add_column(
        "clients", sa.Column("default_service_mode", sa.String(16), nullable=True)
    )
    op.add_column(
        "clients",
        sa.Column(
            "billing_profile_confirmed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.add_column(
        "projects",
        sa.Column("billing_rate_type_override", sa.String(16), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column(
            "default_service_mode",
            sa.String(16),
            nullable=False,
            server_default="remote",
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "is_individual_project",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "billing_profile_confirmed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    for column in (
        sa.Column("billable_minutes", sa.Integer(), nullable=True),
        sa.Column("billing_rate_type", sa.String(16), nullable=True),
        sa.Column("billing_rate_source", sa.String(32), nullable=True),
        sa.Column("applied_minimum_minutes", sa.Integer(), nullable=True),
        sa.Column("applied_increment_minutes", sa.Integer(), nullable=True),
        sa.Column("service_mode", sa.String(16), nullable=True),
        sa.Column(
            "is_first_order", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("billing_reason", sa.String(64), nullable=True),
        sa.Column("billing_policy_id", sa.String(80), nullable=True),
        sa.Column(
            "billing_policy_applied",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "travel_actual_minutes",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("travel_billable_minutes", sa.Integer(), nullable=True),
        sa.Column("travel_hourly_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("travel_minimum_minutes", sa.Integer(), nullable=True),
        sa.Column("travel_increment_minutes", sa.Integer(), nullable=True),
        sa.Column("travel_billing_reason", sa.String(64), nullable=True),
    ):
        op.add_column("time_entries", column)
    op.execute(
        "UPDATE time_entries SET billing_policy_id = "
        "CASE WHEN billed THEN 'legacy-preserved-v0' ELSE 'legacy-unconfirmed-v0' END, "
        "billing_reason = "
        "CASE WHEN billed THEN 'legacy_preserved' ELSE 'legacy_unconfirmed' END"
    )

    for column in (
        sa.Column("tax_status_snapshot", sa.String(32), nullable=True),
        sa.Column("tax_notice_snapshot", sa.Text(), nullable=True),
        sa.Column("footer_note_snapshot", sa.Text(), nullable=True),
        sa.Column("billing_confirmation_token", sa.String(80), nullable=True),
    ):
        op.add_column("invoices", column)

    for column in (
        sa.Column("snapshot_line_kind", sa.String(16), nullable=True),
        sa.Column("snapshot_actual_minutes", sa.Integer(), nullable=True),
        sa.Column("snapshot_billable_minutes", sa.Integer(), nullable=True),
        sa.Column("snapshot_hourly_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("snapshot_rate_type", sa.String(16), nullable=True),
        sa.Column("snapshot_minimum_minutes", sa.Integer(), nullable=True),
        sa.Column("snapshot_increment_minutes", sa.Integer(), nullable=True),
        sa.Column("snapshot_service_mode", sa.String(16), nullable=True),
        sa.Column("snapshot_is_first_order", sa.Boolean(), nullable=True),
        sa.Column("snapshot_billing_reason", sa.String(64), nullable=True),
        sa.Column("snapshot_billing_policy_id", sa.String(80), nullable=True),
        sa.Column("snapshot_service_date", sa.Date(), nullable=True),
        sa.Column("snapshot_project_name", sa.String(255), nullable=True),
    ):
        op.add_column("invoice_line_items", column)

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("invoice_line_items") as batch:
            batch.alter_column(
                "quantity",
                existing_type=sa.Numeric(10, 2),
                type_=sa.Numeric(12, 4),
                existing_nullable=False,
            )
    else:
        op.alter_column(
            "invoice_line_items",
            "quantity",
            existing_type=sa.Numeric(10, 2),
            type_=sa.Numeric(12, 4),
            existing_nullable=False,
        )
        _postgresql_constraints()

    op.execute(
        "UPDATE module_installations SET state = 'disabled' "
        "WHERE module_id = 'communication.smtp'"
    )


def downgrade() -> None:
    raise RuntimeError(
        "Refusing to discard billing-policy and invoice-snapshot evidence; "
        "restore a verified complete backup instead"
    )

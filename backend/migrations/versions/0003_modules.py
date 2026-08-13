"""Add the repository-local Essentials+ module contract state and audit log."""

from alembic import op
import sqlalchemy as sa

revision = "0003_modules"
down_revision = "0002_projects_quotes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "module_installations",
        sa.Column("module_id", sa.String(128), primary_key=True),
        sa.Column("manifest_schema_version", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column(
            "configuration_json", sa.Text(), nullable=False, server_default="{}"
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "state IN ('not_installed', 'needs_configuration', 'disabled', 'enabled', 'degraded')",
            name="ck_module_installations_state",
        ),
    )
    op.create_table(
        "module_audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "module_id",
            sa.String(128),
            sa.ForeignKey("module_installations.module_id"),
            nullable=False,
        ),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("previous_state", sa.String(32), nullable=False),
        sa.Column("resulting_state", sa.String(32), nullable=False),
        sa.Column("actor", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_module_audit_events_module_id", "module_audit_events", ["module_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_module_audit_events_module_id", table_name="module_audit_events"
    )
    op.drop_table("module_audit_events")
    op.drop_table("module_installations")

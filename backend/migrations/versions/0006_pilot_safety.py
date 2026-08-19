"""Add idempotent invoice-send evidence for the internal pilot."""

from alembic import op
import sqlalchemy as sa


revision = "0006_pilot_safety"
down_revision = "0005_operational_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This exact sentence was formerly injected by the application on every
    # fresh installation. It was not proof of an operator tax decision, so the
    # pilot migration removes only that known generated value. Custom footer
    # text is preserved verbatim.
    op.execute(
        sa.text(
            "UPDATE company_settings SET invoice_footer_note = '' "
            "WHERE invoice_footer_note = :legacy_default"
        ).bindparams(
            legacy_default="Gemäß § 19 UStG wird keine Umsatzsteuer berechnet."
        )
    )
    op.create_table(
        "invoice_send_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "invoice_id",
            sa.Integer(),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("is_resend", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("outcome", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("message_id", sa.String(255), nullable=True),
        sa.Column("failure_code", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "outcome IN ('pending', 'sent', 'failed')",
            name="ck_invoice_send_attempts_outcome",
        ),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_invoice_send_attempts_idempotency_key"
        ),
    )
    op.create_index(
        "ix_invoice_send_attempts_invoice_id",
        "invoice_send_attempts",
        ["invoice_id"],
    )
    op.create_index(
        "ix_invoice_send_attempts_invoice_created",
        "invoice_send_attempts",
        ["invoice_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_invoice_send_attempts_invoice_created",
        table_name="invoice_send_attempts",
    )
    op.drop_index(
        "ix_invoice_send_attempts_invoice_id", table_name="invoice_send_attempts"
    )
    op.drop_table("invoice_send_attempts")

#!/usr/bin/env python3
"""Upgrade a populated copy of the previous PostgreSQL schema and compare it."""

from __future__ import annotations

from decimal import Decimal
import os
import re

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def database_url(admin_url: str, name: str) -> str:
    return f"{admin_url.rsplit('/', 1)[0]}/{name}"


def migration_config(url: str) -> Config:
    config = Config("/app/alembic.ini")
    config.set_main_option("script_location", "/app/migrations")
    config.set_main_option("sqlalchemy.url", url)
    return config


def main() -> None:
    admin_url = os.environ["MIGRATION_ADMIN_DATABASE_URL"]
    run_id = os.environ["MIGRATION_RUN_ID"].lower()
    expect(bool(re.fullmatch(r"[a-z0-9]+", run_id)), "unsafe migration run id")
    source_name = f"billing_0006_source_{run_id}"
    copy_name = f"billing_0006_copy_{run_id}"
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    source = None
    copied = None

    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{source_name}"'))

        source_url = database_url(admin_url, source_name)
        command.upgrade(migration_config(source_url), "0006_pilot_safety")
        source = create_engine(source_url)
        with source.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO company_settings ("
                    "id, company_name, owner_name, address_line1, address_line2, "
                    "zip_city, email, phone, tax_id, iban, bic, bank_name, "
                    "invoice_footer_note, invoice_number_prefix, next_invoice_number, "
                    "quote_number_prefix, next_quote_number, logo_path, "
                    "default_hourly_rate, default_payment_terms_days) VALUES ("
                    "1, 'Historischer Betrieb', 'Historische Betreiberin', "
                    "'Altweg 1', '', '00000 Altstadt', 'old@example.invalid', '', '', "
                    "'', '', '', 'Eigener historischer Footer', 'RE', 43, 'AN', 7, "
                    "NULL, 84.25, 14)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO clients ("
                    "id, name, contact_person, address_line1, address_line2, zip_city, "
                    "email, hourly_rate, notes, active, created_at) VALUES ("
                    "1, 'Historischer Kunde', '', '', '', '', 'old-client@example.invalid', "
                    "84.25, '', TRUE, '2026-08-01 10:00:00')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO projects ("
                    "id, client_id, name, description, hourly_rate, active, created_at) "
                    "VALUES (1, 1, 'Historisches Projekt', '', 75.00, TRUE, "
                    "'2026-08-01 10:00:00')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO invoices ("
                    "id, client_id, invoice_number, issue_date, due_date, status, "
                    "subtotal, tax_total, total, notes, pdf_path, sent_at, paid_at, "
                    "created_at, quote_id, request_key, request_fingerprint) VALUES ("
                    "1, 1, 'RE-2026-0042', '2026-08-02', '2026-08-16', 'sent', "
                    "14.17, 0.00, 14.17, 'Historische Rechnung', "
                    "'/data/invoices/RE-2026-0042.pdf', '2026-08-02 12:00:00', NULL, "
                    "'2026-08-02 11:00:00', NULL, NULL, NULL)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO invoice_line_items ("
                    "id, invoice_id, description, quantity, unit_price, net_amount, "
                    "tax_rate, tax_amount, amount, unit, project_id) VALUES ("
                    "1, 1, 'Historische Leistung', 0.17, 84.25, 14.17, 0.00, "
                    "0.00, 14.17, 'hours', 1)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO time_entries ("
                    "id, client_id, project_id, date, description, duration_minutes, "
                    "hourly_rate, running_started_at, billed, invoice_id, created_at, "
                    "start_request_key, start_request_fingerprint) VALUES "
                    "(1, 1, 1, '2026-08-02', 'Historisch abgerechnet', 10, 84.25, "
                    "NULL, TRUE, 1, '2026-08-02 10:00:00', NULL, NULL), "
                    "(2, 1, 1, '2026-08-03', 'Historisch offen', 16, 84.25, "
                    "NULL, FALSE, NULL, '2026-08-03 10:00:00', NULL, NULL)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO module_installations ("
                    "module_id, manifest_schema_version, state, configuration_json, "
                    "created_at, updated_at) VALUES ("
                    "'communication.smtp', 1, 'enabled', '{}', "
                    "'2026-08-01 10:00:00', '2026-08-01 10:00:00')"
                )
            )

        source.dispose()
        source = None
        with admin.connect() as connection:
            connection.execute(
                text(f'CREATE DATABASE "{copy_name}" TEMPLATE "{source_name}"')
            )

        copy_url = database_url(admin_url, copy_name)
        command.upgrade(migration_config(copy_url), "head")
        source = create_engine(source_url)
        copied = create_engine(copy_url)

        with source.connect() as source_connection:
            expect(
                source_connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar()
                == "0006_pilot_safety",
                "source database was modified",
            )
            expect(
                source_connection.execute(
                    text("SELECT total FROM invoices WHERE id = 1")
                ).scalar()
                == Decimal("14.17"),
                "source invoice changed",
            )

        with copied.connect() as connection:
            expect(
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
                == "0007_billing_policy",
                "copied database did not reach 0007",
            )
            invoice = connection.execute(
                text(
                    "SELECT invoice_number, subtotal, tax_total, total, pdf_path "
                    "FROM invoices WHERE id = 1"
                )
            ).one()
            expect(
                invoice
                == (
                    "RE-2026-0042",
                    Decimal("14.17"),
                    Decimal("0.00"),
                    Decimal("14.17"),
                    "/data/invoices/RE-2026-0042.pdf",
                ),
                "historical invoice fields changed",
            )
            line = connection.execute(
                text(
                    "SELECT quantity, unit_price, net_amount, tax_amount, amount, "
                    "snapshot_actual_minutes FROM invoice_line_items WHERE id = 1"
                )
            ).one()
            expect(
                line
                == (
                    Decimal("0.1700"),
                    Decimal("84.25"),
                    Decimal("14.17"),
                    Decimal("0.00"),
                    Decimal("14.17"),
                    None,
                ),
                "historical invoice line changed",
            )
            times = connection.execute(
                text(
                    "SELECT id, duration_minutes, hourly_rate, billing_policy_applied, "
                    "billing_policy_id FROM time_entries ORDER BY id"
                )
            ).all()
            expect(
                times
                == [
                    (1, 10, Decimal("84.25"), False, "legacy-preserved-v0"),
                    (2, 16, Decimal("84.25"), False, "legacy-unconfirmed-v0"),
                ],
                "historical time rows changed or were silently confirmed",
            )
            profiles = connection.execute(
                text(
                    "SELECT c.billing_rate_type, c.billing_profile_confirmed, "
                    "p.billing_profile_confirmed FROM clients c "
                    "JOIN projects p ON p.client_id = c.id WHERE c.id = 1"
                )
            ).one()
            expect(
                profiles == ("custom", False, False),
                "legacy billing profiles were silently confirmed",
            )
            settings = connection.execute(
                text(
                    "SELECT private_hourly_rate, business_hourly_rate, travel_hourly_rate, "
                    "travel_minimum_minutes, travel_increment_minutes, "
                    "invoice_footer_note, next_invoice_number "
                    "FROM company_settings WHERE id = 1"
                )
            ).one()
            expect(
                settings
                == (
                    Decimal("50.00"),
                    Decimal("75.00"),
                    Decimal("30.00"),
                    30,
                    None,
                    "Eigener historischer Footer",
                    43,
                ),
                "billing defaults, footer, or invoice sequence differ",
            )
            expect(
                connection.execute(
                    text(
                        "SELECT state FROM module_installations "
                        "WHERE module_id = 'communication.smtp'"
                    )
                ).scalar()
                == "disabled",
                "SMTP was not disabled during upgrade",
            )

        print("postgres-migration-copy: populated 0006 copy upgraded without history drift")
    finally:
        if copied is not None:
            copied.dispose()
        if source is not None:
            source.dispose()
        with admin.connect() as connection:
            for name in (copy_name, source_name):
                connection.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname = :name AND pid <> pg_backend_pid()"
                    ),
                    {"name": name},
                )
                connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        admin.dispose()


if __name__ == "__main__":
    main()

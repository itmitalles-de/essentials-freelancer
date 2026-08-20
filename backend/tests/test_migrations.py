from hashlib import sha256
from pathlib import Path
from decimal import Decimal

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, Table, create_engine, inspect, insert, text


def migration_config(database_url: str) -> Config:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(backend_dir / "alembic.ini")
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_base_migration_creates_empty_database_and_revision_chain(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'migrations.sqlite'}"
    config = migration_config(database_url)
    command.upgrade(config, "0001_existing_mvp")
    command.stamp(config, "head")

    engine = create_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert {
        "alembic_version",
        "clients",
        "time_entries",
        "invoices",
    } <= tables
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0007_billing_policy"


def test_legacy_baseline_refuses_partial_schema(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'partial.sqlite'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))

    try:
        command.upgrade(migration_config(database_url), "head")
    except RuntimeError as exc:
        assert "Legacy schema is incomplete" in str(exc)
    else:
        raise AssertionError("partial legacy schema was accepted")


def test_legacy_baseline_refuses_destructive_downgrade(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'downgrade.sqlite'}"
    config = migration_config(database_url)
    command.upgrade(config, "0001_existing_mvp")

    try:
        command.downgrade(config, "base")
    except RuntimeError as exc:
        assert "Refusing to downgrade the legacy baseline" in str(exc)
    else:
        raise AssertionError("destructive baseline downgrade was accepted")


def test_pilot_migration_clears_only_generated_tax_footer(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'pilot-footer.sqlite'}"
    config = migration_config(database_url)
    command.upgrade(config, "0001_existing_mvp")
    # Earlier migrations contain PostgreSQL-specific ALTER operations. This
    # fixture isolates 0006 while the full-check exercises the complete chain
    # on PostgreSQL.
    command.stamp(config, "0005_operational_hardening")
    engine = create_engine(database_url)
    company = Table("company_settings", MetaData(), autoload_with=engine)
    values = {}
    for column in company.columns:
        if column.name == "id":
            values[column.name] = 1
        elif column.name == "invoice_footer_note":
            values[column.name] = "Gemäß § 19 UStG wird keine Umsatzsteuer berechnet."
        elif "INT" in str(column.type).upper() or "NUMERIC" in str(column.type).upper():
            values[column.name] = 0
        elif not column.nullable:
            values[column.name] = ""
    with engine.begin() as connection:
        connection.execute(insert(company).values(**values))

    command.upgrade(config, "0006_pilot_safety")
    assert "invoice_send_attempts" in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT invoice_footer_note FROM company_settings WHERE id = 1")
        ).scalar() == ""


def test_billing_migration_preserves_legacy_rows_and_document_bytes(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'billing-upgrade.sqlite'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE company_settings ("
                "id INTEGER PRIMARY KEY, invoice_footer_note TEXT NOT NULL)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE clients (id INTEGER PRIMARY KEY, "
                "hourly_rate NUMERIC(10,2))"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE projects (id INTEGER PRIMARY KEY, "
                "hourly_rate NUMERIC(10,2))"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE time_entries (id INTEGER PRIMARY KEY, "
                "duration_minutes INTEGER NOT NULL, hourly_rate NUMERIC(10,2) NOT NULL, "
                "billed BOOLEAN NOT NULL)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE invoices (id INTEGER PRIMARY KEY, "
                "invoice_number VARCHAR(64) NOT NULL, total NUMERIC(12,2) NOT NULL)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE invoice_line_items (id INTEGER PRIMARY KEY, "
                "invoice_id INTEGER NOT NULL, description TEXT NOT NULL, "
                "quantity NUMERIC(10,2) NOT NULL, unit_price NUMERIC(10,2) NOT NULL, "
                "amount NUMERIC(12,2) NOT NULL)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE module_installations (module_id VARCHAR(128) PRIMARY KEY, "
                "state VARCHAR(32) NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO company_settings (id, invoice_footer_note) "
                "VALUES (1, 'Eigener Footer')"
            )
        )
        connection.execute(
            text("INSERT INTO clients (id, hourly_rate) VALUES (1, 84.25)")
        )
        connection.execute(
            text("INSERT INTO projects (id, hourly_rate) VALUES (1, 75.00)")
        )
        connection.execute(
            text(
                "INSERT INTO time_entries (id, duration_minutes, hourly_rate, billed) "
                "VALUES (1, 10, 84.25, 1), (2, 16, 84.25, 0)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO invoices (id, invoice_number, total) "
                "VALUES (1, 'RE-2026-0042', 14.17)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO invoice_line_items "
                "(id, invoice_id, description, quantity, unit_price, amount) "
                "VALUES (1, 1, 'Historische Leistung', 0.17, 84.25, 14.17)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO module_installations (module_id, state) "
                "VALUES ('communication.smtp', 'enabled')"
            )
        )

    document = tmp_path / "RE-2026-0042.pdf"
    document.write_bytes(b"%PDF-legacy-byte-exact\n")
    before_hash = sha256(document.read_bytes()).hexdigest()

    config = migration_config(database_url)
    command.stamp(config, "0006_pilot_safety")
    command.upgrade(config, "head")

    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT invoice_number FROM invoices WHERE id = 1")
        ).scalar() == "RE-2026-0042"
        assert str(
            connection.execute(text("SELECT total FROM invoices WHERE id = 1")).scalar()
        ) == "14.17"
        line = connection.execute(
            text(
                "SELECT quantity, unit_price, amount, snapshot_actual_minutes "
                "FROM invoice_line_items WHERE id = 1"
            )
        ).one()
        assert [Decimal(str(line[0])), Decimal(str(line[1])), Decimal(str(line[2])), line[3]] == [
            Decimal("0.17"),
            Decimal("84.25"),
            Decimal("14.17"),
            None,
        ]
        times = connection.execute(
            text(
                "SELECT id, duration_minutes, hourly_rate, billing_policy_applied, "
                "billing_policy_id FROM time_entries ORDER BY id"
            )
        ).all()
        assert [(row[0], row[1], Decimal(str(row[2])), bool(row[3]), row[4]) for row in times] == [
            (1, 10, Decimal("84.25"), False, "legacy-preserved-v0"),
            (2, 16, Decimal("84.25"), False, "legacy-unconfirmed-v0"),
        ]
        assert connection.execute(
            text("SELECT billing_rate_type FROM clients WHERE id = 1")
        ).scalar() == "custom"
        assert not bool(
            connection.execute(
                text("SELECT billing_profile_confirmed FROM clients WHERE id = 1")
            ).scalar()
        )
        assert connection.execute(
            text("SELECT state FROM module_installations WHERE module_id = 'communication.smtp'")
        ).scalar() == "disabled"
        rates = connection.execute(
            text(
                "SELECT private_hourly_rate, business_hourly_rate, travel_hourly_rate, "
                "travel_minimum_minutes, travel_increment_minutes "
                "FROM company_settings WHERE id = 1"
            )
        ).one()
        assert [Decimal(str(rates[0])), Decimal(str(rates[1])), Decimal(str(rates[2])), rates[3], rates[4]] == [
            Decimal("50.00"),
            Decimal("75.00"),
            Decimal("30.00"),
            30,
            None,
        ]
        assert connection.execute(
            text("SELECT invoice_footer_note FROM company_settings WHERE id = 1")
        ).scalar() == "Eigener Footer"

    assert sha256(document.read_bytes()).hexdigest() == before_hash

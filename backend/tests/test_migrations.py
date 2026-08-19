from pathlib import Path

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
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0006_pilot_safety"


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

    command.upgrade(config, "head")
    assert "invoice_send_attempts" in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT invoice_footer_note FROM company_settings WHERE id = 1")
        ).scalar() == ""

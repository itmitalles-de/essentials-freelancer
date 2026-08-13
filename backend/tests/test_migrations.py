from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


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
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0004_quote_assistant"


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

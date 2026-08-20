import os
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

TEST_ROOT = Path(tempfile.mkdtemp(prefix="freelancer-tests-"))
os.environ.update(
    {
        "DATABASE_URL": f"sqlite:///{TEST_ROOT / 'test.sqlite'}",
        "JWT_SECRET": "test-only-jwt-secret-at-least-32-bytes",
        "ADMIN_USERNAME": "test-admin",
        "ADMIN_PASSWORD": "test-only-password",
        "PDF_STORAGE_DIR": str(TEST_ROOT / "documents"),
        "RUN_MIGRATIONS": "false",
        "LOGIN_RATE_LIMIT_PER_MINUTE": "1000",
        "SMTP_RATE_LIMIT_PER_MINUTE": "1000",
    }
)

from app.database import Base, SessionLocal, engine  # noqa: E402
import app.main as main_module  # noqa: E402
from app.main import app, seed_admin  # noqa: E402
from app.rate_limit import limiter  # noqa: E402


def _fast_test_hash(password: str) -> str:
    """Exercise bcrypt semantics without paying production work factor per test."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()


main_module.hash_password = _fast_test_hash


@event.listens_for(engine, "connect")
def _configure_test_sqlite(dbapi_connection, _connection_record) -> None:
    """Avoid durable fsync overhead for the disposable synthetic test database."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=MEMORY")
    cursor.execute("PRAGMA synchronous=OFF")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.close()


@pytest.fixture(autouse=True)
def reset_storage() -> Iterator[None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_admin()
    limiter.reset()
    documents = TEST_ROOT / "documents"
    shutil.rmtree(documents, ignore_errors=True)
    documents.mkdir(parents=True)
    yield


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": "test-admin", "password": "test-only-password"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
    shutil.rmtree(TEST_ROOT, ignore_errors=True)

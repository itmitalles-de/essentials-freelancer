from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.models import (
    Client,
    Expense,
    Invoice,
    InvoiceStatus,
    Project,
    Quote,
    QuoteStatus,
    TimeEntry,
)
from app.rate_limit import limiter


REPORT_DATE = date(2026, 8, 13)


def _seed_report_data(db_session):
    first = Client(name="Alpha Studio", hourly_rate=Decimal("100.00"))
    second = Client(name="Beta Studio", hourly_rate=Decimal("80.00"))
    db_session.add_all([first, second])
    db_session.flush()
    project = Project(client_id=first.id, name="Alpha Project")
    db_session.add(project)
    db_session.flush()
    db_session.add_all(
        [
            TimeEntry(
                client_id=first.id,
                project_id=project.id,
                date=REPORT_DATE,
                description="=synthetic formula",
                duration_minutes=120,
                hourly_rate=Decimal("100.00"),
                billed=False,
            ),
            TimeEntry(
                client_id=first.id,
                project_id=project.id,
                date=REPORT_DATE,
                description="Already billed",
                duration_minutes=60,
                hourly_rate=Decimal("100.00"),
                billed=True,
            ),
            TimeEntry(
                client_id=second.id,
                date=REPORT_DATE,
                description="Other client",
                duration_minutes=30,
                hourly_rate=Decimal("80.00"),
                billed=False,
            ),
        ]
    )
    for number, status in enumerate(
        [QuoteStatus.converted, QuoteStatus.rejected, QuoteStatus.draft], start=1
    ):
        db_session.add(
            Quote(
                client_id=first.id,
                project_id=project.id,
                quote_number=f"AN-TEST-{number}",
                issue_date=REPORT_DATE,
                valid_until=REPORT_DATE + timedelta(days=14),
                status=status,
                subtotal=Decimal("100.00"),
                tax_total=Decimal("19.00"),
                total=Decimal("119.00"),
            )
        )
    today = date.today()
    invoice_specs = [
        (InvoiceStatus.draft, today + timedelta(days=14), Decimal("20.00")),
        (InvoiceStatus.sent, today + timedelta(days=14), Decimal("50.00")),
        (InvoiceStatus.sent, today - timedelta(days=1), Decimal("100.00")),
        (InvoiceStatus.paid, today, Decimal("70.00")),
        (InvoiceStatus.cancelled, today, Decimal("10.00")),
    ]
    for number, (status, due_date, total) in enumerate(invoice_specs, start=1):
        db_session.add(
            Invoice(
                client_id=first.id,
                invoice_number=f"RE-TEST-{number}",
                issue_date=REPORT_DATE - timedelta(days=12),
                due_date=due_date,
                status=status,
                subtotal=total,
                tax_total=Decimal("0.00"),
                total=total,
            )
        )
    db_session.add_all(
        [
            Expense(
                date=REPORT_DATE,
                description="Hosting",
                category="Software",
                amount=Decimal("10.00"),
            ),
            Expense(
                date=REPORT_DATE,
                description="Train",
                category="Travel",
                amount=Decimal("5.50"),
            ),
        ]
    )
    db_session.commit()
    return first.id, second.id, project.id


def test_reporting_summary_filters_and_csv_are_machine_readable(
    client: TestClient, auth_headers: dict[str, str], db_session
):
    first_id, second_id, project_id = _seed_report_data(db_session)

    response = client.get(
        "/api/reports/summary?date_from=2026-08-01&date_to=2026-08-31",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["time"]["captured_hours"] == "3.50"
    assert report["time"]["unbilled_hours"] == "2.50"
    assert report["quotes"]["statuses"] == {
        "draft": 1,
        "sent": 0,
        "accepted": 0,
        "rejected": 1,
        "converted": 1,
    }
    assert report["quotes"]["conversion_rate_percent"] == "50.00"
    assert report["invoices"]["statuses"] == {
        "draft": 1,
        "sent": 1,
        "overdue": 1,
        "paid": 1,
        "cancelled": 1,
    }
    assert report["invoices"]["open_amount"] == "150.00"
    assert report["invoices"]["paid_amount"] == "70.00"
    assert report["expenses"]["total"] == "15.50"

    filtered = client.get(
        f"/api/reports/summary?client_id={second_id}", headers=auth_headers
    ).json()
    assert filtered["time"]["captured_hours"] == "0.50"
    assert filtered["time"]["groups"][0]["client_id"] == second_id
    assert filtered["quotes"]["statuses"]["draft"] == 0

    project_filtered = client.get(
        f"/api/reports/summary?project_id={project_id}", headers=auth_headers
    ).json()
    assert project_filtered["time"]["captured_hours"] == "3.00"
    assert project_filtered["time"]["groups"][0]["client_id"] == first_id

    csv_response = client.get("/api/reports/time.csv", headers=auth_headers)
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "'=synthetic formula" in csv_response.text
    assert "date,client_id,project_id" in csv_response.text

    assert (
        client.get(
            "/api/reports/summary?date_from=2026-09-01&date_to=2026-08-01",
            headers=auth_headers,
        ).status_code
        == 422
    )


def test_list_filter_pagination_and_database_constraint(
    client: TestClient, auth_headers: dict[str, str], db_session
):
    for name, active in [("Alpha One", True), ("Alpha Two", False), ("Beta", True)]:
        assert client.post(
            "/api/clients",
            headers=auth_headers,
            json={"name": name, "active": active},
        ).status_code == 200

    page = client.get(
        "/api/clients?q=Alpha&limit=1&offset=1", headers=auth_headers
    )
    assert page.status_code == 200
    assert page.headers["x-total-count"] == "2"
    assert [item["name"] for item in page.json()] == ["Alpha Two"]
    active = client.get("/api/clients?active=true", headers=auth_headers)
    assert active.headers["x-total-count"] == "2"

    db_session.add(
        Expense(
            date=REPORT_DATE,
            description="Invalid",
            category="Synthetic",
            amount=Decimal("-0.01"),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_timer_and_invoice_idempotency(
    client: TestClient, auth_headers: dict[str, str]
):
    customer = client.post(
        "/api/clients",
        headers=auth_headers,
        json={"name": "Idempotency Client", "hourly_rate": "90.00"},
    ).json()
    timer_headers = {**auth_headers, "Idempotency-Key": "timer-request-1"}
    payload = {"client_id": customer["id"], "description": "Same command"}
    first = client.post("/api/time-entries/start", headers=timer_headers, json=payload)
    repeated = client.post("/api/time-entries/start", headers=timer_headers, json=payload)
    assert first.status_code == repeated.status_code == 200
    assert first.json()["id"] == repeated.json()["id"]
    conflict = client.post(
        "/api/time-entries/start",
        headers=timer_headers,
        json={"client_id": customer["id"], "description": "Changed command"},
    )
    assert conflict.status_code == 409
    stopped = client.post(
        f"/api/time-entries/{first.json()['id']}/stop", headers=auth_headers
    )
    repeated_stop = client.post(
        f"/api/time-entries/{first.json()['id']}/stop", headers=auth_headers
    )
    assert stopped.json() == repeated_stop.json()

    entry_ids = []
    for description in ("First", "Second"):
        entry = client.post(
            "/api/time-entries",
            headers=auth_headers,
            json={
                "client_id": customer["id"],
                "date": "2026-08-13",
                "description": description,
                "duration_minutes": 60,
            },
        )
        entry_ids.append(entry.json()["id"])
    invoice_headers = {**auth_headers, "Idempotency-Key": "invoice-request-1"}
    invoice_payload = {
        "client_id": customer["id"],
        "time_entry_ids": [entry_ids[0]],
        "tax_rate": "0",
    }
    invoice = client.post(
        "/api/invoices", headers=invoice_headers, json=invoice_payload
    )
    repeated_invoice = client.post(
        "/api/invoices", headers=invoice_headers, json=invoice_payload
    )
    assert invoice.status_code == repeated_invoice.status_code == 200
    assert invoice.json()["id"] == repeated_invoice.json()["id"]
    mismatch = client.post(
        "/api/invoices",
        headers=invoice_headers,
        json={
            "client_id": customer["id"],
            "time_entry_ids": [entry_ids[1]],
            "tax_rate": "0",
        },
    )
    assert mismatch.status_code == 409


def test_health_readiness_security_headers_structured_errors_and_rate_limit(
    client: TestClient, monkeypatch
):
    health = client.get("/api/health")
    assert health.json() == {"status": "ok"}
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"
    assert health.headers["x-request-id"]
    readiness = client.get("/api/ready")
    assert readiness.status_code == 200
    assert readiness.json()["status"] == "ready"
    assert readiness.json()["expected_schema_revision"] == "0006_pilot_safety"

    invalid = client.post("/api/auth/login", json={})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
    assert invalid.json()["request_id"]

    monkeypatch.setattr(settings, "login_rate_limit_per_minute", 2)
    limiter.reset()
    for expected in (401, 401, 429):
        response = client.post(
            "/api/auth/login",
            json={"username": "test-admin", "password": "wrong"},
        )
        assert response.status_code == expected
    assert response.json()["detail"]["code"] == "rate_limit_exceeded"
    assert int(response.headers["retry-after"]) >= 1

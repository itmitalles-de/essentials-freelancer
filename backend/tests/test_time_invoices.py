import os
import smtplib
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from app.models import CompanySettings, Invoice, TimeEntry
from app.config import settings
from app.time_utils import utc_now_naive


def create_client(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/clients",
        headers=headers,
        json={
            "name": "Example Consulting",
            "contact_person": "Erika Example",
            "email": "billing@example.invalid",
            "hourly_rate": "80.00",
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def create_time_entry(
    client: TestClient, headers: dict[str, str], client_id: int, minutes: int = 90
) -> int:
    response = client.post(
        "/api/time-entries",
        headers=headers,
        json={
            "client_id": client_id,
            "date": "2026-08-13",
            "description": "Synthetic implementation work",
            "duration_minutes": minutes,
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def create_invoice(
    client: TestClient,
    headers: dict[str, str],
    client_id: int,
    entry_id: int,
    due_in_days: int | None = None,
):
    payload = {"client_id": client_id, "time_entry_ids": [entry_id]}
    if due_in_days is not None:
        payload["due_in_days"] = due_in_days
    response = client.post("/api/invoices", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    return response


def test_manual_time_timer_and_single_running_constraint(
    client: TestClient, auth_headers: dict[str, str], db_session
):
    client_id = create_client(client, auth_headers)
    manual_id = create_time_entry(client, auth_headers, client_id)

    manual = client.get("/api/time-entries", headers=auth_headers).json()[0]
    assert manual["id"] == manual_id
    assert manual["hourly_rate"] == "80.00"

    started = client.post(
        "/api/time-entries/start",
        headers=auth_headers,
        json={"client_id": client_id, "description": "Synthetic timer"},
    )
    assert started.status_code == 200
    timer_id = started.json()["id"]

    second = client.post(
        "/api/time-entries/start",
        headers=auth_headers,
        json={"client_id": client_id, "description": "Second timer"},
    )
    assert second.status_code == 400

    timer = db_session.get(TimeEntry, timer_id)
    timer.running_started_at = utc_now_naive() - timedelta(seconds=90)
    db_session.commit()
    stopped = client.post(
        f"/api/time-entries/{timer_id}/stop", headers=auth_headers
    )
    assert stopped.status_code == 200
    assert stopped.json()["duration_minutes"] >= 1
    assert stopped.json()["running_started_at"] is None


def test_invoice_pdf_status_and_delete_flow(
    client: TestClient, auth_headers: dict[str, str], db_session, monkeypatch
):
    client_id = create_client(client, auth_headers)
    entry_id = create_time_entry(client, auth_headers, client_id)
    response = create_invoice(
        client, auth_headers, client_id, entry_id, due_in_days=0
    )
    invoice = response.json()

    assert invoice["invoice_number"].startswith(f"RE-{date.today().year}-")
    assert invoice["issue_date"] == invoice["due_date"]
    assert Decimal(invoice["total"]) == Decimal("120.00")
    assert len(invoice["line_items"]) == 1

    pdf = client.get(f"/api/invoices/{invoice['id']}/pdf", headers=auth_headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content.startswith(b"%PDF-")

    billed_entry = db_session.get(TimeEntry, entry_id)
    db_session.refresh(billed_entry)
    assert billed_entry.billed is True
    assert billed_entry.invoice_id == invoice["id"]

    invalid_status = client.put(
        f"/api/invoices/{invoice['id']}/status",
        headers=auth_headers,
        json={"status": "paid"},
    )
    assert invalid_status.status_code == 400

    missing_smtp = client.post(
        f"/api/invoices/{invoice['id']}/send", headers=auth_headers
    )
    assert missing_smtp.status_code == 409
    assert missing_smtp.json()["detail"]["code"] == "module_unavailable"
    db_session.expire_all()
    assert db_session.get(Invoice, invoice["id"]).status.value == "draft"

    monkeypatch.setattr(
        "app.routers.invoices.send_invoice_email", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.invalid")
    monkeypatch.setattr(settings, "smtp_from", "sender@example.invalid")
    enabled = client.post(
        "/api/admin/modules/communication.smtp/enable", headers=auth_headers
    )
    assert enabled.status_code == 200
    assert enabled.json()["state"] == "enabled"
    sent = client.post(
        f"/api/invoices/{invoice['id']}/send", headers=auth_headers
    )
    assert sent.status_code == 200
    assert sent.json()["status"] == "sent"

    paid = client.put(
        f"/api/invoices/{invoice['id']}/status",
        headers=auth_headers,
        json={"status": "paid"},
    )
    assert paid.status_code == 200
    assert paid.json()["paid_at"] is not None

    cannot_delete = client.delete(
        f"/api/invoices/{invoice['id']}", headers=auth_headers
    )
    assert cannot_delete.status_code == 400


def test_smtp_failure_keeps_invoice_as_draft(
    client: TestClient, auth_headers: dict[str, str], db_session, monkeypatch
):
    client_id = create_client(client, auth_headers)
    entry_id = create_time_entry(client, auth_headers, client_id, 60)
    invoice = create_invoice(client, auth_headers, client_id, entry_id).json()

    def fail_smtp(*args, **kwargs):
        raise smtplib.SMTPException("synthetic SMTP failure")

    monkeypatch.setattr("app.routers.invoices.send_invoice_email", fail_smtp)
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.invalid")
    monkeypatch.setattr(settings, "smtp_from", "sender@example.invalid")
    assert (
        client.post(
            "/api/admin/modules/communication.smtp/enable", headers=auth_headers
        ).status_code
        == 200
    )
    failed = client.post(
        f"/api/invoices/{invoice['id']}/send", headers=auth_headers
    )
    assert failed.status_code == 502
    db_session.expire_all()
    stored = db_session.get(Invoice, invoice["id"])
    assert stored.status.value == "draft"
    assert stored.sent_at is None


def test_deleting_draft_unbills_time_and_missing_pdf_is_404(
    client: TestClient, auth_headers: dict[str, str], db_session
):
    client_id = create_client(client, auth_headers)
    entry_id = create_time_entry(client, auth_headers, client_id)
    invoice = create_invoice(client, auth_headers, client_id, entry_id).json()
    stored = db_session.get(Invoice, invoice["id"])
    os.remove(stored.pdf_path)

    missing = client.get(
        f"/api/invoices/{invoice['id']}/pdf", headers=auth_headers
    )
    assert missing.status_code == 404

    deleted = client.delete(
        f"/api/invoices/{invoice['id']}", headers=auth_headers
    )
    assert deleted.status_code == 204
    db_session.expire_all()
    entry = db_session.get(TimeEntry, entry_id)
    assert entry.billed is False
    assert entry.invoice_id is None


def test_invoice_request_rejects_duplicate_entries(
    client: TestClient, auth_headers: dict[str, str]
):
    client_id = create_client(client, auth_headers)
    entry_id = create_time_entry(client, auth_headers, client_id)
    response = client.post(
        "/api/invoices",
        headers=auth_headers,
        json={"client_id": client_id, "time_entry_ids": [entry_id, entry_id]},
    )
    assert response.status_code == 422


def test_pdf_failure_rolls_back_invoice_and_time_entry(
    client: TestClient, auth_headers: dict[str, str], db_session, monkeypatch
):
    client_id = create_client(client, auth_headers)
    entry_id = create_time_entry(client, auth_headers, client_id)

    def fail_pdf(*args, **kwargs):
        raise OSError("synthetic PDF storage failure")

    monkeypatch.setattr("app.routers.invoices.generate_invoice_pdf", fail_pdf)
    response = client.post(
        "/api/invoices",
        headers=auth_headers,
        json={"client_id": client_id, "time_entry_ids": [entry_id]},
    )

    assert response.status_code == 500
    db_session.expire_all()
    entry = db_session.get(TimeEntry, entry_id)
    company = db_session.get(CompanySettings, 1)
    assert entry.billed is False
    assert entry.invoice_id is None
    assert db_session.query(Invoice).count() == 0
    assert company.next_invoice_number == 1

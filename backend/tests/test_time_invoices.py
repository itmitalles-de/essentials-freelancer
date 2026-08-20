import os
import smtplib
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
import pytest

from app.models import CompanySettings, Invoice, TimeEntry
from app.config import settings
from app.time_utils import utc_now_naive


def create_client(
    client: TestClient,
    headers: dict[str, str],
    hourly_rate: str = "80.00",
) -> int:
    response = client.post(
        "/api/clients",
        headers=headers,
        json={
            "name": "Example Consulting",
            "contact_person": "Erika Example",
            "email": "billing@example.invalid",
            "hourly_rate": hourly_rate,
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
    payload = {
        "client_id": client_id,
        "time_entry_ids": [entry_id],
        "tax_rate": "0",
    }
    if due_in_days is not None:
        payload["due_in_days"] = due_in_days
    preview = client.post("/api/invoices/preview", headers=headers, json=payload)
    assert preview.status_code == 200, preview.text
    payload.update(
        {
            "billing_confirmation_token": preview.json()["confirmation_token"],
            "billing_confirmed": True,
        }
    )
    response = client.post("/api/invoices", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    return response


def send_confirmation(
    client: TestClient,
    headers: dict[str, str],
    invoice: dict,
    key: str,
    *,
    resend: bool = False,
    pdf_reviewed: bool = True,
    recipient: str = "billing@example.invalid",
):
    return client.post(
        f"/api/invoices/{invoice['id']}/send",
        headers={**headers, "Idempotency-Key": key},
        json={
            "recipient": recipient,
            "invoice_number": invoice["invoice_number"],
            "total": invoice["total"],
            "pdf_reviewed": pdf_reviewed,
            "resend": resend,
        },
    )


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


def test_tax_status_is_explicit_and_fresh_footer_is_empty(
    client: TestClient, auth_headers: dict[str, str]
):
    company = client.get("/api/settings", headers=auth_headers)
    assert company.status_code == 200
    assert company.json()["invoice_footer_note"] == ""

    client_id = create_client(client, auth_headers)
    entry_id = create_time_entry(client, auth_headers, client_id)
    missing_tax = client.post(
        "/api/invoices",
        headers=auth_headers,
        json={"client_id": client_id, "time_entry_ids": [entry_id]},
    )
    assert missing_tax.status_code == 422


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

    missing_smtp = send_confirmation(
        client, auth_headers, invoice, "missing-smtp"
    )
    assert missing_smtp.status_code == 409
    assert missing_smtp.json()["detail"]["code"] == "pilot_module_locked"
    db_session.expire_all()
    assert db_session.get(Invoice, invoice["id"]).status.value == "draft"

    enabled = client.post(
        "/api/admin/modules/communication.smtp/enable", headers=auth_headers
    )
    assert enabled.status_code == 409
    assert enabled.json()["detail"]["code"] == "pilot_module_locked"

    unconfirmed_manual = client.put(
        f"/api/invoices/{invoice['id']}/status",
        headers=auth_headers,
        json={"status": "sent"},
    )
    assert unconfirmed_manual.status_code == 400
    sent = client.put(
        f"/api/invoices/{invoice['id']}/status",
        headers=auth_headers,
        json={
            "status": "sent",
            "pdf_reviewed": True,
            "manual_delivery_confirmed": True,
        },
    )
    assert sent.status_code == 200
    assert sent.json()["status"] == "sent"
    assert sent.json()["sent_at"] is not None
    assert client.get(
        f"/api/invoices/{invoice['id']}/send-attempts", headers=auth_headers
    ).json() == []

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
        == 409
    )
    failed = send_confirmation(client, auth_headers, invoice, "failed-send")
    assert failed.status_code == 409
    assert failed.json()["detail"]["code"] == "pilot_module_locked"
    db_session.expire_all()
    stored = db_session.get(Invoice, invoice["id"])
    assert stored.status.value == "draft"
    assert stored.sent_at is None


@pytest.mark.parametrize(
    "smtp_error",
    [
        TimeoutError("synthetic SMTP timeout"),
        smtplib.SMTPRecipientsRefused(
            {"billing@example.invalid": (550, b"synthetic rejection")}
        ),
        smtplib.SMTPAuthenticationError(535, b"synthetic authentication failure"),
        smtplib.SMTPServerDisconnected("synthetic connection loss"),
    ],
    ids=["timeout", "recipient-rejection", "authentication", "disconnect"],
)
def test_specific_smtp_failures_never_mark_invoice_sent(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
    monkeypatch,
    smtp_error: Exception,
):
    client_id = create_client(client, auth_headers)
    entry_id = create_time_entry(client, auth_headers, client_id, 60)
    invoice = create_invoice(client, auth_headers, client_id, entry_id).json()

    def fail_smtp(*args, **kwargs):
        raise smtp_error

    monkeypatch.setattr("app.routers.invoices.send_invoice_email", fail_smtp)
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.invalid")
    monkeypatch.setattr(settings, "smtp_from", "sender@example.invalid")
    assert client.post(
        "/api/admin/modules/communication.smtp/enable", headers=auth_headers
    ).status_code == 409

    failed = send_confirmation(
        client, auth_headers, invoice, f"failed-{type(smtp_error).__name__}"
    )
    assert failed.status_code == 409
    assert failed.json()["detail"]["code"] == "pilot_module_locked"
    db_session.expire_all()
    stored = db_session.get(Invoice, invoice["id"])
    assert stored.status.value == "draft"
    assert stored.sent_at is None


def test_send_requires_review_and_matching_confirmation(
    client: TestClient, auth_headers: dict[str, str], monkeypatch
):
    client_id = create_client(client, auth_headers)
    entry_id = create_time_entry(client, auth_headers, client_id)
    invoice = create_invoice(client, auth_headers, client_id, entry_id).json()
    calls: list[str] = []

    def send_email(*args, **kwargs):
        calls.append("sent")
        return "<review-test@example.invalid>"

    monkeypatch.setattr("app.routers.invoices.send_invoice_email", send_email)
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.invalid")
    monkeypatch.setattr(settings, "smtp_from", "sender@example.invalid")
    assert client.post(
        "/api/admin/modules/communication.smtp/enable", headers=auth_headers
    ).status_code == 409

    not_reviewed = send_confirmation(
        client, auth_headers, invoice, "not-reviewed", pdf_reviewed=False
    )
    assert not_reviewed.status_code == 409
    wrong_recipient = send_confirmation(
        client,
        auth_headers,
        invoice,
        "wrong-recipient",
        recipient="other@example.invalid",
    )
    assert wrong_recipient.status_code == 409
    assert wrong_recipient.json()["detail"]["code"] == "pilot_module_locked"
    assert calls == []


def test_partial_smtp_auth_configuration_never_sends(
    client: TestClient, auth_headers: dict[str, str], db_session, monkeypatch
):
    client_id = create_client(client, auth_headers)
    entry_id = create_time_entry(client, auth_headers, client_id)
    invoice = create_invoice(client, auth_headers, client_id, entry_id).json()
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.invalid")
    monkeypatch.setattr(settings, "smtp_from", "sender@example.invalid")
    monkeypatch.setattr(settings, "smtp_user", "configured-without-password")
    monkeypatch.setattr(settings, "smtp_password", "")
    assert client.post(
        "/api/admin/modules/communication.smtp/enable", headers=auth_headers
    ).status_code == 409

    failed = send_confirmation(client, auth_headers, invoice, "partial-smtp-auth")
    assert failed.status_code == 409
    assert failed.json()["detail"]["code"] == "pilot_module_locked"
    db_session.expire_all()
    stored = db_session.get(Invoice, invoice["id"])
    assert stored.status.value == "draft"
    assert stored.sent_at is None


def test_smtp_lock_preserves_manually_sent_state(
    client: TestClient, auth_headers: dict[str, str], db_session
):
    client_id = create_client(client, auth_headers)
    entry_id = create_time_entry(client, auth_headers, client_id)
    invoice = create_invoice(client, auth_headers, client_id, entry_id).json()
    sent = client.put(
        f"/api/invoices/{invoice['id']}/status",
        headers=auth_headers,
        json={
            "status": "sent",
            "pdf_reviewed": True,
            "manual_delivery_confirmed": True,
        },
    )
    assert sent.status_code == 200
    original_sent_at = sent.json()["sent_at"]

    failed = send_confirmation(
        client, auth_headers, sent.json(), "failed-resend", resend=True
    )
    assert failed.status_code == 409
    assert failed.json()["detail"]["code"] == "pilot_module_locked"
    db_session.expire_all()
    stored = db_session.get(Invoice, invoice["id"])
    assert stored.status.value == "sent"
    assert stored.sent_at.isoformat() == original_sent_at
    attempts = client.get(
        f"/api/invoices/{invoice['id']}/send-attempts", headers=auth_headers
    ).json()
    assert attempts == []


@pytest.mark.parametrize(
    ("minutes", "expected_quantity", "expected_total"),
    [
        (1, "0.2500", "30.86"),
        (16, "0.5000", "61.73"),
        (31, "0.7500", "92.59"),
        (59, "1.0000", "123.45"),
    ],
)
def test_invoice_uses_confirmed_billable_minutes_for_amount(
    client: TestClient,
    auth_headers: dict[str, str],
    minutes: int,
    expected_quantity: str,
    expected_total: str,
):
    client_id = create_client(client, auth_headers, hourly_rate="123.45")
    entry_id = create_time_entry(client, auth_headers, client_id, minutes)
    invoice = create_invoice(client, auth_headers, client_id, entry_id).json()
    line = invoice["line_items"][0]
    assert line["quantity"] == expected_quantity
    assert line["net_amount"] == expected_total
    assert line["amount"] == expected_total
    assert line["snapshot_actual_minutes"] == minutes
    assert line["snapshot_billable_minutes"] in {15, 30, 45, 60}
    assert line["snapshot_increment_minutes"] == 15
    assert invoice["subtotal"] == expected_total
    assert invoice["total"] == expected_total


@pytest.mark.parametrize("initial_status", ["draft", "sent"])
def test_cancelled_invoices_are_terminal(
    client: TestClient,
    auth_headers: dict[str, str],
    initial_status: str,
):
    client_id = create_client(client, auth_headers)
    entry_id = create_time_entry(client, auth_headers, client_id)
    invoice = create_invoice(client, auth_headers, client_id, entry_id).json()
    if initial_status == "sent":
        invoice = client.put(
            f"/api/invoices/{invoice['id']}/status",
            headers=auth_headers,
            json={
                "status": "sent",
                "pdf_reviewed": True,
                "manual_delivery_confirmed": True,
            },
        ).json()

    cancelled = client.put(
        f"/api/invoices/{invoice['id']}/status",
        headers=auth_headers,
        json={"status": "cancelled"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert client.put(
        f"/api/invoices/{invoice['id']}/status",
        headers=auth_headers,
        json={"status": "paid"},
    ).status_code == 400


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
    cannot_confirm_delivery = client.put(
        f"/api/invoices/{invoice['id']}/status",
        headers=auth_headers,
        json={
            "status": "sent",
            "pdf_reviewed": True,
            "manual_delivery_confirmed": True,
        },
    )
    assert cannot_confirm_delivery.status_code == 400

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
        json={
            "client_id": client_id,
            "time_entry_ids": [entry_id, entry_id],
            "tax_rate": "0",
        },
    )
    assert response.status_code == 422


def test_pdf_failure_rolls_back_invoice_and_time_entry(
    client: TestClient, auth_headers: dict[str, str], db_session, monkeypatch
):
    client_id = create_client(client, auth_headers)
    entry_id = create_time_entry(client, auth_headers, client_id)

    def fail_pdf(*args, **kwargs):
        raise OSError("synthetic PDF storage failure")

    payload = {"client_id": client_id, "time_entry_ids": [entry_id], "tax_rate": "0"}
    preview = client.post("/api/invoices/preview", headers=auth_headers, json=payload)
    assert preview.status_code == 200
    payload.update(
        {
            "billing_confirmation_token": preview.json()["confirmation_token"],
            "billing_confirmed": True,
        }
    )
    monkeypatch.setattr("app.routers.invoices.generate_invoice_pdf", fail_pdf)
    response = client.post(
        "/api/invoices",
        headers=auth_headers,
        json=payload,
    )

    assert response.status_code == 500
    db_session.expire_all()
    entry = db_session.get(TimeEntry, entry_id)
    company = db_session.get(CompanySettings, 1)
    assert entry.billed is False
    assert entry.invoice_id is None
    assert db_session.query(Invoice).count() == 0
    assert company.next_invoice_number == 1

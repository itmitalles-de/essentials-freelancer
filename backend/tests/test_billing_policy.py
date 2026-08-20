from __future__ import annotations

from datetime import date
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from fastapi.testclient import TestClient

from app.models import Invoice, TimeEntry


def create_client(
    client: TestClient,
    headers: dict[str, str],
    *,
    rate_type: str = "private",
    hourly_rate: str | None = None,
) -> dict:
    response = client.post(
        "/api/clients",
        headers=headers,
        json={
            "name": f"{rate_type.title()} billing client",
            "billing_rate_type": rate_type,
            "hourly_rate": hourly_rate,
            "default_service_mode": "remote",
            "billing_profile_confirmed": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def create_project(
    client: TestClient,
    headers: dict[str, str],
    client_id: int,
    **overrides,
) -> dict:
    payload = {
        "client_id": client_id,
        "name": "Billing project",
        "default_service_mode": "remote",
        "billing_profile_confirmed": True,
    }
    payload.update(overrides)
    response = client.post("/api/projects", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def create_time(
    client: TestClient,
    headers: dict[str, str],
    client_id: int,
    minutes: int,
    **overrides,
) -> dict:
    payload = {
        "client_id": client_id,
        "date": "2026-08-20",
        "description": "Billing policy test",
        "duration_minutes": minutes,
        "service_mode": "remote",
        "is_first_order": False,
        "travel_actual_minutes": 0,
    }
    payload.update(overrides)
    response = client.post("/api/time-entries", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def preview_and_create(
    client: TestClient,
    headers: dict[str, str],
    client_id: int,
    entry_ids: list[int],
) -> tuple[dict, dict]:
    payload = {
        "client_id": client_id,
        "time_entry_ids": entry_ids,
        "tax_rate": "0",
    }
    preview = client.post("/api/invoices/preview", headers=headers, json=payload)
    assert preview.status_code == 200, preview.text
    payload.update(
        {
            "billing_confirmation_token": preview.json()["confirmation_token"],
            "billing_confirmed": True,
        }
    )
    invoice = client.post("/api/invoices", headers=headers, json=payload)
    assert invoice.status_code == 200, invoice.text
    return preview.json(), invoice.json()


def work_line(preview: dict) -> dict:
    return next(line for line in preview["lines"] if line["line_kind"] == "work")


def travel_line(preview: dict) -> dict:
    return next(line for line in preview["lines"] if line["line_kind"] == "travel")


def test_private_remote_follow_up_one_minute_is_fifteen_at_fifty(
    client: TestClient, auth_headers: dict[str, str]
):
    customer = create_client(client, auth_headers)
    assert customer["hourly_rate"] == "50.00"
    entry = create_time(client, auth_headers, customer["id"], 1)
    assert entry["actual_minutes"] == 1
    assert entry["billable_minutes"] == 15
    assert entry["hourly_rate"] == "50.00"
    preview, invoice = preview_and_create(
        client, auth_headers, customer["id"], [entry["id"]]
    )
    line = work_line(preview)
    assert line["actual_minutes"] == 1
    assert line["billable_minutes"] == 15
    assert line["increment_minutes"] == 15
    assert line["minimum_minutes"] == 0
    assert line["net_amount"] == "12.50"
    assert invoice["total"] == "12.50"


def test_private_remote_follow_up_sixteen_minutes_is_thirty(
    client: TestClient, auth_headers: dict[str, str]
):
    customer = create_client(client, auth_headers)
    project = create_project(client, auth_headers, customer["id"])
    entry = create_time(
        client,
        auth_headers,
        customer["id"],
        16,
        project_id=project["id"],
    )
    assert entry["billable_minutes"] == 30


def test_business_remote_follow_up_thirty_one_minutes_is_forty_five_at_seventy_five(
    client: TestClient, auth_headers: dict[str, str]
):
    customer = create_client(client, auth_headers, rate_type="business")
    entry = create_time(client, auth_headers, customer["id"], 31)
    assert entry["billable_minutes"] == 45
    assert entry["hourly_rate"] == "75.00"
    preview, _ = preview_and_create(
        client, auth_headers, customer["id"], [entry["id"]]
    )
    assert work_line(preview)["net_amount"] == "56.25"


def test_first_order_ten_minutes_bills_sixty(
    client: TestClient, auth_headers: dict[str, str]
):
    customer = create_client(client, auth_headers)
    entry = create_time(
        client, auth_headers, customer["id"], 10, is_first_order=True
    )
    assert entry["billable_minutes"] == 60
    assert entry["applied_minimum_minutes"] == 60
    assert entry["applied_increment_minutes"] is None


def test_onsite_twenty_minutes_bills_sixty(
    client: TestClient, auth_headers: dict[str, str]
):
    customer = create_client(client, auth_headers)
    entry = create_time(
        client, auth_headers, customer["id"], 20, service_mode="onsite"
    )
    assert entry["billable_minutes"] == 60
    assert entry["billing_reason"] == "onsite_or_travel_minimum"


def test_travel_ten_minutes_bills_thirty_at_thirty_per_hour(
    client: TestClient, auth_headers: dict[str, str]
):
    customer = create_client(client, auth_headers)
    entry = create_time(
        client,
        auth_headers,
        customer["id"],
        20,
        service_mode="remote",
        travel_actual_minutes=10,
    )
    assert entry["billable_minutes"] == 60
    assert entry["travel_billable_minutes"] == 30
    assert entry["travel_hourly_rate"] == "30.00"
    preview, invoice = preview_and_create(
        client, auth_headers, customer["id"], [entry["id"]]
    )
    travel = travel_line(preview)
    assert travel["actual_minutes"] == 10
    assert travel["billable_minutes"] == 30
    assert travel["net_amount"] == "15.00"
    assert invoice["subtotal"] == "65.00"


def test_travel_thirty_minutes_costs_fifteen_and_no_increment_is_invented(
    client: TestClient, auth_headers: dict[str, str]
):
    customer = create_client(client, auth_headers)
    entry = create_time(
        client,
        auth_headers,
        customer["id"],
        60,
        service_mode="onsite",
        travel_actual_minutes=30,
    )
    preview, _ = preview_and_create(
        client, auth_headers, customer["id"], [entry["id"]]
    )
    travel = travel_line(preview)
    assert travel["billable_minutes"] == 30
    assert travel["increment_minutes"] is None
    assert travel["net_amount"] == "15.00"

    second_customer = create_client(client, auth_headers, hourly_rate="50.00")
    second_entry = create_time(
        client,
        auth_headers,
        second_customer["id"],
        60,
        service_mode="onsite",
        travel_actual_minutes=31,
    )
    assert second_entry["travel_billable_minutes"] == 31


def test_travel_increment_is_used_only_after_explicit_configuration(
    client: TestClient, auth_headers: dict[str, str]
):
    settings = client.get("/api/settings", headers=auth_headers).json()
    settings["travel_increment_minutes"] = 15
    for output_only in ("next_invoice_number", "next_quote_number", "has_logo"):
        settings.pop(output_only, None)
    updated = client.put("/api/settings", headers=auth_headers, json=settings)
    assert updated.status_code == 200, updated.text

    customer = create_client(client, auth_headers)
    entry = create_time(
        client,
        auth_headers,
        customer["id"],
        60,
        service_mode="onsite",
        travel_actual_minutes=31,
    )
    assert entry["travel_actual_minutes"] == 31
    assert entry["travel_billable_minutes"] == 45
    assert entry["travel_increment_minutes"] == 15
    assert entry["travel_billing_reason"] == "travel_configured_increment"


def test_project_override_and_custom_rate_are_snapshotted(
    client: TestClient, auth_headers: dict[str, str]
):
    private_customer = create_client(client, auth_headers)
    project = create_project(
        client,
        auth_headers,
        private_customer["id"],
        billing_rate_type_override="business",
        hourly_rate="75.00",
    )
    project_entry = create_time(
        client,
        auth_headers,
        private_customer["id"],
        15,
        project_id=project["id"],
    )
    assert project_entry["hourly_rate"] == "75.00"
    assert project_entry["billing_rate_source"] == "project_rate_override"

    custom_customer = create_client(
        client, auth_headers, rate_type="custom", hourly_rate="99.99"
    )
    custom_entry = create_time(client, auth_headers, custom_customer["id"], 15)
    preview, _ = preview_and_create(
        client, auth_headers, custom_customer["id"], [custom_entry["id"]]
    )
    custom_line = work_line(preview)
    assert custom_line["hourly_rate"] == "99.99"
    assert custom_line["net_amount"] == "25.00"


def test_individual_project_without_override_uses_business_rate(
    client: TestClient, auth_headers: dict[str, str]
):
    private_customer = create_client(client, auth_headers)
    project = create_project(
        client,
        auth_headers,
        private_customer["id"],
        is_individual_project=True,
        hourly_rate=None,
        billing_rate_type_override=None,
    )
    entry = create_time(
        client,
        auth_headers,
        private_customer["id"],
        31,
        project_id=project["id"],
    )
    assert entry["hourly_rate"] == "75.00"
    assert entry["billing_rate_type"] == "business"
    assert entry["billing_rate_source"] == "individual_project"
    assert entry["billable_minutes"] == 45


def test_quote_creation_is_free_and_never_creates_time(
    client: TestClient, auth_headers: dict[str, str], db_session
):
    customer = create_client(client, auth_headers)
    before = db_session.query(TimeEntry).count()
    quote = client.post(
        "/api/quotes",
        headers=auth_headers,
        json={
            "client_id": customer["id"],
            "valid_in_days": 14,
            "line_items": [
                {
                    "description": "Kostenlos erstellter Kostenvoranschlag",
                    "quantity": "1",
                    "unit": "flat",
                    "unit_price": "0",
                    "tax_rate": "0",
                }
            ],
        },
    )
    assert quote.status_code == 200, quote.text
    db_session.expire_all()
    assert db_session.query(TimeEntry).count() == before


def test_invoice_and_policy_snapshot_survive_later_rate_changes(
    client: TestClient, auth_headers: dict[str, str], db_session
):
    customer = create_client(client, auth_headers)
    project = create_project(client, auth_headers, customer["id"])
    entry = create_time(
        client,
        auth_headers,
        customer["id"],
        16,
        project_id=project["id"],
    )
    original_policy = entry["billing_policy_id"]
    preview, invoice = preview_and_create(
        client, auth_headers, customer["id"], [entry["id"]]
    )
    stored = db_session.get(Invoice, invoice["id"])
    original_pdf_hash = sha256(Path(stored.pdf_path).read_bytes()).hexdigest()

    customer.update({"hourly_rate": "75.00", "billing_rate_type": "business"})
    changed = client.put(
        f"/api/clients/{customer['id']}", headers=auth_headers, json=customer
    )
    assert changed.status_code == 200, changed.text
    renamed_project = client.put(
        f"/api/projects/{project['id']}",
        headers=auth_headers,
        json={
            "client_id": customer["id"],
            "name": "Renamed after invoicing",
            "description": "",
            "hourly_rate": "75.00",
            "billing_rate_type_override": "business",
            "default_service_mode": "remote",
            "is_individual_project": False,
            "billing_profile_confirmed": True,
            "active": True,
        },
    )
    assert renamed_project.status_code == 200, renamed_project.text

    fetched = client.get(f"/api/invoices/{invoice['id']}", headers=auth_headers).json()
    line = fetched["line_items"][0]
    assert fetched["total"] == invoice["total"] == "25.00"
    assert line["snapshot_hourly_rate"] == "50.00"
    assert line["snapshot_billable_minutes"] == 30
    assert line["snapshot_billing_policy_id"] == original_policy
    assert line["snapshot_project_name"] == "Billing project"
    assert work_line(preview)["billing_policy_id"] == original_policy
    assert sha256(Path(stored.pdf_path).read_bytes()).hexdigest() == original_pdf_hash


def test_stale_preview_cannot_create_invoice(
    client: TestClient, auth_headers: dict[str, str]
):
    customer = create_client(client, auth_headers)
    entry = create_time(client, auth_headers, customer["id"], 1)
    payload = {
        "client_id": customer["id"],
        "time_entry_ids": [entry["id"]],
        "tax_rate": "0",
    }
    preview = client.post("/api/invoices/preview", headers=auth_headers, json=payload)
    assert preview.status_code == 200
    changed = client.put(
        f"/api/time-entries/{entry['id']}",
        headers=auth_headers,
        json={"duration_minutes": 16},
    )
    assert changed.status_code == 200
    response = client.post(
        "/api/invoices",
        headers=auth_headers,
        json={
            **payload,
            "billing_confirmation_token": preview.json()["confirmation_token"],
            "billing_confirmed": True,
        },
    )
    assert response.status_code == 409


def test_migrated_unbilled_time_requires_visible_profile_confirmation(
    client: TestClient, auth_headers: dict[str, str], db_session
):
    customer_response = client.post(
        "/api/clients",
        headers=auth_headers,
        json={
            "name": "Migrated customer",
            "hourly_rate": "50.00",
            "billing_rate_type": "custom",
            "default_service_mode": "remote",
            "billing_profile_confirmed": False,
        },
    )
    assert customer_response.status_code == 200, customer_response.text
    customer = customer_response.json()
    project_response = client.post(
        "/api/projects",
        headers=auth_headers,
        json={
            "client_id": customer["id"],
            "name": "Migrated project",
            "hourly_rate": "75.00",
            "billing_rate_type_override": "custom",
            "default_service_mode": "remote",
            "billing_profile_confirmed": False,
        },
    )
    assert project_response.status_code == 200, project_response.text
    project = project_response.json()
    entry = TimeEntry(
        client_id=customer["id"],
        project_id=project["id"],
        date=date(2026, 8, 20),
        description="Migrated open time",
        duration_minutes=16,
        hourly_rate=Decimal("84.25"),
        billed=False,
        billing_policy_applied=False,
        billing_policy_id="legacy-unconfirmed-v0",
        billing_reason="legacy_unconfirmed",
    )
    db_session.add(entry)
    db_session.commit()
    payload = {
        "client_id": customer["id"],
        "time_entry_ids": [entry.id],
        "tax_rate": "0",
    }

    blocked_client = client.post(
        "/api/invoices/preview", headers=auth_headers, json=payload
    )
    assert blocked_client.status_code == 409
    assert "Kunden" in blocked_client.json()["detail"]

    customer["billing_profile_confirmed"] = True
    confirmed_client = client.put(
        f"/api/clients/{customer['id']}", headers=auth_headers, json=customer
    )
    assert confirmed_client.status_code == 200, confirmed_client.text
    blocked_project = client.post(
        "/api/invoices/preview", headers=auth_headers, json=payload
    )
    assert blocked_project.status_code == 409
    assert "Projekts" in blocked_project.json()["detail"]

    project["billing_profile_confirmed"] = True
    confirmed_project = client.put(
        f"/api/projects/{project['id']}", headers=auth_headers, json=project
    )
    assert confirmed_project.status_code == 200, confirmed_project.text
    updated_entry = client.put(
        f"/api/time-entries/{entry.id}",
        headers=auth_headers,
        json={"duration_minutes": 31},
    )
    assert updated_entry.status_code == 200, updated_entry.text
    assert updated_entry.json()["billing_policy_applied"] is True
    assert updated_entry.json()["billing_rate_type"] == "custom"
    assert updated_entry.json()["billing_rate_source"] == "project_rate_override"
    assert updated_entry.json()["hourly_rate"] == "75.00"
    assert updated_entry.json()["billable_minutes"] == 45
    preview = client.post("/api/invoices/preview", headers=auth_headers, json=payload)
    assert preview.status_code == 200, preview.text
    assert work_line(preview.json())["billable_minutes"] == 45
    db_session.refresh(entry)
    assert entry.billing_policy_applied is True
    created = client.post(
        "/api/invoices",
        headers=auth_headers,
        json={
            **payload,
            "billing_confirmation_token": preview.json()["confirmation_token"],
            "billing_confirmed": True,
        },
    )
    assert created.status_code == 200, created.text
    db_session.refresh(entry)
    assert entry.billing_policy_applied is True
    assert entry.billable_minutes == 45


def test_explicit_zero_percent_small_business_profile_is_snapshotted(
    client: TestClient, auth_headers: dict[str, str]
):
    settings = client.get("/api/settings", headers=auth_headers).json()
    settings.update(
        {
            "default_tax_rate": "0",
            "small_business_notice_enabled": True,
            "small_business_notice_text": (
                "Gemäß § 19 UStG wird keine Umsatzsteuer berechnet."
            ),
        }
    )
    for output_only in ("next_invoice_number", "next_quote_number", "has_logo"):
        settings.pop(output_only, None)
    updated = client.put("/api/settings", headers=auth_headers, json=settings)
    assert updated.status_code == 200, updated.text

    customer = create_client(client, auth_headers)
    entry = create_time(client, auth_headers, customer["id"], 15)
    preview, invoice = preview_and_create(
        client, auth_headers, customer["id"], [entry["id"]]
    )
    assert preview["tax_status"] == "small_business_section_19"
    assert preview["tax_rate"] == "0"
    assert "§ 19 UStG" in preview["tax_notice"]
    assert invoice["tax_total"] == "0.00"
    assert invoice["tax_status_snapshot"] == "small_business_section_19"
    assert invoice["tax_notice_snapshot"] == preview["tax_notice"]


def test_small_business_notice_cannot_be_enabled_with_nonzero_tax(
    client: TestClient, auth_headers: dict[str, str]
):
    settings = client.get("/api/settings", headers=auth_headers).json()
    settings.update(
        {
            "default_tax_rate": "19.00",
            "small_business_notice_enabled": True,
            "small_business_notice_text": "Expliziter §-19-Hinweis",
        }
    )
    for output_only in ("next_invoice_number", "next_quote_number", "has_logo"):
        settings.pop(output_only, None)
    rejected = client.put("/api/settings", headers=auth_headers, json=settings)
    assert rejected.status_code == 422

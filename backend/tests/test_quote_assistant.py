from decimal import Decimal

from fastapi.testclient import TestClient

from app.models import QuoteAssistantDraft


def enable_assistant(client: TestClient, headers: dict[str, str]) -> None:
    response = client.post(
        "/api/admin/modules/sales.quote_assistant/enable", headers=headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "enabled"


def create_client_project(client: TestClient, headers: dict[str, str]) -> tuple[int, int]:
    client_id = client.post(
        "/api/clients",
        headers=headers,
        json={"name": "Synthetic Assistant Client", "email": "billing@example.invalid"},
    ).json()["id"]
    project_id = client.post(
        "/api/projects",
        headers=headers,
        json={"client_id": client_id, "name": "Synthetic Assistant Project"},
    ).json()["id"]
    return client_id, project_id


def create_catalog_item(
    client: TestClient,
    headers: dict[str, str],
    *,
    stable_key: str,
    kind: str,
    unit: str,
    price: str,
    tax_rate: str,
    valid_from: str = "2026-01-01",
    valid_until: str | None = None,
) -> dict:
    response = client.post(
        "/api/quote-assistant/catalog/items",
        headers=headers,
        json={
            "stable_key": stable_key,
            "kind": kind,
            "name": stable_key,
            "version": {
                "description": f"Synthetic {stable_key}",
                "unit": unit,
                "net_unit_price": price,
                "tax_rate": tax_rate,
                "valid_from": valid_from,
                "valid_until": valid_until,
            },
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def latest_version(item: dict) -> dict:
    return max(item["versions"], key=lambda version: version["version"])


def test_preview_rounding_tax_units_surcharge_and_discount(
    client: TestClient, auth_headers: dict[str, str]
):
    enable_assistant(client, auth_headers)
    service = create_catalog_item(
        client,
        auth_headers,
        stable_key="service.rounding",
        kind="service",
        unit="hours",
        price="0.50",
        tax_rate="0",
    )
    material = create_catalog_item(
        client,
        auth_headers,
        stable_key="material.standard",
        kind="material",
        unit="items",
        price="100.00",
        tax_rate="7",
    )
    travel = create_catalog_item(
        client,
        auth_headers,
        stable_key="travel.kilometres",
        kind="travel",
        unit="km",
        price="50.00",
        tax_rate="19",
    )
    response = client.post(
        "/api/quote-assistant/preview",
        headers=auth_headers,
        json={
            "pricing_date": "2026-06-01",
            "selections": [
                {"catalog_version_id": latest_version(service)["id"], "quantity": "0.03"},
                {"catalog_version_id": latest_version(material)["id"], "quantity": "2"},
                {"catalog_version_id": latest_version(travel)["id"], "quantity": "1"},
            ],
            "surcharge_percent": "10",
            "discount_percent": "5",
        },
    )
    assert response.status_code == 200, response.text
    preview = response.json()
    assert preview["lines"][0]["net_amount"] == "0.02"
    assert [line["unit"] for line in preview["lines"]] == ["hours", "items", "km"]
    assert [item["tax_rate"] for item in preview["tax_breakdown"]] == [
        "0.00",
        "7.00",
        "19.00",
    ]
    assert Decimal(preview["base_net_total"]) == Decimal("250.02")
    assert Decimal(preview["surcharge_amount"]) == Decimal("25.00")
    assert Decimal(preview["discount_amount"]) == Decimal("13.75")
    assert Decimal(preview["net_total"]) == Decimal("261.27")
    assert Decimal(preview["tax_total"]) == Decimal("24.56")
    assert Decimal(preview["total"]) == Decimal("285.83")
    assert preview["calculation_steps"][-1]["expression"] == "Netto + Steuer"


def test_expired_catalog_price_is_rejected(
    client: TestClient, auth_headers: dict[str, str]
):
    enable_assistant(client, auth_headers)
    expired = create_catalog_item(
        client,
        auth_headers,
        stable_key="service.expired",
        kind="service",
        unit="hours",
        price="80.00",
        tax_rate="19",
        valid_from="2025-01-01",
        valid_until="2025-12-31",
    )
    response = client.post(
        "/api/quote-assistant/preview",
        headers=auth_headers,
        json={
            "pricing_date": "2026-01-01",
            "selections": [
                {"catalog_version_id": latest_version(expired)["id"], "quantity": 1}
            ],
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "catalog_price_expired"


def test_package_and_template_versions_are_reusable_and_pinned(
    client: TestClient, auth_headers: dict[str, str]
):
    enable_assistant(client, auth_headers)
    service = create_catalog_item(
        client,
        auth_headers,
        stable_key="service.package",
        kind="service",
        unit="hours",
        price="75.00",
        tax_rate="19",
    )
    material = create_catalog_item(
        client,
        auth_headers,
        stable_key="material.package",
        kind="material",
        unit="items",
        price="25.00",
        tax_rate="7",
    )
    package = client.post(
        "/api/quote-assistant/packages",
        headers=auth_headers,
        json={
            "stable_key": "package.installation",
            "name": "Synthetic installation package",
            "version": {
                "description": "Initial package",
                "valid_from": "2026-01-01",
                "items": [
                    {"catalog_version_id": latest_version(service)["id"], "quantity": 2},
                    {"catalog_version_id": latest_version(material)["id"], "quantity": 3},
                ],
            },
        },
    )
    assert package.status_code == 200, package.text
    package_data = package.json()
    first_package_version = package_data["versions"][0]

    template = client.post(
        "/api/quote-assistant/templates",
        headers=auth_headers,
        json={
            "stable_key": "template.installation",
            "name": "Synthetic guided template",
            "version": {
                "description": "Guided initial version",
                "questions": ["Wo findet die Leistung statt?", "Wann soll sie beginnen?"],
                "selections": [
                    {"package_version_id": first_package_version["id"], "quantity": 1}
                ],
                "surcharge_percent": 5,
                "discount_percent": 0,
            },
        },
    )
    assert template.status_code == 200, template.text
    template_data = template.json()
    assert template_data["versions"][0]["questions"][0].startswith("Wo")

    second_package = client.post(
        f"/api/quote-assistant/packages/{package_data['id']}/versions",
        headers=auth_headers,
        json={
            "description": "Future package version",
            "valid_from": "2027-01-01",
            "items": [
                {"catalog_version_id": latest_version(service)["id"], "quantity": 4}
            ],
        },
    )
    assert second_package.status_code == 200, second_package.text
    assert [version["version"] for version in second_package.json()["versions"]] == [1, 2]
    listed_template = client.get(
        "/api/quote-assistant/templates", headers=auth_headers
    ).json()[0]
    assert listed_template["versions"][0]["selections"][0][
        "package_version_id"
    ] == first_package_version["id"]


def test_draft_snapshot_human_approval_transfer_and_one_time_invoice_conversion(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session,
):
    enable_assistant(client, auth_headers)
    client_id, project_id = create_client_project(client, auth_headers)
    item = create_catalog_item(
        client,
        auth_headers,
        stable_key="service.snapshot",
        kind="service",
        unit="hours",
        price="100.00",
        tax_rate="19",
    )
    first_version = latest_version(item)
    draft_response = client.post(
        "/api/quote-assistant/drafts",
        headers=auth_headers,
        json={
            "client_id": client_id,
            "project_id": project_id,
            "title": "Synthetic approved scope",
            "pricing_date": "2026-06-01",
            "guided_answers": {"location": "Synthetic workshop"},
            "notes": "Machine-verifiable assistant quote",
            "selections": [{"catalog_version_id": first_version["id"], "quantity": 2}],
            "surcharge_percent": 10,
            "discount_percent": 5,
        },
    )
    assert draft_response.status_code == 200, draft_response.text
    draft = draft_response.json()
    assert draft["status"] == "draft"
    assert draft["quote_id"] is None

    blocked_transfer = client.post(
        f"/api/quote-assistant/drafts/{draft['id']}/transfer", headers=auth_headers
    )
    assert blocked_transfer.status_code == 409
    assert blocked_transfer.json()["detail"]["code"] == "draft_not_approved"

    changed_catalog = client.post(
        f"/api/quote-assistant/catalog/items/{item['id']}/versions",
        headers=auth_headers,
        json={
            "description": "Synthetic future price",
            "unit": "hours",
            "net_unit_price": "250.00",
            "tax_rate": "19",
            "valid_from": "2027-01-01",
        },
    )
    assert changed_catalog.status_code == 200, changed_catalog.text
    unchanged = client.get(
        f"/api/quote-assistant/drafts/{draft['id']}", headers=auth_headers
    ).json()
    assert unchanged["lines"][0]["unit_price"] == "100.00"
    assert Decimal(unchanged["total"]) == Decimal("248.71")

    approved = client.post(
        f"/api/quote-assistant/drafts/{draft['id']}/approve", headers=auth_headers
    )
    assert approved.status_code == 200
    assert approved.json()["approved_at"] is not None
    assert client.post(
        f"/api/quote-assistant/drafts/{draft['id']}/approve", headers=auth_headers
    ).status_code == 200

    cannot_edit = client.put(
        f"/api/quote-assistant/drafts/{draft['id']}",
        headers=auth_headers,
        json={
            "client_id": client_id,
            "title": "Changed after approval",
            "pricing_date": "2026-06-01",
            "selections": [{"catalog_version_id": first_version["id"], "quantity": 1}],
        },
    )
    assert cannot_edit.status_code == 409

    transferred = client.post(
        f"/api/quote-assistant/drafts/{draft['id']}/transfer", headers=auth_headers
    )
    assert transferred.status_code == 200, transferred.text
    transferred_data = transferred.json()
    quote_id = transferred_data["quote_id"]
    assert transferred_data["status"] == "transferred"
    assert quote_id is not None
    repeated = client.post(
        f"/api/quote-assistant/drafts/{draft['id']}/transfer", headers=auth_headers
    )
    assert repeated.status_code == 200
    assert repeated.json()["quote_id"] == quote_id

    quote = client.get(f"/api/quotes/{quote_id}", headers=auth_headers).json()
    assert quote["status"] == "draft"
    assert Decimal(quote["subtotal"]) == Decimal("209.00")
    assert Decimal(quote["tax_total"]) == Decimal("39.71")
    assert Decimal(quote["total"]) == Decimal("248.71")
    assert [line["description"].split()[0] for line in quote["line_items"]] == [
        "Synthetic",
        "Aufschlag",
        "Rabatt",
    ]
    pdf = client.get(f"/api/quotes/{quote_id}/pdf", headers=auth_headers)
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF-")

    for status in ("sent", "accepted"):
        assert client.put(
            f"/api/quotes/{quote_id}/status",
            headers=auth_headers,
            json={"status": status},
        ).status_code == 200
    converted = client.post(f"/api/quotes/{quote_id}/convert", headers=auth_headers)
    assert converted.status_code == 200, converted.text
    invoice_id = converted.json()["converted_invoice_id"]
    invoice = client.get(f"/api/invoices/{invoice_id}", headers=auth_headers).json()
    assert Decimal(invoice["subtotal"]) == Decimal("209.00")
    assert Decimal(invoice["tax_total"]) == Decimal("39.71")
    assert Decimal(invoice["total"]) == Decimal("248.71")
    repeated_conversion = client.post(
        f"/api/quotes/{quote_id}/convert", headers=auth_headers
    )
    assert repeated_conversion.status_code == 200
    assert repeated_conversion.json()["converted_invoice_id"] == invoice_id

    disabled = client.post(
        "/api/admin/modules/sales.quote_assistant/disable", headers=auth_headers
    )
    assert disabled.status_code == 200
    assert client.get("/api/quote-assistant/drafts", headers=auth_headers).status_code == 409
    db_session.expire_all()
    assert db_session.get(QuoteAssistantDraft, draft["id"]).quote_id == quote_id
    assert client.get(f"/api/quotes/{quote_id}", headers=auth_headers).status_code == 200

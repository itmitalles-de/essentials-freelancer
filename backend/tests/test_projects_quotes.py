from decimal import Decimal

from fastapi.testclient import TestClient


def create_client(client: TestClient, headers: dict[str, str], name: str) -> int:
    response = client.post(
        "/api/clients",
        headers=headers,
        json={
            "name": name,
            "email": "billing@example.invalid",
            "hourly_rate": "80.00",
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_project_links_time_and_invoice(
    client: TestClient, auth_headers: dict[str, str]
):
    client_id = create_client(client, auth_headers, "Example Project Client")
    project = client.post(
        "/api/projects",
        headers=auth_headers,
        json={
            "client_id": client_id,
            "name": "Synthetic Website",
            "description": "A wholly invented project",
            "hourly_rate": "95.00",
        },
    )
    assert project.status_code == 200
    project_id = project.json()["id"]

    entry = client.post(
        "/api/time-entries",
        headers=auth_headers,
        json={
            "client_id": client_id,
            "project_id": project_id,
            "date": "2026-08-13",
            "description": "Synthetic project work",
            "duration_minutes": 60,
        },
    )
    assert entry.status_code == 200
    assert entry.json()["project_id"] == project_id
    assert entry.json()["hourly_rate"] == "95.00"

    invoice = client.post(
        "/api/invoices",
        headers=auth_headers,
        json={"client_id": client_id, "time_entry_ids": [entry.json()["id"]]},
    )
    assert invoice.status_code == 200, invoice.text
    assert invoice.json()["line_items"][0]["project_id"] == project_id

    linked_entries = client.get(
        f"/api/time-entries?project_id={project_id}", headers=auth_headers
    )
    assert [item["invoice_id"] for item in linked_entries.json()] == [
        invoice.json()["id"]
    ]

    blocked = client.delete(f"/api/projects/{project_id}", headers=auth_headers)
    assert blocked.status_code == 400


def test_quote_pdf_status_and_invoice_conversion(
    client: TestClient, auth_headers: dict[str, str]
):
    client_id = create_client(client, auth_headers, "Example Quote Client")
    project_id = client.post(
        "/api/projects",
        headers=auth_headers,
        json={"client_id": client_id, "name": "Synthetic Launch"},
    ).json()["id"]

    created = client.post(
        "/api/quotes",
        headers=auth_headers,
        json={
            "client_id": client_id,
            "project_id": project_id,
            "valid_in_days": 21,
            "notes": "Synthetic <scope> & delivery",
            "line_items": [
                {
                    "description": "Discovery & planning <workshop>",
                    "quantity": "2.00",
                    "unit": "hours",
                    "unit_price": "100.00",
                },
                {
                    "description": "Implementation package",
                    "quantity": "1.00",
                    "unit": "flat",
                    "unit_price": "500.00",
                },
            ],
        },
    )
    assert created.status_code == 200, created.text
    quote = created.json()
    assert quote["quote_number"].startswith("AN-")
    assert Decimal(quote["total"]) == Decimal("700.00")

    pdf = client.get(f"/api/quotes/{quote['id']}/pdf", headers=auth_headers)
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF-")

    cannot_convert = client.post(
        f"/api/quotes/{quote['id']}/convert", headers=auth_headers
    )
    assert cannot_convert.status_code == 400

    for status in ("sent", "accepted"):
        transitioned = client.put(
            f"/api/quotes/{quote['id']}/status",
            headers=auth_headers,
            json={"status": status},
        )
        assert transitioned.status_code == 200
        assert transitioned.json()["status"] == status

    converted = client.post(
        f"/api/quotes/{quote['id']}/convert", headers=auth_headers
    )
    assert converted.status_code == 200, converted.text
    assert converted.json()["status"] == "converted"
    invoice_id = converted.json()["converted_invoice_id"]

    invoice = client.get(f"/api/invoices/{invoice_id}", headers=auth_headers)
    assert invoice.status_code == 200
    assert invoice.json()["quote_id"] == quote["id"]
    assert invoice.json()["line_items"][0]["project_id"] == project_id
    assert Decimal(invoice.json()["total"]) == Decimal("700.00")

    deleted = client.delete(f"/api/invoices/{invoice_id}", headers=auth_headers)
    assert deleted.status_code == 204
    restored_quote = client.get(
        f"/api/quotes/{quote['id']}", headers=auth_headers
    ).json()
    assert restored_quote["status"] == "accepted"
    assert restored_quote["converted_invoice_id"] is None


def test_project_must_belong_to_quote_client(
    client: TestClient, auth_headers: dict[str, str]
):
    first_client = create_client(client, auth_headers, "First Example Client")
    second_client = create_client(client, auth_headers, "Second Example Client")
    project_id = client.post(
        "/api/projects",
        headers=auth_headers,
        json={"client_id": first_client, "name": "First Project"},
    ).json()["id"]

    response = client.post(
        "/api/quotes",
        headers=auth_headers,
        json={
            "client_id": second_client,
            "project_id": project_id,
            "line_items": [
                {
                    "description": "Synthetic service",
                    "quantity": 1,
                    "unit_price": 10,
                }
            ],
        },
    )
    assert response.status_code == 400

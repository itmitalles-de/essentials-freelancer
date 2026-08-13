from fastapi.testclient import TestClient


def test_login_and_current_user(client: TestClient):
    assert client.get("/api/health").json() == {"status": "ok"}
    rejected = client.post(
        "/api/auth/login",
        json={"username": "test-admin", "password": "wrong"},
    )
    assert rejected.status_code == 401

    accepted = client.post(
        "/api/auth/login",
        json={"username": "test-admin", "password": "test-only-password"},
    )
    assert accepted.status_code == 200
    token = accepted.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json() == {"username": "test-admin"}


def test_clients_crud_and_protected_delete(
    client: TestClient, auth_headers: dict[str, str]
):
    payload = {
        "name": "Example Studio",
        "contact_person": "Alex Example",
        "email": "alex@example.invalid",
        "hourly_rate": "80.00",
    }
    created = client.post("/api/clients", headers=auth_headers, json=payload)
    assert created.status_code == 200
    client_id = created.json()["id"]

    listed = client.get("/api/clients", headers=auth_headers)
    assert [item["name"] for item in listed.json()] == ["Example Studio"]

    payload["active"] = False
    updated = client.put(
        f"/api/clients/{client_id}", headers=auth_headers, json=payload
    )
    assert updated.status_code == 200
    assert updated.json()["active"] is False

    entry = client.post(
        "/api/time-entries",
        headers=auth_headers,
        json={
            "client_id": client_id,
            "date": "2026-08-13",
            "description": "Synthetic consulting",
            "duration_minutes": 60,
        },
    )
    assert entry.status_code == 200

    blocked = client.delete(f"/api/clients/{client_id}", headers=auth_headers)
    assert blocked.status_code == 400
    assert "inaktiv" in blocked.json()["detail"]


def test_all_business_routes_require_authentication(client: TestClient):
    for path in (
        "/api/clients",
        "/api/time-entries",
        "/api/invoices",
        "/api/expenses",
        "/api/settings",
    ):
        assert client.get(path).status_code in {401, 403}

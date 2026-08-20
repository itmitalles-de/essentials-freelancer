import json

from fastapi.testclient import TestClient

from app.config import settings
from app.models import Expense, ModuleAuditEvent, ModuleInstallation


def module_by_id(payload: list[dict], module_id: str) -> dict:
    return next(item for item in payload if item["manifest"]["id"] == module_id)


def test_catalog_contains_complete_contract_without_secret_values(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
):
    monkeypatch.setattr(settings, "smtp_password", "synthetic-password-must-not-leak")
    response = client.get("/api/admin/modules", headers=auth_headers)
    assert response.status_code == 200
    catalog = response.json()
    assert {
        "Arbeit",
        "Verkauf und Angebote",
        "Abrechnung",
        "Ausgaben",
        "Kommunikation",
        "Export und Integrationen",
    } <= {item["manifest"]["group"] for item in catalog}

    assistant = module_by_id(catalog, "sales.quote_assistant")
    manifest = assistant["manifest"]
    for field in (
        "id",
        "schema_version",
        "display_name",
        "description",
        "group",
        "module_type",
        "required",
        "default_state",
        "dependencies",
        "conflicts",
        "compatible_product_versions",
        "compatible_schema_versions",
        "configuration_fields",
        "secret_requirements",
        "api_boundaries",
        "navigation_boundaries",
        "job_boundaries",
        "healthcheck",
        "data_ownership",
        "export_behavior",
        "backup_behavior",
        "restore_behavior",
        "activation_behavior",
        "deactivation_behavior",
        "update_behavior",
    ):
        assert field in manifest
    serialized = json.dumps(catalog)
    assert "synthetic-password-must-not-leak" not in serialized


def test_module_activation_is_idempotent_audited_and_checks_dependencies(
    client: TestClient, auth_headers: dict[str, str], db_session
):
    blocked_required = client.post(
        "/api/admin/modules/core.clients/disable", headers=auth_headers
    )
    assert blocked_required.status_code == 409
    assert blocked_required.json()["detail"]["code"] == "required_module"

    disabled_quotes = client.post(
        "/api/admin/modules/sales.quotes/disable", headers=auth_headers
    )
    assert disabled_quotes.status_code == 200
    assert disabled_quotes.json()["state"] == "disabled"

    dependency_block = client.post(
        "/api/admin/modules/sales.quote_assistant/enable", headers=auth_headers
    )
    assert dependency_block.status_code == 409
    assert dependency_block.json()["detail"]["dependency_id"] == "sales.quotes"

    assert (
        client.post(
            "/api/admin/modules/sales.quotes/enable", headers=auth_headers
        ).status_code
        == 200
    )
    for _ in range(2):
        enabled = client.post(
            "/api/admin/modules/sales.quote_assistant/enable", headers=auth_headers
        )
        assert enabled.status_code == 200
        assert enabled.json()["state"] == "enabled"
    for _ in range(2):
        disabled = client.post(
            "/api/admin/modules/sales.quote_assistant/disable", headers=auth_headers
        )
        assert disabled.status_code == 200
        assert disabled.json()["state"] == "disabled"

    events = (
        db_session.query(ModuleAuditEvent)
        .filter(ModuleAuditEvent.module_id == "sales.quote_assistant")
        .order_by(ModuleAuditEvent.id)
        .all()
    )
    assert [event.action for event in events] == [
        "enable",
        "enable_noop",
        "disable",
        "disable_noop",
    ]


def test_disabled_module_blocks_api_and_preserves_business_data(
    client: TestClient, auth_headers: dict[str, str], db_session
):
    created = client.post(
        "/api/expenses",
        headers=auth_headers,
        json={
            "date": "2026-08-13",
            "description": "Synthetic retained expense",
            "category": "Test",
            "amount": "12.34",
        },
    )
    expense_id = created.json()["id"]

    disabled = client.post(
        "/api/admin/modules/expenses.receipts/disable", headers=auth_headers
    )
    assert disabled.status_code == 200
    blocked = client.get("/api/expenses", headers=auth_headers)
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == {
        "code": "module_unavailable",
        "message": "Modul expenses.receipts ist nicht verfügbar (disabled).",
        "module_id": "expenses.receipts",
        "state": "disabled",
    }
    assert db_session.get(Expense, expense_id) is not None

    enabled = client.post(
        "/api/admin/modules/expenses.receipts/enable", headers=auth_headers
    )
    assert enabled.status_code == 200
    listed = client.get("/api/expenses", headers=auth_headers)
    assert [item["id"] for item in listed.json()] == [expense_id]


def test_needs_configuration_and_not_installed_states_block_access(
    client: TestClient, auth_headers: dict[str, str], db_session
):
    smtp = client.get("/api/admin/modules", headers=auth_headers).json()
    assert module_by_id(smtp, "communication.smtp")["state"] == "disabled"
    locked = client.post(
        "/api/admin/modules/communication.smtp/enable", headers=auth_headers
    )
    assert locked.status_code == 409
    assert locked.json()["detail"]["code"] == "pilot_module_locked"

    installation = db_session.get(ModuleInstallation, "expenses.receipts")
    installation.state = "not_installed"
    db_session.commit()
    blocked = client.get("/api/expenses", headers=auth_headers)
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["state"] == "not_installed"

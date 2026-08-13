from fastapi.testclient import TestClient

from app.main import app


def test_openapi_contract_contains_protected_product_boundaries(client: TestClient):
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == "Essentials+ Freelancer"
    assert schema["info"]["version"] == "0.2.0"

    expected_operations = {
        "/api/auth/login": {"post"},
        "/api/admin/modules": {"get"},
        "/api/quote-assistant/preview": {"post"},
        "/api/reports/summary": {"get"},
        "/api/reports/time.csv": {"get"},
        "/api/ready": {"get"},
        "/api/meta": {"get"},
    }
    for path, methods in expected_operations.items():
        assert path in schema["paths"]
        assert methods <= set(schema["paths"][path])

    protected = schema["paths"]["/api/reports/summary"]["get"]
    assert protected["security"] == [{"HTTPBearer": []}]
    assert "ReportSummary" in schema["components"]["schemas"]
    report = schema["components"]["schemas"]["ReportSummary"]
    assert set(report["required"]) >= {"time", "quotes", "invoices", "expenses"}


def test_api_does_not_publish_internal_idempotency_or_secret_columns():
    schema_text = str(app.openapi())
    for internal_name in (
        "request_fingerprint",
        "start_request_key",
        "start_request_fingerprint",
        "smtp_password",
    ):
        assert internal_name not in schema_text

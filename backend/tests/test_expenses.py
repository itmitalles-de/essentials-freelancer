import os

from fastapi.testclient import TestClient

from app.models import Expense
from app.routers.expenses import MAX_RECEIPT_SIZE


def test_expense_crud_and_receipt_roundtrip(
    client: TestClient, auth_headers: dict[str, str], db_session
):
    created = client.post(
        "/api/expenses",
        headers=auth_headers,
        json={
            "date": "2026-08-13",
            "description": "Synthetic software subscription",
            "category": "Software",
            "amount": "19.90",
        },
    )
    assert created.status_code == 200
    expense_id = created.json()["id"]
    assert created.json()["has_receipt"] is False

    pdf_content = b"%PDF-1.4\n% synthetic receipt\n%%EOF\n"
    uploaded = client.post(
        f"/api/expenses/{expense_id}/receipt",
        headers=auth_headers,
        files={"file": ("receipt.pdf", pdf_content, "application/pdf")},
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["has_receipt"] is True

    downloaded = client.get(
        f"/api/expenses/{expense_id}/receipt", headers=auth_headers
    )
    assert downloaded.status_code == 200
    assert downloaded.content == pdf_content

    stored = db_session.get(Expense, expense_id)
    receipt_path = stored.receipt_path
    assert os.path.isfile(receipt_path)

    deleted = client.delete(f"/api/expenses/{expense_id}", headers=auth_headers)
    assert deleted.status_code == 204
    assert not os.path.exists(receipt_path)


def test_receipt_rejects_spoofed_and_oversized_files(
    client: TestClient, auth_headers: dict[str, str]
):
    expense_id = client.post(
        "/api/expenses",
        headers=auth_headers,
        json={
            "date": "2026-08-13",
            "description": "Synthetic hardware",
            "amount": "5.00",
        },
    ).json()["id"]

    spoofed = client.post(
        f"/api/expenses/{expense_id}/receipt",
        headers=auth_headers,
        files={"file": ("fake.pdf", b"not a pdf", "application/pdf")},
    )
    assert spoofed.status_code == 400

    oversized = client.post(
        f"/api/expenses/{expense_id}/receipt",
        headers=auth_headers,
        files={
            "file": (
                "large.pdf",
                b"%PDF-" + b"0" * MAX_RECEIPT_SIZE,
                "application/pdf",
            )
        },
    )
    assert oversized.status_code == 400

    unsupported = client.post(
        f"/api/expenses/{expense_id}/receipt",
        headers=auth_headers,
        files={"file": ("receipt.txt", b"plain text", "text/plain")},
    )
    assert unsupported.status_code == 400

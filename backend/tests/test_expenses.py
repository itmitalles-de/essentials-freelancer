import os
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.models import Expense
from app.routers.expenses import MAX_RECEIPT_SIZE


def image_bytes(image_format: str) -> bytes:
    output = BytesIO()
    Image.new("RGB", (2, 2), color=(12, 34, 56)).save(output, format=image_format)
    return output.getvalue()


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


def test_png_jpeg_and_pdf_receipts_validate_content_and_mime(
    client: TestClient, auth_headers: dict[str, str]
):
    for index, (filename, content, content_type) in enumerate(
        [
            ("receipt.png", image_bytes("PNG"), "image/png"),
            ("receipt.jpg", image_bytes("JPEG"), "image/jpeg"),
            ("receipt.pdf", b"%PDF-1.4\nsynthetic\n%%EOF\n", "application/pdf"),
        ],
        start=1,
    ):
        expense_id = client.post(
            "/api/expenses",
            headers=auth_headers,
            json={
                "date": "2026-08-13",
                "description": f"Synthetic receipt {index}",
                "amount": "1.00",
            },
        ).json()["id"]
        uploaded = client.post(
            f"/api/expenses/{expense_id}/receipt",
            headers=auth_headers,
            files={"file": (filename, content, content_type)},
        )
        assert uploaded.status_code == 200, uploaded.text
        downloaded = client.get(
            f"/api/expenses/{expense_id}/receipt", headers=auth_headers
        )
        assert downloaded.content == content
        assert downloaded.headers["content-type"].startswith(content_type)

    mismatch_id = client.post(
        "/api/expenses",
        headers=auth_headers,
        json={"date": "2026-08-13", "description": "Mismatch", "amount": "1"},
    ).json()["id"]
    mismatch = client.post(
        f"/api/expenses/{mismatch_id}/receipt",
        headers=auth_headers,
        files={"file": ("wrong.png", image_bytes("JPEG"), "image/png")},
    )
    assert mismatch.status_code == 400


def test_logo_upload_is_validated_and_previous_file_survives_rejection(
    client: TestClient, auth_headers: dict[str, str]
):
    png = image_bytes("PNG")
    uploaded = client.post(
        "/api/settings/logo",
        headers=auth_headers,
        files={"file": ("logo.png", png, "image/png")},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["has_logo"] is True

    rejected = client.post(
        "/api/settings/logo",
        headers=auth_headers,
        files={"file": ("logo.jpg", png, "image/jpeg")},
    )
    assert rejected.status_code == 400
    downloaded = client.get("/api/settings/logo", headers=auth_headers)
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"].startswith("image/png")
    assert downloaded.content == png

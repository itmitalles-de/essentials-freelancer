#!/usr/bin/env python3
"""Seed only synthetic, unmistakably non-bookable Android smoke objects."""

import argparse
import json
import urllib.error
import urllib.request


def request(base_url, method, path, token=None, body=None, headers=None):
    payload = json.dumps(body).encode() if body is not None else None
    request_headers = dict(headers or {})
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    response = urllib.request.urlopen(
        urllib.request.Request(
            f"{base_url.rstrip('/')}{path}",
            data=payload,
            headers=request_headers,
            method=method,
        ),
        timeout=15,
    )
    return json.load(response) if response.length != 0 else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    token = request(
        args.base_url,
        "POST",
        "/api/auth/login",
        body={"username": args.username, "password": args.password},
    )["access_token"]
    request(
        args.base_url,
        "PUT",
        "/api/settings",
        token,
        {
            "company_name": "TESTBETRIEB — NICHT BUCHEN",
            "owner_name": "Synthetic Operator",
            "address_line1": "Testweg 1",
            "address_line2": "",
            "zip_city": "00000 Teststadt",
            "email": "operator@example.invalid",
            "phone": "",
            "tax_id": "",
            "iban": "DE00000000000000000000",
            "bic": "SYNTHETIC",
            "bank_name": "Synthetic Test Bank",
            "invoice_footer_note": "NICHT BUCHEN — SYNTHETISCHER ANDROID-SMOKE",
            "invoice_number_prefix": "TESTRECHNUNG",
            "quote_number_prefix": "TESTANGEBOT",
            "default_hourly_rate": "0",
            "default_payment_terms_days": 14,
        },
    )
    client = request(
        args.base_url,
        "POST",
        "/api/clients",
        token,
        {
            "name": "TESTKUNDE",
            "contact_person": "NICHT BUCHEN",
            "address_line1": "Kunden-Testweg 2",
            "zip_city": "00000 Teststadt",
            "email": "android-smoke@example.invalid",
            "hourly_rate": "80.00",
        },
    )
    project = request(
        args.base_url,
        "POST",
        "/api/projects",
        token,
        {
            "client_id": client["id"],
            "name": "TESTPROJEKT",
            "description": "NICHT BUCHEN",
            "hourly_rate": "80.00",
        },
    )
    request(
        args.base_url,
        "POST",
        "/api/time-entries",
        token,
        {
            "client_id": client["id"],
            "project_id": project["id"],
            "date": "2026-08-19",
            "description": "ANDROID-SMOKE — NICHT BUCHEN",
            "duration_minutes": 15,
        },
    )
    quote = request(
        args.base_url,
        "POST",
        "/api/quotes",
        token,
        {
            "client_id": client["id"],
            "project_id": project["id"],
            "notes": "TESTANGEBOT — NICHT BUCHEN",
            "line_items": [
                {
                    "description": "TESTANGEBOT — NICHT BUCHEN",
                    "quantity": "1",
                    "unit": "flat",
                    "unit_price": "1.00",
                    "tax_rate": "0",
                }
            ],
        },
    )
    request(args.base_url, "PUT", f"/api/quotes/{quote['id']}/status", token, {"status": "sent"})
    request(args.base_url, "PUT", f"/api/quotes/{quote['id']}/status", token, {"status": "accepted"})
    converted = request(args.base_url, "POST", f"/api/quotes/{quote['id']}/convert", token)
    invoice = request(args.base_url, "GET", f"/api/invoices/{converted['converted_invoice_id']}", token)
    request(args.base_url, "POST", "/api/admin/modules/communication.smtp/enable", token)
    request(
        args.base_url,
        "POST",
        f"/api/invoices/{invoice['id']}/send",
        token,
        {
            "recipient": "android-smoke@example.invalid",
            "invoice_number": invoice["invoice_number"],
            "total": invoice["total"],
            "pdf_reviewed": True,
            "resend": False,
        },
        {"Idempotency-Key": "android-smoke-first-send"},
    )
    print("android-smoke-seed: TESTKUNDE/TESTPROJEKT/TESTANGEBOT/TESTRECHNUNG ready")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as error:
        raise SystemExit(
            f"android-smoke-seed: HTTP {error.code}: {error.read().decode(errors='replace')}"
        )

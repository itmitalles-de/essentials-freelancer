#!/usr/bin/env python3
import argparse
import base64
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date


class Failure(RuntimeError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


class Api:
    def __init__(self, base_url: str, username: str, password: str, work_dir: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.work_dir = work_dir
        self.token = ""

    def request(
        self,
        method: str,
        path: str,
        body: object | None = None,
        expected: int = 200,
        headers: dict[str, str] | None = None,
        raw: bool = False,
    ):
        data = json.dumps(body).encode() if body is not None else None
        request_headers = dict(headers or {})
        if data is not None:
            request_headers["Content-Type"] = "application/json"
        if self.token:
            request_headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=data, headers=request_headers, method=method
        )
        try:
            response = urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        content = response.read()
        if response.status != expected:
            raise Failure(
                f"{method} {path}: expected {expected}, got {response.status}: "
                f"{content.decode(errors='replace')}"
            )
        if raw:
            return content, dict(response.headers)
        return json.loads(content or b"null")

    def upload(
        self, path: str, filename: str, content_type: str, content: bytes, expected: int = 200
    ):
        boundary = "----essentials-full-check-boundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        try:
            response = urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        data = response.read()
        if response.status != expected:
            raise Failure(
                f"upload {filename}: expected {expected}, got {response.status}: "
                f"{data.decode(errors='replace')}"
            )
        return json.loads(data or b"null")

    def login(self) -> None:
        response = self.request(
            "POST",
            "/api/auth/login",
            {"username": self.username, "password": self.password},
        )
        self.token = response["access_token"]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--smtp-api-url")
    parser.add_argument("--revision", required=True)
    parser.add_argument(
        "--phase", choices=["source", "enable-backup", "restore"], required=True
    )
    return parser.parse_args()


def fixture_request(base_url: str, method: str, path: str, body: object | None = None):
    content = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=content,
        headers={"Content-Type": "application/json"} if content else {},
        method=method,
    )
    return json.load(urllib.request.urlopen(request, timeout=10))


def confirmed_invoice_payload(api: Api, payload: dict) -> tuple[dict, dict]:
    preview = api.request("POST", "/api/invoices/preview", payload)
    return (
        {
            **payload,
            "billing_confirmation_token": preview["confirmation_token"],
            "billing_confirmed": True,
        },
        preview,
    )


def tiny_images() -> tuple[bytes, bytes]:
    # Generated synthetic 2x2 RGB fixtures, never real receipt content.
    png = "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGMU0bBhYGBgYmBgYGBgAAAFogB8q5SvRgAAAABJRU5ErkJggg=="
    jpeg = "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAACAAIDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDyOiiiuw5D/9k="
    return base64.b64decode(png), base64.b64decode(jpeg)


def verify_pdf(content: bytes, path: str, expected_terms: list[str]) -> None:
    expect(content.startswith(b"%PDF-"), f"{path} is not a PDF")
    with open(path, "wb") as output:
        output.write(content)
    text_path = f"{path}.txt"
    subprocess.run(["pdftotext", path, text_path], check=True)
    with open(text_path, encoding="utf-8") as source:
        text = source.read()
    for term in expected_terms:
        expect(term in text, f"PDF {path} lacks expected term {term!r}")


def verify_core(api: Api, revision: str, *, backup_state: str) -> None:
    ready = api.request("GET", "/api/ready")
    expect(ready["schema_revision"] == "0007_billing_policy", "schema mismatch")
    meta = api.request("GET", "/api/meta")
    expect(meta["product"] == "Essentials+ Freelancer", "product metadata mismatch")
    expect(meta["repository_revision"] == revision, "repository revision mismatch")
    expect(meta["build_time"] != "unknown", "build time was not embedded")
    expect(meta["readiness"] == "ready", "metadata readiness mismatch")
    clients = api.request("GET", "/api/clients?q=Synthetic%20Full%20Check")
    expect(len(clients) == 1, "restored client not unique/present")
    expect(
        clients[0]["billing_rate_type"] == "private"
        and clients[0]["hourly_rate"] == "50.00"
        and clients[0]["default_service_mode"] == "remote"
        and clients[0]["billing_profile_confirmed"],
        "client billing profile differs after restore",
    )
    projects = api.request("GET", f"/api/projects?client_id={clients[0]['id']}")
    expect(
        len(projects) == 1
        and projects[0]["hourly_rate"] == "75.00"
        and projects[0]["billing_rate_type_override"] == "business"
        and projects[0]["default_service_mode"] == "onsite"
        and projects[0]["is_individual_project"]
        and projects[0]["billing_profile_confirmed"],
        "project billing override differs after restore",
    )
    settings = api.request("GET", "/api/settings")
    expect(
        settings["private_hourly_rate"] == "50.00"
        and settings["business_hourly_rate"] == "75.00"
        and settings["travel_hourly_rate"] == "30.00"
        and settings["travel_minimum_minutes"] == 30
        and settings["travel_increment_minutes"] is None
        and settings["default_tax_rate"] == "0.00"
        and settings["small_business_notice_enabled"],
        "operator billing/tax profile differs after restore",
    )
    invoices = api.request("GET", f"/api/invoices?client_id={clients[0]['id']}")
    expect(len(invoices) == 2, "invoice core count differs after restore")
    for invoice in invoices:
        document, _ = api.request("GET", f"/api/invoices/{invoice['id']}/pdf", raw=True)
        expect(document.startswith(b"%PDF-"), "restored invoice PDF is unavailable")
    paid_invoice = next(item for item in invoices if item["status"] == "paid")
    snapshot_lines = sorted(paid_invoice["line_items"], key=lambda item: item["id"])
    expect(
        [item["snapshot_line_kind"] for item in snapshot_lines]
        == ["work", "work", "travel"],
        "billing snapshot line kinds differ",
    )
    expect(
        [item["snapshot_actual_minutes"] for item in snapshot_lines] == [31, 20, 10]
        and [item["snapshot_billable_minutes"] for item in snapshot_lines]
        == [45, 60, 30]
        and [item["snapshot_hourly_rate"] for item in snapshot_lines]
        == ["50.00", "75.00", "30.00"],
        "actual/billable duration or applied rates differ",
    )
    send_attempts = api.request(
        "GET", f"/api/invoices/{paid_invoice['id']}/send-attempts"
    )
    expect(send_attempts == [], "SMTP send history must stay empty in the pilot")
    quotes = api.request("GET", f"/api/quotes?client_id={clients[0]['id']}")
    expect(
        len(quotes) == 2
        and sorted(item["status"] for item in quotes) == ["converted", "draft"],
        "quote core differs",
    )
    for quote in quotes:
        document, _ = api.request("GET", f"/api/quotes/{quote['id']}/pdf", raw=True)
        expect(document.startswith(b"%PDF-"), "restored quote PDF is unavailable")
    drafts = api.request("GET", "/api/quote-assistant/drafts")
    expect(
        len(drafts) == 1
        and drafts[0]["status"] == "transferred"
        and drafts[0]["title"] == "Synthetic Assistant Draft",
        "assistant snapshots differ",
    )
    expenses = api.request("GET", "/api/expenses?q=Synthetic")
    expect(len(expenses) == 3 and all(item["has_receipt"] for item in expenses), "receipts differ")
    receipt_signatures = {
        "Synthetic PNG receipt": b"\x89PNG",
        "Synthetic JPEG receipt": b"\xff\xd8\xff",
        "Synthetic PDF receipt": b"%PDF-",
    }
    for expense in expenses:
        receipt, _ = api.request("GET", f"/api/expenses/{expense['id']}/receipt", raw=True)
        expect(
            receipt.startswith(receipt_signatures[expense["description"]]),
            f"restored receipt differs for {expense['description']}",
        )
    module_states = {
        item["manifest"]["id"]: item["state"]
        for item in api.request("GET", "/api/admin/modules")
    }
    expect(module_states["sales.quote_assistant"] == "enabled", "assistant state differs")
    expect(module_states["backup.offsite"] == backup_state, "offsite state differs")
    expect(module_states["communication.smtp"] == "disabled", "SMTP pilot lock differs")
    report = api.request("GET", f"/api/reports/summary?client_id={clients[0]['id']}")
    expect(report["time"]["captured_hours"] == "1.35", "captured time differs")
    expect(report["invoices"]["statuses"]["paid"] == 1, "paid invoice differs")


def run_source(api: Api, smtp_api_url: str, revision: str) -> None:
    today = date.today().isoformat()
    company_settings = {
        "company_name": "TESTBETRIEB — NICHT BUCHEN",
        "owner_name": "Synthetic Operator",
        "address_line1": "Testweg 1",
        "address_line2": "",
        "zip_city": "00000 Teststadt",
        "email": "operator@example.invalid",
        "phone": "+49 000 000000",
        "tax_id": "SYNTHETIC-TAX-ID",
        "iban": "DE00000000000000000000",
        "bic": "SYNTHETIC",
        "bank_name": "Synthetic Test Bank",
        "invoice_footer_note": "SYNTHETIC FOOTER — NICHT BUCHEN",
        "invoice_number_prefix": "RE",
        "quote_number_prefix": "AN",
        "default_hourly_rate": "50.00",
        "default_payment_terms_days": 14,
        "private_hourly_rate": "50.00",
        "business_hourly_rate": "75.00",
        "travel_hourly_rate": "30.00",
        "first_order_minimum_minutes": 60,
        "onsite_minimum_minutes": 60,
        "remote_increment_minutes": 15,
        "travel_minimum_minutes": 30,
        "travel_increment_minutes": None,
        "default_tax_rate": "0.00",
        "small_business_notice_enabled": True,
        "small_business_notice_text": (
            "Gemäß § 19 UStG wird keine Umsatzsteuer berechnet."
        ),
    }
    configured = api.request("PUT", "/api/settings", company_settings)
    expect(
        configured["invoice_footer_note"] == company_settings["invoice_footer_note"],
        "synthetic company settings were not persisted",
    )
    modules = api.request("GET", "/api/admin/modules")
    expect(all("value" not in item for item in modules), "module response exposed value field")
    expect(not any("smtp_password" in json.dumps(item) and "synthetic" in json.dumps(item) for item in modules), "secret leaked")
    backup = next(item for item in modules if item["manifest"]["id"] == "backup.offsite")
    expect(backup["state"] == "disabled", "offsite backup should start disabled")

    assistant = api.request("POST", "/api/admin/modules/sales.quote_assistant/enable")
    expect(assistant["state"] == "enabled", "assistant did not enable")
    repeated_enable = api.request("POST", "/api/admin/modules/sales.quote_assistant/enable")
    expect(repeated_enable["state"] == "enabled", "repeated enable failed")

    client = api.request(
        "POST",
        "/api/clients",
        {
            "name": "Synthetic Full Check Client",
            "contact_person": "Synthetic Recipient",
            "address_line1": "Kunden-Testweg 2",
            "zip_city": "00000 Teststadt",
            "email": "billing@example.invalid",
            "hourly_rate": "50.00",
            "billing_rate_type": "private",
            "default_service_mode": "remote",
            "billing_profile_confirmed": True,
        },
    )
    project = api.request(
        "POST",
        "/api/projects",
        {
            "client_id": client["id"],
            "name": "Synthetic Full Check Project",
            "hourly_rate": "75.00",
            "billing_rate_type_override": "business",
            "default_service_mode": "onsite",
            "is_individual_project": True,
            "billing_profile_confirmed": True,
        },
    )

    timer_headers = {"Idempotency-Key": "full-check-timer-start"}
    timer = api.request(
        "POST",
        "/api/time-entries/start",
        {"client_id": client["id"], "project_id": project["id"], "description": "Synthetic timer"},
        headers=timer_headers,
    )
    repeated_timer = api.request(
        "POST",
        "/api/time-entries/start",
        {"client_id": client["id"], "project_id": project["id"], "description": "Synthetic timer"},
        headers=timer_headers,
    )
    expect(timer["id"] == repeated_timer["id"], "timer start not idempotent")
    stopped = api.request("POST", f"/api/time-entries/{timer['id']}/stop")
    repeated_stop = api.request("POST", f"/api/time-entries/{timer['id']}/stop")
    expect(stopped == repeated_stop, "timer stop not idempotent")
    api.request(
        "PUT", f"/api/time-entries/{timer['id']}", {"duration_minutes": 30}
    )
    manual = api.request(
        "POST",
        "/api/time-entries",
        {
            "client_id": client["id"],
            "date": today,
            "description": "Synthetic private remote work",
            "duration_minutes": 31,
            "service_mode": "remote",
            "is_first_order": False,
        },
    )
    onsite = api.request(
        "POST",
        "/api/time-entries",
        {
            "client_id": client["id"],
            "project_id": project["id"],
            "date": today,
            "description": "Synthetic onsite work",
            "duration_minutes": 20,
            "service_mode": "onsite",
            "is_first_order": False,
            "travel_actual_minutes": 10,
        },
    )

    # This is deliberately exercised on PostgreSQL, not the SQLite unit-test
    # fixture: both requests contend for the invoice-number row lock.
    parallel_entries = [
        api.request(
            "POST",
            "/api/time-entries",
            {
                "client_id": client["id"],
                "project_id": project["id"],
                "date": today,
                "description": f"Synthetic parallel invoice {index}",
                "duration_minutes": 60,
            },
        )
        for index in (1, 2)
    ]

    parallel_payloads = [
        confirmed_invoice_payload(
            api,
            {
                "client_id": client["id"],
                "time_entry_ids": [entry["id"]],
                "tax_rate": "0",
            },
        )[0]
        for entry in parallel_entries
    ]

    def create_parallel_invoice(index: int):
        return api.request(
            "POST",
            "/api/invoices",
            parallel_payloads[index],
            headers={"Idempotency-Key": f"parallel-invoice-{index}"},
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        parallel_invoices = list(executor.map(create_parallel_invoice, (0, 1)))
    parallel_numbers = sorted(
        int(item["invoice_number"].rsplit("-", 1)[1]) for item in parallel_invoices
    )
    expect(
        parallel_numbers[1] == parallel_numbers[0] + 1,
        "parallel invoice numbers were not unique and consecutive",
    )
    for parallel_invoice, parallel_entry in zip(parallel_invoices, parallel_entries):
        api.request("DELETE", f"/api/invoices/{parallel_invoice['id']}", expected=204)
        api.request("DELETE", f"/api/time-entries/{parallel_entry['id']}", expected=204)

    catalog = api.request(
        "POST",
        "/api/quote-assistant/catalog/items",
        {
            "stable_key": "service.full-check",
            "kind": "service",
            "name": "Synthetic Full Check Service",
            "version": {
                "description": "Synthetic assistant service",
                "unit": "hours",
                "net_unit_price": "99.95",
                "tax_rate": "0",
                "valid_from": "2026-01-01",
            },
        },
    )
    catalog_version_id = catalog["versions"][0]["id"]
    preview = api.request(
        "POST",
        "/api/quote-assistant/preview",
        {
            "pricing_date": today,
            "selections": [{"catalog_version_id": catalog_version_id, "quantity": "2"}],
            "surcharge_percent": "10",
            "discount_percent": "5",
        },
    )
    expect(preview["calculation_steps"][-1]["expression"] == "Netto + Steuer", "assistant calculation path missing")
    draft = api.request(
        "POST",
        "/api/quote-assistant/drafts",
        {
            "client_id": client["id"],
            "project_id": project["id"],
            "title": "Synthetic Assistant Draft",
            "pricing_date": today,
            "guided_answers": {"scope": "Synthetic answer"},
            "selections": [{"catalog_version_id": catalog_version_id, "quantity": "2"}],
            "surcharge_percent": "10",
            "discount_percent": "5",
        },
    )
    api.request("POST", f"/api/quote-assistant/drafts/{draft['id']}/transfer", expected=409)
    approved = api.request("POST", f"/api/quote-assistant/drafts/{draft['id']}/approve")
    expect(approved["status"] == "approved", "assistant human approval missing")
    api.request("POST", f"/api/quote-assistant/drafts/{draft['id']}/approve")
    transferred_draft = api.request("POST", f"/api/quote-assistant/drafts/{draft['id']}/transfer")
    repeated_transfer = api.request("POST", f"/api/quote-assistant/drafts/{draft['id']}/transfer")
    expect(transferred_draft["quote_id"] == repeated_transfer["quote_id"], "assistant transfer not idempotent")

    quote = api.request(
        "POST",
        "/api/quotes",
        {
            "client_id": client["id"],
            "project_id": project["id"],
            "notes": "Synthetic full check quote",
            "line_items": [
                {"description": "Synthetic service", "quantity": "2", "unit": "hours", "unit_price": "100", "tax_rate": "0"},
                {"description": "Synthetic material", "quantity": "3", "unit": "items", "unit_price": "25", "tax_rate": "0"},
            ],
        },
    )
    quote_pdf, _ = api.request("GET", f"/api/quotes/{quote['id']}/pdf", raw=True)
    verify_pdf(quote_pdf, os.path.join(api.work_dir, "quote.pdf"), [quote["quote_number"], "Synthetic service", "Synthetic material"])
    api.request("PUT", f"/api/quotes/{quote['id']}/status", {"status": "sent"})
    api.request("PUT", f"/api/quotes/{quote['id']}/status", {"status": "accepted"})
    quote_invoice_preview = api.request(
        "POST",
        f"/api/quotes/{quote['id']}/invoice-preview",
        {"service_date": today},
    )
    expect(
        quote_invoice_preview["fixed_total"] == "275.00"
        and quote_invoice_preview["work_total"] == "0.00"
        and quote_invoice_preview["travel_total"] == "0.00"
        and all(
            line["actual_minutes"] is None
            and line["billable_minutes"] is None
            and line["service_date"] == today
            for line in quote_invoice_preview["lines"]
        ),
        "fixed-quote invoice preview invented time or totals",
    )
    quote_conversion_payload = {
        "service_date": today,
        "billing_confirmation_token": quote_invoice_preview["confirmation_token"],
        "billing_confirmed": True,
    }
    converted = api.request(
        "POST", f"/api/quotes/{quote['id']}/convert", quote_conversion_payload
    )
    repeated_conversion = api.request(
        "POST", f"/api/quotes/{quote['id']}/convert", quote_conversion_payload
    )
    expect(converted["converted_invoice_id"] == repeated_conversion["converted_invoice_id"], "quote converted twice")

    invoice_headers = {"Idempotency-Key": "full-check-time-invoice"}
    invoice_payload, billing_preview = confirmed_invoice_payload(
        api,
        {
            "client_id": client["id"],
            "time_entry_ids": [manual["id"], onsite["id"]],
            "tax_rate": "0",
        },
    )
    expect(
        [(line["actual_minutes"], line["billable_minutes"], line["hourly_rate"])
         for line in billing_preview["lines"]]
        == [(31, 45, "50.00"), (20, 60, "75.00"), (10, 30, "30.00")],
        "billing preview did not expose the confirmed work/travel decisions",
    )
    expect(
        billing_preview["work_total"] == "112.50"
        and billing_preview["travel_total"] == "15.00"
        and billing_preview["total"] == "127.50"
        and billing_preview["tax_status"] == "small_business_section_19",
        "billing preview totals or tax status differ",
    )
    invoice = api.request(
        "POST",
        "/api/invoices",
        invoice_payload,
        headers=invoice_headers,
    )
    repeated_invoice = api.request(
        "POST",
        "/api/invoices",
        invoice_payload,
        headers=invoice_headers,
    )
    expect(invoice["id"] == repeated_invoice["id"], "invoice command not idempotent")
    invoice_pdf, _ = api.request("GET", f"/api/invoices/{invoice['id']}/pdf", raw=True)
    verify_pdf(
        invoice_pdf,
        os.path.join(api.work_dir, "invoice.pdf"),
        [
            invoice["invoice_number"],
            "Synthetic",
            "private",
            "work",
            "Tatsächlich: 31 Min.",
            "Abrechenbar: 45 Min.",
            "Tatsächlich: 10 Min.",
            "Abrechenbar: 30 Min.",
            "0.7500",
            "Std.",
            "Stundensatz: 50,00 €/Std.",
            "127,50",
            "Steuer 0,00 %",
            "§ 19 UStG",
            "TESTBETRIEB",
            "Synthetic Operator",
            "Kunden-Testweg 2",
            "SYNTHETIC FOOTER",
            "IBAN",
            f"Leistungsdatum: {date.today().strftime('%d.%m.%Y')}",
        ],
    )
    changed_settings = dict(company_settings)
    changed_settings["invoice_footer_note"] = "SYNTHETIC FOOTER V2 — NICHT BUCHEN"
    api.request("PUT", "/api/settings", changed_settings)
    stable_pdf, _ = api.request("GET", f"/api/invoices/{invoice['id']}/pdf", raw=True)
    expect(stable_pdf == invoice_pdf, "existing invoice PDF changed after footer update")

    fixture_request(smtp_api_url, "POST", "/api/reset", {})
    smtp_module = next(
        item
        for item in api.request("GET", "/api/admin/modules")
        if item["manifest"]["id"] == "communication.smtp"
    )
    expect(smtp_module["state"] == "disabled", "SMTP did not start disabled")
    locked = api.request(
        "POST", "/api/admin/modules/communication.smtp/enable", expected=409
    )
    expect(
        locked["detail"]["code"] == "pilot_module_locked",
        "SMTP pilot lock can be bypassed",
    )
    first_send_body = {
        "recipient": "billing@example.invalid",
        "invoice_number": invoice["invoice_number"],
        "total": invoice["total"],
        "pdf_reviewed": True,
        "resend": False,
    }
    locked_send = api.request(
        "POST",
        f"/api/invoices/{invoice['id']}/send",
        first_send_body,
        expected=409,
        headers={"Idempotency-Key": "full-check-first-send"},
    )
    expect(
        locked_send["detail"]["code"] == "pilot_module_locked",
        "disabled SMTP path did not report its locked state",
    )
    messages = fixture_request(smtp_api_url, "GET", "/api/messages")
    expect(messages == [], "locked SMTP path emitted an external message")
    expect(
        api.request("GET", f"/api/invoices/{invoice['id']}/send-attempts") == [],
        "locked SMTP path persisted a send attempt",
    )
    sent = api.request(
        "PUT",
        f"/api/invoices/{invoice['id']}/status",
        {
            "status": "sent",
            "pdf_reviewed": True,
            "manual_delivery_confirmed": True,
        },
    )
    expect(sent["status"] == "sent" and sent["sent_at"] is not None, "manual delivery confirmation failed")
    paid = api.request("PUT", f"/api/invoices/{invoice['id']}/status", {"status": "paid"})
    expect(paid["paid_at"] is not None, "paid timestamp missing")
    api.request("PUT", f"/api/invoices/{invoice['id']}/status", {"status": "cancelled"}, expected=400)
    paid_locked_send = api.request(
        "POST",
        f"/api/invoices/{invoice['id']}/send",
        {**first_send_body, "resend": True},
        expected=409,
        headers={"Idempotency-Key": "full-check-send-after-paid"},
    )
    expect(
        paid_locked_send["detail"]["code"] == "pilot_module_locked",
        "SMTP pilot lock changed after manual invoice status updates",
    )
    expect(
        api.request("GET", f"/api/invoices/{invoice['id']}/send-attempts") == []
        and fixture_request(smtp_api_url, "GET", "/api/messages") == [],
        "paid-invoice SMTP probe created local or external send evidence",
    )

    png, jpeg = tiny_images()
    fixtures = [
        ("Synthetic PNG receipt", "receipt.png", "image/png", png),
        ("Synthetic JPEG receipt", "receipt.jpg", "image/jpeg", jpeg),
        ("Synthetic PDF receipt", "receipt.pdf", "application/pdf", b"%PDF-1.4\nsynthetic receipt\n%%EOF\n"),
    ]
    for description, filename, content_type, content in fixtures:
        expense = api.request(
            "POST",
            "/api/expenses",
            {"date": today, "description": description, "category": "Synthetic", "amount": "1.23"},
        )
        uploaded = api.upload(f"/api/expenses/{expense['id']}/receipt", filename, content_type, content)
        expect(uploaded["has_receipt"], f"{content_type} receipt not attached")

    for kind in ("time", "quotes", "invoices", "expenses"):
        content, headers = api.request("GET", f"/api/reports/{kind}.csv", raw=True)
        expect(content and "text/csv" in headers["Content-Type"], f"{kind} CSV missing")

    assistant_disabled = api.request("POST", "/api/admin/modules/sales.quote_assistant/disable")
    expect(assistant_disabled["state"] == "disabled", "assistant did not disable")
    repeated_disabled = api.request("POST", "/api/admin/modules/sales.quote_assistant/disable")
    expect(repeated_disabled["state"] == "disabled", "repeated disable failed")
    audit = api.request("GET", "/api/admin/modules/audit")
    expect(any(item["action"] == "enable_noop" for item in audit), "enable noop audit missing")
    expect(any(item["action"] == "disable_noop" for item in audit), "disable noop audit missing")
    api.request("POST", "/api/admin/modules/sales.quote_assistant/enable")
    verify_core(api, revision, backup_state="disabled")


def main() -> int:
    args = parse_args()
    api = Api(args.base_url, args.username, args.password, args.work_dir)
    api.login()
    if args.phase == "source":
        expect(bool(args.smtp_api_url), "--smtp-api-url is required for source phase")
        run_source(api, args.smtp_api_url, args.revision)
    elif args.phase == "enable-backup":
        backup = api.request("POST", "/api/admin/modules/backup.offsite/enable")
        expect(backup["state"] == "enabled", "configured offsite module did not enable")
        repeated = api.request("POST", "/api/admin/modules/backup.offsite/enable")
        expect(repeated["state"] == "enabled", "offsite enable is not idempotent")
    else:
        verify_core(api, args.revision, backup_state="enabled")
    print(f"api-flow: {args.phase} checks passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Failure, urllib.error.URLError, subprocess.CalledProcessError) as error:
        print(f"api-flow: {error}", file=sys.stderr)
        raise SystemExit(1)

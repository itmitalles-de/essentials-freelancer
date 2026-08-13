#!/usr/bin/env python3
import argparse
import base64
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
    expect(ready["schema_revision"] == "0005_operational_hardening", "schema mismatch")
    meta = api.request("GET", "/api/meta")
    expect(meta["product"] == "Essentials+ Freelancer", "product metadata mismatch")
    expect(meta["repository_revision"] == revision, "repository revision mismatch")
    clients = api.request("GET", "/api/clients?q=Synthetic%20Full%20Check")
    expect(len(clients) == 1, "restored client not unique/present")
    projects = api.request("GET", f"/api/projects?client_id={clients[0]['id']}")
    expect(len(projects) == 1 and projects[0]["hourly_rate"] == "123.45", "project/rate missing")
    invoices = api.request("GET", f"/api/invoices?client_id={clients[0]['id']}")
    expect(len(invoices) == 2, "invoice core count differs after restore")
    for invoice in invoices:
        document, _ = api.request("GET", f"/api/invoices/{invoice['id']}/pdf", raw=True)
        expect(document.startswith(b"%PDF-"), "restored invoice PDF is unavailable")
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
    report = api.request("GET", f"/api/reports/summary?client_id={clients[0]['id']}")
    expect(report["time"]["captured_hours"] == "2.50", "captured time differs")
    expect(report["invoices"]["statuses"]["paid"] == 1, "paid invoice differs")


def run_source(api: Api, smtp_api_url: str, revision: str) -> None:
    today = date.today().isoformat()
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
            "email": "billing@example.invalid",
            "hourly_rate": "88.00",
        },
    )
    project = api.request(
        "POST",
        "/api/projects",
        {
            "client_id": client["id"],
            "name": "Synthetic Full Check Project",
            "hourly_rate": "123.45",
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
            "project_id": project["id"],
            "date": today,
            "description": "Synthetic manual work",
            "duration_minutes": 120,
        },
    )

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
                "tax_rate": "19",
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
                {"description": "Synthetic service", "quantity": "2", "unit": "hours", "unit_price": "100", "tax_rate": "19"},
                {"description": "Synthetic material", "quantity": "3", "unit": "items", "unit_price": "25", "tax_rate": "7"},
            ],
        },
    )
    quote_pdf, _ = api.request("GET", f"/api/quotes/{quote['id']}/pdf", raw=True)
    verify_pdf(quote_pdf, os.path.join(api.work_dir, "quote.pdf"), [quote["quote_number"], "Synthetic service", "Synthetic material"])
    api.request("PUT", f"/api/quotes/{quote['id']}/status", {"status": "sent"})
    api.request("PUT", f"/api/quotes/{quote['id']}/status", {"status": "accepted"})
    converted = api.request("POST", f"/api/quotes/{quote['id']}/convert")
    repeated_conversion = api.request("POST", f"/api/quotes/{quote['id']}/convert")
    expect(converted["converted_invoice_id"] == repeated_conversion["converted_invoice_id"], "quote converted twice")

    invoice_headers = {"Idempotency-Key": "full-check-time-invoice"}
    invoice = api.request(
        "POST",
        "/api/invoices",
        {"client_id": client["id"], "time_entry_ids": [manual["id"]]},
        headers=invoice_headers,
    )
    repeated_invoice = api.request(
        "POST",
        "/api/invoices",
        {"client_id": client["id"], "time_entry_ids": [manual["id"]]},
        headers=invoice_headers,
    )
    expect(invoice["id"] == repeated_invoice["id"], "invoice command not idempotent")
    invoice_pdf, _ = api.request("GET", f"/api/invoices/{invoice['id']}/pdf", raw=True)
    verify_pdf(invoice_pdf, os.path.join(api.work_dir, "invoice.pdf"), [invoice["invoice_number"], "Synthetic manual work", "246,90"])

    fixture_request(smtp_api_url, "POST", "/api/reset", {})
    sent = api.request("POST", f"/api/invoices/{invoice['id']}/send")
    expect(sent["status"] == "sent", "SMTP success did not mark sent")
    api.request("POST", f"/api/invoices/{invoice['id']}/send")
    messages = fixture_request(smtp_api_url, "GET", "/api/messages")
    expect(len(messages) == 2, "repeated SMTP send not captured exactly twice")
    for message in messages:
        expect(message["to"] == ["billing@example.invalid"], "SMTP recipient differs")
        expect(message["subject"] == f"Rechnung {invoice['invoice_number']}", "SMTP subject differs")
        expect(len(message["attachments"]) == 1, "SMTP attachment missing")
        attachment = message["attachments"][0]
        expect(attachment["content_type"] == "application/pdf", "attachment MIME differs")
        expect(base64.b64decode(attachment["content_base64"]).startswith(b"%PDF-"), "attachment is not PDF")

    failure_invoices: list[tuple[int, int]] = []
    for index, mode in enumerate(("reject", "timeout", "disconnect"), start=1):
        entry = api.request(
            "POST",
            "/api/time-entries",
            {
                "client_id": client["id"],
                "project_id": project["id"],
                "date": today,
                "description": f"Synthetic SMTP {mode}",
                "duration_minutes": 5,
            },
        )
        failed_invoice = api.request(
            "POST",
            "/api/invoices",
            {"client_id": client["id"], "time_entry_ids": [entry["id"]]},
        )
        fixture_request(smtp_api_url, "POST", "/api/mode", {"mode": mode})
        api.request("POST", f"/api/invoices/{failed_invoice['id']}/send", expected=502)
        stored = api.request("GET", f"/api/invoices/{failed_invoice['id']}")
        expect(stored["status"] == "draft" and stored["sent_at"] is None, f"{mode} falsely marked sent")
        failure_invoices.append((failed_invoice["id"], entry["id"]))
    fixture_request(smtp_api_url, "POST", "/api/mode", {"mode": "success"})

    paid = api.request("PUT", f"/api/invoices/{invoice['id']}/status", {"status": "paid"})
    expect(paid["paid_at"] is not None, "paid timestamp missing")
    api.request("PUT", f"/api/invoices/{invoice['id']}/status", {"status": "cancelled"}, expected=400)
    api.request("POST", f"/api/invoices/{invoice['id']}/send", expected=400)

    # Remove failure-only drafts so the exported/restored core count stays deterministic.
    for invoice_id, entry_id in failure_invoices:
        api.request("DELETE", f"/api/invoices/{invoice_id}", expected=204)
        api.request("DELETE", f"/api/time-entries/{entry_id}", expected=204)

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

#!/usr/bin/env python3
"""Validate deployment evidence structure and prove configured secrets are absent."""

import json
import pathlib
import sys


def fail(message: str) -> None:
    raise SystemExit(f"deployment-evidence-check: {message}")


if len(sys.argv) != 3:
    fail("expected EVIDENCE_JSON ENV_FILE")

evidence_path = pathlib.Path(sys.argv[1])
env_path = pathlib.Path(sys.argv[2])
raw = evidence_path.read_text(encoding="utf-8")
evidence = json.loads(raw)

required_top_level = {
    "collected_at_utc",
    "hostname",
    "repository",
    "compose",
    "containers",
    "volume_roles",
    "application",
    "backup",
    "last_restore",
    "proxy_tls",
}
if not required_top_level.issubset(evidence):
    fail("required top-level fields are missing")
if not evidence["repository"].get("commit"):
    fail("repository revision is missing")
if not evidence["compose"].get("name"):
    fail("Compose project is missing")
if not evidence["containers"]:
    fail("container evidence is missing")
if not evidence["volume_roles"].get("database"):
    fail("database volume was not identified")
if not evidence["volume_roles"].get("documents"):
    fail("document volume was not identified")
meta = evidence["application"].get("meta") or {}
if meta.get("readiness") != "ready" or meta.get("build_time") in {None, "unknown"}:
    fail("application build/readiness metadata is incomplete")
if evidence["application"].get("database_schema_revision") != meta.get("schema_revision"):
    fail("database and application schema revisions differ")
if evidence["backup"].get("status") != "found":
    fail("latest export evidence is missing")
if evidence["proxy_tls"].get("status") != "reachable":
    fail("authorized proxy URL was not reachable")

sensitive_keys = {"POSTGRES_PASSWORD", "JWT_SECRET", "ADMIN_PASSWORD", "SMTP_PASSWORD"}
for line in env_path.read_text(encoding="utf-8").splitlines():
    key, separator, value = line.partition("=")
    if separator and key in sensitive_keys and value and value in raw:
        fail(f"value of {key} leaked into evidence")

for service in evidence["compose"]["services"].values():
    if "environment" in service:
        fail("rendered Compose environment values were retained")
    if not isinstance(service.get("environment_keys"), list):
        fail("redacted Compose environment-key inventory is missing")

print("deployment-evidence-check: JSON structure and secret redaction passed")

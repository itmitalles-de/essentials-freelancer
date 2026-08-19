#!/usr/bin/env python3
"""Collect read-only, secret-safe deployment evidence as JSON and Markdown."""

from __future__ import annotations

import argparse
import datetime as dt
import http.client
import json
import os
import pathlib
import socket
import ssl
import subprocess
import sys
import urllib.parse
from typing import Any


SAFE_META_FIELDS = {
    "product",
    "product_version",
    "schema_revision",
    "repository_revision",
    "build_time",
    "readiness",
}
SAFE_IMAGE_LABELS = {
    "org.opencontainers.image.created",
    "org.opencontainers.image.revision",
    "org.opencontainers.image.source",
    "org.opencontainers.image.title",
    "org.opencontainers.image.version",
}
SAFE_RESTORE_FIELDS = {
    "completed_at_utc",
    "source_repository_commit",
    "target_repository_commit",
    "database_counts_match",
    "document_hashes_match",
    "isolated_target",
    "result",
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def run(command: list[str], cwd: pathlib.Path | None = None) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False, ""
    return result.returncode == 0, result.stdout.strip()


def json_output(command: list[str], cwd: pathlib.Path | None = None) -> Any | None:
    ok, output = run(command, cwd)
    if not ok or not output:
        return None
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return None


def git_state(project_dir: pathlib.Path) -> dict[str, Any]:
    ok, commit = run(["git", "rev-parse", "HEAD"], project_dir)
    status_ok, status = run(["git", "status", "--porcelain"], project_dir)
    return {
        "commit": commit if ok else None,
        "dirty": bool(status) if status_ok else None,
        "dirty_entry_count": len(status.splitlines()) if status_ok and status else 0,
    }


def compose_command(args: argparse.Namespace) -> list[str]:
    command = ["docker", "compose", "--project-directory", str(args.project_dir)]
    if args.env_file:
        command.extend(["--env-file", str(args.env_file)])
    for compose_file in args.compose_file:
        command.extend(["-f", str(compose_file)])
    return command


def redacted_compose(config: dict[str, Any]) -> dict[str, Any]:
    services: dict[str, Any] = {}
    for name, service in sorted((config.get("services") or {}).items()):
        environment = service.get("environment") or {}
        if isinstance(environment, list):
            environment_keys = sorted(str(item).split("=", 1)[0] for item in environment)
        else:
            environment_keys = sorted(str(key) for key in environment)
        volumes = []
        for volume in service.get("volumes") or []:
            if isinstance(volume, str):
                source, _, target = volume.partition(":")
                volumes.append({"source": source, "target": target or None})
            elif isinstance(volume, dict):
                volumes.append(
                    {
                        key: volume.get(key)
                        for key in ("type", "source", "target", "read_only")
                        if key in volume
                    }
                )
        build = service.get("build")
        if isinstance(build, dict):
            safe_build = {
                key: build.get(key)
                for key in ("context", "dockerfile", "target")
                if build.get(key) is not None
            }
            safe_build["argument_keys"] = sorted((build.get("args") or {}).keys())
        else:
            safe_build = build
        services[name] = {
            "image": service.get("image"),
            "build": safe_build,
            "environment_keys": environment_keys,
            "ports": service.get("ports") or [],
            "volumes": volumes,
            "networks": sorted((service.get("networks") or {}).keys()),
            "profiles": service.get("profiles") or [],
            "depends_on": sorted((service.get("depends_on") or {}).keys()),
            "healthcheck_configured": bool(service.get("healthcheck")),
        }
    return {
        "name": config.get("name"),
        "services": services,
        "volumes": sorted((config.get("volumes") or {}).keys()),
        "networks": sorted((config.get("networks") or {}).keys()),
    }


def container_evidence(base: list[str], services: list[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    containers: list[dict[str, Any]] = []
    volume_roles: dict[str, Any] = {"database": None, "documents": None}
    for service in services:
        ok, ids_output = run([*base, "ps", "--all", "--quiet", service])
        if not ok:
            continue
        for container_id in filter(None, ids_output.splitlines()):
            inspected = json_output(["docker", "inspect", container_id])
            if not isinstance(inspected, list) or not inspected:
                continue
            item = inspected[0]
            state = item.get("State") or {}
            health = state.get("Health") or {}
            image_id = item.get("Image")
            image_info = json_output(["docker", "image", "inspect", image_id]) if image_id else None
            image = image_info[0] if isinstance(image_info, list) and image_info else {}
            labels = (image.get("Config") or {}).get("Labels") or {}
            mounts = []
            for mount in item.get("Mounts") or []:
                safe_mount = {
                    "type": mount.get("Type"),
                    "name": mount.get("Name"),
                    "source": mount.get("Source"),
                    "destination": mount.get("Destination"),
                    "read_write": mount.get("RW"),
                }
                mounts.append(safe_mount)
                if mount.get("Destination") == "/var/lib/postgresql/data":
                    volume_roles["database"] = safe_mount
                elif mount.get("Destination") == "/data/invoices":
                    volume_roles["documents"] = safe_mount
            containers.append(
                {
                    "service": service,
                    "name": str(item.get("Name") or "").lstrip("/"),
                    "container_id": str(item.get("Id") or "")[:12] or None,
                    "image_name": (item.get("Config") or {}).get("Image"),
                    "image_id": image_id,
                    "image_digests": sorted(image.get("RepoDigests") or []),
                    "image_labels": {
                        key: labels[key]
                        for key in sorted(SAFE_IMAGE_LABELS)
                        if labels.get(key)
                    },
                    "status": state.get("Status"),
                    "health": health.get("Status") if health else "not_configured",
                    "restart_count": item.get("RestartCount"),
                    "started_at": state.get("StartedAt"),
                    "mounts": mounts,
                }
            )
    return containers, volume_roles


def application_state(base: list[str]) -> dict[str, Any]:
    meta_command = [
        *base,
        "exec",
        "-T",
        "backend",
        "python",
        "-c",
        (
            "import json,urllib.request;"
            "print(json.dumps(json.load(urllib.request.urlopen("
            "'http://127.0.0.1:8000/api/meta',timeout=3))))"
        ),
    ]
    meta = json_output(meta_command)
    safe_meta = (
        {key: meta.get(key) for key in sorted(SAFE_META_FIELDS)}
        if isinstance(meta, dict)
        else None
    )
    ok, schema = run(
        [
            *base,
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            "tracker",
            "-d",
            "tracker",
            "-At",
            "-c",
            "SELECT version_num FROM alembic_version;",
        ]
    )
    return {
        "meta": safe_meta,
        "database_schema_revision": schema if ok and schema else None,
        "meta_available": safe_meta is not None,
        "schema_available": bool(ok and schema),
    }


def backup_state(root: pathlib.Path | None, collected_at: dt.datetime) -> dict[str, Any]:
    if root is None:
        return {"status": "not_configured", "latest_export_utc": None, "age_seconds": None}
    try:
        manifests = [path for path in root.glob("*/MANIFEST.txt") if path.is_file()]
    except OSError:
        manifests = []
    if not manifests:
        return {"status": "no_export_found", "latest_export_utc": None, "age_seconds": None}
    latest = max(manifests, key=lambda path: path.stat().st_mtime)
    modified = dt.datetime.fromtimestamp(latest.stat().st_mtime, tz=dt.timezone.utc)
    return {
        "status": "found",
        "latest_export_utc": modified.replace(microsecond=0).isoformat(),
        "age_seconds": max(0, int((collected_at - modified).total_seconds())),
    }


def restore_state(path: pathlib.Path | None) -> dict[str, Any]:
    if path is None:
        return {"status": "no_evidence_file_configured"}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "evidence_unreadable"}
    if not isinstance(raw, dict):
        return {"status": "evidence_invalid"}
    return {
        "status": "evidence_loaded",
        **{key: raw.get(key) for key in sorted(SAFE_RESTORE_FIELDS)},
    }


def proxy_tls_state(url: str | None) -> dict[str, Any]:
    if not url:
        return {"status": "not_authorized_or_configured"}
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        return {"status": "invalid_safe_url"}
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path.rstrip("/") + "/api/ready"
    try:
        if parsed.scheme == "https":
            connection: http.client.HTTPConnection = http.client.HTTPSConnection(
                parsed.hostname,
                port,
                timeout=5,
                context=ssl.create_default_context(),
            )
        else:
            connection = http.client.HTTPConnection(parsed.hostname, port, timeout=5)
        connection.request("GET", path)
        response = connection.getresponse()
        response.read(4096)
        certificate = None
        if parsed.scheme == "https" and getattr(connection, "sock", None):
            certificate = connection.sock.getpeercert()  # type: ignore[union-attr]
        connection.close()
        return {
            "status": "reachable",
            "scheme": parsed.scheme,
            "http_status": response.status,
            "tls_verified": parsed.scheme == "https",
            "tls_not_after": certificate.get("notAfter") if certificate else None,
        }
    except (OSError, ssl.SSLError, http.client.HTTPException):
        return {
            "status": "unreachable_or_tls_invalid",
            "scheme": parsed.scheme,
            "http_status": None,
            "tls_verified": False,
            "tls_not_after": None,
        }


def markdown(evidence: dict[str, Any]) -> str:
    git = evidence["repository"]
    app = evidence["application"]
    meta = app.get("meta") or {}
    backup = evidence["backup"]
    restore = evidence["last_restore"]
    lines = [
        "# Deployment State",
        "",
        "> Read-only evidence. Secret values and Compose environment values are intentionally omitted.",
        "",
        f"- Collected (UTC): `{evidence['collected_at_utc']}`",
        f"- Hostname: `{evidence['hostname']}`",
        f"- Repository commit: `{git.get('commit') or 'unknown'}`",
        f"- Dirty worktree: `{git.get('dirty')}` ({git.get('dirty_entry_count')} entries)",
        f"- Compose project: `{evidence['compose'].get('name') or 'unknown'}`",
        f"- Product version: `{meta.get('product_version') or 'unknown'}`",
        f"- Repository revision reported by app: `{meta.get('repository_revision') or 'unknown'}`",
        f"- Build time: `{meta.get('build_time') or 'unknown'}`",
        f"- Schema (database/app): `{app.get('database_schema_revision') or 'unknown'}` / `{meta.get('schema_revision') or 'unknown'}`",
        f"- Readiness: `{meta.get('readiness') or 'unknown'}`",
        f"- Latest export: `{backup.get('latest_export_utc') or backup.get('status')}`",
        f"- Last restore evidence: `{restore.get('status')}`",
        f"- Proxy/TLS: `{evidence['proxy_tls'].get('status')}`",
        "",
        "## Containers",
        "",
        "| Service | Container | Status | Health | Restarts | Image ID |",
        "|---|---|---|---|---:|---|",
    ]
    for item in evidence["containers"]:
        lines.append(
            "| {service} | {name} | {status} | {health} | {restart_count} | `{image_id}` |".format(
                **{key: item.get(key) for key in ("service", "name", "status", "health", "restart_count", "image_id")}
            )
        )
    lines.extend(
        [
            "",
            "## Volume roles",
            "",
            f"- Database: `{json.dumps(evidence['volume_roles']['database'], sort_keys=True)}`",
            f"- Documents: `{json.dumps(evidence['volume_roles']['documents'], sort_keys=True)}`",
            "",
            "The accompanying JSON contains the redacted rendered Compose structure, image digests, safe image labels, mounts, and machine-readable gate evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    default_project = pathlib.Path(__file__).resolve().parents[1]
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    parser.add_argument("--project-dir", type=pathlib.Path, default=default_project)
    parser.add_argument("--env-file", type=pathlib.Path)
    parser.add_argument("--compose-file", type=pathlib.Path, action="append", default=[])
    parser.add_argument("--backup-root", type=pathlib.Path)
    parser.add_argument("--restore-evidence", type=pathlib.Path)
    parser.add_argument("--public-url")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.project_dir = args.project_dir.resolve()
    if not args.compose_file:
        args.compose_file = [args.project_dir / "docker-compose.yml"]
    base = compose_command(args)
    config = json_output([*base, "config", "--format", "json"], args.project_dir)
    if not isinstance(config, dict):
        print("deployment-state: Compose configuration could not be rendered", file=sys.stderr)
        return 1
    redacted = redacted_compose(config)
    services = sorted(redacted["services"])
    containers, volume_roles = container_evidence(base, services)
    collected_at = dt.datetime.now(dt.timezone.utc)
    evidence = {
        "format_version": 1,
        "collected_at_utc": collected_at.replace(microsecond=0).isoformat(),
        "hostname": socket.gethostname(),
        "repository": git_state(args.project_dir),
        "compose": redacted,
        "containers": containers,
        "volume_roles": volume_roles,
        "application": application_state(base),
        "backup": backup_state(args.backup_root, collected_at),
        "last_restore": restore_state(args.restore_evidence),
        "proxy_tls": proxy_tls_state(args.public_url),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(args.output_dir, 0o700)
    json_path = args.output_dir / "deployment-state.json"
    markdown_path = args.output_dir / "deployment-state.md"
    json_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown(evidence), encoding="utf-8")
    os.chmod(json_path, 0o600)
    os.chmod(markdown_path, 0o600)
    print(f"deployment-state: wrote {json_path} and {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

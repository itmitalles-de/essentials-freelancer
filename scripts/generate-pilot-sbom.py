#!/usr/bin/env python3
"""Generate a dependency-lock-derived CycloneDX SBOM for a pilot build."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import pathlib
import re
import subprocess
import urllib.parse
import uuid
import xml.etree.ElementTree as ET


def component_ref(kind: str, name: str, version: str) -> str:
    return f"{kind}:{name}@{version}"


def python_components(root: pathlib.Path) -> list[dict]:
    components = []
    seen = set()
    for requirements in (root / "backend/requirements.txt", root / "backend/requirements-dev.txt"):
        for raw_line in requirements.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith(("#", "-r ")) or "==" not in line:
                continue
            raw_name, version = line.split("==", 1)
            name = raw_name.split("[", 1)[0].lower().replace("_", "-")
            ref = component_ref("pypi", name, version)
            if ref in seen:
                continue
            seen.add(ref)
            components.append(
                {
                    "type": "library",
                    "bom-ref": ref,
                    "name": name,
                    "version": version,
                    "purl": f"pkg:pypi/{name}@{version}",
                    "properties": [{"name": "essentials:ecosystem", "value": "python"}],
                }
            )
    return components


def npm_components(root: pathlib.Path) -> list[dict]:
    lock = json.loads((root / "frontend/package-lock.json").read_text(encoding="utf-8"))
    components = []
    seen = set()
    for path, package in sorted((lock.get("packages") or {}).items()):
        if not path or not package.get("version"):
            continue
        name = package.get("name") or path.rsplit("node_modules/", 1)[-1]
        version = package["version"]
        ref = component_ref("npm", name, version)
        if ref in seen:
            continue
        seen.add(ref)
        component = {
            "type": "library",
            "bom-ref": ref,
            "name": name,
            "version": version,
            "purl": f"pkg:npm/{urllib.parse.quote(name, safe='@/')}@{version}",
            "properties": [{"name": "essentials:ecosystem", "value": "npm"}],
        }
        integrity = package.get("integrity", "")
        if integrity.startswith("sha512-"):
            try:
                digest = base64.b64decode(integrity[7:], validate=True).hex().upper()
                component["hashes"] = [{"alg": "SHA-512", "content": digest}]
            except ValueError:
                pass
        components.append(component)
    return components


def gradle_components(root: pathlib.Path) -> list[dict]:
    metadata = root / "android/gradle/verification-metadata.xml"
    tree = ET.parse(metadata)
    namespace = {"v": "https://schema.gradle.org/dependency-verification"}
    components = []
    for item in tree.findall(".//v:component", namespace):
        group = item.attrib["group"]
        name = item.attrib["name"]
        version = item.attrib["version"]
        ref = component_ref("maven", f"{group}:{name}", version)
        artifact_hashes = []
        for artifact in item.findall("v:artifact", namespace):
            checksum = artifact.find("v:sha256", namespace)
            if checksum is not None:
                artifact_hashes.append(f"{artifact.attrib['name']}={checksum.attrib['value']}")
        components.append(
            {
                "type": "library",
                "bom-ref": ref,
                "group": group,
                "name": name,
                "version": version,
                "purl": f"pkg:maven/{urllib.parse.quote(group, safe='.')}/{urllib.parse.quote(name)}@{version}",
                "properties": [
                    {"name": "essentials:ecosystem", "value": "gradle"},
                    *[
                        {"name": "essentials:verified-artifact-sha256", "value": value}
                        for value in artifact_hashes
                    ],
                ],
            }
        )
    return components


def image_components(root: pathlib.Path) -> list[dict]:
    sources = [
        root / "backend/Dockerfile",
        root / "frontend/Dockerfile",
        root / "tests/full-check/smtp-fixture/Dockerfile",
        root / "docker-compose.yml",
        root / "scripts/full-check.sh",
    ]
    pattern = re.compile(r"(?P<name>[A-Za-z0-9][A-Za-z0-9./_-]*):(?P<tag>[A-Za-z0-9._-]+)@sha256:(?P<digest>[0-9a-f]{64})")
    components = []
    seen = set()
    for source in sources:
        content = source.read_text(encoding="utf-8")
        for match in pattern.finditer(content):
            name, tag, digest = match.group("name", "tag", "digest")
            ref = component_ref("oci", name, digest)
            if ref in seen:
                continue
            seen.add(ref)
            components.append(
                {
                    "type": "container",
                    "bom-ref": ref,
                    "name": name,
                    "version": tag,
                    "hashes": [{"alg": "SHA-256", "content": digest.upper()}],
                    "properties": [
                        {"name": "essentials:ecosystem", "value": "container"},
                        {"name": "essentials:image-tag", "value": tag},
                    ],
                }
            )
    if len(components) < 7:
        raise SystemExit("pilot-sbom: expected container image digest pins are missing")
    return components


def action_components(root: pathlib.Path) -> list[dict]:
    workflow = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    unpinned = re.findall(r"uses:\s*([^\s#]+)@(?![0-9a-f]{40}(?:\s|$))([^\s#]+)", workflow)
    if unpinned:
        raise SystemExit(f"pilot-sbom: unpinned GitHub Actions remain: {unpinned}")
    components = []
    seen = set()
    for name, revision in re.findall(r"uses:\s*([^\s#]+)@([0-9a-f]{40})", workflow):
        ref = component_ref("github-action", name, revision)
        if ref in seen:
            continue
        seen.add(ref)
        components.append(
            {
                "type": "application",
                "bom-ref": ref,
                "name": name,
                "version": revision,
                "purl": f"pkg:github/{name}@{revision}",
                "properties": [{"name": "essentials:ecosystem", "value": "github-actions"}],
            }
        )
    return components


def git_revision(root: pathlib.Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--revision")
    parser.add_argument(
        "--project-dir", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    root = args.project_dir.resolve()
    revision = args.revision or git_revision(root)
    components = [
        *python_components(root),
        *npm_components(root),
        *gradle_components(root),
        *image_components(root),
        *action_components(root),
    ]
    components.sort(key=lambda item: item["bom-ref"])
    root_ref = f"application:essentials-freelancer@{revision}"
    document = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, root_ref)}",
        "version": 1,
        "metadata": {
            "timestamp": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
            "component": {
                "type": "application",
                "bom-ref": root_ref,
                "name": "Essentials+ Freelancer",
                "version": revision,
            },
            "properties": [
                {"name": "essentials:scope", "value": "first-internal-pilot"},
                {"name": "essentials:source", "value": "https://github.com/itmitalles-de/essentials-freelancer"},
            ],
        },
        "components": components,
        "dependencies": [
            {"ref": root_ref, "dependsOn": [item["bom-ref"] for item in components]}
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"pilot-sbom: wrote {len(components)} components to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

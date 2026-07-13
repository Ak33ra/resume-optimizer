#!/usr/bin/env python3
"""Validate claim-to-source provenance markers in a generated resume."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


CLAIM_COMMANDS = (
    "resumeItem",
    "resumeSubheading",
    "resumeSubSubheading",
    "resumeProjectHeading",
)
MARKER = re.compile(r"^\s*%\s*source:\s*([a-zA-Z0-9_.-]+)\s*$")
COMMAND = re.compile(r"\\(" + "|".join(CLAIM_COMMANDS) + r")\b")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def active_claim_markers(tex: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Return active claim commands with their immediately preceding marker."""
    document = re.search(r"\\begin\s*\{document\}", tex)
    body = tex[document.end():] if document else tex
    claims = []
    errors = []
    pending_marker: tuple[str, int] | None = None
    for line_number, line in enumerate(body.splitlines(), start=1):
        stripped = line.strip()
        marker = MARKER.match(line)
        if marker:
            pending_marker = (marker.group(1), line_number)
            continue
        if not stripped:
            continue
        if stripped.startswith("%"):
            continue
        command = COMMAND.search(line)
        if command:
            if pending_marker is None:
                errors.append(
                    f"line {line_number}: active \\{command.group(1)} has no preceding % source: <id>"
                )
            else:
                claims.append(
                    {
                        "id": pending_marker[0],
                        "line": line_number,
                        "command": command.group(1),
                    }
                )
                pending_marker = None
        elif pending_marker is not None:
            errors.append(
                f"line {pending_marker[1]}: source marker is not followed by a claim command"
            )
            pending_marker = None
    if pending_marker is not None:
        errors.append(f"line {pending_marker[1]}: dangling source marker")
    return claims, errors


def _safe_source_path(root: Path, value: str) -> Path | None:
    source_root = (root / "source_material").resolve()
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(source_root)
    except ValueError:
        return None
    return candidate


def validate_provenance(tex_path: Path, manifest_path: Path, root: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        tex = tex_path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"passed": False, "errors": [f"cannot read resume source: {exc}"], "claims": []}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"passed": False, "errors": [f"cannot read provenance manifest: {exc}"], "claims": []}

    claims, marker_errors = active_claim_markers(tex)
    errors.extend(marker_errors)
    if manifest.get("schema_version") != 1:
        errors.append("manifest.schema_version must be 1")
    manifest_claims = manifest.get("claims")
    if not isinstance(manifest_claims, dict):
        errors.append("manifest.claims must be an object keyed by claim ID")
        manifest_claims = {}

    seen: set[str] = set()
    for claim in claims:
        claim_id = claim["id"]
        if claim_id in seen:
            errors.append(f"duplicate active claim ID: {claim_id}")
        seen.add(claim_id)
        entry = manifest_claims.get(claim_id)
        if not isinstance(entry, dict):
            errors.append(f"claim {claim_id}: missing manifest entry")
            continue
        sources = entry.get("sources")
        if not isinstance(sources, list) or not sources:
            errors.append(f"claim {claim_id}: sources must be a non-empty array")
            continue
        for index, source in enumerate(sources, start=1):
            prefix = f"claim {claim_id}, source {index}"
            if not isinstance(source, dict):
                errors.append(f"{prefix}: must be an object")
                continue
            path_value = source.get("file")
            evidence = source.get("evidence")
            section = source.get("section")
            if not isinstance(path_value, str):
                errors.append(f"{prefix}: file must be a string")
                continue
            source_path = _safe_source_path(root, path_value)
            if source_path is None:
                errors.append(f"{prefix}: file must be inside source_material/")
                continue
            if not source_path.is_file():
                errors.append(f"{prefix}: file does not exist: {path_value}")
                continue
            if not isinstance(section, str) or not section.strip():
                errors.append(f"{prefix}: section must be a non-empty locator")
            if not isinstance(evidence, str) or not evidence.strip():
                errors.append(f"{prefix}: evidence must be a non-empty source excerpt")
                continue
            source_text = source_path.read_text(encoding="utf-8", errors="replace")
            if normalize(evidence) not in normalize(source_text):
                errors.append(f"{prefix}: evidence text not found in {path_value}")

    unused = sorted(set(manifest_claims) - seen)
    return {
        "passed": not errors,
        "errors": errors,
        "claims": claims,
        "unused_manifest_claims": unused,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tex")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    output = validate_provenance(
        Path(args.tex), Path(args.manifest), Path(args.root).resolve()
    )
    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(f"PROVENANCE: {'PASS' if output['passed'] else 'FAIL'} "
              f"({len(output['claims'])} active claims)")
        for error in output["errors"]:
            print("  - " + error)
        if output["unused_manifest_claims"]:
            print("  advisory: unused manifest claims: " + ", ".join(output["unused_manifest_claims"]))
    raise SystemExit(0 if output["passed"] else 1)


if __name__ == "__main__":
    main()

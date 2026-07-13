#!/usr/bin/env python3
"""CLI for preparing private job-description snapshots from job_targets.csv."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .job_intake import (
        FetchError,
        IntakeError,
        JobTarget,
        atomic_write,
        document_for,
        fetch_target,
        finalize_manual,
        load_targets,
        manual_stub,
        target_by_slug,
        validate_document,
    )
except ImportError:
    from job_intake import (
        FetchError,
        IntakeError,
        JobTarget,
        atomic_write,
        document_for,
        fetch_target,
        finalize_manual,
        load_targets,
        manual_stub,
        target_by_slug,
        validate_document,
    )


def paths_for(root: Path, slug: str) -> tuple[Path, Path]:
    return root / "job_descriptions" / f"{slug}.md", root / "resumes" / f"{slug}.state.json"


def manual_message(path: Path, slug: str) -> str:
    return (
        f"Manual intervention required: populate {path} with the complete posting, "
        f"then run `python3 scripts/jobs.py finalize {slug}`. Optimization is blocked "
        "until validation passes."
    )


def target_mismatches(result, target: JobTarget) -> list[str]:
    mismatches = []
    if result.metadata.get("family") != target.family:
        mismatches.append(
            f"family {result.metadata.get('family')!r} does not match CSV family {target.family!r}"
        )
    if result.metadata.get("source_url") != target.url:
        mismatches.append("source_url does not match the selected CSV URL")
    return mismatches


def prepare(root: Path, target: JobTarget) -> dict[str, object]:
    destination, _ = paths_for(root, target.slug)
    if destination.exists():
        result = validate_document(destination, target.slug)
        mismatches = target_mismatches(result, target) if result.valid else []
        if result.valid and not mismatches:
            return {"slug": target.slug, "status": "ready", "path": str(destination), "source": "existing"}
        raise IntakeError(
            f"existing job description is not ready: {' | '.join((*result.errors, *mismatches))}. "
            + manual_message(destination, target.slug)
        )
    try:
        fetched = fetch_target(target)
        content = document_for(target, fetched)
        atomic_write(destination, content)
        result = validate_document(destination, target.slug)
        if not result.valid:
            destination.unlink(missing_ok=True)
            raise FetchError("rendered description failed validation: " + " | ".join(result.errors))
    except (FetchError, IntakeError) as exc:
        if not destination.exists():
            atomic_write(destination, manual_stub(target))
        raise IntakeError(f"automatic retrieval failed for {target.slug}: {exc}. {manual_message(destination, target.slug)}") from exc
    return {
        "slug": target.slug,
        "status": "ready",
        "path": str(destination),
        "source": fetched.source_type,
        "warnings": list(fetched.warnings) + list(result.warnings),
    }


def refresh(root: Path, target: JobTarget, accept_change: bool) -> dict[str, object]:
    destination, state = paths_for(root, target.slug)
    current = validate_document(destination, target.slug)
    if not current.valid:
        raise IntakeError(f"current description is not ready: {' | '.join(current.errors)}")
    fetched = fetch_target(target)
    content = document_for(target, fetched)
    temporary = destination.with_name(destination.name + ".refresh")
    atomic_write(temporary, content)
    try:
        candidate = validate_document(temporary, target.slug)
    finally:
        temporary.unlink(missing_ok=True)
    if not candidate.valid:
        raise IntakeError("refreshed description failed validation: " + " | ".join(candidate.errors))
    compared_fields = (
        "company", "role", "family", "location", "canonical_url", "external_id",
        "published_at", "content_sha256",
    )
    changed_fields = [
        field for field in compared_fields
        if current.metadata.get(field) != candidate.metadata.get(field)
    ]
    changed = bool(changed_fields)
    if changed and accept_change:
        if state.exists():
            raise IntakeError(
                f"cannot replace the JD while optimization state exists at {state}; "
                "use a new slug, or archive the old state and rerun the baseline panel/init workflow"
            )
        atomic_write(destination, content)
    return {
        "slug": target.slug,
        "status": "changed" if changed else "unchanged",
        "accepted": bool(changed and accept_change),
        "changed_fields": changed_fields,
        "current_sha256": current.metadata["content_sha256"],
        "fetched_sha256": candidate.metadata["content_sha256"],
        "warnings": list(fetched.warnings) + list(candidate.warnings),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--targets", type=Path, help="defaults to <root>/job_targets.csv")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("slug", nargs="?")
    prepare_parser.add_argument("--all", action="store_true")
    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("slug", nargs="?")
    validate_parser.add_argument("--all", action="store_true")
    status_parser = sub.add_parser("status")
    status_parser.add_argument("slug", nargs="?")
    refresh_parser = sub.add_parser("refresh")
    refresh_parser.add_argument("slug")
    refresh_parser.add_argument("--accept-change", action="store_true")
    finalize_parser = sub.add_parser("finalize")
    finalize_parser.add_argument("slug")
    return parser


def _selected(targets: list[JobTarget], slug: str | None, all_targets: bool) -> list[JobTarget]:
    if bool(slug) == bool(all_targets):
        raise IntakeError("provide exactly one slug or --all")
    if slug:
        return [target_by_slug(targets, slug)]
    return sorted((target for target in targets if target.enabled), key=lambda value: (-value.priority, value.slug))


def _print(results: object, as_json: bool) -> None:
    if as_json:
        print(json.dumps(results, indent=2))
        return
    values = results if isinstance(results, list) else [results]
    for value in values:
        if not isinstance(value, dict):
            print(value)
            continue
        details = " ".join(f"{key}={item}" for key, item in value.items() if key not in {"slug", "warnings"})
        print(f"{value.get('slug', '-')}: {details}")
        for warning in value.get("warnings", []):
            print(f"  warning: {warning}")


def main() -> None:
    args = build_parser().parse_args()
    root = Path(args.root).resolve()
    targets_path = args.targets.resolve() if args.targets else root / "job_targets.csv"
    try:
        if args.command == "finalize":
            destination, _ = paths_for(root, args.slug)
            result = finalize_manual(destination, args.slug)
            output: object = {"slug": args.slug, "status": "ready", "path": str(destination), "warnings": list(result.warnings)}
        else:
            targets = load_targets(targets_path)
            if args.command == "prepare":
                output = [prepare(root, target) for target in _selected(targets, args.slug, args.all)]
            elif args.command == "validate":
                output = []
                for target in _selected(targets, args.slug, args.all):
                    destination, _ = paths_for(root, target.slug)
                    result = validate_document(destination, target.slug)
                    mismatches = target_mismatches(result, target) if result.valid else []
                    output.append({
                        "slug": target.slug,
                        "status": "ready" if result.valid and not mismatches else "invalid",
                        "path": str(destination),
                        "errors": list(result.errors) + mismatches,
                        "warnings": list(result.warnings),
                    })
                if any(value["status"] != "ready" for value in output):
                    _print(output, args.json)
                    raise SystemExit(1)
            elif args.command == "refresh":
                output = refresh(root, target_by_slug(targets, args.slug), args.accept_change)
            else:
                selected = [target_by_slug(targets, args.slug)] if args.slug else sorted(
                    (target for target in targets if target.enabled), key=lambda value: (-value.priority, value.slug)
                )
                output = []
                for target in selected:
                    destination, _ = paths_for(root, target.slug)
                    result = validate_document(destination, target.slug)
                    mismatches = target_mismatches(result, target) if result.valid else []
                    output.append({
                        "slug": target.slug,
                        "status": "ready" if result.valid and not mismatches else "missing" if not destination.exists() else "manual_required",
                        "path": str(destination),
                        "errors": list(result.errors) + mismatches,
                    })
        _print(output, args.json)
    except IntakeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

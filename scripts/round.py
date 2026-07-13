#!/usr/bin/env python3
"""Stateful orchestration for one resume-optimization target.

This script owns mechanical state transitions and file promotion. The optimizer
still owns editing, source-aware truth review, and the hypothesis for each round.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from .job_intake import validate_document
    from .provenance_check import validate_provenance
    from .scoring import DIMS, FAMILY_ADJUSTMENTS, keep_decision, weights_for
except ImportError:  # Direct execution
    from job_intake import validate_document
    from provenance_check import validate_provenance
    from scoring import DIMS, FAMILY_ADJUSTMENTS, keep_decision, weights_for


STATE_SCHEMA_VERSION = 2


class RoundError(RuntimeError):
    pass


@dataclass(frozen=True)
class TargetPaths:
    root: Path
    slug: str

    @property
    def jd(self) -> Path:
        return self.root / "job_descriptions" / f"{self.slug}.md"

    @property
    def canonical(self) -> Path:
        return self.root / "resumes" / f"{self.slug}_resume.tex"

    @property
    def candidate(self) -> Path:
        return self.root / "resumes" / f"{self.slug}_resume.candidate.tex"

    @property
    def canonical_pdf(self) -> Path:
        return self.root / "resumes" / f"{self.slug}_resume.pdf"

    @property
    def candidate_pdf(self) -> Path:
        return self.root / "resumes" / f"{self.slug}_resume.candidate.pdf"

    @property
    def output_pdf(self) -> Path:
        return self.root / "outputs" / f"{self.slug}_resume.pdf"

    @property
    def provenance(self) -> Path:
        return self.root / "resumes" / f"{self.slug}_provenance.json"

    @property
    def candidate_provenance(self) -> Path:
        return self.root / "resumes" / f"{self.slug}_provenance.candidate.json"

    @property
    def keywords(self) -> Path:
        return self.root / "resumes" / f"{self.slug}.kw.txt"

    @property
    def state(self) -> Path:
        return self.root / "resumes" / f"{self.slug}.state.json"

    @property
    def log(self) -> Path:
        return self.root / "optimization_log.md"


def sha256_text(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8", errors="replace").encode()).hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=destination.name + ".", dir=destination.parent)
    os.close(fd)
    try:
        shutil.copy2(source, temp_name)
        os.replace(temp_name, destination)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RoundError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RoundError(f"expected a JSON object in {path}")
    return value


def load_state(paths: TargetPaths) -> dict[str, Any]:
    state = load_json(paths.state)
    if state.get("schema_version") != STATE_SCHEMA_VERSION:
        raise RoundError(f"unsupported state schema in {paths.state}")
    if state.get("slug") != paths.slug:
        raise RoundError(f"state slug does not match {paths.slug}")
    return state


def validate_job_description(paths: TargetPaths, expected_family: str | None = None) -> str:
    if not paths.jd.is_file():
        raise RoundError(
            f"job description is missing: {paths.jd}; run "
            f"`python3 scripts/jobs.py prepare {paths.slug}` or populate it manually"
        )
    result = validate_document(paths.jd, paths.slug)
    if not result.valid:
        raise RoundError(
            "job description is not ready: " + " | ".join(result.errors) + "; run "
            f"`python3 scripts/jobs.py finalize {paths.slug}` after correcting it"
        )
    if expected_family and result.metadata.get("family") != expected_family:
        raise RoundError(
            f"job description family {result.metadata.get('family')!r} does not match "
            f"optimization family {expected_family!r}"
        )
    return sha256_text(paths.jd)


def assert_job_description_frozen(paths: TargetPaths, state: dict[str, Any]) -> None:
    expected = state.get("job_description", {}).get("sha256")
    actual = validate_job_description(paths, state.get("family"))
    if not expected or actual != expected:
        raise RoundError(
            "job description changed after baseline; use a new slug, or archive the old "
            "state and rerun the baseline panel/init workflow"
        )


def validate_panel_metadata(panel: dict[str, Any]) -> None:
    if panel.get("schema_version") != 2:
        raise RoundError("panel schema_version must be 2")
    metadata = panel.get("panel")
    if not isinstance(metadata, dict):
        raise RoundError("panel metadata is missing")
    completed = metadata.get("completed")
    families = metadata.get("reviewer_families")
    minimum = metadata.get("minimum_reviewers")
    optimizer = metadata.get("optimizer_family")
    if not isinstance(completed, list) or not all(isinstance(name, str) for name in completed):
        raise RoundError("panel completed-reviewer list is invalid")
    if not isinstance(families, dict) or any(name not in families for name in completed):
        raise RoundError("panel reviewer-family map is invalid")
    if not isinstance(minimum, int) or minimum < 1:
        raise RoundError("panel minimum-reviewer count is invalid")
    expected_valid = len(completed) >= minimum
    if metadata.get("valid") is not expected_valid:
        raise RoundError("panel validity does not match its completed-reviewer count")
    external_families = {
        families[name]
        for name in completed
        if families[name] not in (optimizer, "test")
    }
    expected_decorrelated = len(external_families) >= 2
    if metadata.get("decorrelated") is not expected_decorrelated:
        raise RoundError("panel diversity metadata is inconsistent")


def panel_scores(panel: dict[str, Any], identity: str | None = None) -> dict[str, Any]:
    validate_panel_metadata(panel)
    if not panel.get("panel", {}).get("valid"):
        raise RoundError("panel result is not valid")
    aggregate = panel.get("aggregate")
    if not isinstance(aggregate, dict):
        raise RoundError("panel result has no aggregate")
    if identity is not None:
        aggregate = aggregate.get(identity)
        if not isinstance(aggregate, dict):
            raise RoundError(f"panel result has no {identity} aggregate")
    dimensions = aggregate.get("dimensions")
    if not isinstance(dimensions, dict) or any(dim not in dimensions for dim in DIMS):
        raise RoundError("panel aggregate is missing score dimensions")
    return {
        "dimensions": {dim: float(dimensions[dim]) for dim in DIMS},
        "composite": float(aggregate["composite"]),
    }


def panel_label(panel: dict[str, Any]) -> str:
    meta = panel.get("panel", {})
    completed = meta.get("completed", [])
    families = meta.get("reviewer_families", {})
    reviewers = ", ".join(f"{name}:{families.get(name, '?')}" for name in completed)
    kind = "cross-family" if meta.get("decorrelated") else "correlated/simulated"
    return f"{kind} [{reviewers}]"


def validate_panel_target(panel: dict[str, Any], slug: str, family: str) -> None:
    validate_panel_metadata(panel)
    if panel.get("family") != family:
        raise RoundError(
            f"panel family {panel.get('family')!r} does not match target family {family!r}"
        )
    if panel.get("slug") not in (None, slug):
        raise RoundError(f"panel slug {panel.get('slug')!r} does not match {slug!r}")


def score_line(scores: dict[str, Any]) -> str:
    return ", ".join(f"{dim} {scores['dimensions'][dim]:.1f}" for dim in DIMS)


def prepend_log_entry(path: Path, entry: str) -> None:
    try:
        current = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RoundError(f"cannot read optimization log: {exc}") from exc
    marker = "## Rounds"
    index = current.find(marker)
    if index < 0:
        raise RoundError("optimization log is missing the '## Rounds' marker")
    insert_at = current.find("\n", index) + 1
    updated = current[:insert_at] + "\n" + entry.rstrip() + "\n" + current[insert_at:]
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(updated)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def ensure_log_ready(path: Path) -> None:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RoundError(f"cannot read optimization log: {exc}") from exc
    if "## Rounds" not in content:
        raise RoundError("optimization log is missing the '## Rounds' marker")


def relative_or_string(root: Path, path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def init_target(
    paths: TargetPaths, family: str, panel_path: Path, truth_check: str
) -> dict[str, Any]:
    if truth_check != "passed":
        raise RoundError("baseline requires an explicit source-aware truth check")
    if paths.state.exists():
        raise RoundError(f"state already exists: {paths.state}")
    ensure_log_ready(paths.log)
    for required in (paths.canonical, paths.output_pdf, paths.provenance):
        if not required.is_file():
            raise RoundError(f"baseline prerequisite is missing: {required}")
    jd_sha256 = validate_job_description(paths, family)
    provenance = validate_provenance(paths.canonical, paths.provenance, paths.root)
    if not provenance["passed"]:
        raise RoundError("baseline provenance failed: " + " | ".join(provenance["errors"]))
    panel = load_json(panel_path)
    validate_panel_target(panel, paths.slug, family)
    scores = panel_scores(panel)
    if not _input_hash_matches(paths, "incumbent", panel.get("input", {}).get("candidate_sha256")):
        raise RoundError("baseline panel hash does not match the canonical resume")
    if panel.get("input", {}).get("jd_sha256") != jd_sha256:
        raise RoundError("baseline panel job-description hash does not match the frozen target")
    state = {
        "schema_version": STATE_SCHEMA_VERSION,
        "slug": paths.slug,
        "family": family,
        "status": "initializing",
        "round": 0,
        "job_description": {
            "path": relative_or_string(paths.root, paths.jd),
            "sha256": jd_sha256,
        },
        "canonical": {
            "sha256": sha256_text(paths.canonical),
            "scores": scores,
            "last_keep_round": 0,
        },
        "panel": {
            "last_result": relative_or_string(paths.root, panel_path),
            "label": panel_label(panel),
        },
        "open_gaps": [],
        "history": [],
    }
    atomic_json(paths.state, state)
    entry = f"""### {paths.slug} - baseline - {dt.date.today().isoformat()}
- family: {family}
- composite: {scores['composite']:.1f} (decision: BASELINE)
- scores: {score_line(scores)}
- gate: compile/page/ATS passed before initialization | provenance PASS | no-fabrication confirmed by optimizer
- panel: {panel_label(panel)}
- benchmark: not recorded
- change: established canonical baseline
- open gaps/questions to user: none
"""
    prepend_log_entry(paths.log, entry)
    state["status"] = "ready"
    atomic_json(paths.state, state)
    return state


def start_round(paths: TargetPaths, hypothesis: str) -> dict[str, Any]:
    state = load_state(paths)
    if state["status"] not in ("ready", "stopped"):
        raise RoundError(f"cannot start while target status is {state['status']}")
    if not paths.canonical.is_file() or not paths.provenance.is_file():
        raise RoundError("canonical resume or provenance manifest is missing")
    assert_job_description_frozen(paths, state)
    if sha256_text(paths.canonical) != state["canonical"]["sha256"]:
        raise RoundError("canonical resume changed outside the orchestrator; re-baseline explicitly")
    if paths.candidate.exists() or paths.candidate_provenance.exists():
        raise RoundError("candidate files already exist; finish or recover the active round")
    shutil.copy2(paths.canonical, paths.candidate)
    shutil.copy2(paths.provenance, paths.candidate_provenance)
    state["round"] += 1
    state["status"] = "editing"
    state.pop("stop_reason", None)
    state["pending"] = {
        "round": state["round"],
        "hypothesis": hypothesis,
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "incumbent_sha256": state["canonical"]["sha256"],
        "gate": None,
    }
    atomic_json(paths.state, state)
    return state


def run_gate(paths: TargetPaths, max_pages: int) -> dict[str, Any]:
    state = load_state(paths)
    if state["status"] not in ("editing", "gated"):
        raise RoundError(f"cannot gate while target status is {state['status']}")
    if not paths.candidate.is_file() or not paths.candidate_provenance.is_file():
        raise RoundError("candidate resume or provenance manifest is missing")
    assert_job_description_frozen(paths, state)

    compile_proc = subprocess.run(
        [str(paths.root / "scripts" / "compile.sh"), str(paths.candidate), str(max_pages)],
        cwd=paths.root,
        capture_output=True,
        text=True,
    )
    if compile_proc.returncode != 0:
        raise RoundError("compile/page gate failed:\n" + compile_proc.stdout + compile_proc.stderr)
    ats_command = [
        sys.executable,
        str(paths.root / "scripts" / "ats_check.py"),
        str(paths.candidate_pdf),
        "--tex",
        str(paths.candidate),
        "--json",
    ]
    if paths.keywords.is_file():
        ats_command.extend(["--keywords", str(paths.keywords)])
    ats_proc = subprocess.run(ats_command, cwd=paths.root, capture_output=True, text=True)
    if ats_proc.returncode != 0:
        raise RoundError("ATS gate failed:\n" + ats_proc.stdout + ats_proc.stderr)
    ats = json.loads(ats_proc.stdout)
    provenance = validate_provenance(paths.candidate, paths.candidate_provenance, paths.root)
    if not provenance["passed"]:
        raise RoundError("provenance gate failed: " + " | ".join(provenance["errors"]))

    state["status"] = "gated"
    state["pending"]["gate"] = {
        "passed": True,
        "compile": compile_proc.stdout.strip(),
        "ats": ats,
        "provenance_claims": len(provenance["claims"]),
        "truth_check": "passed",
        "candidate_sha256": sha256_text(paths.candidate),
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    atomic_json(paths.state, state)
    return state


def _input_hash_matches(paths: TargetPaths, identity: str, expected: str | None) -> bool:
    if identity == "candidate":
        tex, pdf = paths.candidate, paths.candidate_pdf
    else:
        tex, pdf = paths.canonical, paths.canonical_pdf
    if expected == sha256_text(tex):
        return True
    if pdf.is_file():
        try:
            try:
                from .panel_review import extract_resume_text
            except ImportError:
                from panel_review import extract_resume_text
            return expected == hashlib.sha256(extract_resume_text(str(pdf)).encode()).hexdigest()
        except RuntimeError:
            pass
    return False


def cleanup_candidate(paths: TargetPaths) -> None:
    prefix = paths.root / "resumes" / f"{paths.slug}_resume.candidate"
    for suffix in (".tex", ".pdf", ".aux", ".log", ".out", ".fls", ".fdb_latexmk", ".synctex.gz"):
        candidate = Path(str(prefix) + suffix)
        if candidate.exists():
            candidate.unlink()
    if paths.candidate_provenance.exists():
        paths.candidate_provenance.unlink()


def _flag_values(panel: dict[str, Any]) -> list[str]:
    flags = panel.get("review_flags", {}).get("candidate", {})
    if not isinstance(flags, dict):
        return []
    return [flag for values in flags.values() if isinstance(values, list) for flag in values]


def finish_round(
    paths: TargetPaths,
    panel_path: Path,
    change: str,
    gaps: list[str],
    benchmark: Path | None,
    flags_resolved: bool,
) -> tuple[dict[str, Any], str]:
    state = load_state(paths)
    if state["status"] != "gated" or not state.get("pending", {}).get("gate", {}).get("passed"):
        raise RoundError("candidate must pass round.py gate before finish")
    if sha256_text(paths.candidate) != state["pending"]["gate"]["candidate_sha256"]:
        raise RoundError("candidate changed after the gate; run the gate again")
    assert_job_description_frozen(paths, state)
    panel = load_json(panel_path)
    validate_panel_target(panel, paths.slug, state["family"])
    if not panel.get("panel", {}).get("valid"):
        raise RoundError("cannot finish with an invalid verifier panel")
    recommendation = panel.get("recommendation")
    if not isinstance(recommendation, dict) or recommendation.get("decision") not in ("KEEP", "REVERT"):
        raise RoundError("paired panel result has no KEEP/REVERT recommendation")
    input_meta = panel.get("input", {})
    if not _input_hash_matches(paths, "candidate", input_meta.get("candidate_sha256")):
        raise RoundError("panel candidate hash does not match the gated candidate")
    if not _input_hash_matches(paths, "incumbent", input_meta.get("incumbent_sha256")):
        raise RoundError("panel incumbent hash does not match the canonical resume")
    if input_meta.get("jd_sha256") != state["job_description"]["sha256"]:
        raise RoundError("panel job-description hash does not match the frozen target")
    flags = _flag_values(panel)
    if flags and not flags_resolved:
        raise RoundError("candidate has unresolved reviewer flags: " + " | ".join(flags))
    ensure_log_ready(paths.log)

    before = panel_scores(panel, "incumbent")
    after = panel_scores(panel, "candidate")
    min_delta = 1.0 if panel["panel"].get("decorrelated") else 2.0
    policy = keep_decision(
        before["dimensions"],
        after["dimensions"],
        weights_for(state["family"]),
        min_delta=min_delta,
    )
    if recommendation["decision"] != policy["decision"]:
        raise RoundError("panel recommendation does not match the repository scoring policy")
    decision = policy["decision"]
    round_number = state["round"]
    if decision == "KEEP" and not paths.candidate_pdf.is_file():
        raise RoundError("compiled candidate PDF is missing")
    state["status"] = "finalizing"
    state["pending"]["finalization"] = {
        "decision": decision,
        "panel_result": relative_or_string(paths.root, panel_path),
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    atomic_json(paths.state, state)

    if decision == "KEEP":
        os.replace(paths.candidate, paths.canonical)
        os.replace(paths.candidate_provenance, paths.provenance)
        atomic_copy(paths.candidate_pdf, paths.canonical_pdf)
        atomic_copy(paths.candidate_pdf, paths.output_pdf)
        state["canonical"] = {
            "sha256": sha256_text(paths.canonical),
            "scores": after,
            "last_keep_round": round_number,
        }
    cleanup_candidate(paths)

    gap_entries = []
    for index, question in enumerate(gaps, start=1):
        item = {
            "id": f"r{round_number}-g{index}",
            "question": question,
            "status": "open",
            "opened_round": round_number,
        }
        state["open_gaps"].append(item)
        gap_entries.append(item)
    history_item = {
        "round": round_number,
        "date": dt.date.today().isoformat(),
        "hypothesis": state["pending"]["hypothesis"],
        "change": change,
        "decision": decision,
        "before": before,
        "after": after,
        "panel_result": relative_or_string(paths.root, panel_path),
        "panel": panel_label(panel),
        "benchmark": relative_or_string(paths.root, benchmark),
        "review_flags_resolved": flags_resolved if flags else None,
        "new_gap_ids": [item["id"] for item in gap_entries],
    }
    state["history"].append(history_item)
    state["status"] = "ready"
    state["panel"] = {
        "last_result": relative_or_string(paths.root, panel_path),
        "label": panel_label(panel),
    }
    gaps_text = "; ".join(f"{item['id']}: {item['question']}" for item in gap_entries) or "none"
    dimension_deltas = ", ".join(
        f"{dim} {before['dimensions'][dim]:.1f} -> {after['dimensions'][dim]:.1f}"
        for dim in DIMS
    )
    entry = f"""### {paths.slug} - round {round_number} - {dt.date.today().isoformat()}
- family: {state['family']}
- composite: {before['composite']:.1f} -> {after['composite']:.1f} (decision: {decision})
- scores (before -> after): {dimension_deltas}
- gate: compile/page PASS | ATS PASS | provenance PASS | no-fabrication PASS
- panel: {panel_label(panel)}; threshold +{min_delta:.1f}
- benchmark: {relative_or_string(paths.root, benchmark) or 'not recorded'}
- hypothesis: {state['history'][-1]['hypothesis']}
- change: {change}
- open gaps/questions to user: {gaps_text}
"""
    prepend_log_entry(paths.log, entry)
    del state["pending"]
    atomic_json(paths.state, state)
    return state, decision


def resolve_gap(paths: TargetPaths, gap_id: str, resolution: str, source: str) -> dict[str, Any]:
    state = load_state(paths)
    for gap in state["open_gaps"]:
        if gap["id"] == gap_id:
            if gap["status"] != "open":
                raise RoundError(f"gap {gap_id} is already resolved")
            gap.update(
                {
                    "status": "resolved",
                    "resolution": resolution,
                    "source": source,
                    "resolved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                }
            )
            atomic_json(paths.state, state)
            return state
    raise RoundError(f"unknown gap ID: {gap_id}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    init.add_argument("slug")
    init.add_argument("--family", required=True, choices=list(FAMILY_ADJUSTMENTS))
    init.add_argument("--panel", required=True, type=Path)
    init.add_argument("--truth-check", required=True, choices=("passed",))

    start = sub.add_parser("start")
    start.add_argument("slug")
    start.add_argument("--hypothesis", required=True)

    gate = sub.add_parser("gate")
    gate.add_argument("slug")
    gate.add_argument("--max-pages", type=int, default=1, choices=(1, 2))
    gate.add_argument(
        "--truth-check",
        required=True,
        choices=("passed",),
        help="explicitly attest that a source-aware verifier confirmed no fabrication",
    )

    finish = sub.add_parser("finish")
    finish.add_argument("slug")
    finish.add_argument("--panel", required=True, type=Path)
    finish.add_argument("--change", required=True)
    finish.add_argument("--gap", action="append", default=[])
    finish.add_argument("--benchmark", type=Path)
    finish.add_argument("--review-flags-resolved", action="store_true")

    status = sub.add_parser("status")
    status.add_argument("slug")

    stop = sub.add_parser("stop")
    stop.add_argument("slug")
    stop.add_argument("--reason", required=True)

    resolve = sub.add_parser("resolve-gap")
    resolve.add_argument("slug")
    resolve.add_argument("gap_id")
    resolve.add_argument("--resolution", required=True)
    resolve.add_argument("--source", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    root = Path(args.root).resolve()
    paths = TargetPaths(root, args.slug)
    try:
        if args.command == "init":
            state = init_target(paths, args.family, args.panel.resolve(), args.truth_check)
        elif args.command == "start":
            state = start_round(paths, args.hypothesis)
        elif args.command == "gate":
            state = run_gate(paths, args.max_pages)
        elif args.command == "finish":
            state, decision = finish_round(
                paths,
                args.panel.resolve(),
                args.change,
                args.gap,
                args.benchmark.resolve() if args.benchmark else None,
                args.review_flags_resolved,
            )
            print(f"round {state['round']}: {decision}")
        elif args.command == "resolve-gap":
            state = resolve_gap(paths, args.gap_id, args.resolution, args.source)
        elif args.command == "stop":
            state = load_state(paths)
            if state["status"] != "ready":
                raise RoundError("only a ready target can be stopped")
            state["status"] = "stopped"
            state["stop_reason"] = args.reason
            atomic_json(paths.state, state)
        else:
            state = load_state(paths)
        if args.command != "finish":
            print(json.dumps(state, indent=2))
    except RoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

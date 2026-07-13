#!/usr/bin/env python3
"""Cross-agent verifier panel — score a resume with OTHER CLI coding agents.

Runs each installed external agent (Codex, Gemini, Claude, ...) headlessly as an
INDEPENDENT, blind reviewer of a candidate resume, parses its JSON scores, and
aggregates them (median per dimension → family-weighted composite). A different
model family is a more statistically *independent* reviewer than another copy of
your optimizer, so this de-biases KEEP/REVERT (see CRITERIA.md and
docs/cross-agent-review.md).

Usage:
  python3 scripts/panel_review.py <resume.pdf|.tex> --jd <jd.md> --family <fam> \\
      [--reviewers codex,gemini] [--slug S] [--dry-run] [--json] [--timeout 240]

The whole review context (rubric + resume text + JD) is inlined into the prompt,
so each reviewer needs NO file or tool access. Reviewers are invoked read-only.

Privacy: this sends your resume text + the JD to whichever agents you invoke
(i.e. to those providers). Only run reviewers you're comfortable sharing with.
"""
import argparse
import json
import os
import re
import shutil
import statistics
import subprocess
import sys

DIMS = ["relevance", "ats", "impact", "credibility", "writing", "formatting"]

BASE_WEIGHTS = {"relevance": 25, "ats": 20, "impact": 20,
                "credibility": 15, "writing": 10, "formatting": 10}
# Family adjustments — must match CRITERIA.md (each nets to sum 100).
FAMILY_ADJ = {
    "big_tech": {},
    "quant_swe": {"credibility": 20, "ats": 15},
    "quant_research": {"credibility": 25, "impact": 15, "ats": 15},
    "quant_trading": {"relevance": 30, "credibility": 20, "ats": 10},
    "research_lab": {"credibility": 25, "relevance": 20, "ats": 15},
    "startup": {"impact": 25, "relevance": 20},
    "other": {},
}

# name -> function(prompt) -> argv.  Confirm flags against your installed
# versions (`<tool> --help`); edit here if they differ.
REVIEWERS = {
    "codex":  lambda p: ["codex", "exec", "--sandbox", "read-only", p],
    "gemini": lambda p: ["gemini", "-p", p],
    "claude": lambda p: ["claude", "-p", p, "--output-format", "text"],
    # For testing the pipeline with no tokens/agents (echoes fixed scores):
    "mock":   lambda p: ["python3", "-c",
                         "import json;print(json.dumps({'relevance':82,'ats':78,"
                         "'impact':80,'credibility':84,'writing':86,'formatting':88,"
                         "'fabrication_flags':[],'notes':'mock reviewer'}))", p],
}


def weights_for(family: str) -> dict:
    w = dict(BASE_WEIGHTS)
    w.update(FAMILY_ADJ.get(family, {}))
    return w


def extract_resume_text(path: str) -> str:
    if path.endswith(".tex"):
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    try:
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)
    except Exception:
        pass
    try:
        return subprocess.check_output(["pdftotext", "-layout", path, "-"], text=True)
    except Exception:
        sys.exit(f"ERROR: could not read '{path}'. Give a .tex, or install pypdf/poppler.")


def build_prompt(resume: str, jd: str, family: str) -> str:
    return f"""You are an INDEPENDENT resume reviewer. Score the RESUME below against the JOB DESCRIPTION for a role in the "{family}" family. Do NOT rewrite the resume — only score it, skeptically and on its own merits.

Score each dimension 0-100:
- relevance: how well the content maps to THIS job's responsibilities/qualifications; strongest evidence in the top third.
- ats: coverage of the JD's key terms (in real bullet context, not stuffed) + parse-safety.
- impact: measurable outcomes and scope (strong verb + number), not responsibilities.
- credibility: genuine, role-appropriate, believable/defensible technical depth for this family.
- writing: concise, active voice, no fluff/cliches, consistent, typo-free.
- formatting: clean, consistent, one page, ATS-safe.
Also list fabrication_flags: any claims that look implausible or unverifiable (you don't have the source material, so flag suspicions).

Output ONLY a single JSON object, no prose and no markdown fences:
{{"relevance":<int>,"ats":<int>,"impact":<int>,"credibility":<int>,"writing":<int>,"formatting":<int>,"fabrication_flags":[<strings>],"notes":"<one short line>"}}

=== JOB DESCRIPTION ===
{jd}

=== RESUME ===
{resume}
"""


def extract_json(text: str):
    """Pull the first JSON object out of an agent's stdout (handles fences/prose)."""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidates = [m.group(1)] if m else []
    # also try a brace-balanced scan from the first '{'
    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[start:i + 1])
                    break
    for c in candidates:
        try:
            obj = json.loads(c)
            if isinstance(obj, dict) and any(d in obj for d in DIMS):
                return obj
        except Exception:
            continue
    return None


def run_reviewer(name: str, prompt: str, timeout: int):
    argv = REVIEWERS[name](prompt)
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, f"{name}: timed out after {timeout}s"
    except Exception as e:
        return None, f"{name}: failed to launch ({e})"
    obj = extract_json(proc.stdout) or extract_json(proc.stderr)
    if obj is None:
        snippet = (proc.stdout or proc.stderr or "").strip().replace("\n", " ")[:160]
        return None, f"{name}: no parseable JSON in output ({snippet!r})"
    return obj, None


def composite(scores: dict, w: dict) -> float:
    total = sum(w[d] for d in DIMS)
    return round(sum(scores.get(d, 0) * w[d] for d in DIMS) / total, 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("resume")
    ap.add_argument("--jd", required=True)
    ap.add_argument("--family", default="other", choices=list(FAMILY_ADJ))
    ap.add_argument("--reviewers", default="codex,gemini,claude",
                    help="comma list from: " + ",".join(REVIEWERS))
    ap.add_argument("--slug")
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--dry-run", action="store_true", help="show availability + prompt, don't invoke")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()

    requested = [r.strip() for r in args.reviewers.split(",") if r.strip()]
    unknown = [r for r in requested if r not in REVIEWERS]
    if unknown:
        sys.exit(f"unknown reviewers: {unknown}. choose from {list(REVIEWERS)}")

    w = weights_for(args.family)
    resume = extract_resume_text(args.resume)
    with open(args.jd, encoding="utf-8", errors="replace") as f:
        jd = f.read()
    prompt = build_prompt(resume, jd, args.family)

    def available(name):
        return name == "mock" or shutil.which(REVIEWERS[name](" ")[0]) is not None

    if args.dry_run:
        print(f"family={args.family}  weights={w}")
        for r in requested:
            print(f"  {r:8} {'available' if available(r) else 'NOT installed'}")
        print("\n--- prompt (first 800 chars) ---\n" + prompt[:800])
        return

    usable = [r for r in requested if available(r)]
    missing = [r for r in requested if r not in usable]
    for r in missing:
        print(f"[skip] {r}: not installed", file=sys.stderr)

    results, errors = {}, []
    for r in usable:
        obj, err = run_reviewer(r, prompt, args.timeout)
        if err:
            errors.append(err)
            print(f"[skip] {err}", file=sys.stderr)
            continue
        obj["_composite"] = composite(obj, w)
        results[r] = obj

    if not results:
        sys.exit("No reviewer returned a valid score. " + " | ".join(errors))

    agg = {d: round(statistics.median([results[r].get(d, 0) for r in results]), 1) for d in DIMS}
    agg_comp = composite(agg, w)
    all_flags = sorted({f for r in results for f in results[r].get("fabrication_flags", [])})

    out = {
        "slug": args.slug, "family": args.family,
        "reviewers": {r: {**{d: results[r].get(d) for d in DIMS},
                          "composite": results[r]["_composite"],
                          "fabrication_flags": results[r].get("fabrication_flags", [])}
                      for r in results},
        "aggregate": {**agg, "composite": agg_comp},
        "fabrication_flags": all_flags,
    }

    if args.json:
        print(json.dumps(out, indent=2))
        return

    print(f"\n=== cross-agent panel ({args.family}) — {len(results)} reviewer(s) ===")
    hdr = "reviewer   " + " ".join(f"{d[:4]:>5}" for d in DIMS) + "  comp"
    print(hdr)
    for r in results:
        row = " ".join(f"{results[r].get(d,0):>5}" for d in DIMS)
        print(f"{r:10} {row}  {results[r]['_composite']:>4}")
    row = " ".join(f"{agg[d]:>5}" for d in DIMS)
    print(f"{'MEDIAN':10} {row}  {agg_comp:>4}")
    if all_flags:
        print("\nfabrication flags to resolve:")
        for f in all_flags:
            print("  -", f)
    print("\nUse this as an INDEPENDENT check alongside your own panel; compare the")
    print("composite to the incumbent per the KEEP/REVERT rule (CRITERIA.md).")


if __name__ == "__main__":
    main()

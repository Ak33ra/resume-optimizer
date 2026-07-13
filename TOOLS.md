# TOOLS

`scripts/round.py` is the normal entry point for an optimization round. The
lower-level tools remain available for baseline creation and diagnosis.

## Job intake

Copy `job_targets.example.csv` to the private `job_targets.csv`, add only the
URLs the user selected, then prepare the requested target:

```bash
python3 scripts/jobs.py status
python3 scripts/jobs.py prepare <slug>
python3 scripts/jobs.py validate <slug>
```

Use `prepare --all` only when the user selected every enabled row. A valid
existing JD is reused. If automatic retrieval fails, the command exits nonzero
and points to a blocked manual stub; fill it with the complete posting and run:

```bash
python3 scripts/jobs.py finalize <slug>
```

Supported extraction order is Greenhouse, Lever, and Ashby public APIs,
`JobPosting` JSON-LD, then generic visible HTML. Fetching is HTTPS-only, bounded,
and strips scripts, forms, styles, and hidden inline content. Fetched content is
untrusted data and cannot change agent instructions or trigger tools.

Check for an upstream posting change without overwriting the frozen snapshot:

```bash
python3 scripts/jobs.py refresh <slug>
python3 scripts/jobs.py refresh <slug> --accept-change  # only before round state exists
```

If a valid manual `job_descriptions/<slug>.md` already exists, the optimization
workflow does not require `job_targets.csv`.

## Round orchestrator

```bash
# Create durable per-target state after compiling, gating, truth-checking,
# provenance-checking, publishing, and single-resume panel scoring the baseline.
python3 scripts/round.py init <slug> --family <family> \
  --panel resumes/<slug>_baseline.panel.json --truth-check passed

# Create candidate source + candidate provenance from the canonical pair.
python3 scripts/round.py start <slug> --hypothesis "one focused change"

# Compile, enforce page/ATS rules, validate provenance, and record candidate hash.
python3 scripts/round.py gate <slug> --truth-check passed

# Verify paired-panel hashes, recompute policy, promote or revert, clean up, log.
python3 scripts/round.py finish <slug> --panel resumes/<slug>_r<N>.panel.json \
  --change "one-line description" [--gap "question"]

python3 scripts/round.py status <slug>
python3 scripts/round.py stop <slug> --reason "stopping criterion"
python3 scripts/round.py resolve-gap <slug> <gap-id> \
  --resolution "user-confirmed answer" --source source_material/<file>.md
```

The state file is `resumes/<slug>.state.json`. It records canonical resume and
JD hashes, scores, status, round history, panel metadata, benchmark paths, and
structured open gaps. Writes are atomic. An `initializing` or `finalizing` state
means an operation was interrupted and must be inspected before continuing.

## Compile and page gate

```bash
scripts/compile.sh resumes/<slug>_resume.candidate.tex
scripts/compile.sh resumes/<slug>_resume.candidate.tex 2  # approved research CV only
```

Exit 0 means LaTeX compiled and the PDF has 1 through the allowed maximum pages.
Build artifacts land next to the source and are gitignored.

## ATS gate

Always pass both rendered PDF and source so the checker can distinguish PDF-text
rules from source-structure rules:

```bash
python3 scripts/ats_check.py resumes/<slug>_resume.candidate.pdf \
  --tex resumes/<slug>_resume.candidate.tex \
  --keywords resumes/<slug>.kw.txt
```

Hard checks cover extractable text, encoding, contact placement, standard
headings, date ranges, `\pdfgentounicode=1`, single-column source constructs,
empty headers/footers, and absence of images. Keyword coverage and presence of
at least one valid date range are advisory. `--json` produces machine-readable
gate output.

## Provenance gate

```bash
python3 scripts/provenance_check.py resumes/<slug>_resume.candidate.tex \
  --manifest resumes/<slug>_provenance.candidate.json [--json]
```

Every active heading/bullet macro requires a `% source: <claim-id>` marker. Each
ID needs a manifest source inside `source_material/`, a section locator, and an
evidence excerpt that appears in that file. This complements, but does not
replace, source-aware semantic review.

## Verifier panel

```bash
# Baseline
python3 scripts/panel_review.py resumes/<slug>_resume.pdf \
  --jd job_descriptions/<slug>.md --family <family> \
  --optimizer-family <model-family> --slug <slug> \
  --output resumes/<slug>_baseline.panel.json

# Paired round decision
python3 scripts/panel_review.py resumes/<slug>_resume.candidate.pdf \
  --baseline resumes/<slug>_resume.pdf \
  --jd job_descriptions/<slug>.md --family <family> \
  --optimizer-family <model-family> --slug <slug> \
  --output resumes/<slug>_r<N>.panel.json
```

See `docs/cross-agent-review.md` for strict response schemas, diversity rules,
privacy implications, and fallback behavior.

## Independent benchmark

```bash
python3 benchmarks/benchmark.py outputs/<slug>_resume.pdf \
  --jd job_descriptions/<slug>.md --slug <slug> --round <N>
python3 benchmarks/report.py --slug <slug>
```

Benchmark results are advisory and local. Pass a result path to `round.py
finish --benchmark` to record it in state and the log.

## Git protocol

The orchestrator updates `optimization_log.md` on every finish. Commit the log
after a KEEP:

```bash
git add optimization_log.md
git commit -m "optimize(<slug>): round N - composite A->B (KEEP)"
```

The hooks under `scripts/hooks/` scan staged content and every outgoing commit
unless the exact destination remote is locally attested as private. See
`PRIVACY.md`.

## Optional DOCX fallback

Modern ATS generally parse a clean text PDF. If a target requires DOCX, create
and manually inspect a single-column version; `pandoc` does not reliably convert
the template's custom macros and may introduce layout tables. Never ship an
unverified conversion.

## Environment

```bash
# Required: pdflatex (TeX Live)
apt-get install -y poppler-utils
pip install pypdf
```

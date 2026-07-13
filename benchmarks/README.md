# benchmarks/

Independently verify the toolkit's output with **third-party** scorers. The
loop already self-scores (`CRITERIA.md`) and gate-checks (`scripts/ats_check.py`);
this directory cross-checks that with tools built by other people, so a
disagreement is a signal worth chasing.

**Golden rule: trust deltas, not absolutes.** No free tool is the exact ATS a
given employer runs (Greenhouse, Lever, Workday, iCIMS… all parse differently).
Judge a resume by *measurable before→after improvement* plus a clean parse — not
by hitting one magic number. Never let a scorer pressure you into fabrication
(`CONSTRAINTS.md` §1) or keyword-stuffing (a §4 violation that also fails good
human reviewers).

## Quick start (local, offline, no PII leaves your machine)

```bash
# one-time (optional richer scorers):
pip install -r benchmarks/requirements.txt
python -m spacy download en_core_web_lg          # ~600MB, enables SkillNER coverage

# per round, on the published PDF:
python3 benchmarks/benchmark.py outputs/<slug>_resume.pdf \
        --jd job_descriptions/<slug>.md --slug <slug> --round <N>

# see improvement across rounds:
python3 benchmarks/report.py --slug <slug>
```

`benchmark.py` runs even with **no** extra dependencies (it falls back to a
built-in CS/quant/ML skill lexicon and skips the semantic metric). Install the
optionals to upgrade it to dictionary-based and semantic scoring.

## What it measures

| Score | How | Target |
|-------|-----|--------|
| **Parse-safety** | Heuristic checklist on the extracted text (selectable text, no `�`, contact recovered, ≥3 standard headings). Authoritative check is a real parser — see below. | **100%** |
| **Keyword coverage** | SkillNer (EMSI ~60k-skill DB) if installed, else the built-in lexicon: `|JD∩resume skills| / |JD skills|`. | **~60–80%** (100% usually = stuffing) |
| **Semantic relevance** | `sentence-transformers` cosine(resume, JD), if installed. | no absolute target — **watch the round-over-round trend** |

Results are written to `results/<slug>_r<N>.json`; `report.py` turns them into a
before/after delta table (the real proof of efficacy).

## Recommended external tools

These are the best free options found in research. Use them to catch scorer
bias — run one occasionally, not every round.

### Local / open-source (preferred)
- **OpenResume parser** — https://open-resume.com/resume-parser — the best free
  "what did the ATS actually see?" **visual parse check**. Runs client-side
  (nothing uploaded); self-hostable (`git clone`, `npm install`, `npm run dev`).
  Confirm every field lands in the right bucket, in order.
- **SkillNer** — https://github.com/AnasAito/SkillNER — deterministic skill
  extraction against a 60k skill DB; the engine behind our coverage score when
  installed.
- **sentence-transformers** — https://www.sbert.net — local semantic similarity.
- **Resume Matcher (srbhr)** — https://github.com/srbhr/Resume-Matcher — self-host
  with local Ollama for a second, LLM-based opinion. **Non-deterministic** (v1.x
  is an LLM harness) — use qualitatively, don't gate KEEP/REVERT on it.
- **pyresparser** — a third machine parse opinion; **unmaintained** (old spaCy
  2.x), isolate in its own venv if you use it.

### Free online (manual; redact PII before pasting)
- **Jobalytics** (https://jobalytics.co) — 100% free, unlimited, 0–100 keyword
  match + missing keywords. Best free online cross-check.
- **Jobscan** (https://jobscan.co/resume-scanner) — 5 free scans/month;
  industry-standard match rate, **target ≥75%**.
- **Resume Worded / Targeted Resume** (https://resumeworded.com/targeted-resume)
  — free "Relevancy Score", **target ≥80–85**.
- **Affinda free parser** (https://affinda.com/resume-parser) — high-accuracy
  commercial parser, free web sandbox — great "did every field extract?" check.

> All online tools upload your resume. Use a **redacted/dummy** copy (fake name,
> `test@example.com`, fake phone). Prefer the local tools for routine runs —
> consistent with this repo's local-first, no-PII design.

## Methodology (per round)

1. **Extract** the text layer (same as the gate): `pdftotext -layout <pdf>` — if
   this is garbage (`�`/broken ligatures), every score below is invalid; fix the
   PDF first (`TOOLS.md` gate check 2).
2. **Parse-safety** → aim 100%. For the authoritative check, drop the PDF into
   OpenResume and confirm all fields; optionally record true fields in
   `ground_truth/<slug>.yaml` and diff.
3. **Keyword coverage** → 60–80%. Low = genuinely missing relevant experience →
   route to the "Open gaps / questions for the user" list, never fabricate.
4. **Semantic relevance** → log it; require a positive trend across rounds.
5. **(Optional) one external tool** → catch bias; if it wildly disagrees,
   investigate before trusting either.
6. **Delta table** (`report.py`) → a round is a genuine win only if it improves
   ≥1 score without regressing another, while staying one page / truthful /
   ATS-safe. This mirrors the KEEP/REVERT rule in `CRITERIA.md`.

## Directory layout

```
benchmarks/
├── README.md            # this file
├── requirements.txt     # optional richer-scorer deps (pin after first run)
├── benchmark.py         # parse-safety + keyword coverage + semantic → results/<slug>_r<N>.json
├── report.py            # results/*.json → before/after delta table
├── ground_truth/        # (gitignored) true fields per posting for the parse diff
│   └── example.example.yaml
├── results/             # (gitignored) one JSON per slug/round
└── external/            # (gitignored) manual Jobalytics/Jobscan/Affinda notes
```

`ground_truth/`, `results/`, and `external/` are gitignored (they can hold or
imply personal data). Pin every library/model version in `requirements.txt` so
scores are reproducible.

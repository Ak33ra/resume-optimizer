# OPTIMIZATION LOOP

The round-based procedure the agent follows to tailor a resume to a job and
iterate until it stops improving. Read `CONSTRAINTS.md`, `CRITERIA.md`,
`WRITING_GUIDE.md`, and `ROLE_PROFILES.md` before starting; use `TOOLS.md` for
the exact commands.

The core idea: **one change at a time, verified by an independent panel, keeping
only what scores higher.** Every claim stays truthful (`CONSTRAINTS.md` §1).

---

## 0. Preconditions

- `source_material/` has the user's real material. If it contains **no real
  `*.md`** (only the shipped `*.example.md` templates), treat it as empty: stop
  and ask the user to fill in the templates (`source_material/README.md`).
  **Never draft from placeholder scaffolds.**
- `job_descriptions/` has at least one target. If empty, ask the user to add
  postings.
- `pdflatex` is available (`TOOLS.md`). Recommend `poppler-utils` / `pypdf` for
  the ATS checks.

## 1. Select targets

- Optimize **only** the postings that fit the user's instructions. If they said
  "target Jane Street and Anthropic," do only those.
- **If the user gave no preference, ask** which company / role / family to target
  before doing any work — don't guess or optimize everything.
- For each chosen posting, fix its `<slug>` (matches the JD filename) and
  determine its `family` (from JD front-matter, else infer, else ask) — this
  selects the profile in `ROLE_PROFILES.md` and the weight adjustments in
  `CRITERIA.md`.

## 2. Parse the JD

Extract and note (do not put PII here):
- Role family + seniority (intern / new_grad / experienced).
- Responsibilities and required/preferred qualifications.
- The **top ~12–20 keywords** in the JD's exact phrasing (skills, tools,
  methods, qualifications). Save them (one per line) to `resumes/<slug>.kw.txt`
  (per-target so parallel targets don't collide; already gitignored) for
  `scripts/ats_check.py --keywords`.

## 3. Establish the baseline

- If `resumes/<slug>_resume.tex` already exists, it's the incumbent. Compile and
  score it (steps 4c–4d) to get the current composite.
- If not, generate the **first draft**: fill `resume_template.tex` from
  `source_material/`, tailored to this JD using `WRITING_GUIDE.md` +
  `ROLE_PROFILES.md` (right section order, strongest signal in the top third,
  truthful keyword coverage). The template's custom macros document their
  argument order inline — read the `\newcommand` comments in
  `resume_template.tex` before filling them. Save as
  `resumes/<slug>_resume.tex`, compile, gate, and score it — this becomes the
  baseline, logged as **round 1 with `decision: baseline`** (there's no
  incumbent to compare against). Publish its PDF as the current deliverable:
  `mkdir -p outputs && cp resumes/<slug>_resume.pdf outputs/<slug>_resume.pdf`.

## 4. Round loop

Repeat until a stopping criterion (§5) is hit. **One focused change per round.**

**4a. Hypothesize.** Pick the single highest-leverage improvement, guided by the
lowest-scoring dimension and the JD. Examples: surface true JD keywords into
existing bullets; rewrite weak bullets to impact-first XYZ; reorder sections per
the role profile; cut low-relevance content to free space; tighten wording to
protect the one-page limit.

**4b. Apply to a candidate.** Copy the canonical `.tex` to
`resumes/<slug>_resume.candidate.tex` and edit the candidate only. The canonical
file is never touched until a KEEP (this is the rollback mechanism — `TOOLS.md`).

**4c. Fatal gate** (`CRITERIA.md` Stage 1). Run `scripts/compile.sh` (compiles +
one page) and `scripts/ats_check.py` (selectable text, headings, contact,
dates). Have a verifier confirm **no fabrication** vs `source_material/`. If the
gate fails, fix the candidate or discard the change — never score or keep a gate
failure. (Keyword coverage from `ats_check.py` is **advisory input to Stage-2
scoring, not a gate** — don't discard a candidate for low coverage.)

**4d. Score with the verifier panel** (`CRITERIA.md` Stage 2). Run the panel
(see below); aggregate by median per dimension → composite (family-adjusted
weights).

> **Running the panel.** The verifiers must be *independent* judgments — you are
> the optimizer, so you must not be the sole judge (`AGENT.md`).
> - **Preferred:** launch **≥3** subagents/tasks in fresh contexts (whatever your
>   harness provides — e.g. the Task/Agent tool), each given ONLY the candidate
>   PDF text + `.tex`, the JD, the family, and `CRITERIA.md` — not each other's
>   scores nor your change rationale.
> - **Single-context fallback:** if you cannot spawn independent contexts, score
>   in **≥3 separate passes** that each start fresh from the rubric alone, and
>   record `panel: simulated` in the log entry. This is weaker — prefer real
>   independence.
> - **Aggregate:** median per dimension; with an even count, average the two
>   middle values. Compute the composite from the medians.

**4e. Decide** (`CRITERIA.md` KEEP/REVERT rule).
- **KEEP** (composite up ≥ +1.0, no dimension down > 5, gate passes): promote the
  candidate to canonical, recompile it, **publish the deliverable**
  (`mkdir -p outputs && cp resumes/<slug>_resume.pdf outputs/<slug>_resume.pdf`),
  remove the leftover candidate artifacts (`rm -f resumes/<slug>_resume.candidate.*`),
  append a KEEP entry to `optimization_log.md`, and commit the log
  (`CONSTRAINTS.md` §7).
- **REVERT** (otherwise): discard the candidate, append a REVERT entry to the
  log, leave canonical untouched. No commit needed.

**4f. Record gaps.** If the JD wanted something the source material doesn't
support, add it to the round's "Open gaps / questions for the user" — never
invent it.

## 5. Stopping criteria

Stop optimizing a target when any holds:
- **Plateau:** 3 consecutive rounds with no KEEP.
- **Diminishing returns:** the last KEEP's composite gain was < 2.0 and all
  dimensions are ≥ 85.
- **Ceiling:** composite ≥ ~92 and no dimension < 85.
- **Blocked on the user:** the only remaining improvements need info from the
  gaps list — surface them and pause this target.
- **Round cap:** ~8 rounds per target (raise only if still clearly improving).

## 5b. Optional — independent benchmark

For extra confidence (or when the user wants proof), cross-check the canonical
resume with the third-party scorers in `benchmarks/`:

```bash
python3 benchmarks/benchmark.py outputs/<slug>_resume.pdf --jd job_descriptions/<slug>.md --slug <slug> --round <N>
python3 benchmarks/report.py --slug <slug>      # before/after delta table
```

Treat these as an independent sanity check on your own scores, not the source of
truth — trust the round-over-round delta, and never optimize to a single tool's
number (`benchmarks/README.md`).

## 6. Report

After each target (and at the end), summarize for the user:
- Final composite and per-dimension scores; the delta from baseline.
- What changed across rounds (from the log).
- The **open gaps / questions** — the highest-value thing the user can do next
  (supply a metric, confirm a skill) to raise the score further.
- Where the deliverable is: `outputs/<slug>_resume.pdf` (ready to submit).

---

### Quick reference — one round

```
hypothesize → cp canonical → candidate; edit candidate
  → scripts/compile.sh candidate            # gate: compiles + 1 page
  → scripts/ats_check.py candidate.pdf --keywords resumes/<slug>.kw.txt  # gate: ATS structure (coverage advisory)
  → verifier confirms no fabrication         # gate: truthfulness (verifier sees source_material)
  → panel of ≥3 independent verifiers score (median)   # CRITERIA Stage 2
  → KEEP  : mv candidate → canonical; recompile; cp pdf → outputs/; rm candidate.*; log; git commit
    REVERT: rm candidate.*; log
```

# resume-optimizer

An agentic resume optimization loop for coding agents. Point an agent at your
master resume and a job description; it produces a one-page, ATS-safe,
truthfully tailored resume, scores incumbent/candidate pairs with a blind panel,
and iterates while keeping only policy-clearing changes.

Built for landing interviews at top CS roles — FAANG-tier internships and
new-grad SWE, frontier research labs (Anthropic, OpenAI, DeepMind), and quant
firms (SWE, research, trading) — but it works for any role.

## How it works

```
source_material/  (your true experience)          job_descriptions/<slug>.md  (a target)
                         \                        /
                          v                      v
        ┌───────────────────────────────────────────────────┐
        │  tailor -> gate + provenance -> paired panel ->      │
        │  policy KEEP/REVERT -> state + log                   │  <- repeat until plateau
        └───────────────────────────────────────────────────┘
                          |
                          v
   outputs/<slug>_resume.pdf   +   optimization_log.md (score history, no contact PII)
```

The agent tailors truthfully (it only ever uses facts from your
`source_material/` — it never invents experience), keeps the PDF to exactly one
page, formats it to survive ATS parsing, and records every round.

## Setup (one time)

1. **Install the toolchain.** `pdflatex` (TeX Live) is required. Recommended
   extras for the ATS checks: `apt-get install -y poppler-utils` and
   `pip install pypdf`.
2. **(Recommended) make a private fork** (a private *mirror* — GitHub can't
   privatize a fork of a public repo) so your resume history stays private. See
   [`PRIVACY.md`](PRIVACY.md) — a few git commands, with guardrails that stop PII
   from ever reaching a public remote.
3. **Add your material.** In `source_material/`, copy each `*.example.md`
   template to a real `*.md` and fill it in — one per resume section (education,
   experience, projects, skills (`TECHNOLOGIES.md`), courses, awards,
   publications, …). Be exhaustive and include raw numbers; the agent selects
   and tailors but never invents. See
   [`source_material/README.md`](source_material/README.md).
   ```bash
   cd source_material && for f in *.example.md; do cp "$f" "${f%.example.md}.md"; done
   ```
   **Short on time?** Jump-start this by exporting what an AI assistant (ChatGPT,
   Claude, Gemini, …) already knows about you — see
   [`docs/importing-from-ai-memory.md`](docs/importing-from-ai-memory.md) — then
   verify and correct it.
4. **Add targets.** Save each job posting as `job_descriptions/<slug>.md` (full
   text, especially the qualifications). See
   [`job_descriptions/README.md`](job_descriptions/README.md).

Your resumes and source material stay **local** by default (gitignored). See
**Privacy** below.

## What goes where

| Folder | You put in | Committed? |
|--------|-----------|-----------|
| `source_material/` | Everything true about you — your master resume and per-section facts (copy the `*.example.md` templates). The agent's only source of truth. | Local by default; private fork only (PII). |
| `job_descriptions/` | One file per role you're targeting — paste the full posting. | Yes (public postings). |
| `resumes/` | *Generated for you* — the tailored LaTeX **source** `<slug>_resume.tex` (+ transient build files). | Local by default; private fork only (PII). |
| `outputs/` | *Generated for you* — the ready-to-submit **PDF** `<slug>_resume.pdf` (published on baseline + every KEEP). | Local by default; private fork only (PII). |
| `optimization_log.md` | Score, panel, gate, benchmark, change, gap, and decision summary for each round (no contact PII). | Yes. |

## Usage

Start your coding agent in this repo and tell it, in plain language, which jobs
to optimize for — for example:

> "Read AGENT.md and optimize my resume for the Anthropic and Jane Street
> postings in job_descriptions/."

The agent reads `AGENT.md`, then follows `OPTIMIZATION_LOOP.md`. If you don't
name targets, it will ask which company/role to focus on. When it needs a metric
or a skill it can't find in your material, it will ask rather than make something
up. Each finished resume lands in `outputs/<slug>_resume.pdf`, ready to submit.

## What's in here

| File | Purpose |
|------|---------|
| `AGENT.md` / `CLAUDE.md` | Entry point for the agent — read order + operating principles. |
| `OPTIMIZATION_LOOP.md` | The round-based procedure the agent follows. |
| `CRITERIA.md` | Scoring rubric: fatal gate + weighted dimensions + verifier panel. |
| `CONSTRAINTS.md` | Hard rules (truthfulness, one page, ATS-safe, privacy, git). |
| `WRITING_GUIDE.md` | Bullet craft — impact-first XYZ, verbs, clichés to cut. |
| `ROLE_PROFILES.md` | Per-industry playbooks (big tech / quant / research labs / startup). |
| `TOOLS.md` | Exact build & verification commands. |
| `PRIVACY.md` | Public-skeleton / private-fork model + PII guardrails. |
| `resume_template.tex` | The single-column, ATS-safe LaTeX template (Jake's Resume). |
| `scripts/` | `round.py` (state machine), compile/ATS/provenance gates, strict paired panel, benchmarks, and git privacy hooks. |
| `benchmarks/` | Independent third-party scoring to verify efficacy (parse-safety, keyword coverage, semantic match). |
| `optimization_log.md` | Committed score history of every round. |
| `source_material/`, `job_descriptions/`, `resumes/`, `outputs/` | Your inputs (`source_material/`, `job_descriptions/`) and generated outputs (`resumes/` sources, `outputs/` final PDFs). |

## Verifying it works

Beyond the built-in scoring, `benchmarks/` cross-checks each resume with
**independent** tools — a local parse-safety + keyword-coverage + semantic-match
script (`benchmark.py`), plus pointers to free tools like OpenResume, Jobalytics,
and Jobscan. The proof is the before→after delta across rounds, not any single
number. See [`benchmarks/README.md`](benchmarks/README.md).

**Multiple coding agents?** If you have others on your CLI (Codex, Gemini, …),
`scripts/panel_review.py` runs paired blind reviews and records model-family
diversity. Different families reduce shared bias; correlated panels use a wider
decision margin rather than claiming false independence. See
[`docs/cross-agent-review.md`](docs/cross-agent-review.md).

## Principles

- **Truthful and traceable.** The agent rewords, reorders, and emphasizes what's
  real; claim IDs map back to source evidence and every line must survive a live
  interview.
- **Blindly cross-checked.** The agent that writes is not the sole judge; a
  recorded, diversity-aware panel scores each incumbent/candidate pair.
- **Private by default.** Resume content and PII stay on your machine. Share the
  skeleton publicly; keep your history in a private fork, with gitignore + a
  pre-push hook guarding against accidental leaks. See [`PRIVACY.md`](PRIVACY.md).

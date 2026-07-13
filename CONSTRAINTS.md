# CONSTRAINTS

Hard rules for every resume the agent produces. A change that violates any of
these is **invalid** — fix it or discard it; never log it as a KEEP. The gate
in `OPTIMIZATION_LOOP.md` enforces the checkable ones before scoring.

## 1. Truthfulness (non-negotiable)

- **Never fabricate.** Every fact, metric, technology, title, date, and outcome
  on the resume must be traceable to something in `source_material/`.
- The agent may **reword, reorder, select, compress, and re-emphasize** what's
  there. It may **not** invent experience, inflate numbers, add skills the user
  hasn't demonstrated, or claim authorship/scope the source doesn't support.
- **Rewrite policy — truthful, ask to fill gaps:** when a bullet lacks impact or
  numbers, or a JD demands a skill/keyword the source material doesn't cover,
  **do not invent it**. Add it to an "Open gaps / questions for the user" list
  and ask. Estimates are allowed only when the user supplies or confirms them,
  and only if defensible in an interview.
- If you wouldn't want to defend a line in a live interview, it doesn't go on
  the resume.

## 2. One page, exactly

- The compiled PDF must be **exactly one page**. Not 1.1, not 2.
- To reclaim space, in this order: (1) cut fluff and tighten wording, (2) drop
  the least-relevant content, (3) only then adjust `\vspace`, margins, or font
  size in the template. See `WRITING_GUIDE.md`.
- **One page is absolute** for interns, new grads, and all engineer-leaning
  tracks (SWE, RE/MTS/MLE, quant SWE/research/trading).
- **Exception:** a pure **Research Scientist / academic-CV** target with a
  substantial publication record may run to **2 pages** — but only when the user
  explicitly opts in for that target (`ROLE_PROFILES.md` research_lab). Pass the
  page limit to the gate accordingly (`scripts/compile.sh <tex> 2`). Everyone
  else is strictly one page.

## 3. Template & format

- Every resume follows `resume_template.tex` (single-column, ATS-safe, Jake's
  Resume). Do not switch to multi-column, sidebars, tables-as-layout, or
  graphic templates.
- **Keep the ATS line `\pdfgentounicode=1`** (with `\input{glyphtounicode}`).
  It's what makes the PDF text machine-readable. Removing it silently breaks
  parsing.
- Compile with `pdflatex` (see `TOOLS.md`).

## 4. ATS-safe formatting (hard rules)

Derived from how real parsers (Greenhouse, Lever, Workday, iCIMS, Ashby, Taleo)
behave. These are checkable — see the gate in `OPTIMIZATION_LOOP.md` and the
verification commands in `TOOLS.md`.

- Single column, top-to-bottom reading order.
- **PDF text must be machine-selectable** — extraction must yield clean text
  (no `�` replacement chars, no broken ligatures).
- Contact info (name, email, phone, links) in the document **body**, near the
  top — never in a header/footer.
- **Standard section headings only:** Education, Experience (or Work Experience
  / Employment), Projects, Technical Skills, Publications, Research, Awards (or
  Awards & Competitions), Honors, Leadership, Volunteer, Summary, Certifications.
  Keep coursework *under* Education, not as its own heading. No creative headings
  ("My Toolkit", "Where I've Been"). This list is the allowlist enforced by
  `scripts/ats_check.py`.
- Dates as `Mon YYYY -- Mon YYYY` (e.g., `Aug 2024 -- Dec 2024`) or `Mon YYYY --
  Present`. No year-only ranges (`2023 -- 2024`), no `'24`, and no season-year
  (`Summer 2025`) — some parsers drop them or invent employment gaps.
- **Fonts:** embedded and machine-readable. The template's default (Computer
  Modern) is fine because it embeds with a ToUnicode map; if you switch, use a
  web-safe face (Arial, Helvetica, Calibri, Times New Roman, Georgia, Roboto,
  Open Sans, Lato) and keep it embedded. No decorative or icon fonts.
- No images, icons, logos, headshots, or skill-bar graphics. Skill levels as
  text if at all.
- Use the JD's **exact keyword phrasing** where truthful; don't rely on
  synonyms parsing. Never keyword-stuff or add hidden/white text.

## 5. One canonical resume per posting

- Exactly one running resume per job: the LaTeX source
  `resumes/<slug>_resume.tex` and its published PDF `outputs/<slug>_resume.pdf`
  (the ready-to-submit deliverable). The `<slug>` matches
  `job_descriptions/<slug>.md`.
- Round work happens on a transient `resumes/<slug>_resume.candidate.tex`. The
  canonical source is overwritten — and the PDF in `outputs/` re-published —
  **only** when a round is a KEEP (this is the rollback mechanism — no git needed
  for the `.tex`). A REVERT leaves both the canonical `.tex` and the `outputs/`
  PDF untouched.

## 6. Privacy (see `PRIVACY.md`)

This repo is a **public skeleton**; personal data lives in a **private fork**.

- `resumes/`, `outputs/`, and `source_material/` are gitignored by default and
  contain PII. In a clone of the public skeleton, **never** commit their
  contents. Only in the user's **private fork** (private `origin`,
  `resumeopt.allowPII true`) may they be version-controlled — and even then
  never pushed to the public upstream.
- **Never push PII to a public remote**, and never put raw contact PII
  (name/email/phone) in any file that could reach one. The `pre-push` guardrail
  (`scripts/hooks/pre-push`) blocks this, but don't rely on it alone.
- Job descriptions and all toolkit `.md`/`.tex`/script files are safe to commit
  publicly.

## 7. Version control (per round)

- Each optimization round is recorded in `optimization_log.md` (scores + change
  + decision). Keep entries to scores and change *descriptions*; referencing
  your own resume specifics is fine and useful in a private fork, but never put
  raw contact PII there. See the log header for the entry format.
- **On a KEEP:** update the canonical resume, append the log entry, and commit
  the log (and any toolkit changes) directly to `main`. Message format:
  `optimize(<slug>): round N — composite A→B (KEEP)`.
- **On a REVERT:** still append the log entry (decision: REVERT), discard the
  candidate file, leave the canonical resume untouched. No commit is required
  for a revert, but if one was already made, `git revert` it — don't leave a
  regression in history.
- Commit only when the user has asked you to optimize; don't push unless asked.
  In a private fork, resume/source files may also be committed (to the private
  origin) for history — see `PRIVACY.md`.

## 8. Authenticity

- The resume must read as written by the candidate, not by an AI. Plain, precise
  engineering language beats florid phrasing.
- Some target firms **hand-read** applications and explicitly reject AI-written
  materials (e.g., Jane Street). Never auto-generate cover letters; if asked for
  one, draft points for the user to write in their own voice. See
  `ROLE_PROFILES.md`.

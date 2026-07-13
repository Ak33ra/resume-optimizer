# TOOLS

Commands the agent uses to build and verify resumes. Everything here works with
just `pdflatex`; the extras (poppler, pypdf) make the ATS checks better and are
worth installing once.

Two helper scripts wrap the common cases (`scripts/`), but the raw commands are
documented too so nothing is a black box.

## Compile

```bash
# Compile one resume. Use the .candidate.tex while iterating a round.
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=resumes \
  resumes/<slug>_resume.candidate.tex
# Run twice only if you add \ref/\cite cross-references (this template needs one pass).
```

Or: `scripts/compile.sh resumes/<slug>_resume.candidate.tex` — compiles and
prints exit status + page count in one step (exit 0 iff 1 page). For the
RS/academic-CV exception, pass a max page count: `scripts/compile.sh <tex> 2`
(`CONSTRAINTS.md` §2).

Build artifacts (`.aux`, `.log`, `.out`) land next to the source and are
gitignored.

## Gate check 1 — exactly one page

`pdflatex`'s log line-wraps, so strip newlines before matching. This needs **no
extra tools**:

```bash
python3 - <<'PY'
import re
log = open('resumes/<slug>_resume.candidate.log','rb').read().decode('latin-1')
m = re.search(r'Output written on .*?\((\d+) page', log.replace('\n',''))
print('PAGES:', m.group(1) if m else 'UNKNOWN')
PY
```

Better, if installed: `pdfinfo resumes/<slug>_resume.candidate.pdf | grep Pages`
(from `poppler-utils`), or via `pypdf`: `len(PdfReader(pdf).pages)`.

**PASS iff pages == 1.**

## Gate check 2 — text is machine-selectable & clean

The `\pdfgentounicode=1` line in the template makes text extractable. Verify the
rendered PDF actually extracts cleanly. `scripts/ats_check.py` does this for you;
to check by hand, `pypdf` works out of the box and also flags corruption:

```bash
python3 - <<'PY'
from pypdf import PdfReader
txt = "\n".join((p.extract_text() or "") for p in PdfReader('resumes/<slug>_resume.candidate.pdf').pages)
print('chars:', len(txt))
print('replacement-char present:', '�' in txt)   # must be False
print(txt[:600])
PY
```

If you have `poppler-utils`: `pdftotext -layout resumes/<slug>_resume.candidate.pdf - | head -50`.

**PASS iff** extracted text is non-trivial (>~200 chars for one page), contains
no `�` (U+FFFD), and shows no broken ligatures (e.g., "office"→"oce"). If it
fails, the ATS trick is broken — check `\input{glyphtounicode}` and
`\pdfgentounicode=1` are present.

## Gate check 3 — ATS structure + keyword coverage

`scripts/ats_check.py` bundles the structural checks (standard section headings,
contact info in body, date formats, single-column reading order, no stuffing)
and keyword coverage:

```bash
# Structural checks only:
python3 scripts/ats_check.py resumes/<slug>_resume.candidate.pdf

# With keyword coverage against a JD's key terms (one per line):
python3 scripts/ats_check.py resumes/<slug>_resume.candidate.pdf --keywords resumes/<slug>.kw.txt
```

The full list of testable ATS rules is in `CONSTRAINTS.md` §4. Coverage is
**advisory** (not a gate); target ~60–80% of the JD's top ~12–20 keywords, in
real bullet context (not stuffed).

## Optional — .docx fallback for legacy ATS

Modern ATS parse a clean text PDF fine, so PDF is the default deliverable. A few
legacy systems (notably Oracle Taleo) parse `.docx` more reliably. If a target
is known to use one, and `pandoc` is available, you can also produce a Word
copy — but never at the cost of the one-page PDF being correct:

```bash
pandoc resumes/<slug>_resume.tex -o resumes/<slug>_resume.docx   # optional, if pandoc installed
```

**Caveat:** pandoc won't cleanly round-trip this template's custom `\resume*`
macros / `tabular*` rows and may emit Word tables — the exact thing some ATS
mangle. Treat the output as **unverified**: re-run the parse check on it (or on a
PDF export of it), or hand-build a single-column `.docx`. Never ship a docx you
haven't parse-checked.

## Git — commit protocol (see CONSTRAINTS.md §7)

```bash
# On a KEEP: canonical resume already updated locally (gitignored); commit the log.
git add optimization_log.md
git commit -m "optimize(<slug>): round N — composite A→B (KEEP)"

# Never stage resumes/, outputs/, or source_material/ — they're gitignored; verify:
git status --porcelain            # these dirs must not appear
```

## Candidate ↔ canonical file workflow (the rollback mechanism)

```bash
# Start a round from the current best:
cp resumes/<slug>_resume.tex resumes/<slug>_resume.candidate.tex   # or create the first draft

# ... edit + compile + score the candidate ...

# KEEP: promote candidate to canonical, recompile, publish the deliverable PDF:
mv resumes/<slug>_resume.candidate.tex resumes/<slug>_resume.tex
scripts/compile.sh resumes/<slug>_resume.tex
mkdir -p outputs && cp resumes/<slug>_resume.pdf outputs/<slug>_resume.pdf   # ready-to-submit PDF
rm -f resumes/<slug>_resume.candidate.*

# REVERT: just discard the candidate (outputs/ keeps the last good PDF):
rm -f resumes/<slug>_resume.candidate.*
```

## One-time environment setup (recommended)

```bash
apt-get install -y poppler-utils   # pdfinfo, pdftotext  (may need sudo)
pip install pypdf                  # fallback PDF text extraction
# LaTeX: pdflatex must be installed (TeX Live). Check: pdflatex --version
```

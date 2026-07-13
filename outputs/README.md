# outputs/

The **ready-to-submit PDFs**. The agent publishes the current best resume here
after the baseline draft and after every KEEP, so you always have the final
file without recompiling anything yourself.

- One PDF per posting: `<slug>_resume.pdf` (same name as
  `resumes/<slug>_resume.tex`, just `.pdf`).
- This is the deliverable you actually upload/submit.
- `resumes/` holds the LaTeX **sources** (`.tex`) and transient build artifacts;
  `outputs/` holds only the finished **PDFs**.

**This folder is gitignored** (the PDFs contain PII) and stays on your machine —
same as `resumes/` and `source_material/`. See `PRIVACY.md`. Only KEEP rounds
update these files; a REVERT leaves the current PDF untouched.

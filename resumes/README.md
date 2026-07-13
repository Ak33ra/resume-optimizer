# resumes/

Generated, job-tailored resumes live here. **This folder is gitignored**
(the files contain PII) — it stays on your machine. Version history of each
optimization round is tracked in `../optimization_log.md` (scores + change
notes, no contact PII).

## Naming convention

For a target with slug `<slug>` (e.g. `google_swe_intern`):

| File                          | What it is                                              |
|-------------------------------|---------------------------------------------------------|
| `<slug>_resume.tex`           | **Canonical** tailored resume. Only overwritten when a round scores higher (a KEEP). |
| `<slug>_resume.pdf`           | Compiled PDF of the canonical `.tex` (what you submit).  |
| `<slug>_resume.candidate.tex` | Transient working copy for the round in progress. Deleted/ignored on REVERT. |

The slug matches the job description file in `../job_descriptions/<slug>.md`.

One canonical resume per posting (see `CONSTRAINTS.md`). You start these by
pointing the agent at a job description — nothing to create by hand.

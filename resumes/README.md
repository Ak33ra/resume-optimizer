# resumes/

The LaTeX **sources** for your job-tailored resumes (the finished **PDFs** live
in `../outputs/`). **This folder is gitignored** (the files contain PII) — it
stays on your machine. Version history of each optimization round is tracked in
`../optimization_log.md` (scores + change notes, no contact PII).

## Naming convention

For a target with slug `<slug>` (e.g. `google_swe_intern`):

| File                              | What it is                                              |
|-----------------------------------|---------------------------------------------------------|
| `resumes/<slug>_resume.tex`       | **Canonical** source. Only overwritten when a round scores higher (a KEEP). |
| `resumes/<slug>_resume.candidate.tex` | Transient working copy for the round in progress. Deleted on KEEP/REVERT. |
| `resumes/<slug>_provenance.json` | Canonical claim-ID to source-evidence map. |
| `resumes/<slug>_provenance.candidate.json` | Transient provenance map edited with the candidate. |
| `resumes/<slug>.state.json` | Local durable round state, hashes, scores, panel metadata, history, and gaps. |
| `resumes/<slug>_r<N>.panel.json` | Strict paired reviewer result used for round N. |
| `outputs/<slug>_resume.pdf`       | The compiled, ready-to-submit PDF (published on baseline + every KEEP). |

Build artifacts (`.aux`, `.log`, and transient `.pdf` from compiles) also land
here and are gitignored. The slug matches `../job_descriptions/<slug>.md`.

One canonical resume/provenance pair per posting (see `CONSTRAINTS.md`). Use
`scripts/round.py` rather than manually copying or promoting candidate files.
Copy `provenance.example.json` to `<slug>_provenance.json` when creating a
baseline, then replace its sample claim IDs and evidence.

# source_material/

Everything **true about you**. This is the agent's single source of truth — it
only ever uses facts that appear here, and it never invents experience, metrics,
or skills (`CONSTRAINTS.md` §1). The more you put here, the better it can tailor.

**Privacy:** your real files here are **gitignored** and stay on your machine.
The `*.example.md` templates are tracked (they're just scaffolds, no PII). See
`PRIVACY.md` for how to keep a private version history of your material.

## How to use it

Each resume section has a starter template. **Copy each one, dropping the
`.example`, then fill it in:**

```bash
cd source_material
for f in *.example.md; do cp "$f" "${f%.example.md}.md"; done
# now edit CONTACT.md, EDUCATION.md, EXPERIENCE.md, ... (the .md copies)
```

Your filled-in `*.md` files are the material the agent reads. Fill in only the
sections you have; delete templates that don't apply.

## The starter files

| File | What goes in it |
|------|-----------------|
| `CONTACT.md` | Name, email, phone, location, links (GitHub, LinkedIn, site, Scholar). |
| `EDUCATION.md` | Degrees, GPA, honors, thesis. |
| `EXPERIENCE.md` | **The big one** — every job/internship/research role, dumped brag-doc style with raw metrics. |
| `PROJECTS.md` | Personal / OSS / hackathon / research projects, with links and traction. |
| `TECHNOLOGIES.md` | Languages, frameworks, tools, domains — only what you can defend. |
| `COURSES.md` | Relevant advanced/graduate coursework. |
| `AWARDS.md` | Awards, scholarships, and competitions (CP, olympiads, Kaggle, trading games). |
| `PUBLICATIONS.md` | Papers, talks, research artifacts (research/quant-research targets). |
| `VOLUNTEERING.md` | Leadership, teaching/mentoring, community, volunteering — with impact. |

You can also just drop in a full `master_resume.tex`/`.md` and any extra notes,
transcripts, or brag docs — the agent reads everything in this folder. The
templates above are the recommended structure, not a straitjacket.

## The golden rules

- **Be exhaustive.** Include more than fits on one page; the agent selects.
- **Capture raw numbers.** If a metric exists anywhere, write it down — the agent
  won't make one up, and quantified bullets are what land interviews.
- **Stay honest.** Everything here must be defensible in an interview.

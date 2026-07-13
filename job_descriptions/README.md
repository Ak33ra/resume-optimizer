# job_descriptions/

One file per role you're targeting. These are committed by default (job posts
are public). To keep your target list private, see the commented lines in
`../.gitignore`.

## How to add a target

Save each posting as `<slug>.md` (or `.txt`), where `<slug>` is a short,
lowercase, underscore-separated id you'll reuse for the resume, e.g.:

- `google_swe_intern.md`
- `janestreet_swe_newgrad.md`
- `anthropic_research_engineer.md`
- `hrt_quant_trader.md`

Paste the **full posting** — title, team, responsibilities, and especially the
**required/preferred qualifications** (that's where the keywords the agent
matches against live). A link alone isn't enough; include the text.

Optional front-matter the agent will honor if present:

```
---
company: Google
role: Software Engineer Intern
family: big_tech        # big_tech | quant_swe | quant_research | quant_trading | research_lab | startup | other
seniority: intern       # intern | new_grad | experienced
location: Mountain View, CA
url: https://...
---
```

Delete any sample/cloned files you don't want to target. Then start the agent
and tell it which of these to optimize for (see the root `README.md`).

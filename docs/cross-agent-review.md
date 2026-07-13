# Cross-agent review

`scripts/panel_review.py` obtains blind judgments from installed Codex, Gemini,
and Claude CLIs. Model-family diversity reduces shared evaluator bias, but it
does not make scores objective or statistically independent in a strict sense.
The script therefore records exactly which CLI families completed and widens
the KEEP margin when diversity is weak.

## Paired decision scoring

Score the incumbent and candidate in the same reviewer call:

```bash
python3 scripts/panel_review.py resumes/<slug>_resume.candidate.pdf \
  --baseline resumes/<slug>_resume.pdf \
  --jd job_descriptions/<slug>.md --family <family> \
  --optimizer-family <openai|google|anthropic|other> --slug <slug> \
  --reviewers codex,gemini,claude \
  --output resumes/<slug>_r<N>.panel.json
```

Reviewers see neutral Resume A/Resume B labels; the script alternates which
artifact is A. They do not see the edit hypothesis, change description, other
scores, source material, or provenance manifest. Each must return all six
0-100 dimensions, a reason for each score, and explicit fabrication, keyword,
and formatting flag arrays. Partial, malformed, or out-of-range responses are
rejected rather than filled with defaults.

Reviewers run concurrently. Prompts are sent over stdin where supported and the
CLIs run without workspace write access. The result includes input hashes,
reviewer families, failures, median dimensions, composites, flags, and a policy
recommendation.

## Decision strength

- At least three completed reviewers are required by default.
- `decorrelated: true` requires at least two completed reviewer families that
  differ from `--optimizer-family`; the margin is `+1.0`.
- A valid but correlated/simulated panel uses `+2.0` to absorb more evaluator
  noise.
- A dimension drop greater than five points always reverts.
- Any reviewer flag must be investigated before `round.py finish` accepts it.

`--min-reviewers 2` is an explicit weaker fallback, not the normal protocol.
The orchestrator independently recomputes the decision and verifies both input
hashes before promoting anything.

## Availability and testing

```bash
python3 scripts/panel_review.py resumes/<slug>_resume.pdf \
  --jd job_descriptions/<slug>.md --family <family> \
  --optimizer-family <model-family> --dry-run

python3 scripts/panel_review.py resumes/<slug>_resume.tex \
  --jd job_descriptions/<slug>.md --family <family> \
  --optimizer-family other --reviewers mock --min-reviewers 1 --json
```

The mock exercises plumbing only; it is never valid evidence of resume quality.
CLI flags evolve, so check each installed tool's help if a reviewer fails to
launch.

## Limits

- This sends resume and JD text to the selected providers under the user's
  accounts. It is opt-in and no longer local-only.
- LLM scores remain noisy and correlated through shared data and conventions.
Use deltas and rationales, not false precision.
- Source-blind fabrication flags are suspicions. The source-aware truth gate and
  provenance manifest remain authoritative.
- PDF input is preferred because formatting cannot be judged reliably from raw
  LaTeX source.

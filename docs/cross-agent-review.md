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

The JD and resumes are explicitly marked as untrusted data in every prompt.
Panel JSON records the exact JD hash; `round.py` rejects baseline or paired
scores created from a different frozen snapshot.

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
resume and JD hashes before promoting anything.

## OpenAI-compatible reviewer (OSS models)

`oss` is a built-in reviewer backed by any OpenAI-compatible
`/v1/chat/completions` gateway, letting you add a model family beyond
Codex/Gemini/Claude (GLM, Qwen, MiniMax, Kimi, DeepSeek, ...) for genuine
decorrelation without another OAuth flow. Configure it entirely through
environment variables — nothing provider-specific is committed:

```bash
export PANEL_OSS_BASE_URL="https://your-gateway/v1"
export PANEL_OSS_API_KEY="..."        # kept in env, never in the repo
export PANEL_OSS_MODEL="glm-5.2"       # any model id the gateway serves
export PANEL_OSS_FAMILY="zhipu"        # a label distinct from the optimizer family
# optional: PANEL_OSS_TEMPERATURE, PANEL_OSS_MAX_TOKENS, PANEL_OSS_TIMEOUT, PANEL_OSS_USER_AGENT

python3 scripts/panel_review.py resumes/<slug>_resume.candidate.pdf \
  --baseline resumes/<slug>_resume.pdf --jd job_descriptions/<slug>.md \
  --family <family> --optimizer-family anthropic \
  --reviewers codex,oss,claude --slug <slug> \
  --output resumes/<slug>_r<N>.panel.json
```

With `--optimizer-family anthropic`, a `codex` (openai) + `oss`
(non-openai/anthropic family) + `claude` (anthropic) panel has two families that
differ from the optimizer, so `decorrelated: true` and the KEEP margin is `+1.0`.
The reviewer sends the resume and JD text to the configured gateway; treat that
as opt-in data sharing, exactly like any other external reviewer.

`oss` is fully opt-in: if `PANEL_OSS_BASE_URL` / `PANEL_OSS_API_KEY` /
`PANEL_OSS_MODEL` are unset, it is reported as unavailable and skipped like an
uninstalled CLI, so the default `codex,gemini,claude` panel on a fresh clone is
unaffected. Prefer a straightforward non-reasoning instruct model — some
reasoning models return empty completions on non-streamed calls. If your gateway
sits behind Cloudflare and returns HTTP 403 (error 1010), the wrapper already
sends a browser-like `User-Agent`; override it with `PANEL_OSS_USER_AGENT`.

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

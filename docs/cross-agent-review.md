# Cross-agent review — independent verifiers from other CLI agents

The optimization loop scores each round with a **panel of independent
verifiers** (`CRITERIA.md`). The catch: if those verifiers are all the same
model as your optimizer, their scores are **correlated** — they share training
data and blind spots, so three of them mostly agree with each other (and with
the optimizer) for the same reasons. That inflates confidence without adding
much real information.

A reviewer from a **different model family** (e.g. you optimize with Claude Code
and review with OpenAI Codex and/or Gemini CLI) is a more statistically
**independent** estimator. It disagrees for *different* reasons, so it catches
things a same-model panel misses and de-biases the KEEP/REVERT decision. This is
the strongest tier of the independence spectrum in `CRITERIA.md`:

```
weak  (a) ≥3 fresh passes in one context (simulated)
      (b) ≥3 independent subagents of your optimizer's model
strong(c) reviewers from DIFFERENT model families (Codex, Gemini, …)  ← this doc
```

## What the toolkit ships

`scripts/panel_review.py` runs whichever external agents you have installed as
blind reviewers and aggregates their scores.

```bash
python3 scripts/panel_review.py outputs/<slug>_resume.pdf \
    --jd job_descriptions/<slug>.md --family <family> [--reviewers codex,gemini] [--slug <slug>]
```

- It **inlines** the rubric + resume text + JD into the prompt, so each reviewer
  needs **no file or tool access** — it only reads what you hand it.
- Each reviewer returns a strict JSON object of per-dimension 0-100 scores +
  fabrication flags; the script computes the family-weighted composite (same
  weights as `CRITERIA.md`) and reports the **median** across reviewers.
- Missing agents and unparseable output are skipped with a note; a reviewer runs
  **read-only**.

Check what's wired up without spending anything:

```bash
python3 scripts/panel_review.py outputs/<slug>_resume.pdf --jd job_descriptions/<slug>.md \
    --family big_tech --dry-run        # shows which agents are installed + the prompt
python3 scripts/panel_review.py ... --reviewers mock   # fake reviewer, exercises the pipeline
```

## Exact commands per agent (confirm against your version)

The script invokes each agent in its documented headless mode. Flags evolve —
run `<tool> --help` and edit the `REVIEWERS` table at the top of
`scripts/panel_review.py` if yours differ.

| Agent | Headless invocation | Notes |
|-------|---------------------|-------|
| **Codex CLI** | `codex exec --sandbox read-only "<prompt>"` | `exec` = non-interactive; **read-only is the default**; final answer → stdout. |
| **Gemini CLI** | `gemini -p "<prompt>"` | `-p`/`--prompt` = headless single turn → stdout. |
| **Claude Code** | `claude -p "<prompt>" --output-format text` | print mode → stdout. Useful when your optimizer is *not* Claude. |

You authenticate each CLI with its own account; the toolkit just shells out.

## Using it in the loop

Treat cross-agent scores as an **additional, decorrelated** input to the
KEEP/REVERT decision (`OPTIMIZATION_LOOP.md` §4d), not a replacement for your
own panel:

- **Agreement gate (recommended):** KEEP only if *both* your own panel and the
  cross-agent panel clear the `+1.0` margin. Disagreement → don't keep; look at
  why.
- **Or pool them:** take the median composite across all reviewers (yours +
  cross-agent) and apply the normal rule.
- Note which reviewers ran in the log's change line, e.g.
  `panel: claude x3 + codex + gemini`.

If the cross-agent panel strongly disagrees with your own, that's the signal you
wanted — investigate before trusting either.

## Caveats

- **Privacy tradeoff.** This sends your resume text + the JD to whichever agents
  you invoke — i.e. to those providers, under your accounts. It's opt-in and
  breaks the otherwise local-only default. Only run reviewers you're comfortable
  sharing that content with. (Nothing is committed; this is a runtime call.)
- **Non-determinism.** LLM reviewers are noisy and non-deterministic; the same
  input can score differently across runs. That's exactly why the `+1.0` margin
  and median aggregation exist — don't over-fit to a single reviewer's number.
- **Cost/latency.** Each reviewer is a full agent run on your account; a panel
  of three is three runs per round. Use it on near-final candidates, not every
  micro-edit.
- **Truthfulness still rules.** A cross-agent reviewer can't see your
  `source_material/`, so its fabrication flags are *suspicions*; the
  authoritative no-fabrication check remains the source-aware gate verifier
  (`OPTIMIZATION_LOOP.md` §4c). Never let any reviewer's score pressure you into
  a claim you can't defend (`CONSTRAINTS.md` §1).

# CRITERIA

How a resume is scored. The optimization loop uses this to decide whether a
round's change is kept or reverted. Scoring is done by a **blind verifier
panel** so no single perspective dominates.

There are two stages: a **fatal gate** (pass/fail, checked first) and a
**weighted score** (0–100 per dimension). A candidate that fails the gate is
invalid and is never scored or kept.

---

## Stage 1 — Fatal gate (pass/fail)

If any of these fail, the candidate is invalid. Fix it or discard it — do not
score it, do not log it as a KEEP. Commands to check the mechanical ones are in
`TOOLS.md`.

1. **Compiles** cleanly with `pdflatex` (no errors).
2. **Exactly one page** (`CONSTRAINTS.md` §2).
3. **No fabrication** — every claim traces to `source_material/`
   (`CONSTRAINTS.md` §1). The provenance manifest must pass its mechanical check,
   and a source-aware verifier must confirm the semantics. This is the most
   important gate.
4. **Machine-selectable text** — extraction yields clean text, no `�` / broken
   ligatures (`CONSTRAINTS.md` §4).
5. **ATS-structural** — single column, standard section headings, contact info
   in body, valid date formats (`CONSTRAINTS.md` §4).

---

## Stage 2 — Weighted dimensions (0–100 each)

| # | Dimension | Weight | What it measures |
|---|-----------|:------:|------------------|
| 1 | **Relevance** | 25% | How well the content maps to *this* JD's responsibilities and required/preferred qualifications. The strongest predictor of getting an interview. Is the most relevant evidence in the top third? |
| 2 | **ATS / keyword coverage** | 20% | Coverage of the JD's top ~12–20 keywords (JD's exact phrasing) present in real bullet context, ~60–80% target; plus parse-safety beyond the gate (headings, density, no stuffing). |
| 3 | **Impact & quantification** | 20% | Do bullets show measurable outcomes and scope (XYZ), not responsibilities? Strong verbs, real numbers or concrete scale. |
| 4 | **Technical depth & credibility** | 15% | Does it signal genuine, role-appropriate engineering/research ability at the right level? Are claims believable and defensible? Right depth for the family (`ROLE_PROFILES.md`). |
| 5 | **Writing quality & clarity** | 10% | Concise, active voice, no fluff/clichés, consistent tense/format, zero typos. |
| 6 | **Formatting & length** | 10% | Clean, consistent, dense-but-scannable, template-compliant, comfortably one page. |

**Composite** = `0.25·Relevance + 0.20·ATS + 0.20·Impact + 0.15·Credibility +
0.10·Writing + 0.10·Formatting`, rounded to one decimal.

### Scoring bands (per dimension)
- **90–100** — excellent; a top candidate for this specific role.
- **75–89** — strong; minor gaps.
- **60–74** — adequate; clear room to improve.
- **40–59** — weak; notable misses.
- **<40** — failing on this dimension.

---

## Role-family weight adjustments

Start from the defaults above, then shift for the target family (see
`ROLE_PROFILES.md`). Compute the composite with the **family-adjusted** weights,
not the defaults. Each row below already sums to 100; if you tweak further,
renormalize so the six weights still sum to 100.

| Family | Adjustments vs default |
|--------|------------------------|
| `big_tech` | Defaults. |
| `quant_swe` | Credibility 15→20, ATS 20→15 (some elite shops hand-read). Reward competitive-programming/systems signal within Relevance & Credibility. |
| `quant_research` | Credibility 15→25, Impact 20→15, ATS 20→15. Weight publications, math depth, out-of-sample rigor. |
| `quant_trading` | Relevance 25→30, Credibility 15→20, ATS 20→10. Reward mental-math/competition/EV signal; penalize diluting ML/systems keywords. |
| `research_lab` | Credibility 15→25, Relevance 25→20, ATS 20→15. Weight publications/authorship, scale/systems, mission-safety engagement; strongest evidence must be top-of-page. |
| `startup` | Impact 20→25, Relevance 25→20. Reward breadth, ownership, shipping speed. |
| `other` | Defaults. |

For firms known to hand-read and reject AI-written materials (e.g., Jane
Street), the panel should also weight authenticity/human-readability and flag
anything that reads as machine-generated (`CONSTRAINTS.md` §9).

---

## Verifier panel protocol

- **At least 3 verifier judgments** per candidate. For decisions, each reviewer
  scores the incumbent and candidate in one blind A/B prompt. It sees the PDF
  text, JD, family, and fixed rubric, but not identities, other scores, the
  hypothesis, or change description. A/B order alternates across reviewers.
- **Decorrelation spectrum (weakest to strongest):** (a) at least 3 fresh passes
  in one context (simulated); (b) at least 3 separate subagents of the
  optimizer's model;
  (c) reviewers from **different model families** (e.g. Codex, Gemini) via
  `scripts/panel_review.py`. Same-model reviewers share training biases, so their
  scores are *correlated*; a different family is a less-correlated estimator,
  not a guarantee of independence. Prefer (c) when available; see
  `docs/cross-agent-review.md`.
- Each verifier returns every 0–100 dimension with a non-empty justification,
  plus fabrication, keyword, and format flags. Missing, malformed, or
  out-of-range responses are discarded. The script computes composites.
- Every panel artifact records the exact JD hash. Baseline initialization and
  round finalization reject scores produced from any other snapshot.
- **Aggregate** by taking the **median** per dimension (robust to one outlier),
  then compute the composite from the medians.
- The blind scorers don't see `source_material/`, so they flag claims that look
  **implausible or unverifiable**. The authoritative no-fabrication check is the
  separate gate verifier in `OPTIMIZATION_LOOP.md` §5b, which *does* get
  `source_material/`. **Any fabrication/implausibility flag** forces a gate
  review before the score counts — resolve it (cut the claim or confirm with the
  user) first.

## KEEP / REVERT rule

Compare the candidate's aggregated composite to the current canonical resume's.

- **KEEP** if: gate passes, the panel is valid, the composite improves by the
  applicable margin, and no single dimension regresses by more than 5 points.
- Otherwise **REVERT**.

The margin is `+1.0` only for a cross-family panel with at least two reviewer
families different from the optimizer. Correlated or simulated panels use
`+2.0`. A tie or sub-margin gain is a REVERT.

See `OPTIMIZATION_LOOP.md` for how this plugs into the round loop and
`optimization_log.md` for how to record the scores.

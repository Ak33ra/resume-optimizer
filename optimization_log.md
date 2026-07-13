# Optimization Log

The **committed** record of every optimization round — the version history of
your tailoring work (`CONSTRAINTS.md` §7).

**Rules for the agent**
- Append one entry per round, **newest first**, under `## Rounds`.
- Record the verifier-panel scores (before → after), a one-line description of
  what changed, and the KEEP/REVERT decision.
- Keep entries to **scores + change descriptions**. Referencing your own resume
  specifics (which bullet, which metric) is fine and useful in a private fork,
  but **never** put raw contact PII (name/email/phone) here. The `pre-push`
  guardrail blocks that from reaching a public remote (`PRIVACY.md`).
- On a **KEEP**, commit this file (see the commit protocol in `CONSTRAINTS.md`).
  On a **REVERT**, still log the round, discard the candidate `.tex`, and do not
  update the canonical resume.

## Entry format

```
### <slug> — round <N> — <YYYY-MM-DD>
- family: <big_tech|quant_swe|quant_research|quant_trading|research_lab|startup|other>
- composite: <before> → <after>   (decision: KEEP | REVERT)
- scores (before → after): relevance <> → <>, ats <> → <>, impact <> → <>, credibility <> → <>, writing <> → <>, formatting <> → <>
- gate: compiles ✓ | 1 page ✓ | no-fabrication ✓
- change: <one line — e.g. "reordered Experience above Projects; added 'distributed systems', 'gRPC' from JD; tightened 3 bullets to impact-first">
- open gaps/questions to user: <none | short note>
```

## Rounds

<!-- newest first; agent appends here -->

<!--
EXAMPLE (fictional — delete once real rounds exist):

### google_swe_intern — round 2 — 2026-07-12
- family: big_tech
- composite: 81 → 87   (decision: KEEP)
- scores (before → after): relevance 78 → 88, ats 84 → 90, impact 80 → 84, credibility 82 → 85, writing 83 → 86, formatting 88 → 88
- gate: compiles ✓ | 1 page ✓ | no-fabrication ✓
- change: moved Experience above Projects; surfaced "distributed systems"/"gRPC" from JD in existing bullets; rewrote 3 bullets to lead with quantified impact
- open gaps/questions to user: none

### google_swe_intern — round 3 — 2026-07-12
- family: big_tech
- composite: 87 → 85   (decision: REVERT)
- scores (before → after): relevance 88 → 84, ats 90 → 90, impact 84 → 82, credibility 85 → 84, writing 86 → 85, formatting 88 → 88
- gate: compiles ✓ | 1 page ✓ | no-fabrication ✓
- change: attempted a Summary section — pushed a bullet off-page and diluted relevance; reverted
- open gaps/questions to user: none
-->

# Optimization Log

Committed summary of baseline and round decisions. `scripts/round.py` prepends
entries under `## Rounds`; detailed local state and panel JSON stay in
`resumes/`.

Rules:

- Decisions are `BASELINE`, `KEEP`, or `REVERT`.
- Record family, before/after scores, complete gate status, panel type and
  reviewers, decision threshold, benchmark path/result, hypothesis, change, and
  gap IDs/questions.
- Never include raw contact PII. Resume-specific change descriptions are fine in
  a private fork.
- Commit this file after each KEEP. REVERT entries may remain uncommitted until
  the next KEEP or an explicit history checkpoint.

## Entry formats

```text
### <slug> - baseline - <YYYY-MM-DD>
- family: <family>
- composite: <score> (decision: BASELINE)
- scores: relevance <>, ats <>, impact <>, credibility <>, writing <>, formatting <>
- gate: compile/page/ATS PASS | provenance PASS | no-fabrication PASS
- panel: <cross-family|correlated/simulated> [reviewer:family, ...]
- benchmark: <path/result | not recorded>
- change: established canonical baseline
- open gaps/questions to user: <none | gap IDs and questions>

### <slug> - round <N> - <YYYY-MM-DD>
- family: <family>
- composite: <before> -> <after> (decision: KEEP | REVERT)
- scores (before -> after): relevance <> -> <>, ats <> -> <>, impact <> -> <>, credibility <> -> <>, writing <> -> <>, formatting <> -> <>
- gate: compile/page PASS | ATS PASS | provenance PASS | no-fabrication PASS
- panel: <type and reviewers>; threshold <+1.0|+2.0>
- benchmark: <path/result | not recorded>
- hypothesis: <one focused expected improvement>
- change: <one line describing the actual edit>
- open gaps/questions to user: <none | gap IDs and questions>
```

## Rounds

<!-- newest first; scripts/round.py writes entries here -->

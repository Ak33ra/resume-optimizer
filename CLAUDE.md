# CLAUDE.md

This repo is an agentic resume optimization toolkit. **Read `AGENT.md` first** —
it's the entry point and tells you what to read and how to operate. Then follow
`OPTIMIZATION_LOOP.md`.

Key rules you must not break (full detail in `CONSTRAINTS.md`):
- Never fabricate — every claim traces to `source_material/`; ask the user to
  fill structured gaps and maintain the claim provenance manifest.
- Compiled PDF must be exactly one page, single-column, ATS-safe.
- Never commit or paste resume content / contact PII; log rounds in
  `optimization_log.md` (scores + change notes, no contact PII).
- Optimize only the jobs the user names; if none given, ask first.
- Use `scripts/round.py` for state transitions and paired blind panel results for
  KEEP/REVERT decisions.

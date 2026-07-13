# WRITING GUIDE

How to write and rewrite bullets. This is the craft the agent applies inside the
loop. Pair it with `ROLE_PROFILES.md` (what to emphasize per industry) and
`CONSTRAINTS.md` (what's not allowed).

## The one rule: impact first, then how

Every bullet leads with a strong verb, states a quantified result, and names the
technical method. Google's **XYZ formula** captures it:

> **Accomplished [X] as measured by [Y], by doing [Z].**

- **X** — the accomplishment (start with an action verb).
- **Y** — the number that proves it (%, ms, ×, $, users, QPS, GB, rank).
- **Z** — the specific technical work / tools that make it credible.

The parts can be reordered for flow, but all three should be present. The
"so what" (Y) and the "how" (Z) are what separate a real engineer from a task
list.

## Weak → strong

| Weak | Strong |
|---|---|
| Responsible for the search feature. | Cut search latency 65% (480ms→170ms) by adding an Elasticsearch cache layer, serving 12M+ monthly queries. |
| Worked on a data pipeline. | Automated a nightly ETL pipeline in Python/Airflow, eliminating ~10 hrs/week of manual work and cutting data errors 40%. |
| Helped improve the mobile app. | Raised Lighthouse performance 45→92 via lazy rendering and image optimization, driving 500K additional MAU. |
| Built a microservice. | Designed a Go microservice handling 1M+ daily requests at p99 < 30ms, replacing a monolith endpoint. |
| Did research on transformers. | First-authored a NeurIPS'25 paper on efficient attention, cutting training FLOPs 22% at matched perplexity. |

## Quantify honestly when metrics are fuzzy

Real numbers are best, but scope is also proof. When no hard business metric
exists, substitute a concrete, defensible dimension (see `CONSTRAINTS.md` §1 —
never invent a precise figure you can't defend):

- **Scale:** "processing 2M records/day", "across 12 services", "for a 30k-user tool".
- **Performance/reliability:** latency, throughput, uptime, error-rate reduction.
- **Productivity:** build time cut, test coverage raised, onboarding shortened.
- **Breadth:** endpoints, integrations, teams served, PRs reviewed/merged.

If the source material has no number and the user can't supply one, keep the
bullet method-and-scope specific rather than padding it with a fake metric.

## Verbs

**Ban these** (weak / task-framing): Responsible for, Helped, Assisted, Worked
on, Participated in, Involved in, Duties included, Handled, Utilized.

**Reach for these** (vary them; don't repeat a verb on one page):

- Build: Architected, Engineered, Designed, Developed, Built, Implemented, Prototyped, Shipped.
- Improve: Optimized, Refactored, Accelerated, Reduced, Cut, Scaled, Hardened, Streamlined.
- Automate/integrate: Automated, Integrated, Deployed, Migrated, Orchestrated, Containerized, Instrumented.
- Fix/operate: Debugged, Diagnosed, Resolved, Stabilized, Secured, Monitored.
- Results: Achieved, Delivered, Drove, Doubled, Tripled, Won.
- Lead: Led, Spearheaded, Owned, Mentored, Coordinated, Partnered.
- Research: Analyzed, Modeled, Evaluated, Benchmarked, Formalized, Proved.

## Clichés to delete

Team player, detail-oriented, hard worker, results-driven, problem solver,
self-starter, proven track record, strong work ethic, dynamic, think outside the
box, synergy, passionate, excellent communication skills. **Show the trait with
a bullet; never assert it.** (e.g., "team player" → a bullet showing a shipped
cross-team result.)

## Mechanics

- **No pronouns.** Implied first person; start with the verb. Never "I/me/my".
- **Tense:** present for your current role, past for everything finished. Don't
  mix under one heading.
- **One idea per bullet.** Don't chain achievements with "and".
- **3–5 bullets** for the most recent/relevant role; 1–2 for older ones.
- **Consistency:** uniform date format, punctuation (bullets either all end with
  a period or none do), capitalization, and tense throughout.
- **Skills section:** categorize (Languages / Frameworks / Tools / …), ~15–25
  relevant terms, no 40-item dumps, no star ratings. List only what you can
  discuss for five minutes.

## Section ordering (default; `ROLE_PROFILES.md` overrides per role)

- **Thin experience (most students):** Education → Experience → Projects → Skills.
- **Strong internships:** Experience → Projects → Education → Skills.
- **Research-heavy:** put Publications/Research high (right after a short summary).
- Lead with your single strongest signal. Compress everything that has stopped
  adding new signal.

## Tailoring to a JD (what the loop does each round)

1. Pull the top ~12–20 keywords from the JD (skills, tools, qualifications) in
   the JD's exact phrasing.
2. Surface the true ones you already have into real bullet context (aim ~60–80%
   coverage), reinforcing the most important 2–4 times naturally — not stuffed.
3. Reorder sections/bullets so the most JD-relevant evidence is in the top third.
4. Cut or compress content the target role doesn't care about to protect the
   one-page limit.
5. Anything the JD wants that the source material doesn't support → gaps list,
   ask the user. Don't invent it.

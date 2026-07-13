# Jump-start: import your context from an AI assistant

Filling `source_material/` from scratch is the slowest part of setup. If you've
used ChatGPT, Claude, Gemini, Copilot, or similar, they've often stored a lot of
career-relevant context about you already — projects, roles, skills, goals. You
can export that in one shot and use it to seed your source files.

> **Read this first.** An AI's memory is a *starting point*, not truth. It is
> frequently incomplete, out of date, or subtly wrong — and this toolkit treats
> `source_material/` as ground truth and **will not fabricate** (`CONSTRAINTS.md`
> §1). A wrong fact you paste in here becomes a wrong, indefensible résumé line.
> So: import, then **verify and correct every entry**, fix the numbers, and keep
> only what you could defend in an interview.

## 1. Run the export prompt

Paste this into each assistant you've used a lot. It's adapted from Anthropic's
data-export prompt, but focused on what a résumé actually needs — and it insists
on **exact numbers**, which are what land interviews and what the agent can't
invent for you.

```
I'm building a tailored résumé and want to export everything you know about my
professional and academic background. List every memory you have stored about
me, plus any context you've learned about me from past conversations that could
matter for a résumé or job application.

Output everything in a single code block so I can copy it. Format each entry as:
[date saved, if available] - content. Preserve my words verbatim where possible,
and KEEP ALL NUMBERS AND METRICS EXACTLY (percentages, latencies, user/request
counts, dollar amounts, dataset sizes, model sizes, rankings, GPAs, dates).

Organize entries under these headings, and include everything you have for each:
- CONTACT & LINKS: name, location, email, GitHub, LinkedIn, personal site/blog,
  Google Scholar.
- EDUCATION: schools, degrees, majors/minors, GPA, start/grad dates, honors,
  thesis.
- EXPERIENCE: every job, internship, research role, TA/teaching — company,
  title, dates, and specifically what I built or shipped and its measurable
  impact (with the numbers).
- PROJECTS: personal / open-source / course / hackathon / research projects —
  what each does, my role, tech stack, links, and traction (stars, users,
  benchmarks).
- TECHNICAL SKILLS: languages, frameworks, tools, and domains I actually use,
  with any sign of how deeply.
- COURSEWORK: relevant advanced or graduate courses.
- AWARDS & COMPETITIONS: awards, scholarships, competitive programming
  (ratings/ranks), olympiads, Kaggle, hackathon wins, trading/mental-math scores.
- PUBLICATIONS & RESEARCH: papers/talks with venue, year, my authorship
  position, links, and citation counts.
- LEADERSHIP & ACTIVITIES: leadership, mentoring, community/open-source,
  volunteering — with scope and impact.
- OTHER: career goals, target companies/roles, constraints (work authorization,
  location, timeline), and any stated preferences.

Do not summarize, group away detail, or omit entries. If you're unsure something
is accurate, still include it but mark it "(unverified)". After the code block,
tell me whether that's the complete set or if more remains, and list any
career-relevant info you do NOT appear to have about me.
```

If the assistant can generate files, add: *"Also export this as a Markdown
file."* Trim anything sensitive before saving it into this repo.

## 2. Where each assistant keeps memory (varies, changes often)

- **ChatGPT** — Settings → Personalization → *Memory*; or just run the prompt
  (it can also draw on chat history if that's enabled).
- **Claude** — can reference your past chats / stored memory when asked; run the
  prompt directly.
- **Gemini** — *Saved info* / personalization; run the prompt directly.
- **Copilot / others** — run the prompt; memory support differs by product.

Memory features and their names change — if one heading comes back empty, the
assistant may simply not store that; move on.

## 3. Land it in `source_material/`

The prompt's headings map 1:1 onto the section templates
(`source_material/README.md`):

| Export heading | File |
|----------------|------|
| CONTACT & LINKS | `CONTACT.md` |
| EDUCATION | `EDUCATION.md` |
| EXPERIENCE | `EXPERIENCE.md` |
| PROJECTS | `PROJECTS.md` |
| TECHNICAL SKILLS | `TECHNOLOGIES.md` |
| COURSEWORK | `COURSES.md` |
| AWARDS & COMPETITIONS | `AWARDS.md` |
| PUBLICATIONS & RESEARCH | `PUBLICATIONS.md` |
| LEADERSHIP & ACTIVITIES | `VOLUNTEERING.md` |
| OTHER | any of the above, or a note at the top of `EXPERIENCE.md` |

Copy each `*.example.md` to its real `*.md` first (see
`source_material/README.md`), then paste the matching export section in.

## 4. Verify — do not skip this

1. **Delete anything untrue or `(unverified)` you can't confirm.**
2. **Fix every number** — memory paraphrases metrics; use the real ones from a
   dashboard, PR, offer letter, or transcript.
3. **Fill the gaps** the export missed (it rarely has your best metrics).
4. Keep only what you can defend in an interview.

## Privacy

This export is personal data. It lives in `source_material/`, which is
**gitignored** and stays on your machine (`PRIVACY.md`). Don't paste it into a
committed file, and redact anything sensitive before saving.

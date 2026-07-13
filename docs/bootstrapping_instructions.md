> **HISTORICAL / DESIGN NOTE.** This is the original brief that seeded the
> toolkit. It is kept for provenance only and may not match the shipped
> conventions (e.g. it predates the `<slug>_resume.tex` naming and the
> `source_material/` layout). For how the toolkit actually works, read
> `AGENT.md` and `OPTIMIZATION_LOOP.md` — not this file.

---

Idea:

This repo will act as an agentic resume optimization loop, taiing advantage 
of coding agents. 

The idea is to post your master resume/ cv, and have an agent optimize your 
resume for target job descriptions. Critera include but are not limited to 
ATS score, relevance to target job, etc. 

User initial setup:
1. Make dir called resumes
2. Upload job descriptions to job_descriptions/, delete cloned ones you don't 
want
3. Start coding agent, tell it to read README, AGENT and start optimizing for 
the specified jobs in natural language

Agent workflow:

Read the repo context and follow an optimizations loop, which involves:
Read JD, user source material, and existing resumes -> optimize resume for 
that job, output of the form {job name}_resume.tex, using the given template 
and subject to constraints (e.g. page length when pdf output) -> independent 
verifiers score the resume -> log it and iterate, only keeping changes that 
score higher

Contraints:
- resume pdf should be exactly 1 page 
- follow the template
- etc

INSTRUCTIONS:

given the above idea, populate the readme with appropriate context for users 
on the repo overview and usage, concisely with easy to follow language. 

afterwards, please draft an OPTIMIZATION_LOOP.md which contains specific 
instructions for the round / loop-based optimization. it should only target 
posts which fit the users instructions, and ask the user if no preference was 
given (e.g. user might say to target job descriptions from X company). 
the AGENT.md should give this context and then point the agent to read the 
optimization markdown. 


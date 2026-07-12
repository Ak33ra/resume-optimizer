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
3. Start coding agent, tell it to read README, AGENT and start optimizing 

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

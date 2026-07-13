# ROLE PROFILES

Industry-specific playbooks. A resume tuned for one family underperforms for
another — the signals, section order, and keywords genuinely differ. When a job
description has a `family:` field (see `job_descriptions/README.md`), use that
profile. Otherwise infer it from the JD and, if unsure, ask the user.

Families (the codes used in JD front-matter and `optimization_log.md`):
`big_tech`, `quant_swe`, `quant_research`, `quant_trading`, `research_lab`,
`startup`, `other`.

Cross-cutting seniority note:
- **intern** — coursework + one project/internship + relevant skills carry it.
- **new_grad** — must show substantive *shipped* work; internships > projects >
  coursework for standard SWE (research > internships for research roles).
- **experienced (1–4 yr)** — lead with professional experience; scope,
  ownership, and impact dominate; shrink or drop projects/coursework.

---

## big_tech — Big Tech / FAANG-tier SWE

Google, Meta, Amazon, Apple, Microsoft, Netflix, Nvidia, Stripe, Databricks, etc.

**How it's screened:** a recruiter keep/reject in ~6–10 seconds. The top third
must look "on-pattern": clear current title, recognizable company or strong
project, quantified impact, matching keywords. The resume mainly gates into a
coding online assessment, so pass-the-scan + real keyword-matched skills matter
more than GPA or school prestige.

**Section order:** thin experience → Education, Projects, Experience, Skills.
Strong internships → Experience, Projects, Education, Skills. Put a compact
categorized Skills block high enough to be seen fast.

**Emphasize:** internships at recognizable companies (2–4 quantified bullets
each); substantive projects (open-source with adoption, systems, real users,
hackathon wins, competitive-programming, research) — *not* tutorial/CRUD/clone
apps; DS&A and system-design signal; GPA if ~3.5+.

**Keywords (use only what's true, match JD phrasing):** Python, Java, C++, Go,
TypeScript, SQL; React, Node, Spring, gRPC, REST; PostgreSQL, Redis, Kafka,
Spark; AWS/GCP, Docker, Kubernetes, Terraform, CI/CD; Distributed Systems,
Microservices, Concurrency, System Design, Scalability, low latency (p95/p99).

**Firm cues:** Google — literally champions XYZ bullets. Amazon — frame impact
toward Leadership Principles (Ownership, Bias for Action, Deliver Results).
Stripe — practical, work-like interviews (not LeetCode); emphasize real shipped,
correct, production-quality engineering. Nvidia/Databricks/infra teams — systems
depth (C++/CUDA/GPU, perf, Spark), quantify throughput/latency/memory. Netflix —
early-career roles are rare and skew senior; needs stronger evidence of
independent impact.

**Don't:** exceed one page; use designer/2-column templates; open bullets with
responsibilities; include an objective, high-school info, or hobby lists; dump
40+ skills; send one generic resume to every company.

---

## quant_swe — Quant Software Engineer / Core Dev

Jane Street, HRT, Citadel Securities, Jump, D.E. Shaw (core dev), Optiver, IMC.

**How it's screened:** algorithmic strength first; for low-latency shops (HRT,
Jump, Citadel Securities, DE Shaw core dev), demonstrable C++/systems/OS/
networking depth. Competitive-programming rank is the single strongest override
for a weak GPA or non-target school.

**Emphasize (in order for non-target/low-GPA candidates):** competitive
programming at the very top — ICPC (World Finalist/Regionalist), Codeforces
(Candidate Master / Master / Grandmaster + rating), IOI, LeetCode contest
strength; then top-tech/quant SWE internships; latency-optimization and systems
projects; open-source with real ownership.

**Keywords:** C++ (C++17/20, templates, RAII, move semantics), low-latency,
lock-free, concurrency/multithreading, Linux, OS internals, CPU architecture,
cache/NUMA, kernel bypass, networking (TCP/IP, UDP, multicast), FPGA/ASIC
(bonus), profiling/perf, deterministic latency; DS&A, distributed systems,
compilers; Python, Rust (some shops), kdb+/q (some shops).

**Firm cues:** Jane Street — **no GPA/degree bar, hand-reads every application,
no ATS scanners, no required language (not even OCaml)**; lead with curiosity +
demonstrable coding; **write your own cover letter — AI-written apps are
binned.** HRT — wants "top developer in your org", explicit low-latency C++ +
hardware exposure. DE Shaw/Jump — HackerRank/algorithmic screens.

**GPA:** list only if ≥3.7 / First / 2:1 (a higher bar than FAANG's ~3.5);
otherwise omit it and let competitions/projects carry the page.

**De-emphasize:** heavy pure-math/measure-theory framing (unless a research-eng
hybrid); trader/mental-math game scores.

---

## quant_research — Quantitative Researcher / Quant

Citadel & Citadel Securities, Two Sigma, D.E. Shaw, Jump, Point72/Cubist, etc.

**How it's screened:** mathematical/statistical depth + research capability +
(usually) an advanced degree. Interviews resemble a PhD qualifying exam. PhD is
the default at Citadel Securities / Two Sigma / DE Shaw / Jump for senior QR;
BS/MS is fine for analyst/intern tiers and Point72/Cubist entry level.

**Section order:** short summary/interests → Publications/Research → Experience
→ Education (with advanced coursework) → Skills. Lead with research output.

**Emphasize:** publications/conference talks; Putnam/IMO/IOI; Kaggle
(Master/Grandmaster — casual participation is weak signal); WorldQuant BRAIN;
thesis with methodology; research projects with rigorous methods + quantified
out-of-sample results (rank IC, Sharpe, information ratio, AUC). List advanced
coursework: probability theory, **measure theory, stochastic calculus**,
statistical inference, time-series, convex/numerical optimization, real
analysis, ML/DL.

**Keywords:** probability, mathematical statistics, stochastic calculus, measure
theory, time-series, Bayesian inference, Monte Carlo, convex optimization,
linear algebra, stochastic processes; machine learning, deep learning,
XGBoost/LightGBM, feature engineering, NLP, cross-validation, signal/alpha
research, overfitting control; Python (pandas, NumPy, scikit-learn, PyTorch),
C++, R, SQL, kdb+/q.

**GPA:** list only if ≥3.7 / First / 2:1 (higher bar than FAANG's ~3.5).

**De-emphasize:** pure low-latency systems detail; mental-math game scores.
**Don't:** apply to senior QR as an undergrad with no research/publications —
target analyst/rotational tiers instead.

---

## quant_trading — Trader

Optiver, IMC, SIG/Susquehanna, Jane Street, Akuna, Jump, DRW, etc.

**How it's screened:** speed + accuracy in mental math and probability, EV/game
reasoning, competitiveness, composure. Assessments are the hard filter (Optiver
"80-in-8", IMC "NeurOlympics", SIG poker/EV + probability brainteasers, trading
sims). Hired straight from undergrad.

**Emphasize:** mental-math scores — report your **raw score per test**, don't
apply one number across tests (Zetamac ~50+ good / 65+ strong; Optiver 80-in-8
report as-is; SIG and other drills score differently); competitive achievement
of any kind — **poker (especially SIG)**, chess rating, competitive sports,
debate, math olympiads (AMC/AIME/Putnam); trading-game / datathon wins; STEM
degree with a **high GPA (list if ≥3.7)**; basic Python + probability.

**Keywords:** probability, expected value (EV), mental math, options pricing,
market making, risk management, game theory, decision-making under uncertainty,
statistics.

**Firm cues:** SIG — poker/decision-theory culture. Optiver — options-pricing
rigor + arithmetic speed. IMC — cognitive-game batteries. Jane Street traders —
strong quantitative minds, finance optional.

**De-emphasize (these dilute a trader profile):** deep ML, publications,
low-latency C++, measure theory.

---

## research_lab — Frontier / Industry AI Research

Anthropic, OpenAI, Google DeepMind, Meta FAIR/GenAI, Microsoft Research/AI,
Mistral, Cohere, xAI, Nvidia Research. Roles: Research Engineer (RE), Research
Scientist (RS), Member of Technical Staff (MTS), ML Engineer (MLE).

**How it's screened:** demonstrated evidence of building/discovering at the AI
frontier — not a job-ladder narrative. The big split:
- **RS** — top-venue publications (NeurIPS/ICML/ICLR/ACL/CVPR), first/last
  authorship, research taste, usually a PhD. → publication-forward CV; selected
  publications high up. A pure RS/academic application may run to a **1–2 page
  CV** — the one exception to the one-page rule (`CONSTRAINTS.md` §2), opt in per
  target; compile with `scripts/compile.sh <tex> 2`.
- **RE / MTS / MLE** — strong systems engineering fused with real ML at scale.
  **PhD not required** if a public portfolio proves capability. → impact/systems
  resume, **one page**; a compact Publications/OSS section or links.

**Section order (Anthropic's explicit guidance, applies broadly):** put your
strongest evidence at the **top** — independent research, a notable repo, a
well-read technical blog post, or a first-author paper — regardless of type.
3+ relevant top-venue papers → dedicated Publications section placed early;
fewer → fold into Research/Projects or link Google Scholar/GitHub.

**Emphasize:** scale + systems depth (cluster sizes, parallelism strategy,
tokens/params, GPU-hours, reliability); reproductions of SOTA papers; a **live
portfolio link in the header** (GitHub, personal site, **technical blog**,
Google Scholar) — for Anthropic a well-read blog post or notable repo can be
your single strongest top-of-page item; mission/safety engagement (alignment,
evals, interpretability) you actually did; high agency and empiricism (owned
ambiguous problems, ran experiments, iterated fast).

**Keywords:** LLMs, transformers, attention, tokenization; pre/mid/post-training,
fine-tuning, RLHF/RLAIF, DPO/PPO, reward modeling, Constitutional AI (Anthropic);
evals, red-teaming, interpretability, alignment, AI safety; PyTorch, JAX/Flax
(DeepMind-native), Hugging Face, DeepSpeed, Megatron-LM, vLLM, FSDP, Triton;
distributed training, tensor/pipeline/model parallelism, ZeRO, CUDA, GPU kernel
optimization, mixed precision, Kubernetes, Ray, Slurm; inference optimization,
quantization, KV-cache; data pipelines, dataset curation/dedup; scaling laws,
ablations, baselines.

**Firm cues:** Anthropic — "cares what you can do, not where you learned it";
empirical/pragmatic ("simple thing that works"); high agency; **the safety/values
round eliminates more technically-qualified candidates than any other stage** —
genuine safety engagement must show in the portfolio; if your strength is
engineering, apply as an *engineer*. DeepMind — JAX-native, scientific rigor.
Meta FAIR — first/last-author top-venue pubs required for RS. Cohere — top papers
+ citation counts prominent. xAI/OpenAI — velocity, scrappiness, a considered
AGI/safety view.

**Don't:** use a generic SWE/LeetCode resume or buzzword padding (signals
misunderstanding); bury research/OSS under routine duties; write task lists with
no outcomes; over-claim keywords or inflate authorship (interviewers probe hard);
submit a multi-page academic CV for an engineer/MTS req.

---

## startup — Startups / Scaleups

**How it's screened:** breadth, ownership, and shipping speed. Founders want
evidence you build end-to-end and move fast with little structure.

**Emphasize:** full-stack range; things you shipped to real users; ownership of
whole features/products; measurable growth/impact; comfort with ambiguity;
relevant modern stack matching theirs. Named metrics (users, revenue, growth %).

**Don't:** over-specialize the narrative; hide the breadth; lead with process
over outcomes.

---

## other — General / everything else

Fall back to `WRITING_GUIDE.md` fundamentals: impact-first XYZ bullets, one page,
single-column ATS-safe format, JD keyword matching, strongest signal in the top
third. Infer what the specific employer values from the JD and tailor
accordingly; ask the user if the target is unclear.

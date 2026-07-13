#!/usr/bin/env python3
"""Independent benchmark for a generated resume — parse-safety + JD match.

Cross-checks the toolkit's own `scripts/ats_check.py` with *independent* scorers
so a disagreement is a signal worth investigating. Runs locally and offline; no
PII leaves the machine.

Usage:
    python3 benchmarks/benchmark.py <resume.pdf> --jd <jd.txt|.md> [--slug NAME] [--round N]

Richer scorers are used automatically **if installed** (see requirements.txt):
  - skillNer + spaCy en_core_web_lg   → dictionary-based skill coverage (~60k skills)
  - sentence-transformers             → semantic cosine similarity
Without them it falls back to a built-in CS/quant/ML skill lexicon and skips the
cosine metric — printing the pip command so you can enable the richer path.

Writes benchmarks/results/<slug>_r<round>.json and prints a summary. Read-only
against your resume; never mutates resumes/.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")

# Keep in sync with scripts/ats_check.py ALLOWED_HEADINGS and CONSTRAINTS.md sec 4.
STANDARD_HEADINGS = [
    "education", "experience", "work experience", "professional experience",
    "employment", "skills", "technical skills", "projects", "certifications",
    "summary", "publications", "research", "awards", "honors", "leadership",
    "volunteer",
]

# Built-in fallback lexicon (curated from the toolkit's research notes). Used
# only when SkillNer is not installed. Lowercase; multi-word allowed.
SKILL_LEXICON = {
    # languages
    "python", "java", "c++", "c#", "c", "go", "golang", "rust", "typescript",
    "javascript", "sql", "scala", "kotlin", "swift", "r", "matlab", "ocaml",
    "haskell", "bash", "cuda", "verilog",
    # web / frameworks
    "react", "node.js", "node", "next.js", "angular", "vue", "spring",
    "spring boot", "django", "flask", "fastapi", "rest", "graphql", "grpc",
    "express", "redux",
    # data / storage / infra
    "postgresql", "postgres", "mysql", "mongodb", "redis", "kafka", "spark",
    "hadoop", "elasticsearch", "kubernetes", "docker", "terraform", "aws",
    "gcp", "azure", "linux", "bazel", "ci/cd", "jenkins", "github actions",
    "airflow", "kdb+", "ray", "slurm",
    # cs concepts
    "distributed systems", "microservices", "concurrency", "multithreading",
    "system design", "data structures", "algorithms", "operating systems",
    "compilers", "networking", "low latency", "scalability", "fault tolerance",
    "object-oriented", "tcp/ip", "lock-free", "kernel", "fpga",
    # ml / research
    "pytorch", "tensorflow", "jax", "flax", "scikit-learn", "numpy", "pandas",
    "hugging face", "transformers", "llm", "llms", "nlp", "computer vision",
    "reinforcement learning", "rlhf", "rlaif", "dpo", "ppo", "deep learning",
    "machine learning", "mlops", "fine-tuning", "distributed training",
    "quantization", "vllm", "deepspeed", "megatron", "fsdp", "triton",
    "diffusion", "evals", "interpretability", "alignment", "xgboost",
    "lightgbm", "weights & biases", "constitutional ai",
    # quant / math
    "probability", "statistics", "stochastic calculus", "measure theory",
    "time series", "linear algebra", "convex optimization", "monte carlo",
    "bayesian", "options pricing", "market making", "expected value",
    "game theory", "signal processing", "backtesting",
    # tools / practices
    "git", "agile", "scrum", "unit testing", "tdd", "observability",
}


def extract_text(pdf: str) -> str:
    try:
        from pypdf import PdfReader
    except Exception:
        PdfReader = None
    if PdfReader is not None:
        try:
            return "\n".join((p.extract_text() or "") for p in PdfReader(pdf).pages)
        except Exception as e:
            sys.exit(f"ERROR: could not read '{pdf}' as a PDF ({e}).")
    try:
        return subprocess.check_output(["pdftotext", "-layout", pdf, "-"], text=True)
    except FileNotFoundError:
        sys.exit("ERROR: no PDF text extractor. Install `pip install pypdf` or `apt-get install -y poppler-utils`.")
    except Exception as e:
        sys.exit(f"ERROR: could not read '{pdf}' ({e}).")


def _norm(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9+#./& -]", " ", text.lower()) + " "


def _lexicon_terms(text: str, lexicon) -> set:
    t = re.sub(r"\s+", " ", _norm(text))
    return {s for s in lexicon if f" {s} " in t}


def keyword_coverage(resume_text: str, jd_text: str) -> dict:
    """Prefer SkillNer (skill DB); fall back to the built-in lexicon."""
    try:
        import spacy
        from spacy.matcher import PhraseMatcher
        from skillNer.skill_extractor_class import SkillExtractor
        from skillNer.general_params import SKILL_DB
        nlp = spacy.load("en_core_web_lg")
        se = SkillExtractor(nlp, SKILL_DB, PhraseMatcher)

        def skills(t):
            res = se.annotate(t)["results"]
            return {m["doc_node_value"].lower()
                    for m in res["full_matches"] + res["ngram_scored"]}
        jd, rv, method = skills(jd_text), skills(resume_text), "skillner"
    except Exception:
        jd = _lexicon_terms(jd_text, SKILL_LEXICON)
        rv = _lexicon_terms(resume_text, SKILL_LEXICON)
        method = "builtin-lexicon"
    covered = sorted(jd & rv)
    missing = sorted(jd - rv)
    pct = round(100 * len(covered) / max(1, len(jd)))
    return {"method": method, "coverage_pct": pct,
            "jd_skill_count": len(jd), "covered": covered, "missing": missing}


def semantic_match(resume_text: str, jd_text: str) -> dict:
    try:
        from sentence_transformers import SentenceTransformer, util
        model = "all-MiniLM-L6-v2"
        m = SentenceTransformer(model)
        cos = float(util.cos_sim(m.encode(resume_text), m.encode(jd_text)))
        return {"cosine": round(cos, 4), "model": model}
    except Exception:
        return {"cosine": None, "model": None,
                "note": "install `pip install sentence-transformers` for semantic similarity"}


def parse_safety(text: str) -> dict:
    """Heuristic parse-safety checklist. The authoritative check is a real
    parser (OpenResume) + a ground-truth diff — see README.md."""
    head = "\n".join([l for l in text.splitlines() if l.strip()][:15])
    checks = {
        "selectable_text": len(text) > 200,
        "no_replacement_chars": "�" not in text,
        "email_extracted": bool(re.search(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", head, re.I)),
        "contact_link_or_phone": bool(
            re.search(r"\+?\d[\d\-.\s()]{7,}\d", head)
            or re.search(r"(github|linkedin|scholar|http)", head, re.I)),
        "standard_headings": sum(
            bool(re.search(r"(?m)^\s*" + re.escape(h) + r"\s*$", text.lower()))
            for h in STANDARD_HEADINGS) >= 3,
    }
    passed = sum(checks.values())
    return {"score_pct": round(100 * passed / len(checks)), "checks": checks}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--jd", required=True, help="job description text/markdown file")
    ap.add_argument("--slug", help="target id (defaults to the PDF basename)")
    ap.add_argument("--round", type=int, default=0)
    args = ap.parse_args()

    slug = args.slug or re.sub(r"_resume.*", "", os.path.basename(args.pdf)).rsplit(".", 1)[0]
    resume_text = extract_text(args.pdf)
    with open(args.jd, encoding="utf-8") as f:
        jd_text = f.read()

    result = {
        "slug": slug,
        "round": args.round,
        "date": datetime.date.today().isoformat(),
        "parse_safety": parse_safety(resume_text),
        "keywords": keyword_coverage(resume_text, jd_text),
        "semantic": semantic_match(resume_text, jd_text),
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out = os.path.join(RESULTS_DIR, f"{slug}_r{args.round}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    ps = result["parse_safety"]
    kw = result["keywords"]
    sem = result["semantic"]
    print(f"\n=== benchmark: {slug} (round {args.round}) ===")
    print(f"parse-safety : {ps['score_pct']}%   (target 100)   {ps['checks']}")
    print(f"keyword cov. : {kw['coverage_pct']}%  via {kw['method']}   "
          f"(target ~60-80; {len(kw['covered'])}/{kw['jd_skill_count']} JD skills)")
    if kw["missing"]:
        print(f"  missing JD skills: {', '.join(kw['missing'][:25])}")
    print(f"semantic cos.: {sem['cosine']}  {('('+sem['model']+')') if sem['cosine'] is not None else sem.get('note','')}")
    print(f"\nsaved → {out}")
    print("Cross-check manually with OpenResume / Jobalytics / Jobscan — see benchmarks/README.md")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Aggregate benchmarks/results/*.json into a before/after delta table.

Usage:
    python3 benchmarks/report.py [--slug NAME]   # all slugs, or one

The point of the toolkit is *improvement*, so the headline evidence is the
per-round delta, not any single absolute score. Prints a markdown table.
"""
import argparse
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")


def load():
    rows = []
    for path in glob.glob(os.path.join(RESULTS_DIR, "*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                rows.append(json.load(f))
        except Exception:
            continue
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug")
    args = ap.parse_args()

    rows = [r for r in load() if not args.slug or r.get("slug") == args.slug]
    if not rows:
        print("No results yet. Run: python3 benchmarks/benchmark.py <pdf> --jd <jd> --slug <slug> --round <n>")
        return

    by_slug = {}
    for r in rows:
        by_slug.setdefault(r.get("slug", "?"), []).append(r)

    for slug, rs in sorted(by_slug.items()):
        rs.sort(key=lambda r: r.get("round", 0))
        print(f"\n## {slug}\n")
        print("| Round | Parse-safety | Keyword cov. | Semantic cos. | Coverage method |")
        print("|------:|:------------:|:------------:|:-------------:|:----------------|")
        for r in rs:
            ps = r.get("parse_safety", {}).get("score_pct", "—")
            kw = r.get("keywords", {})
            cov = kw.get("coverage_pct", "—")
            cos = r.get("semantic", {}).get("cosine")
            cos = "—" if cos is None else cos
            print(f"| {r.get('round','—')} | {ps}% | {cov}% | {cos} | {kw.get('method','—')} |")
        first, last = rs[0], rs[-1]
        d_cov = last.get("keywords", {}).get("coverage_pct", 0) - first.get("keywords", {}).get("coverage_pct", 0)
        d_ps = last.get("parse_safety", {}).get("score_pct", 0) - first.get("parse_safety", {}).get("score_pct", 0)
        print(f"\nΔ from baseline: parse-safety {d_ps:+d}pp, keyword coverage {d_cov:+d}pp")


if __name__ == "__main__":
    main()

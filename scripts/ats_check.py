#!/usr/bin/env python3
"""ATS parse-safety, source-structure, and keyword-coverage checker."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

try:
    from .ats_rules import hard_checks_pass, tex_checks, text_checks
except ImportError:  # Direct execution
    from ats_rules import hard_checks_pass, tex_checks, text_checks


def normalize(text: str) -> str:
    return " " + re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+#./& -]", " ", text.lower())) + " "


def extract_text(pdf: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        PdfReader = None
    if PdfReader is not None:
        try:
            return "\n".join((page.extract_text() or "") for page in PdfReader(pdf).pages)
        except Exception as exc:
            raise RuntimeError(f"could not read {pdf!r} as a PDF ({exc})") from exc
    try:
        return subprocess.check_output(
            ["pdftotext", "-layout", pdf, "-"], text=True, stderr=subprocess.PIPE
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "no PDF extractor available; install pypdf or poppler-utils"
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"could not read {pdf!r} ({exc})") from exc


def keyword_coverage(text: str, path: str | None) -> dict | None:
    if not path:
        return None
    with open(path, encoding="utf-8") as handle:
        keywords = [line.strip() for line in handle if line.strip() and not line.lstrip().startswith("#")]
    padded = normalize(text)
    present = [keyword for keyword in keywords if f" {normalize(keyword).strip()} " in padded]
    missing = [keyword for keyword in keywords if keyword not in present]
    return {
        "present": present,
        "missing": missing,
        "total": len(keywords),
        "coverage_pct": round(100 * len(present) / max(1, len(keywords))),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf")
    parser.add_argument("--tex", help="LaTeX source for structure checks")
    parser.add_argument("--keywords", help="file with one JD keyword per line")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        extracted = extract_text(args.pdf)
        checks = text_checks(extracted)
        if args.tex:
            with open(args.tex, encoding="utf-8", errors="replace") as handle:
                checks.extend(tex_checks(handle.read()))
        coverage = keyword_coverage(extracted, args.keywords)
    except (OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)

    passed = hard_checks_pass(checks)
    output = {"passed": passed, "checks": checks, "keyword_coverage": coverage}
    if args.json:
        print(json.dumps(output, indent=2))
    else:
        for item in checks:
            if item["hard"]:
                status = "PASS" if item["passed"] else "FAIL"
            else:
                status = "ok" if item["passed"] else "WARN"
            detail = f" - {item['detail']}" if item["detail"] else ""
            print(f"[{status}] {item['name']}{detail}")
        if coverage is not None:
            print(
                f"\nKEYWORD COVERAGE: {len(coverage['present'])}/{coverage['total']} "
                f"({coverage['coverage_pct']}%) [target ~60-80%]"
            )
            if coverage["missing"]:
                print("  missing: " + ", ".join(coverage["missing"]))
        print("\nRESULT:", "PASS" if passed else "FAIL")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()

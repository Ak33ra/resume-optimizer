#!/usr/bin/env python3
"""ATS parse-safety + keyword-coverage checker for a compiled resume PDF.

Usage:
    python3 scripts/ats_check.py <resume.pdf> [--keywords kw.txt]

Runs the mechanically-checkable rules from CONSTRAINTS.md sec 4 against the
rendered PDF (the thing an ATS actually sees). [PASS/FAIL] lines are hard gate
checks; [ok/WARN] lines are advisory. With --keywords (one JD term per line, '#'
comments allowed) it also reports keyword coverage.

Text extraction uses pypdf if available, else the `pdftotext` CLI (poppler).
Exit code: 0 if all hard checks pass, 1 if any failed, 2 if text can't be read.
"""
import argparse
import re
import subprocess
import sys

# Keep in sync with CONSTRAINTS.md sec 4 and benchmarks/benchmark.py.
ALLOWED_HEADINGS = {
    "education", "experience", "work experience", "professional experience",
    "employment", "skills", "technical skills", "projects", "certifications",
    "summary", "professional summary", "publications", "research",
    "research experience", "awards", "awards & competitions",
    "awards and competitions", "honors", "leadership", "volunteer",
}


def _norm(text: str) -> str:
    """Lowercase and collapse to space-delimited tokens for boundary matching."""
    return " " + re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+#./& -]", " ", text.lower())) + " "


def extract_text(pdf: str) -> str:
    try:
        from pypdf import PdfReader
    except Exception:
        PdfReader = None
    if PdfReader is not None:
        try:
            return "\n".join((p.extract_text() or "") for p in PdfReader(pdf).pages)
        except Exception as e:
            print(f"ERROR: could not read '{pdf}' as a PDF ({e}).", file=sys.stderr)
            sys.exit(2)
    try:
        return subprocess.check_output(["pdftotext", "-layout", pdf, "-"], text=True)
    except FileNotFoundError:
        print("ERROR: no PDF text extractor available. Install one:\n"
              "  pip install pypdf\n  apt-get install -y poppler-utils", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"ERROR: could not read '{pdf}' ({e}).", file=sys.stderr)
        sys.exit(2)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--keywords", help="file with one JD keyword per line")
    args = ap.parse_args()

    text = extract_text(args.pdf)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    low = text.lower()
    hard_fail = False

    def check(ok: bool, label: str, detail: str = "") -> None:
        nonlocal hard_fail
        print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
        if not ok:
            hard_fail = True

    def warn(ok: bool, label: str, detail: str = "") -> None:
        print(f"[{'ok' if ok else 'WARN'}] {label}" + (f" — {detail}" if detail else ""))

    # 1. Text is machine-selectable.
    check(len(text) > 200, "machine-selectable text", f"{len(text)} chars extracted")
    # 2. No replacement characters / broken encoding.
    check("�" not in text, "no replacement characters (U+FFFD)")
    # 3. Contact info near the top (in the body, not a header/footer).
    head = "\n".join(lines[:15])
    email = re.search(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", head, re.I)
    phone = re.search(r"\+?\d[\d\-.\s()]{7,}\d", head)
    check(bool(email), "email present near top", email.group(0) if email else "not in first 15 lines")
    warn(bool(phone), "phone present near top")
    # 4. Standard section headings (>=3, matching benchmarks/benchmark.py).
    found = sorted({h for h in ALLOWED_HEADINGS
                    if re.search(r"(?m)^\s*" + re.escape(h) + r"\s*$", low)})
    check(len(found) >= 3, "standard section headings detected", ", ".join(found) or "none")
    # 5. Date formats — hard gate (CRITERIA.md gate #5): no year-only ranges,
    #    'YY, or season-year values that parsers drop or misread.
    bad = re.findall(r"\b(?:19|20)\d{2}\s*[–-]\s*(?:19|20)\d{2}\b", text)
    bad += re.findall(r"'\d{2}\b", text)
    bad += re.findall(r"\b(?:Spring|Summer|Fall|Autumn|Winter)\s+\d{4}\b", text, flags=re.I)
    check(not bad, "date formats (Mon YYYY ranges; no year-only / 'YY / season-year)",
          ("suspect: " + ", ".join(sorted(set(bad)))) if bad else "clean")

    # 6. Keyword coverage (optional; advisory — NOT a gate).
    if args.keywords:
        with open(args.keywords) as f:
            kws = [k.strip() for k in f if k.strip() and not k.startswith("#")]
        padded = _norm(text)
        def _present(k: str) -> bool:
            return f" {_norm(k).strip()} " in padded
        present = [k for k in kws if _present(k)]
        missing = [k for k in kws if not _present(k)]
        pct = 100 * len(present) // max(1, len(kws))
        print(f"\nKEYWORD COVERAGE: {len(present)}/{len(kws)} ({pct}%)  [target ~60-80%]")
        if missing:
            print("  missing:", ", ".join(missing))

    print()
    print("RESULT:", "FAIL" if hard_fail else "PASS")
    sys.exit(1 if hard_fail else 0)


if __name__ == "__main__":
    main()

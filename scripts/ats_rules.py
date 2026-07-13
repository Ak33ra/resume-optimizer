"""Shared, mechanically checkable ATS rules."""

from __future__ import annotations

import re
from typing import Any


ALLOWED_HEADINGS = {
    "education",
    "experience",
    "work experience",
    "professional experience",
    "employment",
    "skills",
    "technical skills",
    "projects",
    "certifications",
    "summary",
    "professional summary",
    "publications",
    "research",
    "research experience",
    "awards",
    "awards & competitions",
    "awards and competitions",
    "honors",
    "leadership",
    "volunteer",
    "volunteering",
}

MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
SEPARATOR = r"(?:--|[-\u2013\u2014])"
VALID_RANGE = re.compile(
    rf"\b{MONTH}\s+(?:19|20)\d{{2}}\s*{SEPARATOR}\s*"
    rf"(?:{MONTH}\s+(?:19|20)\d{{2}}|Present)\b",
    re.IGNORECASE,
)
POSSIBLE_RANGE = re.compile(
    rf"\b(?:[A-Za-z]+\s+)?(?:19|20)\d{{2}}\s*{SEPARATOR}\s*"
    rf"(?:(?:[A-Za-z]+\s+)?(?:19|20)\d{{2}}|Present)\b",
    re.IGNORECASE,
)


def result(name: str, passed: bool, detail: str = "", *, hard: bool = True) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail, "hard": hard}


def text_checks(text: str) -> list[dict[str, Any]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    head = "\n".join(lines[:15])
    low = text.lower()
    email = re.search(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", head, re.IGNORECASE)
    phone = re.search(r"\+?\d[\d\-.\s()]{7,}\d", head)
    headings = sorted(
        heading
        for heading in ALLOWED_HEADINGS
        if re.search(r"(?m)^\s*" + re.escape(heading) + r"\s*$", low)
    )

    possible_ranges = POSSIBLE_RANGE.findall(text)
    malformed_ranges = [value for value in possible_ranges if not VALID_RANGE.fullmatch(value)]
    shorthand_years = re.findall(r"'\d{2}\b", text)
    season_years = re.findall(
        r"\b(?:Spring|Summer|Fall|Autumn|Winter)\s+\d{4}\b", text, re.IGNORECASE
    )
    date_issues = sorted(set(malformed_ranges + shorthand_years + season_years))
    valid_ranges = VALID_RANGE.findall(text)

    return [
        result("machine-selectable text", len(text) > 200, f"{len(text)} chars extracted"),
        result("no replacement characters (U+FFFD)", "\ufffd" not in text),
        result(
            "email present near top",
            bool(email),
            email.group(0) if email else "not in first 15 non-empty lines",
        ),
        result("phone present near top", bool(phone), hard=False),
        result(
            "standard section headings detected",
            len(headings) >= 3,
            ", ".join(headings) or "none",
        ),
        result(
            "date ranges use Mon YYYY -- Mon YYYY/Present",
            not date_issues,
            "suspect: " + ", ".join(date_issues) if date_issues else "clean",
        ),
        result(
            "at least one valid date range detected",
            bool(valid_ranges),
            f"{len(valid_ranges)} detected",
            hard=False,
        ),
    ]


def _nonempty_command(tex: str, command: str) -> bool:
    return bool(re.search(r"\\" + command + r"(?:\[[^]]*\])?\s*\{\s*[^}\s]", tex))


def tex_checks(tex: str) -> list[dict[str, Any]]:
    document = re.search(r"\\begin\s*\{document\}", tex)
    body = tex[document.end():] if document else ""
    email_in_body = re.search(r"[^@\s{}]+@[^@\s{}]+\.[A-Za-z]{2,}", body)
    multi_column_patterns = {
        "multicol": r"\\begin\s*\{multicols?\}",
        "minipage": r"\\begin\s*\{minipage\}",
        "paracol": r"\\begin\s*\{paracol\}",
        "wrapfigure": r"\\begin\s*\{wrapfigure\}",
    }
    found_layouts = [name for name, pattern in multi_column_patterns.items() if re.search(pattern, tex)]
    nonempty_headers = [
        command for command in ("fancyhead", "fancyfoot", "lhead", "chead", "rhead", "lfoot", "cfoot", "rfoot")
        if _nonempty_command(tex, command)
    ]
    images = re.findall(r"\\(?:includegraphics|includepdf)\b", tex)

    return [
        result("LaTeX document body detected", bool(document)),
        result("ToUnicode mapping enabled", bool(re.search(r"\\pdfgentounicode\s*=\s*1", tex))),
        result(
            "contact email appears in document body",
            bool(email_in_body),
            email_in_body.group(0) if email_in_body else "not found after \\begin{document}",
        ),
        result(
            "single-column source structure",
            not found_layouts,
            "disallowed: " + ", ".join(found_layouts) if found_layouts else "clean",
        ),
        result(
            "no content in headers or footers",
            not nonempty_headers,
            "non-empty: " + ", ".join(nonempty_headers) if nonempty_headers else "clean",
        ),
        result("no embedded images", not images, f"{len(images)} image command(s)"),
    ]


def hard_checks_pass(checks: list[dict[str, Any]]) -> bool:
    return all(item["passed"] for item in checks if item["hard"])

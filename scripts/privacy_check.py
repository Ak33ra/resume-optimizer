#!/usr/bin/env python3
"""Scan staged content or every outgoing commit for likely private data."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import PurePosixPath


ZERO_SHA = "0" * 40
PROTECTED_PREFIXES = (
    "resumes/",
    "outputs/",
    "source_material/",
    "benchmarks/ground_truth/",
    "benchmarks/results/",
    "benchmarks/external/",
)
BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".ico", ".svg",
}
EMAIL = re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(rb"(?:\+?[0-9]{1,3}[ .-])?\(?[0-9]{3}\)?[ .-][0-9]{3}[ .-][0-9]{4}")


class ScanError(RuntimeError):
    pass


def git(*args: str, input_bytes: bytes | None = None) -> bytes:
    proc = subprocess.run(
        ["git", *args], input=input_bytes, capture_output=True, check=False
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode(errors="replace").strip()
        raise ScanError(f"git {' '.join(args)} failed: {detail}")
    return proc.stdout


def safe_template(path: str) -> bool:
    name = PurePosixPath(path).name
    return (
        name == "README.md"
        or name == ".gitkeep"
        or ".example." in name
    )


def protected_path(path: str) -> bool:
    return path.startswith(PROTECTED_PREFIXES) and not safe_template(path)


def pii_kinds(content: bytes) -> set[str]:
    if b"\x00" in content:
        return set()
    kinds = set()
    emails = [match.group().lower() for match in EMAIL.finditer(content)]
    real_emails = [
        value for value in emails
        if not value.endswith((b"@example.com", b"@example.org", b"@example.net"))
        and value != b"candidate@private.dev"  # historical test fixture
        and value.split(b"@", 1)[0] not in {b"you", b"git", b"user", b"name", b"first.last", b"noreply"}
    ]
    if real_emails:
        kinds.add("email")
    phones = [match.group() for match in PHONE.finditer(content)]

    def fictional_phone(value: bytes) -> bool:
        digits = re.sub(rb"\D", b"", value)
        if digits == b"1234567890":
            return True
        # NANP reserves 555-0100 through 555-0199 for fictional use.
        return len(digits) == 10 and digits[3:6] == b"555" and 100 <= int(digits[6:]) <= 199

    if any(not fictional_phone(value) for value in phones):
        kinds.add("phone")
    return kinds


def content_at(revision: str, path: str) -> bytes:
    return git("show", f"{revision}:{path}")


def changed_files(commit: str) -> list[str]:
    raw = git(
        "diff-tree", "--root", "--no-commit-id", "--name-only", "-r",
        "--diff-filter=ACMR", "-z", commit,
    )
    return [value.decode(errors="surrogateescape") for value in raw.split(b"\0") if value]


def outgoing_commits(local_sha: str, remote_sha: str) -> list[str]:
    if remote_sha == ZERO_SHA:
        raw = git("rev-list", local_sha)
    else:
        git("rev-parse", "--verify", f"{remote_sha}^{{commit}}")
        raw = git("rev-list", local_sha, f"^{remote_sha}")
    return raw.decode().split()


def scan_revision(revision: str, paths: list[str]) -> list[str]:
    problems = []
    for path in paths:
        if protected_path(path):
            problems.append(f"protected personal-data path: {path} ({revision[:12]})")
        if safe_template(path) or PurePosixPath(path).suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            kinds = pii_kinds(content_at(revision, path))
        except ScanError:
            continue
        for kind in sorted(kinds):
            problems.append(f"possible {kind} in {path} ({revision[:12]})")
    return problems


def scan_outgoing(local_sha: str, remote_sha: str) -> list[str]:
    problems = []
    for commit in outgoing_commits(local_sha, remote_sha):
        problems.extend(scan_revision(commit, changed_files(commit)))
    return sorted(set(problems))


def scan_staged() -> list[str]:
    raw = git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    paths = [value.decode(errors="surrogateescape") for value in raw.split(b"\0") if value]
    problems = []
    for path in paths:
        if protected_path(path):
            problems.append(f"protected personal-data path: {path} (staged)")
        if safe_template(path) or PurePosixPath(path).suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            content = git("show", f":{path}")
        except ScanError:
            continue
        for kind in sorted(pii_kinds(content)):
            problems.append(f"possible {kind} in {path} (staged)")
    return sorted(set(problems))


def main() -> None:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--staged", action="store_true")
    modes.add_argument("--outgoing", nargs=2, metavar=("LOCAL_SHA", "REMOTE_SHA"))
    args = parser.parse_args()
    try:
        problems = scan_staged() if args.staged else scan_outgoing(*args.outgoing)
    except ScanError as exc:
        print(f"privacy scan failed closed: {exc}", file=sys.stderr)
        raise SystemExit(2)
    if problems:
        for problem in problems:
            print(problem)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

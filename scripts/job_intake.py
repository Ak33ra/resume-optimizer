#!/usr/bin/env python3
"""Structured, reproducible ingestion of user-selected job postings."""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import html
import ipaddress
import json
import os
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
FAMILIES = (
    "big_tech",
    "quant_swe",
    "quant_research",
    "quant_trading",
    "research_lab",
    "startup",
    "other",
)
READY_STATUS = "ready"
MIN_DESCRIPTION_CHARS = 200
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
SLUG_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
PLACEHOLDER_RE = re.compile(r"\b(?:TODO|REPLACE_ME|PASTE_FULL_JOB_DESCRIPTION_HERE)\b")


class IntakeError(RuntimeError):
    pass


class FetchError(IntakeError):
    pass


@dataclass(frozen=True)
class JobTarget:
    slug: str
    url: str
    family: str = "other"
    priority: int = 0
    enabled: bool = True
    notes: str = ""
    company: str = ""
    role: str = ""


@dataclass(frozen=True)
class FetchedJob:
    company: str
    role: str
    description: str
    source_type: str
    source_url: str
    canonical_url: str
    location: str = ""
    external_id: str = ""
    published_at: str = ""
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValidationResult:
    path: Path
    metadata: dict[str, Any]
    body: str
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class HttpResponse:
    url: str
    content_type: str
    text: str


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256_string(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_text(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in value.splitlines()]
    output: list[str] = []
    blank = False
    for line in lines:
        if line:
            output.append(line)
            blank = False
        elif output and not blank:
            output.append("")
            blank = True
    return "\n".join(output).strip()


def humanize_token(value: str) -> str:
    return re.sub(r"[-_]", " ", value).strip().title()


def validate_remote_url(url: str) -> urllib.parse.SplitResult:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise IntakeError(f"job URL must be an absolute HTTPS URL: {url!r}")
    if parsed.username or parsed.password:
        raise IntakeError("job URL must not contain credentials")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".local"):
        raise IntakeError("job URL must not target localhost or a .local host")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address and not address.is_global:
        raise IntakeError("job URL must not target a private or reserved IP address")
    return parsed


def _parse_bool(value: str, *, row: int) -> bool:
    normalized = value.strip().lower()
    if normalized in ("", "true", "yes", "1"):
        return True
    if normalized in ("false", "no", "0"):
        return False
    raise IntakeError(f"row {row}: enabled must be true or false")


def load_targets(path: Path) -> list[JobTarget]:
    try:
        handle = path.open(newline="", encoding="utf-8-sig")
    except OSError as exc:
        raise IntakeError(f"cannot read target manifest {path}: {exc}") from exc
    with handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        missing = {"slug", "url"} - fields
        if missing:
            raise IntakeError(f"target manifest is missing columns: {', '.join(sorted(missing))}")
        targets: list[JobTarget] = []
        seen_slugs: set[str] = set()
        seen_urls: set[str] = set()
        for row_number, row in enumerate(reader, start=2):
            slug = (row.get("slug") or "").strip()
            url = (row.get("url") or "").strip()
            if not slug and not url:
                continue
            if not SLUG_RE.fullmatch(slug):
                raise IntakeError(f"row {row_number}: invalid slug {slug!r}")
            if slug in seen_slugs:
                raise IntakeError(f"row {row_number}: duplicate slug {slug!r}")
            validate_remote_url(url)
            normalized_url = urllib.parse.urlunsplit(
                urllib.parse.urlsplit(url)._replace(fragment="")
            )
            if normalized_url in seen_urls:
                raise IntakeError(f"row {row_number}: duplicate URL {url!r}")
            family = (row.get("family") or "other").strip() or "other"
            if family not in FAMILIES:
                raise IntakeError(f"row {row_number}: unsupported family {family!r}")
            priority_text = (row.get("priority") or "0").strip() or "0"
            try:
                priority = int(priority_text)
            except ValueError as exc:
                raise IntakeError(f"row {row_number}: priority must be an integer") from exc
            targets.append(
                JobTarget(
                    slug=slug,
                    url=url,
                    family=family,
                    priority=priority,
                    enabled=_parse_bool(row.get("enabled") or "", row=row_number),
                    notes=(row.get("notes") or "").strip(),
                    company=(row.get("company") or "").strip(),
                    role=(row.get("role") or "").strip(),
                )
            )
            seen_slugs.add(slug)
            seen_urls.add(normalized_url)
    return targets


def target_by_slug(targets: Iterable[JobTarget], slug: str) -> JobTarget:
    for target in targets:
        if target.slug == slug:
            if not target.enabled:
                raise IntakeError(f"target {slug!r} is disabled in job_targets.csv")
            return target
    raise IntakeError(f"target {slug!r} is not present in job_targets.csv")


class HttpClient:
    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def get(self, url: str, *, accept: str = "text/html,application/json") -> HttpResponse:
        validate_remote_url(url)
        request = urllib.request.Request(
            url,
            headers={
                "Accept": accept,
                "User-Agent": "resume-optimizer-job-intake/1.0 (+local user-selected fetch)",
            },
        )
        try:
            opener = urllib.request.build_opener(_SafeRedirectHandler())
            with opener.open(request, timeout=self.timeout) as response:
                final_url = response.geturl()
                validate_remote_url(final_url)
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise FetchError(f"response exceeded {MAX_RESPONSE_BYTES} bytes")
                content_type = response.headers.get_content_type()
                charset = response.headers.get_content_charset() or "utf-8"
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise FetchError(f"GET {url} failed: {exc}") from exc
        return HttpResponse(final_url, content_type, raw.decode(charset, errors="replace"))

    def get_json(self, url: str) -> tuple[Any, str]:
        response = self.get(url, accept="application/json")
        try:
            return json.loads(response.text), response.url
        except json.JSONDecodeError as exc:
            raise FetchError(f"GET {url} did not return valid JSON") from exc


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        validate_remote_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _VisibleTextParser(HTMLParser):
    BLOCK_TAGS = {
        "address", "article", "aside", "blockquote", "br", "dd", "div", "dl",
        "dt", "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr",
        "li", "main", "nav", "ol", "p", "pre", "section", "table", "td", "th",
        "tr", "ul",
    }
    SKIP_TAGS = {"script", "style", "noscript", "svg", "form", "button"}
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0
        self.hidden_depth = 0
        self.h1_parts: list[str] = []
        self.title_parts: list[str] = []
        self.in_h1 = False
        self.in_title = False
        self.json_ld: list[str] = []
        self._json_parts: list[str] | None = None
        self._frames: list[tuple[str, bool, bool]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        values = {key.lower(): value or "" for key, value in attrs}
        if tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self._json_parts = []
            self._frames.append((tag, False, False))
            return
        skipped = tag in self.SKIP_TAGS
        if skipped:
            self.skip_depth += 1
        hidden = "hidden" in values or values.get("aria-hidden", "").lower() == "true"
        style = values.get("style", "").replace(" ", "").lower()
        if hidden or "display:none" in style or "visibility:hidden" in style:
            self.hidden_depth += 1
            hidden = True
        else:
            hidden = False
        if tag not in self.VOID_TAGS:
            self._frames.append((tag, skipped, hidden))
        if skipped:
            return
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")
        if tag == "h1":
            self.in_h1 = True
        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "script" and self._json_parts is not None:
            self.json_ld.append("".join(self._json_parts))
            self._json_parts = None
            if self._frames and self._frames[-1][0] == tag:
                self._frames.pop()
            return
        frame_index = next(
            (index for index in range(len(self._frames) - 1, -1, -1) if self._frames[index][0] == tag),
            None,
        )
        removed = self._frames[frame_index:] if frame_index is not None else []
        if frame_index is not None:
            del self._frames[frame_index:]
        self.skip_depth = max(0, self.skip_depth - sum(1 for _, skipped, _ in removed if skipped))
        self.hidden_depth = max(0, self.hidden_depth - sum(1 for _, _, hidden in removed if hidden))
        if any(skipped for _, skipped, _ in removed):
            return
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")
        if tag == "h1":
            self.in_h1 = False
        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self._json_parts is not None:
            self._json_parts.append(data)
            return
        if self.skip_depth or self.hidden_depth:
            return
        self.parts.append(data)
        if self.in_h1:
            self.h1_parts.append(data)
        if self.in_title:
            self.title_parts.append(data)


def html_to_text(value: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(html.unescape(html.unescape(value)))
    return normalize_text("".join(parser.parts))


def _json_ld_objects(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        graph = value.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                yield from _json_ld_objects(item)
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _json_ld_objects(item)


def _is_job_posting(value: dict[str, Any]) -> bool:
    kind = value.get("@type")
    return kind == "JobPosting" or isinstance(kind, list) and "JobPosting" in kind


def _location_from_json_ld(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(filter(None, (_location_from_json_ld(item) for item in value)))
    if not isinstance(value, dict):
        return str(value or "")
    address = value.get("address", value)
    if isinstance(address, str):
        return address
    if not isinstance(address, dict):
        return ""
    return ", ".join(
        str(address[key]).strip()
        for key in ("addressLocality", "addressRegion", "addressCountry")
        if address.get(key)
    )


def _company_from_json_ld(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or "").strip()
    return str(value or "").strip()


def extract_generic(response: HttpResponse, target: JobTarget) -> FetchedJob:
    parser = _VisibleTextParser()
    parser.feed(response.text)
    for raw in parser.json_ld:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for value in _json_ld_objects(payload):
            if not _is_job_posting(value):
                continue
            description = html_to_text(str(value.get("description") or ""))
            role = str(value.get("title") or target.role).strip()
            company = _company_from_json_ld(value.get("hiringOrganization")) or target.company
            canonical = str(value.get("url") or response.url)
            return FetchedJob(
                company=company or humanize_token(urllib.parse.urlsplit(response.url).hostname or "company"),
                role=role,
                description=description,
                source_type="json_ld",
                source_url=target.url,
                canonical_url=canonical,
                location=_location_from_json_ld(value.get("jobLocation")),
                external_id=str(value.get("identifier", {}).get("value", ""))
                if isinstance(value.get("identifier"), dict) else "",
                published_at=str(value.get("datePosted") or ""),
            )
    visible = normalize_text("".join(parser.parts))
    role = target.role or normalize_text("".join(parser.h1_parts))
    if not role:
        role = normalize_text("".join(parser.title_parts)).split("|")[0].strip()
    host = urllib.parse.urlsplit(response.url).hostname or "company"
    return FetchedJob(
        company=target.company or humanize_token(host.split(".")[0]),
        role=role,
        description=visible,
        source_type="generic_html",
        source_url=target.url,
        canonical_url=response.url,
        warnings=("generic HTML extraction should be reviewed for completeness",),
    )


class SourceAdapter:
    name = "base"

    def match(self, parsed: urllib.parse.SplitResult) -> bool:
        raise NotImplementedError

    def fetch(self, target: JobTarget, client: HttpClient) -> FetchedJob:
        raise NotImplementedError


class GreenhouseAdapter(SourceAdapter):
    name = "greenhouse"
    HOSTS = {"boards.greenhouse.io", "job-boards.greenhouse.io", "boards-api.greenhouse.io"}

    def match(self, parsed: urllib.parse.SplitResult) -> bool:
        return (parsed.hostname or "").lower() in self.HOSTS

    def fetch(self, target: JobTarget, client: HttpClient) -> FetchedJob:
        parsed = urllib.parse.urlsplit(target.url)
        parts = [urllib.parse.unquote(part) for part in parsed.path.split("/") if part]
        if parsed.hostname == "boards-api.greenhouse.io" and len(parts) >= 5:
            board, job_id = parts[2], parts[4]
        elif "jobs" in parts:
            index = parts.index("jobs")
            if index < 1 or index + 1 >= len(parts):
                raise FetchError("could not identify Greenhouse board and job ID")
            board, job_id = parts[index - 1], parts[index + 1]
        else:
            raise FetchError("could not identify Greenhouse board and job ID")
        api = f"https://boards-api.greenhouse.io/v1/boards/{urllib.parse.quote(board)}/jobs/{urllib.parse.quote(job_id)}"
        payload, _ = client.get_json(api)
        if not isinstance(payload, dict):
            raise FetchError("Greenhouse job response is not an object")
        company = target.company
        try:
            board_payload, _ = client.get_json(
                f"https://boards-api.greenhouse.io/v1/boards/{urllib.parse.quote(board)}"
            )
            if isinstance(board_payload, dict):
                company = company or str(board_payload.get("name") or "").strip()
        except FetchError:
            pass
        location = payload.get("location")
        return FetchedJob(
            company=company or humanize_token(board),
            role=str(payload.get("title") or target.role).strip(),
            description=html_to_text(str(payload.get("content") or "")),
            source_type=self.name,
            source_url=target.url,
            canonical_url=str(payload.get("absolute_url") or target.url),
            location=str(location.get("name") or "").strip() if isinstance(location, dict) else "",
            external_id=str(payload.get("id") or job_id),
            published_at=str(payload.get("updated_at") or ""),
        )


class LeverAdapter(SourceAdapter):
    name = "lever"
    HOSTS = {"jobs.lever.co", "jobs.eu.lever.co", "api.lever.co", "api.eu.lever.co"}

    def match(self, parsed: urllib.parse.SplitResult) -> bool:
        return (parsed.hostname or "").lower() in self.HOSTS

    def fetch(self, target: JobTarget, client: HttpClient) -> FetchedJob:
        parsed = urllib.parse.urlsplit(target.url)
        parts = [urllib.parse.unquote(part) for part in parsed.path.split("/") if part]
        if "postings" in parts:
            index = parts.index("postings")
            parts = parts[index + 1:]
        if len(parts) < 2:
            raise FetchError("could not identify Lever site and posting ID")
        site, posting_id = parts[0], parts[1]
        eu = ".eu." in (parsed.hostname or "")
        api_host = "api.eu.lever.co" if eu else "api.lever.co"
        api = f"https://{api_host}/v0/postings/{urllib.parse.quote(site)}/{urllib.parse.quote(posting_id)}?mode=json"
        payload, _ = client.get_json(api)
        if not isinstance(payload, dict):
            raise FetchError("Lever job response is not an object")
        categories = payload.get("categories")
        location = str(categories.get("location") or "") if isinstance(categories, dict) else ""
        description = payload.get("descriptionPlain") or payload.get("description") or ""
        return FetchedJob(
            company=target.company or humanize_token(site),
            role=str(payload.get("text") or target.role).strip(),
            description=html_to_text(str(description)),
            source_type=self.name,
            source_url=target.url,
            canonical_url=str(payload.get("hostedUrl") or target.url),
            location=location.strip(),
            external_id=str(payload.get("id") or posting_id),
        )


class AshbyAdapter(SourceAdapter):
    name = "ashby"

    def match(self, parsed: urllib.parse.SplitResult) -> bool:
        return (parsed.hostname or "").lower() in {"jobs.ashbyhq.com", "api.ashbyhq.com"}

    def fetch(self, target: JobTarget, client: HttpClient) -> FetchedJob:
        parsed = urllib.parse.urlsplit(target.url)
        parts = [urllib.parse.unquote(part) for part in parsed.path.split("/") if part]
        if parsed.hostname == "api.ashbyhq.com" and "job-board" in parts:
            parts = parts[parts.index("job-board") + 1:]
        if not parts:
            raise FetchError("could not identify Ashby job board")
        board = parts[0]
        requested_tail = parts[-1].lower()
        api = f"https://api.ashbyhq.com/posting-api/job-board/{urllib.parse.quote(board)}?includeCompensation=true"
        payload, _ = client.get_json(api)
        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            raise FetchError("Ashby job-board response has no jobs list")
        matches = []
        for value in jobs:
            if not isinstance(value, dict):
                continue
            job_url = str(value.get("jobUrl") or "")
            tail = urllib.parse.urlsplit(job_url).path.rstrip("/").split("/")[-1].lower()
            if len(parts) == 1 or tail == requested_tail:
                matches.append(value)
        if len(matches) != 1:
            raise FetchError(f"Ashby posting URL matched {len(matches)} jobs; expected exactly one")
        value = matches[0]
        return FetchedJob(
            company=target.company or humanize_token(board),
            role=str(value.get("title") or target.role).strip(),
            description=html_to_text(str(value.get("descriptionPlain") or value.get("descriptionHtml") or "")),
            source_type=self.name,
            source_url=target.url,
            canonical_url=str(value.get("jobUrl") or target.url),
            location=str(value.get("location") or "").strip(),
            external_id=urllib.parse.urlsplit(str(value.get("jobUrl") or target.url)).path.rstrip("/").split("/")[-1],
            published_at=str(value.get("publishedAt") or ""),
        )


ADAPTERS: tuple[SourceAdapter, ...] = (GreenhouseAdapter(), LeverAdapter(), AshbyAdapter())


def _validate_fetched(job: FetchedJob) -> None:
    problems = []
    if not job.company.strip():
        problems.append("company is missing")
    if not job.role.strip():
        problems.append("role title is missing")
    if len(normalize_text(job.description)) < MIN_DESCRIPTION_CHARS:
        problems.append(f"description is shorter than {MIN_DESCRIPTION_CHARS} characters")
    if problems:
        raise FetchError("incomplete extraction: " + "; ".join(problems))


def fetch_target(target: JobTarget, client: HttpClient | None = None) -> FetchedJob:
    client = client or HttpClient()
    parsed = validate_remote_url(target.url)
    adapter = next((value for value in ADAPTERS if value.match(parsed)), None)
    errors: list[str] = []
    if adapter:
        try:
            job = adapter.fetch(target, client)
            _validate_fetched(job)
            return job
        except FetchError as exc:
            errors.append(f"{adapter.name}: {exc}")
    try:
        job = extract_generic(client.get(target.url), target)
        _validate_fetched(job)
        return job
    except FetchError as exc:
        errors.append(f"generic: {exc}")
    raise FetchError("all extraction methods failed: " + " | ".join(errors))


def _front_value(value: str) -> Any:
    value = value.strip()
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def parse_document(text: str) -> tuple[dict[str, Any], str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.startswith("---\n"):
        raise IntakeError("job description must begin with YAML front matter")
    end = normalized.find("\n---\n", 4)
    if end < 0:
        raise IntakeError("job description front matter is not terminated")
    metadata: dict[str, Any] = {}
    for number, line in enumerate(normalized[4:end].splitlines(), start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise IntakeError(f"invalid front-matter line {number}")
        key, value = line.split(":", 1)
        key = key.strip()
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise IntakeError(f"invalid front-matter key on line {number}")
        if key in metadata:
            raise IntakeError(f"duplicate front-matter key {key!r}")
        metadata[key] = _front_value(value)
    return metadata, normalize_text(normalized[end + 5:])


def _front_line(key: str, value: Any) -> str:
    if isinstance(value, (int, float)):
        rendered = str(value)
    else:
        rendered = json.dumps(str(value), ensure_ascii=True)
    return f"{key}: {rendered}"


FRONT_ORDER = (
    "schema_version", "slug", "company", "role", "family", "seniority", "location",
    "source_type", "source_url", "canonical_url", "external_id", "published_at",
    "retrieved_at", "content_sha256", "status",
)


def render_document(metadata: dict[str, Any], body: str) -> str:
    lines = ["---"]
    seen = set()
    for key in FRONT_ORDER:
        if key in metadata and metadata[key] not in (None, ""):
            lines.append(_front_line(key, metadata[key]))
            seen.add(key)
    for key in sorted(set(metadata) - seen):
        if metadata[key] not in (None, ""):
            lines.append(_front_line(key, metadata[key]))
    lines.extend(["---", "", normalize_text(body), ""])
    return "\n".join(lines)


def document_for(target: JobTarget, job: FetchedJob) -> str:
    description = normalize_text(job.description)
    body_parts = [f"# {job.role}", "", f"## Company\n{job.company}"]
    if job.location:
        body_parts.extend(["", f"## Location\n{job.location}"])
    body_parts.extend(["", "## Job Description", description])
    body = normalize_text("\n".join(body_parts))
    metadata: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "slug": target.slug,
        "company": job.company,
        "role": job.role,
        "family": target.family,
        "location": job.location,
        "source_type": job.source_type,
        "source_url": job.source_url,
        "canonical_url": job.canonical_url,
        "external_id": job.external_id,
        "published_at": job.published_at,
        "retrieved_at": utc_now(),
        "content_sha256": sha256_string(body),
        "status": READY_STATUS,
    }
    return render_document(metadata, body)


def validate_document(path: Path, expected_slug: str | None = None) -> ValidationResult:
    try:
        metadata, body = parse_document(path.read_text(encoding="utf-8"))
    except (OSError, IntakeError) as exc:
        return ValidationResult(path, {}, "", (str(exc),))
    errors: list[str] = []
    warnings: list[str] = []
    required = {
        "schema_version", "slug", "company", "role", "family", "source_type",
        "retrieved_at", "content_sha256", "status",
    }
    missing = sorted(key for key in required if metadata.get(key) in (None, ""))
    if missing:
        errors.append("missing metadata: " + ", ".join(missing))
    if metadata.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    slug = metadata.get("slug")
    if not isinstance(slug, str) or not SLUG_RE.fullmatch(slug):
        errors.append("slug is invalid")
    if expected_slug and slug != expected_slug:
        errors.append(f"slug {slug!r} does not match expected {expected_slug!r}")
    if metadata.get("family") not in FAMILIES:
        errors.append(f"family must be one of: {', '.join(FAMILIES)}")
    if metadata.get("status") != READY_STATUS:
        errors.append("status must be ready")
    for key in ("company", "role"):
        if PLACEHOLDER_RE.search(str(metadata.get(key) or "")):
            errors.append(f"{key} still contains a template placeholder")
    source_type = metadata.get("source_type")
    if source_type != "manual" and not metadata.get("source_url"):
        errors.append("fetched descriptions require source_url")
    if len(body) < MIN_DESCRIPTION_CHARS:
        errors.append(f"description body is shorter than {MIN_DESCRIPTION_CHARS} characters")
    if PLACEHOLDER_RE.search(body):
        errors.append("description still contains template placeholders")
    actual_hash = sha256_string(body)
    if metadata.get("content_sha256") != actual_hash:
        errors.append("content_sha256 does not match the normalized description body")
    if "## Job Description" not in body:
        errors.append("description body is missing the '## Job Description' section")
    lowered = body.lower()
    if not any(term in lowered for term in ("qualification", "requirement", "experience", "responsibilit")):
        warnings.append("description may be missing responsibilities or qualifications")
    return ValidationResult(path, metadata, body, tuple(errors), tuple(warnings))


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def manual_stub(target: JobTarget) -> str:
    body = normalize_text(
        f"""# {target.role or 'REPLACE_ME'}

## Company
{target.company or 'REPLACE_ME'}

## Job Description
PASTE_FULL_JOB_DESCRIPTION_HERE

Include responsibilities, required qualifications, preferred qualifications,
location, and compensation where the posting provides them.
"""
    )
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "slug": target.slug,
        "company": target.company or "REPLACE_ME",
        "role": target.role or "REPLACE_ME",
        "family": target.family,
        "source_type": "manual",
        "source_url": target.url,
        "retrieved_at": utc_now(),
        "content_sha256": sha256_string(body),
        "status": "needs_manual_input",
    }
    return render_document(metadata, body)


def finalize_manual(path: Path, expected_slug: str) -> ValidationResult:
    try:
        metadata, body = parse_document(path.read_text(encoding="utf-8"))
    except (OSError, IntakeError) as exc:
        raise IntakeError(f"cannot finalize {path}: {exc}") from exc
    metadata["schema_version"] = SCHEMA_VERSION
    metadata["slug"] = expected_slug
    metadata["source_type"] = "manual"
    metadata["retrieved_at"] = utc_now()
    metadata["content_sha256"] = sha256_string(body)
    metadata["status"] = READY_STATUS
    atomic_write(path, render_document(metadata, body))
    result = validate_document(path, expected_slug)
    if not result.valid:
        metadata["status"] = "needs_manual_input"
        atomic_write(path, render_document(metadata, body))
        raise IntakeError("manual description is incomplete: " + " | ".join(result.errors))
    return result

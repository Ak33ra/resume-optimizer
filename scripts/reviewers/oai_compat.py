#!/usr/bin/env python3
"""Blind-panel reviewer backed by any OpenAI-compatible chat-completions API.

Reads the reviewer prompt from stdin and writes the model's text response to
stdout, matching the CLI reviewer contract in ``panel_review.py`` (which then
extracts the JSON verdict from stdout). Every provider detail comes from the
environment, so no endpoint, key, or model id is hardcoded and this file is safe
to commit to a public repo.

Environment:
  PANEL_OSS_BASE_URL    e.g. https://gateway.example/v1      (required)
  PANEL_OSS_API_KEY     bearer token                          (required)
  PANEL_OSS_MODEL       model id, e.g. glm-5.2                (required)
  PANEL_OSS_TIMEOUT     per-request seconds (default 210; keep < panel --timeout)
  PANEL_OSS_MAX_TOKENS  max completion tokens (only sent if set)
  PANEL_OSS_TEMPERATURE sampling temperature (only sent if set)

Exit codes: 2 = misconfiguration (bad/absent env or empty prompt); 1 = request
or response failure. Both are reported to the panel as a reviewer failure.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def _fail(msg: str, code: int = 1):
    print(f"oai_compat: {msg}", file=sys.stderr)
    raise SystemExit(code)


def main() -> None:
    base_url = os.environ.get("PANEL_OSS_BASE_URL", "").strip()
    api_key = os.environ.get("PANEL_OSS_API_KEY", "").strip()
    model = os.environ.get("PANEL_OSS_MODEL", "").strip()
    missing = [
        name
        for name, val in (
            ("PANEL_OSS_BASE_URL", base_url),
            ("PANEL_OSS_API_KEY", api_key),
            ("PANEL_OSS_MODEL", model),
        )
        if not val
    ]
    if missing:
        _fail(f"unset env var(s): {', '.join(missing)}", code=2)

    try:
        timeout = float(os.environ.get("PANEL_OSS_TIMEOUT", "210"))
    except ValueError as exc:
        _fail(f"bad PANEL_OSS_TIMEOUT ({exc})", code=2)

    prompt = sys.stdin.read()
    if not prompt.strip():
        _fail("empty prompt on stdin", code=2)

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    # Only send tuning params when explicitly set — some models (e.g. reasoning
    # variants) reject a non-default temperature or an unsupported token field.
    if os.environ.get("PANEL_OSS_TEMPERATURE"):
        try:
            payload["temperature"] = float(os.environ["PANEL_OSS_TEMPERATURE"])
        except ValueError as exc:
            _fail(f"bad PANEL_OSS_TEMPERATURE ({exc})", code=2)
    if os.environ.get("PANEL_OSS_MAX_TOKENS"):
        try:
            payload["max_tokens"] = int(os.environ["PANEL_OSS_MAX_TOKENS"])
        except ValueError as exc:
            _fail(f"bad PANEL_OSS_MAX_TOKENS ({exc})", code=2)

    endpoint = base_url.rstrip("/") + "/chat/completions"
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # Some gateways sit behind Cloudflare, which 403s (error 1010) the
            # default urllib User-Agent as a bot even on authenticated API calls.
            # Send a browser-like UA; override with PANEL_OSS_USER_AGENT if needed.
            "User-Agent": os.environ.get(
                "PANEL_OSS_USER_AGENT",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            ),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        _fail(f"HTTP {exc.code} from {endpoint}: {detail}")
    except Exception as exc:  # URLError, socket timeout, etc.
        _fail(f"request to {endpoint} failed ({exc})")

    try:
        data = json.loads(raw)
        message = data["choices"][0]["message"]
        content = message.get("content") or message.get("reasoning_content") or ""
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        _fail(f"unexpected response shape ({exc}); first 300 chars: {raw[:300]!r}")

    if not content.strip():
        _fail("model returned empty content")
    sys.stdout.write(content)


if __name__ == "__main__":
    main()

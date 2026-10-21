"""Minimal GitHub REST client on the standard library (no dependencies)."""

from __future__ import annotations

import json
import math
import os
import socket
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com"
ATTEMPTS = 3
BACKOFF = (2, 4)  # seconds before attempt 2 and 3
RETRY_AFTER_MAX = 30


def _retry_delay(e: urllib.error.HTTPError | None, attempt: int) -> float:
    """Seconds to wait before the next attempt: Retry-After if the server sent it (capped)."""
    if e is not None and e.headers is not None:
        value = e.headers.get("Retry-After")
        if value is not None:
            try:
                seconds = float(value)
            except ValueError:
                seconds = float("nan")  # HTTP-date form: use the backoff
            if not math.isnan(seconds):
                return min(max(seconds, 0.0), RETRY_AFTER_MAX)
    return BACKOFF[attempt - 1]


def _transient(e: urllib.error.HTTPError) -> bool:
    """5xx, 429 and 403 with an exhausted rate limit are worth another attempt."""
    if e.code >= 500 or e.code == 429:
        return True
    remaining = e.headers.get("X-RateLimit-Remaining") if e.headers is not None else None
    return e.code == 403 and remaining == "0"


def get(path: str, raw: bool = False, allow_404: bool = False, soft: bool = False):
    """GET an API path. Exits on errors so a broken run never publishes partial data.

    raw=True returns the body as text (used for README). allow_404=True returns None on 404.
    soft=True returns None (with a warning) instead of exiting on an HTTP error, for lookups
    whose failure must not stop the run, e.g. a known repository blocked with 403 or 451.
    Server errors, rate limits and network failures are retried up to ATTEMPTS times in total.
    """
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github.raw+json" if raw else "application/vnd.github+json",
        "User-Agent": "asofwar-site",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    for attempt in range(1, ATTEMPTS + 1):
        last = attempt == ATTEMPTS
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if allow_404 and e.code == 404:
                return None
            if last or not _transient(e):
                if soft:
                    print(f"warning: GitHub API {path}: HTTP {e.code} {e.reason}, skipped", file=sys.stderr)
                    return None
                sys.exit(f"GitHub API {path}: HTTP {e.code} {e.reason}")
            delay = _retry_delay(e, attempt)
            reason = f"HTTP {e.code} {e.reason}"
        # socket.timeout is TimeoutError only since Python 3.10.
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as e:  # noqa: UP041
            reason = e.reason if isinstance(e, urllib.error.URLError) else (str(e) or type(e).__name__)
            if last:
                sys.exit(f"GitHub API {path}: {reason}")
            delay = _retry_delay(None, attempt)
        else:
            return body if raw else json.loads(body)
        print(f"retry {attempt + 1}/{ATTEMPTS} in {delay:g} s, GitHub API {path}: {reason}",
              file=sys.stderr)
        time.sleep(delay)
    raise AssertionError("unreachable")

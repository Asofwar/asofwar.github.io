"""Minimal GitHub REST client on the standard library (no dependencies)."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"


def get(path: str, raw: bool = False, allow_404: bool = False):
    """GET an API path. Exits on errors so a broken run never publishes partial data.

    raw=True returns the body as text (used for README). allow_404=True returns None on 404.
    """
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github.raw+json" if raw else "application/vnd.github+json",
        "User-Agent": "asofwar-site",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if allow_404 and e.code == 404:
            return None
        sys.exit(f"GitHub API {path}: HTTP {e.code} {e.reason}")
    except urllib.error.URLError as e:
        sys.exit(f"GitHub API {path}: {e.reason}")
    return body if raw else json.loads(body)

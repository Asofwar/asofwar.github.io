"""Snapshot new public repositories of the owner into data/candidates.json.

Runs in GitHub Actions (the cloud agent cannot list the owner's repositories itself).
The agent then reads the snapshot and decides which candidates become project cards.

Usage:
    python scripts/discover.py

The file is rewritten only when candidates or status hints change, so a quiet week
produces no commit.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ghapi

ROOT = Path(__file__).resolve().parent.parent
OWNER = "Asofwar"
ACTIVE_DAYS = 120
README_LIMIT = 4000
OUT = ROOT / "data" / "candidates.json"


def repo_of(url: str | None) -> str | None:
    m = re.match(r"https://github\.com/([^/]+/[^/#?]+)", url or "")
    return m.group(1).lower() if m else None


def known_repos(data: dict) -> set[str]:
    known = {f"{OWNER}/{OWNER}.github.io".lower()}
    for p in data["projects"]:
        for value in (p.get("releases"), repo_of(p.get("source")),
                      repo_of((p.get("link") or {}).get("url"))):
            if value:
                known.add(value.lower())
    for item in data.get("ignore", []):
        known.add(item["repo"].lower())
    return known


def list_repos() -> list[dict]:
    repos, page = [], 1
    while True:
        batch = ghapi.get(f"/users/{OWNER}/repos?per_page=100&type=owner&sort=pushed&page={page}")
        if not batch:
            return repos
        repos.extend(batch)
        page += 1


def releases_of(full_name: str, limit: int = 3) -> list[dict]:
    items = ghapi.get(f"/repos/{full_name}/releases?per_page=10")
    out = [{"version": r["tag_name"], "date": r["published_at"][:10], "pre": bool(r.get("prerelease"))}
           for r in items if not r.get("draft") and r.get("published_at")]
    return out[:limit]


def is_stable_1x(version: str) -> bool:
    m = re.match(r"v?(\d+)\.", version)
    return bool(m and int(m.group(1)) >= 1)


def main() -> None:
    data = json.loads((ROOT / "data" / "projects.json").read_text(encoding="utf-8"))
    known = known_repos(data)
    cutoff = datetime.now(timezone.utc) - timedelta(days=ACTIVE_DAYS)

    candidates = []
    for r in list_repos():
        pushed = datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00"))
        if r["fork"] or r["archived"] or r["private"] or pushed < cutoff:
            continue
        if r["full_name"].lower() in known:
            continue
        readme = ghapi.get(f"/repos/{r['full_name']}/readme", raw=True, allow_404=True) or ""
        candidates.append({
            "repo": r["full_name"],
            "url": r["html_url"],
            "description": r.get("description") or "",
            "homepage": r.get("homepage") or "",
            "language": r.get("language") or "",
            "topics": r.get("topics") or [],
            "pushed_at": r["pushed_at"][:10],
            "releases": releases_of(r["full_name"]),
            "readme_excerpt": readme[:README_LIMIT],
        })

    # Status hints: a project in development whose latest stable release reached 1.0.
    hints = []
    for p in data["projects"]:
        if p["status"] != "dev" or not p.get("releases"):
            continue
        stable = [x for x in releases_of(p["releases"], limit=10) if not x["pre"]]
        if stable and is_stable_1x(stable[0]["version"]):
            hints.append({"id": p["id"], "suggest_status": "live", "version": stable[0]["version"]})

    payload = {"candidates": candidates, "status_hints": hints}
    if OUT.exists():
        previous = json.loads(OUT.read_text(encoding="utf-8"))
        if {k: previous.get(k) for k in payload} == payload:
            print(f"no changes: {len(candidates)} candidates, {len(hints)} status hints")
            return
    document = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **payload}
    OUT.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.name}: {len(candidates)} candidates, {len(hints)} status hints")


if __name__ == "__main__":
    main()

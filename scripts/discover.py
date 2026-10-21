"""Snapshot new public repositories of the owner into data/candidates.json.

Runs in GitHub Actions (the cloud agent cannot list the owner's repositories itself).
The agent then reads the snapshot and decides which candidates become project cards.
Forks are taken only if they have an own release within ACTIVE_DAYS; their fork_of names
the upstream. Repositories already on the site are also matched by their current name,
so a renamed repository does not come back as a new candidate.

Usage:
    python scripts/discover.py

An empty snapshot (no candidates, no status hints) is rewritten only when it changes,
so a quiet week produces no commit. Even without changes it is rewritten (new generated_at)
at least every KEEPALIVE_DAYS, so GitHub does not disable the scheduled workflows
after 60 days without repository activity. A snapshot with candidates or status hints is
rewritten on every run: its generated_at then tells the agent whether the latest weekly
run wrote it or a missed run left an old one behind.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ghapi

ROOT = Path(__file__).resolve().parent.parent
OWNER = "Asofwar"
ACTIVE_DAYS = 120
README_LIMIT = 4000
FORK_README_LIMIT = 1000  # a fork's README is mostly upstream text: less foreign text for the agent
KEEPALIVE_DAYS = 28
OUT = ROOT / "data" / "candidates.json"


def repo_of(url: object) -> str | None:
    m = re.match(r"https://github\.com/([^/]+/[^/#?]+)", url if isinstance(url, str) else "")
    return m.group(1).lower() if m else None


def known_repos(data: dict) -> set[str]:
    """Repositories already on the site or ignored. Bad entries are skipped here;
    build.py rejects them when the agent validates its change."""
    known = {f"{OWNER}/{OWNER}.github.io".lower()}
    for p in data.get("projects") or []:
        if not isinstance(p, dict):
            continue
        link = p.get("link")
        releases = p.get("releases")
        for value in (releases if isinstance(releases, str) and releases else None,
                      repo_of(p.get("source")),
                      repo_of(link.get("url") if isinstance(link, dict) else None)):
            if value:
                known.add(value.lower())
    for item in data.get("ignore") or []:
        repo = item.get("repo") if isinstance(item, dict) else None
        if isinstance(repo, str) and repo:
            known.add(repo.lower())
        else:
            print(f"warning: skipped ignore entry {item!r}", file=sys.stderr)
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
    site = f"{OWNER}/{OWNER}.github.io".lower()
    # Canonical names: a renamed repository is listed under its new name, while the data may
    # still hold the old one (GitHub keeps a 301 redirect, urllib follows it). The old name
    # stays in known too. A deleted or private repository answers 404 and is skipped.
    for name in sorted(known - {site}):
        meta = ghapi.get(f"/repos/{name}", allow_404=True)
        if meta is not None:
            known.add(meta["full_name"].lower())
    cutoff = datetime.now(timezone.utc) - timedelta(days=ACTIVE_DAYS)

    candidates = []
    for r in list_repos():
        pushed = datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00"))
        if r["archived"] or r["private"] or pushed < cutoff:
            continue
        if r["full_name"].lower() in known:
            continue
        rels = releases_of(r["full_name"])
        fork_of = None
        homepage = r.get("homepage") or ""
        if r["fork"]:
            # Forks only with an own release within ACTIVE_DAYS (mirrors of upstream have none).
            if not rels or datetime.fromisoformat(rels[0]["date"]).replace(tzinfo=timezone.utc) < cutoff:
                continue
            parent = ghapi.get(f"/repos/{r['full_name']}")["parent"]
            fork_of = parent["full_name"]
            if homepage == (parent.get("homepage") or ""):
                homepage = ""  # inherited upstream site, not the fork's own
        readme = ghapi.get(f"/repos/{r['full_name']}/readme", raw=True, allow_404=True) or ""
        candidates.append({
            "repo": r["full_name"],
            "url": r["html_url"],
            "description": r.get("description") or "",
            "homepage": homepage,
            "language": r.get("language") or "",
            "topics": r.get("topics") or [],
            "pushed_at": r["pushed_at"][:10],
            "releases": rels,
            "readme_excerpt": readme[:FORK_README_LIMIT if fork_of else README_LIMIT],
            "fork_of": fork_of,
        })

    # Status hints: a project in development whose latest stable release reached 1.0.
    hints = []
    for p in data.get("projects") or []:
        if not isinstance(p, dict) or p.get("status") != "dev" or not isinstance(p.get("releases"), str):
            continue
        stable = [x for x in releases_of(p["releases"], limit=10) if not x["pre"]]
        if stable and is_stable_1x(stable[0]["version"]):
            hints.append({"id": p["id"], "suggest_status": "live", "version": stable[0]["version"]})

    payload = {"candidates": candidates, "status_hints": hints}
    if OUT.exists():
        previous = json.loads(OUT.read_text(encoding="utf-8"))
        # Age in calendar days (UTC), so the weekly run on day 28 rewrites the file even
        # when it starts a few minutes earlier than the run that wrote it.
        try:
            generated = datetime.fromisoformat(str(previous.get("generated_at") or "").replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc).date() - generated.astimezone(timezone.utc).date()).days
        except (ValueError, OverflowError):
            age_days = KEEPALIVE_DAYS
        # Candidates or hints wait for the agent: rewrite them every run, so a fresh
        # generated_at shows the agent that this week's run produced them.
        pending = bool(candidates or hints)
        if not pending and {k: previous.get(k) for k in payload} == payload and age_days < KEEPALIVE_DAYS:
            print(f"no changes: {len(candidates)} candidates, {len(hints)} status hints")
            return
    document = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **payload}
    OUT.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.name}: {len(candidates)} candidates, {len(hints)} status hints")


if __name__ == "__main__":
    main()

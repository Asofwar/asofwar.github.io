"""Build the static site from data/projects.json and template.html.

Usage:
    python scripts/build.py            # fetch releases from GitHub, write _site/
    python scripts/build.py --offline  # skip GitHub API (local preview without releases)

GITHUB_TOKEN, when set, is used for the GitHub API (higher rate limit).
Any API or data error fails the build, so a broken run never replaces the live site.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import random
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ghapi

ROOT = Path(__file__).resolve().parent.parent
MSK = timezone(timedelta(hours=3))
NEW_DAYS = 14
LOG_LIMIT = 10
TICKER_LIMIT = 8

STATUS = {
    "live": "Работает",
    "dev": "В разработке",
    "research": "Исследование",
}
REQUIRED = ("id", "title", "kind", "summary", "stack", "platforms", "status")


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def fmt_date(dt: datetime) -> str:
    return dt.astimezone(MSK).strftime("%d.%m.%Y")


def time_tag(dt: datetime) -> str:
    """<time> whose machine date is the same Moscow day as the visible one."""
    return f'<time datetime="{dt.astimezone(MSK).date().isoformat()}">{fmt_date(dt)}</time>'


def version_of(tag: str, repo: str = "") -> str:
    """Release tag as shown on the site: 'flint2-openwrt-v25.12.5-f0a60eee' -> '25.12.5-f0a60eee'."""
    name = repo.rsplit("/", 1)[-1]
    if name and tag.lower().startswith(name.lower() + "-") and len(tag) > len(name) + 1:
        tag = tag[len(name) + 1:]
    return tag[1:] if tag[:1] in ("v", "V") and tag[1:2].isdigit() else tag


# Own repository in a card's 'source', used for releases when 'releases' is not set.
OWN_REPO = re.compile(r"^https://github\.com/(Asofwar/[A-Za-z0-9._-]+?)(?:\.git)?(?:[/#?]|$)", re.IGNORECASE)


def releases_repo(p: dict) -> tuple[str | None, bool]:
    """Repository to read releases from and whether a 404 there is acceptable.

    'releases' as a string is used as is (404 fails the build); false turns releases off;
    null or a missing key falls back to the card's own GitHub 'source' (404 tolerated).
    """
    value = p.get("releases")
    if isinstance(value, str) and value:
        return value, False
    if value is False:
        return None, False
    if value is None:
        m = OWN_REPO.match(p.get("source") or "")
        if m:
            return m.group(1), True
    return None, False


# ---------- data ----------

def load_projects() -> list[dict]:
    data = json.loads((ROOT / "data" / "projects.json").read_text(encoding="utf-8"))
    projects = data.get("projects")
    if not isinstance(projects, list) or not projects:
        sys.exit("data/projects.json: 'projects' must be a non-empty list")
    seen: set[str] = set()
    for i, p in enumerate(projects):
        where = f"data/projects.json: projects[{i}]"
        for key in REQUIRED:
            if key not in p or p[key] in (None, "", []):
                sys.exit(f"{where}: missing '{key}'")
        if p["status"] not in STATUS:
            sys.exit(f"{where}: status must be one of {', '.join(STATUS)}")
        if not isinstance(p["stack"], list) or not isinstance(p["platforms"], list):
            sys.exit(f"{where}: 'stack' and 'platforms' must be lists")
        if p["id"] in seen:
            sys.exit(f"{where}: duplicate id '{p['id']}'")
        seen.add(p["id"])
        link = p.get("link")
        if link is not None and not (isinstance(link, dict) and link.get("url") and link.get("label")):
            sys.exit(f"{where}: 'link' must be null or {{url, label}}")
    return projects


# ---------- GitHub releases ----------

def fetch_releases(repo: str, optional: bool = False) -> tuple[list[dict], bool]:
    """Releases of a repo, newest first, and whether the single page may be truncated.

    optional=True turns a 404 into "no releases" instead of a failed build.
    """
    raw = ghapi.get(f"/repos/{repo}/releases?per_page=100", allow_404=optional)
    if raw is None:
        return [], False
    out = []
    for r in raw:
        if r.get("draft") or not r.get("published_at"):
            continue
        out.append({
            "version": version_of(r["tag_name"], repo),
            "date": datetime.fromisoformat(r["published_at"].replace("Z", "+00:00")),
            "url": r["html_url"],
            "pre": bool(r.get("prerelease")),
        })
    out.sort(key=lambda x: x["date"], reverse=True)
    return out, len(raw) == 100


# ---------- generative plate ----------

def plate_svg(seed: str) -> str:
    """Deterministic PCB-like plate: a chip with traces to the edge, one trace in signal colour."""
    rng = random.Random(hashlib.sha256(seed.encode("utf-8")).hexdigest())
    n, step, off = 6, 20, 10

    def px(i: int) -> int:
        return off + i * step

    x0, y0 = rng.randint(1, 3), rng.randint(1, 3)
    chip = [(x0, y0), (x0 + 1, y0), (x0, y0 + 1), (x0 + 1, y0 + 1)]
    chip_set = set(chip)
    used = set(chip)
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    traces: list[list[tuple[int, int]]] = []

    for _ in range(rng.randint(4, 6)):
        start = rng.choice(chip)
        options = [d for d in dirs
                   if (start[0] + d[0], start[1] + d[1]) not in chip_set
                   and 0 <= start[0] + d[0] < n and 0 <= start[1] + d[1] < n]
        if not options:
            continue
        d = rng.choice(options)
        pts, cur, turned = [start], start, False
        for _ in range(rng.randint(2, 5)):
            nxt = (cur[0] + d[0], cur[1] + d[1])
            if not (0 <= nxt[0] < n and 0 <= nxt[1] < n) or nxt in used:
                break
            cur = nxt
            pts.append(cur)
            used.add(cur)
            if not turned and rng.random() < 0.45:
                turned = True
                d = rng.choice([(d[1], d[0]), (-d[1], -d[0])])
        if len(pts) >= 2:
            traces.append(pts)

    sig = rng.randrange(len(traces)) if traces else -1
    parts = ['<svg class="plate-svg" viewBox="0 0 120 120" aria-hidden="true" focusable="false">']
    for gx in range(n):
        for gy in range(n):
            if (gx, gy) not in used:
                parts.append(f'<circle class="pl-dot" cx="{px(gx)}" cy="{px(gy)}" r="1.2"/>')
    for i, pts in enumerate(traces):
        cls = "pl-trace pl-sig" if i == sig else "pl-trace"
        points = " ".join(f"{px(x)},{px(y)}" for x, y in pts)
        parts.append(f'<polyline class="{cls}" points="{points}"/>')
    for i, pts in enumerate(traces):
        ex, ey = pts[-1]
        cls = "pl-pad sig" if i == sig else "pl-pad"
        parts.append(f'<circle class="{cls}" cx="{px(ex)}" cy="{px(ey)}" r="3.6"/>')
    parts.append(f'<rect class="pl-chip" x="{px(x0) - 6}" y="{px(y0) - 6}" width="{step + 12}" height="{step + 12}" rx="2"/>')
    parts.append(f'<rect class="pl-chip-dot" x="{px(x0) - 2}" y="{px(y0) - 2}" width="4" height="4"/>')
    parts.append("</svg>")
    return "".join(parts)


# ---------- rendering ----------

def render_project(num: int, p: dict, rel: list[dict], now: datetime) -> str:
    latest = rel[0] if rel else None
    is_new = bool(latest and now - latest["date"] <= timedelta(days=NEW_DAYS))

    links = []
    if p.get("link"):
        links.append(f'<a class="go" href="{esc(p["link"]["url"])}">{esc(p["link"]["label"])} <span aria-hidden="true">→</span></a>')
    if p.get("source") and (not p.get("link") or p["source"] != p["link"]["url"]):
        links.append(f'<a class="src" href="{esc(p["source"])}">Код ↗</a>')
    if not links:
        links.append('<span class="closed">Код закрыт</span>')

    if latest:
        version = (f'<a href="{esc(latest["url"])}">{esc(latest["version"])}</a>'
                   f' <span class="muted">· {time_tag(latest["date"])}</span>')
    else:
        version = '<span class="muted">—</span>'

    spec = [
        f'<div><dt>Статус</dt><dd><span class="dot dot-{p["status"]}" aria-hidden="true"></span>{STATUS[p["status"]]}</dd></div>',
        f"<div><dt>Версия</dt><dd>{version}</dd></div>",
        f'<div><dt>Стек</dt><dd>{esc(", ".join(p["stack"]))}</dd></div>',
        f'<div><dt>Платформы</dt><dd>{esc(", ".join(p["platforms"]))}</dd></div>',
    ]
    if p.get("fork_of"):
        spec.append(f'<div><dt>Основа</dt><dd><a href="https://github.com/{esc(p["fork_of"])}">{esc(p["fork_of"])}</a></dd></div>')

    new_badge = ' <span class="new">NEW</span>' if is_new else ""
    return f"""      <li class="row reveal" id="p-{esc(p['id'])}">
        <div class="row-num">{num:02d}</div>
        <div class="plate">{plate_svg(p['id'])}</div>
        <div class="row-main">
          <p class="row-kind">{esc(p['kind'])}</p>
          <h3>{esc(p['title'])}{new_badge}</h3>
          <p class="row-sum">{esc(p['summary'])}</p>
          <div class="row-links">{''.join(links)}</div>
        </div>
        <dl class="spec">{''.join(spec)}</dl>
      </li>"""


def render_ticker(log: list[tuple[dict, dict]]) -> str:
    if not log:
        return ""
    items = "".join(
        f'<span class="tick"><span class="sig">●</span> {esc(p["title"].upper())} {esc(r["version"])} — {fmt_date(r["date"])}</span>'
        for p, r in log[:TICKER_LIMIT]
    )
    return (f'<div class="ticker" role="marquee" aria-label="Последние релизы">'
            f'<div class="ticker-track"><div class="ticker-group">{items}</div>'
            f'<div class="ticker-group" aria-hidden="true">{items}</div></div></div>')


def render_log(log: list[tuple[dict, dict]]) -> str:
    if not log:
        return '    <p class="muted">Журнал появится после сборки с доступом к GitHub.</p>'
    rows = []
    for p, r in log[:LOG_LIMIT]:
        pre = ' <span class="pre">pre</span>' if r["pre"] else ""
        rows.append(
            f'      <li class="log-row reveal">{time_tag(r["date"])}'
            f'<a class="log-proj" href="#p-{esc(p["id"])}">{esc(p["title"])}</a>'
            f'<a class="log-ver" href="{esc(r["url"])}">{esc(r["version"])}{pre} <span aria-hidden="true">↗</span></a></li>'
        )
    return '    <ol class="log">\n' + "\n".join(rows) + "\n    </ol>"


def build(offline: bool, out: Path) -> None:
    now = datetime.now(timezone.utc)
    projects = load_projects()

    releases: dict[str, list[dict]] = {}
    truncated = False
    for p in projects:
        repo, optional = releases_repo(p)
        rel, capped = fetch_releases(repo, optional) if repo and not offline else ([], False)
        releases[p["id"]] = rel
        # A full page whose oldest release is still within 30 days: the count is a lower bound.
        if capped and rel and now - rel[-1]["date"] <= timedelta(days=30):
            truncated = True

    log = sorted(((p, r) for p in projects for r in releases[p["id"]]),
                 key=lambda pr: pr[1]["date"], reverse=True)
    recent = sum(1 for _, r in log if now - r["date"] <= timedelta(days=30))
    suffix = "+" if truncated else ""
    if log:
        p, r = log[0]
        last = (f'<a href="{esc(r["url"])}">{esc(p["title"])} {esc(r["version"])}</a>'
                f' <span class="muted">· {time_tag(r["date"])}</span>')
    else:
        last = '<span class="muted">—</span>'

    page = (ROOT / "template.html").read_text(encoding="utf-8")
    values = {
        "year": str(now.astimezone(MSK).year),
        "project_count": str(len(projects)),
        "releases_30d": f"{recent}{suffix}",
        "last_release": last,
        "ticker": render_ticker(log),
        "projects": "\n".join(render_project(i + 1, p, releases[p["id"]], now) for i, p in enumerate(projects)),
        "release_log": render_log(log),
        "built_at": now.astimezone(MSK).strftime("%d.%m.%Y %H:%M МСК"),
    }
    def fill(m: re.Match) -> str:
        if m.group(1) not in values:
            sys.exit(f"template.html: unknown placeholder {m.group(0)}")
        return values[m.group(1)]

    page = re.sub(r"\{\{(\w+)\}\}", fill, page)

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    shutil.copytree(ROOT / "assets", out / "assets")
    shutil.copytree(ROOT / "img", out / "img")
    print(f"built {out / 'index.html'}: {len(projects)} projects, {len(log)} releases")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--offline", action="store_true", help="do not call the GitHub API")
    ap.add_argument("--out", default=str(ROOT / "_site"), help="output directory (default: _site)")
    args = ap.parse_args()
    build(args.offline, Path(args.out))


if __name__ == "__main__":
    main()

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
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import ghapi
import schema

ROOT = Path(__file__).resolve().parent.parent
MSK = timezone(timedelta(hours=3))
NEW_DAYS = 14
# Initial import: every card that existed before the site went live has this 'added' date.
LAUNCH = date(2026, 10, 16)
NEW_PROJECT_DAYS = 30
LOG_LIMIT = 10
LOG_PER_PROJECT = 3
NOTE_MAX = 120
TICKER_LIMIT = 8

STATUS = {
    "live": "Работает",
    "dev": "В разработке",
    "research": "Исследование",
}

# Empty version or last release: a visible dash, a spoken phrase.
NO_RELEASES = '<span class="muted"><span aria-hidden="true">—</span><span class="sr">релизов нет</span></span>'


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


def added_date(p: dict) -> date | None:
    try:
        return date.fromisoformat(str(p.get("added") or "")[:10])
    except ValueError:
        return None


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
    path = ROOT / "data" / "projects.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"data/projects.json: invalid JSON: {e}")
    errors = schema.validate(data, STATUS)
    if errors:
        print("data/projects.json: validation failed", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        sys.exit(1)
    return data["projects"]


# ---------- release notes ----------

# Headings that only frame a release body; such a first heading is not the note itself.
SECTION_HEADS = {
    "release", "changes", "changelog", "what's changed", "что изменилось", "что изменено",
    "изменения", "изменено", "добавлено", "исправлено", "удалено", "новое", "added", "changed",
    "fixed", "removed", "notes", "assets", "checks", "проверка", "checksums", "файлы", "files",
    "установка", "install", "new contributors",
}
# Headings whose first item describes the change.
CHANGE_HEADS = {
    "changes", "changelog", "what's changed", "что изменилось", "что изменено", "изменения",
    "изменено", "добавлено", "исправлено", "новое", "added", "changed", "fixed",
}
HEAD = re.compile(r"^#{1,4}\s+(.+?)\s*#*$")
ITEM = re.compile(r"^\s*([-*+]|\d+[.)])\s")
SERVICE_LINE = re.compile(r"^(version name|version code|git tag|full changelog)\b", re.IGNORECASE)
COMMIT_PREFIX = re.compile(r"^(fix|feat|feature|chore|docs|refactor|perf|build|ci)(\([^)]*\))?!?:\s*", re.IGNORECASE)
CYRILLIC = re.compile(r"[А-Яа-яЁё]")


def _head_key(text: str) -> str:
    return text.lower().rstrip(":").strip()


def _body_lines(body: str) -> list[str]:
    """Body lines with the contents of ``` code blocks blanked out."""
    lines, fenced = [], False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
            lines.append(line)
        else:
            lines.append("" if fenced else line)
    return lines


def _meaningful(line: str) -> bool:
    s = line.strip()
    if not s or s.startswith(("#", "|", ">", "```", "<")):
        return False
    s = s.lstrip("-*+ ").replace("**", "")
    return bool(s) and not SERVICE_LINE.match(s)


def _item(lines: list[str], i: int) -> str:
    """Line i with its wrapped continuation lines."""
    parts = [lines[i].strip()]
    for line in lines[i + 1:]:
        s = line.strip()
        if not s or HEAD.match(s) or ITEM.match(line) or not _meaningful(line):
            break
        parts.append(s)
    return " ".join(parts)


def _note_candidates(name: str, body: str):
    m = re.match(r"^.*?\d[^:]*:\s+(\S.{2,})$", name.strip())
    if m:
        yield m.group(1)
    lines = _body_lines(body)
    first = next((line.strip() for line in lines if line.strip()), "")
    head = HEAD.match(first)
    if head and _head_key(head.group(1)) not in SECTION_HEADS:
        yield head.group(1)
    under = False
    for i, line in enumerate(lines):
        head = HEAD.match(line.strip())
        if head:
            under = _head_key(head.group(1)) in CHANGE_HEADS
        elif under and _meaningful(line):
            yield _item(lines, i)
            break
    for i, line in enumerate(lines):
        if _meaningful(line):
            yield _item(lines, i)
            break


def _clean_note(s: str) -> str:
    s = re.sub(r"!?\[([^\]]*)\]\([^)]+\)", r"\1", s)
    s = s.replace("`", "").replace("**", "")
    s = re.sub(r"<[^>]*>", "", s)
    s = re.sub(r"\s+by @\S+ in https?://\S+$", "", s)
    s = re.sub(r"https?://\S+", "", s)
    s = s.strip(" -*\t")
    s = COMMIT_PREFIX.sub("", s)
    s = re.split(r"(?<=[.!?])\s+(?=[А-ЯЁA-Z«\"])", s, maxsplit=1)[0]
    s = re.sub(r"\s+", " ", s).rstrip(" :;,—-")
    if not CYRILLIC.search(s):
        return ""  # English auto-notes do not belong on the Russian page
    if len(s) > NOTE_MAX:
        cut = s[:NOTE_MAX + 1]
        cut = cut[:cut.rindex(" ")] if " " in cut else s[:NOTE_MAX]
        s = cut.rstrip(",.;:—- ") + "…"
    return s


def release_note(name: str, body: str) -> str:
    """One short Russian line about a release, from its name or Markdown body; "" if none fits."""
    try:
        return next((note for note in map(_clean_note, _note_candidates(name, body)) if note), "")
    except Exception:  # noqa: BLE001 - a malformed body must never fail the build
        return ""


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
            "note": release_note(r.get("name") or "", r.get("body") or ""),
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
    today = now.astimezone(MSK).date()
    a = added_date(p)
    is_new_project = bool(a and a > LAUNCH and timedelta(0) <= today - a <= timedelta(days=NEW_PROJECT_DAYS))
    is_fresh = bool(latest and now - latest["date"] <= timedelta(days=NEW_DAYS))
    title = esc(p["title"])

    links = []
    if p.get("link"):
        links.append(f'<a class="go" href="{esc(p["link"]["url"])}">{esc(p["link"]["label"])}'
                     f'<span class="sr"> — {title}</span> <span aria-hidden="true">→</span></a>')
    if p.get("source") and (not p.get("link") or p["source"] != p["link"]["url"]):
        links.append(f'<a class="src" href="{esc(p["source"])}">Код<span class="sr"> проекта {title}</span>'
                     f' <span aria-hidden="true">↗</span></a>')
    if not links:
        links.append('<span class="closed">Код закрыт</span>')

    if latest:
        date_cls = "fresh" if is_fresh else "muted"
        version = (f'<a href="{esc(latest["url"])}"><span class="sr">{title}, версия </span>{esc(latest["version"])}</a>'
                   f' <span class="{date_cls}">· {time_tag(latest["date"])}</span>')
    else:
        version = NO_RELEASES

    spec = [
        f'<div><dt>Статус</dt><dd><span class="dot dot-{p["status"]}" aria-hidden="true"></span>{STATUS[p["status"]]}</dd></div>',
        f"<div><dt>Версия</dt><dd>{version}</dd></div>",
        f'<div><dt>Стек</dt><dd>{esc(", ".join(p["stack"]))}</dd></div>',
        f'<div><dt>Платформы</dt><dd>{esc(", ".join(p["platforms"]))}</dd></div>',
    ]
    if p.get("fork_of"):
        spec.append(f'<div><dt>Основа</dt><dd><a href="https://github.com/{esc(p["fork_of"])}">{esc(p["fork_of"])}</a></dd></div>')

    primary = p["link"]["url"] if p.get("link") else p.get("source")
    title_html = f'<a class="row-title" href="{esc(primary)}">{title}</a>' if primary else title
    new_badge = ' <span class="new">Новый</span>' if is_new_project else ""
    return f"""      <li class="row reveal" id="p-{esc(p['id'])}">
        <a class="row-num" href="#p-{esc(p['id'])}" title="Постоянная ссылка на проект" aria-label="{num:02d} — ссылка на проект {title}">{num:02d}</a>
        <div class="plate">{plate_svg(p['id'])}</div>
        <div class="row-main">
          <p class="row-kind">{esc(p['kind'])}</p>
          <h3>{title_html}{new_badge}</h3>
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


def group_log(log: list[tuple[dict, dict]]) -> list[dict]:
    """Releases of one project on one Moscow day as one group, newest group first."""
    groups: dict[tuple[str, date], dict] = {}
    for p, r in log:
        key = (p["id"], r["date"].astimezone(MSK).date())
        group = groups.get(key)
        if group is None:
            groups[key] = {"p": p, "newest": r, "oldest": r, "count": 1}
        else:
            group["oldest"] = r
            group["count"] += 1
    return list(groups.values())


def render_log(log: list[tuple[dict, dict]]) -> str:
    if not log:
        return '    <p class="muted">Журнал появится после сборки с доступом к GitHub.</p>'
    rows = []
    per_project: dict[str, int] = {}
    for g in group_log(log):
        p, newest, oldest = g["p"], g["newest"], g["oldest"]
        shown = per_project.get(p["id"], 0)
        if shown >= LOG_PER_PROJECT:
            continue
        per_project[p["id"]] = shown + 1
        title = esc(p["title"])
        if g["count"] == 1:
            ver_text = esc(newest["version"])
        else:
            ver_text = f'{esc(oldest["version"])}–{esc(newest["version"])} · {g["count"]}'
        pre = ' <span class="pre">pre</span>' if newest["pre"] else ""
        note = newest.get("note") or ""
        note_html = f'<span class="log-note">{esc(note)}</span>' if note else ""
        rows.append(
            f'      <li class="log-row reveal">{time_tag(newest["date"])}'
            f'<div class="log-what"><a class="log-proj" href="#p-{esc(p["id"])}">{title}</a>{note_html}</div>'
            f'<a class="log-ver" href="{esc(newest["url"])}"><span class="sr">{title}, версия </span>'
            f'{ver_text}{pre} <span aria-hidden="true">↗</span></a></li>'
        )
        if len(rows) == LOG_LIMIT:
            break
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
        last = NO_RELEASES

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

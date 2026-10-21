"""Strict check of data/projects.json (standard library only).

validate() collects every problem instead of stopping at the first one. Each message
starts with the address of the bad value, for example
"projects[3] (id=foo).link.url: ..." or "ignore[2].repo: ...".

A new card field is added to ALLOWED first, then used in build.py.
"""

from __future__ import annotations

import difflib
import re
from datetime import date
from urllib.parse import urlsplit

TOP_LEVEL = ("projects", "ignore")
ALLOWED = ("id", "title", "kind", "summary", "stack", "platforms", "status",
           "releases", "link", "source", "fork_of", "added")
REQUIRED = ("id", "title", "kind", "summary", "stack", "platforms", "status")
LINK_KEYS = ("url", "label")
IGNORE_KEYS = ("repo", "reason")
SUMMARY_MAX = 300

ID_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
REPO_RE = re.compile(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}")
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
URL_SCHEMES = ("http", "https")


def _type(value: object) -> str:
    """JSON name of a value's type, for messages."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _show(value: object) -> str:
    """Short printable form of a bad value."""
    if isinstance(value, str):
        text = value if len(value) <= 60 else value[:57] + "..."
        return repr(text)
    if isinstance(value, (list, dict)) and not value:
        return "empty " + _type(value)
    return _type(value)


def _hint(key: str, allowed: tuple[str, ...]) -> str:
    match = difflib.get_close_matches(key, allowed, n=1)
    return f"; did you mean '{match[0]}'?" if match else f"; allowed: {', '.join(allowed)}"


def _is_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_repo(value: object) -> bool:
    return isinstance(value, str) and REPO_RE.fullmatch(value) is not None


def _is_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parts = urlsplit(value)
    except ValueError:
        return False
    return parts.scheme in URL_SCHEMES and bool(parts.netloc)


def _is_date(value: object) -> bool:
    if not isinstance(value, str) or DATE_RE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _check_list(errors: list[str], where: str, value: object) -> None:
    """Non-empty list of non-empty strings."""
    if not isinstance(value, list) or not value:
        errors.append(f"{where}: must be a non-empty list of strings, got {_show(value)}")
        return
    for j, item in enumerate(value):
        if not _is_text(item):
            errors.append(f"{where}[{j}]: must be a non-empty string, got {_show(item)}")


def _check_keys(errors: list[str], where: str, obj: dict, allowed: tuple[str, ...]) -> None:
    for key in obj:
        if key not in allowed:
            errors.append(f"{where}.{key}: unknown field{_hint(str(key), allowed)}")


def _check_project(errors: list[str], where: str, p: dict, statuses) -> None:
    _check_keys(errors, where, p, ALLOWED)
    for key in REQUIRED:
        if key not in p:
            errors.append(f"{where}.{key}: required field is missing")

    if "id" in p and not (isinstance(p["id"], str) and ID_RE.fullmatch(p["id"])):
        errors.append(f"{where}.id: must be kebab-case (a-z, 0-9, single hyphens), got {_show(p['id'])}")
    for key in ("title", "kind", "summary"):
        if key in p and not _is_text(p[key]):
            errors.append(f"{where}.{key}: must be a non-empty string, got {_show(p[key])}")
    summary = p.get("summary")
    if isinstance(summary, str) and len(summary) > SUMMARY_MAX:
        errors.append(f"{where}.summary: {len(summary)} characters, the limit is {SUMMARY_MAX}")
    if "status" in p:
        status = p["status"]
        if not (isinstance(status, str) and status in statuses):
            errors.append(f"{where}.status: must be one of {', '.join(statuses)}, got {_show(status)}")
    for key in ("stack", "platforms"):
        if key in p:
            _check_list(errors, f"{where}.{key}", p[key])

    releases = p.get("releases")
    if not (releases is None or releases is False or _is_repo(releases)):
        errors.append(f"{where}.releases: must be null, false or 'owner/repo', got {_show(releases)}")
    fork_of = p.get("fork_of")
    if fork_of is not None and not _is_repo(fork_of):
        errors.append(f"{where}.fork_of: must be null or 'owner/repo', got {_show(fork_of)}")

    link = p.get("link")
    if link is not None:
        if not isinstance(link, dict):
            errors.append(f"{where}.link: must be null or an object {{url, label}}, got {_show(link)}")
        else:
            _check_keys(errors, f"{where}.link", link, LINK_KEYS)
            if not _is_url(link.get("url")):
                errors.append(f"{where}.link.url: must be an http(s) URL, got {_show(link.get('url'))}")
            if not _is_text(link.get("label")):
                errors.append(f"{where}.link.label: must be a non-empty string, got {_show(link.get('label'))}")

    source = p.get("source")
    if source is not None and not _is_url(source):
        errors.append(f"{where}.source: must be null or an http(s) URL, got {_show(source)}")
    added = p.get("added")
    if added is not None and not _is_date(added):
        errors.append(f"{where}.added: must be null or a date YYYY-MM-DD, got {_show(added)}")


def _check_ignore(errors: list[str], ignore: object) -> None:
    if ignore is None:
        return
    if not isinstance(ignore, list):
        errors.append(f"ignore: must be a list of objects {{repo, reason}}, got {_show(ignore)}")
        return
    seen: dict[str, int] = {}
    for i, item in enumerate(ignore):
        where = f"ignore[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: must be an object {{repo, reason}}, got {_show(item)}")
            continue
        _check_keys(errors, where, item, IGNORE_KEYS)
        repo = item.get("repo")
        if "repo" not in item:
            errors.append(f"{where}.repo: required field is missing")
        elif not _is_repo(repo):
            errors.append(f"{where}.repo: must be 'owner/repo', got {_show(repo)}")
        else:
            first = seen.setdefault(repo.lower(), i)
            if first != i:
                errors.append(f"{where}.repo: duplicate {_show(repo)} (also ignore[{first}])")
        if "reason" not in item:
            errors.append(f"{where}.reason: required field is missing")
        elif not _is_text(item["reason"]):
            errors.append(f"{where}.reason: must be a non-empty string, got {_show(item['reason'])}")


def validate(data: object, statuses) -> list[str]:
    """All problems in a parsed projects.json; an empty list means the data is valid.

    statuses is the collection of allowed 'status' values (build.py passes its STATUS dict).
    A missing optional field is the same as null.
    """
    errors: list[str] = []
    if not isinstance(data, dict):
        return [f"(root): must be an object {{projects, ignore}}, got {_show(data)}"]
    for key in data:
        if key not in TOP_LEVEL:
            errors.append(f"{key}: unknown top-level field{_hint(str(key), TOP_LEVEL)}")

    projects = data.get("projects")
    if not isinstance(projects, list) or not projects:
        errors.append(f"projects: must be a non-empty list of objects, got {_show(projects)}")
        projects = []
    ids: dict[str, int] = {}
    repos: dict[str, int] = {}
    for i, p in enumerate(projects):
        where = f"projects[{i}]"
        if not isinstance(p, dict):
            errors.append(f"{where}: must be an object, got {_show(p)}")
            continue
        pid = p.get("id")
        if _is_text(pid):
            where += f" (id={pid})"
        _check_project(errors, where, p, statuses)
        if isinstance(pid, str) and ID_RE.fullmatch(pid):
            first = ids.setdefault(pid, i)
            if first != i:
                errors.append(f"{where}.id: duplicate id (also projects[{first}])")
        releases = p.get("releases")
        if _is_repo(releases):
            first = repos.setdefault(releases.lower(), i)
            if first != i:
                errors.append(f"{where}.releases: {_show(releases)} is already used by projects[{first}]")

    _check_ignore(errors, data.get("ignore"))
    return errors

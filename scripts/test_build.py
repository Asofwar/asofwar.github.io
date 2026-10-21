"""Unit tests for the site scripts (standard library only, no network).

Run from the repository root:
    python3 -m unittest discover -s scripts -p "test_*.py" -v
Both this and `python3 scripts/test_build.py` put scripts/ on sys.path,
so the scripts are imported as top-level modules, as build.py imports ghapi.
"""

from __future__ import annotations

import contextlib
import copy
import email.message
import io
import json
import tempfile
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import build
import discover
import ghapi
import repos
import schema

DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "projects.json").read_text(encoding="utf-8"))


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


def release(version: str, when: str, pre: bool = False, note: str = "") -> dict:
    return {"version": version, "date": utc(when), "url": f"https://example.com/{version}",
            "pre": pre, "note": note}


def project(pid: str, title: str = "") -> dict:
    return {"id": pid, "title": title or pid.title()}


class VersionOfTest(unittest.TestCase):
    def test_repo_prefix_and_v_removed(self):
        self.assertEqual(build.version_of("flint2-openwrt-v25.12.5-f0a60eee", "Asofwar/flint2-openwrt"),
                         "25.12.5-f0a60eee")

    def test_plain_tags(self):
        self.assertEqual(build.version_of("v3.7.0", "Asofwar/GsmNotify-releases"), "3.7.0")
        self.assertEqual(build.version_of("2.32.0", "Asofwar/prokop"), "2.32.0")
        self.assertEqual(build.version_of("v0.1.46.1-asofwar.3", "Asofwar/Strata"), "0.1.46.1-asofwar.3")

    def test_word_after_v_kept(self):
        self.assertEqual(build.version_of("vendor-build"), "vendor-build")
        self.assertEqual(build.version_of("flint2-openwrt-", "Asofwar/flint2-openwrt"), "flint2-openwrt-")


class ReleasesRepoTest(unittest.TestCase):
    def test_string_is_used_and_404_fails(self):
        self.assertEqual(build.releases_repo({"releases": "Asofwar/prokop"}), ("Asofwar/prokop", False))

    def test_false_turns_off(self):
        p = {"releases": False, "source": "https://github.com/Asofwar/prokop"}
        self.assertEqual(build.releases_repo(p), (None, False))

    def test_null_with_own_source(self):
        p = {"releases": None, "source": "https://github.com/Asofwar/Strata.git"}
        self.assertEqual(build.releases_repo(p), ("Asofwar/Strata", True))
        self.assertEqual(build.releases_repo({"source": "https://github.com/asofwar/x/tree/main"}),
                         ("asofwar/x", True))

    def test_null_with_foreign_or_no_source(self):
        p = {"releases": None, "source": "https://github.com/someone/else"}
        self.assertEqual(build.releases_repo(p), (None, False))
        self.assertEqual(build.releases_repo({"releases": None}), (None, False))


class ReleaseNoteTest(unittest.TestCase):
    def test_name_after_version_colon(self):
        self.assertEqual(build.release_note("Strata Asofwar 0.2.1.1-3: +30% генерации на длинном контексте", ""),
                         "+30% генерации на длинном контексте")

    def test_first_heading(self):
        body = "## DNS роутера больше не пропадает: исправление 2.30.6 доведено\nСрочное исправление."
        self.assertEqual(build.release_note("2.30.7", body),
                         "DNS роутера больше не пропадает: исправление 2.30.6 доведено")

    def test_item_under_changes(self):
        body = "## Changes\n- Групповые команды: над списком объектов появились группы."
        self.assertEqual(build.release_note("GsmNotify 3.7.0", body),
                         "Групповые команды: над списком объектов появились группы.")

    def test_english_auto_note_dropped(self):
        body = ("## What's Changed\n"
                "* fix: keep unverified charging state unknown by @x in https://github.com/a/b/pull/12\n"
                "**Full Changelog**: https://github.com/a/b/compare/v1...v2")
        self.assertEqual(build.release_note("v1.3.4", body), "")

    def test_long_note_cut_on_word(self):
        note = build.release_note("x", "А" * 50 + " " + "Б" * 50 + " " + "В" * 50)
        self.assertEqual(note, "А" * 50 + " " + "Б" * 50 + "…")
        self.assertLessEqual(len(note), build.NOTE_MAX + 1)


class GroupLogTest(unittest.TestCase):
    def test_same_project_same_msk_day_collapses(self):
        a, b = project("a"), project("b")
        log = [
            (a, release("1.2", "2026-10-15T20:00:00")),  # 23:00 MSK, 15.10
            (b, release("9.0", "2026-10-15T09:00:00")),
            (a, release("1.1", "2026-10-14T21:30:00")),  # 00:30 MSK, 15.10: other UTC day, same MSK day
            (a, release("1.0", "2026-10-14T20:30:00")),  # 23:30 MSK, 14.10
        ]
        groups = build.group_log(log)
        self.assertEqual([(g["p"]["id"], g["newest"]["version"], g["oldest"]["version"], g["count"])
                          for g in groups],
                         [("a", "1.2", "1.1", 2), ("b", "9.0", "9.0", 1), ("a", "1.0", "1.0", 1)])

    def test_render_log_caps_groups_per_project(self):
        a, b = project("a", "Alpha"), project("b", "Beta")
        log = [(a, release(f"1.{9 - d}", f"2026-10-{19 - d:02d}T12:00:00")) for d in range(5)]
        log.append((b, release("2.0", "2026-10-01T12:00:00")))
        html = build.render_log(log)
        self.assertEqual(html.count('<li class="log-row'), build.LOG_PER_PROJECT + 1)
        self.assertEqual(html.count('href="#p-a"'), build.LOG_PER_PROJECT)
        self.assertIn('href="#p-b"', html)
        self.assertNotIn("example.com/1.6", html)

    def test_render_log_limit_and_series_label(self):
        log = [(project(f"p{i}"), release("1.0", f"2026-10-{20 - i:02d}T12:00:00")) for i in range(12)]
        self.assertEqual(build.render_log(log).count('<li class="log-row'), build.LOG_LIMIT)
        a = project("a", "Alpha")
        series = [(a, release("1.3", "2026-10-15T12:00:00", pre=True, note="Заметка <b>")),
                  (a, release("1.2", "2026-10-15T11:00:00")),
                  (a, release("1.1", "2026-10-15T10:00:00", note="Старая"))]
        html = build.render_log(series)
        self.assertIn("1.1–1.3 · 3", html)
        self.assertIn('<span class="pre">pre</span>', html)
        self.assertIn('<span class="log-note">Заметка &lt;b&gt;</span>', html)
        self.assertNotIn("Старая", html)

    def test_offline_log_placeholder(self):
        self.assertIn("Журнал появится", build.render_log([]))


class SchemaTest(unittest.TestCase):
    def errors(self, mutate) -> list[str]:
        data = copy.deepcopy(DATA)
        mutate(data)
        return schema.validate(data, build.STATUS)

    def assertError(self, mutate, *parts: str):
        errors = self.errors(mutate)
        self.assertTrue(any(all(part in e for part in parts) for e in errors),
                        f"no error with {parts!r} in {errors!r}")

    def test_current_data_is_valid(self):
        self.assertEqual(schema.validate(DATA, build.STATUS), [])

    def test_javascript_url(self):
        def mutate(d):
            d["projects"][0]["link"] = {"url": "javascript:alert(1)", "label": "Открыть"}
        self.assertError(mutate, "projects[0]", ".link.url:", "http(s)")

    def test_non_http_source_with_host(self):
        for url in ("javascript://example.com/%0Aalert(1)", "data://example.com/x", "ftp://example.com/"):
            def mutate(d, url=url):
                d["projects"][1]["source"] = url
            self.assertError(mutate, "projects[1]", ".source:", "http(s)")

    def test_bad_id(self):
        def mutate(d):
            d["projects"][0]["id"] = "a b"
        self.assertError(mutate, "projects[0] (id=a b).id:", "kebab-case")

    def test_unknown_key_suggestion(self):
        def mutate(d):
            d["projects"][1]["relases"] = "Asofwar/x"
        self.assertError(mutate, "projects[1]", ".relases: unknown field", "did you mean 'releases'?")

    def test_title_not_string(self):
        def mutate(d):
            d["projects"][0]["title"] = {"ru": "Проект"}
        self.assertError(mutate, ".title: must be a non-empty string", "object")

    def test_stack_with_int(self):
        def mutate(d):
            d["projects"][0]["stack"] = ["Rust", 5]
        self.assertError(mutate, ".stack[1]: must be a non-empty string", "number")

    def test_ignore_without_repo(self):
        def mutate(d):
            d["ignore"] = list(d.get("ignore") or []) + [{"reason": "нет репозитория"}]
        index = len(DATA.get("ignore") or [])
        self.assertError(mutate, f"ignore[{index}].repo: required field is missing")

    def test_bad_added(self):
        def mutate(d):
            d["projects"][2]["added"] = "вчера"
        self.assertError(mutate, "projects[2]", ".added:", "YYYY-MM-DD")

    def test_all_errors_collected(self):
        def mutate(d):
            d["projects"][0]["id"] = "a b"
            d["projects"][1]["added"] = "2026-13-01"
        self.assertGreaterEqual(len(self.errors(mutate)), 2)


class PlateTest(unittest.TestCase):
    def test_deterministic_and_hidden(self):
        svg = build.plate_svg("prokop")
        self.assertEqual(svg, build.plate_svg("prokop"))
        self.assertNotEqual(svg, build.plate_svg("strata"))
        self.assertTrue(svg.startswith('<svg class="plate-svg"'))
        self.assertIn('aria-hidden="true"', svg)
        self.assertIn('focusable="false"', svg)


class OfflineBuildTest(unittest.TestCase):
    def test_build_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "site"
            with contextlib.redirect_stdout(io.StringIO()):
                build.build(offline=True, out=out)
            page = (out / "index.html").read_text(encoding="utf-8")
            fonts = sorted(p.name for p in (out / "assets" / "fonts").glob("*.woff2"))
            unused = [(out / "assets" / name).exists() for name in ("style.css", "main.js")]
        self.assertEqual(fonts, ["golos.woff2", "jbmono.woff2", "unbounded.woff2"])
        self.assertEqual(unused, [False, False])  # inlined into the page, not published as files
        self.assertNotIn("{{", page)
        self.assertEqual(page.count('<li class="row reveal"'), len(DATA["projects"]))
        self.assertIn("Журнал появится", page)


class KnownReposTest(unittest.TestCase):
    def test_bad_ignore_entry_skipped(self):
        data = {
            "projects": [
                {"id": "a", "releases": "Asofwar/A", "source": "https://github.com/Asofwar/Src"},
                {"id": "b", "releases": False, "link": {"url": "https://github.com/Asofwar/Link/releases"}},
                "not a project",
            ],
            "ignore": [{"reason": "без repo"}, "Asofwar/str", {"repo": "Asofwar/Ignored", "reason": "x"}],
        }
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            known = discover.known_repos(data)
        self.assertEqual(known, {"asofwar/asofwar.github.io", "asofwar/a", "asofwar/src",
                                 "asofwar/link", "asofwar/ignored"})
        self.assertEqual(err.getvalue().count("warning: skipped ignore entry"), 2)


class FakeResponse:
    def __init__(self, body: str):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self) -> bytes:
        return self.body.encode("utf-8")


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://api.github.com/x", code, "Reason", email.message.Message(), None)


class GhapiRetryTest(unittest.TestCase):
    def call(self, script: list, **kwargs):
        """ghapi.get('/x') against a fake urlopen that plays `script` item by item."""
        calls: list[str] = []

        def fake_urlopen(req, timeout=None):
            calls.append(req.full_url)
            item = script[len(calls) - 1]
            if isinstance(item, BaseException):
                raise item
            return FakeResponse(item)

        with mock.patch("urllib.request.urlopen", fake_urlopen), \
                mock.patch.object(ghapi.time, "sleep") as sleep, \
                contextlib.redirect_stderr(io.StringIO()):
            result = ghapi.get("/x", **kwargs)
        return result, len(calls), [c.args[0] for c in sleep.call_args_list]

    def test_503_twice_then_ok(self):
        result, calls, sleeps = self.call([http_error(503), http_error(503), '{"ok": true}'])
        self.assertEqual(result, {"ok": True})
        self.assertEqual(calls, 3)
        self.assertEqual(sleeps, [2, 4])

    def test_503_every_time_exits(self):
        with self.assertRaises(SystemExit) as ctx:
            self.call([http_error(503)] * ghapi.ATTEMPTS)
        self.assertIn("HTTP 503", str(ctx.exception.code))

    def test_404_allowed_without_retry(self):
        result, calls, sleeps = self.call([http_error(404)], allow_404=True)
        self.assertIsNone(result)
        self.assertEqual(calls, 1)
        self.assertEqual(sleeps, [])

    def test_404_not_allowed_exits_without_retry(self):
        with self.assertRaises(SystemExit):
            self.call([http_error(404)])

    def test_soft_returns_none_on_blocked_repo(self):
        result, calls, sleeps = self.call([http_error(451)], allow_404=True, soft=True)
        self.assertIsNone(result)
        self.assertEqual(calls, 1)
        self.assertEqual(sleeps, [])


class RepoOfTest(unittest.TestCase):
    def test_names(self):
        self.assertEqual(repos.repo_of("https://github.com/Asofwar/Foo.git"), "asofwar/foo")
        self.assertEqual(repos.repo_of("https://github.com/Asofwar/foo/releases/latest"), "asofwar/foo")
        self.assertEqual(repos.repo_of("https://github.com/Asofwar/foo"), "asofwar/foo")
        self.assertEqual(repos.repo_of("https://github.com/Asofwar/foo.github.io"), "asofwar/foo.github.io")
        self.assertIsNone(repos.repo_of("https://asofwar.github.io/prokop/"))
        self.assertIsNone(repos.repo_of(None))

    def test_known_repos_strip_git_suffix(self):
        data = {"projects": [{"id": "a", "source": "https://github.com/Asofwar/Foo.git"}]}
        self.assertIn("asofwar/foo", discover.known_repos(data))


def fake_api(routes: dict):
    """ghapi.get replacement answering by path prefix; records the paths it was asked for."""
    asked: list[str] = []

    def get(path, raw=False, allow_404=False, soft=False):
        asked.append(path)
        for prefix, answer in routes.items():
            if path.startswith(prefix):
                return answer
        raise AssertionError(f"unexpected request {path}")

    return get, asked


class DiscoverTest(unittest.TestCase):
    RECENT = "2026-10-20T10:00:00Z"
    CUTOFF = utc("2026-06-01")

    def test_status_hint_uses_source_fallback(self):
        get, asked = fake_api({"/repos/Asofwar/Tool/releases": [
            {"tag_name": "v1.0.0", "published_at": self.RECENT, "prerelease": False}]})
        projects = [{"id": "tool", "status": "dev", "releases": None,
                     "source": "https://github.com/Asofwar/Tool"}]
        with mock.patch.object(discover.ghapi, "get", get):
            hints = discover.status_hints(projects)
        self.assertEqual(hints, [{"id": "tool", "suggest_status": "live", "version": "v1.0.0"}])
        self.assertEqual(asked, ["/repos/Asofwar/Tool/releases?per_page=10"])

    def test_fork_drops_inherited_text_and_readme(self):
        get, asked = fake_api({
            "/repos/Asofwar/fork/releases": [{"tag_name": "v2", "published_at": self.RECENT}],
            "/repos/Asofwar/fork": {"parent": {"full_name": "Up/proj", "description": "Upstream text",
                                               "homepage": "https://up.example"}},
        })
        repo = {"full_name": "Asofwar/fork", "html_url": "https://github.com/Asofwar/fork", "fork": True,
                "description": "Upstream text", "homepage": "https://up.example", "pushed_at": self.RECENT}
        with mock.patch.object(discover.ghapi, "get", get):
            entry = discover.candidate(repo, self.CUTOFF)
        self.assertEqual(entry["fork_of"], "Up/proj")
        self.assertEqual((entry["description"], entry["homepage"], entry["readme_excerpt"]), ("", "", ""))
        self.assertFalse(any(p.endswith("/readme") for p in asked))

    def test_fork_keeps_own_description(self):
        get, _ = fake_api({
            "/repos/Asofwar/fork/releases": [{"tag_name": "v2", "published_at": self.RECENT}],
            "/repos/Asofwar/fork": {"parent": {"full_name": "Up/proj", "description": "Upstream text"}},
        })
        repo = {"full_name": "Asofwar/fork", "html_url": "u", "fork": True,
                "description": "Порт на Steam Deck", "pushed_at": self.RECENT}
        with mock.patch.object(discover.ghapi, "get", get):
            entry = discover.candidate(repo, self.CUTOFF)
        self.assertEqual(entry["description"], "Порт на Steam Deck")

    def test_fork_without_fresh_release_skipped(self):
        get, _ = fake_api({"/repos/Asofwar/fork/releases": []})
        repo = {"full_name": "Asofwar/fork", "html_url": "u", "fork": True, "pushed_at": self.RECENT}
        with mock.patch.object(discover.ghapi, "get", get):
            self.assertIsNone(discover.candidate(repo, self.CUTOFF))


if __name__ == "__main__":
    unittest.main()

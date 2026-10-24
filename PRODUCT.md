# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two audiences, equally important (confirmed by the owner):

- **People who came for a tool.** Users of Prokop, GSM-Пульт, AvangardRO, Flint 2 firmware, FreeBrush and other projects who need the current version, a download link or the project page.
- **People evaluating the developer.** Employers, clients and fellow developers who want to see what Asofwar builds, how actively, and in which areas.

Both arrive on one page and must find their thing without being routed through the other's content.

## Product Purpose

https://asofwar.github.io/ is the index of Asofwar's own projects: one page listing each project with its kind, summary, status, stack, platforms, latest release and links.

Success, as confirmed by the owner:

1. A visitor finds the fresh release of the project they need in seconds.
2. A visitor can get in touch (issues, requests, offers).
3. The site works as a living chronicle: it shows on its own that releases keep shipping.

## Positioning

The page maintains itself from real GitHub data: release versions, dates and release notes are pulled on every build (every 6 hours), and new projects are discovered weekly and added by an automated agent. What it shows is what actually shipped, not a hand-curated showcase that goes stale.

## Operating Context

- Static site on GitHub Pages, built by `scripts/build.py` from `data/projects.json` + `template.html`; workflows in `.github/workflows/`.
- `discover.yml` (Sunday 18:00 UTC) snapshots new public repositories into `data/candidates.json`; a Claude cloud routine (Monday 07:00 UTC) follows `agent/update-projects.md`, edits only `data/projects.json` and pushes to `main` without review.
- Card fields and validation rules: `README.md` («Поля карточки») and `scripts/schema.py`.
- Projects span routers (OpenWrt), Android apps, a game client and server tooling for Ragnarok Online, local LLM serving, Windows utilities and game ports.

## Capabilities and Constraints

- No frameworks or npm build step; Python standard library only in scripts (the cloud agent may run an older python3); vanilla CSS/JS, CSS and JS are inlined into the page.
- Content comes from data: any new UI must keep working when the agent adds cards, and new card fields must be optional and registered in `scripts/schema.py`.
- Must stay fast and accessible: Lighthouse 100 in all four categories on mobile and desktop as of 2026-10-21.
- Light and dark themes follow the system setting; print must produce complete pages.
- Contact channel today is GitHub only. Projects without a public repository (GSM-Пульт, AvangardRO, AVAAI) have no issue tracker; whether to publish another channel is an open decision for the owner.

## Brand Commitments

- Name: Asofwar (logo set as «ASOF/WAR»).
- Language: Russian only for UI and copy.
- The visual identity approved by the owner is original and must not imitate projectugarte.com, which inspired the idea of the site.
- Projects built around other companies' games (e.g. SpeedBreaker HLE) are presented with restraint: no publisher or game brands, logos or marketing language.
- Git history: commits are authored by Asofwar only, with no AI attribution.

## Evidence on Hand

- Project facts: `data/projects.json`; releases and release notes come live from GitHub Releases.
- Assets: `img/favicon.svg`, `img/apple-touch-icon.png`, `img/og.png`; generative per-project «plates» are produced by `build.py`.
- There are no testimonials, user counts, download statistics, clients or press. Do not invent them.

## Product Principles

1. Truth from data: every number, version and date on the page is computed from GitHub, never typed by hand.
2. The download is one step away: a visitor who knows what they want reaches the release without reading the rest.
3. Zero upkeep: anything new must keep working when the agent adds or changes cards unattended.
4. Show activity, don't claim it: the release log and dates are the proof of momentum, not adjectives.
5. Restraint where content touches third-party IP.

## Accessibility & Inclusion

WCAG AA contrast in both themes, full keyboard access with visible focus, `prefers-reduced-motion` honoured, readable without JavaScript and in print.

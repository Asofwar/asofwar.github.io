---
name: Asofwar — индекс проектов
description: Self-updating project index styled as an engineering datasheet
colors:
  signal-orange: "#ff4f1f"
  signal-ink: "#c4380f"
  paper: "#f3f1ec"
  paper-shade: "#ebe8e0"
  ink: "#16161a"
  ink-soft: "#4a4944"
  muted: "#6b685f"
  rule: "#d6d2c8"
  rule-strong: "#b3ae9f"
  status-live: "#2f9e5b"
  status-dev: "#d49a00"
  status-research: "#6a6ad8"
  night-paper: "#111110"
  night-ink: "#ecebe6"
  night-signal: "#ff6a3d"
  night-signal-ink: "#ff8a63"
typography:
  display:
    fontFamily: "Unbounded, \"Unbounded Fallback\", \"Segoe UI\", sans-serif"
    fontSize: "clamp(40px, 12.5vw, 160px)"
    fontWeight: 800
    lineHeight: 0.92
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "Unbounded, \"Unbounded Fallback\", \"Segoe UI\", sans-serif"
    fontSize: "44px"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Unbounded, \"Unbounded Fallback\", \"Segoe UI\", sans-serif"
    fontSize: "30px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  body:
    fontFamily: "\"Golos Text\", \"Golos Fallback\", -apple-system, \"Segoe UI\", Roboto, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.6
  lead:
    fontFamily: "\"Golos Text\", \"Golos Fallback\", -apple-system, \"Segoe UI\", Roboto, sans-serif"
    fontSize: "20px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "\"JetBrains Mono\", \"Mono Fallback\", Consolas, Menlo, monospace"
    fontSize: "12px"
    fontWeight: 400
    letterSpacing: "0.12em"
  mono:
    fontFamily: "\"JetBrains Mono\", \"Mono Fallback\", Consolas, Menlo, monospace"
    fontSize: "13px"
    fontWeight: 400
rounded:
  none: "0"
  dot: "50%"
spacing:
  gutter: "24px"
  column-gap: "32px"
  row: "32px"
  section: "96px"
  section-mobile: "64px"
components:
  badge-new:
    backgroundColor: "{colors.signal-orange}"
    textColor: "{colors.ink}"
    typography: "{typography.mono}"
    rounded: "{rounded.none}"
    padding: "3px 7px"
  link-action:
    textColor: "{colors.signal-ink}"
    typography: "{typography.mono}"
  board:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "16px 18px"
  ticker:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    typography: "{typography.mono}"
    padding: "14px 0"
  plate:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.none}"
    size: "132px"
  status-dot:
    rounded: "{rounded.dot}"
    size: "8px"
---

# Design System: Asofwar — индекс проектов

## Overview

**Creative North Star: "The Datasheet"**

The site reads like the technical datasheet of a component family: numbered positions, spec tables, hairline rules, a mono caption over every value. Each project is an item in an index, not a card in a gallery; its facts (status, version, stack, platforms, upstream) sit in a key/value table exactly as they would in a part's spec sheet. The visitor reads data, not adjectives.

The mood is precise and restrained. Generous whitespace, one accent, no decoration that does not carry information. The only ornaments are functional ones that belong to the datasheet world: a faint 40 px drafting grid behind the hero, a generative circuit «plate» per project, and a running release ticker that behaves like a departure board. Dark mode is the same sheet printed in negative, not a different mood.

The identity is the owner's own and must not drift toward the portfolio site that inspired the idea (projectugarte.com): no centred hero with pill badge and rounded cards, no soft shadows.

**Key Characteristics:**
- Paper, ink and one signal colour; status colours only as 8 px dots.
- Three type voices: wide grotesk for names, humanist sans for prose, mono for every label and number.
- Square corners everywhere, hairline and 2 px ink rules instead of boxes and shadows.
- Numbered index rows with a fixed column grid (number, plate, text, spec).
- Motion only where it signals life: ticker, a flowing trace on hover, a short reveal.

## Colors

A warm off-white paper with near-black ink, cut by a single Signal Orange; everything else is greys of the same warm family.

### Primary
- **Signal Orange** (#ff4f1f; night #ff6a3d): the mark square, the slash in ASOF/WAR, the «Новый» badge background, the live trace on every plate, ticker bullets, title underline on hover, the `:target` stripe. It marks what is alive or new.
- **Signal Ink** (#c4380f; night #ff8a63): the text-safe shade of the accent for small text on paper: action links («Скачать →»), release versions in the log, fresh release dates, hover and focus states, the focus ring (2 px outline, 3 px offset). 4.75:1 on paper.

### Neutral
- **Paper** (#f3f1ec; night #111110): page background and the fill of plates and the board.
- **Paper Shade** (#ebe8e0; night #1a1a18): reserved quiet surface tone.
- **Ink** (#16161a; night #ecebe6): text, headings, 2 px section rules, board frame, ticker band, plate chips and traces.
- **Ink Soft** (#4a4944; night #b9b7ae): lead paragraph, summaries, release notes, «github.com/» prefix.
- **Muted** (#6b685f; night #8d8b81): mono labels, row numbers, dates, secondary links. 4.93:1 on paper.
- **Rule** (#d6d2c8; night #2b2a27) and **Rule Strong** (#b3ae9f; night #4a4842): hairlines between rows, dashed spec dividers, plate frames, plate grid dots, link underlines.
- **Grid** (ink at 5%; night 4.5%): the drafting grid behind the hero.

### Status
- **Live Green** (#2f9e5b), **Dev Amber** (#d49a00), **Research Violet** (#6a6ad8): only as the 8 px dot before the status word in the spec table. Never as text, fills or borders.

### Named Rules
**The One Signal Rule.** Signal Orange is the only chromatic accent; it marks liveness and newness and covers a few percent of any screen. Status colours never grow beyond their dot.

**The Small-Text Ink Rule.** Orange text at body or label size always uses Signal Ink, never Signal Orange; Signal Orange is for fills, strokes, glyphs and display-size marks.

## Typography

**Display Font:** Unbounded (700–800), metric fallback «Unbounded Fallback» (Arial Bold, size-adjust 132%)
**Body Font:** Golos Text (400–500), metric fallback «Golos Fallback» (Arial, 105.9%)
**Label/Mono Font:** JetBrains Mono (400–500), metric fallback «Mono Fallback» (Consolas, 109.1%)

All three are self-hosted Latin + Cyrillic subsets in `assets/fonts/`; the fallbacks are tuned so the swap does not shift the layout.

**Character:** a wide, heavy grotesk names things; a calm humanist sans explains them; a mono annotates every value like a caption on a drawing.

### Hierarchy
- **Display** (800, 14.4cqi of the hero width ≈ clamp(40px, 12.5vw, 160px), 0.92, −0.035em): only the ASOF/WAR wordmark, sized to fill the content width on one line.
- **Headline** (700, 44px, 1.1, −0.02em; 34px under 600px): section names («Индекс», «Журнал», «Контакт»). The contact link uses the same face at clamp(34px, 9.5vw, 72px).
- **Title** (700, 30px, 1.2, −0.01em; 24px under 600px): project names in the index; board figures at 40px (32px mobile).
- **Lead** (400, 20px, 1.5; 17px mobile, max 620px): the one introductory paragraph.
- **Body** (400, 16px, 1.6, max 62ch): summaries; spec values at 14px; release notes 14px/1.45.
- **Label** (400, 11–12px, 0.08–0.12em, UPPERCASE): section labels («01 — Проекты»), project kind, spec keys, board captions.
- **Mono** (400–500, 13–14px): row numbers, links, dates, versions, ticker, nav.

### Named Rules
**The Caption Rule.** Every number, date, version, key and navigational link is set in JetBrains Mono; prose never is.

**The Wide-for-Names Rule.** Unbounded is reserved for names (the wordmark, section titles, project titles, the contact address, board figures). Never for running text or labels.

## Layout

A single 1200 px column (24 px gutters) on paper. The hero spans the full width with the wordmark on top, then the lead and a two-cell «board» (340 px) side by side; a faint 40 px drafting grid fades out behind it.

The project index is a strict four-column row: number (48 px), plate (132 px), text (fluid), spec table (300 px, separated by a hairline), with 32 px gaps and 32 px vertical padding per row. The release log above 960 px aligns to the same columns: date under number+plate, project and note under text, version under spec, with the same vertical hairline. Sections open with a 96 px top space (64 px on phones) and a heading bar: title left, mono label right, 2 px ink rule under it.

Breakpoints: ≤960 px the hero stacks and rows become plate (88 px) + text with the spec table below; ≤600 px plate shrinks to 64 px beside the number, text and spec go full width, log rows put the version under the project; ≤380 px the top bar tightens. Header links are 44 px tall on phones.

### Named Rules
**The Shared Column Rule.** Everything that lists projects or releases sits on the index grid; a new list aligns to number / plate / text / spec rather than inventing its own columns.

## Elevation & Depth

Flat. There are no shadows and no layered surfaces: depth is expressed with rules (1 px hairlines, 2 px ink section rules, a 1 px ink frame on the board) and with the inverted ink band of the ticker. The only shadow-like effect is a 3 px inset Signal Orange stripe on top of a `:target` row, which is a marker, not elevation.

### Named Rules
**The Flat Sheet Rule.** Surfaces never lift. If something needs separation, draw a rule; if it needs emphasis, invert it to ink or mark it with Signal Orange.

## Shapes

Square. Every box, badge, plate, board and band has 0 radius; the only round shapes are the 8 px status dots, the plate pads, and the ● ticker bullets. Borders are hairlines in Rule, dashed Rule between spec rows, and 2 px Ink under section headings and above the footer.

## Components

### Index row (signature)
Precise and quiet; the row is the unit of the site.
- **Structure:** mono number (a permalink, `#p-<id>`), generative plate, kind label + title + summary + links, spec table.
- **Title:** a link to the project's primary destination; on hover/focus a 2 px Signal Orange underline grows from the left (0.25 s).
- **Target:** when opened by permalink, a 3 px Signal Orange inset stripe on top and the number in Signal Ink.
- **Links:** primary action in Signal Ink mono («Скачать →»), secondary «Код ↗» in Muted; underline on hover.

### Plate (signature)
A deterministic 6×6 circuit drawn from the project id: dot grid in Rule Strong, ink traces and pads, a square ink chip with an orange dot, and exactly one trace in Signal Orange. 132 px with a 1 px Rule frame (88 px tablet, 64 px phone). On row hover or keyboard focus the orange trace starts flowing (dashed, 0.7 s loop). Decorative: `aria-hidden`.

### Spec table
Key/value rows: mono uppercase key (11px, Muted) in a 92 px column, value at 14px; dashed Rule between rows. Status shows an 8 px colour dot then the word; the version is an underlined link to the release, followed by its date (Signal Ink when the release is fresh).

### Board
Two figures and the latest release in a 1 px ink frame with ink dividers, square corners: mono caption on top, Unbounded figure pinned to the bottom so neighbouring figures share a baseline.

### Ticker
Full-bleed ink band, paper mono text, 13px, 0.06em tracking; items separated by a Signal Orange ●. Scrolls continuously (48 s), pauses on hover, becomes a static scrollable strip under reduced motion.

### Badge «Новый»
Signal Orange fill, Ink text, mono 11px medium, 0.08em, padding 3px 7px, square. Only for projects added within the last 30 days.

### Navigation
Sticky top bar on paper with a hairline bottom rule: the mark (12 px orange square + «ASOFWAR» in Unbounded 15px) on the left; mono links with muted section numbers on the right, Signal Ink on hover.

### Release log row
Mono date, project name (Golos 500) with a release note under it in Ink Soft, and the version in Signal Ink mono with ↗. Same-day releases of one project collapse into «A–B · N».

## Do's and Don'ts

### Do:
- **Do** keep every corner square (0 radius); only status dots and plate pads are round.
- **Do** use Signal Ink (#c4380f light / #ff8a63 dark) for any orange text smaller than display size.
- **Do** set every label, number, date, version and nav link in JetBrains Mono, and every name in Unbounded.
- **Do** separate content with rules (1 px Rule hairlines, 2 px Ink section rules), not with boxes or shadows.
- **Do** place new lists of projects or releases on the index grid (48 / 132 / fluid / 300 px, 32 px gaps).
- **Do** give every motion a reduced-motion fallback and keep the page complete without JavaScript and in print.

### Don't:
- **Don't** add box-shadows, gradients on surfaces, or rounded cards.
- **Don't** introduce a second accent colour or use status colours beyond their 8 px dot.
- **Don't** imitate the projectugarte.com look: centred hero with pill badge, soft rounded cards, generic portfolio grid.
- **Don't** use publisher or game logos and brand imagery for projects built around other companies' games.
- **Don't** set prose or summaries in mono, or labels in Unbounded.

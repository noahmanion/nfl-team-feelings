---
phase: 13
slug: explore-charts-win-totals-display
status: approved
reviewed_at: 2026-11-11
shadcn_initialized: false
preset: none
created: 2026-11-11
---

# Phase 13 — UI Design Contract

> This phase adds the `#/explore` page with two opinionated scatters (EXPL-02, EXPL-03), a "Preseason expectations" block on the team page (DATA-03), and four cheap leftovers from the Phase 12 UI review (#4, #7, #8, #9). It **extends** the Phase 12 contract (`12-UI-SPEC.md`). Tokens, type scale, `plotTheme.ts`, `ChartFrame`, `TeamLogo`, era names and the 375px rules all carry over unchanged unless this file names a change. All decisions in `13-CONTEXT.md` (D-01..D-27) are locked. This file sets final values for everything left to discretion.

Scope: `web/` plus the one display-only `pipeline/src/fgs/export.py` addition (D-17). There are no score changes, and the golden pin `3ac3c2b5…` must not change.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none. Svelte 5 + Vite with hand-rolled CSS tokens in `web/src/app.css` (Phase 12). The shadcn gate doesn't apply because this isn't a React project. |
| Preset | not applicable |
| Component library | none |
| Icon library | none. Text glyphs ▲ ▼ – → ← · and the existing mood emoji. Team logos are content. |
| Font (text/UI) | Inter Variable (`@fontsource-variable/inter` 5.3.0), unchanged |
| Font (numbers/annotations) | IBM Plex Mono 400/600 (`@fontsource/ibm-plex-mono` 5.3.0), unchanged |
| Charts | Observable Plot 0.6.19 via `web/src/lib/plotTheme.ts` (`withTheme`, `valueAxis`, `baseAxis`, `teamStroke`) |
| New npm packages | none |

---

## Spacing Scale

The Phase 12 tokens are reused verbatim. No new spacing tokens.

| Token | Value | Usage in this phase |
|-------|-------|---------------------|
| `--space-xs` | 4px | Page headline-to-dek gap; marker-to-label gap in the win-totals legend; ChartFrame source-to-notes gap |
| `--space-sm` | 8px | Table cell vertical padding; legend row padding; `<details>` top margin under the chart; mobile table horizontal padding |
| `--space-md` | 16px | Dek-to-Scrubber gap; table cell horizontal padding (≥640); number-line-to-legend gap |
| `--space-lg` | 24px | Scrubber-to-first-chart gap |
| `--space-xl` | 32px | Gap between the two Explore ChartFrames (each is a rule-topped section); team page section gap |
| `--space-2xl` | 48px | Unchanged (header top margin ≥1024, team page column gap) |
| `--space-3xl` | 64px | Unchanged (bottom page padding ≥1024) |

Size tokens are unchanged: `--tap-min` 44px, `--content-max` 960px, `--prose-max` 680px, `--score-cell` 56px, `--stripe-width` 4px, `--radius-md` 8px (controls only).

Exceptions (all multiples of 4 unless noted):
- **Scatter logo marks:** 28px at chart width ≥640 and 20px below. The pinned team gets +8, so 36px or 28px.
- **Inside Plot only** (SVG coordinates, not layout spacing):
  - Margins: `marginTop` 28, `marginRight` 16 (record chart ≥640: plus the measured band-label gutter), `marginBottom` 36, `marginLeft` 48.
  - The ring radius is `size/2 + 3`, the dark disc radius is `size/2 + 2`, the corner-label inset is 8, and the OLS label `dy` is −8.
- **Number line** (team page): track 2px, Vegas tick 2×20px, model/pace markers 12px. These are graphic sizes, not spacing.
- All tap targets (`<summary>`, table links, nav item) are at least 44px.

---

## Typography

The Phase 12 scale is reused verbatim. There are 4 reading sizes plus the locked mono micro annotation size, Inter at 400/700, and Plex Mono at 400/600. No new `font-size` literals are allowed. Plot `fontSize` uses `CHART_FONT_PX` (12) or `LABEL_FONT_PX` (14) only.

| Role | Token | Size | Weight | Line height | Used for in this phase |
|------|-------|------|--------|-------------|------------------------|
| Display | `--text-display` | 28px | Inter 700 | 1.1 | none new |
| Heading | `--text-heading` | 20px | Inter 700 | 1.25 | Explore page h2 "Explore"; both ChartFrame headlines; "Preseason expectations" headline |
| Body | `--text-body` | 16px | Inter 400 | 1.5 | Page dek, chart deks, empty-state text |
| Label | `--text-label` | 14px | Inter 400 / mono 400 & 600 | 1.4 | `<summary>` "Show as table"; table team names; win-totals legend labels (Inter 400) and values (mono 600); table numbers (mono 400); table rank (mono 600) |
| Micro | `--text-micro` | 12px | mono 400, UPPERCASE, 0.04em | 1.4 | Table column headers; SOURCE/NOTES footers; tick labels; axis end labels; quadrant/zone labels; tooltip text; number-line tick labels |

Weights: Inter is used only at `--weight-regular` 400 and `--weight-bold` 700. Plex Mono is used only at 400 and `--weight-semibold` 600 (table ranks, legend values, Delta, the pinned team abbreviation in the logo-off fallback).

Every number (EPA, success rate, win %, score, gap, record, wins, pace, Vegas line, rank) uses `.num` / mono `tabular-nums`. The minus sign in signed values is U+2212 (`−`), and positive values carry an explicit `+`.

Number formats (put these in `lib/explore.ts` and `lib/format.ts`, with tests):

| Value | Ticks | Tooltip / table / legend |
|-------|-------|--------------------------|
| EPA/play | 2 dp signed: `+0.10`, `0.00`, `−0.05` | 3 dp signed: `+0.123` |
| Success rate | — | 1 dp: `48.2%` |
| Win % | integer: `0%`, `25%`, `50%`, `75%`, `100%` | 1 dp: `62.5%` |
| Feel-good score | integer `0..100`, ticks every 20 | integer |
| Gap vs line | — | 1 dp signed + unit: `+8.4 pts`, `−3.1 pts` |
| Wins (Vegas, model, pace) | integer ticks | 1 dp: `6.5`, `12.8`. A finished season shows wins as an integer, or `.5` if there were ties |

---

## Color

### Core tokens (unchanged from Phase 12)

| Role | Token | Light | Dark | Usage |
|------|-------|-------|------|-------|
| Dominant (60%) | `--bg` | `#ffffff` | `#141414` | Page, chart areas, tables, tooltip fill |
| Secondary (30%) | `--surface` + rules | `#ffffff` / `--border` `#e3e3e3` / `--rule-strong` `#222222` / `--grid` `#e6e6e6` | `#1c1c1c` / `#333333` / `#ededed` / `#2e2e2e` | Scrubber bar, section rules, table rules, tier diagonals, number-line track |
| Accent (10%) | `--accent` | `#1f5fbf` | `#8db4ff` | Reserved list below |
| Destructive | `--danger` | `#b3362c` | `#f2877b` | Not used. This phase has no destructive actions. |
| Up / Down | `--up` / `--down` | `#1e7a4c` / `#b3362c` | `#5fbf8a` / `#f2877b` | Rank-delta text (D-24); gap-vs-line sign in the record table |
| Muted text | `--text-muted` | `#6b6b6b` | `#a3a3a3` | Deks, ticks, crosshairs, OLS line, quadrant/zone labels, empty-state text |
| Logo disc | `--logo-disc` | `transparent` | `#f2f2f2` | Dark-mode disc under each scatter logo |

### Accent reserved for (unchanged list; no new uses)

1. The `:focus-visible` outline on every focusable element, including the new `<summary>`, table links and SVG (chart) focus
2. Text links: table team links on Explore, plus all existing links
3. The current nav item's 2px underline. "Explore" gets it on `#/explore*`.
4. The Scrubber's slider track/thumb and the "Latest" button fill (reused unchanged)
5. The "In progress" and "Still going" badges
6. The my-team row outline plus tint. On Explore this applies to the pinned team's **table row**. The chart ring uses the team color, not accent.
7. The MethodologyChart composite dot
8. The Copy link button text

Accent is **never** used for scatter marks, crosshairs, the OLS line, diagonals, number-line markers, quadrant/zone labels, or the `<summary>` text (which is `--text`).

### Chart colors (this phase)

| Element | Value |
|---------|-------|
| Tier diagonals (EPA) | `var(--grid)`, 1px, solid, unlabeled |
| League-average crosshairs (EPA) | `var(--text-muted)`, 1px, dashed `4,3` (the Phase 12 reference-rule style) |
| OLS "typical score" line (record) | `var(--text-muted)`, 1.5px, dashed `4,3` |
| Mood band rects (record) | `var(--mood-n)` at `fillOpacity` 0.10 (light) / 0.14 (dark), the same as HistoryChart |
| Gridlines | Record chart: y only, `var(--grid)` via `valueAxis`. EPA chart: none (the diagonals are the grid). |
| Pinned-team ring | `highlightColor(team)` (≥3:1 vs `--bg`, Phase 12 fix), 2px stroke, no fill |
| Non-pinned logos when a team is pinned | opacity 0.5 |
| Logo-off fallback dot | team primary via `teamStroke(primary)`, r 6, plus abbreviation in `var(--text)` mono 12 |
| Tooltip | fill `var(--bg)`, stroke `var(--border)`, text `var(--text)`, mono 12 |
| Win-totals markers | Vegas tick `var(--text)`; model ring `var(--text-muted)` on `var(--bg)`; pace dot `highlightColor(team)` |
| Win-totals track | `var(--border)` |

---

## Route & Navigation Contract

- Routes:
  - `#/explore` shows the latest week.
  - `#/explore/{season}/{week}` shows a historical week.
  - Add a `Route` kind `{ kind: 'explore'; season?: number; week?: number }` and `exploreHash(season?, week?)` in `lib/router.ts`, with tests.
  - An invalid season or week `replace`s to `#/explore` silently (D-01).
  - A Scrubber change to the latest season and latest week writes `#/explore`, not the explicit form, the same way the board writes `#/` for latest.
- SiteHeader:
  - `current` union gains `'explore'`.
  - Nav order: `Board · Mood over time · Explore · Records · How it works`.
  - The new item uses the existing `<span class="item"><Sep /><a …></a></span>` wrapper and `aria-current="page"` when current.
  - No other nav changes. At <640px the dots stay hidden and the column gap stays 16px (Phase 12 fix #3).

---

## Layout Contract: Explore page (`ExplorePage.svelte`)

Global frame: the same as other pages (≤640px centered below 1024, `--content-max` 960 at ≥1024).

Order, top to bottom:

```
<article class="explore" aria-labelledby="explore-heading">
  <header class="page-head">
    <h2 id="explore-heading">Explore</h2>                 heading 20/700
    <p class="dek">{page dek}</p>                          body 16 muted, max-width --prose-max, margin-top --space-xs
  </header>
  <Scrubber … />                                           unchanged component, margin-top --space-md
  <section class="block" aria-labelledby="epa-heading">    margin-top --space-lg (first section only, no top rule)
    <ChartFrame id="epa-heading" level={3} …>{chart or empty}</ChartFrame>
    <details class="as-table">…</details>                  margin-top --space-sm
  </section>
  <section class="block" aria-labelledby="rve-heading">    border-top 1px --border, padding-top --space-md, margin-top --space-xl
    <ChartFrame id="rve-heading" level={3} …>…</ChartFrame>
    <details class="as-table">…</details>
  </section>
</article>
```

- Both charts take the full content width at every breakpoint (no side-by-side layout).
- Chart height for both scatters: `clamp(width × 0.8, 320, 560)` (D-13). At 960 → 560, at 343 (375 viewport) → 320.
- Chart container: `inline-size: 100%; min-width: 0; overflow: hidden`. SVG is `display:block; max-inline-size:100%`. No horizontal scroll at 320–375px.
- Plot rendering follows the HistoryChart pattern: `bind:clientWidth`, build inside `$effect`, `container.replaceChildren(plot)`, and remove on cleanup. Re-render on scheme change (`matchMedia('(prefers-color-scheme: dark)')`), width change, pin change and data change.
- SVG gets `role="img"`, an `aria-label` summary (see Copywriting) and `tabindex="-1"`. Keyboard and screen-reader access goes through the table (D-16a), not the SVG.

### Loading / empty / error (both charts, per frame)

| State | Contract |
|-------|----------|
| Loading | The ChartFrame headline renders. The body is a placeholder block of the computed chart height with 1px `--border` top and bottom rules, containing `Loading {season} {week label}…` (body muted, `role="status"`, centered). No spinner, no layout shift. Dek, footer and table are hidden. |
| Empty (week 0 / no games played, D-05) | Body becomes `.chart-empty`: min-height 160px, 1px `--border` top and bottom rules, body 16 muted, centered text. The dek and `<details>` are omitted; the footer stays. |
| EPA: season not in `meta.epa_seasons` | The same `.chart-empty` block, with its own copy (below). The record chart still renders. |
| EPA: season present but `seasonToDate` yields no teams for the week | `.chart-empty`, "through this week" copy (below). |
| Snapshot load error | One `StatusPanel` (variant error) **replaces both sections**. Actions are "Try again" (retry) and "Go to latest" (`#/explore`). |
| EPA file load error | `StatusPanel` inside the EPA frame body only, action "Try again". The record chart is unaffected. |

---

## Chart Contract: EPA scatter (EXPL-02, D-07..D-13)

| Property | Value |
|----------|-------|
| Data | `seasonToDate(loadEpa(meta, season), week)` joined to snapshot rows by franchise. Filter with `isActiveFranchise(F, season)`. |
| x | Offensive EPA/play. `baseAxis({ ticks, tickFormat: signed2 })`. Domain: data min/max padded by 0.03, then expanded outward to the nearest 0.05. |
| y | Defensive EPA/play **allowed**, with `reverse: true` (up = better defense). The data is not negated. Domain rule as for x. Ticks show the real signed values. `baseAxis` (no grid). |
| Tick spacing | 0.1 when the domain span is ≥0.3, else 0.05. Never more than 6 ticks per axis at <640 (drop to every other tick). |
| Axis end labels | No rotated titles. x: Plot `label: 'Offense EPA/play →'`, `labelAnchor: 'right'`, `labelArrow: 'none'`. y: `label: '↑ Defense, EPA/play allowed (flipped)'`, `labelAnchor: 'top'`, `labelArrow: 'none'`. Both mono 12 muted. |
| Tier diagonals | Lines of constant net = off − def for every multiple of 0.1 that crosses the domain. Draw them with `Plot.link` clipped to the frame (`clip: true`). `--grid` 1px. No labels. Drawn first. |
| Crosshairs | `ruleX([leagueOff])` and `ruleY([leagueDef])` (play-weighted league means from `lib/explore.ts`). `--text-muted`, dashed `4,3`, 1px. Drawn after the diagonals. |
| Quadrant labels | `Plot.text` with `frameAnchor` corners, inset 8, mono 12 muted, uppercase, `textAnchor` matching the corner. Top-right "Good at both"; bottom-right "All offense"; top-left "All defense"; bottom-left "Struggling on both". **Hidden below 400px chart width.** Drawn before the logos so logos sit on top. |
| Marks | Per team: in dark mode only, a `Plot.dot` disc first (`r = size/2 + 2`, fill `var(--logo-disc)`, no stroke), then `Plot.image` (`src: logoSrc(F)`, `width = height = size`; dark mode draws the image at `size × 0.76`). `size` = 28 (chart width ≥640) or 20. |
| Draw order of marks | Non-pinned teams first, pinned team last (on top). |
| Pinned team (D-10) | Size +8. A ring `Plot.dot` (`r = size/2 + 3`, `stroke: highlightColor`, `strokeWidth: 2`, `fill: 'none'`) is drawn under the image. Every other team's image and disc get `opacity: 0.5`. No pin, or the pinned team isn't in the data: everyone at 1.0. |
| Logos off (`VITE_LOGOS=off`) or `logoSrc` null | `Plot.dot` r 6, fill `teamStroke(primary)`, stroke `var(--bg)` 1px, plus `Plot.text` era abbreviation (mono 12, `var(--text)`, `dx: 8`, `textAnchor: 'start'`). The pinned team uses r 8 plus the ring rule, with its abbreviation at weight 600. No external URLs, ever. |
| Tooltip (D-11) | `Plot.tip(data, Plot.pointer({ x, y, title }))` with the multi-line title below. `fill: 'var(--bg)'`, `stroke: 'var(--border)'`, `fontSize: 12`. |
| Click (D-11) | `plot.value` pattern: listen to `input` to track the pointed datum, and on `click` with a non-null value call `go(teamHash(F, season, week))`, or `teamHash(F)` when viewing the latest week. Set the SVG `cursor: pointer` while a value is non-null. |
| Height | `clamp(width × 0.8, 320, 560)` |

Tooltip lines (exact, mono 12):
```
{era name}
Offense {+0.123} EPA/play · #{rank}
Defense {−0.045} allowed · #{rank}
Success {48.2%} off · {43.1%} def
{6–2} · {8} games
```
Ranks: offense descending, defense ascending (lowest allowed = #1). Ties share the lower number.

---

## Chart Contract: Record vs evidence (EXPL-03, D-14..D-16)

| Property | Value |
|----------|-------|
| Data | Snapshot rows for the season/week, filtered with `isActiveFranchise`. Rows with 0 games played are excluded. |
| x | Win % = (W + 0.5·T) / GP. Domain [0, 1]. `baseAxis({ ticks: [0, .25, .5, .75, 1], tickFormat: pct0 })`. End label `'Win % →'`, `labelAnchor: 'right'`, `labelArrow: 'none'`. |
| y | Feel-good score, domain [0, 100]. `valueAxis({ ticks: [0,20,40,60,80,100] })` (y gridlines in `--grid`). End label `'↑ Feel-good score'`, `labelAnchor: 'top'`, `labelArrow: 'none'`. |
| Mood bands | `Plot.rect` across x [0, 1] per `meta.bands` (`y1 = min`, `y2 = min(100, max + 1)`), fill `var(--mood-n)`, opacity 0.10 light / 0.14 dark. Drawn first. |
| Band labels | At chart width ≥640: in a right gutter (mono 12 muted, `dx` 10), the same as HistoryChart. `marginRight` = 16 + the measured label width (canvas measure, re-measured after `document.fonts.ready`). Below 640: none (the tooltip carries the mood label). |
| OLS line (D-15) | `fitLine(points)` in `lib/explore.ts` (least squares of score on win %; tested). Drawn from min to max observed win % only, with no extrapolation. `--text-muted`, 1.5px, dashed `4,3`. Not drawn when fewer than 3 teams or zero x-variance; the zone labels are hidden then too. |
| OLS label | `Typical score for this record`. Mono 12 muted, at the line's right end, `textAnchor: 'end'`, `dy: −8`. Hidden below 400px chart width. |
| Zone labels | Uppercase mono 12 muted with `frameAnchor` corners, inset 8. Top-left "Better than their record"; bottom-right "Worse than their record". Shown at all widths. |
| Marks / pin / logos-off / dark disc | Identical to the EPA chart (sizes, ring, 0.5 opacity, fallback dot plus abbreviation, disc). |
| Tooltip | Lines below. Same styling as the EPA chart. |
| Click | Same `plot.value` pattern → `teamHash(F, season, week)` or `teamHash(F)` on latest. |
| Height | `clamp(width × 0.8, 320, 560)` |
| Equation of the line | Not shown (discretion default). |

Tooltip lines (exact):
```
{era name}
{6–2} · {75.0%}
Score {71} · {emoji} {mood label}
{+8.4 pts} vs typical for this record
```

---

## Table View Contract ("Show as table", D-16a)

`<details class="as-table">` sits directly under each ChartFrame and is collapsed by default.

- `<summary>`: "Show as table". Inter 14, `--text`, native disclosure marker, `min-block-size: 44px`, `display: flex; align-items: center`, `cursor: pointer`, accent focus ring.
- The table sits inside a `div` with `overflow-x: auto; min-width: 0` as a safety net. With the column drops below, it fits at 343px without scrolling.
- `<table>`: `width: 100%`, `border-collapse: collapse`.
  - `thead th`: mono micro uppercase muted, `border-bottom: 1px solid var(--rule-strong)`, `padding: 0 16px 8px`, numeric headers right-aligned.
  - `tbody td`: `padding: 8px 16px` (≥640) or `8px 8px` (<640), `border-bottom: 1px solid var(--border)`. Numbers are right-aligned mono 400 14.
  - Rank: mono 600 14 muted.
  - Team cell: `TeamLogo` 20 + era abbreviation as a link (Inter 700 14, accent, to the same href as the mark click), plus the era name (Inter 400 14 muted, hidden <640, ellipsis).
- The pinned team's row gets the Phase 12 my-team treatment: 2px accent outline inset −2px plus a 6%/8% accent tint.
- `<caption class="visually-hidden">` holds the chart headline.

| Table | Columns (≥640) | Dropped <640 | Sort |
|-------|----------------|--------------|------|
| EPA | `#` · `Team` · `Off EPA` · `Def EPA` · `Net` · `Record` | `Record` | Net (off − def) descending. Discretion: this deviates from the "chart y" default because net is the tier ranking the diagonals encode. |
| Record vs evidence | `#` · `Team` · `Record` · `Win %` · `Score` · `Gap` | `Win %` | Score descending (the chart's y). Gap text in `--up` (positive) / `--down` (negative) / muted (|gap| < 0.5). |

---

## Component Contract: `WinTotals.svelte` (DATA-03, D-17..D-21)

Wrapped in `ChartFrame` (level 3, `id="expect-heading"`, headline "Preseason expectations"). `ChartFrame` gains an optional `source?: string` prop. When it's omitted the footer reads `SOURCE: NFLVERSE · FEEL-GOOD SCORE` exactly as before. Add a `chartFrame.test.ts` case for both.

Placement (D-21):
- **<1024:** after the "Why" section and before "Recent games", as its own rule-topped `section.block`.
- **≥1024:** the first item in the right column, above "Recent games", separated from it by the standard section rule plus `--space-xl`.

Anatomy:

```
ChartFrame (headline, dek, source, notes)
  .numline (aria-hidden="true")      height 40px, full width
     track: 2px --border, at y=12
     markers centered on the track at left = value / reg_games × 100% (clamped 0..100%)
     tick labels under the track at y=24: mono 12 muted
  ul.legend (margin-top --space-md)  rows: grid 16px | minmax(0,1fr) | auto, column-gap 8px,
                                    padding 8px 0, border-bottom 1px --border, align-items baseline
     [marker 12px] [label Inter 14 --text (+ muted suffix)] [value mono 600 14, right]
```

| Marker | Shape | Color | Shown when |
|--------|-------|-------|-----------|
| Vegas preseason | Vertical bar 2×20px | `var(--text)` | A `vegas_win_totals` entry exists for the season |
| Model preseason | 12px ring, 2px border | `var(--text-muted)` border, `var(--bg)` fill | `expectation.source[i] === 'model'` |
| Pace / final | 12px filled dot | `highlightColor(team)` | GP > 0 |

- Z-order: model, then Vegas, then pace on top.
- Number-line ticks: multiples of 4 that are ≤ `reg_games − 2`, plus `reg_games`. For 17 games that's `0 4 8 12 17`; for 16 games `0 4 8 12 16`.
- Labels are centered on their position, except the first is left-aligned and the last right-aligned.
- Pace = (W + 0.5·T) / GP × reg_games, 1 dp, computed in a pure helper (`lib/winTotals.ts`, tested): week 0, mid-season, finished, ties, and the 16-game 2022 BUF/CIN case.
- "Finished" means GP === reg_games.
- States:
  - Loading: `Loading expectations…` (label muted, `role="status"`) in place of the number line and legend.
  - `loadTeam` failure: the whole section is omitted (display-only extra; no second error panel on the team page).
  - No Vegas row and no expectation for the season: the section is omitted.

---

## Phase 12 Review Leftovers (D-22..D-25)

| # | Contract |
|---|----------|
| #4 Records width/ragged cells | `.records` drops `max-width: 680px` and uses the full content width (960 at ≥1024). The dek and footnote keep `max-width: var(--prose-max)`. Each `ol.rows` becomes `display: grid; grid-template-columns: 28px minmax(0, 1fr) max-content`. Each `li` and `a.row` use `grid-column: 1 / -1; display: grid; grid-template-columns: subgrid`, so the value column is one width per list. Value cells (`.big`) are right-aligned mono 600 20 with `min-inline-size: var(--score-cell)`, padding 0 8px. Shaded tint and 4px band edge are unchanged. Applies to all four lists at every width. |
| #7 History logo clipping | `HistoryChart` sets `marginTop: 24` when the end-of-line logo is drawn (`drawLogo`), else Plot's default 20. That leaves at least 12px above a 20px or 24px logo centered at y=100, so it isn't clipped at 375px. The y domain stays [0, 100], and nothing else moves. |
| #8 Rank delta | New `formatRankDelta(v)` in `lib/format.ts` returns `{ text, dir, aria }`. Positive → `▲1 spot` / `▲3 spots`, `dir: 'up'`, aria `Up 1 spot in rank`. Negative → `▼2 spots`, aria `Down 2 spots in rank`. 0 or null → `no change`, `dir: 'none'`, aria `No change in rank`. `Delta kind="rank"` renders this text (no `#` prefix) with `aria-label={aria}`, mono 600 14. Score deltas (`formatDelta`) are unchanged. Update `format.test.ts`. |
| #9 Callout action rows | The `CalloutCards` grid uses `align-items: stretch`. Each grid item (the `li`, if present) is `display: flex`, and `.card` is `flex: 1`, so cards in a row share a height. The existing `.actions { margin-top: auto }` then lines up the buttons along the bottom edge at 1280. Copy and markup are unchanged. |

Still deferred (log in SUMMARY): #5, #6 beyond the win-totals placement, #10, #11.

---

## Interaction & State Contract

| Interaction | Contract |
|-------------|----------|
| Scrubber on Explore | The same component and props as the board. A season change calls `go(exploreHash(season, carryWeek(...)))`; a week slider change calls `replace(...)`; "Latest" calls `go('#/explore')`. One season/week drives both charts (D-03). |
| Hover / pointer on marks | The Plot tip appears. No other hover styling on marks. |
| Click on mark | Navigates to the team page (see chart contracts). |
| Touch | Tap shows the tip (Plot pointer). A second tap on the same mark navigates. This is Plot's default `pointer` + `click` behavior and needs no custom code. |
| Keyboard | Tab skips the SVGs. The `<summary>` and the table links are reachable and carry the accent focus ring. |
| Pin change | Both charts re-render with the new highlight. The table row tint updates. |
| Dark mode | `prefers-color-scheme` only. Charts read CSS variables and re-render on the scheme `change` event (disc on/off). |
| Reduced motion | No animations are added. Plot renders statically. |
| Images | Same-origin `/logos/sm/{F}.png` only. `nohotlink.test.ts` must keep passing. |

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary CTA | No new buttons. The table toggle is `Show as table`. Mark clicks and table links go to the team page. Existing CTAs (`Latest`, `Try again`, `Go to latest`) keep their copy. |
| Empty state heading | none (inline chart empty state, no heading) |
| Empty state body (week 0 / no games, both charts) | `No games played yet in {season}. Pick a later week.` |
| Empty state body (EPA, season without pbp) | `No play-by-play efficiency data for {season}. Pick {first epa season} or later.` |
| Empty state body (EPA, no data through this week) | `No efficiency data through {week label} yet. Pick an earlier week.` |
| Error state (snapshot) | Title `Couldn’t load this week`, body `The data for {season} {week label} didn’t load. Try again, or jump to the latest week.`, actions `Try again` / `Go to latest` |
| Error state (EPA file) | Title `Couldn’t load efficiency data`, body `The play-by-play numbers for {season} didn’t load.`, action `Try again` |
| Destructive confirmation | none (this phase has no destructive actions) |

### New copy (exact strings; curly apostrophe ’, U+2212 minus, U+2013 en dash in records)

| Location | Copy |
|----------|------|
| Nav item | `Explore` |
| Explore h2 | `Explore` |
| Explore page dek (D-06) | `Two ways to check the board: how efficiently teams play, and how their record compares with the evidence.` |
| EPA headline | `How efficiently every team plays` |
| EPA dek | `Offense against defense in expected points added per play, {season} through {week label}. Efficiency is one input to the feel-good score, not the score itself.` |
| EPA dek, extra sentence when week ≤ 3 | ` Early-season efficiency is noisy: a single game can move a team a long way.` |
| EPA notes (D-12; sentence case per Phase 12 footer rule) | `EPA per play, season to date, garbage time filtered. Not adjusted for opponents. Defense axis is flipped: higher = fewer points allowed.` |
| EPA quadrant labels (rendered uppercase) | `Good at both` · `All offense` · `All defense` · `Struggling on both` |
| EPA axis labels | `Offense EPA/play →` · `↑ Defense, EPA/play allowed (flipped)` |
| EPA aria-label | `Scatter of offensive against defensive EPA per play for {n} teams, {season} through {week label}. Full values in the table below.` |
| Record headline | `Record vs evidence` |
| Record dek (D-16, generated) | `The {nick A} look better than their {W–L} record; the {nick B} look worse than theirs.` |
| Record dek fallback (OLS not drawn, or both extreme gaps < 1 pt) | `Win percentage against feel-good score, {season} through {week label}.` |
| Record notes | `Win % counts ties as half a win. The dashed line is the typical score for each record this week. Shaded bands are the mood labels.` |
| OLS label | `Typical score for this record` |
| Zone labels (rendered uppercase) | `Better than their record` · `Worse than their record` |
| Record axis labels | `Win % →` · `↑ Feel-good score` |
| Record aria-label | `Scatter of win percentage against feel-good score for {n} teams, {season} through {week label}. Full values in the table below.` |
| Table toggle | `Show as table` |
| Loading (Explore) | `Loading {season} {week label}…` |
| WinTotals headline | `Preseason expectations` |
| WinTotals dek: Vegas, in progress | `Vegas set the line at {line} wins. They’re on pace for {pace}.` |
| WinTotals dek: Vegas, finished | `Vegas set the line at {line} wins. They finished with {wins}.` |
| WinTotals dek: Vegas, week 0 | `Vegas set the line at {line} wins. No games yet.` |
| WinTotals dek: model only (1999–2002) | `The model expected {exp} wins. They’re on pace for {pace}.` / `… They finished with {wins}.` / `… No games yet.` |
| Legend: Vegas, 2003–2020 | `Vegas preseason (used in score)` |
| Legend: Vegas, 2021+ | `Vegas preseason (display only, not used in score)` |
| Legend: suffix when `line_type === 'preseason_open'` (muted) | ` · opening line, not the final preseason number` |
| Legend: model | `Model preseason (used in score)` |
| Legend: pace, in progress | `On pace for {pace} wins ({W–L[–T]} after {GP} games)` (value column `{pace}`) |
| Legend: pace, finished | `Finished {W–L[–T]}` (value column `{wins}`) |
| Legend: pace, week 0 | `No games yet.` (value column `–`, no marker) |
| WinTotals source (when a Vegas row shows) | `SOURCE: NFLVERSE (2003–2020) · COVERS / DRAFTKINGS (2021+)` |
| WinTotals source (model only) | default `SOURCE: NFLVERSE · FEEL-GOOD SCORE` |
| WinTotals notes: Vegas used in score | `The score uses this line, normalized to the league average.` |
| WinTotals notes: Vegas display only | `Shown for context. The score uses the model’s preseason expectation for this season.` |
| WinTotals notes: model only | `No Vegas line on file before 2003. The score uses the model’s preseason expectation.` |
| Rank delta (D-24) | `▲1 spot` · `▲{n} spots` · `▼1 spot` · `▼{n} spots` · `no change`; aria `Up {n} spot(s) in rank` / `Down {n} spot(s) in rank` / `No change in rank` |

Copy rules:
- The words "lucky", "unlucky" and "luck" never appear on the Explore page, in `ExplorePage.svelte`, in the chart components, or in `lib/explore.ts`. Add a vitest that greps those files, case-insensitive (D-15).
- "FiveThirtyEight", "538" and "fox" never appear (Phase 12 rule).
- Era names come from `eraName`/`eraText` for the viewed season. Washington's former name is never used.
- Records use an en dash (`6–2`, `6–2–1`). Signed numbers use `+` / U+2212.

---

## Component Inventory (this phase)

| File | Status | Notes |
|------|--------|-------|
| `src/lib/router.ts` (+test) | modify | `explore` route kind, `exploreHash` |
| `src/App.svelte` | modify | Route switch for `explore`, validation and silent fallback, `SiteHeader current="explore"` |
| `src/components/SiteHeader.svelte` | modify | "Explore" nav item, `'explore'` in the `current` union |
| `src/components/ExplorePage.svelte` | new | Page head, Scrubber, two sections, states |
| `src/components/EpaScatter.svelte` | new | Plot chart per the EPA contract |
| `src/components/RecordScatter.svelte` | new | Plot chart per the record contract |
| `src/components/ExploreTable.svelte` | new | `<details>` table (column config passed in) |
| `src/lib/explore.ts` (+test) | new | Joins, league means, `fitLine`, residuals, ranks, domains/ticks, empty checks, number formats, dek generation, the no-"luck" grep test |
| `src/lib/data.ts` | modify | `TeamFile` type, `loadTeam(meta, F)` (session cache keyed by `generated_at`, evict on failure) |
| `src/lib/winTotals.ts` (+test) | new | Pace, rows, labels, ticks |
| `src/components/WinTotals.svelte` | new | Number line plus legend in ChartFrame |
| `src/components/ChartFrame.svelte` (+`chartFrame.test.ts`) | modify | Optional `source` prop |
| `src/components/TeamPage.svelte` | modify | Insert WinTotals (placement per D-21) |
| `src/components/RecordsPage.svelte` | modify | #4 full width plus subgrid |
| `src/components/HistoryChart.svelte` | modify | #7 marginTop |
| `src/lib/format.ts` (+test), `src/components/Delta.svelte` | modify | #8 `formatRankDelta`, aria-label |
| `src/components/CalloutCards.svelte` / `CalloutCard.svelte` | modify | #9 stretch plus flex |
| `pipeline/src/fgs/export.py` (+`test_export.py`) | modify | D-17 `expectation` block, display-only; golden pin unchanged |

Gates (D-26/D-27): `npm test`, `npm run check` and `npm run build` pass under Node 24, and `cd pipeline && uv run pytest` passes. Playwright at 1280 and 375, light and dark: Explore latest, Explore 2025/10, Explore week 0, and team win totals for 2026, a 2021–2025 season and a 2003–2020 season. No horizontal scroll at 375. At most 6 screenshots in `screenshots/`.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| none (no shadcn, no third-party registries) | none | not applicable |

No new npm packages. No runtime third-party requests; logos and data are same-origin.

---

## Pre-population Sources

| Source | Decisions used |
|--------|----------------|
| 13-CONTEXT.md | D-01..D-27: routes, nav order, Scrubber reuse, data sources, empty states, axis orientation, logo sizes, crosshairs/diagonals/quadrants, pin treatment, tooltip fields, notes copy, height clamp, win %/score axes, OLS line and labels, dek template, tables, dark disc, export block, WinTotals labels/pace/placement/source, leftovers #4/#7/#8/#9, verification |
| 12-UI-SPEC.md | All tokens, type scale, weights, accent list, chart colors, ChartFrame anatomy, TeamLogo/disc rules, era-name rules, section-rule layout, 375px rules |
| 12-UI-REVIEW.md | Leftover items #4, #7, #8, #9 and their findings |
| research/FEATURES.md (D1, D2, T11) | Tier-chart conventions, "record vs evidence" framing, the never-"luck" rule, "Vegas said 6.5, on pace for 11" story, axis labels at the axis end |
| Codebase (`app.css`, `plotTheme.ts`, `ChartFrame.svelte`, `HistoryChart.svelte`, `SiteHeader.svelte`, `RecordsPage.svelte`, `CalloutCard.svelte`, `format.ts`) | Exact current values, the Plot-in-`$effect` pattern, the nav `.item` pattern, the records 680px cap (#4 cause), `.actions { margin-top: auto }` already present (#9 needs stretch) |
| Claude's discretion (autonomous) | Headline copy, tick/format rules, margins, ring/disc radii, band-label gutter ≥640, OLS label hide <400, table columns and EPA sort by net, number-line marker shapes, WinTotals deks/notes, empty/error copy, loadTeam failure = omit section |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending

## Checker notes (approved 2026-11-11)

- The NOTES casing is sentence case on purpose. D-12's wording is unchanged, and the `NOTES:` prefix stays uppercase per the Phase 12 footer rule.
- The records cells (D-22) use `max-content` subgrid columns instead of fixed widths. The intent, one consistent width per list, is unchanged.
- Focal point when no team is pinned: the diagonals, crosshairs and reference line anchor the eye, and the logos carry the data.

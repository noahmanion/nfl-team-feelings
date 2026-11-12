# Phase 13: Explore Charts & Win Totals Display - Research

**Researched:** 2026-11-11
**Domain:** Svelte 5 + Observable Plot 0.6.19 scatter charts (logo marks, pointer/tip, click-through), one display-only Polars export field, small CSS fixes
**Confidence:** HIGH. Almost everything was verified against the repo's code, the installed Plot 0.6.19 source in `web/node_modules`, and the committed data files.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Area 1: Explore page, route & controls
- D-01 Routes: `#/explore` (latest) and `#/explore/{season}/{week}`. New `explore` Route kind in `lib/router.ts` + `exploreHash(season?, week?)`, with router tests. Invalid season/week falls back to `#/explore` (latest) silently, the same way a bad team week goes to the team's latest page.
- D-02 Nav: add "Explore" to `SiteHeader` between "Mood over time" and "Records" (Board · Mood over time · Explore · Records · How it works), with the existing `.item`/`Sep` wrapping pattern and `aria-current`.
- D-03 Controls: reuse the existing `Scrubber.svelte` unchanged (season select + week slider + "Latest" button) at the top of the page. Season changes use `carryWeek` like the board. Week slider updates with `replace`, season with `go`. One season/week drives both charts.
- D-04 Data: rows come from `latest.json` (latest) or `loadSeason` (other weeks), the same session-cached loaders the board uses. EPA comes from `loadEpa(meta, season)` + Phase 11's `seasonToDate(file, week)` (play-weighted). Only seasons in `meta.epa_seasons` get the EPA chart; otherwise it shows an empty state. HOU before 2002 is filtered with `isActiveFranchise`.
- D-05 Week 0 (preseason) and weeks with no played games: both charts show a short empty state ("No games played yet in {season}. Pick a later week.") instead of a chart of 32 logos at the origin.
- D-06 New page component `ExplorePage.svelte` with a page headline ("Explore") and gray dek ("Two ways to check the board: how efficiently teams play, and how their record compares with the evidence."). Pure logic (joins, league means, regression line, residuals, ranks, empty-state checks) lives in a new `lib/explore.ts` with vitest tests.

#### Area 2: EPA scatter (EXPL-02)
- D-07 X = offensive EPA/play; Y = defensive EPA/play allowed with the **axis reversed** (`y: { reverse: true }`), so up means better defense. The data is not negated. Tick labels show the real signed values (e.g. `+0.10`, `−0.05`).
- D-08 Marks: team logos as Plot `image` marks, 28px at width ≥ 640 and 20px below. Every logo uses the local `/logos/sm/{F}.png` path (`logoSrc` from lib), and `VITE_LOGOS=off` falls back to a `dot` mark in the team's primary color plus the abbreviation (no external URLs).
- D-09 Reference lines: dashed league-average crosshairs (play-weighted league mean for offense and defense) in `--text-muted`. Faint net-EPA tier diagonals (slope 1, i.e. constant off − def) at 0.1 EPA/play spacing in `--grid`, with no labels. Quadrant labels in the corners, mono micro, muted: top-right "Good at both", bottom-right "All offense", top-left "All defense", bottom-left "Struggling on both". Hide the quadrant labels below 400px if they collide.
- D-10 My-team highlight: when a team is pinned, its logo is drawn larger (+8px) with a ring in its `highlightColor` and other logos drop to 0.5 opacity. No pin means all logos at full opacity.
- D-11 Tooltip: Plot `tip` on pointer, showing era name, Off EPA/play and rank, Def EPA/play allowed and rank, success rates, record, and games counted. Clicking a mark opens `teamHash(F, season, week)` (or `teamHash(F)` when on the latest week). Implemented with the `plot.value` input pattern.
- D-12 Honesty notes (Pitfall 12). The ChartFrame NOTES read: "EPA PER PLAY, SEASON TO DATE, GARBAGE TIME FILTERED. NOT ADJUSTED FOR OPPONENTS. DEFENSE AXIS IS FLIPPED: HIGHER = FEWER POINTS ALLOWED." The dek states that efficiency is one input to the score, not the score itself. When week ≤ 3, an extra dek sentence warns that early-season EPA is noisy.
- D-13 Size: height = clamp(width × 0.8, 320, 560). Square-ish, no horizontal scroll at 375px.

#### Area 3: Record vs evidence scatter (EXPL-03)
- D-14 X = win% = (W + 0.5·T) / games played, from the snapshot row (regular-season record), axis 0–100%. Y = feel-good score 0–100. Mood bands from `meta.bands` appear as faint horizontal background rects (low-alpha `--mood-N` via `color-mix`), the same encoding as the board.
- D-15 Perception gap: draw an ordinary least-squares reference line of score on win% across the teams shown that week (computed in `lib/explore.ts`, tested), labeled "Typical score for this record". Zone labels in plain words: above the line "Better than their record", below it "Worse than their record". Never "lucky"/"unlucky"/"luck" anywhere on the page (v1 luck weight ≈ 0). A unit test greps the Explore component and lib for those words.
- D-16 The dek is generated from residuals: "The {nick A} look better than their {W–L} record; the {nick B} look worse than theirs." (largest positive and negative residual, era nicknames via `eraText`). Logos are marks, with the same sizes, my-team ring and tooltip pattern as D-08/D-10/D-11 (tooltip: era name, record, win%, score, mood label, and the gap vs the line in points). Clicking opens the team page at that season/week.

#### Area 4: Accessibility & theme for both charts
- D-16a Each chart is a `ChartFrame` (headline, dek, SOURCE/NOTES footer) built with `withTheme`, `valueAxis` and `baseAxis`. Both charts get a collapsed `<details>` "Show as table" under the chart: a rule-separated table (rank, logo, team link, the plotted values). This gives keyboard and screen-reader access to every mark's link.
- D-16b Dark mode: logos already sit on the light disc inside TeamLogo; in Plot image marks, draw a `dot` disc (`--logo-disc`) under each logo in dark mode only (r ≈ size/2 + 2). Gridlines and diagonals use tokens.

#### Area 5: Win totals on the team page (DATA-03)
- D-17 Pipeline export tweak (display-only, `export.py` only): each `teams/{F}.json` gains `expectation: { season[], exp_total[] (1 dp), source[] ('vegas'|'model'), reg_games[] }` taken from the week-0 rows of `derived["features"]` (`exp_total`, `expectation_source`). `reg_games` is that team-season's actual regular-season game count, so pace handles the 2022 BUF/CIN 16-game seasons. Nothing reads it back into the score. Add a test in `test_export.py`. Then regenerate the site data once from cache with `uv run fgs export` (no refresh/network). The golden pin `3ac3c2b5…` must be unchanged before and after, and `uv run pytest` must pass.
- D-18 Web: add a `TeamFile` type and a `loadTeam(meta, F)` loader (session cache keyed by `generated_at`, evicted on failure, the same pattern as `loadGames`).
- D-19 New `WinTotals.svelte` section on the team page for the viewed season, titled "Preseason expectations". It is a compact HTML number line (0 to reg_games wins) with up to three labeled markers plus a text list (no Plot needed):
  - **Vegas preseason**: line from `vegas_win_totals`. Labels: when `used_in_score` is true (2003–2020): "Vegas preseason (used in score)". When false (2021+): "Vegas preseason (display only, not used in score)". When `line_type === 'preseason_open'` (2026): append "· opening line, not the final preseason number".
  - **Model preseason (used in score)**: `exp_total` when `source === 'model'`. For Vegas-sourced seasons the score uses a league-normalized Vegas line, so the model row is omitted and a note says "The score uses this line, normalized to the league average."
  - **Pace**: (W + 0.5·T) / GP × reg_games, 1 dp: "On pace for 12.8 wins (6–2 after 8 games)". After the regular season it becomes "Finished 13–4". At week 0 it reads "No games yet."
  - 1999–2002 (no Vegas line): only the model row and pace.
- D-20 Source line for this block: `SOURCE: NFLVERSE (2003–2020) · COVERS / DRAFTKINGS (2021+)`. `ChartFrame` gains an optional `source` prop (default unchanged); add a chartFrame test.
- D-21 Placement: after the "Why" factor block and before "Recent games". On wide screens it can sit in the right column, which helps the Phase 12 "unbalanced team page" finding (#6) at no extra cost.

#### Area 6: Phase 12 UI-review leftovers (cheap only)
- D-22 #4 Records rows span the full 960px frame, with consistent streak/record cell widths (grid columns with fixed mono widths).
- D-23 #7 History end-mark logo: add top inset/margin so a logo at y=100 is not clipped at 375px.
- D-24 #8 Rank delta: replace `#▲1` / `#–` with readable text, e.g. "▲1 spot" / "▼2 spots" / "no change", plus an `aria-label` "Up 1 spot in rank". Update the format tests.
- D-25 #9 Callout cards: the action row sits at the bottom of each card (flex column, `margin-top: auto`) so buttons line up across a row at 1280.
- Skipped unless trivially adjacent: #5 (saddest/happiest lead), #10 (callout count at 375), #11 (methodology table). Log them as still deferred.

#### Verification
- D-26 `npm test`, `npm run check`, `npm run build` pass under Node 24. `cd pipeline && uv run pytest` passes (pipeline touched). The golden pin is unchanged.
- D-27 Playwright MCP at 1280 and 375, light and dark: explore (latest, plus a historical week such as 2025/10), week-0 empty state, team page win totals (2026 opener, a 2021–2025 display-only season, a 2003–2020 used-in-score season). No horizontal scroll at 375. Save ≤ 6 screenshots in `screenshots/` in the phase dir.

### Claude's Discretion
- Exact pixel sizes, opacities, diagonal spacing and label positions, within the constraints above.
- Whether to show the regression line's equation (default: no).
- Table-view column choice and sort order (default: sorted by the chart's y value).

### Deferred Ideas (OUT OF SCOPE)
- Season-to-date vs last-8-games window toggle on the EPA scatter.
- Opponent-adjusted EPA.
- Share cards for Explore charts (Phase 14 covers teams and callouts only).
- Phase 12 UI items #5, #6 (beyond the win-totals placement), #10, #11.
- Callout-team annotations on the record-vs-evidence chart.

**UI-SPEC (`13-UI-SPEC.md`, approved) is also locked.** It fixes the exact copy, tokens, margins, table columns, WinTotals anatomy and the component inventory. The planner should cite it per task and not restate it.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXPL-02 | A new Explore page shows an offense-vs-defense EPA/play scatter with team logos as marks, for the selected season and week | Plot `image` and `pointer` internals verified (§Plot 0.6.19 facts). `seasonToDate` week semantics, plus a playoff-week mismatch to handle (Pitfall 1). Domain, diagonal and inset recipes (Code Examples). Router and App wiring (Pattern 1). |
| EXPL-03 | A "record vs evidence" scatter (win% vs feel-good score) makes the perception gap visible, and each mark links to its team page | `plot.value` + `input` + `click` wiring, and the touch-tap behaviour the spec gets wrong (Pitfall 2). OLS, residual and rank helpers (Code Examples). The no-"luck" grep test has to avoid the `contribs.luck` key and match itself (Pitfall 6). |
| DATA-03 | The team page shows the preseason Vegas win total next to actual pace, labeled "not used in score" where the model expectation drives the score | The exact `export.py` insertion point, plus verified week-0 `exp_total`/`expectation_source` coverage (893 rows, 0 null; 576 vegas / 317 model). `reg_games` comes from `EXPECTED_GAME_EXCEPTIONS`. Golden-pin and fingerprint safety (Pitfalls 4 and 5). The TeamPage DOM order for D-21 (Pattern 4). |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Work only inside `feel-good-scorew/`. No shared or root deps. Keep it light: quick prototypes, no heavy CI/test suites beyond what this phase needs.
- Stack: Python (nflreadpy/Polars) → static JSON; Vite 8 + Svelte 5 (plain, hash routing) + Observable Plot 0.6.19. No new npm packages (UI-SPEC).
- TypeScript stays `~6.0.3` (svelte-check 4.7 does not support TS 7).
- Node: the shell default is Node 20. Run web commands with `source ~/.nvm/nvm.sh && nvm use 24` (package.json `engines.node` is `24.x`).
- GSD workflow: edits happen inside `/gsd-execute-phase`.
- Phase-specific: don't touch pipeline model code (`mood.py`, `expectation.py`, `features.py`, `score.py`, `season_config.py`, …), `pipeline/inputs/`, or `PREREGISTRATION*.md`. The only pipeline change allowed is the display-only addition in `export.py` plus its test.
- Full autonomy: never ask the user. CONTEXT and UI-SPEC decisions are locked.

## Summary

Every building block already exists in the codebase. Phase 13 wires them together:
- Data loaders: `loadSeason`, `loadEpa`, plus the `loadGames` cache pattern to copy for `loadTeam`.
- Aggregation: `seasonToDate`.
- Chart theme and frame: `plotTheme`, `ChartFrame`.
- The Plot-in-`$effect` render pattern: `HistoryChart`.
- Shared UI and helpers: `Scrubber`, `carryWeek`, `highlightColor`, `logoSrc`/`logosEnabled`, `eraName`/`eraText`/`isActiveFranchise`, `myTeam`/`validMyTeam`.

The novel work:
1. Two Plot scatters with logo `image` marks, a click-through via `plot.value`, and explicit scale domains.
2. Pure helpers in `lib/explore.ts` and `lib/winTotals.ts`.
3. A ~20-line `expectation` block in `export.py`.
4. A `WinTotals.svelte` HTML number line.
5. Four small CSS/format fixes.

Reading the actual Plot 0.6.19 source turned up two facts the UI-SPEC gets wrong or doesn't cover:
- **Touch taps navigate on the first tap.** Plot's `pointer` sets `value` on touch contact (`pointerenter`/`pointermove` fire for touch), and its `pointerdown` handler ignores non-mouse pointers. A naive `click` listener therefore navigates on the first tap. The spec says "tap shows tip, second tap navigates … needs no custom code", which is false. It needs a ~10-line armed-tap guard.
- **Explicit `x`/`y` domains are mandatory.** Otherwise the tier-diagonal `link` endpoints and the band `rect`s widen the scales.

The data has one trap. EPA files include playoff weeks (`week` 19–22 = WC/DIV/CON/SB, `game_type != 'REG'`), but snapshot W–L freezes at the regular-season record. Unfiltered `seasonToDate` in playoff weeks would mix playoff EPA with REG records.

The pipeline change is safe:
- `export.py` is **not** in `fgs.fingerprint.CODE_FILES`, so the callout-evidence check is unaffected.
- The golden test hashes only `snapshots/{≤2025}.json` `(season, week, franchise, score, label)`, so a new key in `teams/{F}.json` cannot move it.
- Week-0 `exp_total` is non-null for all 893 team-seasons (verified in `pipeline/data/derived/features.parquet`).

**Primary recommendation:** Build `lib/explore.ts` and `lib/winTotals.ts` test-first. Then build `EpaScatter`/`RecordScatter` by copying the HistoryChart render pattern with explicit domains, per-group marks (non-pinned, then pinned) and a shared `attachClick(plot, onPick)` helper that includes the touch-arming guard. Do the export addition plus regeneration as a separate early plan, so the web plans can rely on `teams/{F}.json.expectation`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Preseason expectation per team-season (`exp_total`, `source`, `reg_games`) | Pipeline export (`export.py`, build time) | — | The values live only in `derived["features"]` and `season_config`. The browser can't derive them. |
| EPA season-to-date aggregation, league means, ranks | Browser (`lib/explore.ts` over `seasonToDate`) | Static JSON (`epa/{season}.json`) | Already client-side since Phase 11 (EXPL-01). Per week × season is too many combinations to precompute. |
| OLS line, residuals, dek text | Browser (`lib/explore.ts`) | — | Per-view, cheap, testable. |
| Win-total pace | Browser (`lib/winTotals.ts`) | — | Depends on the viewed week's row. |
| Routing / validation | Browser (`lib/router.ts`, `App.svelte`) | — | Hash routing, validated against `meta`. |
| Hosting | CDN/static (Vercel `dist/`) | — | No server runtime. |

## Standard Stack

### Core (all already installed; no new packages)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @observablehq/plot | 0.6.19 (exact pin in `web/package.json`) [VERIFIED: node_modules/package.json] | Both scatters | Already the project's chart lib. `image`, `dot`, `link`, `rule`, `rect`, `text`, `tip`, `pointer` are all present. |
| svelte | ^5.57.3 [VERIFIED: package.json] | Components (runes) | Project standard |
| vitest | ^5.1.0 [VERIFIED: package.json] | Unit tests (216 passing today) | Project standard |
| polars | per `pipeline/uv.lock` | Export block | Project standard |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plot `image` marks | HTML-positioned `<img>` overlay | Rejected: duplicates scale math. Plot handles positioning, tips and clipping. |
| Plot for WinTotals number line | — | D-19 locks plain HTML/CSS. |
| d3-regression for OLS | 6 lines of arithmetic | No new deps (UI-SPEC). OLS of score on win% is trivial. |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed in this phase (UI-SPEC: "New npm packages: none"), so slopcheck was not needed.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| (none) | — | — | — | — | — | — |

**Packages removed:** none. **Packages flagged:** none.

## Plot 0.6.19 facts (verified in `web/node_modules/@observablehq/plot/dist/plot.js` and `src/*.d.ts`)

| Fact | Evidence | Consequence |
|------|----------|-------------|
| `image` `src`: a string is a **constant** only if it starts with `./`, `../`, `/` or `http(s):/data:/blob:/file:`. Any other string is a **field name**. | `isPath` / `isUrl` / `maybePathChannel` (plot.js ~13038) | `logoSrc()` returns `${BASE_URL}logos/sm/F.png`. With base `/` that is a path, but use a channel anyway: `src: (d) => d.src` (HistoryChart uses `src: () => src`). Never pass a bare string per datum. |
| `image` `width`/`height`: a number is a constant in px; a function is an **unscaled** px channel. Setting only `width` sets `height` too. `r` turns on circular clip. `preserveAspectRatio` defaults to `xMidYMid` (meet). `crossOrigin` defaults to unset. | Image constructor and render (~13058–13120) | Use constant widths per mark group (others / pinned) so there's no channel sorting. Don't set `crossOrigin` (same-origin logos). Don't set `r` (it would circle-clip the logos). |
| `opacity` and other MarkOptions apply per mark | MarkOptions | Non-pinned group: `opacity: 0.5` on both disc and image when a pin is active. |
| `Plot.dot` with numeric `r` = constant px radius; `fill: 'var(--logo-disc)'` works | HistoryChart already does this | Dark disc and ring as in UI-SPEC. |
| Plot returns the bare `<svg>` when there's no title/caption/legend. `value` lives on the returned element. | `context.dispatchValue` sets `figure.value` and dispatches a bubbling `input` Event (~8401). If wrapped, `figure.value = svg.value` (~8560). | `plot.addEventListener('input', …)` and read `(plot as unknown as { value: Datum \| null }).value`. Plot's TS types don't declare `value`, so a cast is needed for `npm run check`. |
| `pointer` default `maxRadius = 40` px. It picks the nearest point within the radius. | `pointerK` (~4625) | Pass `maxRadius: size/2 + 6` so clicks on empty space near a logo don't navigate. |
| Mouse `pointerdown` on a pointed datum toggles **sticky** (the tip stays). **Non-mouse `pointerdown` returns early.** Touch still fires `pointerenter`/`pointermove`, which set `value`. Non-mouse `pointerleave` is ignored, so `value` stays set after the tap. | `pointerdown` / `pointerleave` / `pointermove` (~4755–4799) | **On touch, the first tap sets `value` and the following `click` sees non-null → navigates immediately.** Implement arming (Pattern 3). |
| `tip` with a `title` channel shows the title string as-is (multi-line on `\n`). Otherwise it shows channel name/value pairs. | Tip render (~7905) | `Plot.tip(data, Plot.pointer({x, y, title: (d) => lines.join('\n'), maxRadius}))`. Put the tip mark **last**. |
| Scale `reverse: true`, `labelAnchor`, `labelArrow: 'none'`, scale `inset` all exist | `scales.d.ts` lines 353, 415, 624 | `y: baseAxis({domain, reverse: true, label: '↑ Defense…', labelAnchor: 'top', labelArrow: 'none'})`. |
| Default number tick format already uses U+2212 for negatives, but not `+` for positives | d3-format | A custom `signed2` tickFormat must add `+` and use `−`. |
| Mark `clip: true` clips to the frame | `mark.d.ts` ~303 | Diagonals: `Plot.link(…, {clip: true})`. |
| Grid strokeOpacity is hard-coded to 0.1, and app.css restores it | `plotTheme.ts` comment | Use `valueAxis` for the record chart's y grid. Don't fight it. |

## Architecture Patterns

### System Architecture Diagram

```
 hash change ──► route.svelte.ts ──► parseHash (lib/router.ts) ──► App.svelte
                                                         │  kind 'explore' {season?,week?}
                                                         │  validate vs meta → replace('#/explore') if bad
                                                         ▼
                                              ExplorePage {meta, latestRows}
            Scrubber ──(go/replace exploreHash)──┘      │
                                                         ├─ latest? latestRows : loadSeason(meta,s).weeks[w]
                                                         ├─ rows ─► filter isActiveFranchise
                                                         │
             ┌──────────── EPA branch ───────────────────┤
             │ s ∈ meta.epa_seasons? ─no─► empty state   │
             │ loadEpa(meta,s) ─► regOnly? ─► seasonToDate(file, w)
             │ ─► explore.joinEpa(rows, agg) ─► leagueMeans / ranks / domains / diagonals
             │ ─► EpaScatter (Plot) ─► input/click ─► go(teamHash)
             │                                            │
             └──────────── Record branch ────────────────┤
               explore.recordPoints(rows) (GP>0) ─► fitLine ─► residuals ─► dek text
               ─► RecordScatter (Plot) ─► input/click ─► go(teamHash)
               ─► ExploreTable (<details>) ─► <a href=teamHash>

 Team page:  TeamPage ─► loadTeam(meta,F) ─► teams/F.json {vegas_win_totals, expectation}
             + snapshot row (W,L,T) ─► winTotals.rows(season) ─► WinTotals (HTML number line)

 Pipeline:   fgs export ─► derive(cache) ─► build_export ─► scored week-0 rows
             ─► expectation{season, exp_total(1dp), source, reg_games} ─► teams/F.json
```

### Recommended file structure (matches the UI-SPEC Component Inventory)
```
web/src/lib/explore.ts (+explore.test.ts)       pure: joins, means, ranks, domains, ticks, diagonals, fitLine, residuals, dek, formats, tapAction
web/src/lib/winTotals.ts (+winTotals.test.ts)   pure: pace, finished, ticks, legend rows/labels
web/src/lib/noLuck.test.ts (or inside explore.test.ts)  raw-source grep
web/src/components/{ExplorePage,EpaScatter,RecordScatter,ExploreTable,WinTotals}.svelte
pipeline/src/fgs/export.py (+tests/test_export.py)
.planning/phases/13-.../verify_ui.py            copy and adapt the Phase 12 harness (Python Playwright is installed)
```

### Pattern 1: Route + App wiring
- `lib/router.ts`: add `| { kind: 'explore'; season?: number; week?: number }` and the regex `const EXPLORE = /^\/explore(?:\/(\d{4})(?:\/(\d{1,2}))?)?\/?$/`.
  - Season-only parses as `{kind:'explore', season}`, the same as the team route.
  - `exploreHash = (s?, w?) => s === undefined || w === undefined ? '#/explore' : \`#/explore/${s}/${w}\``.
  - Tests: `#/explore`, `#/explore/`, `#/explore/2025/10`, season-only, `#/explore/abc` → `invalid`.
- `App.svelte`:
  - Add `r.kind === 'explore'` to the `notice = null` branch.
  - If `season !== undefined` and (week undefined or `!validTeamWeek(meta, season, week)`) → `replace('#/explore')`. Reuse `validTeamWeek`; it is the same check.
  - An explicit hash equal to `meta.latest` renders as latest. The Scrubber writes `#/explore` for latest (UI-SPEC).
  - Add a render branch `{:else if route.current.kind === 'explore' && status === 'ready' && meta && latestFile}<ExplorePage {meta} latestRows={latestFile.rows} …/>` plus the loading branch.
  - Extend the `SiteHeader current` ternary and the SiteHeader prop union with `'explore'`.
- ExplorePage owns its own season fetch. Copy TeamPage's `live`-flag `$effect` around `loadSeason`; the stale-response guard is required.

### Pattern 2: Plot chart component (copy HistoryChart)
`bind:clientWidth={width}` + `bind:this={container}`, then:
```ts
$effect(() => { if (width <= 0) return; /* read all reactive deps */ const plot = Plot.plot(withTheme({...})); attach(plot); container.replaceChildren(plot); return () => plot.remove() })
```
- `dark` comes from `matchMedia('(prefers-color-scheme: dark)')`, as in HistoryPage lines 68–75.
- Highlight color: `highlightColor(primary, secondary, getComputedStyle(document.documentElement).getPropertyValue('--bg'), dark)`.
- Pin: `validMyTeam(myTeam.abbr, meta.teams)`. Read it inside the effect so pin changes re-render.

### Pattern 3: Click-through with touch arming
```ts
// lib/explore.ts (pure, tested)
export function tapAction(pointerType: string, armed: string | null, picked: string | null): { go: boolean; armed: string | null } {
  if (!picked) return { go: false, armed: null }
  if (pointerType === 'mouse') return { go: true, armed: null }
  return picked === armed ? { go: true, armed: null } : { go: false, armed: picked }
}
// component
let pType = 'mouse', armed: string | null = null
plot.addEventListener('pointerdown', (e) => (pType = (e as PointerEvent).pointerType))
plot.addEventListener('input', () => { (plot as SVGElement).style.cursor = val() ? 'pointer' : '' })
plot.addEventListener('click', () => { const r = tapAction(pType, armed, val()?.franchise ?? null); armed = r.armed; if (r.go) go(href(val()!)) })
```
Plot attaches its own `pointerdown` to the same svg, so a listener added after `Plot.plot` returns runs after Plot's. Both are fine, because ours only records the type.

### Pattern 4: TeamPage placement (D-21)
Keep the DOM order `Why`, then `div.right { WinTotals section; Recent games section }`. Below 1024 that reads Why → WinTotals → Recent games. At ≥1024 the existing 2-column `.columns` grid puts Why on the left and the `.right` stack on the right. If WinTotals and games stay sibling grid items instead, games would wrap to row 2 on the left, which is wrong. Load `loadTeam(meta, team)` in a TeamPage `$effect` with the `live` guard. If it fails, omit the section.

### Anti-Patterns to Avoid
- **Implicit scale domains** with diagonals or rects: the link endpoints and the 0–100 rects stretch the scale. Always pass `domain`.
- **One image mark with a per-datum width channel**: you lose explicit draw order (pinned last) and opacity control. Use separate mark groups.
- **Reading `row.contribs.luck` or naming anything `luck*`** in Explore files: it breaks the D-15 grep test.
- **Changing `formatRecord`**: `format.test.ts` pins a hyphen (`'7-2'`) and the board uses it. Add an en-dash helper (e.g. `recordText(w,l,t)` → `6–2`, `6–2–1`) for the new copy.
- **Editing `season_config.py` to add a helper**: it is in `fingerprint.CODE_FILES`, so `fgs export` would then fail the callout-evidence staleness check. Read `EXPECTED_GAME_EXCEPTIONS` from `export.py`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Nearest-mark hover/tooltip | Custom hit-testing | `Plot.tip` + `Plot.pointer({maxRadius})` | Handles nearest-point search, anchoring inside the frame and sticky mode. |
| Season-to-date EPA | New aggregation | `seasonToDate` (play-weighted, null-safe, tested) | WR-05 null-rate handling is already solved. |
| Session caching | New fetch layer | Copy `loadGames` for `loadTeam` | Eviction on failure, keyed by `generated_at`. |
| Era names, HOU filter, Washington copy | Ad-hoc strings | `eraName`, `eraAbbr`, `eraText`, `isActiveFranchise` | Covered by the LOGO-03 tests. |
| Contrast-safe team color | Raw `primary` | `highlightColor` | ≥3:1 fix from Phase 12. |
| Week carry across seasons | Clamp logic | `carryWeek` | Era-aware (reg_weeks differs). |
| Band colors | Hex literals | `var(--mood-${moodToken(i, bands.length)})` | Same as HistoryChart. |
| Text measuring for the band gutter | Hard-coded width | HistoryChart's canvas `textWidth` + `document.fonts.ready` tick | Already proven. Copy it into RecordScatter (DOM-bound, so it doesn't belong in a pure lib). |

## Pipeline change (D-17): exact recipe

- **Where:** `pipeline/src/fgs/export.py`, `build_export`, in the per-franchise loop that writes `files[f"teams/{fid}.json"]` (it currently ends with `"vegas_win_totals": _vegas_win_totals(win_totals, fid)`). Add `"expectation": _expectation(scored, fid)`.
- **Source:** `scored` (= `score_frame(derived["features"])`) keeps `exp_total` and `expectation_source`; `_row` already reads `r.get("expectation_source")`. `exp_total` is joined per (season, franchise), so it is constant across weeks; the week-0 row is canonical.
- **Verified** in `pipeline/data/derived/features.parquet`:
  - 893 week-0 rows, `exp_total` null count 0.
  - Sources: `vegas` 576 (2003–2020), `model` 317 (1999–2002 and 2021–2026).
  - Some values are float32-ish (e.g. `6.287499904632568`), so use `round(float(v), 1) + 0.0`.
- **Helper:**
```python
EXPECTATION_KEYS = ("season", "exp_total", "source", "reg_games")

def _expectation(scored: pl.DataFrame, fid: str) -> dict[str, list]:
    """Display-only preseason expectation per team-season (D-17): week-0 exp_total (1 dp) and its source,
    plus the team-season's REG game count (EXPECTED_GAME_EXCEPTIONS, e.g. 2022 BUF/CIN = 16). Never read back."""
    cols = [c for c in ("exp_total", "expectation_source") if c in scored.columns]
    w0 = scored.filter((pl.col("week") == 0) & (pl.col("franchise_id") == fid)).sort("season")
    seasons = [int(s) for s in w0["season"]]
    exp = w0["exp_total"].to_list() if "exp_total" in cols else [None] * len(seasons)
    src = w0["expectation_source"].to_list() if "expectation_source" in cols else [None] * len(seasons)
    return {
        "season": seasons,
        "exp_total": [None if v is None else round(float(v), 1) + 0.0 for v in exp],
        "source": src,
        "reg_games": [season_config.EXPECTED_GAME_EXCEPTIONS.get((s, fid), season_config.reg_games(s)) for s in seasons],
    }
```
  The synthetic test frames have no sim (`exp_total` is null), so the block keeps a stable shape with nulls. That is the same philosophy as `_vegas_win_totals` returning empty lists.
- **Tests in `tests/test_export.py`:**
  - (a) Real data via `real_files`. Keys equal `EXPECTATION_KEYS`. Equal lengths. Seasons ascending and equal to the team's history seasons (HOU starts 2002). `source == 'vegas'` iff 2003 ≤ season ≤ 2020. `exp_total` is non-null and in (0, 17]. `reg_games` is 16 for ≤2020, 17 for ≥2021, except BUF/CIN 2022 = 16. Cross-check `reg_games` against the count of REG games per team in `derived["games"]` for completed seasons. `json.dumps(…, allow_nan=False)` succeeds.
  - (b) Synthetic: the key exists with `exp_total` all None (same `_draft_export` helper as `test_vegas_win_totals_empty_without_frame`).
  - (c) Optional: exported snapshot rows are unaffected. The golden test already covers this.
- **Golden (INTEG-01):** `tests/test_golden_scores.py` hashes sorted `(season, week, franchise, score, label)` from `web/public/data/snapshots/{≤2025}.json` (export check), plus a fresh derive (derive check). Pin overall `3ac3c2b58d0bfecf2ba7641160cac7a78110265d1c209e27764c2febf0539472`, 19,102 rows. `teams/*.json` is never read, so adding the key cannot change it. Run `cd pipeline && uv run pytest tests/test_golden_scores.py -q` before and after the regeneration.
- **Regeneration:** `cd pipeline && uv run fgs export`.
  - It uses `derive(load_schedules(), **cached_inputs(), sim_cache_dir=…)` and is cache-only. Schedules download only if missing; the cache is present (18 MB in `pipeline/data/cache`).
  - It refuses if a refresh marker is incomplete.
  - Phase 11 ran it in ~6 minutes, including gates. The full pytest run was 631 tests in 147s.
  - Expected diff: all 32 `teams/*.json` and `meta.json` (`generated_at`). `records.json`, `callouts.json` and `snapshots/2026.json` callouts may also change: active streaks count through the export date (`as_of_date`), and so do the latest week's streak cards. **`snapshots/≤2025` must not change.** Verify with `git diff --stat web/public/data`.
- **Persistence:** there is no GitHub Actions workflow (no `.github/` in the repo). Data refresh is manual (`uv run fgs refresh`), and it calls the same `build_export`, so future refreshes keep the field automatically. Vercel only builds `web/` from committed data.

## Common Pitfalls

### Pitfall 1: Playoff weeks mix playoff EPA with regular-season records
**What goes wrong:** At weeks > `reg_weeks` (e.g. 2025 weeks 19–22), `seasonToDate(file, week)` includes WC/DIV/CON/SB games. Snapshot `wins/losses` stay frozen at the REG record (verified: SEA 14–3 at weeks 18, 19 and 22). The tooltip "{6–2} · {n} games" would disagree, and playoff teams get extra samples.
**How to avoid:** In `lib/explore.ts`, build a REG-only view of the EpaFile (filter indices where `game_type[i] === 'REG'`) before calling `seasonToDate`. In playoff weeks the EPA chart then equals the final regular-season picture, which is consistent with the record chart. Note this in the code comment.
**Warning signs:** "games" in the tooltip exceeds W+L+T.

### Pitfall 2: Touch taps navigate immediately
See the Plot facts table and Pattern 3. Test `tapAction` in vitest. Verify by tapping at 375 in Playwright (`hasTouch: true` context, `page.tap`): the first tap shows the tip and keeps the URL, the second tap navigates.

### Pitfall 3: Logos clipped at the frame edges
A team at 0% or 100% win%, a score near 0 or 100, or an EPA extreme puts a 28–36px logo half outside the frame, and the container is `overflow: hidden`. Use scale `inset` (e.g. `x: {…, inset: maxSize/2 + 4}`, same for y) in both charts. The domains stay [0, 1] and [0, 100] as specified. Same root cause as Phase 12 #7.

### Pitfall 4: Changing a fingerprinted module breaks `fgs export`
`fgs export` → `_load_evidence` compares `callout_evidence.json` against `fingerprint.code_fingerprint()`, which hashes `CODE_FILES` (`franchises, games, elo, snapshots, sim, efficiency, expectation, features, draft, score, mood, season_config, backtest, evidence`) plus `cli.derive_games/draft_winsor` and `insights.record_ranks/gap_flags`. Touching any of these, even a docstring-free helper, makes the export raise "callout_evidence.json is stale". `export.py` is safe.

### Pitfall 5: Regeneration diff noise is mistaken for score drift
Expect `generated_at`, `records.json` streak days and 2026 callouts to move with the export date. The golden test is the arbiter for ≤2025. Commit the data regeneration as its own `data(13-xx)` commit, as in 11-05.

### Pitfall 6: The no-"luck" grep test matches itself or misses files
Copy the `nohotlink.test.ts` / `brand.test.ts` pattern: `import.meta.glob([...], {query:'?raw', import:'default', eager:true})` over `../components/{ExplorePage,EpaScatter,RecordScatter,ExploreTable}.svelte` and `./explore.ts`. Build the regex from parts (`new RegExp(['lu','ck'].join(''), 'i')`) so the test file never matches. Assert the glob found ≥5 files, so a rename doesn't silently pass. Don't scan `types.ts`: `Row.contribs` has a `luck` key.

### Pitfall 7: Rank-delta text overflows the board column
BoardRow's ≥1024 grid ends in a `72px` column (`.change`, `white-space: nowrap`), and MoodBoard's header grid has the same template. "no change" in mono 14 is about 76px. Widen that last column in **both** `BoardRow.svelte` and `MoodBoard.svelte` (e.g. 88px), or check it at 1280 in Playwright. `.change` is `aria-hidden` in BoardRow, so the new `aria-label` matters on other Delta uses only. That's harmless.

### Pitfall 8: Early-season and lagging-pbp weeks
- In the live season, pbp can lag the snapshot (2026 epa has weeks 1–9 with 28–32 teams per week because of byes). `seasonToDate` simply counts fewer games. Show "games counted" honestly.
- "No efficiency data through {week}" only when the aggregate is empty.
- All 28 seasons (1999–2026) are in `meta.epa_seasons` today, so the "season without pbp" state is defensive only. Test it with a fake meta.

### Pitfall 9: HOU pre-2002 and the 31-team era
HOU has no snapshot rows before 2002 (verified: 31 rows in 2001), but filter with `isActiveFranchise` anyway, as D-04 requires. For EPA, join on snapshot rows (inner), so a franchise without a row never plots.

### Pitfall 10: Ties and win%
Win% = (W + 0.5T)/GP with GP = W+L+T. Exclude GP = 0 rows. Ranks use competition ranking ("ties share the lower number": 1, 2, 2, 4). OLS isn't drawn when n < 3 or var(x) = 0, e.g. week 1 when every team is 1–0 or 0–1. Var(x) > 0 there, but the line is crude, which is fine. The zone labels hide with the line.

### Pitfall 11: BASE_URL and hash routing
`logoSrc` already prefixes `import.meta.env.BASE_URL`. Hash routes never change the document path, so relative and absolute logo paths both resolve. Don't build logo URLs by hand. `nohotlink.test.ts` must keep passing.

### Pitfall 12: Dark-mode re-render and pin reactivity
The effect must read `dark`, `width`, `pinned` and the data so Svelte tracks them. Read `myTeam.abbr` inside the `$effect`/`$derived`, not once at module scope.

## Code Examples

```ts
// lib/explore.ts — verified-against-codebase sketches (types from lib/types.ts, EpaAgg from lib/epa.ts)
export const regOnly = (f: EpaFile): EpaFile => {
  const keep = f.game_type.map((t, i) => (t === 'REG' ? i : -1)).filter((i) => i >= 0)
  const pick = <T,>(a: T[]) => keep.map((i) => a[i])
  return { ...f, game_id: pick(f.game_id), week: pick(f.week), game_type: pick(f.game_type), franchise: pick(f.franchise),
    opponent: pick(f.opponent), off_epa: pick(f.off_epa), off_plays: pick(f.off_plays), off_sr: pick(f.off_sr),
    def_epa: pick(f.def_epa), def_plays: pick(f.def_plays), def_sr: pick(f.def_sr) }
}
// play-weighted league means (D-09): Σ(off_epa·off_plays)/Σoff_plays over plotted teams
export function leagueMeans(a: EpaAgg[]): { off: number; def: number } { /* skip null rates */ }
export function fitLine(pts: { x: number; y: number }[]): { a: number; b: number } | null {
  const n = pts.length; if (n < 3) return null
  const mx = pts.reduce((s, p) => s + p.x, 0) / n, my = pts.reduce((s, p) => s + p.y, 0) / n
  const sxx = pts.reduce((s, p) => s + (p.x - mx) ** 2, 0); if (sxx === 0) return null
  const b = pts.reduce((s, p) => s + (p.x - mx) * (p.y - my), 0) / sxx
  return { a: my - b * mx, b }
}
export function paddedDomain(min: number, max: number): [number, number] {
  const lo = Math.floor((min - 0.03) / 0.05) * 0.05, hi = Math.ceil((max + 0.03) / 0.05) * 0.05
  return [Math.round(lo * 100) / 100, Math.round(hi * 100) / 100] // kill float noise
}
// tier diagonals: off − def = c for c = k·0.1 crossing the frame
export function diagonals([x0, x1]: [number, number], [y0, y1]: [number, number]) {
  const out = []; for (let k = Math.ceil((x0 - y1) / 0.1 - 1e-9); k <= Math.floor((x1 - y0) / 0.1 + 1e-9); k++) {
    const c = k / 10; out.push({ x1: x0, y1: x0 - c, x2: x1, y2: x1 - c }) } return out
}
export const signed = (v: number, dp: number) => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(dp)
export const height = (w: number) => Math.min(560, Math.max(320, Math.round(w * 0.8)))
```

```ts
// EPA chart skeleton (Plot 0.6.19)
Plot.plot(withTheme({
  width, height: height(width), marginTop: 28, marginRight: 16, marginBottom: 36, marginLeft: 48,
  x: baseAxis({ domain: xd, inset, ticks: xt, tickFormat: (v: number) => signed(v, 2), label: 'Offense EPA/play →', labelAnchor: 'right', labelArrow: 'none' }),
  y: baseAxis({ domain: yd, reverse: true, inset, ticks: yt, tickFormat: (v: number) => signed(v, 2), label: '↑ Defense, EPA/play allowed (flipped)', labelAnchor: 'top', labelArrow: 'none' }),
  marks: [
    Plot.link(diagonals(xd, yd), { x1: 'x1', y1: 'y1', x2: 'x2', y2: 'y2', stroke: 'var(--grid)', strokeWidth: 1, clip: true }),
    Plot.ruleX([lm.off], { stroke: 'var(--text-muted)', strokeDasharray: '4,3' }),
    Plot.ruleY([lm.def], { stroke: 'var(--text-muted)', strokeDasharray: '4,3' }),
    ...(width >= 400 ? quadrantLabels : []),          // Plot.text([s], {frameAnchor:'top-right', dx:-8, dy:8, textAnchor:'end', …})
    ...logoMarks(others, size, pinned ? 0.5 : 1, dark),  // [dark disc dot] + image {src: d=>d.src, width: dark? size*.76 : size}
    ...(pin ? [ring(pin, size + 8), ...logoMarks([pin], size + 8, 1, dark)] : []),
    Plot.tip(points, Plot.pointer({ x: 'off', y: 'def', title: tipText, maxRadius: size / 2 + 6, fill: 'var(--bg)', stroke: 'var(--border)', fontSize: 12 })),
  ],
}))
```

```ts
// lib/winTotals.ts
export const pace = (w: number, l: number, t: number, reg: number): number | null => {
  const gp = w + l + t; return gp === 0 ? null : Math.round(((w + 0.5 * t) / gp) * reg * 10) / 10 }
export const finished = (w: number, l: number, t: number, reg: number) => w + l + t === reg
export const lineTicks = (reg: number) => [...Array.from({ length: Math.floor((reg - 2) / 4) + 1 }, (_, i) => i * 4), reg]
// 17 → [0,4,8,12,17]; 16 → [0,4,8,12,16]
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Rank delta `#▲1` | `formatRankDelta` → `▲1 spot` + aria | D-24, update `format.test.ts` |
| Records capped at 680px | Full width with subgrid columns | D-22. Subgrid works in all evergreen browsers (Safari 16+, Chrome 117+) [ASSUMED] |
| ChartFrame fixed source line | Optional `source` prop | D-20 |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Mobile browsers fire `pointerenter`/`pointermove` on touch contact before `click`, so Plot sets `value` before the click | Pitfall 2 | Low. Either way, `tapAction` gives the spec'd behaviour, and Playwright `hasTouch` verifies it. |
| A2 | Filtering EPA to REG games in playoff weeks fits D-04's "season to date" intent | Pitfall 1 | Low. Alternative: keep playoff games and drop "games" from the tooltip. The planner may pick either, but should document the choice. |
| A3 | CSS subgrid support is adequate for the target browsers | D-22 | Low. Fallback: fixed `grid-template-columns` per row with a `--score-cell` value column. |
| A4 | The `fgs export` runtime is a few minutes (sim cache warm) | Pipeline recipe | Low. Only affects task timing. |

## Open Questions

1. **REG-only EPA in playoff weeks?** Recommended yes (A2). It keeps both charts and the tooltip consistent.
2. **Lenient `#/explore/<garbage>` handling.** With the recommended regex, `#/explore/abc` is `invalid` and goes to `#/` with the board notice, while bad numeric season/week goes to `#/explore` silently (D-01). If the planner wants all `/explore…` paths to fall back to `#/explore`, add a catch-all `^\/explore\b` → `{kind:'explore'}` after the strict regex. Either is acceptable; test whichever is chosen.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node 24 (nvm) | web test/check/build | ✓ | v24.20.0 (default shell is 20.19, so run `nvm use 24`) | — |
| npm deps (Plot 0.6.19 etc.) | web | ✓ | `web/node_modules` present; vitest 216/216 pass under Node 24 | — |
| uv | pipeline | ✓ | `~/.local/bin/uv` | — |
| pipeline cache | `fgs export`, real-data tests | ✓ | `pipeline/data/cache` 18 MB, `data/derived` 5.1 MB | — |
| Python Playwright | D-27 visual sweep (`verify_ui.py`) | ✓ | importable | Playwright MCP |

No missing dependencies.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (web) | vitest ^5.1 (19 files, 216 tests passing at research time). SSR component tests via `svelte/server` `render` (see `chartFrame.test.ts`). |
| Framework (pipeline) | pytest via `uv run pytest` (631 tests at 11-05, ~150s) |
| Config | `web/vite.config.ts` (no separate vitest config); `pipeline/pyproject.toml`, `tests/conftest.py` |
| Quick run (web) | `source ~/.nvm/nvm.sh && nvm use 24 >/dev/null && cd web && npx vitest run src/lib/<file>.test.ts` |
| Full suite (web) | `source ~/.nvm/nvm.sh && nvm use 24 >/dev/null && cd web && npm test && npm run check && npm run build` |
| Quick run (pipeline) | `cd pipeline && uv run pytest tests/test_export.py -q -k expectation` then `uv run pytest tests/test_golden_scores.py -q` |
| Full suite (pipeline) | `cd pipeline && uv run pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXPL-02 | `explore` route parse and `exploreHash` | unit | `npx vitest run src/lib/router.test.ts` | ✅ extend |
| EXPL-02 | `regOnly`, EPA join (inner on snapshot rows, HOU<2002 dropped), play-weighted league means, off/def ranks (def ascending, ties share), `paddedDomain`, ticks (≤6 at <640), `diagonals`, `signed` formats (U+2212, `+`), `height` clamp, empty-state classifier (week 0 / not in epa_seasons / empty aggregate) | unit | `npx vitest run src/lib/explore.test.ts` | ❌ Wave 0 |
| EXPL-02/03 | `tapAction` (mouse navigates; touch arms then navigates; different mark re-arms; null → no-op) | unit | same | ❌ Wave 0 |
| EXPL-03 | win% with ties, GP=0 excluded, `fitLine` (null when n<3 or var 0, known slope/intercept), residuals, dek text (max ± residual, WAS era text via `eraText`, fallback when OLS null or both gaps <1), gap format `+8.4 pts` | unit | same | ❌ Wave 0 |
| EXPL-03 | No "luck"/"lucky"/"unlucky" in Explore files and `explore.ts` | static grep | `npx vitest run src/lib/noLuck.test.ts` | ❌ Wave 0 |
| EXPL-02/03 | Charts render, click navigates, no h-scroll at 375, dark disc, pinned ring | e2e/manual-visual | `python3 .planning/phases/13-.../verify_ui.py` (adapted from Phase 12) or Playwright MCP | ❌ Wave 0 (copy harness) |
| DATA-03 | `expectation` block: keys, lengths, sources by era, 1 dp, reg_games incl. 2022 BUF/CIN = 16, null-safe without sim | unit (real and synthetic) | `cd pipeline && uv run pytest tests/test_export.py -q -k expectation` | ✅ extend |
| DATA-03 | Golden pin unchanged after regeneration | regression | `cd pipeline && uv run pytest tests/test_golden_scores.py -q` | ✅ |
| DATA-03 | `pace` (week 0 null, mid-season, finished, ties, 16-game), `finished`, `lineTicks` (16/17), legend label selection (used / display-only / `preseason_open` suffix / model-only 1999–2002 / vegas-sourced omits model row), dek variants | unit | `npx vitest run src/lib/winTotals.test.ts` | ❌ Wave 0 |
| DATA-03 | `loadTeam` cache keyed by `generated_at`, evicted on failure | unit (mock `fetch`) | `npx vitest run src/lib/data.test.ts` | ❌ Wave 0 (no data.test yet; optional, small) |
| DATA-03 | ChartFrame `source` prop: default unchanged, custom shown | SSR unit | `npx vitest run src/lib/chartFrame.test.ts` | ✅ extend |
| D-24 | `formatRankDelta` text, dir and aria | unit | `npx vitest run src/lib/format.test.ts` | ✅ extend |
| D-22/23/25 | Records width, history logo, callout buttons | manual-visual | Playwright at 1280/375 | — |

### Sampling Rate
- **Per task commit:** the quick vitest file(s) touched; for the pipeline task, `pytest tests/test_export.py -k expectation` plus the golden test.
- **Per wave merge:** the full web suite (test + check + build) under Node 24; pipeline `uv run pytest -q` if the wave touched the pipeline.
- **Phase gate:** both full suites green, golden hash equal before and after, Playwright sweep (≤6 screenshots, 375 no h-scroll, light and dark).

### Wave 0 Gaps
- [ ] `web/src/lib/explore.test.ts`: covers EXPL-02/03 pure logic and `tapAction`
- [ ] `web/src/lib/winTotals.test.ts`: covers DATA-03 pace and labels
- [ ] `web/src/lib/noLuck.test.ts`: D-15 grep (or a `describe` in explore.test.ts)
- [ ] `pipeline/tests/test_export.py`: new `test_expectation_*` cases
- [ ] `.planning/phases/13-explore-charts-win-totals-display/verify_ui.py`: adapt the Phase 12 harness (`npm run preview -- --port 4173 --strictPort`; `?r=1` reload trick)

## Security Domain

`security_enforcement` is `false` in `.planning/config.json`, so this section is omitted. Note: no new inputs beyond hash params, which are validated against `meta`. No external requests; same-origin logos only.

## Sources

### Primary (HIGH confidence)
- `web/node_modules/@observablehq/plot/dist/plot.js` v0.6.19: Image mark (~13030–13140), `pointerK` (~4625–4806), `dispatchValue` (~8401), Tip title handling (~7905). `src/marks/image.d.ts`, `tip.d.ts`, `scales.d.ts`, `mark.d.ts`.
- Codebase: `web/src/{App.svelte, lib/data.ts, lib/router.ts, lib/epa.ts, lib/plotTheme.ts, lib/logos.ts, lib/teamNames.ts, lib/format.ts, lib/history.ts, lib/myteam.svelte.ts, components/HistoryChart.svelte, ChartFrame.svelte, Scrubber.svelte, TeamPage.svelte, SiteHeader.svelte, BoardRow.svelte, Delta.svelte, CalloutCard(s).svelte}`, `lib/{chartFrame,nohotlink,brand,router,format}.test.ts`.
- Pipeline: `src/fgs/{export.py, features.py, expectation.py, season_config.py, fingerprint.py, cli.py}`, `tests/{test_golden_scores.py, test_export.py, conftest.py}`, `tests/golden/v1_scores_le2025.json`.
- Data probes: `web/public/data/{epa/2025.json, epa/2026.json, snapshots/2025.json, snapshots/2001.json, snapshots/2022.json, latest.json, meta.json, teams/BUF.json}`, `pipeline/data/derived/features.parquet` (week-0 `exp_total` coverage).
- `.planning/phases/11-pipeline-data-guards/11-05-SUMMARY.md` (regeneration procedure, golden before/after), `12-VALIDATION.md`, `12-*/verify_ui.py`.

### Secondary / Tertiary
- None needed.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. No new deps; versions read from package.json and node_modules.
- Architecture: HIGH. Mirrors existing, working components.
- Plot behaviour: HIGH. Read from the installed source. Touch-event ordering is MEDIUM (A1), with a mitigation that holds either way.
- Pipeline safety: HIGH. Fingerprint scope, golden scope and data coverage were checked directly.

**Research date:** 2026-11-11
**Valid until:** 2026-12-11 (stable; pinned Plot version)

## Open Question Resolutions (orchestrator, autonomous, 2026-11-11)
1. **EPA is regular-season only.** Filter `game_type === 'REG'` before `seasonToDate` on the Explore page, so EPA, the games count and the W–L record describe the same games. In playoff weeks the chart shows the full regular season, and the NOTES add "Regular season only."
2. **Malformed explore hashes.** `#/explore/abc` doesn't match the explore regex, so it parses as `invalid` and follows the existing path (board plus notice). A well-formed `#/explore/{season}/{week}` with an unknown season or an out-of-range week is replaced with `#/explore` (latest), with no notice. Both cases are tested.
3. **Touch.** Use the `tapAction` arming guard from Pattern 3: the first tap shows the tip, a second tap on the same team navigates. The UI-SPEC touch note is superseded by this.

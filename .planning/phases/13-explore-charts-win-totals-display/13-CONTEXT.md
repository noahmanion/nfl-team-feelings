# Phase 13: Explore Charts & Win Totals Display - Context

**Gathered:** 2026-11-11
**Status:** Ready for planning
**Mode:** Smart discuss, full autonomy (recommended answers auto-accepted; no user prompts)

<domain>
## Phase Boundary

Add a new `#/explore` page with two opinionated exploratory charts, and show preseason expectations on the team page:

- EXPL-02: offense-vs-defense EPA/play scatter with team logos as marks, for a selected season and week.
- EXPL-03: "record vs evidence" scatter (win% vs feel-good score) that makes the perception gap visible; each mark links to its team page.
- DATA-03: the team page shows the team's preseason Vegas win total next to its actual pace, labeled "not used in score" for seasons where the model expectation drives the score.
- Cheap leftovers from the Phase 12 UI review (records row width/ragged cells, history logo clipping, cryptic rank delta, uneven callout buttons).

Extends Phase 12's editorial design system (tokens, `plotTheme.ts`, `ChartFrame.svelte`, `TeamLogo.svelte`, era names). It does not reinvent it.

Out of scope: pipeline model code (`mood.py`, `expectation.py`, `features.py`, `score.py`, etc.), `pipeline/inputs/`, `pipeline/PREREGISTRATION*.md`, share cards (Phase 14), and any change to scores. The one allowed pipeline change is a display-only addition to `export.py` (D-17), guarded by the INTEG-01 golden test.
</domain>

<decisions>
## Implementation Decisions

### Area 1: Explore page, route & controls
- D-01 Routes: `#/explore` (latest) and `#/explore/{season}/{week}`. New `explore` Route kind in `lib/router.ts` + `exploreHash(season?, week?)`, with router tests. Invalid season/week falls back to `#/explore` (latest) silently, the same way a bad team week goes to the team's latest page.
- D-02 Nav: add "Explore" to `SiteHeader` between "Mood over time" and "Records" (Board · Mood over time · Explore · Records · How it works), with the existing `.item`/`Sep` wrapping pattern and `aria-current`.
- D-03 Controls: reuse the existing `Scrubber.svelte` unchanged (season select + week slider + "Latest" button) at the top of the page. Season changes use `carryWeek` like the board. Week slider updates with `replace`, season with `go`. One season/week drives both charts.
- D-04 Data: rows come from `latest.json` (latest) or `loadSeason` (other weeks), the same session-cached loaders the board uses. EPA comes from `loadEpa(meta, season)` + Phase 11's `seasonToDate(file, week)` (play-weighted). Only seasons in `meta.epa_seasons` get the EPA chart; otherwise it shows an empty state. HOU before 2002 is filtered with `isActiveFranchise`.
- D-05 Week 0 (preseason) and weeks with no played games: both charts show a short empty state ("No games played yet in {season}. Pick a later week.") instead of a chart of 32 logos at the origin.
- D-06 New page component `ExplorePage.svelte` with a page headline ("Explore") and gray dek ("Two ways to check the board: how efficiently teams play, and how their record compares with the evidence."). Pure logic (joins, league means, regression line, residuals, ranks, empty-state checks) lives in a new `lib/explore.ts` with vitest tests.

### Area 2: EPA scatter (EXPL-02)
- D-07 X = offensive EPA/play; Y = defensive EPA/play allowed with the **axis reversed** (`y: { reverse: true }`), so up means better defense. The data is not negated. Tick labels show the real signed values (e.g. `+0.10`, `−0.05`).
- D-08 Marks: team logos as Plot `image` marks, 28px at width ≥ 640 and 20px below. Every logo uses the local `/logos/sm/{F}.png` path (`logoSrc` from lib), and `VITE_LOGOS=off` falls back to a `dot` mark in the team's primary color plus the abbreviation (no external URLs).
- D-09 Reference lines: dashed league-average crosshairs (play-weighted league mean for offense and defense) in `--text-muted`. Faint net-EPA tier diagonals (slope 1, i.e. constant off − def) at 0.1 EPA/play spacing in `--grid`, with no labels. Quadrant labels in the corners, mono micro, muted: top-right "Good at both", bottom-right "All offense", top-left "All defense", bottom-left "Struggling on both". Hide the quadrant labels below 400px if they collide.
- D-10 My-team highlight: when a team is pinned, its logo is drawn larger (+8px) with a ring in its `highlightColor` and other logos drop to 0.5 opacity. No pin means all logos at full opacity.
- D-11 Tooltip: Plot `tip` on pointer, showing era name, Off EPA/play and rank, Def EPA/play allowed and rank, success rates, record, and games counted. Clicking a mark opens `teamHash(F, season, week)` (or `teamHash(F)` when on the latest week). Implemented with the `plot.value` input pattern.
- D-12 Honesty notes (Pitfall 12). The ChartFrame NOTES read: "EPA PER PLAY, SEASON TO DATE, GARBAGE TIME FILTERED. NOT ADJUSTED FOR OPPONENTS. DEFENSE AXIS IS FLIPPED: HIGHER = FEWER POINTS ALLOWED." The dek states that efficiency is one input to the score, not the score itself. When week ≤ 3, an extra dek sentence warns that early-season EPA is noisy.
- D-13 Size: height = clamp(width × 0.8, 320, 560). Square-ish, no horizontal scroll at 375px.

### Area 3: Record vs evidence scatter (EXPL-03)
- D-14 X = win% = (W + 0.5·T) / games played, from the snapshot row (regular-season record), axis 0–100%. Y = feel-good score 0–100. Mood bands from `meta.bands` appear as faint horizontal background rects (low-alpha `--mood-N` via `color-mix`), the same encoding as the board.
- D-15 Perception gap: draw an ordinary least-squares reference line of score on win% across the teams shown that week (computed in `lib/explore.ts`, tested), labeled "Typical score for this record". Zone labels in plain words: above the line "Better than their record", below it "Worse than their record". Never "lucky"/"unlucky"/"luck" anywhere on the page (v1 luck weight ≈ 0). A unit test greps the Explore component and lib for those words.
- D-16 The dek is generated from residuals: "The {nick A} look better than their {W–L} record; the {nick B} look worse than theirs." (largest positive and negative residual, era nicknames via `eraText`). Logos are marks, with the same sizes, my-team ring and tooltip pattern as D-08/D-10/D-11 (tooltip: era name, record, win%, score, mood label, and the gap vs the line in points). Clicking opens the team page at that season/week.

### Area 4: Accessibility & theme for both charts
- D-16a Each chart is a `ChartFrame` (headline, dek, SOURCE/NOTES footer) built with `withTheme`, `valueAxis` and `baseAxis`. Both charts get a collapsed `<details>` "Show as table" under the chart: a rule-separated table (rank, logo, team link, the plotted values). This gives keyboard and screen-reader access to every mark's link.
- D-16b Dark mode: logos already sit on the light disc inside TeamLogo; in Plot image marks, draw a `dot` disc (`--logo-disc`) under each logo in dark mode only (r ≈ size/2 + 2). Gridlines and diagonals use tokens.

### Area 5: Win totals on the team page (DATA-03)
- D-17 Pipeline export tweak (display-only, `export.py` only): each `teams/{F}.json` gains `expectation: { season[], exp_total[] (1 dp), source[] ('vegas'|'model'), reg_games[] }` taken from the week-0 rows of `derived["features"]` (`exp_total`, `expectation_source`). `reg_games` is that team-season's actual regular-season game count, so pace handles the 2022 BUF/CIN 16-game seasons. Nothing reads it back into the score. Add a test in `test_export.py`. Then regenerate the site data once from cache with `uv run fgs export` (no refresh/network). The golden pin `3ac3c2b5…` must be unchanged before and after, and `uv run pytest` must pass.
- D-18 Web: add a `TeamFile` type and a `loadTeam(meta, F)` loader (session cache keyed by `generated_at`, evicted on failure, the same pattern as `loadGames`).
- D-19 New `WinTotals.svelte` section on the team page for the viewed season, titled "Preseason expectations". It is a compact HTML number line (0 to reg_games wins) with up to three labeled markers plus a text list (no Plot needed):
  - **Vegas preseason**: line from `vegas_win_totals`. Labels: when `used_in_score` is true (2003–2020): "Vegas preseason (used in score)". When false (2021+): "Vegas preseason (display only, not used in score)". When `line_type === 'preseason_open'` (2026): append "· opening line, not the final preseason number".
  - **Model preseason (used in score)**: `exp_total` when `source === 'model'`. For Vegas-sourced seasons the score uses a league-normalized Vegas line, so the model row is omitted and a note says "The score uses this line, normalized to the league average."
  - **Pace**: (W + 0.5·T) / GP × reg_games, 1 dp: "On pace for 12.8 wins (6–2 after 8 games)". After the regular season it becomes "Finished 13–4". At week 0 it reads "No games yet."
  - 1999–2002 (no Vegas line): only the model row and pace.
- D-20 Source line for this block: `SOURCE: NFLVERSE (2003–2020) · COVERS / DRAFTKINGS (2021+)`. `ChartFrame` gains an optional `source` prop (default unchanged); add a chartFrame test.
- D-21 Placement: after the "Why" factor block and before "Recent games". On wide screens it can sit in the right column, which helps the Phase 12 "unbalanced team page" finding (#6) at no extra cost.

### Area 6: Phase 12 UI-review leftovers (cheap only)
- D-22 #4 Records rows span the full 960px frame, with consistent streak/record cell widths (grid columns with fixed mono widths).
- D-23 #7 History end-mark logo: add top inset/margin so a logo at y=100 is not clipped at 375px.
- D-24 #8 Rank delta: replace `#▲1` / `#–` with readable text, e.g. "▲1 spot" / "▼2 spots" / "no change", plus an `aria-label` "Up 1 spot in rank". Update the format tests.
- D-25 #9 Callout cards: the action row sits at the bottom of each card (flex column, `margin-top: auto`) so buttons line up across a row at 1280.
- Skipped unless trivially adjacent: #5 (saddest/happiest lead), #10 (callout count at 375), #11 (methodology table). Log them as still deferred.

### Verification
- D-26 `npm test`, `npm run check`, `npm run build` pass under Node 24. `cd pipeline && uv run pytest` passes (pipeline touched). The golden pin is unchanged.
- D-27 Playwright MCP at 1280 and 375, light and dark: explore (latest, plus a historical week such as 2025/10), week-0 empty state, team page win totals (2026 opener, a 2021–2025 display-only season, a 2003–2020 used-in-score season). No horizontal scroll at 375. Save ≤ 6 screenshots in `screenshots/` in the phase dir.

### Claude's Discretion
- Exact pixel sizes, opacities, diagonal spacing and label positions, within the constraints above.
- Whether to show the regression line's equation (default: no).
- Table-view column choice and sort order (default: sorted by the chart's y value).
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lib/epa.ts` `seasonToDate(file, week)`: play-weighted season-to-date EPA/SR per franchise (EXPL-01, tested).
- `lib/data.ts`: `loadEpa`, `loadSeason`, `loadLatest`, `findSeason`, `isLatest`; the cache pattern to copy for `loadTeam`.
- `lib/plotTheme.ts`: `withTheme`, `valueAxis`, `baseAxis`, `teamStroke`, `HIGHLIGHT_WIDTH`, `LOGO_MARK_PX`. `ChartFrame.svelte` (headline/dek/SOURCE/NOTES).
- `TeamLogo.svelte`, `lib/logos.ts` (`logoSrc`), `lib/logoSwitch.ts` (`VITE_LOGOS`), `highlightColor`, `lib/teamNames.ts` (`eraName`, `eraText`, `isActiveFranchise`).
- `Scrubber.svelte` (season/week/latest), `lib/format.ts` (`carryWeek`, `formatRecord`, `formatDelta`, `moodToken`).
- `lib/myteam.svelte.ts` (`myTeam.abbr`), `validMyTeam`.
- `HistoryChart.svelte`: the Plot-in-`$effect` + `bind:clientWidth` + `replaceChildren` pattern and the image-mark end logo.
- `teams/{F}.json` already carries `vegas_win_totals` {season, line, over_odds, under_odds, line_type ('nflverse'|'preseason_close'|'preseason_open'), source, used_in_score}.

### Established Patterns
- Svelte 5 runes; hash routing via `route.svelte.ts` (`go`, `replace`); App validates routes against meta and redirects bad ones.
- Tokens only; mono tabular numbers; rule-separated sections; no cards or shadows.
- Pure logic in `lib/*.ts` with vitest tests beside it.

### Integration Points
- `App.svelte` route switch plus the `SiteHeader current` prop; `lib/router.ts` Route union.
- `TeamPage.svelte` sections ("Why", "Recent games", "This season").
- `pipeline/src/fgs/export.py` `build_export` → `files["teams/{fid}.json"]`; `derived["features"]` has `exp_total` and `expectation_source` per row.
- Deferred UI items: `RecordsPage.svelte`, `HistoryChart.svelte`, `Delta.svelte`/`format.ts` `formatDelta`, `CalloutCard.svelte`.
</code_context>

<specifics>
## Specific Ideas

- The EPA tiers chart follows community conventions (rbsdm/nfelo tiers): logos, diagonals, crosshairs, plain-word quadrants.
- "Record vs evidence", never "lucky/unlucky".
- The example the label should support: "Vegas said 6.5, they're on pace for 11."
</specifics>

<deferred>
## Deferred Ideas

- Season-to-date vs last-8-games window toggle on the EPA scatter.
- Opponent-adjusted EPA.
- Share cards for Explore charts (Phase 14 covers teams and callouts only).
- Phase 12 UI items #5, #6 (beyond the win-totals placement), #10, #11.
- Callout-team annotations on the record-vs-evidence chart.
</deferred>

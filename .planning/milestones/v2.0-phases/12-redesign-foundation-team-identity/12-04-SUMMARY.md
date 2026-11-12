---
phase: 12-redesign-foundation-team-identity
plan: 04
subsystem: web
tags: [charts, observable-plot, theme, logos, chartframe]
requires:
  - phase: 12-01
    provides: tokens (--grid, --font-mono, --logo-disc) and global -grid CSS rule
  - phase: 12-02
    provides: logosEnabled/logoSrc helpers and local small logos
  - phase: 12-03
    provides: plotTheme module and ChartFrame component
provides:
  - All three Plot charts (HistoryChart, MethodologyChart, Sparkline) built through withTheme
  - HistoryChart single logo end mark (LOGO-02 chart surface)
  - ChartFrame around the history and methodology charts with UI-SPEC copy
  - Raw-source scan test guarding the theme contract
affects: [12-05, 12-06, 12-07, 13, 14]
tech-stack:
  added: []
  patterns:
    - "Plot.plot(withTheme({...})) with valueAxis/baseAxis for every chart"
    - "Re-measure canvas text gutters after document.fonts.ready"
key-files:
  created: []
  modified:
    - web/src/components/HistoryChart.svelte
    - web/src/components/HistoryPage.svelte
    - web/src/components/MethodologyChart.svelte
    - web/src/components/Sparkline.svelte
    - web/src/lib/plotTheme.test.ts
key-decisions:
  - "MethodologyChart x grid comes from valueAxis (grid:true). Plot names the inferred grid group `x-grid`, which the global `-grid` CSS rule matches, so the explicit Plot.gridX fallback was not needed"
  - "MethodologyChart wraps candidate names with Plot's monospace metrics because the theme font is now mono"
  - "History firstSeason = min of meta.seasons[].season (fallback 1999)"
patterns-established:
  - "Chart headlines/deks/notes live in ChartFrame; the Plot options never set title/subtitle/caption"
requirements-completed: [DESIGN-02, DESIGN-03, DESIGN-04, LOGO-02]
duration: 5min
completed: 2026-11-12
---

# Phase 12 Plan 04: Charts on the Shared Theme Summary

**HistoryChart, MethodologyChart and Sparkline now build their options through `withTheme`. The history chart puts one team logo at the end of the highlighted line, and the history and methodology charts sit inside ChartFrame with the UI-SPEC headline, dek and SOURCE/NOTES footer.**

## Performance

- **Duration:** about 5 min
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- **HistoryChart:**
  - Options go through `withTheme`, with `baseAxis` on x and `valueAxis` on y.
  - The y=0 rule and the tick-colour CSS override are removed.
  - Background lines use `BACKGROUND_STROKE`. The highlighted line uses `teamStroke(color)` at `HIGHLIGHT_WIDTH`.
  - One `Plot.image` logo sits at the last highlighted point: 24px at widths of 900 or more, otherwise 20px. In dark mode it sits on a `--logo-disc` dot. The label is offset past the logo and the gutter grows by `logoPx + 4`.
  - Gutters are measured again after `document.fonts.ready`.
  - The legend is mono and uppercase, with square swatches.
- **HistoryPage:**
  - New page dek: "Every team's feel-good score, every week since {firstSeason}…".
  - The chart is wrapped in ChartFrame using the "How {name} fans should have felt since {firstSeason}" headline, the dek and the notes.
  - The h2 is now bold. Only current names are used (no eraName).
- **MethodologyChart:**
  - Options go through `withTheme`, with a `valueAxis` x grid. The explicit `gridX` is removed.
  - The Elo reference line is `--text-muted`, dashed.
  - The figure/figcaption is replaced by ChartFrame with metric-specific headline and dek ("Which method ranks teams best" / "Which method calls single games best"). The notes carry the interval sentence.
  - Props are unchanged.
- **Sparkline:** uses `withTheme` with `axis: null`. The baseline is muted and dashed, the min/max labels are `CHART_FONT_PX`, and the colour goes through `teamStroke`.
- **plotTheme.test.ts:** a new `chart sources use the theme` block scans the three chart sources for:
  - `withTheme(`
  - the plotTheme import
  - no title, subtitle or caption keys
  - ChartFrame in MethodologyChart
  - exactly one `Plot.image(` in HistoryChart

## Task Commits

1. **Task 1: HistoryChart + HistoryPage onto theme, logo end mark, ChartFrame** - `e1fc4ca` (feat)
2. **Task 2: MethodologyChart and Sparkline onto theme; source-scan test** - `dc367e9` (feat)

## Decisions Made
- **Grid path:** the methodology x grid comes from `valueAxis` (`grid: true`). Plot 0.6.19 labels inferred grid marks `${k}-grid`, checked in `dist/plot.js`, and the plan-01 global rule targets `g[aria-label$='-grid']`. The `gridX` fallback was not used. Plan 07 should still confirm visually.
- `FONT_PX` in MethodologyChart is now `CHART_FONT_PX` (12) to match the theme. `Plot.axisY` gets `monospace: true` so line wrapping uses mono character widths.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Mono metrics for wrapped methodology labels**
- **Found during:** Task 2
- **Issue:** Plot's default line-wrap heuristic assumes a proportional font. The theme font is now mono, which is wider, so candidate names could overflow the left margin.
- **Fix:** Added `monospace: true, fontFamily: 'var(--font-mono)'` to the `Plot.axisY` mark.
- **Files modified:** web/src/components/MethodologyChart.svelte
- **Commit:** dc367e9

The plan's fallback for a `metric` value other than the two named ones is implemented, but it can't be reached: `ChartMetric` is `'spearman_n8' | 'brier'`.

## Issues Encountered
- I tried an ad hoc jsdom render to confirm the x grid, but there is no DOM test library in web. I stopped it and checked Plot's dist source instead. Nothing was added to the repo.

## Known Stubs
None.

## Next Phase Readiness
Every Plot chart shares one theme. Plan 07 should check visually that the logo end mark, the dark-mode disc and the methodology x gridlines render.

## Self-Check: PASSED
- FOUND: all five modified files
- FOUND: commits e1fc4ca, dc367e9
- Gate: npm test (212 passed), npm run check (0 errors), npm run build green

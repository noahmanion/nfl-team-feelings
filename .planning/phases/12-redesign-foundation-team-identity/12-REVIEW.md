---
phase: 12-redesign-foundation-team-identity
reviewed: 2026-11-11T22:45:00Z
depth: standard
iteration: 2
files_reviewed: 43
files_reviewed_list:
  - README.md
  - web/package.json
  - web/vite.config.ts
  - web/scripts/logos-sm.sh
  - web/src/App.svelte
  - web/src/app.css
  - web/src/main.ts
  - web/src/components/Badge.svelte
  - web/src/components/BoardHeading.svelte
  - web/src/components/BoardRow.svelte
  - web/src/components/CalloutCard.svelte
  - web/src/components/CalloutCards.svelte
  - web/src/components/ChartFrame.svelte
  - web/src/components/Delta.svelte
  - web/src/components/FactorBars.svelte
  - web/src/components/HistoryChart.svelte
  - web/src/components/HistoryPage.svelte
  - web/src/components/MethodologyChart.svelte
  - web/src/components/MethodologyPage.svelte
  - web/src/components/MoodBoard.svelte
  - web/src/components/MoodLabel.svelte
  - web/src/components/MoversStrip.svelte
  - web/src/components/PinButton.svelte
  - web/src/components/RecentGames.svelte
  - web/src/components/RecordsPage.svelte
  - web/src/components/Scrubber.svelte
  - web/src/components/SiteFooter.svelte
  - web/src/components/SiteHeader.svelte
  - web/src/components/Sparkline.svelte
  - web/src/components/StatusPanel.svelte
  - web/src/components/TeamChip.svelte
  - web/src/components/TeamLogo.svelte
  - web/src/components/TeamPage.svelte
  - web/src/lib/brand.test.ts
  - web/src/lib/chartFrame.test.ts
  - web/src/lib/history.ts
  - web/src/lib/logoSwitch.ts
  - web/src/lib/logos.test.ts
  - web/src/lib/logos.ts
  - web/src/lib/plotTheme.test.ts
  - web/src/lib/plotTheme.ts
  - web/src/lib/teamLogo.test.ts
  - web/src/lib/teamNames.test.ts
  - web/src/lib/teamNames.ts
findings:
  critical: 0
  warning: 0
  info: 8
  total: 8
status: clean
---

# Phase 12: Code Review Report (iteration 2)

**Reviewed:** 2026-11-11T22:45:00Z
**Depth:** standard
**Files Reviewed:** 43
**Status:** clean (no Critical or Warning findings; Info only)

## Narrative Findings (AI reviewer)

## Summary

This re-review covers the four fix commits for iteration-1 findings WR-01 to WR-04 (`04b2ccc`, `4885f69`, `cd6c744`, `893f9d0`), plus the same file scope as iteration 1, `web/vite.config.ts`, `web/src/App.svelte`, the new `web/src/lib/logoSwitch.ts`, and `README.md`. All four fixes are correct, and I found no regressions.

Checks I ran:
- `vitest run` passes (213 tests).
- `VITE_LOGOS=OFF vite build` into a scratch outDir produced a `dist` with no `logos/` directory. That confirms the plugin works with an uppercase value set only through `process.env`. `og-default.png` and `favicon.svg` contain no team marks.

**Fix verification:**
- **WR-01 (fixed):** `dropLogos()` reads `config.env.VITE_LOGOS` in `configResolved`. Vite's `loadEnv` merges prefixed `process.env` keys with `.env*` files, so both sources are covered. The plugin removes `<outDir>/logos` in `closeBundle`, which runs after Vite has copied `public/`. The predicate lives in `logoSwitch.ts` and is shared with `logosEnabled`. A test asserts that the two agree. `tsconfig.node.json` uses `allowImportingTsExtensions`, so the `.ts` import in `vite.config.ts` type-checks. No other source path references `/logos/` (no CSS `url()`, no `index.html` link).
- **WR-02 (fixed):** `App.svelte` filters both `rows` and `callouts` once when it builds `shown`. `BoardHeading` count, `CalloutCards` (via `shownCards`), `MoversStrip` (via `shownMovers`) and `MoodBoard` all read the filtered data. `Callout.franchise` is a required `string`, so the filter cannot drop league-level callouts by accident. The filter uses `target.season`, which matches the `season` stored in `shown`.
- **WR-03 (fixed):** The headline and the dek now both require `hasPoints && ok(row.score)`, so a non-finite score is never interpolated.
- **WR-04 (fixed):** `drawLogo` requires `src === logoOk`. The preload effect handles three cases correctly:
  - **Team switch:** a stale `logoOk` for the old URL never matches the new `src`.
  - **Failed load:** a `404` falls back to no disc, no label gap and no gutter widening.
  - **Stale results:** the `live` guard ignores late loads after cleanup.

  Reading `logoOk` inside the plot `$effect` makes the chart redraw when the image loads.

## Info

### IN-01: History chart redraws and shifts once the logo loads

**File:** `web/src/components/HistoryChart.svelte:67-84, 114-117`
**Issue:** The first render now always draws without the logo. When the image loads, `teamCol` grows by `logoPx + 4` and the label moves by `labelDx`, so the plot reflows a moment after first paint. A cached image makes the reflow brief, but it can still be seen on a slow first load. This is cosmetic and is the expected trade-off of the WR-04 fix.
**Fix (optional):** Reserve the logo gutter whenever `logoUrl` is non-null and only defer the `image`/`dot` marks. The trade-off is a little empty space if the load fails.

### IN-02: Board rank numbers can still skip a value for a filtered HOU row

**File:** `web/src/App.svelte:178`, `web/src/components/BoardRow.svelte`
**Issue:** The fix report calls this out: `row.rank` comes from the pipeline, so a pre-2002 HOU row, if one were ever emitted, would leave a gap in the ranks. Current pipeline output has no such rows, so this cannot happen today.
**Fix:** If it ever matters, derive the displayed rank from the index in the filtered list, or have the pipeline exclude these rows.

### IN-03: Redundant second filter in MoodBoard

**File:** `web/src/components/MoodBoard.svelte:35`
**Issue:** `visibleRows` re-applies `isActiveFranchise` to rows that `App.svelte` has already filtered. It is harmless, but the rule now lives in two places.
**Fix:** Keep it as a documented defensive guard, or drop it and rely on the upstream filter.

### IN-04 to IN-08: iteration-1 Info items carried forward (unchanged, out of fix scope)

- **IN-04 (was IN-01):** `TeamLogo.svelte:28-42`. The `alt` prop is lost on the chip fallback. No current caller passes it.
- **IN-05 (was IN-02):** `CalloutCard.svelte:18-21`, `MoversStrip.svelte:27-29`. Streak callouts name Washington by the callout season. `RecordsPage` uses `start_season` (D-18).
- **IN-06 (was IN-03 and IN-04):** `TeamChip.svelte:8` and `plotTheme.ts:19` validate hex colors differently. Separately, `withTheme` (`plotTheme.ts:42-46`) drops a string-valued `style`.
- **IN-07 (was IN-05):** `scripts/logos-sm.sh` needs macOS `sips` and has no guard and no `nullglob`.
- **IN-08 (was IN-06):** `MethodologyPage.svelte:72` gives the page title and the section headings the same `h2` level.

---

_Reviewed: 2026-11-11T22:45:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

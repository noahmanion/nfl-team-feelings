---
phase: 13-explore-charts-win-totals-display
plan: 06
subsystem: web
tags: [explore, router, nav, a11y, svelte]
requires:
  - 13-02 (lib/explore.ts pure logic)
  - 13-05 (EpaScatter, RecordScatter)
provides:
  - "#/explore and #/explore/{season}/{week} routes (exploreHash)"
  - ExplorePage (Scrubber + two ChartFrame sections + states)
  - ExploreTable ("Show as table" details view)
  - noLuck.test.ts wording guard (D-15)
affects:
  - web/src/App.svelte
  - web/src/components/SiteHeader.svelte
tech-stack:
  added: []
  patterns: [HistoryPage live-guard load effect with retry counter, module-script exported types for component props]
key-files:
  created:
    - web/src/components/ExplorePage.svelte
    - web/src/components/ExploreTable.svelte
    - web/src/lib/noLuck.test.ts
  modified:
    - web/src/lib/router.ts
    - web/src/lib/router.test.ts
    - web/src/App.svelte
    - web/src/components/SiteHeader.svelte
    - web/src/lib/sep.test.ts
decisions:
  - "exploreHash(season) with no week returns #/explore; #/explore/{season} parses with season only and App replaces it with #/explore"
  - "ExplorePage falls back to the latest week itself when given an invalid season/week, so it renders sanely during the frame before App's replace()"
  - "EPA empty checks that don't need the EPA file (week 0, season without pbp) run before the EPA load/error states"
  - "League means for the EPA crosshairs are computed over the plotted teams' aggregates only"
metrics:
  duration: ~4 min
  completed: 2026-11-11
  tasks: 3
  files: 8
---

# Phase 13 Plan 06: Explore page, route, nav and tables Summary

The `#/explore` page now works. It has an explore route and `exploreHash`, an "Explore" nav item placed between "Mood over time" and "Records", and an `ExplorePage` where one Scrubber drives both the EPA scatter and the record-vs-evidence scatter. Each chart has a collapsed "Show as table" view, and a vitest guard keeps "luck" out of the Explore sources.

## What was built

- **Router (Task 1, TDD):** Added the `{ kind: 'explore'; season?; week? }` route, an `EXPLORE` regex checked before methodology, and `exploreHash(season?, week?)`. The tests cover the bare and trailing-slash forms, season plus week, season alone, the invalid `#/explore/abc`, hash building and round trips.
- **ExploreTable (Task 1):** A generic `<details class="as-table">` driven by column config. It has a rank column and a Team cell with TeamLogo 20, an accent abbr link and a muted era name (hidden below 640px). Numeric cells are mono and right-aligned. `wideOnly` columns drop below 640px. Cells take up/down/muted tones, the pinned team's row gets the my-team tint and outline, and the caption is visually hidden.
- **ExplorePage (Task 2):**
  - Page head, Scrubber, and two rule-separated sections.
  - Rows come from `latestRows` for the latest week, otherwise from `loadSeason`. Both paths are filtered by `isActiveFranchise`.
  - EPA aggregation is `seasonToDate(regOnly(file), w)`, loaded only for seasons in `meta.epa_seasons`.
  - States:
    - Loading: a placeholder at `chartHeight` height.
    - Empty: `.chart-empty` with `emptyCopy` for the no-games, no-pbp and no-week cases.
    - Snapshot error: one StatusPanel that replaces both sections.
    - EPA error: a StatusPanel inside the EPA frame only.
  - The EPA dek adds the early-season sentence for weeks 1–3. The notes end with "Regular season only." The record dek comes from `recordDek`.
  - Table sort orders: net EPA descending for the EPA table, score descending for the record table. The Gap tone is muted when |gap| < 0.5.
  - The Scrubber writes `#/explore` whenever the target is the latest week.
- **Wiring (Task 3):** In App, a well-formed explore URL with an unknown season or out-of-range week (or a season with no week) does `replace('#/explore')`. A malformed one like `#/explore/abc` takes the existing invalid-route path. App also has an explore render branch with a loading fallback, and passes `current = 'explore'` to SiteHeader.

## Verification

- `npm test`: 274 passed, 23 files. This includes the new router cases and `noLuck.test.ts`, which runs 3 tests over 5 files.
- `npm run check`: 0 errors, 0 warnings.
- `npm run build`: passes.
- Acceptance greps:
  - ExplorePage has `seasonToDate(regOnly` once and two `<ExploreTable`.
  - "luck" and "contribs" don't appear in ExplorePage.
  - App has four matches for `kind === 'explore'`.
  - The nav order is Mood over time (line 18), Explore (21), Records (24).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated sep.test.ts for the fourth nav separator**
- **Found during:** Task 3
- **Issue:** `sep.test.ts` hard-coded 3 `<Sep />` items in the nav. Adding Explore makes it 4.
- **Fix:** Changed the expected counts from 3 to 4. The structural assertions (no dangling dot, nowrap item) are unchanged.
- **Files modified:** web/src/lib/sep.test.ts
- **Commit:** 8382f12

### Minor contract notes

- During loading the UI-SPEC says to hide the footer. ChartFrame always renders its SOURCE line, so loading frames omit the dek and notes but still show `SOURCE: NFLVERSE · FEEL-GOOD SCORE`. This is cosmetic, and plan 07's browser pass can decide whether it matters.
- In-browser behaviour (clicks, touch arming, 375px layout, dark mode) was not exercised here. Plan 07 covers it.

## TDD Gate Compliance

- RED: `test(13-06): add failing tests for explore route and exploreHash` (4 failing, as expected)
- GREEN: `feat(13-06): explore route, exploreHash and ExploreTable view` (bfaf33d)

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 (RED) | 0c1f7da | test(13-06): add failing tests for explore route and exploreHash |
| 1 | bfaf33d | feat(13-06): explore route, exploreHash and ExploreTable view |
| 2 | ebd8341 | feat(13-06): ExplorePage with both scatters, states and table views |
| 3 | 8382f12 | feat(13-06): wire #/explore route and nav, add no-luck wording guard |

## Known Stubs

None. Every chart, table and dek is fed from real snapshot and EPA data.

## Self-Check: PASSED

---
phase: 13-explore-charts-win-totals-display
plan: 04
subsystem: web
tags: [win-totals, team-page, data-03, svelte, chartframe]
requires:
  - web/src/lib/winTotals.ts winTotalsView (13-02)
  - web/public/data/teams/{F}.json vegas_win_totals + expectation (13-01)
provides:
  - web/src/lib/types.ts TeamFile
  - web/src/lib/data.ts loadTeam(meta, franchise)
  - web/src/components/ChartFrame.svelte optional source prop
  - web/src/components/WinTotals.svelte
affects: [13-07]
tech-stack:
  added: []
  patterns: [display-only extra sections fail silently (section omitted), HTML number line instead of Plot for a 3-marker strip]
key-files:
  created:
    - web/src/components/WinTotals.svelte
    - web/src/lib/winTotalsRender.test.ts
  modified:
    - web/src/lib/types.ts
    - web/src/lib/data.ts
    - web/src/components/ChartFrame.svelte
    - web/src/lib/chartFrame.test.ts
    - web/src/components/TeamPage.svelte
decisions:
  - "The WinTotals loading state renders inside ChartFrame with the headline, so the heading doesn't jump in when data arrives"
  - "The pace-dot color falls back to var(--text) during SSR (no document), so the component renders in svelte/server tests"
  - "teamFile state is keyed by team: a stale file from the previous team counts as loading, not as data"
metrics:
  duration: 5m
  completed: 2026-11-11
  tasks: 2
  files: 7
---

# Phase 13 Plan 04: Win totals on the team page Summary

The team page now has a "Preseason expectations" section. It shows an HTML number line (model ring, Vegas bar, team-colored pace dot) and a legend with labels that say whether each number is used in the score: Vegas 2003–2020 is "(used in score)", Vegas 2021+ is "(display only, not used in score)", and the model row is "(used in score)". The data comes from `teams/{F}.json` through a new session-cached `loadTeam`. If that file fails to load, the section is omitted and the rest of the page works.

## Tasks

| # | Task | Commits | Files |
|---|------|---------|-------|
| 1 | TeamFile type, loadTeam, ChartFrame source prop + test (TDD) | e08353f (RED), 397bdea (GREEN) | types.ts, data.ts, ChartFrame.svelte, chartFrame.test.ts |
| 2 | WinTotals.svelte and TeamPage placement | 7da202c | WinTotals.svelte, TeamPage.svelte, winTotalsRender.test.ts |

## What was built

- `TeamFile extends TeamMeta` (franchise, history, vegas_win_totals, expectation?). It is structurally assignable to `WinTotalsInput`.
- `loadTeam(meta, F)` uses a Map cache keyed by `${generated_at}|${F}` and evicts the key on rejection, the same as `loadGames`.
- `ChartFrame` takes an optional `source`. The default footer is unchanged.
- `WinTotals.svelte` gets every bit of copy and every position from `winTotalsView`. It tracks the color scheme with matchMedia and picks the dot color with `highlightColor`.
- `TeamPage` uses a `$effect` with a live guard. A new `div.right` wraps the Preseason expectations section and Recent games, so on narrow screens the order is Why, Expectations, Recent games, and at ≥1024px Expectations sits at the top of the right column.

## Deviations from Plan

- **[Plan-checker suggestion, adopted]** Added `web/src/lib/winTotalsRender.test.ts`, an SSR smoke test covering the 2021+ display-only label, the 2003–2020 used-in-score label, finished/pace rows, loading, and the no-data omission.
- **[Rule 1 - Bug]** The first placement of the new derived values came before the `ok` helper was declared, which made svelte-check fail with "used before declaration". I moved them below `ok`, before committing. Fixed in 7da202c.

## TDD Gate Compliance

RED `test(13-04)` e08353f, then GREEN `feat(13-04)` 397bdea. No refactor needed.

## Verification

`npm test` passed 266/266 across 22 files. `npm run check` reported 0 errors and 0 warnings. `npm run build` succeeded. Every acceptance grep matches. Visual checks for the three eras are left to plan 07.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: web/src/components/WinTotals.svelte, web/src/lib/winTotalsRender.test.ts
- FOUND commits: e08353f, 397bdea, 7da202c

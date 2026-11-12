---
phase: 13-explore-charts-win-totals-display
plan: 03
subsystem: web
tags: [ui-polish, a11y, css, phase-12-leftovers]
requires: []
provides:
  - "formatRankDelta(v) -> { text, dir, aria } in web/src/lib/format.ts"
  - "Readable rank deltas on the board ('▲1 spot' / '▼2 spots' / 'no change')"
affects: [BoardRow, MoodBoard, RecordsPage, HistoryChart, CalloutCards]
tech-stack:
  added: []
  patterns: ["CSS subgrid so list rows share one column template"]
key-files:
  created: []
  modified:
    - web/src/lib/format.ts
    - web/src/lib/format.test.ts
    - web/src/components/Delta.svelte
    - web/src/components/BoardRow.svelte
    - web/src/components/MoodBoard.svelte
    - web/src/components/RecordsPage.svelte
    - web/src/components/HistoryChart.svelte
    - web/src/components/CalloutCards.svelte
    - web/src/components/CalloutCard.svelte
decisions:
  - "Rank delta reads in words without a '#' prefix; aria-label carries 'Up N spots in rank'; board last column widened 72px -> 88px"
  - "Records lists use a grid on ol.rows (28px | 1fr | max-content) with li and a.row subgridding, so the value column is one width per list"
metrics:
  duration: "~2 min"
  completed: 2026-11-11
  tasks: 2
  files: 9
---

# Phase 13 Plan 03: Phase 12 UI-review leftovers Summary

Rank deltas now read "▲1 spot" / "▼2 spots" / "no change" with an aria label. Records lists span the full width and share one value column per list through subgrid. The History chart adds top margin so the logo at y=100 isn't clipped. Callout card buttons line up along the bottom of each row.

## Tasks

| Task | Name | Commits |
| ---- | ---- | ------- |
| 1 | Readable rank delta (D-24) and board column width | d216ea6 (test, RED), c164f97 (feat, GREEN) |
| 2 | Records full width (D-22), history logo inset (D-23), callout alignment (D-25) | 208860e |

## Verification

- `npx vitest run src/lib/format.test.ts`: 28/28 tests pass. The 3 new formatRankDelta cases failed in RED and pass in GREEN.
- `npm test`: 261 tests pass. `npm run check`: 0 errors, 0 warnings. `npm run build`: OK.
- Every acceptance grep passes. Visual confirmation at 1280 and 375 is deferred to plan 07's Playwright sweep.

## Deviations from Plan

None. The plan was executed exactly as written. No existing test pinned the old `#▲1` rendering, so no test assertion needed updating.

## Deferred (still open from 12-UI-REVIEW)

- #5, #6 (everything beyond win-totals placement), #10 and #11 stay deferred under CONTEXT Area 6.

## TDD Gate Compliance

The RED commit (`test(13-03)` d216ea6) comes before the GREEN commit (`feat(13-03)` c164f97). No refactor commit was needed.

## Self-Check: PASSED

- The commits d216ea6, c164f97 and 208860e exist in git log.
- All 9 modified files exist.

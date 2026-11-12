---
phase: 07-draft-aware-offseason
plan: 02
subsystem: web
tags: [chart, board, team-page, offseason, draft]
requires: []
provides:
  - "connectors(h, xs, team?) -> Connector[] (web/src/lib/history.ts)"
  - "changeText(row, week) (web/src/lib/format.ts)"
  - "DraftInfo, Row.draft, Meta.offseason contract types"
affects: [07-04]
tech-stack:
  added: []
  patterns: ["Plot.link for dashed offseason segments over the existing NaN season gap"]
key-files:
  created: []
  modified:
    - web/src/lib/types.ts
    - web/src/lib/history.ts
    - web/src/lib/history.test.ts
    - web/src/lib/format.ts
    - web/src/lib/format.test.ts
    - web/src/components/HistoryChart.svelte
    - web/src/components/HistoryPage.svelte
    - web/src/components/BoardRow.svelte
    - web/src/components/BoardHeading.svelte
    - web/src/components/TeamPage.svelte
decisions:
  - "Connectors only for the highlighted team; background lines keep their NaN gap"
  - "A null score_delta reads 'No change, preseason.' in any week (same as the old BoardRow behavior), so today's data and first-season/expansion rows degrade cleanly"
metrics:
  duration: ~6min
  completed: 2026-11-11
  tasks: 2
  files: 10
---

# Phase 7 Plan 02: Offseason Visibility (web) Summary

Adds a dashed Plot.link connector that carries the highlighted team's line across each offseason gap. Week-0 board and team deltas now read "vs end of last season", and the team page shows the pipeline's draft line. All of it is coded against the Phase 7 JSON contract and falls back cleanly on today's data.

## Tasks

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | Pure helpers: connectors(), changeText(), contract types (with vitest) | b9817d0 |
| 2 | Components: dashed connector, board week-0 wording, team delta caption + draft line | 7c2decc |

## What changed

- `connectors()` walks back to the last non-null score of season S, staying inside S, and ends at week 0 of S+1. It returns no segment when either end is missing. Tests cover the fixture, the team filter, missing ends and three seasons.
- `changeText()` moved out of BoardRow into format.ts. In-season wording is unchanged. Week 0 now reads "Up 5 points, up 2 spots vs end of last season." and "No change from the end of last season." A null delta still reads "No change, preseason."
- HistoryChart takes a `connectors` prop and draws `Plot.link` after the highlighted line with team colour, width 1.5, dash 3,3 and opacity 0.8. The aria-label now mentions the dashed segments.
- BoardHeading's week-0 note now adds "Change is vs the end of last season."
- TeamPage: at week 0, a muted label-size `.delta-note` "vs end of last season" appears under the delta when it is finite. A muted `.draft-note` paragraph after the blurb shows `row.draft.text` when present. Only tokens are used, no new colours.

## Verification

- `npm test`: 86 passed. `npm run check`: 0 errors, 0 warnings. `npm run build`: ok (Node 22).
- Browser check at 375 and 1280 px is left to the orchestrator, per 07-VALIDATION.

## Deviations from Plan

None. The plan was executed as written. Task 1 was committed as one feat commit with its tests, as the plan specified, not as separate RED/GREEN commits.

## Known Stubs

None. The draft line and the week-0 delta caption render only when 07-04 data provides them, which is intended graceful degradation.

## Self-Check: PASSED
- Files: all 10 modified files exist; commits b9817d0 and 7c2decc are in git log.

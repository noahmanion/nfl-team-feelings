---
phase: 13-explore-charts-win-totals-display
plan: 02
subsystem: web
tags: [explore, epa, win-totals, pure-logic, vitest, tdd]
requires:
  - web/src/lib/epa.ts seasonToDate / EpaAgg
  - web/src/lib/teamNames.ts, web/src/lib/logos.ts
provides:
  - web/src/lib/explore.ts (EpaPoint, RecordPoint, Line, EpaEmpty + 22 pure functions)
  - web/src/lib/winTotals.ts (WinTotalsInput, LegendRow, WinTotalsView, winTotalsView)
affects: [13-04, 13-05, 13-06]
tech-stack:
  added: []
  patterns: [pure tested view-model modules feeding thin Svelte components]
key-files:
  created:
    - web/src/lib/explore.ts
    - web/src/lib/explore.test.ts
    - web/src/lib/winTotals.ts
    - web/src/lib/winTotals.test.ts
  modified: []
decisions:
  - "signed() leaves a value that rounds to zero unsigned (−0.0001 -> 0.00), so no stray minus on 0.00"
  - "Tooltip/legend game counts pluralize (1 game, 8 games)"
  - "epaTicks below 640px keeps every 2nd (then 4th) integer step, so 0 always stays a tick"
  - "recordDek needs both a positive and a negative gap, otherwise the fallback dek is used"
metrics:
  duration: 4m
  completed: 2026-11-11
  tasks: 2
  files: 4
---

# Phase 13 Plan 02: Explore and win-totals pure logic Summary

This plan adds two pure, test-first TypeScript modules. `lib/explore.ts` produces everything the EPA and record-vs-evidence scatters show: the REG-only EPA join, competition ranks, play-weighted league means, the OLS line and gaps, the generated dek, U+2212/en-dash formats, ticks, diagonals, the touch-arming `tapAction`, the tooltip lines and the empty states. `lib/winTotals.ts` builds the full Preseason-expectations view model: Vegas, model and pace rows, with the deks, notes and source line for each era.

## Tasks

| Task | Name | Commits |
|------|------|---------|
| 1 | lib/explore.ts with tests | 08f0a2f (RED), ad57763 (GREEN) |
| 2 | lib/winTotals.ts with tests | 47caafc (RED), 2f2f4db (GREEN) |

Verification: explore.test.ts has 30 tests and winTotals.test.ts has 12, all green. The full `npm test` run passes 258 tests, and `tsc --noEmit` is clean. All acceptance greps pass: there is no "luck" or "contribs" in explore.ts, it has one `tapAction` export and uses a literal U+2212, and the winTotals copy strings are present.

## Deviations from Plan

These are small refinements within the plan's discretion. None changes the contract:
- `signed` returns an unsigned string when the value rounds to zero. Without this, a tiny negative would print as `−0.00`.
- Counts are pluralized (`1 game`, `after 1 game`). The UI-SPEC only shows plural examples.
- `finished` uses `GP >= reg_games` as a guard. It is the same as `===` for real data.

## TDD Gate Compliance

Both tasks have a `test(...)` RED commit followed by a `feat(...)` GREEN commit. Both RED runs failed because the module was missing. No refactor commits were needed.

## Known Stubs

None.

## Self-Check: PASSED

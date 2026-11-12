---
phase: 13-explore-charts-win-totals-display
reviewed: 2026-11-11T23:59:59Z
depth: standard
iteration: 2
files_reviewed: 34
files_reviewed_list:
  - pipeline/src/fgs/export.py
  - pipeline/tests/test_export.py
  - web/src/App.svelte
  - web/src/components/BoardRow.svelte
  - web/src/components/CalloutCard.svelte
  - web/src/components/CalloutCards.svelte
  - web/src/components/ChartFrame.svelte
  - web/src/components/Delta.svelte
  - web/src/components/EpaScatter.svelte
  - web/src/components/ExplorePage.svelte
  - web/src/components/ExploreTable.svelte
  - web/src/components/HistoryChart.svelte
  - web/src/components/MoodBoard.svelte
  - web/src/components/RecordScatter.svelte
  - web/src/components/RecordsPage.svelte
  - web/src/components/SiteHeader.svelte
  - web/src/components/TeamPage.svelte
  - web/src/components/WinTotals.svelte
  - web/src/lib/data.ts
  - web/src/lib/explore.ts
  - web/src/lib/format.ts
  - web/src/lib/router.ts
  - web/src/lib/scatterMarks.ts
  - web/src/lib/types.ts
  - web/src/lib/winTotals.ts
  - web/src/lib/explore.test.ts
  - web/src/lib/winTotals.test.ts
  - web/src/lib/winTotalsRender.test.ts
  - web/src/lib/noLuck.test.ts
  - web/src/lib/router.test.ts
  - web/src/lib/format.test.ts
  - web/src/lib/chartFrame.test.ts
  - web/src/lib/sep.test.ts
  - .planning/phases/13-explore-charts-win-totals-display/verify_ui.py
findings:
  critical: 0
  warning: 0
  info: 5
  total: 5
status: clean
---

# Phase 13: Code Review Report (re-review, iteration 2)

**Reviewed:** 2026-11-11
**Depth:** standard
**Files Reviewed:** 34
**Status:** clean (no Critical or Warning findings remain)

## Narrative Findings (AI reviewer)

## Summary

This re-review covers the six `fix(13)` commits (`f470082..2c4898b`) on top of the iteration-1 review, plus the full scope listed above. All three in-scope warnings are fixed. WR-02 was accepted as designed and is not raised again. The fix commits introduced no new Critical or Warning issues. `vitest run` passes on Node 22 (23 files, 277 tests).

Status of the prior findings:

| ID | Status | Evidence |
|----|--------|----------|
| WR-01 | Resolved | `explore.ts:204` now reads "Check back after the play-by-play update." The test is updated, and nothing else in `web/src` or `verify_ui.py` still contains the old copy. |
| WR-02 | Accepted as designed | See the orchestrator note in iteration 1. |
| WR-03 | Resolved | `winTotals.ts:87-91` branches on `season < 2003`. The new 2027 test covers the 2003+ branch. `verify_ui.py:169` (BUF 2000) still matches the pre-2003 copy. |
| WR-04 | Resolved (visual) | `formatRankDelta` returns `–` for null, undefined, or NaN, and "no change" only for a real 0. `Delta.svelte` has no remaining reference to `r.aria`. `verify_ui.py:142` still passes because it accepts "spot" or "no change". See IN-08 for the screen-reader side. |
| IN-01 | Resolved | `aria-label` and the `aria` field are removed. `formatRankDelta` has no other callers. |
| IN-04 | Resolved | The finished dek reads "N wins" (singular for exactly "1"). The pace dek reads "X.X wins". |
| IN-06 | Resolved | `noLuck.test.ts` scans 6 sources, including `scatterMarks.ts`. |
| IN-02, IN-03, IN-05, IN-07 | Open (Info) | Not in the fix scope. Carried over below. |

## Info

### IN-02 (carried over): `leagueMeans` weights by total plays, not by plays with non-null EPA

**File:** `web/src/lib/explore.ts:61-62`
**Issue:** The crosshair weights each team by `off_plays`/`def_plays`, but `seasonToDate` averages over plays that have non-null EPA. This is latent: the current data has no such rows.
**Fix:** Expose `oep`/`dep` from `seasonToDate` and weight by them.

### IN-03 (carried over): Number-line markers overflow the track at 0 and reg_games

**File:** `web/src/components/WinTotals.svelte:108-113`
**Issue:** A 0% or 100% `left` with `translate(-50%)` pushes half of the dot past the track.
**Fix:** Clamp with `left: clamp(6px, X%, calc(100% - 6px))`, or inset the marker container.

### IN-05 (carried over): Team-file failure is never retried for the rest of the session

**File:** `web/src/components/TeamPage.svelte:116-133`
**Issue:** `teamFile = {failed: true}` persists until the user changes team, so the expectations section stays hidden without a retry action.
**Fix:** Add a `teamRetry` counter, or show a StatusPanel with a "Try again" button.

### IN-07 (carried over): Duplicated week validation and a dead fallback in ExplorePage

**File:** `web/src/components/ExplorePage.svelte:40-50`
**Issue:** `validWeek` duplicates `App.svelte` `validTeamWeek`. The `seasonMeta ? … : …` guard is dead under the `findSeason(...)!` assertion.
**Fix:** Move a shared `validWeek` into `lib/data.ts`, then drop either the `!` or the guard.

### IN-08 (new): Screen-reader text still reports a missing delta as "No change"

**File:** `web/src/lib/format.ts:58-63`
**Issue:** After WR-04, the visible rank delta renders `–` for a missing delta. The row's only accessible text is `changeText` in `srText` (BoardRow.svelte:58), and it still announces "No change, preseason." or "No change from last week." when `score_delta` is null. If `score_delta` is present but `rank_delta` is null, `rd` falls back to 0 and the text reads "same spot". So sighted users see "unknown" while screen-reader users hear "unchanged". This behavior is documented (07-04) and predates this phase, so it stays Info.
**Fix:** For null deltas, return wording like "No prior week to compare." (or "No previous season to compare." at week 0). Use the same wording when `rank_delta` alone is null instead of coercing it to 0.

---

_Reviewed: 2026-11-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---
phase: 13-explore-charts-win-totals-display
fixed_at: 2026-11-11T23:59:00Z
review_path: .planning/phases/13-explore-charts-win-totals-display/13-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 3
skipped: 1
status: partial
---

# Phase 13: Code Review Fix Report

**Fixed at:** 2026-11-11T23:59:00Z
**Source review:** .planning/phases/13-explore-charts-win-totals-display/13-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (critical_warning)
- Fixed: 3
- Skipped: 1 (WR-02, accepted as designed)
- Extra Info items fixed at the orchestrator's request: 3 (IN-01, IN-04, IN-06)

Verification: in `web/`, under Node 24, `npm test` passes (23 files, 277 tests; the baseline was 275) and `npm run check` reports 0 errors and 0 warnings.

## Fixed Issues

### WR-01: "No week" empty state tells the user to pick an *earlier* week

**Files modified:** `web/src/lib/explore.ts`, `web/src/lib/explore.test.ts`
**Commit:** f470082
**Applied fix:** The `no-week` copy now reads "No efficiency data through {week} yet. Check back after the play-by-play update." The test expectation was updated to match.

### WR-03: Win-totals note hardcodes "before 2003" for any season without a Vegas line

**Files modified:** `web/src/lib/winTotals.ts`, `web/src/lib/winTotals.test.ts`
**Commit:** 2e37b89
**Applied fix:** The note now depends on the season. Before 2003 it keeps the "before 2003" note. From 2003 on it says "No Vegas line on file for this season yet." A new test covers a 2027 file that has only an `expectation` entry.

### WR-04: Missing rank delta renders as visible "no change"

**Files modified:** `web/src/lib/format.ts`, `web/src/lib/format.test.ts`
**Commit:** 08722e9
**Applied fix:** `formatRankDelta(null/undefined/NaN)` now returns `–`, matching the score delta. "no change" is used only for a real 0. The tests were split into a real-zero case and a missing case.

### IN-01: `aria-label` on rank `Delta` is dead

**Files modified:** `web/src/components/Delta.svelte`, `web/src/lib/format.ts`, `web/src/lib/format.test.ts`
**Commit:** 8988e2c
**Applied fix:** Removed the `aria-label` from the rank span and the `aria` field from `formatRankDelta`, and updated the tests. Screen readers already get this information from BoardRow's `changeText`.

### IN-04: Finished dek drops the unit

**Files modified:** `web/src/lib/winTotals.ts`, `web/src/lib/winTotals.test.ts`
**Commit:** d2156fe
**Applied fix:** The dek now reads "They finished with 13.5 wins." (singular "win" for exactly 1) and "They're on pace for 12.8 wins." The test expectations were updated.

### IN-06: `noLuck.test.ts` skips `scatterMarks.ts`

**Files modified:** `web/src/lib/noLuck.test.ts`
**Commit:** 2c4898b
**Applied fix:** Added `./scatterMarks.ts` to the scanned sources and raised the expected count from 5 to 6.

## Skipped Issues

### WR-02: Malformed explore week (3+ digits) redirects to the board with a board-specific notice

**File:** `web/src/lib/router.ts`, `web/src/App.svelte:127`
**Reason:** Accepted as designed, per the orchestrator note. RESEARCH "Open Question Resolutions" #2 sends malformed explore hashes down the invalid-route path (the board plus a notice).
**Original issue:** `#/explore/2025/123` and `#/explore/abc` parse as invalid and show BOARD_NOTICE instead of falling back silently to `#/explore`.

Info items IN-02, IN-03, IN-05, and IN-07 are out of scope (critical_warning) and were not requested, so they were not attempted.

---

_Fixed: 2026-11-11T23:59:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

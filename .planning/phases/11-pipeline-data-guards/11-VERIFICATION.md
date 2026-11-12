---
phase: 11-pipeline-data-guards
verified: 2026-11-11T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 11: Pipeline Data Guards Verification Report

**Phase Goal:** The pipeline exports everything v2's new views need (verified forfeits, display-only win totals, EPA, local logos) while frozen v1 scores are provably unchanged.
**Status:** passed
**Re-verification:** No (initial)

## Observable Truths

| # | Truth (ROADMAP SC) | Status | Evidence |
|---|---|---|---|
| 1 | Golden test pins hash of exported scores + labels (<=2025), committed first, passes at end | VERIFIED | First execution commit after 5c4951b is c0b01ff; it touches only `pipeline/tests/golden/v1_scores_le2025.json` and `pipeline/tests/test_golden_scores.py`. Golden tests pass after the site-data regeneration (1b0f6b5). The fgs evidence rerun is commit 54485a7. |
| 2 | Forfeit entries cited, each confirmed/corrected/removed, supplemental labeled separately | VERIFIED | Commit 22b36af. `draft.py` has 85 https citations and a `FORFEIT_KIND` dict (line 196). `sources/forfeit_audit.json` exists. `test_draft.py` passes. The 5 sourced-but-unplaceable forfeits are documented, not applied, as the task note says. |
| 3 | 2021-2026 win totals in sourced inputs, validated, display-only; vegas_expectations never reads past 2020 | VERIFIED | `win_totals_2021plus.csv` (160 rows, 2021-2025) has exactly one commit, a3135cb. `win_totals_display_2026plus.csv` (32 rows, 2026) is separate. `wintotals` is referenced only in `cli.py` among the pipeline source files. `cli._cached_vegas` drops seasons after 2020 (WR-02 fix; the plan said refuse, the fix changed this to drop. Behavior still guarantees no leak into the score, and the golden test passes). `test_wintotals.py` passes. |
| 4 | Export carries per-team-season(-game) EPA, success rate and play counts; web computes play-weighted season-to-date | VERIFIED | `web/public/data/epa/` holds 28 files (1999-2026). The web test suite passes (167 tests, including the season-to-date helper). |
| 5 | Logo command puts 32 logos in `web/public/logos/` (committed); no runtime hotlinking | VERIFIED | `web/public/logos/` has 33 files (32 PNGs plus the manifest). `dist/logos` has 33 files after the build. grep for `espncdn` and `wikipedia` in `web/src` and `web/index.html` finds nothing. `test_logos.py` passes. |

**Score:** 5/5

## Behavioral Spot-Checks

| Check | Result | Status |
|---|---|---|
| `uv run pytest tests/test_golden_scores.py tests/test_wintotals.py tests/test_logos.py tests/test_draft.py` | 99 passed | PASS |
| Full pipeline `uv run pytest` | 639 passed | PASS |
| Web `npm test` (Node 24) | 167 passed, 13 files | PASS |
| Web `npm run build` | built OK | PASS |

## Requirements Coverage

| Requirement | Plan | Status | Evidence |
|---|---|---|---|
| INTEG-01 | 11-01, 11-05 | SATISFIED | Golden test passes, and the export is unchanged after regeneration. |
| DATA-01 | 11-01, 11-05 | SATISFIED | Truth 2. |
| DATA-02 | 11-02, 11-05 | SATISFIED | Truth 3. |
| EXPL-01 | 11-03, 11-05 | SATISFIED | Truth 4. |
| LOGO-01 | 11-04, 11-05 | SATISFIED | Truth 5. |

All 5 IDs are marked complete in REQUIREMENTS.md. No orphaned requirements.

## Anti-Patterns

No TBD, FIXME or XXX markers in `pipeline/src` or `web/src`. The code review (11-REVIEW.md) is clean after 3 fix iterations. `git status` was clean at the start of verification.

## Notes (non-blocking)

- The 2026 lines are a single DraftKings opener labeled `preseason_open`, per the accepted constraint.
- The `_cached_vegas` guard drops rather than raises on seasons after 2020. This differs from the plan wording but is a safer equivalent, and the golden test pins the result.

## Human Verification Required

None.

_Verifier: Claude (gsd-verifier)_

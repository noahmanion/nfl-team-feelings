---
phase: 07-draft-aware-offseason
verified: 2026-11-11T00:00:00Z
status: passed
score: 3/3 must-haves verified
overrides_applied: 0
---

# Phase 7: Draft-Aware Offseason Verification Report

**Phase Goal:** Between seasons the score keeps moving and reacts to how well each team drafted, without ever rewarding tanking
**Status:** passed (SC2 judged against the context's explicit no-signal fallback)
**Re-verification:** No, initial verification

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Draft picks + value chart loaded for every season since 1999 (SC1, DATA-06) | VERIFIED | `draft.py` has `load_draft_picks`, `load_draft_values`, `normalize_picks` (filter season >= 1999), PFR->franchise map. `fgs check` includes `draft_coverage` and `draft_sum`, both ok. Surplus is derivable only for 2000+, because 1999 needs 1998 standings. This was an accepted research revision, and the picks and chart are still loaded for 1999. |
| 2 | Week-0 snapshot moves by draft value above original slot, capped; worst team doesn't move up for holding #1 (SC2, MODEL-16) | VERIFIED (fallback path) | Surplus is computed against the original slot, winsorized at [-17.29, 16.19], then z-scored. `fgs draft --season 2020` shows CIN (slot 1, untraded) at surplus 0.0, while MIA, which traded up, is at +39.8. Test `test_acceptance_slot1_untraded_zero` covers every season. The draft term failed its pre-specified gate (fitted -0.28, 8/19 folds, wk0 Δ +0.0002), so weight is 0.00 with `display_only: true`. This is the CONTEXT fallback. The week-0 snapshot still moves via regression to the mean. |
| 3 | Chart and board show offseason movement; draft weight reported; display-only text if no signal (SC3) | VERIFIED | Orchestrator browser check: #/history/DET shows dotted offseason connectors; #/team/MIA/2026/0 shows "Preseason (after draft)", "▲ 2 vs end of last season", and the "Draft haul: +24 over their original slots..." text. The weight and fold-sign result is reported in `pipeline/BACKTEST_LOG.md` line 25 and in the `weights.yaml` `offseason:` block, and `methodology.json` carries draft data. |

**Score:** 3/3

## Frozen weights
There is no git repository in the working directory, so a diff against commit 41e1e54 is not possible. Indirect evidence: the `weights:` and `fit:` blocks in `pipeline/weights.yaml` still match the Phase 6 freeze header (all 11 factors, raw values and fold signs), `frozen: true`, n=12331, and only the `offseason:` block is appended. A byte-for-byte check against that commit was not done.

## Spot-checks
| Check | Result |
|-------|--------|
| `uv run pytest -q` (pipeline) | 483 passed |
| `uv run fgs check` | all checks passed (incl. draft_coverage, draft_sum) |
| `uv run fgs draft --season 2020` | Table renders; CIN slot 1 surplus 0.0 |
| web `npm run test` | 90 passed |
| web `npm run check` | 0 errors, 0 warnings |
| web `npm run build` | built successfully |

## Requirements
| Req | Status |
|-----|--------|
| DATA-06 | SATISFIED |
| MODEL-16 | SATISFIED (display-only fallback; anti-tanking holds via surplus 0 for untraded #1) |

## Anti-patterns
No TBD/FIXME/XXX markers in `draft.py`, `export.py`, or `web/src`.

## Human verification
None outstanding (browser check already done by the orchestrator).

## Notes
- The draft term has no score effect (weight 0). This is the evidence-driven, pre-registered outcome and is not a gap.
- The git-diff check against 41e1e54 is not directly confirmed, as noted above.

_Verifier: Claude (gsd-verifier)_

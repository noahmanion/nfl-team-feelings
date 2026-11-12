---
phase: 05-efficiency-qb-trend-season-simulator
verified: 2026-11-11T21:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 5: Efficiency, QB Trend and Season Simulator Verification Report

**Phase Goal:** The score captures real trajectory (efficiency and QB play) and expectations (preseason expected wins, playoff odds), so "better than your record says" is grounded in evidence.
**Status:** passed. Re-verification: No.

## Test runs (run by verifier)

- `uv run fgs check`: all 14 checks ok, including `pbp_coverage` and `sim_sums`.
- `uv run pytest -q`: 298 passed.
- Web: vitest 66 passed; svelte-check 0 errors, 0 warnings; build OK.

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Per-team-game EPA/QB aggregates 1999 to now, 1999-2000 flagged | VERIFIED | `pbp.py` sets `LOW_CONFIDENCE_LAST = 2000` and emits a `low_confidence` column. `team_game_epa.parquet` exists. `pbp_coverage` check passes. README documents the flag. |
| 2 | epa_traj and qb_trend in the team breakdown with recorded backtest delta | VERIFIED | `latest.json` rows carry `contribs` and `points` for both factors. BACKTEST_LOG.md rows exist for epa_traj (Δ -0.0000), qb_trend (+0.0028), vs_exp (+0.0019) and po_trend (-0.0003), each with Brier delta, sign and last fold. |
| 3 | Monte Carlo sim with era rules gives weekly playoff odds and preseason expected wins, cached by model version; model-vs-Vegas r about 0.7-0.8 | VERIFIED | `sim.py` has `model_version()`. The cache is `pipeline/data/derived/sim/c9b135d58694.parquet`. The `sim_sums` check passes. I ran `test_real_vegas_corr` and it gave r = 0.863 (per-season 0.72-0.93), above the target, which counts as passing per the brief. The test asserts r >= 0.7. |
| 4 | vs_exp tags its expectation source; po_trend in the score with fitted weight reported | VERIFIED | The exported snapshots hold 19,422 rows: 12,672 `vegas` (2003-2020) and 6,750 `model`, with no null `playoff_prob`. `weights.yaml` has po_trend = -0.01, with its derivation documented. |

**Score:** 4/4

## Required Artifacts

`weights.yaml` has exactly 11 keys: elo, season_record, last16, mov, sow, streak, luck, epa_traj, qb_trend, vs_exp and po_trend. All of these exist, are substantive, are wired through export to the web, and carry real data (the 2026 week 9 rows are populated). Orchestrator browser verification of #/team/TEN confirmed the playoff odds and QB line and the factor bars render.

## Requirements Coverage

DATA-05, MODEL-05, MODEL-08, MODEL-11, MODEL-12 and MODEL-13 are SATISFIED. REQUIREMENTS.md marks all six Complete. No orphaned requirements.

## Anti-Patterns

No unreferenced TBD/FIXME/XXX markers were found in the files checked.

- **Info:** The `weights.yaml` header comment says epa_traj is -0.23 "with qb_trend in", while the weights block has -0.33. This is a documentation inconsistency, not a functional gap. Worth a tidy-up.
- **Info:** The separator-spacing cosmetic issue is being handled by code review, per the orchestrator.

## Human Verification Required

None outstanding. The browser check was already done by the orchestrator.

## Gaps Summary

No gaps. The Vegas-dependence of vs_exp is flagged for the Phase 6 holdout, which is the planned place to handle it.

_Verified: 2026-11-11_
_Verifier: Claude (gsd-verifier)_

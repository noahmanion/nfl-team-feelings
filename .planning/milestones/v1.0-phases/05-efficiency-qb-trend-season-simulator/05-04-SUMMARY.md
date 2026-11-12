---
phase: 05-efficiency-qb-trend-season-simulator
plan: 04
subsystem: pipeline
tags: [simulator, playoff-odds, expectations, vegas, vs_exp, ridge, backtest, refresh, leakage]
requires:
  - phase: 05-02
    provides: fgs.sim (simulate_all, model_version, input_digest), fgs.expectation
  - phase: 05-03
    provides: epa_traj + qb_trend factors, pbp inputs through derive, RIDGE_SETS up to ridge:+qb_trend
provides:
  - derived["sim"] (weekly playoff_prob/exp_wins with input_digest) and derived["vegas"] in every derive
  - sim cache at pipeline/data/derived/sim/{model_version}.parquet (gitignored); refresh writes it after checks pass
  - sim_sums check
  - features columns playoff_prob, exp_wins, vs_exp (FEATURE_COLUMNS) + exp_total, expectation_source (display)
  - vs_exp factor (MODEL-08) in the score, 10 weights at alpha 0.01·n
affects: [05-05, phase-06]
tech-stack:
  added: []
  patterns:
    - "read-only cache mode (write_cache=False) + deferred save_sim_cache so refresh stays check-then-write"
    - "cli.SIM_CACHE_DIR override; the test session points it at one tmp sim cache"
key-files:
  created: []
  modified:
    - pipeline/src/fgs/sim.py
    - pipeline/src/fgs/cli.py
    - pipeline/src/fgs/checks.py
    - pipeline/src/fgs/features.py
    - pipeline/src/fgs/backtest.py
    - pipeline/src/fgs/score.py
    - pipeline/src/fgs/explain.py
    - pipeline/weights.yaml
    - pipeline/BACKTEST_LOG.md
    - pipeline/tests/conftest.py
    - pipeline/tests/test_cli.py
    - pipeline/tests/test_checks.py
    - pipeline/tests/test_features.py
    - pipeline/tests/test_backtest.py
    - pipeline/tests/test_explain.py
    - pipeline/tests/test_leakage.py
    - pipeline/tests/test_sim.py
    - pipeline/tests/test_efficiency.py
    - pipeline/tests/test_export.py
    - pipeline/tests/test_snapshots.py
    - web/public/data/**
key-decisions:
  - "vs_exp kept at weight -1.24 (alpha 0.01*n); mixed dSpearman +0.0019, model-only -0.0006, deployment condition -0.0012; flagged for Phase 6 (Vegas-dependent signal)"
  - "Sims always run in derive (also scored=False); the sim cache is content-addressed per season by input_digest and saved by refresh only after checks pass"
  - "FEATURE_COLUMNS order ends epa_traj, qb_trend, playoff_prob, exp_wins, vs_exp (matches the 05-05 plan contract)"
requirements-completed: [MODEL-13, MODEL-08]
duration: ~35min
completed: 2026-11-11
---

# Phase 5 Plan 04: Simulator in the pipeline + vs_exp factor Summary

**Every derive now runs the season simulator from a per-season digest cache (playoff odds and expected wins for every snapshot, sums checked, refresh in 2.3 s). vs_exp (win % minus the Vegas or model preseason pace) joins the score at −1.24, with mixed, model-only and deployment-condition deltas logged.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-11-11
- **Tasks:** 2 (5 task commits)
- **Files modified:** 20 source/test/config files + regenerated web/public/data

## Accomplishments
- `derive_games` runs `sim.simulate_all` right after `build_grid`, even when `scored=False`. The result goes in `derived["sim"]` and Vegas in `derived["vegas"]`. `build`/`check`/`export`/`backtest` use `data/derived/sim/c9b135d58694.parquet`.
- `fgs refresh` reads the sim cache without writing it. It re-simulates only seasons whose digest changed (a test asserts this happens once per current-season snapshot week). It saves the cache next to `_write_derived` after the checks and export pass, and prints `refreshed in 2.3s`.
- New `sim_sums` check: Σplayoff_prob == playoff spots (1e-6) and Σexp_wins == REG games (1e-3) per (season, week). It skips non-standard leagues. It passes on real data and fails on a tampered row.
- Leakage: playoff_prob, exp_wins and vs_exp are in FEATURE_COLUMNS, so they fall under FLOAT_EXACT, and all three fake-future tests pass. sim.py and expectation.py are added to the firewall list.
- vs_exp (MODEL-08) has hand-computed tests: 0.125 for the Vegas 2003 and model 2022 cases, 0 at week 0, all rows model-sourced when vegas=None. Every features row carries expectation_source: vegas has 12,672 rows (2003–2020) and model has 6,750.
- Backtest reproduced the research exactly: ridge:+vs_exp N8 Spearman 0.526532 vs 0.524639 (+0.0019), R² +0.0021, ΔBrier −0.00027, alpha 0.01·n. The proposal also matches research to 2 dp (elo 2.59, season_record 1.83, … vs_exp −1.24). corr(season_record, vs_exp) = 0.920.

## Task Commits

1. **Task 1: wire sims into derive/cache/refresh/checks/backtest/leakage** - `9cfd796` (feat)
2. **Task 2: vs_exp**
   - RED tests - `af2e3a9` (test)
   - feature, FACTORS, PHRASES, ridge set - `f0693ee` (feat)
   - weights + BACKTEST_LOG - `3198d91` (feat)
   - regenerated site data - `3df3913` (chore)

## Variant numbers (all re-run, scratchpad script p504/variants.py, not committed)

| variant | N8 Spearman | Δ vs ridge:+qb_trend (0.524639) | research |
|---|---|---|---|
| mixed (standard) | 0.526532 | +0.0019 | +0.0019 |
| model-only (vegas=None everywhere) | 0.523999 | −0.0006 | −0.0006 |
| deployment (train mixed, test model-sourced) | 0.523472 | −0.0012 | −0.0011 |

My walk-forward reimplementation reproduced the mixed number exactly (0.526532) before it was used for the deployment condition. Everything is within the ±0.002 tolerance, so the fallback rule did not apply.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Synthetic efficiency tests used division-less team codes**
- **Found during:** Task 1 (full pytest)
- **Issue:** `test_epa_traj_zero_without_pbp` and `test_qb_without_pbp` call `derive_games` on teams A/B/C. The simulator needs teams that have a division, so it raises KeyError.
- **Fix:** A `_real_codes` helper maps A/B/C → BUF/MIA/NE for those two derive calls only.
- **Files modified:** pipeline/tests/test_efficiency.py
- **Commit:** 9cfd796

**2. [Rule 3 - Blocking] Tests that run `fgs check/export/backtest/build` would have used the real sim cache**
- **Fix:** Added a `cli.SIM_CACHE_DIR` override (None → `DERIVED_DIR/"sim"`). The session-scoped autouse `sim_cache_dir` fixture points it at a tmp dir. `refresh_dirs` resets it to None so the refresh tests write `sim/*.parquet` under their tmp derived dir.
- **Commit:** 9cfd796

**3. [Rule 1 - Consistency] FEATURE_COLUMNS order**
- Ordered `..., qb_trend, playoff_prob, exp_wins, vs_exp` to match the contract the 05-05 plan reads.

Other notes:
- `_cmd_refresh` reads Vegas from `CACHE_DIR/win_totals.csv` through a no-download helper (`_cached_vegas`). In the tmp-dir refresh tests this gives None, so all rows are model-sourced, as the orchestrator allowed.
- The real `fgs refresh` run only changed meta.json's `generated_at`. I restored that file, so the committed data is the `fgs export` output.

## Verification
- `uv run fgs check`: `ok    sim_sums`, "all checks passed"
- `uv run pytest -q`: 292 passed (~65 s)
- `ls data/derived/sim/*.parquet` → `c9b135d58694.parquet` (one file)
- BACKTEST_LOG row order: epa_traj, qb_trend, vs_exp
- `uv run fgs refresh`: refreshed in 2.3s

## Known Stubs
None. With `sim=None` (synthetic or unit paths only), exp_total and expectation_source are null and vs_exp is 0. Real derives always pass a sim.

## Next Phase Readiness
- 05-05 can read playoff_prob, exp_wins, exp_total, expectation_source and qb_name from features.
- Phase 6 flag: vs_exp's weight is learned mostly on Vegas rows, and 2021+ is always model-sourced. The deployment condition costs −0.0012.

## Self-Check: PASSED
- Commits 9cfd796, af2e3a9, f0693ee, 3198d91, 3df3913 are present in git log
- pipeline/data/derived/sim/c9b135d58694.parquet exists; BACKTEST_LOG has exactly 1 vs_exp row

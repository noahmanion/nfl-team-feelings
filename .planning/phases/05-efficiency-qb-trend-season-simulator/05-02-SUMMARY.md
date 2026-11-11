---
phase: 05-efficiency-qb-trend-season-simulator
plan: 02
subsystem: pipeline/model
tags: [simulator, monte-carlo, playoff-odds, expectations, vegas]
requires: [fgs.season_config, fgs.elo.EloParams, fgs.franchises.RAW_TO_FRANCHISE, fgs.cli.derive (tests only)]
provides: [fgs.sim.simulate_season, fgs.sim.simulate_all, fgs.sim.model_version, fgs.sim.input_digest, fgs.expectation.load_win_totals, fgs.expectation.vegas_expectations, fgs.expectation.expectations]
affects: [05-04 vs_exp, 05-05 po_trend, team page playoff-odds stat]
tech-stack:
  added: []
  patterns: [vectorized NumPy Monte Carlo, per-snapshot RNG stream, content-addressed parquet cache keyed by model_version + per-season input_digest]
key-files:
  created:
    - pipeline/src/fgs/sim.py
    - pipeline/src/fgs/expectation.py
    - pipeline/tests/test_sim.py
    - pipeline/tests/test_expectation.py
  modified: []
decisions:
  - "Ported the prototype's WC_RULE v1 path only (no conference-record tiebreak), and kept the prototype's RNG draw order (u, noise, rnd), so the real-data numbers match the research exactly"
  - "EloParams.seeds (tuple keys) are serialized as a sorted [team, season, value] list inside model_version's canonical JSON"
  - "simulate_all rewrites the cache with exactly the seasons in the current input (stale seasons are dropped)"
metrics:
  duration: ~15 min
  completed: 2026-11-11
  tasks: 2
  files: 4
---

# Phase 5 Plan 02: Season simulator and preseason expectations Summary

This plan adds a vectorized NumPy Monte Carlo season simulator: era rules, the simplified win%/h2h/division% tiebreak chain, per-sim N(0,100) team offsets, and a cache keyed by model_version plus a per-season digest. It also adds the expectations module: nflverse win totals 2003–2020, mapped and normalized per season, with each team-season's preseason expectation tagged `vegas` or `model`.

## What was built

- **`fgs/sim.py`**
  - `simulate_season(season_games, elo, week, n_sims=2000, seed=20261111, sigma=100.0)` returns `(teams, playoff_prob, exp_wins)`.
  - Era rules (divisions, playoff_teams, hfa_for) are looked up from `season_config` at call time. Slots per conference come from the full config.
  - Divisions with no present teams are skipped. Each pick is guarded with `has = m.any(1)`, and wildcard picks stop once a conference has no candidates left.
  - Input is sorted internally, so row order doesn't matter. Each snapshot gets its own RNG stream: `default_rng([seed, season, week])`.
  - `simulate_all(games, snapshots, *, cache_dir=None)` caches results in `{cache_dir}/{model_version}.parquet` and recomputes only the seasons whose `input_digest` changed. The cache is written atomically.
- **`fgs/expectation.py`**
  - `load_win_totals` downloads the frozen nflverse CSV once and caches it. It re-fetches only when `refresh=True`.
  - `vegas_expectations` maps legacy codes (OAK→LV, SD→LAC, STL→LA) and normalizes each season's lines to a mean of `reg_games/2`.
  - `expectations(sim, vegas=None)` returns `exp_total` and `expectation_source` per (season, franchise) at week 0.
  - The docstring flags Pitfall 1: from 2021 on, every expectation is model-sourced.

## Real-data validation (1999–2026, 2,000 sims, sigma 100)

| Metric | Result | Research / target |
|---|---|---|
| Full-history runtime (`simulate_all`, 609 snapshots) | 9.1 s | < ~15 s |
| max \|Σp − spots\| per snapshot | < 1e-6 (asserted) | ~1e-14 |
| max \|Σexp_wins − REG games\| | < 1e-3 (asserted) | ~4e-6 |
| End-of-REG field accuracy, 1999–2021, mean(1 − \|p − made\|) over 733 team-seasons | **0.9754** | ≈0.98 / ≥ 0.97 |
| r(model wk-0 exp_wins, Vegas line), pooled 2003–2020 (576 rows) | **0.863** | 0.863 / ≥ 0.7 |
| per-season r range | 0.72–0.93 | 0.72–0.93 |
| SD: model wk-0 exp_wins vs Vegas line | 1.43 vs 1.64 | — |
| r with actual wins: model vs Vegas | 0.397 vs 0.471 | — |

`load_win_totals().height` is 576, and `vegas_expectations` covers seasons 2003–2020 across 32 canonical franchises.

## Deviations from Plan

- **TDD gate:** For both tasks, the tests and the implementation went into one `feat` commit, so there is no separate RED `test(...)` commit. All behaviour cases listed in the plan are covered.
- No other deviations. Thresholds stay at the CONTEXT targets (0.97, 0.7).

## Notes / Deferred

- The full suite gives 268 passed and 1 failed: `tests/test_cli.py::test_derive_carries_pbp_games`. That test comes from the concurrent plan 05-01, which has `cli.py` mid-edit. It is outside this plan's scope.
- The sim cache is not wired into `fgs build` yet. Plans 05-04 and 05-05 consume it.

## Self-Check: PASSED

- FOUND: pipeline/src/fgs/sim.py, pipeline/src/fgs/expectation.py, pipeline/tests/test_sim.py, pipeline/tests/test_expectation.py
- FOUND commits: 97aa356 (Task 1), b3e9639 (Task 2)

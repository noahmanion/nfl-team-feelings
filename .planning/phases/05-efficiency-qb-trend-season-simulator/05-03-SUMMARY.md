---
phase: 05-efficiency-qb-trend-season-simulator
plan: 03
subsystem: pipeline/model
tags: [pbp, epa, qb, factors, backtest, weights]
requires: [05-01 team_game_epa, cached_inputs]
provides: [epa_traj factor, qb_trend factor, qb_name/qb_new display columns, 9-factor weights.yaml]
affects: [features.build_features, backtest RIDGE_SETS, explain.PHRASES, web/public/data]
tech-stack:
  added: []
  patterns: [as-of join on season*100+week, opponent prior-EWMA shift(1), per-QB dropback-weighted EWMA]
key-files:
  created:
    - pipeline/src/fgs/efficiency.py
    - pipeline/tests/test_efficiency.py
  modified:
    - pipeline/src/fgs/features.py
    - pipeline/src/fgs/score.py
    - pipeline/src/fgs/backtest.py
    - pipeline/src/fgs/explain.py
    - pipeline/src/fgs/cli.py
    - pipeline/weights.yaml
    - pipeline/BACKTEST_LOG.md
    - pipeline/tests/test_backtest.py
    - pipeline/tests/test_explain.py
    - pipeline/tests/test_leakage.py
    - pipeline/tests/test_cli.py
    - web/public/data/**
decisions:
  - "epa_traj kept as defined despite a ~0 backtest delta; its fitted weight is negative (-0.20 alone, -0.23 with qb_trend), so the description says an efficiency upswing tends to fade"
  - "qb_trend = current QB form level (A1), weight +0.63; the literal CONTEXT definition reproduced at -0.0009 (research said -0.0005) and was logged"
  - "backtest seals team_game_epa to season <= last train/test season before features (_sealed_pbp)"
metrics:
  duration: ~25m
  completed: 2026-11-11
  tasks: 2
  files: 13 (+ regenerated site JSON)
---

# Phase 5 Plan 03: Efficiency trajectory + QB trend factors Summary

Adds two pbp factors to the score, one at a time. epa_traj is opponent-adjusted net EPA/play: an EWMA with half-life 4, minus the season-to-date mean. qb_trend is the current starter's dropback-weighted EPA/dropback form, which follows him across teams and seasons. Each one was backtested, logged, weighted from 1999–2021 only, phrased, and exported, so the team page shows 9 factor bars.

## Results (all reproduced, matching research within ±0.002)

| step | Spearman N=8 | R² N=8 | ΔSpearman | ΔBrier | sign |
|---|---|---|---|---|---|
| ridge:+luck (base) | 0.52194 | 0.27133 | | | |
| ridge:+epa_traj | 0.52189 | 0.27103 | −0.0000 (−0.00005) | −0.00007 | − (−0.20) |
| ridge:+qb_trend | 0.52464 | 0.27473 | +0.0028 | −0.00081 | + (0.63) |

Both proposal weight vectors match the research table exactly at 2 dp.

Variants (scratch script, not committed):
- epa level: −0.0019, matching research.
- qb literal definition: −0.0009. Research had −0.0005. The gap is under the 0.002 tolerance, but the logged value is the actual one.

## Tasks

| Task | Commits |
|---|---|
| 1 epa_traj | 0a8cf83 feat (efficiency.py, plumbing, tests); a426250 weights + log; 51dcf0e site data |
| 2 qb_trend | 9c288e5 feat (qb form, display cols, tests); 35e8158 weights + log; b826f19 site data |

## Deviations from Plan

**1. [Rule 3 - Blocking] test_cli `test_derive_carries_pbp_games` stub frame**
- Found during: Task 1
- Issue: the test passed a 2-column team_game_epa stub. Now that scored derive consumes pbp, it raised ColumnNotFoundError.
- Fix: the stub now has the full TGE_COLUMNS set (null values). The behavior under test (carry-through by identity) is unchanged.
- Files: pipeline/tests/test_cli.py. Commit: 0a8cf83

**2. [Test design] fake-future-pbp leakage test restricted to future games**
- The first version anti-joined every played team-game that had no pbp. That also caught the 3 historical no-pbp games from 1999–2000, which legitimately changed past values. The test now only adds fake pbp for games after the latest played week. It also sets those games' results to 60-0 and gives them extreme EPA/QB values (fake QB id).

**3. [Numbers] qb literal-definition Δ logged as −0.0009, not research's −0.0005**
- Within tolerance. The reproduced value was logged, as the fallback rule requires.

Other notes:
- weights.yaml claims only reproduced numbers. The fold sign is the last fold (2021), not the research "19/19 folds".
- The "INTERIM: these 7 weights" header was generalized to "these weights".

## Verification

- Full `uv run pytest -q`: 283 passed. This includes the new test_efficiency (11 hand-computed cases), the fake-future-pbp leakage test, and a firewall that now covers efficiency.py and pbp.py.
- `load_weights()` keys: elo, season_record, last16, mov, sow, streak, luck, epa_traj, qb_trend.
- meta.json has 9 factors labelled "Getting better (efficiency trend)" and "QB play (recent starts)". In latest.json, `points` has 9 keys.
- Spot-check of a 2026 QB change: CHI qb_name goes C.Williams → C.Keenum → T.Bagent, and qb_trend follows each starter's own form.
- BACKTEST_LOG has exactly 1 epa_traj row and 1 qb_trend row, in that order.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: pipeline/src/fgs/efficiency.py, pipeline/tests/test_efficiency.py
- FOUND commits: 0a8cf83, a426250, 51dcf0e, 9c288e5, 35e8158, b826f19

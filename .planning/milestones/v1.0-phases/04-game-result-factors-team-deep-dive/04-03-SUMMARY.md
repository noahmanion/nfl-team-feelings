---
phase: 04-game-result-factors-team-deep-dive
plan: 03
subsystem: pipeline
tags: [factors, backtest, weights, mov, sow]
requires: [04-01]
provides: [mov factor, sow factor, 5-key weights.yaml, regenerated site data with 5 bars]
affects: [web/public/data/**, pipeline/weights.yaml, pipeline/BACKTEST_LOG.md]
tech-stack:
  added: []
  patterns: [per-game as-of frame + cumsum window + join_asof backward (generic _win/_cnt/_asof helpers)]
key-files:
  created: []
  modified:
    - pipeline/src/fgs/features.py
    - pipeline/src/fgs/score.py
    - pipeline/src/fgs/backtest.py
    - pipeline/weights.yaml
    - pipeline/BACKTEST_LOG.md
    - pipeline/tests/test_features.py
    - pipeline/tests/test_backtest.py
    - web/public/data/**
decisions:
  - "mov added first: dSpearman +0.0026, dR2 +0.0015, fitted sign + (1.04); weights elo 3.76 / season_record 0.42 / last16 -1.16 / mov 1.04"
  - "sow added after mov: dSpearman +0.0047, dR2 +0.0048, fitted sign - (-1.29); kept per CONTEXT, description and phrases say high sow fades"
  - "Final weights: elo 3.92, season_record 0.79, last16 -0.90, mov 1.54, sow -1.29 (1999-2021 fit, alpha 0.001*n, n=12331, holdout sealed)"
  - "_hfa_table duplicated privately in features.py (firewall: features never imports backtest)"
metrics:
  duration: ~15 min
  completed: 2026-11-11
  tasks: 2
  files: 7 source/config + regenerated JSON
---

# Phase 4 Plan 03: mov and sow game-result factors Summary

Margin of victory (last 8 games, each capped at ±24) and quality of results (result minus an average team's expected result against the same opponent's pre-game Elo at that venue, last 8 games) were added one at a time. Each step was backtested walk-forward, weights were re-proposed from 1999–2021 only and logged, and the site data was regenerated. Team pages now carry 5 factor bars.

## Reproduced numbers (match the RESEARCH prototype exactly)

| step | Spearman N=8 | R² N=8 | Δ vs previous | proposal |
|------|------|------|------|------|
| ridge:+last16 | 0.5155 | 0.2656 | base | |
| ridge:+mov | 0.5181 | 0.2672 | +0.0026 / +0.0015 | elo 3.76, season_record 0.42, last16 −1.16, mov 1.04 |
| ridge:+sow | 0.5228 | 0.2720 | +0.0047 / +0.0048 | elo 3.92, season_record 0.79, last16 −0.90, mov 1.54, sow −1.29 |

I checked the sow sign myself with a scratch script against the 1999–2021 data. Alone, sow has Spearman 0.4286 and a fitted weight of +3.32. With elo it fits to −0.28, and with elo+mov to −1.06. Both the univariate and the elo+sow claims from RESEARCH Pitfall 1 reproduce, and the log row cites these numbers. I did not reproduce the per-fold sign counts (19/19), so the log cites the last-fold (2021) weight instead: mov +1.04, sow −1.22.

## Tasks

| Task | Commits |
|------|---------|
| 1. mov (MODEL-06) | 04e2aba feat, 13feaea weights+log, 2b77561 data |
| 2. sow (MODEL-07) | aaada37 feat, 9e29e52 weights+log, c703965 data |

## Deviations from Plan

- The no-null check in `test_build_features_shape_and_no_nulls` was widened to all non-elo FEATURE_COLUMNS, so new factors are covered automatically.
- Each task committed the tests together with the feature in one commit, as the plan's commit order specifies, with no separate RED commit.
- explain.py is unchanged because the fitted sow sign is negative, which is what the plan expected.

## TDD Gate Compliance

There are no separate `test(...)` RED commits. Tests and implementation went into the same `feat` commits, following the plan's "feature+tests" commit order. Hand-computed tests cover the behaviour block: mov cap, window, season carry, bye; sow home, neutral, tie, away loss, bye.

## Verification

- `uv run pytest -q`: 213 passed (leakage, holdout-sealed, and export contract tests included)
- meta.json has 5 factors. The latest BUF row has points {elo 50, season_record 9, last16 −11, mov 14, sow −15} and its blurb uses the "(that tends to fade)" sow phrase
- `grep -c "import.*backtest" pipeline/src/fgs/features.py` returns 0
- BACKTEST_LOG.md has exactly one mov row and then one sow row, in that order

## Self-Check: PASSED

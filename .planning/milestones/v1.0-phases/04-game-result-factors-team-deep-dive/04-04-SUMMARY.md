---
phase: 04-game-result-factors-team-deep-dive
plan: 04
subsystem: pipeline
tags: [factors, backtest, weights, streak, luck, readme, phase-close]
requires: [04-02, 04-03]
provides: [streak factor, luck factor, final interim 7-key weights.yaml, regenerated site data with 7 bars, README for Phase 4]
affects: [web/public/data/**, pipeline/weights.yaml, pipeline/BACKTEST_LOG.md, README.md]
tech-stack:
  added: []
  patterns: [sequential numpy pass over the sorted per-game frame for path-dependent factors (streak), then the shared _asof join]
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
    - README.md
    - .planning/REQUIREMENTS.md
decisions:
  - "streak added after sow: dSpearman +0.0000 (0.522780 -> 0.522782), dR2 -0.0001, fitted sign - (-0.15); kept per CONTEXT, and the description says a hot streak slightly fades"
  - "luck added last: dSpearman -0.0008 (0.5228 -> 0.5219), dR2 -0.0006, fitted sign - (-0.30); +0.0029 alone vs the elo+season_record+last16 base; sign - in all 19 folds; kept per CONTEXT"
  - "Final interim weights: elo 3.75, season_record 0.90, last16 -0.56, mov 1.34, sow -1.07, streak -0.14, luck -0.30 (1999-2021 fit, alpha 0.001*n, n=12331, holdout sealed)"
metrics:
  duration: ~20 min
  completed: 2026-11-11
  tasks: 3
  files: 10
---

# Phase 4 Plan 04: Streak, close-game luck and Phase 4 close-out Summary

This plan added the signed current streak (capped at ±8, ties reset it) and close-game luck (one-score wins minus one-score losses over the last 16 games) one at a time. Each got its own backtest log row and fitted sign. The final interim 7-factor weights come from the 1999–2021 fit, the site data was regenerated with 7 bars, and the README now describes all 7 factors, the negative weights, the team page, and Phase 4 status.

## Backtest results (all reproduced; within ±0.002 of the RESEARCH prototype)

| step | Spearman N=8 | R² N=8 | proposal |
| ---- | ------------ | ------ | -------- |
| ridge:+sow (prev) | 0.5228 | 0.2720 | |
| ridge:+streak | 0.5228 | 0.2719 | elo 3.96, season_record 0.86, last16 −0.94, mov 1.54, sow −1.24, streak −0.15 |
| ridge:+luck | 0.5219 | 0.2713 | elo 3.75, season_record 0.90, last16 −0.56, mov 1.34, sow −1.07, streak −0.14, luck −0.30 |

The streak proposal differs from the prototype by ≤0.01 per weight (season_record 0.86 vs 0.87, mov 1.54 vs 1.55, sow −1.24 vs −1.25), which is rounding. The luck proposal matches exactly. I reproduced both log notes with a scratch script before quoting them. The alone-vs-base check is 0.518383 vs 0.515479, or +0.0029. Every 7-factor fit in the walk-forward has a negative luck weight.

## Tasks

| # | Task | Commits |
| - | ---- | ------- |
| 1 | streak (MODEL-09): feature, tests, backtest, weights, log, data | a433d5d, 1a20e90, 228134b |
| 2 | luck (MODEL-10): feature, tests, backtest, final interim weights, log, data | 8457998, 1c3fc5d, fb6adff |
| 3 | README close-out + full gate | bff000b |

## Sample for the browser check (latest = 2026 week 9)

Check `#/team/{ABBR}` at 375px and 1280px, in light and dark mode.

Top 3:
- **BUF** 96 (7-1): elo 49, season_record 10, last16 −7, mov 12, sow −13, streak −1, luck −3. "The Bills are one of the best teams in football, but have a record that runs ahead of their margins (that tends to fade)."
- **JAX** 94 (6-2): elo 37, season_record 7, last16 −7, mov 18, sow −8, streak −1, luck −1. "The Jaguars are one of the best teams in football, and have been blowing teams out."
- **SF** 90 (7-1): elo 37, season_record 11, last16 −7, mov 16, sow −12, streak 0, luck −4. "The 49ers are one of the best teams in football, and have been blowing teams out."

Bottom 3:
- **LAC** 7 (0-8): elo −32, season_record −13, last16 5, mov −18, sow 13, streak 2, luck 1. "The Chargers are one of the worst teams in football, and have been getting blown out."
- **MIA** 6 (1-7): elo −33, season_record −9, last16 2, mov −13, sow 10, streak 1, luck −1. "The Dolphins are one of the worst teams in football, and have been getting blown out."
- **TEN** 5 (1-7): elo −45, season_record −9, last16 6, mov −10, sow 11, streak 0, luck 3. "The Titans are one of the worst teams in football, but have a record that lags behind their margins (that tends to even out)."

High-record team with negative luck/sow points ("8-2 but worried"):
- **DEN** 79 (7-2): elo 45, season_record 9, last16 −7, mov 8, sow −16, streak −2, luck −7. "The Broncos are one of the best teams in football, but have a record that runs ahead of their margins (that tends to fade)."

meta.baseline = 49 (int). meta.factors = elo, season_record, last16, mov, sow, streak, luck.

## Deviations from Plan

- The streak and luck tests were committed together with each feature in one `feat` commit, following the plan's "feature+tests" commit order (same as 04-03). There are no separate RED commits.
- Task 3's re-export changed only `generated_at` in meta.json (I checked by comparing the JSON), so that change was discarded and no data commit was made.
- REQUIREMENTS.md traceability: MODEL-06, MODEL-07, MODEL-09, MODEL-10, SITE-02 and INSIGHT-05 are marked Complete, as the orchestrator allowed.
- explain.py is unchanged. The streak and luck phrases from 04-01 already handle negative signs through the FADE suffix.

## TDD Gate Compliance

There are no separate `test(...)` RED commits. Tests and implementation went into the same `feat` commits, as the plan's commit order specifies. The behavior cases covered are: all streak anchors from the synthetic league, the cap at 8 with a loss going to −1 and a tie going to 0, week 0 being 0; the luck anchors (BUF +3, MIA −3, NE 0/−1/0); the 8-point boundary (counts) vs 9 points (does not); and the 16-game window.

## Verification

- `uv run pytest -q`: 217 passed (holdout, leakage and export contract tests included)
- `npm test`: 60 passed. `npm run check`: 0 errors, 0 warnings. `npm run build`: succeeded.
- BACKTEST_LOG has 4 Phase 4 rows in order: mov, sow, streak, luck
- `load_weights()` keys: elo, season_record, last16, mov, sow, streak, luck
- README: "Phase 4" appears 1 time, and it lists `mov`, `sow`, `streak`, `luck` with their weights

## Self-Check: PASSED

- FOUND: pipeline/BACKTEST_LOG.md (luck row), pipeline/weights.yaml (luck: -0.30), README.md (Phase 4)
- FOUND commits: a433d5d, 1a20e90, 228134b, 8457998, 1c3fc5d, fb6adff, bff000b

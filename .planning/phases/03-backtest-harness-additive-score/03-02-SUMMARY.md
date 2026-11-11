---
phase: 03-backtest-harness-additive-score
plan: 02
subsystem: pipeline/score + backtest
tags: [score, ridge, weights, backtest]
requires: [fgs.features.build_features, fgs.backtest.run_backtest, targets]
provides: [fgs.score (FACTORS, load_weights, zscore, composite, contrib_columns), fgs.backtest (ridge_fit, ridge_predict, choose_alpha, propose_weights, format_proposal, RIDGE_SETS), fgs.paths.WEIGHTS_PATH, pipeline/weights.yaml, pipeline/BACKTEST_LOG.md, `fgs backtest --propose-weights`]
affects: [03-03 score wiring into export + meta.factors, Phase 4 factor bars, Phase 6 refit]
tech-stack:
  added: [pyyaml==6.0.3]
  patterns: [per-snapshot z with std guard, closed-form ridge with unpenalized intercept, LOSO-CV alpha, walk-forward fold-consistent logistic Brier]
key-files:
  created:
    - pipeline/src/fgs/score.py
    - pipeline/tests/test_score.py
    - pipeline/weights.yaml
    - pipeline/BACKTEST_LOG.md
  modified:
    - pipeline/pyproject.toml
    - pipeline/uv.lock
    - pipeline/src/fgs/paths.py
    - pipeline/src/fgs/backtest.py
    - pipeline/src/fgs/cli.py
    - pipeline/tests/test_backtest.py
key-decisions:
  - "Interim weights: elo 4.58, season_record 0.63, last16 -1.25 (ridge on 1999-2021, N=8, alpha=0.001*n, n=12331); last16 sign kept negative"
  - "Ridge composite Brier: each fold's ridge scores both train and test next-game rows, then a logistic on (pred_h - pred_a, home_ind) is fit on seasons < S"
  - "score.py has no word 'backtest' outside comments (firewall enforced by a source-scan test)"
metrics:
  duration: ~15 min
  completed: 2026-11-11
  tasks: 2
  files: 10
---

# Phase 3 Plan 02: Additive Score Engine and Interim Weights Summary

This plan adds `fgs.score`, the additive engine: a per-(season, week) z-score with a zero-variance guard, plus contrib_f = w_f·z_f with composite = Σ contrib_f. Weights are read only from `pipeline/weights.yaml`. `fgs backtest` now runs walk-forward ridge composites. `--propose-weights` fits on 1999–2021 only. The proposed weights (elo +4.58, season_record +0.63, last16 −1.25) are committed with their provenance, and BACKTEST_LOG.md records each factor's measured delta.

## Tasks

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | score.py (FACTORS, load_weights, zscore, composite) + PyYAML pin + tests | bd1058a |
| 2 | Ridge composites, propose_weights, CLI flag, weights.yaml, BACKTEST_LOG.md, tests | fc4f65d |

## Composite results (`uv run fgs backtest`, N=8, test seasons 2003–2021)

```
candidate               Spearman        R²       wk0     early       mid      late     Brier        n
elo                        0.513     0.264     0.425     0.480     0.558     0.502    0.2197    10234
ridge:elo                  0.511     0.260     0.424     0.479     0.558     0.502    0.2197    10234
ridge:+season_record       0.512     0.261     0.425     0.479     0.559     0.499    0.2196    10234
ridge:+last16              0.515     0.266     0.425     0.484     0.562     0.503    0.2195    10234
```

All the exact values match the research prototype: 0.5114/0.2602, 0.5122/0.2615, and 0.5155/0.2656.

## Final weights (pipeline/weights.yaml)

```yaml
weights:
  elo: 4.58
  season_record: 0.63
  last16: -1.25
```

The proposal fit used alpha = 0.001·n (chosen by leave-one-season-out CV) with n = 12331 snapshot rows, 1999–2021, target y8.

## Factor log (BACKTEST_LOG.md)

- season_record: ΔSpearman +0.0008, ΔR² +0.0013, sign +
- last16: ΔSpearman +0.0033, ΔR² +0.0042, sign − (kept, with no positivity constraint)

## Verification

- `uv run pytest -q`: 161 passed (13 new in test_score.py, 5 new in test_backtest.py).
- The holdout test swaps every 2022+ result, and `propose_weights` stays identical.
- `grep -v '^\s*#' src/fgs/score.py | grep -c backtest` returns 0.
- PyYAML 6.0.3 was checked against the PyPI JSON API (source at github.com/yaml/pyyaml) before `uv add`.

## Deviations from Plan

None. The plan was executed as written. Minor additions:
- `format_proposal` is a helper in backtest.py, so the CLI only prints the block.
- The proposal dict also carries `intercept`.
- The candidate column in the report is widened to 22 characters to fit `ridge:+season_record`.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: pipeline/src/fgs/score.py, pipeline/tests/test_score.py, pipeline/weights.yaml, pipeline/BACKTEST_LOG.md
- FOUND commits: bd1058a, fc4f65d

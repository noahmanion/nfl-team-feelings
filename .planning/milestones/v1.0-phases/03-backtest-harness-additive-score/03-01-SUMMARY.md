---
phase: 03-backtest-harness-additive-score
plan: 01
subsystem: pipeline/backtest
tags: [backtest, features, walk-forward, baselines]
requires: [derive(), snapshots.build_grid, team_games]
provides: [fgs.backtest (adjusted_margins, targets, spearman, r2, logit_fit, brier, run_backtest, format_report), fgs.features.build_features, season_config split constants, fgs backtest CLI]
affects: [03-02 ridge weights, 03-03 score + import firewall, Phase 6 holdout]
tech-stack:
  added: []
  patterns: [global cumsum windows for next-N targets, join_asof backward for as-of features, NumPy IRLS logistic]
key-files:
  created:
    - pipeline/src/fgs/backtest.py
    - pipeline/src/fgs/features.py
    - pipeline/tests/test_backtest.py
    - pipeline/tests/test_features.py
  modified:
    - README.md
    - pipeline/src/fgs/season_config.py
    - pipeline/src/fgs/cli.py
key-decisions:
  - "Holdout sealed by filtering snapshots/team_games/games to season <= last test season before features, targets or fits run"
  - "Spread Brier uses x = spread_line only (no home indicator), its own n (rows with a line, 2003-2021: 5082)"
  - "Report floats rounded to 6 dp and NaN/inf mapped to None so backtest.json is strict JSON"
metrics:
  duration: ~20 min
  completed: 2026-11-11
  tasks: 3
  files: 7
---

# Phase 3 Plan 01: Backtest Harness and Baselines Summary

The target is documented in the README and committed first: the opponent- and HFA-adjusted mean margin over the next 4 or 8 games. The plan also adds leak-free as-of features (season_record, last16, pd_pg) and a `fgs backtest` command. That command prints walk-forward baselines with the 2022–2025 holdout sealed and writes `pipeline/data/derived/backtest.json`.

## Tasks

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | README target section, split constants, adjusted_margins/targets + tests | 40ea3bd |
| 2 | features.py: season_record, last16, pd_pg + tests | 517dfdb |
| 3 | Metrics, run_backtest, format_report, `fgs backtest` CLI + tests | 853f217 |

## Baseline results (`uv run fgs backtest`, test seasons 2003–2021, holdout sealed)

```
N=8  (target: mean adjusted margin over next 8 games; bucket columns are Spearman)
candidate     Spearman        R²       wk0     early       mid      late     Brier        n
elo              0.513     0.264     0.425     0.480     0.558     0.502    0.2197    10234
season_wpct      0.402     0.143         —     0.330     0.500     0.447    0.2320    10234
last16           0.449     0.199     0.371     0.403     0.491     0.456    0.2260    10234
pd_pg            0.462     0.185         —     0.403     0.555     0.475    0.2282    10234
spread               —         —         —         —         —         —    0.2112     5082
elo_538              —         —         —         —         —         —    0.2194     5082
```

N=4: elo 0.466 / R² 0.218. The others rank in the same order. The numbers match the research prototype: elo N=8 Spearman 0.513, Brier about 0.22, spread 0.211. With `--include-holdout` (2003–2025), elo N=8 Spearman is 0.507 and its Brier is 0.2203.

## Verification

- `uv run pytest -q`: 143 passed (128 existing + 15 new).
- `uv run fgs backtest` exits 0 and prints both N tables. It writes backtest.json with no 2022+ per-season keys, and `json.dumps(allow_nan=False)` succeeds on it.
- Holdout seal test: swapping every 2024 result leaves the default report identical. The same swap does change the `--include-holdout` report, so the test can detect a leak.
- `features.py` has no reference to backtest. The README target commit (40ea3bd) comes before any weights or ridge code.

## Deviations from Plan

None. The plan was executed as written. Minor implementation choices:
- `join_asof` uses `check_sortedness=False` because the inputs are explicitly sorted on the key, and this silences a Polars warning about `by` groups.
- The report includes an extra `elo_538` Brier cross-check row (the plan asked for it) next to `spread`.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: pipeline/src/fgs/backtest.py, pipeline/src/fgs/features.py, pipeline/tests/test_backtest.py, pipeline/tests/test_features.py
- FOUND commits: 40ea3bd, 517dfdb, 853f217

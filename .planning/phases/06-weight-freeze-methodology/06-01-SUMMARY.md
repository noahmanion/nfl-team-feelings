---
phase: 06-weight-freeze-methodology
plan: 01
subsystem: pipeline/backtest-methodology
tags: [preregistration, bootstrap, holdout, numpy]
requires: [phase-05 complete (po_trend in weights.yaml, ridge:+po_trend)]
provides:
  - pipeline/PREREGISTRATION.md (committed alone, first Phase 6 commit)
  - fgs.bootstrap (paired season-block + stratified cluster percentile bootstrap)
affects: [06-02 freeze walk-forward CIs, 06-03 holdout evaluator and guards]
tech-stack:
  added: []
  patterns: [paired percentile bootstrap with shared index draws, stat functions injected by caller]
key-files:
  created:
    - pipeline/PREREGISTRATION.md
    - pipeline/src/fgs/bootstrap.py
    - pipeline/tests/test_bootstrap.py
  modified: []
decisions:
  - "PREREGISTRATION.md committed alone (42e57aa) before any freeze/holdout code; contains no 2022-2025 numbers and no frozen weights"
  - "fgs.bootstrap is pure NumPy (no fgs imports); callers pass stat functions, so it carries no leakage surface"
  - "Summary dicts round to 6 dp and map NaN to None; sd is None when no finite draws"
metrics:
  duration: ~2 min
  completed: 2026-11-11
  tasks: 2
  files: 3
---

# Phase 6 Plan 01: Pre-registration and Paired Bootstrap Summary

The one-time 2022–2025 holdout protocol (11-factor ridge with LOSO alpha and no pruning, Spearman N=8 composite − Elo > 0 as the pass rule, B=2000 seed 20221 season-block plus stratified cluster CIs, fixed three-way verdict wording, vs_exp-zeroed diagnostic, guards) is committed on its own. A pure-NumPy paired bootstrap engine with synthetic tests is in place for the freeze and holdout plans.

## Tasks

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Write and commit PREREGISTRATION.md | 42e57aa | pipeline/PREREGISTRATION.md |
| 2 (RED) | Failing synthetic bootstrap tests | 1218506 | pipeline/tests/test_bootstrap.py |
| 2 (GREEN) | Paired bootstrap module | 6265e96 | pipeline/src/fgs/bootstrap.py |

## Verification

- Precondition checked: `po_trend:` in weights.yaml, `ridge:+po_trend` in `backtest.RIDGE_SETS`, 05-05-SUMMARY.md exists.
- `git log --diff-filter=A -- pipeline/PREREGISTRATION.md` shows exactly one commit (42e57aa), and that commit touches only that file. It comes before both bootstrap commits.
- PREREGISTRATION.md contains the 13 sections, the verbatim `choose_alpha` sentence, "Σ round(w)·z ... no intercept", B = 2000, seed 20221, both CI methods for Spearman and Brier, the three exact verdict sentences, the vs_exp diagnostic, the stand-in caveat, the no-refit rule and the guard list. The only numbers in it are training-data stand-in and calibration figures. Nothing was computed on 2022–2025.
- `uv run pytest tests/test_bootstrap.py -q`: 10 passed in about 1 s. `tests/test_leakage.py`: 5 passed.
- `grep -cE "^from fgs|^import fgs" src/fgs/bootstrap.py` = 0.

## TDD Gate Compliance

RED (`test(06-01)` 1218506) → GREEN (`feat(06-01)` 6265e96). No refactor was needed.

## Deviations from Plan

None. The plan was executed as written. One small addition: an extra test covers the all-None case (`ci`/`sd` None, `n_finite` 0) and `percentile_ci` on all-NaN input.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: pipeline/PREREGISTRATION.md, pipeline/src/fgs/bootstrap.py, pipeline/tests/test_bootstrap.py
- FOUND commits: 42e57aa, 1218506, 6265e96

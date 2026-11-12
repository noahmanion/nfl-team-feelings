---
phase: 07-draft-aware-offseason
plan: 03
subsystem: pipeline
tags: [draft, offseason, gate, walk-forward, model-16, weights]
requires:
  - "07-01: fgs.draft (surplus_table, winsor_bounds, draft_z, decay, DECAY_WEEKS, FIRST_DRAFT, CHART), derived['draft']"
  - "Phase 6: frozen weights.yaml, score.is_frozen / load_weights_doc, HOLDOUT_RESULT.md"
provides:
  - "backtest._draft_fit, draft_walk_forward, draft_gate, format_draft_report"
  - "`fgs backtest --draft` (refuses --include-holdout and an unfrozen weights.yaml; writes nothing)"
  - "score.load_offseason, score.apply_offseason, score.OFFSEASON_FACTORS, score.DECAY_NAME"
  - "derived['offseason'] = cfg; features gain composite_inseason, draft_surplus, draft_z (+ contrib_draft only when weight != 0)"
  - "mood.reference_values reads composite_inseason when present"
  - "weights.yaml offseason.draft block (weight 0.00, display_only true)"
  - "BACKTEST_LOG 'Offseason terms (Phase 7)' table"
affects: [07-04]
tech-stack:
  added: []
  patterns:
    - "Residual walk-forward on a fixed (frozen) composite: slope of (y8 - composite) ~ 1 + decay*z per fold"
    - "Gate sign consistency measured against the FINAL weight's sign (Pitfall 4)"
    - "Offseason terms kept outside FACTORS / weights: in a separate top-level YAML block"
key-files:
  created:
    - .planning/phases/07-draft-aware-offseason/07-03-SUMMARY.md
  modified:
    - pipeline/src/fgs/backtest.py
    - pipeline/src/fgs/cli.py
    - pipeline/src/fgs/score.py
    - pipeline/src/fgs/mood.py
    - pipeline/tests/test_backtest.py
    - pipeline/tests/test_score.py
    - pipeline/weights.yaml
    - pipeline/BACKTEST_LOG.md
decisions:
  - "Draft gate FAILED on the frozen composite: fitted -0.2828, fold-sign 8/19, wk0 ΔSpearman +0.0002 -> offseason.draft weight 0.00, display_only true (draft surplus shown, never scored)"
  - "`fgs backtest --draft` dispatches before the Phase 6 guards so `--draft --include-holdout` gets the training-only refusal; Phase 6 guards unchanged"
  - "load_offseason validates display_only as a bool too, and a non-mapping `offseason` key raises ValueError"
  - "apply_offseason computes decay as an expression (max(0, 1 - week/DECAY_WEEKS)), equivalent to draft.decay, to avoid per-row Python"
metrics:
  duration: ~30min
  completed: 2026-11-11
  tasks: 3
  files: 8
---

# Phase 7 Plan 03: Draft Term Gate + Offseason Scoring Path Summary

This plan built a walk-forward test of the draft term on top of the Phase 6 frozen composite, using training seasons only, plus a locked gate that decides its weight. On the real data the gate failed, so `offseason.draft` has weight 0 and is display-only. The scoring path is built and tested for both cases: with weight 0 the scores are unchanged, and a nonzero weight adds a contribution that fades over weeks 0–3 and does not move the percentile reference.

## Gate verdict: FAILED -> weight 0, display only

`uv run fgs backtest --draft` was run once and again on re-run gave the same output byte for byte. Full output:

```
offseason draft term on the FROZEN composite: training-only walk-forward (holdout consumed by Phase 6)
surplus 2000-2021, test seasons 2003-2021, target N=8, chart stuart, winsor [-17.29, 16.19], decay linear to 0 by week 4
  rows (weeks 0-3): 2808
  final weight (2000-2021): -0.2828
  fold weights: 2003:-0.04 2004:+0.10 2005:+0.18 2006:+0.10 2007:+0.14 2008:+0.10 2009:+0.10 2010:+0.11 2011:+0.16 2012:+0.12 2013:+0.20 2014:+0.10 2015:-0.08 2016:-0.06 2017:-0.17 2018:-0.21 2019:-0.26 2020:-0.19 2021:-0.26
  fold-sign consistency vs final: 8/19 (0.42)
  wk0 ΔSpearman (N=8): +0.0002; weeks 0-3: +0.0003; seasons with wk0 Δ>0: 6/19
  partial check wk0 (y8 ~ 1 + composite + x): coef -0.367, t -1.53
  gate failed: fitted -0.28, 8/19 folds share its sign, wk0 ΔSpearman +0.0002 -> weight 0.00, display only

BACKTEST_LOG row (Offseason terms table):
| Date | Term | wk0 ΔSpearman (N=8) | Fitted weight | Fold-sign consistency | Gate | Notes |
| 2026-11-11 | draft | +0.0002 | -0.2828 | 8/19 | fail -> 0.00 | residual on frozen composite; weeks 0-3 Δ +0.0003; wk0 seasons Δ>0 6/19; training-only walk-forward 2003-2021 (no fresh holdout) |

weights.yaml block (append at the end):
offseason:
  draft:
    weight: 0.00
    display_only: true
    chart: stuart
    winsor: [-17.29, 16.19]
    decay: linear_to0_by_wk4
    fit_seasons: 2000-2021
    test_seasons: 2003-2021
    fitted: -0.2828
    fold_sign: "8/19"
    delta_wk0: 0.0002
    evidence: training-only walk-forward (no fresh holdout)
```

These numbers are consistent with the research prototype (−0.23 to −0.30, wk0 Δ +0.0002, partial coefficient −0.35 with t −1.45).

Fold-sign consistency is measured against the final weight's sign (Pitfall 4). The fold weights are mostly positive in the early folds and turn negative in 2015–2021, and the final weight on all of 2000–2021 is negative. The gate fails on two counts: the final weight is negative, and only 8 of 19 folds share its sign. **07-04 therefore ships the display-only path; there is no draft factor bar.**

## What was built

- **backtest.py:**
  - `_draft_fit(frame, seasons)` is the fit core. It takes `[season, week, composite, y8, draft_z]` rows and asserts every season is ≤ 2021. Within weeks 0–3 it sets x = decay·z and fits the residual slope per fold. It computes pooled wk0 and wk0–3 ΔSpearman, counts the seasons where wk0 Δ > 0, and runs a partial OLS check at week 0.
  - `draft_walk_forward(derived, weights, winsor=None)` cuts snapshots, team_games, pbp, sim, vegas and the surplus to ≤ 2021 before anything is computed, with a hard assert on every frame. It then builds features, applies `score.composite` with the frozen weights, and joins `targets(..., (8,))` and `draft.draft_z`.
  - `draft_gate` and `format_draft_report`.
  - None of the draft functions has an `allow_holdout` parameter or a holdout flag.
- **cli.py:**
  - `fgs backtest --draft` exits 1 when combined with `--include-holdout` ("training-only…") or when weights.yaml is not frozen, and exits 1 when the draft cache is missing. Otherwise it prints the report and writes nothing.
  - `derive_games` now calls `score.load_offseason()` (the `offseason=` kwarg can override it), then `apply_offseason`. It also returns `derived["offseason"]`.
- **score.py:**
  - `load_offseason` reads through `load_weights_doc` and validates the block.
  - `apply_offseason` adds the three display columns. It adds `contrib_draft` and the adjusted composite only when weight ≠ 0.
  - `OFFSEASON_FACTORS` holds the draft label and description. `FACTORS` still has exactly 11 entries.
- **mood.py:** the reference uses `composite_inseason` when that column is present.
- **weights.yaml:** an appended comment paragraph and the `offseason.draft` block. **BACKTEST_LOG.md:** a new `## Offseason terms (Phase 7)` section with its own table.

## Verification

- BEFORE weights.yaml sha256: `44b4c7b9115ca620dbe5ffb588792aecf51c05ca2b86cc440845a6b40cf76320`. The JSON of `[load_weights(), fit, frozen]` is byte-identical before and after (`cmp` passed).
- `git diff HEAD~1 --numstat -- weights.yaml` shows 25 lines added and 0 deleted. `is_frozen()` is still True and `load_weights()` still returns 11 factors.
- `freeze.parse_backtest_log` still returns exactly the 11 in-season factors. It ignores the new table because that table has a `Term` column, not `Factor`.
- `uv run fgs export`: the only change across the 93 files is `meta.json` `generated_at` (checked key by key). Every snapshot, game and history file is byte-identical, so scores are unchanged at weight 0. The churn was reverted.
- `uv run pytest -q`: 471 passed, up from 447 after 07-01 and 07-02.
- Holdout safety:
  - A spy test on `backtest.targets` and `draft.draft_z`, run against real derived data that includes seasons through 2026, sees only season ≤ 2021 inputs. Its fold seasons are exactly 2003–2021.
  - A synthetic test confirms that `_draft_fit` asserts on any 2022 row.
  - `--draft --include-holdout` exits 1.
- Phase 6 hash note: nothing compares the live weights.yaml sha256 with `HOLDOUT_RESULT.json` provenance. The `weights_sha256` is computed only when `fgs holdout` runs, and that command is permanently refused. No test needed changing and the HOLDOUT_RESULT files were not touched. The recorded holdout sha (taken before this plan) no longer matches the live file. That is expected: the frozen content is unchanged, and only the offseason block was appended.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Correctness] Stricter offseason parsing**
- **Found during:** Task 2
- **Issue:** The plan did not say how to handle a non-mapping `offseason` key or a non-bool `display_only`.
- **Fix:** Both now raise ValueError, consistent with the plan's "invalid values raise" contract.
- **Files modified:** pipeline/src/fgs/score.py
- **Commit:** 8ef4a8c

**2. [Minor] Extra CLI refusal for a missing draft cache**
- **Found during:** Task 1
- **Issue:** `fgs backtest --draft` now exits 1 with "draft cache missing; run `uv run fgs build`" instead of raising a traceback from `draft_walk_forward`.
- **Commit:** b67f883

Note on acceptance grep: `grep '"draft"' score.py` matches two lines. One is the `OFFSEASON_FACTORS` key. The other is `off.get("draft")` inside `load_offseason`, which reads the YAML block and is not a factor entry. `FACTORS` has 11 keys and no `draft`.

## TDD Gate Compliance

- Task 1: RED `0d50960` (test), then GREEN `b67f883` (feat).
- Task 2: RED `a6214bf` (test), then GREEN `8ef4a8c` (feat).
- Neither task needed a refactor commit.

## Known Stubs

None. The weight-0 path is the intended outcome (display-only), not a stub.

## Self-Check: PASSED

- FOUND: pipeline/src/fgs/backtest.py (def draft_gate), pipeline/src/fgs/score.py (def apply_offseason), pipeline/weights.yaml (offseason:), pipeline/BACKTEST_LOG.md (Offseason terms)
- FOUND commits: 0d50960, b67f883, a6214bf, 8ef4a8c, 760da35
- Unchanged: HOLDOUT_RESULT.md/.json, PREREGISTRATION.md, FREEZE_RESULT.json, and the `weights:`/`fit:`/metadata lines of weights.yaml. Nothing computed a draft metric on 2022–2025.

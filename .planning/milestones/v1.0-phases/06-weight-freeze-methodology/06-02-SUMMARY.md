---
phase: 06-weight-freeze-methodology
plan: 02
subsystem: pipeline/weight-freeze
tags: [ridge, freeze, bootstrap, guards, holdout-seal, weights]
requires:
  - 06-01 (PREREGISTRATION.md committed, fgs.bootstrap)
provides:
  - fgs.backtest.walk_forward_frame (rows + composite, every fold, per-game probabilities)
  - fgs.score.load_weights_doc / is_frozen
  - fgs.paths PREREG_PATH, FREEZE_RESULT_PATH, HOLDOUT_MD_PATH, HOLDOUT_JSON_PATH
  - fgs.freeze (build_freeze, walk_forward_ci, render_weights_yaml, format_weight, fold_sign_consistency, factor_deltas, parse_backtest_log)
  - "`fgs freeze [--unfreeze]` and refusal guards on backtest --propose-weights / --include-holdout"
  - pipeline/weights.yaml frozen (11 factors) + pipeline/FREEZE_RESULT.json
affects: [06-03 holdout evaluator (reads frozen weights + guards), 06-04 methodology.json (reads FREEZE_RESULT.json), 06-05 README]
tech-stack:
  added: []
  patterns: [text-template YAML with round-trip assert, guards before data load tested with derive patched to raise, paired bootstrap on a common game set]
key-files:
  created:
    - pipeline/src/fgs/freeze.py
    - pipeline/tests/test_freeze.py
    - pipeline/FREEZE_RESULT.json
    - .planning/phases/06-weight-freeze-methodology/deferred-items.md
  modified:
    - pipeline/src/fgs/backtest.py
    - pipeline/src/fgs/score.py
    - pipeline/src/fgs/paths.py
    - pipeline/src/fgs/cli.py
    - pipeline/tests/test_backtest.py
    - pipeline/tests/test_export.py
    - pipeline/tests/test_leakage.py
    - pipeline/weights.yaml
    - web/public/data/** (regenerated)
decisions:
  - "Frozen weights are the freeze output as-is. 5 of 11 differ from the 05-05 interim values at 2 dp (season_record, last16, streak, vs_exp, po_trend). Phase 5 sim review fixes after 05-05 changed the playoff-odds inputs. Nothing was hand-edited (MODEL-15)."
  - "Brier evidence uses the intersection of games where every candidate has a probability (5082 games), so the paired diffs compare like with like"
  - "A missing or unreadable weights.yaml counts as not frozen in the CLI guards, so the WR-05 'backtest needs no weights file' behavior is preserved"
  - "The export never-refits test pairs the synthetic league (score path, no cache) with a full build_export on cached data. build_export asserts real season structure, which the tiny synthetic league can't satisfy."
metrics:
  duration: ~25 min
  completed: 2026-11-11
  tasks: 3
  files: 13 (+ regenerated site data)
---

# Phase 6 Plan 02: Weight Freeze Summary

`fgs freeze` refit the existing 11-factor LOSO-alpha Ridge on 1999–2021 once and froze weights.yaml with every sign as fitted. Each factor carries its k/19 walk-forward fold consistency. It also committed FREEZE_RESULT.json: on 2003–2021 walk-forward, the composite beats Elo at Spearman N=8 by +0.0130 (both CIs above 0, 14 of 19 seasons won). Refit and holdout-peek paths now refuse before loading any data.

## Tasks

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Walk-forward evidence frame, frozen-file readers, paths | 84c6143 | backtest.py, score.py, paths.py, test_backtest.py |
| 2 | freeze.py + `fgs freeze` + refusal guards | f9f4f0f | freeze.py, cli.py, test_freeze.py, test_export.py, test_leakage.py |
| 3a | Freeze final weights + FREEZE_RESULT.json | 41e1e54 | pipeline/weights.yaml, pipeline/FREEZE_RESULT.json |
| 3b | Regenerate site data with frozen weights | c90ec96 | web/public/data/** |

## Frozen weights (fit 1999–2021, alpha = 0.01·n, n = 12331, fitted_at 2026-11-11)

| factor | frozen | raw | sign | folds | interim (05-05) | ΔSpearman N8 |
|---|---|---|---|---|---|---|
| elo | 2.59 | +2.5931 | + | 19/19 | 2.59 | (baseline 0.5114) |
| season_record | 1.84 | +1.8410 | + | 19/19 | 1.83 | +0.0008 |
| last16 | −0.21 | −0.2100 | − | 14/19 | −0.20 | +0.0033 |
| mov | 1.24 | +1.2407 | + | 19/19 | 1.24 | +0.0026 |
| sow | −0.56 | −0.5595 | − | 14/19 | −0.56 | +0.0047 |
| streak | −0.03 | −0.0320 | − | 12/19 | −0.05 | +0.0000 |
| luck | −0.35 | −0.3511 | − | 19/19 | −0.35 | −0.0008 |
| epa_traj | −0.33 | −0.3274 | − | 19/19 | −0.33 | −0.0001 |
| qb_trend | 0.63 | +0.6315 | + | 19/19 | 0.63 | +0.0028 |
| vs_exp | −1.22 | −1.2213 | − | 18/19 | −1.23 | +0.0019 |
| po_trend | −0.05 | −0.0513 | − | 17/19 | −0.01 | −0.0003 |

**Differences from the interim proposal (more than 0.01):** streak −0.05 → −0.03 (Δ 0.02) and po_trend −0.01 → −0.05 (Δ 0.04). season_record, last16 and vs_exp moved by exactly 0.01. Both values are recorded and the freeze output is kept, as the plan directs.

The likely cause: after the 05-05 interim fit (9c51be4), the Phase 5 code-review fixes changed the season simulator. These were IN-04 common random numbers (c6b2e4e), WR-07 wildcard tiebreaks (c027c36), WR-05/06 sim cache keys and others. That changed the playoff-odds inputs to po_trend, and its correlated neighbours shifted with it. The walk-forward composite N8 is unchanged at 0.5262, which matches 05-05's 0.5262.

## Walk-forward evidence (2003–2021, B = 2000, seed 20221)

- **Spearman N=8:** composite 0.5262 (season-block CI [0.5046, 0.5460], team-season CI [0.4841, 0.5633]); Elo 0.5132 ([0.4884, 0.5346] / [0.4700, 0.5518]).
- **Composite − Elo, N=8:** +0.0130. Season-block CI [+0.0019, +0.0245], team-season CI [+0.0031, +0.0235]. Composite won 14 of 19 seasons.
- **Spearman N=4:** composite 0.4758 vs Elo 0.4657.
- **Brier** (5082 games, the common set): composite 0.2178, Elo 0.2197, spread 0.2112, elo_538 0.2194.
  - Composite − Elo −0.0018: season-block [−0.0028, −0.0010], season-week [−0.0029, −0.0008].
  - Composite − spread +0.0067: season-block [+0.0047, +0.0087], season-week [+0.0046, +0.0088]. The spread is the market ceiling, as expected.
- **BACKTEST_LOG cross-check:** max |computed − logged| = 0.00005, no warnings.

## Verification

- **Task 1 regression gate:** I copied `data/derived/backtest.json` and the stdout of `uv run fgs backtest` to the scratchpad before the refactor, re-ran after it, and compared them with `diff $S/backtest_before.json data/derived/backtest.json` and `diff $S/before.txt $S/after.txt`. Both diffs were empty (IDENTICAL).
- `uv run pytest tests/test_backtest.py tests/test_score.py -x -q`: 29 passed. `grep -cE "^\s*(from|import)\s+[\w., ]*backtest" src/fgs/score.py` = 0.
- `uv run pytest tests/test_freeze.py tests/test_export.py tests/test_leakage.py`: all passed, including the sealing test (≥2022 home/away results swapped give identical factors and walk_forward), the four guard tests with `cli.derive`/`load_schedules`/`cached_inputs` patched to raise, the CLI write path, and `-k never_refits`.
- `grep -cE "^\s*(from|import)\s+[\w., ]*(freeze|holdout)"` is 0 for score, features, export, mood and explain.
- **Task 3 preconditions:**
  - PREREGISTRATION.md was added once (42e57aa) and is clean.
  - HOLDOUT_RESULT.md is absent.
  - The interim weights.yaml was not frozen, so the freeze ran as plain `uv run fgs freeze` (35 s).
- **Task 3 checks:**
  - The plan's automated verify passes: frozen true; 11 factors, each with fold_sign n = 19; no `-0.00` weight line.
  - The PREREGISTRATION commit 42e57aa is an ancestor of the weights.yaml commit 41e1e54.
  - `load_weights()` returns 11 weights. FREEZE_RESULT.json is tracked.
- **Real-file guards:** `uv run fgs backtest --propose-weights` and `uv run fgs freeze` each exit 1 with "weights are frozen". `--include-holdout` was not run, so it is covered only by the unit test.
- **Full gates:**
  - Pipeline: `uv run pytest -q` 343 passed.
  - Web (Node 22): `npm test` 69 passed, `npm run check` 0 errors / 0 warnings, `npm run build` OK.
- **Holdout discipline:** nothing computed a metric on 2022–2025. walk_forward_ci also raises if handed seasons past 2021.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The never_refits test can't run build_export on the synthetic league**
- **Found during:** Task 2
- **Issue:** `build_export` asserts real season structure (reg_weeks per season), so the two-season synthetic fixture fails before any weights logic. The percentile reference also needs REF_SEASONS to cover the fixture.
- **Fix:** `test_export_never_refits` patches `backtest.ridge_fit`, `propose_weights` and `choose_alpha` to raise. Under that patch it runs the synthetic score path (derive_games → score_frame → explain points, REF_SEASONS patched to 2023) and the full `build_export` on cached data, following the `test_latest_partial_week_synthetic` pattern. The second part skips without a cache.
- **Files modified:** pipeline/tests/test_export.py
- **Commit:** f9f4f0f

**2. [Rule 2 - Correctness] Guard on a missing weights file**
- **Found during:** Task 2
- **Issue:** `score.is_frozen()` raises ValueError when weights.yaml is missing. That would break `test_cli_backtest_writes_json` (WR-05: the backtest must not need a weights file).
- **Fix:** Added `cli._weights_frozen()`, which treats a missing or unreadable file as not frozen.
- **Commit:** f9f4f0f

**3. Extra guard patching:** The guard tests also patch `cli.load_schedules` and `cli.cached_inputs` to raise, not just `cli.derive`. Those run before `derive` in the call expression, so this makes "guards run before any data load" strict.

## Deferred Issues

See `deferred-items.md`. README.md still lists the interim weights (1.83 / −0.20 / −0.05 / −1.23 / −0.01) and says "interim until Phase 6". README.md is outside this plan's files and 06-05 owns the README edit.

## Known Stubs

None.

## TDD Gate Compliance

Tasks 1–2 are marked tdd="true", but the plan specified single commit messages for them (`refactor(...)`, `feat(...)`), so tests and implementation were committed together, with no separate `test(...)` RED commit. Task 1's regression gate (byte-identical backtest.json) served as its safety net.

## Self-Check: PASSED

- FOUND: pipeline/src/fgs/freeze.py, pipeline/tests/test_freeze.py, pipeline/FREEZE_RESULT.json, pipeline/weights.yaml (frozen: true)
- FOUND commits: 84c6143, f9f4f0f, 41e1e54, c90ec96

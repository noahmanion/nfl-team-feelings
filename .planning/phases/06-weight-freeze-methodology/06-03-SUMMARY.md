---
phase: 06-weight-freeze-methodology
plan: 03
subsystem: pipeline/holdout
tags: [holdout, bootstrap, preregistration, cli, guards]
requires: [06-01 bootstrap.py, 06-02 frozen weights.yaml + paths + freeze helpers]
provides: [holdout.evaluate_frozen, holdout.verdict, holdout.render_markdown, holdout.git_state, holdout.file_sha256, "fgs holdout"]
affects: [06-04 (reads HOLDOUT_RESULT.json schema), 06-05 (runs `fgs holdout` once)]
tech-stack:
  added: []
  patterns: [paired percentile bootstrap shared across candidates, guard-before-load CLI, git provenance via subprocess]
key-files:
  created:
    - pipeline/src/fgs/holdout.py
    - pipeline/tests/test_holdout.py
  modified:
    - pipeline/src/fgs/cli.py
decisions:
  - "fgs holdout also refuses when `git status --porcelain` under pipeline/src is non-empty (orchestrator instruction), and records provenance.src_clean"
  - "Stand-in Spearman equality is checked at the 6-dp precision of backtest._clean (the result is strict-JSON rounded), not on raw floats"
  - "Brier uses freeze._brier_block on the common game set where every p (incl. spread, elo_538) is defined"
metrics:
  duration: ~25 min
  completed: 2026-11-11
  tasks: 2
  files: 3
---

# Phase 6 Plan 03: One-time holdout evaluator and guarded `fgs holdout` Summary

`holdout.evaluate_frozen` scores the shipped frozen composite against Elo and the baselines. It adds paired season-block and stratified-cluster bootstrap CIs and the pre-registered verdict. The `fgs holdout` command is guarded so it runs only once. Both were tested only on the 2018–2021 stand-in (weights fit on 1999–2017) and on mocks. The real 2022–2025 holdout was not run.

## Tasks

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | holdout.py: evaluate_frozen, verdict, render_markdown, git_state | 27bf5a7 | pipeline/src/fgs/holdout.py, pipeline/tests/test_holdout.py |
| 2 | `fgs holdout` with one-time guards and result writing | c7c2511 | pipeline/src/fgs/cli.py, pipeline/src/fgs/holdout.py (docstring), pipeline/tests/test_holdout.py |

## What was built

- **evaluate_frozen**
  - Season guard: raises unless `hi <= TRAIN_LAST_SEASON` or the caller opts in. It also raises on a weight mismatch with `derived["weights"]` (Pitfall 8) and when `fit_last >= lo`.
  - Reads no data past `hi`.
  - Computes Spearman at N=8 (pooled, by bucket, per season) and N=4 for composite, elo, season_wpct, last16 and pd_pg.
  - Fits the Brier logistic maps once, on seasons <= fit_last (`_brier_maps`). elo_538 uses the closed form.
  - Paired bootstraps: season-block, team-season stratified (Spearman) and season-week stratified (Brier).
  - Also reports won-k-of-n, the vs_exp-zeroed diagnostic (prereg §10), and the factors with their fold_sign values from the weights.yaml `fit` block.
- **verdict / HEADLINES**: implements prereg §8 word for word, keyed on the wider CI (cluster wins ties). A test checks that each sentence appears verbatim in PREREGISTRATION.md. `passed(diff)` is `diff > 0`.
- **render_markdown**: verdict, BACK-06 PASS/FAIL, provenance, candidate table, differences, diagnostic, factor table, bootstrap footnote, and a `## Reruns` section when there were reruns.
- **`fgs holdout`**: the guards below all run before any data load. It then re-derives from the cache with the frozen weights, calls `evaluate_frozen(..., HOLDOUT_SEASONS, TRAIN_LAST_SEASON, allow_holdout=True)` (the only such call in src), and writes HOLDOUT_RESULT.json, HOLDOUT_RESULT.md and data/derived/holdout.json, in that order, before printing.
  - Guard 1: the result already exists (refused unless `--force`).
  - Guard 2: the weights are not frozen, or the weights file is missing.
  - Guard 3: the prereg is missing.
  - Guard 4: the prereg or weights file is dirty.
  - Guard 5: the prereg's adding commit is not an ancestor of the weights commit.
  - Guard 6: pipeline/src is dirty.
  - If git is unavailable it prints a warning and continues.

## Stand-in check (training data only, B=2000)

These match the stand-in figures quoted in prereg §11.3:

| Measure | Result |
| ------- | ------ |
| composite − Elo, Spearman N=8 | +0.0187 |
| season-block CI | [+0.0036, +0.0419] |
| team-season CI | [−0.0031, +0.0399] |
| verdict | slight |
| seasons won | 3 of 4 |
| distinct season-block resamples | 35 |

## Verification

- `uv run pytest tests/test_holdout.py`: 33 passed. Full `uv run pytest -q`: 387 passed. That count includes the concurrent 06-04 work-in-progress files that were in the tree at the time.
- `grep -rn "allow_holdout=True" src/fgs/` finds exactly one hit, in cli.py. tests/ has zero. `test_holdout_opt_in_only_in_cli` enforces this.
- `pipeline/HOLDOUT_RESULT.md` and `HOLDOUT_RESULT.json` do not exist.
- The only 2022–2025 references in test_holdout.py are:
  - the guard test that expects a raise;
  - the fixed prereg headline sentences;
  - the mock CLI assertion, which compares against `HOLDOUT_SEASONS`.

## Deviations from Plan

1. **[Orchestrator instruction] Dirty-src guard.** `git_state` also returns `src_dirty`, which holds the porcelain lines under `pipeline/src`. `fgs holdout` refuses when that list is non-empty, and `provenance.src_clean` (bool, or null when git is unavailable) records the state. The plan said to keep exactly the listed provenance keys, so this extra key is additive. Covered by `test_holdout_guard_src_dirty` and `test_git_state_src_dirty`.
2. **[Rule 3] holdout.py docstring.** The plan's verbatim docstring contained the literal `allow_holdout=True`, which would have made the plan's own "exactly one hit in src" check fail. I reworded it to "may set the allow_holdout opt-in". (c7c2511)
3. **[Rule 1] Precision of the stand-in equality.** evaluate_frozen returns values through `backtest._clean`, which rounds to 6 dp, so a raw 1e-12 equality isn't possible. The test compares against `round(spearman(Σ w·z, y8), 6)` to 1e-12. The composite − elo diff check uses a tolerance of 2e-6.
4. **Extra guard.** evaluate_frozen also raises if `fit_last >= lo`, so the Brier maps can never be fit on evaluated seasons.
5. **Extra tests:** a missing weights file counts as not frozen; untracked weights.yaml counts as dirty; the opt-in appears only in cli.py.

PREREGISTRATION.md and this plan do not differ in substance.

## TDD Gate Compliance

Both tasks are tdd="true", but the plan specified a single `feat(...)` commit per task, so tests and implementation went in together. There are no separate `test(...)` RED commits. The pure verdict/guard tests and the stand-in tests were written against the spec and passed on the first run of the implementation. The one failure (the "pre-registration" wording in the commit-order message) was fixed before commit.

## Known Stubs

None. `provenance`, `evaluated_at` and `rerun` are left defaulted by evaluate_frozen on purpose. The CLI fills them in, and the tests cover that.

## Self-Check: PASSED

- FOUND: pipeline/src/fgs/holdout.py, pipeline/tests/test_holdout.py, pipeline/src/fgs/cli.py (`_cmd_holdout`)
- FOUND commits: 27bf5a7, c7c2511

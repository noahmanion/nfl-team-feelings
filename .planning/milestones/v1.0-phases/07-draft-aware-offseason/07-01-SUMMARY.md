---
phase: 07-draft-aware-offseason
plan: 01
subsystem: pipeline
tags: [draft, surplus, data-06, model-16, cli, checks]
requires: []
provides:
  - "fgs.draft: PFR_TO_FRANCHISE, map_pfr, load_draft_picks, load_draft_values, normalize_picks, value_table, standings, original_order, align, surplus_table, winsor_bounds, draft_z, decay, equiv_pick, pick_noun (+ derivable_years, SURPLUS_SCHEMA, FORFEITS_R12, N_ROUNDS)"
  - "derived['draft'] (surplus_table frame or None) and derived['draft_values'] (value array or None) from derive()/derive_games(), also when scored=False"
  - "cli.cached_inputs() returns draft_picks + draft_values"
  - "`fgs draft [--season YYYY]`"
  - "checks draft_coverage, draft_sum"
affects: [07-03, 07-04]
tech-stack:
  added: []
  patterns:
    - "Standings-derived original slots aligned to actual picks with an edit-distance DP (sub 1 / del 3 / ins 4, free comp tail in rounds 3-7)"
    - "Frozen CSV loader (draft_values.csv) and owned-parquet loader (draft_picks.parquet), same as win_totals / schedules"
key-files:
  created:
    - pipeline/src/fgs/draft.py
    - pipeline/tests/test_draft.py
  modified:
    - pipeline/src/fgs/cli.py
    - pipeline/src/fgs/checks.py
    - pipeline/tests/test_cli.py
    - pipeline/tests/test_leakage.py
decisions:
  - "surplus_table takes an optional `forfeits` override (default FORFEITS_R12) so synthetic tests can exercise the forfeit table"
  - "Real-cache tests build team_games with build_games -> build_team_games (no Elo replay): standings only need outcomes, and it keeps them fast"
  - "Derivable drafts = years present in picks, >= 2000, whose prior season has played REG games (plan-checker note)"
  - "`fgs draft` derives unscored and read-only on the sim cache (sim_write_cache=False)"
metrics:
  duration: ~25min
  completed: 2026-11-11
  tasks: 2
  files: 6
---

# Phase 7 Plan 01: Draft Surplus Engine Summary

This plan adds a draft-capital-over-slot metric. A team's original slots come from the prior season's standings and are aligned to the picks it actually made, using nflverse draft picks and the stuart value chart. The result is available as `derived['draft']`, as `fgs draft --season YYYY`, and through the DATA-06 checks. A team that kept its own #1 pick scores exactly 0 (CIN 2020), so tanking earns nothing.

## What was built

- **`pipeline/src/fgs/draft.py`** (new, pure apart from two loaders, never imports backtest):
  - The PFR-to-franchise map raises on unknown codes.
  - `standings` gives REG win % with ties counted as .5, SOS, and a playoff stage group (0–5).
  - `original_order` sorts by stage, then win %, then SOS, then id. Tied groups rotate each round, and HOU goes first in 2002.
  - `align` is an edit-distance DP with deterministic backtracking.
  - `surplus_table` charges R1–R2 forfeit-table slots and alignment deletions to the slot owner only. Comp tails are excluded from both sides.
  - Also provides `winsor_bounds`, `draft_z` (clip, then z within each draft), `decay`, `equiv_pick` and `pick_noun`.
- **CLI:**
  - `cached_inputs()` adds `draft_picks`/`draft_values` and warns when either is missing.
  - `derive`/`derive_games` take them as keyword args.
  - `build_all` fetches both.
  - `_cmd_refresh` downloads picks in memory, saves `draft_picks.parquet` only after the checks pass, and falls back to the cache if the download fails.
  - New `fgs draft` subcommand. It exits 1 for a missing cache or a non-derivable year (1999: "no 1998 standings").
- **Checks:** `draft_coverage` expects 31 franchises for 2000–2001 and 32 from 2002, with no null surplus. `draft_sum` requires Σ ≤ 1e-9 per draft. Both pass vacuously when `derived['draft']` is None.
- **Tests:**
  - 37 synthetic tests, selectable with `-k pfr/order/align/surplus/winsor/decay/equiv`.
  - One checks unit test.
  - Six real-cache acceptance tests that skip without the cache.

## Real-data results (cache fetched by `uv run fgs build`)

```
draft: 7154 picks, surplus for drafts 2000-2026
2020 draft: capital over original slots (chart stuart); winsor bounds 2000-2021 [-17.29, +16.19]
 13  CIN      1      0.0  —                         +0.12
```

- MIA 2020 +39.8 and CLE 2018 +37.9 (ranked #1 in their drafts). LV 2012 < −20 and LA 2022 < −15 (tested).
- The winsor bounds match the research exactly: (−17.29, 16.19).
- `fgs check` passes. `draft_coverage` and `draft_sum` are ok.
- The full suite passes: 447 tests.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Refresh/build CLI tests would hit the network for draft data**
- **Found during:** Task 2
- **Issue:** `test_refresh_*` run against a tmp cache, so the new draft loaders would try to download picks and values. The abort test's cache-file assertion also failed because `draft_values.csv` appeared.
- **Fix:** The `refresh_dirs` fixture now copies the frozen `draft_values.csv` the same way it copies `win_totals.csv`, and stubs `draft.load_draft_picks` with the real cached file (or raises without one). The abort test excludes the frozen files and still asserts that `draft_picks.parquet` was not written. The happy path asserts that picks are saved after the checks and that both draft checks print ok. The build test stubs both loaders. The `test_unscored_derive_needs_no_weights_file` key set now includes `draft`/`draft_values`.
- **Files modified:** pipeline/tests/test_cli.py
- **Commit:** b59e75c

**2. [Minor] Exact-zero surplus prints as `0.0`, not `+0.0`, in `fgs draft`** (readability; the pick-equivalent column shows "—" for zero).

## TDD Gate Compliance

RED `ac0026f` (test), then GREEN `4a24644` (feat). No refactor commit was needed.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: pipeline/src/fgs/draft.py, pipeline/tests/test_draft.py, pipeline/data/cache/draft_picks.parquet, pipeline/data/cache/draft_values.csv
- FOUND commits: ac0026f, 4a24644, b59e75c
- No changes to weights.yaml, PREREGISTRATION.md, FREEZE_RESULT.json, HOLDOUT_RESULT.*. Nothing evaluated 2022–2025 outcomes.

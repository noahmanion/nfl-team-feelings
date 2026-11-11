---
phase: 05-efficiency-qb-trend-season-simulator
plan: 01
subsystem: pipeline
tags: [pbp, epa, nflreadpy, polars, cache, cli]
requires: []
provides:
  - "fgs.pbp: SLIM_COLUMNS, load_pbp_season, load_all_pbp, cached_seasons, scrimmage, team_game_epa, KNOWN_NO_PBP, check_pbp"
  - "derived['team_game_epa'] (keyword-only pbp_games on derive/derive_games)"
  - "cli.cached_inputs() -> {'pbp_games': ...} for cache-reading commands/tests"
  - "pbp_coverage data-trust check"
affects: [05-03, 05-04, 05-05]
tech-stack:
  added: []
  patterns: ["per-season slim parquet cache with atomic writes", "check-then-write refresh for pbp"]
key-files:
  created:
    - pipeline/src/fgs/pbp.py
    - pipeline/tests/test_pbp.py
  modified:
    - pipeline/src/fgs/cli.py
    - pipeline/src/fgs/checks.py
    - pipeline/tests/conftest.py
    - pipeline/tests/test_cli.py
    - pipeline/tests/test_checks.py
    - pipeline/tests/test_backtest.py
    - pipeline/tests/test_export.py
    - pipeline/tests/test_leakage.py
decisions:
  - "pbp_seasons() accepts raw schedules (played = result not null), so refresh picks seasons before the code checks run and a bad team code still surfaces as a check FAIL, not a crash"
  - "refresh re-downloads only the current season plus any season missing from the cache, all in memory; saved via save_cache only after checks pass and the export builds"
  - "fgs check also feeds cached pbp (cached_inputs) so pbp_coverage runs there"
metrics:
  duration: "~25 min"
  completed: 2026-11-11
  tasks: 2
  files: 10
---

# Phase 5 Plan 01: pbp ingest and team-game EPA Summary

This plan adds nflverse play-by-play to the pipeline. Each season is downloaded once, slimmed to 20 columns and cached as parquet. The plays are then aggregated into one row per team per game: garbage-time-filtered offense, defense and net EPA per play, plus the primary QB's EPA per dropback and success rate. Scrambles count toward the QB through `passer_id`. 1999–2000 rows are flagged `low_confidence`. `fgs build` fills the cache, `fgs refresh` re-pulls only the current season and writes it only after checks pass, and `derive(...)` carries the frame as `team_game_epa`.

## Results

- `uv run fgs build` printed `pbp: 14818 team-games, seasons 1999-2026`. `data/derived/team_game_epa.parquet` has 14,818 rows, and `low_confidence` seasons are `[1999, 2000]`.
- 28 season files sit in `pipeline/data/cache/pbp/`, which is gitignored. `git status --porcelain pipeline/data` is empty.
- `uv run fgs check` passes all checks, including `ok    pbp_coverage`. The only played games without pbp are the 3 in KNOWN_NO_PBP.
- `uv run pytest -q` reports 271 passed, including the real-cache pbp tests, which did not skip.
- No score factor changed, so the site export is unchanged and was not re-run.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 (RED) | 5cd28fb | test: synthetic-play + real-cache tests for pbp |
| 1 (GREEN) | 8405508 | feat: pbp.py slim cache, scrimmage, team_game_epa, check_pbp |
| 2 | 8606300 | feat: CLI/check wiring, cached_inputs, test fixture updates |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] pbp_seasons works on raw schedules**
- **Found during:** Task 2
- **Issue:** Computing seasons through `build_games(raw)` raised ValueError on a bad team code before `_checked_derive` could report it. The refresh abort test expects a clean `FAIL  codes` and exit 1.
- **Fix:** `_current_season` derives `played` from `result` when the column is absent. build and refresh call `pbp_seasons(raw)`.
- **Commit:** 8606300

**2. [Rule 2] `fgs check` uses cached pbp**
- **Issue:** The plan lists export/backtest as `cached_inputs()` users. Without it, `fgs check` would never run `pbp_coverage`, but the acceptance criteria require `ok    pbp_coverage`.
- **Fix:** `_cmd_check` calls `_checked_derive(raw, **cached_inputs())`.

**3. Cache seeded from the research scratchpad**
- The orchestrator allowed it, so the 28 research pbp files were slimmed to SLIM_COLUMNS and copied into `pipeline/data/cache/pbp/` instead of being downloaded cold. The schema matches. Coverage against the current schedules cache is exact, with only the 3 known gaps. A later `fgs build --refresh` or `fgs refresh` re-pulls the current season.

**4. Extra items**
- `pbp.cached_seasons()` and `pbp.TGE_COLUMNS` were added as helpers.
- `test_cli.test_unscored_derive_needs_no_weights_file` now expects the `team_game_epa` key, as the plan requires.

## TDD Gate Compliance

The RED commit `test(05-01)` (5cd28fb) came before the GREEN commit `feat(05-01)` (8405508). The tests failed at collection without pbp.py. No refactor was needed.

## Known Stubs

None. `team_game_epa` is carried in the derived dict but not yet used by features. That is by design: plan 05-03 consumes it.

## Self-Check: PASSED

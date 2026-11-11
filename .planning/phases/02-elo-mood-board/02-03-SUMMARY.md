---
phase: 02-elo-mood-board
plan: 03
subsystem: pipeline-cli + docs
tags: [refresh, checks, partial-week, readme]
requires:
  - fgs.export.build_export / write_export (02-01)
  - fgs.checks.run_checks, check_columns, check_codes
  - fgs.ingest.load_schedules / load_teams (refresh=True)
provides:
  - "`uv run fgs refresh`: re-download -> derive -> check -> parquet -> site JSON, writing nothing on failure"
  - fgs.cli._checked_derive (shared by check and refresh)
  - fgs.cli._write_derived (shared by build and refresh)
  - README covering idea / run / status
affects:
  - 02-04 (the fatal-error copy that names `uv run fgs refresh` now points at a real command)
tech-stack:
  added: []
  patterns:
    - check-then-write: every check and the pure build_export run before any file is written
key-files:
  created: []
  modified:
    - pipeline/src/fgs/cli.py
    - pipeline/tests/test_cli.py
    - pipeline/tests/test_export.py
    - web/public/data/meta.json
    - README.md
decisions:
  - "refresh runs build_export (pure) before _write_derived, so an export assertion also leaves the parquet untouched"
  - "Partial-week tests derive (season, week) from the cached data; next-week case skips when the season has no unplayed week w+1 game"
metrics:
  duration: 6min
  completed: 2026-11-11
  tasks: 2
  files: 5
---

# Phase 2 Plan 03: One-Command Refresh + README Summary

`uv run fgs refresh` is now the weekly command. It re-downloads schedules and teams from nflverse, runs every pre-derive and post-derive check, and only if all of them pass writes the derived parquet and regenerates `web/public/data/`. On any failure it exits 1 and writes nothing. The README now explains the idea, how to run both halves, and where the project stands.

## What was built

**Task 1 (TDD): `fgs refresh`**
- `_checked_derive(raw)` returns `(ok, derived | None, params)` and prints the same ok/FAIL lines `fgs check` printed before. `_cmd_check` is now a thin wrapper around it, and its output and exit codes are unchanged.
- `_write_derived(out)` writes the three parquet files. `build_all` and `refresh` both use it.
- `_cmd_refresh` runs: `load_schedules(refresh=True)`, then `load_teams(refresh=True)`, then `_checked_derive`, then `build_export`, then `_write_derived`, then `write_export(files, WEB_DATA_DIR)`. It prints `refreshed: exported N files; latest S week W (partial=...); data through YYYY-MM-DD`.
- Every dependency is looked up as a `fgs.cli` module name at call time, so tests can monkeypatch them.
- New tests:
  - Refresh abort: a raw row with code `XXX` makes refresh exit 1, and the sentinel files are byte-identical with no new files in either directory.
  - Refresh happy path: the network is mocked by reading the caches.
  - Partial current week: the last game by gameday and gametime is un-played.
  - Partial next week: one game in week w+1 gets a score. Teams that didn't play keep their Elo and get `score_delta == 0`.
  - The `partial_week` flag matches `week_progress` on real data.

**Task 2: real run and README**
- `uv run fgs refresh` ran against live nflverse and exited 0: 64 files, latest 2026 week 9, partial=False, data through 2026-11-09. This matches the `fgs elo` header.
- Only `meta.json` changed (`generated_at` 2026-11-11T18:40:56+00:00). The scores were byte-identical, and it's committed.
- The README is 46 lines:
  - Refresh and export commands.
  - Starting the site with `nvm use && npm install` once, then `npm run dev`.
  - The other pipeline commands.
  - How the score works, including the note that historical scores can drift by 1 after a refresh.
  - A Status line saying Phase 2 is done.

## Verification

- `cd pipeline && uv run pytest -q`: 118 passed.
- `-k refresh` selects 2 tests and `-k partial` selects 4. All passed with no skips.
- `uv run fgs refresh --help` exits 0, and `uv run fgs check` prints "all checks passed".
- In `_cmd_refresh`, `write_export` comes after `_checked_derive`.
- The Task 2 grep and meta assertions pass.

## Deviations from Plan

None. The plan was executed as written. One note: the existing 02-01 test `test_latest_partial_week_synthetic` also matches `-k partial`. The new partial-week tests passed in the RED commit because 02-01's `build_export` already supported partial weeks, so only the refresh tests were truly RED.

## TDD Gate Compliance

- RED: `1a164b1` (test). GREEN: `ff68fff` (feat). No refactor commit was needed.

## Known Stubs

None added. `callouts.json` is still `[]` on purpose, as recorded in 02-01.

## Commits

- 1a164b1 test(02-03): add failing refresh tests and partial-week export tests
- ff68fff feat(02-03): fgs refresh runs every check before writing parquet or site JSON
- d28f72c docs(02-03): regenerate site JSON via fgs refresh; README covers idea, run, status

## Self-Check: PASSED

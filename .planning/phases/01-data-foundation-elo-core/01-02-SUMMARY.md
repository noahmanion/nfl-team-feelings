---
phase: 01-data-foundation-elo-core
plan: 02
subsystem: pipeline
tags: [python, polars, data-checks, season-config, cli, pytest]

requires:
  - phase: 01-01
    provides: "fgs.cli.derive, games/team_games/snapshots frames, franchise map, season_config (HFA/seeds)"
provides:
  - "fgs.season_config era table: n_teams, reg_games, reg_weeks, playoff_teams, season_rules, DIVISIONS_1999_2001/2002_ON, divisions, division_of, conference_of, ENTRY_SEASON, EXPECTED_GAME_EXCEPTIONS"
  - "fgs.checks: 10 pure check_* functions, CHECKS registry, run_checks, run_all"
  - "`uv run fgs check`: the single data-trust gate (exit 1 on any failure)"
affects: [01-03 snapshot grid check + CLI hardening, phase 2 JSON export (conference/division lookups), phase 4 playoff sims (playoff_teams, divisions)]

tech-stack:
  added: []
  patterns:
    - "Checks are pure functions returning list[str]; CLI prints, pytest asserts == []"
    - "CHECKS is a list of (name, fn(raw, derived)) so later plans append checks without touching the CLI"
    - "divisions() reads module-level tables at call time so tests can monkeypatch them"

key-files:
  created:
    - pipeline/src/fgs/checks.py
    - pipeline/tests/test_checks.py
  modified:
    - pipeline/src/fgs/season_config.py
    - pipeline/src/fgs/cli.py
    - README.md

key-decisions:
  - "test_elo_sanity uses top-5 wins >= losses and bottom-5 losses >= wins, so a .500 team cannot fail it; plan 03 does the human plausibility check"
  - "Division graph check uses a hand-rolled union-find (no networkx dependency)"
  - "fgs check runs columns and codes before deriving and exits 1 without deriving if either fails"
  - "check_continuity also flags any post-entry week-0 row that has no prior-season final, so a missing season cannot pass silently"

patterns-established:
  - "run_checks(raw, derived) -> [(name, failures)] for per-check reporting; run_all flattens it with name prefixes"

requirements-completed: [DATA-02, DATA-03, DATA-04, DATA-07, MODEL-01]

duration: 8min
completed: 2026-11-11
---

# Phase 1 Plan 02: Era Rules and `fgs check` Summary

**`uv run fgs check` asserts 31/32 franchises, 16/17 REG games per team-season (BUF/CIN 2022 allowed 16), only known team codes, unbroken LV/LAC/LA/WAS history with exact 1/3 regression at each season boundary, div_game components equal to the era division table, per-game Elo zero-sum, and a league mean of 1505 from 2012 on. All checks pass on the real 1999–2026 data.**

## Performance

- **Duration:** ~8 min
- **Completed:** 2026-11-11
- **Tasks:** 2/2
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments

- `season_config` is now a single era lookup: team counts, REG games and weeks, playoff teams (12 or 14), HFA, divisions for 1999–2001 and for 2002 onward, conference lookup, HOU entry season, and the BUF/CIN 2022 exception. `check_config_coverage` and `check_divisions` validate it against the data. The real WC counts (4 per season through 2019, 6 from 2020) match playoff_teams.
- `checks.py` holds 10 pure checks plus the `CHECKS` registry, ready for plan 03 to append `check_snapshot_grid`.
- `fgs check` prints `ok` or `FAIL` for each of its 10 checks and exits 0 on real data. With an injected `XXX` code it exits 1, names `XXX`, and does not derive.
- 16 new tests, including 4 negative tests (bad code, dropped 2010 game, swapped division table, LV 2020 Elo reset). The full suite passes 48 tests.

## Task Commits

1. **Task 1: Era rules in season_config and check functions** - `ea80a6c` (feat)
2. **Task 2: `fgs check` CLI and integration tests** - `a8f2c6f` (feat)
3. **README: document `fgs check`** - `1d1f308` (docs)

## Files Created/Modified

- `pipeline/src/fgs/season_config.py`: era rules, divisions, exceptions
- `pipeline/src/fgs/checks.py`: check_* functions, CHECKS, run_checks, run_all
- `pipeline/src/fgs/cli.py`: `check` subcommand
- `pipeline/tests/test_checks.py`: real-cache integration and negative tests (skips if no cache)
- `README.md`: added `fgs check` to the run section

## Deviations from Plan

### Auto-fixed Issues

None. The following small additions go beyond the plan:
- The orchestrator note is applied. `test_elo_sanity` uses `>=` for both top-5 and bottom-5, not the strict `>`/`<` in the plan text.
- An extra `test_continuity_detects_reset` negative test, and `run_checks()`, which gives per-check results for the CLI's ok/FAIL lines.
- The README gained one line for the new command, per the repo CLAUDE.md rule on documenting how to run things.
- `test_checks.py` defines a module-scoped `real_cache` override so the module-scoped `real_raw`/`real_derived` fixtures can depend on it. The conftest fixture is function-scoped.

## Issues Encountered

None.

## Known Stubs

None.

## Next Phase Readiness

- Plan 03 can append `("snapshot_grid", ...)` to `checks.CHECKS`, and `fgs check` will pick it up automatically.
- Division and conference lookups are available for phase 2 and phase 4.

## Self-Check: PASSED

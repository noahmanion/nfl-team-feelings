---
phase: 01-data-foundation-elo-core
plan: 03
subsystem: pipeline
tags: [python, polars, snapshots, cli, data-checks, pytest]

requires:
  - phase: 01-01
    provides: "fgs.snapshots.build_grid, fgs.elo.replay, fgs.games.build_team_games, fgs.cli.derive"
  - phase: 01-02
    provides: "fgs.checks CHECKS registry, season_config.n_teams, `fgs check`"
provides:
  - "Tested Phase 2 contract: elo_snapshots.parquet (season, week, franchise_id, elo, wins, losses, ties, win_pct), dense weekly grid"
  - "fgs.checks.check_snapshot_grid, registered as snapshot_grid in CHECKS"
  - "`fgs elo` with optional --season/--week: latest played week by default, data-through header, partial-week note, beyond-latest error"
  - "fgs.cli._latest_played(games, season=None) and _data_through(games, season, week) helpers"
affects: [phase 2 JSON export and mood board (reads elo_snapshots + latest week), phase 3 backtest (as-of grid)]

tech-stack:
  added: []
  patterns:
    - "CLI reads DERIVED_DIR as a module global at call time so tests monkeypatch fgs.cli.DERIVED_DIR to a tmp dir"
    - "Latest week is derived from cached games.parquet (max played week), never from a network call"

key-files:
  created:
    - pipeline/tests/test_snapshots.py
    - pipeline/tests/test_cli.py
  modified:
    - pipeline/src/fgs/checks.py
    - pipeline/src/fgs/cli.py
    - README.md

key-decisions:
  - "build_grid from 01-01 already met every semantic test; snapshots.py left unchanged (no behavior change needed)"
  - "data-through date = max gameday of played games at or before (season, week), including earlier seasons, so week 0 shows the prior season's last game date instead of n/a"
  - "Partial-week note is appended to the header line ('; partial week: P of T games played') rather than printed on its own line"
  - "Seasons outside the data error with 'available seasons: lo-hi'; negative weeks are rejected"

patterns-established:
  - "Synthetic derived data written to tmp_path for CLI tests; real-cache tests skip when the cache is missing"

requirements-completed: [MODEL-02, DATA-04, MODEL-01]

duration: 6min
completed: 2026-11-11
---

# Phase 1 Plan 03: Snapshot Grid Hardening and Honest As-Of CLI Summary

**The weekly Elo grid is pinned by 11 tests plus a `snapshot_grid` data check, and `fgs elo` defaults to the latest played week, prints a "data through" date, flags partial weeks, and refuses weeks that haven't been played.**

## Performance

- **Duration:** about 6 min
- **Completed:** 2026-11-11
- **Tasks:** 3 (2 auto with TDD, 1 human-verify checkpoint auto-approved)
- **Files modified:** 5

## Accomplishments

- `tests/test_snapshots.py` (11 tests). The synthetic tests cover the dense grid, carrying Elo forward over byes, week 0 equal to the regressed prior final, ties counting once for both teams, REG-only records, playoff games that move Elo but not W-L-T, and unplayed games counting for nothing. The real-data tests check a 32×23 grid for 2025 with eliminated teams frozen at their last game, 31 teams in 1999, completed seasons ending at the SB week (21 through 2020, 22 from 2021), and 2026 ending at week 9.
- `check_snapshot_grid` validates row count (n_teams × (last played week + 1)), null Elo, duplicate keys, and that every team has a week-0 row. It runs in `fgs check` and reports ok on real data.
- `fgs elo` now runs with no flags. `fgs build` also prints `latest: 2026 week 9 (data through 2026-11-09)`.
- `tests/test_cli.py` has 9 tests on synthetic data in a tmp dir. The README documents `fgs check` and `fgs elo`, and its status now reads "Phase 1 done".

## Task Commits

1. **Task 1: Lock snapshot grid semantics**: `f895cd3` (test, RED), `4f2346c` (feat, GREEN)
2. **Task 2: Honest as-of CLI**: `ed200aa` (test, RED), `c50a494` (feat, GREEN)
3. **Task 3: Owner plausibility check**: auto-approved, no code changes

## ⚡ Auto-approved checkpoint (Task 3: 2026 ranking plausibility)

The orchestrator ran this in auto mode with the checkpoint pre-approved, so the executor did the check instead of the owner.

`uv run fgs elo` (2026 week 9, data through 2026-11-09):

```
  1  BUF    1697  7-1-0      17  NYG    1486  5-2-1
  2  DEN    1647  7-2-0      18  BAL    1477  4-5-0
  3  JAX    1645  6-2-0      19  DAL    1467  4-5-0
  4  SEA    1637  5-4-0      20  ATL    1445  3-6-0
  5  SF     1635  7-1-0      21  CLE    1443  5-4-0
  6  CHI    1629  7-2-0      22  WAS    1429  2-5-1
  7  LA     1604  5-4-0      23  CAR    1427  3-5-0
  8  DET    1595  6-2-0      24  NO     1420  3-5-0
  9  MIN    1590  6-2-0      25  LV     1409  4-5-0
 10  CIN    1590  6-2-0      26  PHI    1398  2-7-0
 11  GB     1580  6-3-0      27  ARI    1391  3-6-0
 12  PIT    1576  6-2-0      28  IND    1389  2-7-0
 13  NE     1566  5-4-0      29  LAC    1374  0-8-0
 14  KC     1565  6-2-0      30  MIA    1367  1-7-0
 15  HOU    1541  3-5-0      31  NYJ    1336  2-7-0
 16  TB     1494  3-6-0      32  TEN    1309  1-7-0
```

The two columns are rearranged for readability. The values are exactly what the command printed.

**Judgment: plausible, approved.**
- Top 5 all have winning records, and BUF at 7-1 is #1 as the research prototype predicted. SEA at 5-4 is the weakest of them, which reflects strong carryover from 2025.
- Bottom 5 all have losing records (LAC 0-8, MIA 1-7, NYJ 2-7, TEN 1-7, IND 2-7). TEN, NYJ, MIA and LAC match the research prototype's bottom group.
- Mild oddities, all explained by Elo's carryover and margin weighting and not bugs:
  - HOU is 15th at 3-5 (1541, carried over from 2025 strength).
  - NYG is 17th at 5-2-1 (started 2026 low).
  - CLE is 21st at 5-4.
  - These are exactly the "fans should feel differently" gaps the later momentum factors are meant to address.
- 2007 week 21: NE is #1 at 1824 (16-0 REG) despite the SB loss. NYG climbed from 1534 (12th, week 17) to 1627 (5th) through its playoff run.
- Franchise continuity: 2019 final LV (OAK) 1403, then 2020 week 0 LV 1437 = 1505/3 + 2/3 × 1403 exactly, then 2020 week 1 LV 1454 at 1-0. It appears as LV with no OAK row.
- `uv run fgs check`: all 11 checks ok, including `snapshot_grid`.

## Files Created/Modified

- `pipeline/tests/test_snapshots.py`: synthetic and real grid-semantics tests, plus the check_snapshot_grid test
- `pipeline/tests/test_cli.py`: as-of CLI tests on synthetic derived data in tmp_path
- `pipeline/src/fgs/checks.py`: check_snapshot_grid, and a snapshot_grid entry in CHECKS
- `pipeline/src/fgs/cli.py`: optional --season/--week, _latest_played, _data_through, partial-week note, range/beyond-latest errors, build prints the latest week
- `README.md`: pipeline commands (build/check/elo/as-of), semantics notes, status "Phase 1 done"

## Decisions Made

See key-decisions in the frontmatter. The most notable one is that snapshots.py needed no changes: the 01-01 grid already met every semantic the plan pins down.

## Deviations from Plan

**1. snapshots.py was not modified.** The plan listed it in files_modified "where tests fail". All semantic tests passed against the existing build_grid, so the only RED test in Task 1 was the check_snapshot_grid one, and the TDD RED commit is for that test.

There were no other deviations; the plan ran as written.

## TDD Gate Compliance

- Task 1: `test(01-03)` f895cd3, then `feat(01-03)` 4f2346c
- Task 2: `test(01-03)` ed200aa, then `feat(01-03)` c50a494
- No refactor commits were needed.

## Issues Encountered

None.

## Known Stubs

None.

## Next Phase Readiness

- Phase 1 is complete. Phase 2 can read `data/derived/elo_snapshots.parquet` (fixed column contract) and use `fgs.cli._latest_played` / `_data_through` for the "current week" label.
- Full verification: `uv run fgs build && uv run fgs check && uv run pytest -q` → 68 passed, all checks ok.

## Self-Check: PASSED

- FOUND: pipeline/tests/test_snapshots.py, pipeline/tests/test_cli.py, pipeline/src/fgs/checks.py, pipeline/src/fgs/cli.py, README.md
- FOUND commits: f895cd3, 4f2346c, ed200aa, c50a494

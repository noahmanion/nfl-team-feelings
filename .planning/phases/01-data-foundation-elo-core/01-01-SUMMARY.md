---
phase: 01-data-foundation-elo-core
plan: 01
subsystem: pipeline
tags: [python, uv, nflreadpy, polars, numpy, elo, argparse, pytest]

requires: []
provides:
  - "pipeline/ uv project with `fgs` console script (ingest, build, elo)"
  - "Own parquet cache data/cache/schedules.parquet (all 1999-2026 games)"
  - "Derived games.parquet, team_games.parquet, elo_snapshots.parquet in data/derived/"
  - "538-style Elo replay (fgs.elo) and (season, week, franchise) snapshot grid (fgs.snapshots)"
  - "fgs.cli.derive(raw) pure pipeline entry point for plan 02's `fgs check`"
affects: [01-02 data checks, 01-03 snapshot/CLI hardening, phase 2 JSON export, phase 3 backtest baselines]

tech-stack:
  added: [nflreadpy==0.1.5, polars 2.1, numpy 2.5, pytest 9.2]
  patterns:
    - "Raw frame cached untouched; legacy codes mapped (RAW_TO_FRANCHISE) in build_games before anything else"
    - "Elo replay: NumPy ratings array, eager season regression, sparse emit + Polars forward-fill grid"
    - "Grid ends at the last *played* week per season (latest week derived from data, not get_current_week)"

key-files:
  created:
    - pipeline/pyproject.toml
    - pipeline/uv.lock
    - pipeline/.gitignore
    - pipeline/src/fgs/paths.py
    - pipeline/src/fgs/franchises.py
    - pipeline/src/fgs/season_config.py
    - pipeline/src/fgs/ingest.py
    - pipeline/src/fgs/games.py
    - pipeline/src/fgs/elo.py
    - pipeline/src/fgs/snapshots.py
    - pipeline/src/fgs/cli.py
    - pipeline/tests/conftest.py
    - pipeline/tests/test_e2e.py
    - pipeline/tests/test_elo.py
    - pipeline/tests/test_franchises.py
    - pipeline/tests/test_ingest.py
  modified:
    - README.md

key-decisions:
  - "Era HFA 65/58/30/45 (market-implied, outcome-free) stored in fgs.season_config.hfa_for"
  - "Snapshot grid ends at last played week per season, so 2026 has weeks 0-9 now (19,422 rows vs 19,710 in the prototype, which used the last scheduled week)"
  - "e2e test derives the latest played (season, week) from the cached schedules instead of hardcoding week 9"
  - "build_games fills any missing optional columns (div_game, spread_line, QB ids) with nulls so the games schema stays stable for slim inputs"

patterns-established:
  - "Pure derive(raw) -> dict of frames, with I/O isolated in build_all and load_schedules"
  - "conftest.make_games(rows) helper builds post-normalization frames from compact tuples"

requirements-completed: [DATA-01, DATA-02, DATA-04, MODEL-01, MODEL-02]

duration: 12min
completed: 2026-11-11
---

# Phase 1 Plan 01: Elo Walking Skeleton Summary

**One command (`uv run fgs build`) caches all 7,548 nflverse games from 1999 to 2026, maps OAK/SD/STL to LV/LAC/LA, replays a 538-matching Elo (K=20, MOV multiplier with HFA inside, era HFA, 1/3 regression, CLE/HOU seeded at 1300), and `fgs elo` prints any week's ranked table. The 2026 week 9 output (BUF 1697, DEN 1647) matches the research prototype exactly.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-11-11T17:53Z
- **Completed:** 2026-11-11T18:05Z
- **Tasks:** 3/3
- **Files modified:** 17 (16 created, 1 modified)

## Accomplishments

- `pipeline/` uv project (Python 3.13) with `fgs ingest [--refresh] [--all]`, `fgs build [--refresh]`, `fgs elo --season S --week W [--top N]`.
- A second build with `nflreadpy` import blocked succeeds, which shows that re-runs read only the cache.
- Derived tables: games (7,548 rows, with elo_pre/post and p_home on played games, null on the 136 unplayed 2026 games), team_games (15,096), elo_snapshots (19,422, zero null Elo, 31 teams in 1999-2001 and 32 from 2002).
- Max per-game zero-sum drift on real data is 2.3e-13. Only the 32 canonical codes appear in the derived tables.
- 32 passing tests: 2 e2e on real data, 20 Elo/grid unit tests, 8 franchise tests, 2 ingest/cache tests (counts include parametrized cases).

## Task Commits

1. **Task 1: Scaffold uv project and failing e2e test** - `d298262` (test)
2. **Task 2: Thinnest real slice ingest to `fgs elo`** - `b928f56` (feat)
3. **Task 3: Pin Elo math, franchise map, cache behavior; README** - `12c1bb1` (test)

## Files Created/Modified

- `pipeline/src/fgs/elo.py`: EloParams, win_prob, mov_mult, update, replay
- `pipeline/src/fgs/snapshots.py`: build_grid with forward-filled Elo and REG-only W-L-T
- `pipeline/src/fgs/games.py`: build_games, build_team_games
- `pipeline/src/fgs/cli.py`: argparse CLI, derive, build_all
- `pipeline/src/fgs/{ingest,franchises,season_config,paths}.py`: cache, identity, constants, locations
- `pipeline/tests/*`: e2e plus unit tests
- `README.md`: Pipeline run section and status

## Decisions Made

See key-decisions in the frontmatter. The orchestrator note is addressed: `test_e2e` reads the cached schedules, takes the max season with played games and that season's max played week, skips if there are none, and asserts 32 ranked rows (ranks 1..32, all canonical codes).

## Deviations from Plan

### Auto-fixed Issues

None. The plan was executed as written, with the e2e week derived from data per the orchestrator note. The extra tests (min-margin, playoff Elo vs REG record, bye forward-fill, legacy-code mapping, loader error propagation) go beyond the plan without changing behavior.

## TDD Gate Compliance

Task 3 is `tdd="true"`, but the plan puts the implementation in Task 2, before the pinning tests. The Task 3 tests therefore passed on the first run, and no `elo.py` change was needed. The RED gate for the plan as a whole is commit `d298262` (the e2e test failed with a missing `fgs.cli`), and GREEN is `b928f56`. No separate RED commit exists for the Task 3 unit tests.

## Issues Encountered

None.

## Known Stubs

None. `season_config` deliberately holds only HFA, seeds and the mean. Plan 02 adds team counts and divisions.

## Next Phase Readiness

- Plan 02 can import `fgs.cli.derive` and build `fgs check` on the games/team_games/snapshot frames.
- Plan 03: `fgs elo` currently rejects an out-of-range week with a generic "no snapshot" message and exit 1. The "data through" header and a clearer beyond-latest-week message are left for plan 03.

## Self-Check: PASSED

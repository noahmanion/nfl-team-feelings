---
phase: 01-data-foundation-elo-core
fixed_at: 2026-11-11T18:30:00Z
review_path: .planning/phases/01-data-foundation-elo-core/01-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 0
status: all_fixed
---

# Phase 1: Code Review Fix Report

**Fixed at:** 2026-11-11
**Source review:** .planning/phases/01-data-foundation-elo-core/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 9 (WR-01..WR-06, IN-01, IN-03, IN-04)
- Fixed: 9
- Skipped: 0
- Out of scope (not attempted): IN-02 (`run_all` unused; kept, now threads params), IN-05 (`is_home` at neutral sites)

**Verification:** `uv run fgs build`, `uv run fgs check` (12 checks, all ok), `uv run pytest -q` (74 passed).
On the real cache, derived `elo_snapshots` are byte-for-byte equal to the pre-fix build, and `games` matches
apart from the new `asof_week` column (`asof_week == week` for every 1999-2026 game).

## Fixed Issues

### WR-01: `HFA_BY_ERA` is dead; `hfa_for` hardcodes the same numbers separately

**Files modified:** `pipeline/src/fgs/season_config.py`
**Commit:** 4756876
**Applied fix:** `hfa_for` now looks the season up in `HFA_BY_ERA` at call time and raises `KeyError` if no era matches.

### WR-02: Replay and snapshots order games by the week label, not the date played

**Files modified:** `pipeline/src/fgs/elo.py`, `pipeline/src/fgs/games.py`, `pipeline/src/fgs/snapshots.py`, `pipeline/src/fgs/checks.py`, `pipeline/tests/test_elo.py`, `pipeline/tests/test_checks.py`
**Commit:** 2f3e538
**Status:** fixed: requires human verification (logic change)
**Applied fix:** Took both options, so snapshots stay as-of correct and any inversion is still flagged:
- `replay` sorts by `(season, gameday, gametime, week, game_id)`. It adds `asof_week = cum_max(week) over season` in date order, which is the highest week label reached when the game was played. Sparse Elo rows are keyed by `asof_week`, so a postponed game lands in the week it was actually played.
- `team_games` carries `asof_week`. `build_grid` keys REG records and `wmax` by it, so W-L-T agrees with Elo. `check_snapshot_grid` uses it for `wmax`.
- A new `week_date_order` check (in `CHECKS`, so `fgs check` runs it) fails on any played game dated before a played game from an earlier-labelled week in the same season.
- New synthetic test: a week-1 game moved after week 2 does not appear in the week-1 snapshot (Elo or record), and the check fires for it. New real-data test: the check passes on the cache.

### WR-03: Seasons with no played games are dropped from `elo_snapshots`

**Files modified:** `pipeline/src/fgs/snapshots.py`, `pipeline/src/fgs/checks.py`, `pipeline/tests/test_snapshots.py`
**Commit:** 6f8864c
**Applied fix:** The grid left-joins `wmax` and fills nulls with 0, so a scheduled season with no results yet emits regressed week-0 rows. `check_snapshot_grid` now expects `n_teams x 1` rows for such seasons, flags snapshot seasons that are missing from `games`, and checks week-0 presence for every scheduled season. Added a synthetic test covering an unplayed future season.

### WR-04: Checks hardcode the regression fraction and mean instead of reading `EloParams`

**Files modified:** `pipeline/src/fgs/checks.py`, `pipeline/src/fgs/cli.py`, `pipeline/tests/test_checks.py`
**Commit:** 748aad3
**Applied fix:**
- `check_continuity` and `check_league_mean` take `params: EloParams | None`. Continuity's expected value is `mean*revert + (1-revert)*prev_final`.
- `derive(raw, params=None)` and `run_checks`/`run_all(raw, derived, params=None)` accept params. `CHECKS` lambdas take `(raw, d, p)`.
- `fgs check` builds one `EloParams()` and passes it to both `derive` and `run_checks`.
- New test: with `revert=0.25`, continuity passes given the params and fails without them.
- Note: `MEAN_CHECK_FROM=2012` is still tuned for revert=1/3. A slower revert leaves the CLE/HOU seed deficits above `MEAN_TOL` in 2012, so that cutoff may need revisiting during Phase 3 tuning.

### WR-05: Real-data tests depend on the date and will start failing on their own

**Files modified:** `pipeline/tests/test_snapshots.py`, `pipeline/tests/test_checks.py`
**Commit:** 42c7114
**Applied fix:**
- The current season is now the latest season with results. The `cur == 2026 / latest < 18` assertion became "if the season has unplayed games, latest < max scheduled week". Any later season that has a schedule but no results must be week-0 only.
- The final-week check covers seasons before the latest one with results.
- The continuity range uses `games["season"].max()`.
- `test_elo_sanity` uses the final REG week (`reg_weeks(s)`) of the latest season whose Super Bowl has been played.

### WR-06: `test_e2e` rebuilds into the real `data/derived` and can hit the network

**Files modified:** `pipeline/tests/test_e2e.py`
**Commit:** f41714f
**Applied fix:** The `built` fixture skips when `data/cache/schedules.parquet` is missing. It also monkeypatches `fgs.cli.DERIVED_DIR` to a `tmp_path_factory` dir, undone in `finally`. Verified that `data/derived/*.parquet` mtimes are unchanged after a full pytest run.

### IN-01: `--top` accepts zero or negative values

**Files modified:** `pipeline/src/fgs/cli.py`, `pipeline/tests/test_cli.py`
**Commit:** b5fa032
**Applied fix:** `fgs elo` exits 1 with `--top must be >= 1` when `--top < 1`. Added a parametrized test for 0 and -3.

### IN-03: `CHECKS` is annotated with the builtin `callable`

**Files modified:** `pipeline/src/fgs/checks.py`
**Commit:** d61a283
**Applied fix:** Added `CheckFn = Callable[[pl.DataFrame, dict[str, pl.DataFrame], EloParams], list[str]]` and annotated `CHECKS: list[tuple[str, CheckFn]]`.

### IN-04: Shared default `EloParams()` instance holds a mutable `seeds` dict

**Files modified:** `pipeline/src/fgs/elo.py`, `pipeline/src/fgs/cli.py`
**Commit:** 8ea4d92
**Applied fix:** `replay(params: EloParams | None = None)` builds a fresh `EloParams()` per call. `derive` passes `params` straight through.

---

_Fixed: 2026-11-11_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

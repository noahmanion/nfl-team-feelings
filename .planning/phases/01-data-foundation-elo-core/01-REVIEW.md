---
phase: 01-data-foundation-elo-core
reviewed: 2026-11-11T00:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - pipeline/src/fgs/checks.py
  - pipeline/src/fgs/cli.py
  - pipeline/src/fgs/elo.py
  - pipeline/src/fgs/franchises.py
  - pipeline/src/fgs/games.py
  - pipeline/src/fgs/ingest.py
  - pipeline/src/fgs/paths.py
  - pipeline/src/fgs/season_config.py
  - pipeline/src/fgs/snapshots.py
  - pipeline/tests/conftest.py
  - pipeline/tests/test_checks.py
  - pipeline/tests/test_cli.py
  - pipeline/tests/test_e2e.py
  - pipeline/tests/test_elo.py
  - pipeline/tests/test_franchises.py
  - pipeline/tests/test_ingest.py
  - pipeline/tests/test_snapshots.py
findings:
  critical: 0
  warning: 6
  info: 5
  total: 11
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-11-11
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Review focus: Elo math, future-data leakage into as-of snapshots, franchise mapping, and week off-by-ones.

**Checked and correct:**
- **Elo math** matches 538's `forecast.py` line for line:
  - win probability, MOV multiplier (HFA included in `elo_diff`, winner-view sign, tie denominator 1.0), K=20
  - 1/3 regression toward 1505, applied to every team at season start (equivalent to 538's per-team lazy revert)
  - zero-sum shifts and neutral-site HFA of 0
- **Franchise mapping** (OAK→LV, SD→LAC, STL→LA) is correct. The 1999–2001 division table also matches history (SEA in AFC West, ATL/CAR/STL/NO/SF in NFC West).
- **Era rules** (`n_teams`, `reg_games`, `reg_weeks`, `playoff_teams`) are correct.
- **Snapshot construction** has no off-by-one:
  - weeks run 0..wmax inclusive
  - the per-(season, week, team) `last()` respects processing order
  - forward-fill runs after an explicit sort
  - REG-only cumulative records are ordered by week inside each window

**Leakage check against the cached data:** no week's latest `gameday` is later than the next week's earliest `gameday`, and no team-season has a game out of date order. So the cached history has no actual leakage today.

**What remains:**
- One latent leakage path: ordering uses the week label, not the game date (WR-02).
- A gap where preseason week-0 ratings are dropped (WR-03).
- A duplicated HFA table that does nothing when edited (WR-01).
- Hard-coded regression constants in the checks (WR-04).
- Several tests that depend on the date or on the real data directory (WR-05, WR-06).

## Warnings

### WR-01: `HFA_BY_ERA` is dead; `hfa_for` hardcodes the same numbers separately

**File:** `pipeline/src/fgs/season_config.py:18-33`
**Issue:** `HFA_BY_ERA` is declared as the era table, and the comment says "Phase 3 may tune them". Nothing reads it, though. `hfa_for()` returns its own hardcoded literals. Anyone who tunes the table in Phase 3 will see no change in ratings, and nothing will report the mismatch.
**Fix:** Derive one from the other:
```python
def hfa_for(season: int) -> float:
    for lo, hi, hfa in HFA_BY_ERA:
        if lo <= season <= hi:
            return hfa
    raise KeyError(f"no HFA era for {season}")
```

### WR-02: Replay and snapshots order games by the week label, not the date played (latent as-of leakage)

**File:** `pipeline/src/fgs/elo.py:59,97-98`, `pipeline/src/fgs/games.py:13`
**Issue:** `replay` sorts by `season, week, gameday, ...` and writes each post-game rating into the sparse table under the game's labeled `week`. A postponed game keeps its original week label in nflverse. Examples are the COVID-era reschedules, weather moves, and the kind of in-season postponement that could still happen in 2026. Such a game is played after games from later weeks, but replay applies it *before* them, and its result lands in the earlier week's snapshot. Three consequences:
1. The "Elo as of week w" snapshot contains a result that did not exist at that time. This is leakage into the backtest features Phase 2/3 will build on.
2. Later-week games for the teams involved use pre-game ratings that already include a game played afterwards.
3. For the current season, an unplayed earlier-week game that later gets a result silently rewrites already published snapshots for weeks w..now.

The cached 1999–2026 data has no such inversion (verified: 0 weeks where `max(gameday)` exceeds the next week's `min(gameday)`), so this is latent. Nothing guards against it, though, and `check` does not detect it.
**Fix:** At minimum, add a check that fails when the week order and date order disagree:
```python
def check_week_date_order(games):
    w = (games.filter(pl.col("played")).group_by("season", "week")
         .agg(pl.col("gameday").min().alias("lo"), pl.col("gameday").max().alias("hi"))
         .sort("season", "week")
         .with_columns(pl.col("lo").shift(-1).over("season").alias("next_lo")))
    return [f"{s} wk{wk}: game on {hi} after wk{wk+1} starts {nlo}"
            for s, wk, lo, hi, nlo in w.filter(pl.col("hi") > pl.col("next_lo")).iter_rows()]
```
If it ever fires, sort by `gameday, gametime` first and assign each game an "effective week" from its date for the sparse/snapshot key.

### WR-03: Seasons with no played games are dropped from `elo_snapshots`, so preseason ratings never reach the output

**File:** `pipeline/src/fgs/snapshots.py:11-23`
**Issue:** `wmax` only covers seasons that have played games, and `teams.join(wmax, on="season")` is an inner join. Once nflverse publishes next season's schedule (each May), `replay` computes and emits that season's regressed week-0 ratings, but the snapshot grid throws them away. Effects:
- `fgs elo --season 2027` passes the range check and then fails with "no snapshot for 2027 week 0".
- `check_continuity` and `check_snapshot_grid` never validate that season's regression.
- The project's main deliverable ("how should fans feel right now") has nothing to show for the offseason or preseason.

**Fix:**
```python
grid = (
    teams.join(wmax, on="season", how="left")
    .with_columns(pl.col("wmax").fill_null(0))
    ...
)
```
Then update `check_snapshot_grid` so a season with snapshots but no played games expects `n_teams * 1` rows, instead of reporting "snapshots present but no played games".

### WR-04: Checks hardcode the regression fraction and mean instead of reading `EloParams`

**File:** `pipeline/src/fgs/checks.py:121`, `pipeline/src/fgs/checks.py:189-195`
**Issue:** `check_continuity` recomputes the expected week-0 value as `MEAN_ELO / 3 + 2/3 * prev_final`, and `check_league_mean` assumes `MEAN_ELO`. The stack plan says Optuna will tune `revert`, and `EloParams` is the place it would be tuned. With any non-default `revert`, `continuity` fails for every team-season. Worse, a bug in how `replay` applies `params.revert` could be hidden if the check is "fixed" by hand.
**Fix:** Pass the params in. For example, have `check_continuity(games, snapshots, params: EloParams = EloParams())` use `params.mean * params.revert + (1 - params.revert) * prev_final`, and have `derive()` return the params it used so `run_checks` can thread them through.

### WR-05: Real-data tests depend on the date and will start failing on their own

**File:** `pipeline/tests/test_snapshots.py:152-153`, `pipeline/tests/test_checks.py:77`, `pipeline/tests/test_checks.py:101-115`
**Issue:**
- `if cur == 2026: assert latest < 18` fails once 2026 week 18 is played (January 2027). The suite then goes red with no code change.
- `set(range(1999, 2027)) <= seasons` needs 2026 week-0 rows in the snapshots. Because of WR-03, that only holds if the cache was pulled after the 2026 kickoff. A cache from before September, or a later re-pull that adds 2027 with no games played, behaves differently.
- `test_elo_sanity` asserts that each top-5 Elo team has `wins >= losses` at the latest week. Early in a season, a strong team that is 0-1 or 1-2 still sits in the top 5 and fails the test. The model is not wrong in that case; the test is.

**Fix:**
- Compare against `games["season"].max()` or reg-week constants (`season_config.reg_weeks(cur) + 1`) rather than the literal 2026/2027.
- Limit `test_elo_sanity` to a completed season's final REG week, e.g. `max_season - 1` at `reg_weeks(s)`.

### WR-06: `test_e2e` rebuilds into the real `data/derived` and can hit the network

**File:** `pipeline/tests/test_e2e.py:19-24`
**Issue:** The `built` fixture calls `main(["build"])` with no cache guard and no path patching. When `data/cache/schedules.parquet` is missing, it downloads from nflverse. It always overwrites the real `data/derived/*.parquet`. Every other real-data test skips when the cache is absent; this one doesn't. Running `pytest` therefore silently replaces whatever derived data the user had built.
**Fix:** Skip when the cache is missing, and point `DERIVED_DIR` at `tmp_path`:
```python
@pytest.fixture(scope="module")
def built(tmp_path_factory):
    if not (CACHE_DIR / "schedules.parquet").exists():
        pytest.skip("no cached schedules")
    import fgs.cli as cli
    mp = pytest.MonkeyPatch(); mp.setattr(cli, "DERIVED_DIR", tmp_path_factory.mktemp("derived"))
    assert cli.main(["build"]) == 0
    yield cli.main
    mp.undo()
```

## Info

### IN-01: `--top` accepts zero or negative values

**File:** `pipeline/src/fgs/cli.py:108-109`
**Issue:** `rows.head(-3)` in Polars returns every row *except* the last 3, so `--top -3` prints 29 teams. `--top 0` prints a header and no rows.
**Fix:** Reject `args.top < 1` the same way `week < 0` is rejected.

### IN-02: `run_all` is unused

**File:** `pipeline/src/fgs/checks.py:252-253`
**Issue:** Nothing in `src/` or `tests/` calls `run_all`, because the CLI uses `run_checks`. It is dead code that can drift.
**Fix:** Delete it, or use it in tests.

### IN-03: `CHECKS` is annotated with the builtin `callable`

**File:** `pipeline/src/fgs/checks.py:233`
**Issue:** `list[tuple[str, callable]]` uses the builtin function `callable` as a type, which type checkers reject.
**Fix:** `list[tuple[str, Callable[[pl.DataFrame, dict[str, pl.DataFrame]], list[str]]]]`.

### IN-04: Shared default `EloParams()` instance holds a mutable `seeds` dict

**File:** `pipeline/src/fgs/elo.py:51`
**Issue:** `params: EloParams = EloParams()` is evaluated once. The dataclass is frozen, but `seeds` is a plain dict shared by every default call. If anyone mutates `params.seeds` (likely during tuning experiments), every later `replay()` changes.
**Fix:** Use `params: EloParams | None = None` and create the instance inside, or store seeds as a `MappingProxyType` or frozen tuple.

### IN-05: `team_games.is_home` is True for the designated home team at neutral sites

**File:** `pipeline/src/fgs/games.py:57`
**Issue:** For 103 neutral games (all Super Bowls plus international games), the nominal home team gets `is_home=True`. The `neutral` column is carried alongside, but any later home/away split (Phase 2 factors) that filters on `is_home` alone will count these as home games.
**Fix:** Add an `at_home = is_home & ~neutral` column, or document that consumers must check `neutral` too.

---

_Reviewed: 2026-11-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---
phase: 05-efficiency-qb-trend-season-simulator
reviewed: 2026-11-11T00:00:00Z
depth: standard
files_reviewed: 28
files_reviewed_list:
  - pipeline/src/fgs/backtest.py
  - pipeline/src/fgs/checks.py
  - pipeline/src/fgs/cli.py
  - pipeline/src/fgs/efficiency.py
  - pipeline/src/fgs/expectation.py
  - pipeline/src/fgs/explain.py
  - pipeline/src/fgs/export.py
  - pipeline/src/fgs/features.py
  - pipeline/src/fgs/pbp.py
  - pipeline/src/fgs/score.py
  - pipeline/src/fgs/sim.py
  - pipeline/tests/conftest.py
  - pipeline/tests/test_backtest.py
  - pipeline/tests/test_checks.py
  - pipeline/tests/test_cli.py
  - pipeline/tests/test_efficiency.py
  - pipeline/tests/test_expectation.py
  - pipeline/tests/test_explain.py
  - pipeline/tests/test_export.py
  - pipeline/tests/test_features.py
  - pipeline/tests/test_leakage.py
  - pipeline/tests/test_pbp.py
  - pipeline/tests/test_sim.py
  - pipeline/tests/test_snapshots.py
  - web/src/components/TeamPage.svelte
  - web/src/lib/team.test.ts
  - web/src/lib/team.ts
  - web/src/lib/types.ts
findings:
  critical: 1
  warning: 8
  info: 5
  total: 14
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-11-11
**Depth:** standard
**Files Reviewed:** 28
**Status:** issues_found

## Narrative Findings (AI reviewer)

## Summary

Scope: `git diff 5cd28fb~1 -- pipeline/src pipeline/tests web/src`. I focused on as-of correctness in the pbp, efficiency and simulator code, cache keying, the A5 display override, expectation tagging, and refresh atomicity.

The core as-of logic holds up.
- **Opponent adjustment.** The opponent prior uses `ewm_mean().shift(1).over(franchise)`, so it only sees games strictly before the current one.
- **Snapshot join.** The join is `join_asof` on `season*100 + asof_week` with the backward strategy. epa_traj resets per season through the `g_season` guard.
- **Simulator inputs.** The simulator only uses results with `played & asof_week <= week`, and the backtest seals pbp, sim and Vegas inputs to `season <= last`.
- **vs_exp and po_trend.** Both match CONTEXT.
- **Sum invariants.** These hold by construction. The 2022 BUF–CIN cancelled game is not in `games`, so `_reg_done` is not blocked.

The main defects:
- **CR-01, live A5 override.** The override marks playoff bye teams as 0% during the wildcard window.
- **Refresh robustness.** A pbp feed that lags the schedule blocks the whole refresh (WR-02), and refresh writes several files with no all-or-nothing guarantee (WR-03).
- **Silent degradations.** Missing Vegas data (WR-04) and missing sim rows (WR-08) change scores without any error.
- **Cache keys.** Two inputs to the result are missing from the cache keys (WR-05, WR-06).
- **Separator spacing.** The orchestrator saw the collapsed separator in the browser (WR-01).

## Critical Issues

### CR-01: A5 override shows playoff bye teams as "Playoff odds 0%" until their divisional game is scheduled

**File:** `pipeline/src/fgs/export.py:64-99` (`_playoff_display`)
**Issue:** The override turns on as soon as every REG game is played and *any* non-REG game row exists. It then sets `_in_post` = "appears in some non-REG game row this season" and gives everyone else 0.

nflverse adds playoff games round by round, once each matchup is known. Right after week 18 the schedule only has wildcard games. The #1 seeds have a bye: one per conference since 2020, two per conference before that. They are in no non-REG row yet, so `done` is true and `_in_post` is false. The best team in each conference therefore displays **"Playoff odds 0%"** for the entire wildcard week, which is the most-viewed week of the year.

Completed seasons hide the bug: byes always appear in a divisional game, which is why the 1999–2025 spot-check passed. The live season will hit it every January.
**Fix:** Override only when the post-season field is fully known. Otherwise mark the known post-season teams as 100 and keep the raw sim value for the rest:
```python
n_post = post_teams.group_by("season").len().rename({"len": "_n_post"})
spots = pl.col("season").map_elements(season_config.playoff_teams, return_dtype=pl.Int64)
field_known = pl.col("_n_post").fill_null(0) >= spots
reg_done = pl.col("_reg_done").fill_null(False) & (pl.col("week") >= pl.col("_reg_end"))
in_post = pl.col("_in_post").fill_null(False)
display = (
    pl.when(reg_done & in_post).then(100)
    .when(reg_done & field_known).then(0)
    .otherwise(raw)
)
```
Add a unit test with a synthetic season that has wildcard rows only. The bye team must not show 0.

## Warnings

### WR-01: Team page odds/QB line renders "Playoff odds 0%·QB C.Ward" with collapsed separator (orchestrator browser observation)

**File:** `web/src/components/TeamPage.svelte:121-125` (CSS at 209-212)
**Issue:** In the browser, the orchestrator saw the new third `.sub` line render with no space around the dot. This is the same bug class as Phase 4 WR-05.

The markup packs `{#if}` blocks and `<span class="sep">` onto one line, so the separator's spacing depends entirely on the scoped `.sep { margin-inline }` rule reaching the conditionally rendered span. The current `dist/` bundle does tag that span `svelte-1dw8avi` and does include the margin rule, so a stale dev server or HMR may explain part of what was observed. But this is the second time the same visual bug has shipped. The `.sep` rule is a component-local class that has to be applied correctly at every call site, and nothing tests it.
**Fix:** Pull the separator into one shared component and use it on all three header lines and anywhere else a dot separator appears:
```svelte
<!-- web/src/components/Sep.svelte -->
<span class="sep" aria-hidden="true">·</span>
<style>.sep { margin-inline: var(--space-xs); }</style>
```
Then render `{#if odds}<span>{odds}</span>{/if}{#if odds && qb}<Sep />{/if}{#if qb}<span>{qb}</span>{/if}`. Rebuild, and check the page at 375px and 1280px that it reads "Playoff odds 0% · QB C.Ward". You could also use a CSS `gap` on `.sub` (`display: inline-flex; gap: var(--space-xs)`), which keeps the spacing independent of whitespace and per-element classes.

### WR-02: pbp lagging the schedule makes `fgs refresh` fail outright

**File:** `pipeline/src/fgs/checks.py:311-312`, `pipeline/src/fgs/pbp.py:135-150`, `pipeline/src/fgs/cli.py:248-266`
**Issue:**
- **The check blocks refresh.** `pbp_coverage` is a hard-failing check, and `check_pbp` reports every played game without pbp, minus the three hard-coded 1999–2000 ids. nflverse posts schedule results (`games.csv`) hours before the pbp release is rebuilt. Refreshing on Sunday night or Monday morning therefore returns `checks failed; cache and JSON not updated`. None of the scores, records or Elo update, even though `efficiency.per_game` is designed to tolerate a missing game (inner join, "absent from the sequence, not 0").
- **The download can crash.** When the current season's pbp file doesn't exist yet (the first game of a new season), `load_pbp_season(current, refresh=True)` raises an exception that nothing catches.

**Fix:** Make pbp coverage a soft warning for the current season's latest week(s). For example, `check_pbp` could take `(season, week)` from `latest_played` and only fail on gaps before the latest played week. Alternatively, return the gaps as a separate "warn" list that `_report` prints without setting `failed`. Wrap the current-season download so that a missing release falls back to the cached frame (or an empty one) with a printed warning.

### WR-03: Refresh writes are atomic per file, not as a set

**File:** `pipeline/src/fgs/cli.py:269-275`; `pipeline/src/fgs/cli.py:118-121` (`build_all`)
**Issue:** After the checks pass, refresh writes the files in sequence:
1. schedules
2. teams
3. N pbp seasons
4. derived parquet (games, team_games, snapshots, features, team_game_epa)
5. the sim cache
6. the web JSON

A crash or Ctrl-C partway through leaves the schedules cache newer than the pbp cache, sim cache or exported JSON. The next `fgs export` (cache-only, no checks) then publishes a mix of inputs. Separately, `build_all(refresh=True)` writes the re-downloaded current-season pbp straight to the cache through `load_all_pbp(..., write_cache=True)` before any check runs. That contradicts the stated "check-then-write" invariant.
**Fix:** Stage every output into a temp sibling directory, then `os.replace` them in dependency order with the web export last. Or write a `refresh.complete` marker last and have `fgs export`/`check` refuse to run, or warn, when the marker is older than `schedules.parquet`. In `build_all`, pass `write_cache=False` and save after `_checked_derive` passes, or document that `build --refresh` is unchecked.

### WR-04: Missing win_totals.csv silently switches 2003–2020 expectations to model-sourced

**File:** `pipeline/src/fgs/cli.py:94-97, 100-107, 260`
**Issue:** `_cached_vegas` returns `None` when `CACHE_DIR/win_totals.csv` is absent. `check`, `export`, `backtest` and `refresh` all run on that `None`, so every `expectation_source` becomes `model` and `vs_exp` changes for all 2003–2020 rows. vs_exp carries one of the largest weights (−1.23), so the scores change too. `backtest` then fits the deployment-condition weights shown in 05-04 (−0.0012 ΔSpearman) without saying so. Nothing prints a warning, and no check compares the source mix.
**Fix:** When the CSV is missing, print a loud warning. Better, add a check that fails if no `vegas` rows exist for 2003–2020 while the season range covers those years. Have `refresh` fall back to `load_win_totals()` (it's a frozen file) instead of silently going without.

### WR-05: `input_digest` omits the columns that set the game order, which decides the RNG-to-game mapping

**File:** `pipeline/src/fgs/sim.py:50-52, 104, 196-204`
**Issue:** `simulate_season` sorts games by `gameday, gametime, game_id`, then assigns column `k` of `u = rng.random((n_sims, n_rem))` to the k-th remaining game in that order. `input_digest` hashes the games sorted by `game_id` only, with no `gameday` or `gametime`. When nflverse updates a kickoff (flex scheduling, a moved game) and no result changes, the digest matches. The cached probabilities are reused, but a cold rebuild with the same data would produce different numbers. That breaks the "results do not depend on computation order or on incremental runs" claim in the module docstring, and makes leakage and snapshot tests depend on cache state.
**Fix:** Either hash exactly what the simulator reads:
```python
cols = ["game_id", "home_id", "away_id", "result", "played", "asof_week", "neutral"]
cols += [c for c in ("gameday", "gametime") if c in season_games.columns]
g = _sort_games(season_games).select(cols)
```
or sort by `game_id` inside `simulate_season` so that kickoff times don't affect the draws.

### WR-06: `model_version` does not cover the simulator's code; tiebreak or logic edits silently reuse a stale cache

**File:** `pipeline/src/fgs/sim.py:36, 179-193`
**Issue:** CONTEXT requires the cache key to include the "simulator code version". The code satisfies this with a hand-maintained `SIM_VERSION = "sim-v1"` string. Any edit to `simulate_season` (a tiebreak, the noise, the win-prob formula) or to `_static` keeps the same key unless someone remembers to bump the string. `build`, `export` and `backtest` would then serve the old results with no warning, and the test suite would not notice because its session cache starts cold.
**Fix:** Derive the version from the source:
```python
import inspect
payload["code"] = hashlib.sha256(inspect.getsource(sys.modules[__name__]).encode()).hexdigest()
```
Or keep `SIM_VERSION` but add a test that pins the source hash next to it, so the test fails when the code changes and the version doesn't.

### WR-07: Wildcard head-to-head is applied even when the tied teams never all met

**File:** `pipeline/src/fgs/sim.py:137-141, 158-165`
**Issue:** CONTEXT says wildcards go "win% → head-to-head **(if applicable)** → random". `h2h()` gives 0.5 to a team with no games against the tied set and applies the step anyway. In a three-way wildcard tie where A beat B once and C met neither, C (0.5) beats B (0.0), and in a two-team version a team that lost its only meeting loses to one that never played. NFL rules (and the stated simplification) skip head-to-head unless every tied team met every other, or one team swept. This skews wildcard odds in many simulations: same-conference non-division teams often never meet. Division ties are unaffected because division rivals always play twice.
**Fix:** For the wildcard step, apply h2h only in sims where every pair in the tied set met:
```python
def h2h_applicable(m):
    mf = m.astype(np.float32)
    met = (Gm > 0).astype(np.float32)
    k = mf.sum(1, keepdims=True)
    return ((mf @ met.T) * mf == (k - 1) * mf).all(1)  # each tied team met all others
m2 = best(m, h2h(m))
m = np.where(h2h_applicable(m)[:, None], m2, m)
```

### WR-08: Missing sim rows silently become 0% odds, 0 expected wins and 0 po_trend inside the score

**File:** `pipeline/src/fgs/features.py:226-236`
**Issue:** When `sim` is provided, `_sim_columns` left-joins it and runs `fill_null(0.0)` on `playoff_prob`, `exp_wins` and `po_trend`. `vs_exp` falls back to 0 when `exp_total` is null. A snapshot missing from the sim frame therefore scores as "0% playoff odds, no trend", and the export displays "Playoff odds 0%" for it. The causes could be a snapshot week the sim didn't iterate, a cache/digest bug, or a franchise mismatch. `check_sim` only checks sums per present (season, week), so a season or week with no rows at all is never flagged. The `fill_null` is only meant for the `sim is None` path.
**Fix:** When `sim is not None`, assert full coverage before filling:
```python
j = snap.join(s, on=["season", "week", "franchise_id"], how="left")
miss = j.filter(pl.col("playoff_prob").is_null())
if miss.height:
    raise ValueError(f"sim missing {miss.height} snapshot rows, e.g. {miss.row(0)}")
```
Keep the 0-fill only for the lag (`_p_lag`) at legitimately absent weeks. Also add a coverage check: sim keys == snapshot keys.

## Info

### IN-01: `fgs check` and `fgs export` write the sim cache

**File:** `pipeline/src/fgs/cli.py:235, 285, 302`
**Issue:** These commands call `derive(..., sim_cache_dir=...)` with the default `sim_write_cache=True`, so a read-only verification (`fgs check`) rewrites `data/derived/sim/*.parquet`, even when its own checks then fail. The cache is content-addressed, so the risk is low, but it contradicts refresh's check-then-write design.
**Fix:** Pass `sim_write_cache=False` in `_cmd_check`, or save only when `ok`.

### IN-02: Scramble-only QBs get a null `qb_name`

**File:** `pipeline/src/fgs/pbp.py:88-93`
**Issue:** `qb_id` falls back to `rusher_player_id` on dropbacks, but `qb_name` only coalesces `passer` and `passer_player_name`. The slim schema has no `rusher_player_name`. A primary passer whose dropbacks in that game were all scrambles gets an id but no name, so the team page shows no QB.
**Fix:** Add `rusher_player_name` to `SLIM_COLUMNS` and to the coalesce, behind the same `qb_dropback == 1` guard.

### IN-03: Simulator raises a bare KeyError when a scheduled team has no Elo at that week

**File:** `pipeline/src/fgs/sim.py:101, 212-214`
**Issue:** `_simulate_one_season` asserts there are no *extra* snapshot teams, but not the reverse. A REG team missing from `elo` crashes inside a list comprehension with `KeyError: 'XXX'` and no season or week in the message.
**Fix:** Also assert `set(home|away) - set(elo)` is empty, with a message that names the season and week.

### IN-04: po_trend differences two independent Monte Carlo draws

**File:** `pipeline/src/fgs/sim.py:91`; `pipeline/src/fgs/features.py:228-231`
**Issue:** Each week gets its own `default_rng([seed, season, week])`. `p(w) − p(w−3)` therefore carries about ±0.016 of pure sampling noise at 2,000 sims (SE about 0.011 per side), which is comparable to many real 3-week moves. This may help explain po_trend's ≈0 weight.
**Fix:** Optional: use common random numbers across weeks, by seeding per season and drawing per-game uniforms indexed by game, or raise `N_SIMS`. Note the noise floor in BACKTEST_LOG.

### IN-05: `load_pbp_season` changes nflreadpy's global config

**File:** `pipeline/src/fgs/pbp.py:51`
**Issue:** `update_config(cache_mode="off")` runs on every pbp download and changes process-wide nflreadpy state. That affects any later `load_schedules`/`load_teams` call in the same process, such as `build_all`, which might rely on nflreadpy caching.
**Fix:** Set the cache mode once at CLI startup, or restore the previous config after the call.

---

_Reviewed: 2026-11-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---
phase: 05-efficiency-qb-trend-season-simulator
fixed_at: 2026-11-11T20:53:07Z
review_path: .planning/phases/05-efficiency-qb-trend-season-simulator/05-REVIEW.md
iteration: 1
findings_in_scope: 14
fixed: 14
skipped: 0
status: all_fixed
---

# Phase 5: Code Review Fix Report

**Fixed at:** 2026-11-11T20:53:07Z
**Source review:** .planning/phases/05-efficiency-qb-trend-season-simulator/05-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 14 (CR-01, WR-01..WR-08, IN-01..IN-05)
- Fixed: 14
- Skipped: 0
- `weights.yaml` was not changed (Phase 6 freezes it).

**Verification after all fixes:**
- `uv run fgs export`: 92 files, latest 2026 week 9.
- `uv run fgs check`: all checks pass, including the new `sim_coverage` and `vegas_coverage` checks.
- `uv run pytest -q`: 314 passed.
- Web on Node 22: `npm run test` (69 passed), `npm run check` (0 errors, 0 warnings) and `npm run build` all pass.

**Backtest impact (WR-07 and IN-04 changed the simulator).** These are walk-forward results from `uv run fgs backtest`, test seasons 2003–2021, holdout sealed.

| Candidate | Before | After |
|-----------|--------|-------|
| 11-factor interim composite (`ridge:+po_trend`), N=8 Spearman | 0.5262 | **0.5262** (0.526188 → 0.526249) |
| Same composite, N=4 Spearman | 0.4756 | 0.4758 |
| `ridge:+vs_exp`, N=8 | 0.5265 | 0.5265 (unchanged) |

`vs_exp` does not move because the week-0 sim draws are identical under both seedings. NumPy treats `SeedSequence([seed, season, 0])` the same as `[seed, season]`, and at week 0 every game is still to be played, so the draws match. The end-of-REG playoff-field accuracy for 1999–2021 rose from 0.9754 to 0.9787.

## Fixed Issues

### CR-01: A5 override shows playoff bye teams as "Playoff odds 0%" until their divisional game is scheduled

**Files modified:** `pipeline/src/fgs/export.py`, `pipeline/tests/test_export.py`
**Commit:** 4fa9276
**Applied fix:** `_playoff_display` now shows 100 for teams in a non-REG row once REG is done. It forces 0 only when the post-season field is fully known, meaning the number of distinct non-REG teams is at least `playoff_teams(season)`. Until then every other team keeps its raw sim value, so bye teams in wildcard week show roughly 100% instead of 0%. `playoff_teams` is looked up at call time. Changes to the tests:
- The existing unit test now monkeypatches `playoff_teams` so the field counts as known.
- A new test covers a synthetic wildcard-rows-only season and checks that the bye team keeps 97 rather than dropping to 0.

### WR-01: Team page odds/QB line renders with a collapsed separator

**Files modified:** `web/src/components/Sep.svelte` (new), `web/src/components/TeamPage.svelte`, `web/src/components/SiteHeader.svelte`, `web/src/lib/sep.test.ts` (new)
**Commit:** de326b1
**Applied fix:** There is now one `<Sep />` component. It owns the separator's `margin-inline: var(--space-xs)` and its muted colour in its own scoped style, so the spacing applies wherever it renders, including inside `{#if}`.
- **Team page:** all three header lines use it (when · Now, record · rank, odds · QB). The page-local `.sep` rule is gone.
- **Site header:** the nav uses it too. The nav gap went from sm to xs, so the total spacing is unchanged at 8px.
- **Board:** it has no element separators. BoardHeading and SiteFooter use literal " · " text or CSS `content`, which can't collapse.

The new `sep.test.ts` (vitest) does three things:
- Compiles `Sep.svelte` and asserts the scoped CSS contains the margin.
- Fails if any other component hand-rolls `class="sep"` or a bare `·` span.
- Asserts TeamPage uses `<Sep />` exactly 3 times.

The built CSS contains `.sep.svelte-152ghng{margin-inline:var(--space-xs);...}`. I did not check it visually in a browser at 375px or 1280px.

### WR-02: pbp lagging the schedule makes `fgs refresh` fail outright

**Files modified:** `pipeline/src/fgs/pbp.py`, `pipeline/src/fgs/checks.py`, `pipeline/src/fgs/cli.py`, `pipeline/tests/test_pbp.py`, `pipeline/tests/test_cli.py`
**Commit:** dd1c9c6
**Applied fix:** `pbp._missing_pbp` splits played games that have no pbp into two groups:
- **Lagging:** current-season games played within `PBP_LAG_DAYS = 3` of the season's latest played gameday, or every current-season game when no current-season pbp exists yet.
- **Hard gaps:** everything else.

The window is measured from the data, not the wall clock, so the result is reproducible. `check_pbp` fails only on hard gaps. The new `pbp.pbp_lag` returns the lagging games as messages for a new soft-check list, `checks.WARNINGS` / `run_warnings`. `_checked_derive` prints these as `warn  pbp_lag` and never fails on them.

Downloads are now tolerant:
- **Refresh:** `_download_pbp` catches a failed season download, prints a warning, and falls back to the cached season, or to none.
- **Build:** `build_all` catches a failed download and rebuilds without the new current-season pbp.

The efficiency factors already handle a game with no pbp: it drops out of the EPA sequence rather than counting as 0. Two new tests cover the split, plus a refresh test where the current-season download raises; refresh still exits 0 with a `pbp_lag` warning.

### WR-03: Refresh writes are atomic per file, not as a set

**Files modified:** `pipeline/src/fgs/cli.py`, `pipeline/tests/test_cli.py`
**Commit:** 0456700
**Applied fix:** Refresh writes `data/cache/refresh.incomplete` right before its first write and deletes it after `write_export` succeeds. A crash or Ctrl-C in between leaves the marker behind:
- `fgs export` refuses with an error.
- `fgs check` reports `FAIL  refresh_complete`.
- `fgs backtest` warns.

All three stay that way until a refresh completes. `build_all` and `build --help` now say plainly that build is the unchecked path; I documented this instead of restructuring build. New tests check that the happy path removes the marker and that a leftover marker blocks export and fails check.

### WR-04: Missing win_totals.csv silently switches 2003–2020 expectations to model-sourced

**Files modified:** `pipeline/src/fgs/checks.py`, `pipeline/src/fgs/cli.py`, `pipeline/tests/test_checks.py`, `pipeline/tests/test_cli.py`
**Commit:** 8456dbc
**Applied fix:**
- **New check:** `check_vegas_coverage` (`vegas_coverage`) fails when any scheduled season in 2003–2020 has no Vegas rows, or when `vegas` is None.
- **Loud warning:** `_cached_vegas` prints a WARNING when the file is missing.
- **Refresh fallback:** with `download=True`, refresh fetches the frozen `win_totals.csv` once via `load_win_totals` when it is absent.
- **Tests:** the refresh test fixture copies the real `win_totals.csv` into its tmp cache, so tests stay offline.

### WR-05: `input_digest` omits the columns that set the game order

**Files modified:** `pipeline/src/fgs/sim.py`, `pipeline/tests/test_sim.py`
**Commit:** 45f07ef
**Applied fix:** `input_digest` now hashes `_sort_games(season_games)` with `gameday` and `gametime` included, in the same order the simulator reads them. A moved kickoff therefore invalidates the cached season. A test checks that moving a kickoff changes the digest and that the input frame's row order does not.

### WR-06: `model_version` does not cover the simulator's code

**Files modified:** `pipeline/src/fgs/sim.py`, `pipeline/tests/test_sim.py`
**Commit:** 5f675db
**Applied fix:** `SIM_CODE_HASH`, the sha256 of `sim.py`'s source bytes, is now part of the `model_version` payload. `SIM_VERSION` is kept. The check is conservative: editing a comment also triggers one cold re-simulation. A test pins the hash to the file and checks that changing it changes the version.

### WR-07: Wildcard head-to-head is applied even when the tied teams never all met

**Files modified:** `pipeline/src/fgs/sim.py`, `pipeline/tests/test_sim.py`
**Commit:** c027c36
**Status:** fixed: requires human verification (tiebreak logic change)
**Applied fix:** Wildcard head-to-head now applies, per sim, only when every tied team met every other one (`h2h_applicable`). Skipping h2h alone fell straight through to a coin flip, and end-of-REG field accuracy for 1999–2021 dropped from 0.9754 to 0.9690. That broke `test_real_field`, which requires at least 0.97.

I therefore added the NFL's next wildcard step, **conference win%**, before the coin flip, which brought accuracy to 0.9786.

> **Note: this goes beyond the review's suggestion.** CONTEXT's chain was "win% → h2h (if applicable) → random". It is now "win% → h2h (if applicable) → conference win% → random". The module docstring is updated.

A new test builds a 3-way tie where A beat B and C met neither, with level conference records, and checks it comes out about 1/3 each. Once every pair has met, h2h decides.

### WR-08: Missing sim rows silently become 0% odds, 0 expected wins and 0 po_trend

**Files modified:** `pipeline/src/fgs/features.py`, `pipeline/src/fgs/checks.py`, `pipeline/tests/test_features.py`, `pipeline/tests/test_checks.py`
**Commit:** de58805
**Applied fix:**
- **Features:** when a sim frame is given, `_sim_columns` raises `ValueError("sim missing N snapshot rows, e.g. ...")` instead of filling missing rows with 0. Only the lagged value (`_p_lag`) is still 0-filled.
- **New check:** `check_sim_coverage` (`sim_coverage`) requires the sim keys to equal the snapshot keys, in both directions.

### IN-01: `fgs check` writes the sim cache

**Files modified:** `pipeline/src/fgs/cli.py`, `pipeline/tests/test_checks.py`
**Commit:** 5562a2e
**Applied fix:** `_cmd_check` passes `sim_write_cache=False`, so it reads the sim cache but never writes it. `fgs export` still writes it, since export is a writer.

### IN-02: Scramble-only QBs get a null `qb_name`

**Files modified:** `pipeline/src/fgs/pbp.py`, `pipeline/tests/test_pbp.py`
**Commit:** 51df868
**Applied fix:** `rusher_player_name` is added to `SLIM_COLUMNS` and to the `qb_name` coalesce, behind the same `qb_dropback == 1` guard. The slim pbp caches already on disk lack this column. `scrimmage` adds it as null for them, so old seasons keep a null name for scramble-only QBs until they are re-downloaded. Refresh re-downloads the current season every time, so the live team page benefits right away.

### IN-03: Simulator raises a bare KeyError when a scheduled team has no Elo

**Files modified:** `pipeline/src/fgs/sim.py`, `pipeline/tests/test_sim.py`
**Commit:** 51e5a03
**Applied fix:** `_simulate_one_season` now raises `ValueError("{season} wk{w}: REG teams without an as-of Elo snapshot: [...]")`.

### IN-04: po_trend differences two independent Monte Carlo draws

**Files modified:** `pipeline/src/fgs/sim.py`, `pipeline/tests/test_sim.py`
**Commit:** c6b2e4e
**Decision:** fixed. It was trivial to do with common random numbers.
**Applied fix:**
- **Seeding:** there is one RNG stream per season, `default_rng([seed, season])`, instead of one per week.
- **Draws:** the simulator draws `u` for every game in the season's fixed order (`rng.random((n_sims, G))[:, rem]`). Column k is therefore the same game in every week, and the per-sim team noise and tiebreak coins are shared too.

`p(w) − p(w−3)` now reflects changed inputs rather than fresh sampling noise. A test checks that a week with nothing newly known reproduces the previous week exactly. `N_SIMS` is unchanged, and I did not add a noise-floor note to BACKTEST_LOG.

### IN-05: `load_pbp_season` changes nflreadpy's global config

**Files modified:** `pipeline/src/fgs/ingest.py`, `pipeline/src/fgs/pbp.py`, `pipeline/tests/test_pbp.py`
**Commit:** fb77217
**Applied fix:** The new `ingest.nflreadpy_uncached()` context manager saves `get_config().cache_mode`, sets it to "off" for the download, and restores it in `finally`. The pbp, schedules and teams loaders all use it. A test confirms the mode is restored even when the download raises.

## Other commits

- **475d0b2:** `chore(05): regenerate site data after review fixes` (`uv run fgs export`). Playoff odds and po_trend change with WR-07 and IN-04. Weights are unchanged.
- **478ddae:** `docs(06): create phase plan` landed on main in the middle of this run. It is not from this fixer; I did not touch it.

## Notes for Phase 6

- The sim cache key changed (WR-06 code hash plus the simulator edits). The first `build`, `export` or `backtest` after these commits re-simulates once, in about 10 seconds.
- `data/derived/sim/` still contains the old `c9b135d58694.parquet`. It is unused and safe to delete.
- If Phase 6 needs the wildcard chain to match CONTEXT exactly, revisit the WR-07 conference-win% step.

---

_Fixed: 2026-11-11T20:53:07Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

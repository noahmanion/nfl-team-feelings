# Phase 5: Efficiency, QB Trend & Season Simulator - Research

**Researched:** 2026-11-11
**Domain:** nflverse play-by-play aggregation, as-of EWMA factors (Polars), vectorized NumPy Monte Carlo season simulation with era rules, preseason expectations (Vegas vs model), walk-forward ridge add-one-at-a-time
**Confidence:** HIGH. Every number below comes from a prototype run on real data in this session: 1999–2026 pbp downloaded to scratch, plus the Phase 4 walk-forward harness, whose 7-factor base reproduces exactly (Spearman N=8 0.5219).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Play-by-play data (DATA-05)
- Load via `nflreadpy.load_pbp(season)` per season 1999→current; immediately slim to needed columns and cache as `pipeline/data/cache/pbp/{season}.parquet` (refresh re-downloads only the current season). Never commit pbp.
- Per team-game aggregates in `pipeline/data/derived/team_game_epa.parquet`: offensive EPA/play, defensive EPA/play allowed, net EPA/play, plays count; garbage-time filter keeps plays with win probability between 0.05 and 0.95 (use `wp`; exclude QB kneels/spikes, no-plays). QB: for the team's primary passer that game (most dropbacks): dropback EPA/play, success rate, dropbacks, passer id/name.
- 1999–2000 flagged `low_confidence=true` (nflfastR dropped official support; ~1% null EPA) — included but flagged in data and methodology.
- Map pbp team codes through the existing franchise map (pbp is already normalized per Phase-1 research — assert it).

#### Efficiency trajectory factor `epa_traj` (MODEL-05)
- Opponent-adjusted net EPA/play per game = team net EPA/play − (opponent's as-of season-to-date net EPA/play allowed-adjustment); exact adjustment chosen by research (must be as-of, no leakage).
- Factor = EWMA of adjusted net EPA/play (half-life ~4 games, crossing season boundary) MINUS the team's season-to-date mean (trajectory, not level). Week 0 / no games → 0. Research may propose level+trajectory if trajectory alone has no signal — record both deltas.

#### QB trend factor `qb_trend` (MODEL-11)
- Tracks the CURRENT starting QB (from the latest game's primary passer; schedule `home_qb_name/away_qb_name` as cross-check): EWMA of his dropback EPA over his last ~6 starts (any team, any season) minus the team's season-to-date QB dropback EPA. If the QB changed, the new QB's own history drives it (QB with <2 career starts in data → 0 with a `qb_new` flag). Research finalizes.

#### Season simulator (MODEL-13)
- Vectorized NumPy Monte Carlo per (season, week): simulate all remaining REG games using as-of Elo win probabilities with era HFA (ratings fixed within a sim run, no hot updates in v1), then apply era rules from `season_config` (divisions, 12 vs 14 playoff teams, 16 vs 17 games) with simplified tiebreakers: division winner by win% → head-to-head win% → division win% → random; wildcards by win% → head-to-head (if applicable) → random. Default 2,000 sims; seeded RNG for determinism.
- Outputs per (season, week, franchise): `playoff_prob`, `exp_wins` (final REG wins). Week-0 sim = preseason expected wins. Cached in `pipeline/data/derived/sim/{model_version}.parquet` keyed by (season, week, franchise); `model_version` = hash of Elo params + era config + n_sims + simulator code version.
- Sanity checks: per week Σ playoff_prob ≈ number of playoff spots; exp_wins sums to total games/2 per season (ties aside).

#### vs-expectation factor `vs_exp` (MODEL-08)
- Expected win% to date = preseason expected wins / games in season (constant per season); factor = actual REG win% to date − expected win% (weighted by games played: (wins − exp_wins_per_game × games)/max(games,1)). Week 0 → 0.
- Expectation source: nflverse `win_totals` (2003–2020) where available (tag `vegas`), else model week-0 sim (tag `model`). Every row carries `expectation_source`. Validate model-vs-Vegas correlation on 2003–2020 (target r ≈ 0.7–0.8) and report it.
- No hand-entered 2021+ Vegas totals in v1 (v2 requirement).

#### Playoff-odds trend factor `po_trend` (MODEL-12)
- Factor = playoff_prob(now) − playoff_prob(3 weeks earlier within season; week 0 if fewer). Included in the score with its fitted weight reported even if ≈0.

#### Process
- Add order: epa_traj → qb_trend → vs_exp → po_trend, each: feature + hand-computed test, refit interim walk-forward Ridge (≤2021), `fgs backtest`, append BACKTEST_LOG row (Δ, sign), update weights.yaml, regenerate site data. Team page shows new factors automatically (Phase 4 made it factor-agnostic); meta.factors gets labels/descriptions; blurb phrasebook gains entries for the 4 new factors.
- Leakage test must cover new factors (pbp/sim as-of). Simulator runtime must keep `fgs refresh` reasonable (target < 2 min incremental; full historical sim may be longer but cached).
- `fgs refresh` downloads current-season pbp + recomputes current season sims only.

### Claude's Discretion
- Module layout (`pbp.py`, `efficiency.py`, `sim.py`), exact EWMA spans after research, sim vectorization strategy, cache format.

### Specific Ideas
- `epa_traj` is the user's "WAR improvements" idea — label it "Getting better (efficiency trend)" in the UI.
- Playoff odds can also be displayed on the team page (small stat), since they're computed anyway.

### Deferred Ideas (OUT OF SCOPE)
- Hand-entered 2021+ Vegas win totals (v2), free agency (v2), in-sim Elo hot updates (later).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-05 | Per-team-game pbp aggregates (EPA/play garbage-filtered; QB EPA/dropback + success rate), 1999→present, 1999–2000 flagged | `load_pbp` takes ~1 s per season and 26 s for all 28. The slim cache is ~0.9 MB per season (26 MB total). Aggregating 1.30M plays takes 0.22 s → 14,818 team-game rows. pbp codes are already franchise codes (0 mismatches vs `home_id/away_id`). 3 played games have no pbp. Scrambles need `passer_id`, not `passer_player_id` (Pattern 1) |
| MODEL-05 | Efficiency trajectory (EWMA of opp-adjusted EPA vs season-to-date level) | The CONTEXT definition with the opponent's prior-EWMA adjustment, h=4, is the **best of ~40 variants**: ΔSpearman **−0.0000**, ΔR² −0.0003, ΔBrier −0.00007. Fitted sign **− in 19/19 folds**. Level variants are worse (−0.0013 to −0.0032). Both are logged |
| MODEL-11 | QB play trend for the current starting QB | Literal CONTEXT definition (QB EWMA − team season-to-date): Δ **−0.0005**. **Recommended:** current QB's form level (dropback-weighted EWMA, h=4, his own starts on any team), with 0 at week 0 and for QBs with <2 starts: Δ **+0.0028**, ΔBrier −0.00081, sign **+ in 19/19 folds**. The largest single gain in Phases 4–5 |
| MODEL-13 | Monte Carlo simulator with era rules + simplified tiebreakers | Pattern 4 prototype: **15 ms per (season, week) at 2,000 sims; 609 snapshots (1999–2026) in 9.5 s**. Σp = playoff spots and Σexp_wins = REG games exactly. Deterministic. Simplified tiebreakers pick the actual playoff field for 98% of team-slots at end of REG. σ=100 Elo per-sim rating noise improves Brier from 0.1292 to 0.1263 and fixes overconfidence |
| MODEL-08 | Performance vs preseason expectation, Vegas override where available, source tagged | `win_totals.csv` (nflverse/nfldata): 576 rows, 2003–2020, legacy codes. **Model-vs-Vegas r = 0.863** (per season 0.72–0.93), above the 0.7–0.8 target. Δ **+0.0019** (sign −, 18/19). **But** with model-sourced expectation, which is all of 2021+ including the holdout, it is −0.0011 vs no vs_exp (Pitfall 1) |
| MODEL-12 | Playoff-odds trend | Δ **−0.0003**, weight **−0.01** (≈0), corr with the 3-week Elo change 0.70. Kept in the score per CONTEXT, weight reported |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Work only inside `feel-good-scorew/`. It is self-contained: no shared code or deps, no root manifests.
- Keep it light: quick prototypes, no heavy process. Extend the existing pytest/vitest gates and add no new frameworks.
- The README says what the idea is, how to run it, and where it stands. Update the Status line at phase end.
- Project stack: Python 3.13 + uv + Polars + NumPy in `pipeline/`. Svelte 5 + Plot in `web/`. JSON in `web/public/data/` is the only contract. No decimals in the UI, no logos.
- This research made **no project edits**. All prototypes live in scratch (`.../scratchpad/p5/`) with their own uv env. pbp was downloaded there, not into `pipeline/data`.

## Summary

The pbp side is cheap and clean. `nflreadpy.load_pbp(season)` returns 372 columns, ~100 MB in memory per season, in ~1 s. Slimming to ~20 columns gives ~0.9 MB parquet per season. pbp already uses **modern franchise codes for every season** (LV/LAC/LA, never OAK/SD/STL), so the franchise map is an identity check. Assert `codes ⊆ CANONICAL`. Three played games have no pbp at all (1999_01_BAL_STL, 2000_03_SD_KC, 2000_06_BUF_MIA). Null EPA is ≤0.015% even in 1999–2000, but `qb_dropback` is null on ~1.2% of 1999–2000 plays. Kneels already have pass=rush=0. Spikes have pass=1 and must be excluded. Scrambles have `passer_player_id` null, so use nflfastR's `passer_id`/`passer` (which include scrambles), with `rusher_player_id` as the last fallback. The most-dropbacks passer matches the schedule's listed starter in 96–98% of team-games. The misses are in-game QB changes.

The factor results are honest and mixed, as PITFALLS predicted for momentum-type inputs. **`epa_traj`** as defined in CONTEXT is the best of ~40 trajectory, level and slope variants, but its delta is ~0 (−0.0000) and its fitted weight is negative in every fold: an "improving" EPA trend slightly regresses once Elo, mov and sow are in. EPA *level* has strong univariate signal (Spearman 0.47, the same as mov) but is redundant: corr 0.86 with Elo and mov, Δ −0.0019. **`qb_trend`** as literally defined (QB form minus team season-to-date) is Δ −0.0005. The current QB's *form level* (dropback-weighted EWMA over his own last starts on any team) is **+0.0028**, positive in 19/19 folds, and nearly orthogonal to the game-result factors (corr 0.57 with Elo). It is the biggest gain of Phases 4–5. **`vs_exp`** adds +0.0019, but only because Vegas lines carry information Elo doesn't. With the model's own week-0 expectation it is −0.0006, and when a Vegas-trained weight is applied to model-sourced rows (the 2021+ deployment condition) it is −0.0011 against leaving vs_exp out. **`po_trend`** is ≈0 (weight −0.01), as expected.

The simulator is the easy win. A fully vectorized NumPy design builds the outcome matrix with one RNG draw, then a pairwise-results tensor through one matmul with a one-hot pair matrix. Tiebreakers are stepwise masks. It runs **15 ms per snapshot at 2,000 sims, and all of 1999–2026 (609 snapshots) in under 10 s**, so caching is a convenience rather than a necessity. It is deterministic via `default_rng([seed, season, week])`. Fixed ratings make it overconfident (the 0.85 bin observes 0.77). A per-sim team rating offset N(0, 100 Elo), drawn once per sim so ratings stay fixed within a run, calibrates it (0.849 → 0.858) and lowers playoff-odds Brier from 0.1292 to 0.1263.

**Primary recommendation:** Build `pbp.py` (load/slim/cache + `team_game_epa`), `efficiency.py` (epa_traj + qb form), `sim.py` (the verified vectorized simulator with σ=100) and `expectation.py` (win_totals + vs_exp). Feed their frames into `features.build_features` as optional inputs, so the leakage firewall and purity hold. Run the add-one loop, expecting the BACKTEST_LOG rows in the Prototype Results table. Implement `qb_trend` as **current-QB form level**, and also log the literal-definition delta. Log vs_exp's deployment-condition delta (−0.0011) for Phase 6.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| pbp download, slim, cache | Pipeline I/O (`pbp.py`, called from `cli`/`ingest`) | — | Same "we own the cache" pattern as `ingest.load_schedules` |
| team_game_epa aggregation | Pipeline pure (`pbp.team_game_epa`) | — | Pure function of the slim pbp, unit-testable on a tiny synthetic play frame |
| epa_traj, qb_trend per-game → snapshot | Pipeline pure (`efficiency.py`, used by `features.py`) | — | As-of rules mirror `_last16` (cumsum/EWMA + `join_asof` backward) |
| Season simulation | Pipeline pure (`sim.py`) | `cli` handles the cache read/write | Needs as-of Elo snapshots plus the season schedule. Output is an input to features |
| Win totals ingest | Pipeline I/O (`expectation.py` or `ingest.py`) | — | One-time CSV fetch, cached. The file has been frozen since July 2021 |
| vs_exp, po_trend | Pipeline pure (`features.py`, from the sim + expectation frames) | — | Snapshot-level arithmetic |
| Ridge add-one loop, weights proposal | `backtest.py` (dev-only) | `weights.yaml`, `BACKTEST_LOG.md` | Firewall unchanged |
| playoff_prob display, `expectation_source`, QB name | `export.py` → JSON | Browser team page (small stat) | JSON is the only contract |

## Standard Stack

No new dependencies. **`load_pbp` works with the existing pinned deps.** It was verified in a fresh venv with only `nflreadpy==0.1.5 polars numpy` (no pyarrow, no pandas), loading 2026 in 1.0 s.

### Core
| Library | Version (installed) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| nflreadpy | 0.1.5 (pinned) | `load_pbp(season)`: per-season pbp as Polars | Already the project's nflverse loader [VERIFIED: signature `load_pbp(seasons: int\|list[int]\|bool\|None)` via inspect] |
| polars | 2.1.0 | Slim, aggregate, `ewm_mean(half_life=, adjust=True).over(...)`, `join_asof` | Same patterns as features.py [VERIFIED: prototype] |
| numpy | 2.5.4 | Simulator (`default_rng`, matmul, einsum) | Already used [VERIFIED: prototype] |

### Data sources
| Source | Access | Coverage | Notes |
|--------|--------|----------|-------|
| nflverse pbp | `nflreadpy.load_pbp(s)` with `update_config(cache_mode="off")` | 1999–2026 (2026 partial) | 372 cols. Slim to ~20 [VERIFIED] |
| nflverse win totals | `https://raw.githubusercontent.com/nflverse/nfldata/master/data/win_totals.csv` (12.8 KB) | 2003–2020, 32 teams each (576 rows) | Columns `season,team,line,over_odds,under_odds`. **Legacy codes OAK/SD/STL**, so map through `RAW_TO_FRANCHISE`. Last commit 2021-07-29 (frozen). Not available via nflreadpy (no `load_win_totals`) [VERIFIED: download + GitHub API] |

**Installation:** none. Fetch win_totals with `urllib.request.urlopen` (stdlib) or `pl.read_csv(url)` into `pipeline/data/cache/win_totals.csv`. It is a small, frozen external file. Download it once and never refresh it (or vendor it with a source note; discretion).

## Package Legitimacy Audit

No packages are installed in this phase. nflreadpy, polars and numpy are already pinned. slopcheck was not run because there was nothing new to check.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| (none new) | — | — | — | — | — | — |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Prototype Results (real data, this session)

Scripts are in `/private/tmp/claude-501/-Users-noahmanion-Dropbox-code-idea-graveyard-feel-good-scorew/e9aca8f6-0367-4770-bd90-f3eef6a0daef/scratchpad/p5/`: `dl.py`, `dq.py`, `dq2.py`, `tge.py`, `eff.py`, `qb.py`, `sim.py`, `harness.py`, `run_*.py`, `final.py`, `mismatch.py`. They import a frozen copy of the Phase-3/4 `fgs` code (`p5/src/fgs`) plus the Phase 4 `factors.py`.

### pbp facts [VERIFIED: prototype]
| Fact | Value |
|------|-------|
| Download time | 0.7–1.1 s per season. **26 s for 1999–2026** |
| Raw per season | ~46–50k rows, 372 columns, ~100 MB in memory |
| Slim cache (35 cols tested; ~20 needed) | 0.9–1.0 MB parquet per season, 26 MB total |
| Aggregate all seasons → team-game | 0.22 s, 14,818 rows (7,409 games × 2) |
| Team codes | All in CANONICAL plus `''` (104 rows: timeouts/end-of-quarter with posteam ''). **0 mismatches vs franchise ids**. 877 games differ from *raw* schedule codes only because schedules use OAK/SD/STL |
| Played games without pbp | **3**: 1999_01_BAL_STL, 2000_03_SD_KC, 2000_06_BUF_MIA. pbp→schedule: 0 orphans |
| Null EPA on scrimmage plays | 0.003% (1999), 0.015% (2000), 0.012% (2001), ~0 after |
| `qb_dropback` null | 1.1% (1999), 1.3% (2000), then ~0 |
| Kneels | 10,066, all pass=0/rush=0, so excluded by `pass\|rush` anyway |
| Spikes | 2,017, **pass=1**, so they must be excluded explicitly |
| `play_type=='no_play'` with pass/rush=1 | 38,851 (penalty-nullified, EPA present, mean +0.15). CONTEXT excludes them. Including them changed nothing meaningful (variant `withnp`) |
| Dropbacks with null `passer_player_id` | 500–1,150 per season, mostly scrambles. `passer_id` null on only 0–60 per season |
| wp-filter retention | 83.9% of scrimmage plays. Median 54 plays per team-game after the filter |
| Primary passer == schedule `*_qb_id` | 96.1–98.6% per era. Misses are in-game QB changes |
| Seasons whose week-1 starter ≠ last season's final QB | **34%** |
| Unplayed 2026 games with `*_qb_id` filled | 20% (do not use: inconsistent and not as-of for history) |

### Walk-forward, test 2003–2021, holdout sealed, N=8 target [VERIFIED: prototype run]
The base reproduces Phase 4 exactly (ridge:+luck = 0.5219 / 0.2713 / Brier 0.2190).

| Candidate (cumulative) | Spearman N=8 | R² N=8 | Spearman N=4 | Brier | wk0 | early | mid | late |
|-----------|-------------|--------|--------------|-------|-----|-------|-----|------|
| Phase 4 final (7 factors) | 0.5219 | 0.2713 | 0.4706 | 0.2190 | 0.425 | 0.493 | 0.573 | 0.503 |
| +epa_traj | 0.5219 | 0.2710 | 0.4705 | 0.2189 | 0.426 | 0.494 | 0.573 | 0.501 |
| +qb_trend (form level, wk0→0) | 0.5246 | 0.2747 | 0.4739 | 0.2181 | 0.426 | 0.498 | 0.573 | 0.505 |
| +vs_exp | 0.5265 | 0.2769 | 0.4758 | 0.2178 | 0.424 | 0.502 | 0.574 | 0.507 |
| +po_trend | **0.5262** | **0.2764** | 0.4756 | 0.2179 | 0.424 | 0.502 | 0.573 | 0.507 |

**BACKTEST_LOG rows to expect** (should reproduce to ~4 dp if the implementation matches):

| Factor | ΔSpearman N=8 | ΔR² N=8 | ΔBrier | Fitted sign (1999–2021 proposal) | Note |
|--------|---------------|---------|--------|------------------|------|
| epa_traj | −0.0000 | −0.0003 | −0.00007 | − (−0.20) | − in 19/19 folds. Improving efficiency trend regresses given Elo/mov/sow. Level variant: −0.0019 (logged, not used) |
| qb_trend | **+0.0028** | +0.0037 | −0.00081 | + (+0.63) | + in 19/19 folds. Literal "QB EWMA − team season-to-date" definition: −0.0005 (log it) |
| vs_exp | +0.0019 | +0.0021 | −0.00027 | − (−1.24) | − in 18/19. **Deployment condition (model source, 2021+): −0.0011 vs no vs_exp.** Model-only definition: −0.0006 |
| po_trend | −0.0003 | −0.0005 | +0.00006 | ≈0 (−0.01) | − in 17/19, magnitude tiny. corr(po_trend, 3-wk ΔElo) 0.70 |

**Proposed weights.yaml after each step** (ridge, LOSO-CV alpha, n = 12,331). Note that **alpha jumps from 0.001·n to 0.01·n once vs_exp enters** (season_record/vs_exp collinearity):

| Step | elo | season_record | last16 | mov | sow | streak | luck | epa_traj | qb_trend | vs_exp | po_trend |
|------|-----|---|---|---|---|---|---|---|---|---|---|
| +epa_traj | 3.76 | 0.72 | −0.48 | 1.31 | −1.03 | −0.09 | −0.31 | −0.20 | | | |
| +qb_trend | 3.50 | 0.59 | −0.41 | 1.19 | −0.94 | −0.15 | −0.28 | −0.23 | 0.63 | | |
| +vs_exp | 2.59 | 1.83 | −0.19 | 1.24 | −0.56 | −0.05 | −0.35 | −0.33 | 0.63 | −1.24 | |
| **+po_trend (final interim, 11 factors)** | **2.59** | **1.83** | **−0.20** | **1.24** | **−0.56** | **−0.05** | **−0.35** | **−0.33** | **0.63** | **−1.23** | **−0.01** |

**Fold sign stability (11-factor set, 19 folds):** elo, season_record, mov and qb_trend are + in 19/19. luck and epa_traj are − in 19/19. vs_exp is − in 18/19. po_trend is − in 17/19, but between −0.24 and +0.03. last16, sow and streak are − in only 13–14/19 (unstable, as in Phase 4).
**Alpha sensitivity (final):** at 0.001·n: elo 2.75, season_record 2.11, vs_exp −1.42. At 0.1·n, last16 flips to +0.53 and sow to −0.06. The CV pick is 0.01·n. Keep the procedure (Phase 6 owns changes).

**Collinearity** (Pearson, raw, 1999–2021 REG weeks ≥ 1): **season_record–vs_exp 0.92**, elo–last16 0.90, mov–sow 0.86, elo–mov 0.85, elo–playoff_prob 0.80. epa_traj is near-orthogonal to everything except season_record (−0.36) and vs_exp (−0.43). qb_trend: 0.47–0.57 with the strength factors. po_trend ≤ 0.45. **VIF (11 z-inputs):** season_record **19.8**, elo **17.8**, last16 14.3, vs_exp 9.8, sow 8.0, mov 7.0, luck 3.8, streak 2.3, qb_trend 1.6, epa_traj 1.4, po_trend 1.4. vs_exp ≈ season_record − (preseason expectation), so ridge reads the pair as "season_record plus a negative preseason-expectation term". Expect large offsetting season_record (+) and vs_exp (−) bars on the team page (Pitfall 2).

### epa_traj sweep (Δ vs 7-factor base) [VERIFIED]
| Variant | ΔSpearman | Univariate Spearman vs y8 |
|---|---|---|
| **adj (opp prior EWMA h=4), EWMA h=4 − season mean (CONTEXT)** | **−0.0000** | −0.077 |
| same, h=3 / 6 / 8 / 2 | −0.0003 / −0.0003 / −0.0004 / −0.0005 | |
| opp-adjust by opponent pre-game Elo (scale 0.00143 EPA per Elo pt), h=4 | −0.0003 | |
| raw (unadjusted) h=4 | −0.0004 | −0.099 |
| no wp filter / include no_play, h=4 | +0.0000 / −0.0003 | |
| within-season EWMA h=3 − season mean | −0.0011 | +0.030 |
| OLS slope over last 8 games | −0.0004 | +0.051 |
| short − long EWMA (h vs 16) | −0.0005 to −0.0010 | +0.25 |
| **level** EWMA h=2..8 (any adjustment) | −0.0013 to −0.0029 | +0.46 to +0.49 |
| level + trajectory (h=4) | −0.0020 | |

### qb_trend sweep (Δ vs 8-factor base incl. epa_traj) [VERIFIED]
| Variant | h=2 | h=3 | h=4 | h=6 |
|---|---|---|---|---|
| Literal: QB form − team season-to-date dropback EPA | −0.0002 | −0.0005 | −0.0009 | −0.0010 |
| QB form − team dropback EWMA (crossing seasons) | −0.0002 | +0.0000 | +0.0007 | +0.0014 |
| **QB form level** (new QB → 0) | +0.0018 | +0.0023 | **+0.0025** | +0.0028 |
| QB form level, week 0 → 0 | | | **+0.0028** (wk0 bucket 0.424→0.426) | |
| new-QB fill: replacement level (p20 = −0.064) / league mean (0.040) | | | +0.0026 / +0.0024 | |
| level + literal trend together | | | +0.0018 | |

### Simulator [VERIFIED]
| Check | Result |
|---|---|
| Runtime | **15.5 ms mean per (season, week), p95 19 ms, 2,000 sims**. All 609 snapshots 1999–2026: **9.5 s** (8.2 s with σ=0) |
| Σ playoff_prob per (season, week) − spots | max 7e-15 |
| Σ exp_wins per (season, week) − REG games | max 4e-6 (float32 accumulation) |
| Determinism | identical output on rerun and after shuffling input game order (rows are re-sorted) |
| Monte Carlo noise at 2,000 sims (seed vs seed) | \|Δp\| mean 0.010, max 0.054 |
| End-of-REG (no games left, 861 team-seasons 1999–2025) vs actual playoff field | 17 team-slots wrong (≈8 spots in 27 seasons). 13 of them are 50/50 coin-flip ties that the real NFL broke with common games/SOV. 2 deterministic misses: 2004 NO/LA, 2017 LAC/BUF (multi-team tie rules) |
| Adding conference-record tiebreak + "h2h only for 2-team ties" | 19 wrong. **No improvement, so keep the CONTEXT chain** |
| Week-0 exp_wins vs actual wins (2003–2021) | r 0.418, MAE 2.33 (Vegas: r 0.471, MAE 2.27) |

**Calibration of playoff_prob vs actual qualification, 2003–2021 REG weeks** (σ = per-sim team rating offset in Elo, drawn once per sim):

| σ | Brier all | wk0 | early | mid | late | 0.8–0.9 bin pred/obs | 0.1–0.2 bin pred/obs |
|---|---|---|---|---|---|---|---|
| 0 (fixed ratings) | 0.1292 | 0.2221 | 0.1719 | 0.1121 | 0.0684 | 0.850 / 0.771 | 0.148 / 0.212 |
| 60 | 0.1273 | 0.2168 | 0.1689 | 0.1111 | 0.0679 | 0.851 / 0.800 | 0.148 / 0.204 |
| **100** | **0.1263** | 0.2130 | 0.1674 | 0.1105 | 0.0672 | **0.849 / 0.858** | 0.148 / 0.179 |
| 125 | 0.1261 | 0.2122 | 0.1674 | 0.1105 | 0.0669 | 0.848 / 0.873 | 0.149 / 0.153 |
| 150 | 0.1265 | 0.2124 | 0.1682 | 0.1110 | 0.0664 | 0.851 / 0.889 | 0.149 / 0.132 |

Base-rate Brier is 0.236. Recommend **σ = 100**: it is the round number at the Brier knee with the best upper-bin calibration. It is fit on ≤2021 only and is part of `model_version`. All vs_exp/po_trend numbers above use σ = 100.

### vs_exp / expectations [VERIFIED]
| Check | Result |
|---|---|
| win_totals coverage | 2003–2020 × 32 = 576 rows, no nulls, line 3.5–12.5 |
| Σ lines per season | 252–265.5 vs 256 (books shade). Normalize per season: `line − mean(line) + games/2` (`vegas_norm`, r unchanged) |
| r(model week-0 exp_wins, Vegas line) | **0.863** pooled. Per season 0.72–0.93 |
| r with actual wins | Vegas 0.471, model 0.397. Odds-adjusted line ≈ same (0.471), so don't bother |
| model exp_wins SD vs line SD | 1.43 vs 1.64 (model is more compressed, as expected from ⅓ regression + σ) |
| Walk-forward: train mixed, test mixed | 0.5265 |
| **Train mixed, test with model-sourced vs_exp (2021+ condition)** | **0.5233** |
| Train model-only, test model-only | 0.5238 |
| No vs_exp (10-factor minus vs_exp) | 0.5244 |

## Architecture Patterns

### System Architecture Diagram

```
nflverse ──► schedules (cache) ─► derive_games: replay ─► games(+asof_week, elo_pre/post) ─► team_games ─► snapshots(elo, W-L-T)
   │                                                                     │                                   │
   ├─► load_pbp(s) ─► slim ─► cache/pbp/{s}.parquet                       │                                   │
   │                     └─► pbp.team_game_epa ─► team_game_epa.parquet ──┤                                   │
   │                         (off/def/net EPA, primary QB: id, name,       │                                   │
   │                          db EPA, SR, dropbacks, low_confidence)       ▼                                   ▼
   │                                                       efficiency.per_game: join on (game_id, franchise_id)
   │                                                         adj_epa = net + opp prior-EWMA net (shift 1)
   │                                                         epa_traj = EWMA_h4(adj) − season mean (in-season only)
   │                                                         qb_form  = Σewm(qb_epa·db)/Σewm(db) over QB's own starts
   │                                                                     │
   └─► win_totals.csv (once) ─► expectation: vegas_norm per (season, franchise)
                                                                         │
            sim.simulate_season(season REG games, snapshot elo @ w, w, σ, seed) for every (season, w)
            ─► sim/{model_version}.parquet: playoff_prob, exp_wins  (week 0 = preseason)
                                                                         │
                                                                         ▼
       features.build_features(snapshots, team_games, *, pbp_games, sim, vegas)
         + epa_traj, qb_trend (+qb_name, qb_new), vs_exp (+expectation_source), po_trend, playoff_prob
                                                                         │
                         ┌───────────────────────────────────────────────┴───────────────┐
                         ▼                                                               ▼
               score.composite (11 weights) ─► mood/explain ─► export JSON      backtest (dev-only): RIDGE_SETS +4 steps
               (rows: points/blurb; team page: playoff_prob small stat,          → BACKTEST_LOG, weights.yaml
                QB name; meta.factors +4)
```

### Recommended Project Structure (new/changed)
```
pipeline/src/fgs/
├── pbp.py          # NEW: SLIM_COLUMNS, load_pbp_season(s, refresh) (cache/pbp/{s}.parquet, atomic write),
│                   #      load_all_pbp(seasons), scrimmage(p), team_game_epa(p) (pure)
├── efficiency.py   # NEW, pure: per_game_epa(team_games, tge), add_opp_adjust, epa_traj, qb_form → snapshot join
├── sim.py          # NEW, pure: simulate_season(...), simulate_all(games, snapshots, seasons, n_sims, sigma, seed),
│                   #      model_version(params) (sha256 of a canonical JSON), SIM_VERSION constant
├── expectation.py  # NEW: load_win_totals (I/O, cached), vegas_expectations(df) (pure, normalized, mapped codes)
├── features.py     # build_features(..., pbp_games=None, sim=None, vegas=None): + epa_traj, qb_trend, vs_exp, po_trend
├── score.py        # FACTORS += epa_traj, qb_trend, vs_exp, po_trend
├── backtest.py     # RIDGE_SETS += 4 steps; derived dict carries team_game_epa + sim frames
├── cli.py          # build/refresh: pbp (current season only on refresh), sims (current season only), win_totals once
├── checks.py       # + pbp codes ⊆ CANONICAL, pbp-game coverage (known 3 missing), sim Σ checks
├── explain.py      # PHRASES for 4 new factors
└── export.py       # meta.factors +4; rows: playoff_prob (int %), expectation_source; team page QB name
pipeline/data/cache/pbp/{season}.parquet   # gitignored (data/ already ignored, verify)
pipeline/data/cache/win_totals.csv
pipeline/data/derived/team_game_epa.parquet
pipeline/data/derived/sim/{model_version}.parquet
```

### Pattern 1: pbp slim + team-game aggregation (verified)
```python
# Source: scratchpad/p5/tge.py (run on all 1.30M plays, 0.22 s)
SLIM_COLUMNS = ["game_id", "season", "week", "season_type", "posteam", "defteam", "play_type",
                "pass", "rush", "qb_dropback", "qb_kneel", "qb_spike", "epa", "wp", "success",
                "passer_id", "passer", "passer_player_id", "passer_player_name", "rusher_player_id"]
WP_LO, WP_HI = 0.05, 0.95

def scrimmage(p):
    return p.filter(
        ((pl.col("pass") == 1) | (pl.col("rush") == 1))
        & (pl.col("qb_kneel").fill_null(0) == 0) & (pl.col("qb_spike").fill_null(0) == 0)
        & (pl.col("play_type").fill_null("") != "no_play")
        & pl.col("epa").is_not_null() & pl.col("posteam").is_not_null() & (pl.col("posteam") != "")
        & pl.col("wp").is_between(WP_LO, WP_HI)
    ).with_columns(
        pl.col("posteam").replace(RAW_TO_FRANCHISE), pl.col("defteam").replace(RAW_TO_FRANCHISE),
        # passer_player_id is NULL on scrambles; nflfastR's passer_id includes them
        pl.coalesce("passer_id", "passer_player_id",
                    pl.when(pl.col("qb_dropback") == 1).then(pl.col("rusher_player_id"))).alias("qb_id"),
        pl.coalesce("passer", "passer_player_name").alias("qb_name"))

def team_game_epa(p):
    s = scrimmage(p)
    assert not ((set(s["posteam"]) | set(s["defteam"])) - CANONICAL)
    off = s.group_by("game_id", "season", pl.col("posteam").alias("franchise_id")).agg(
        pl.col("epa").mean().alias("off_epa"), pl.len().alias("off_plays"), pl.col("success").mean().alias("off_sr"))
    dfn = s.group_by("game_id", pl.col("defteam").alias("franchise_id")).agg(
        pl.col("epa").mean().alias("def_epa"), pl.len().alias("def_plays"))
    db = s.filter(pl.col("qb_dropback") == 1)
    team_db = db.group_by("game_id", pl.col("posteam").alias("franchise_id")).agg(
        pl.col("epa").sum().alias("team_db_epa_sum"), pl.len().alias("team_db"))
    qb = (db.group_by("game_id", pl.col("posteam").alias("franchise_id"), "qb_id")
            .agg(pl.len().alias("dropbacks"), pl.col("epa").mean().alias("qb_epa"),
                 pl.col("success").mean().alias("qb_sr"), pl.col("qb_name").drop_nulls().first().alias("qb_name"))
            .filter(pl.col("qb_id").is_not_null())
            .sort("game_id", "franchise_id", "dropbacks", "qb_id", descending=[False, False, True, False])
            .group_by("game_id", "franchise_id", maintain_order=True).first())   # deterministic tie-break by id
    return (off.join(dfn, on=["game_id", "franchise_id"], how="full", coalesce=True)
              .join(team_db, on=["game_id", "franchise_id"], how="left")
              .join(qb, on=["game_id", "franchise_id"], how="left")
              .with_columns((pl.col("off_epa") - pl.col("def_epa")).alias("net_epa"),
                            (pl.col("season") <= 2000).alias("low_confidence")))
```
Every played team-game has an off and a def row, so the full join gives 0 null off/def. 2 team-games have no dropback-QB (qb_* null). These handle themselves: a null qb_id is skipped in the QB EWMA.

### Pattern 2: epa_traj (opp-adjusted, as-of, verified best of the sweep)
```python
# Source: scratchpad/p5/eff.py
g = (team_games.filter("played").join(tge, on=["game_id", "franchise_id"], how="inner")   # drops the 3 no-pbp games
       .with_columns((pl.col("season").cast(pl.Int64) * 100 + pl.col("asof_week")).alias("key"))
       .sort("franchise_id", "key", "game_id"))
# opponent's strength strictly BEFORE this game: its own EWMA of raw net EPA, shifted by one game
g = g.with_columns(pl.col("net_epa").ewm_mean(half_life=4, adjust=True).shift(1).over("franchise_id").alias("prior_net"))
opp = g.select("game_id", pl.col("franchise_id").alias("opponent_id"), pl.col("prior_net").alias("opp_prior_net"))
g = g.join(opp, on=["game_id", "opponent_id"], how="left").with_columns(
    (pl.col("net_epa") + pl.col("opp_prior_net").fill_null(0.0)).alias("adj_epa"))   # good opponent -> credit
season_mean = (pl.col("adj_epa").cum_sum().over("franchise_id", "season")
               / pl.int_range(1, pl.len() + 1).over("franchise_id", "season"))
g = g.with_columns((pl.col("adj_epa").ewm_mean(half_life=4, adjust=True).over("franchise_id")   # crosses seasons
                    - season_mean).alias("epa_traj"))
# last row per (franchise, key) -> join_asof backward on season*100+week; if the matched game's season != snapshot
# season (week 0 / no in-season games) -> 0.0; null -> 0.0
```
Sign derivation: off_adj = off − (O_def_allowed − lg) and def_adj = def − (O_off − lg), so net_adj = net + O_net. A strong opponent adds credit. The CONTEXT phrase "net − (opponent's …)" means the same thing with the opponent term defined as *allowed*. Use `net + opp_prior_net`.

### Pattern 3: qb_trend = current QB's recent form (recommended)
```python
# Source: scratchpad/p5/qb.py (h=4; week 0 -> 0)
QB_HALF_LIFE, QB_MIN_STARTS = 4, 2
q = (g.filter(pl.col("qb_id").is_not_null())
       .select("game_id", "franchise_id", "key", "qb_id", "qb_epa", "dropbacks")
       .with_columns((pl.col("qb_epa") * pl.col("dropbacks")).alias("qsum"), pl.col("dropbacks").cast(pl.Float64).alias("qdb"))
       .sort("qb_id", "key", "game_id")
       .with_columns(   # dropback-weighted EWMA over the QB's OWN games (any team, any season)
           (pl.col("qsum").ewm_mean(half_life=QB_HALF_LIFE, adjust=True).over("qb_id")
            / pl.col("qdb").ewm_mean(half_life=QB_HALF_LIFE, adjust=True).over("qb_id")).alias("qb_form"),
           pl.int_range(1, pl.len() + 1).over("qb_id").alias("qb_starts")))
g = g.join(q.select("game_id", "franchise_id", "qb_form", "qb_starts"), on=["game_id", "franchise_id"], how="left")
g = g.with_columns((pl.col("qb_starts").fill_null(0) < QB_MIN_STARTS).alias("qb_new"),
                   pl.when(pl.col("qb_starts").fill_null(0) < QB_MIN_STARTS).then(0.0)
                     .otherwise(pl.col("qb_form")).alias("qb_trend"))
# snapshot: as-of join to the team's latest game (current QB = that game's primary passer);
# week 0 -> 0.0 (34% of seasons open with a different QB than last season's finale); carry qb_name/qb_new for display
```
"Starts" here means games as primary passer, including playoffs. A relief appearance where a QB led the team in dropbacks counts. That is the most honest proxy available without leakage.

### Pattern 4: Vectorized simulator (verified: 15 ms per snapshot, exact sums, deterministic)
```python
# Source: scratchpad/p5/sim.py
def simulate_season(sg, elo, week, n_sims=2000, seed=SEED, sigma=100.0):
    """sg: ONE season's REG games sorted (gameday, gametime, game_id); elo: {team: as-of rating at (season, week)}."""
    season = int(sg["season"][0]); teams = sorted(set(sg["home_id"]) | set(sg["away_id"])); T = len(teams)
    idx = {t: i for i, t in enumerate(teams)}
    div_id, conf_id = ...  # from season_config.divisions(season); assert every team has a division
    rng = np.random.default_rng([seed, season, week])            # per-snapshot stream -> order/incremental independent
    h = np.array([idx[t] for t in sg["home_id"]]); a = np.array([idx[t] for t in sg["away_id"]])
    known = sg["played"].to_numpy() & (sg["asof_week"].to_numpy() <= week)   # results known AS OF this week
    res = sg["result"].fill_null(0).to_numpy()
    kv = np.where(res > 0, 1.0, np.where(res < 0, 0.0, 0.5))    # ties count 0.5
    rem = ~known; G = len(h)
    u = rng.random((n_sims, int(rem.sum())))
    noise = rng.normal(0.0, sigma, (n_sims, T))                  # per-sim team offset, fixed within the run
    e = np.array([elo[t] for t in teams])
    diff = (e[h] - e[a] + np.where(sg["neutral"].to_numpy(), 0.0, hfa_for(season)))[None, :] + noise[:, h] - noise[:, a]
    out = np.empty((n_sims, G), np.float32); out[:, ~rem] = kv[~rem]
    out[:, rem] = u < 1 / (1 + 10 ** (-diff[:, rem] / 400))
    P = np.zeros((G, T*T), np.float32); Q = np.zeros_like(P)
    P[np.arange(G), h*T + a] = 1; Q[np.arange(G), a*T + h] = 1
    R = (out @ P + (1 - out) @ Q).reshape(n_sims, T, T)          # R[s,i,j] = i's wins over j
    Gm = np.zeros((T, T), np.float32); np.add.at(Gm, (h, a), 1); np.add.at(Gm, (a, h), 1)
    wins = R.sum(2); wpct = np.round(wins / Gm.sum(1), 9)        # win% (not wins): BUF/CIN 2022 played 16
    same_div = (div_id[:, None] == div_id[None, :]) & ~np.eye(T, dtype=bool)
    divpct = np.round((R * same_div).sum(2) / np.maximum((Gm * same_div).sum(1), 1), 9)
    rnd = rng.random((n_sims, T)); made = np.zeros((n_sims, T), bool)
    def top(m, v): return m & (v == np.where(m, v, -1).max(1, keepdims=True))
    def h2h(m):    # win% in games among the tied set; 0.5 if they never met
        hw = np.einsum("sij,sj->si", R, m.astype(np.float32)); hg = m.astype(np.float32) @ Gm.T
        return np.round(np.where(hg > 0, hw / np.maximum(hg, 1), 0.5), 9)
    for d in range(n_div):                                        # division winners
        m = top(np.broadcast_to(div_id == d, (n_sims, T)), wpct); m = top(m, h2h(m)); m = top(m, divpct)
        made[np.arange(n_sims), np.argmax(np.where(m, rnd, -1), 1)] = True
    for c in range(n_conf):                                       # wildcards, one at a time
        for _ in range(playoff_teams(season) // n_conf - n_div // n_conf):
            m = top((conf_id == c)[None, :] & ~made, wpct); m = top(m, h2h(m))
            made[np.arange(n_sims), np.argmax(np.where(m, rnd, -1), 1)] = True
    return made.mean(0), wins.mean(0)        # playoff_prob, exp_wins per team (teams order)
```
Era handling comes entirely from `season_config`. 1999–2001 has 31 teams in 6 divisions of 5/6 (3 division winners + 3 WC per conference). 2002–2019 has 4 + 2. 2020+ has 4 + 3. 2021+ has 17 games. All 609 snapshots pass Σp == spots. Memory per call: R is 2000×32×32 float32 = 8 MB.

### Pattern 5: vs_exp and po_trend (snapshot arithmetic)
```python
exp_total = coalesce(vegas_norm, model_week0_exp_wins)          # expectation_source = "vegas" | "model"
gp = wins + losses + ties                                         # REG, as-of (snapshot columns)
vs_exp = ((wins + 0.5*ties) - exp_total / reg_games(season) * gp) / max(gp, 1)   # week 0 -> 0 automatically
po_trend = playoff_prob(season, week) - playoff_prob(season, max(week - 3, 0))   # same season; null -> 0
vegas_norm = line - mean(line over season) + reg_games(season)/2  # books' lines sum to 252-265.5, not 256
```

### Pattern 6: sim cache + model_version
- `model_version = sha256(json.dumps({"elo": asdict(EloParams()), "hfa": HFA_BY_ERA, "divisions": [DIVISIONS_1999_2001, DIVISIONS_2002_ON], "playoff_teams": {s: playoff_teams(s) ...}, "n_sims": 2000, "sigma": 100.0, "seed": SEED, "sim": SIM_VERSION}, sort_keys=True))[:12]`.
- The hash covers *parameters*, not *data*. Schedule corrections in old seasons, or new results, change Elo and therefore the inputs. Store a per-season `input_digest` column (sha256 over the season's REG `(game_id, result, played, asof_week)` + snapshot `(week, franchise, round(elo, 9))`) and recompute exactly the seasons whose digest changed. On a normal weekly refresh that is only the current season (~10 snapshots, ~0.2 s).
- Full recompute is under 10 s, so a cold cache is never a problem. Keep the cache because CONTEXT wants it and because the backtest/leakage tests call derive repeatedly.

### Anti-Patterns to Avoid
- **Using `passer_player_id` for QB identity:** it drops every scramble (500–1,150 dropbacks/season). Use `passer_id` → `passer_player_id` → `rusher_player_id` (dropbacks only).
- **Counting spikes:** they have pass=1. Filter `qb_spike` explicitly. Kneels are already excluded by pass|rush, but filter them too for clarity.
- **Opponent adjustment from full-season opponent EPA:** leaks. Use the opponent's EWMA *shifted by one game* (strictly before this game).
- **A single RNG stream across all (season, week):** the results would depend on the computation order and on whether earlier weeks were computed. Use `default_rng([seed, season, week])`.
- **Simulating by wins instead of win%:** BUF/CIN 2022 played 16 games.
- **Week-label "remaining games":** use `played & asof_week <= week` as known, so postponed games behave like the rest of the pipeline.
- **Importing sim/efficiency from backtest or vice versa:** sim/efficiency must stay upstream modules. Add them to the firewall test's list.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| EWMA per group | Python loops | `pl.col(x).ewm_mean(half_life=h, adjust=True).over(key)` on sorted rows | Verified as-of (row i uses rows ≤ i only). Weighted EWMA = ewm(x·w)/ewm(w) |
| Full NFL tiebreakers (common games, SOV, SOS, multi-team sweep rules) | nflseedR port | CONTEXT's simplified chain | 98% slot accuracy at end of REG. Adding conference record didn't help. Error is ≈1 spot per 3 seasons, so disclose it on the methodology page |
| Ridge / walk-forward / alpha CV | anything new | `backtest._ridge_walk_forward`, `choose_alpha`, `propose_weights` | Phase 3/4 harness reproduces exactly |
| Win totals scraping | scraper | nfldata `win_totals.csv` | Frozen, 12.8 KB, clean |
| pbp caching | nflreadpy's cache | own parquet per season (`cache_mode="off"`, atomic write like `ingest.save_cache`) | Matches project convention |

## Common Pitfalls

### Pitfall 1: vs_exp's signal comes from Vegas, and 2021+ never has Vegas
**What goes wrong:** The weight (−1.24) is learned almost entirely on 2003–2020 Vegas-sourced rows. From 2021 on (the 2022–2025 holdout and live 2026), every row is model-sourced. In walk-forward, applying the mixed-trained weight to model-sourced vs_exp scores 0.5233, versus 0.5244 without vs_exp at all. The Phase 6 holdout will likely show vs_exp hurting slightly.
**How to avoid (within CONTEXT):** Keep the factor and tag the source as locked. Record **three** numbers in BACKTEST_LOG: Δ mixed (+0.0019), Δ model-only (−0.0006), deployment condition (−0.0011). Flag this for Phase 6, which may choose to fit vs_exp on model-sourced rows for consistency or to prioritize MODEL-V2-03 (hand-entered 2021+ totals). Expose `expectation_source` per row and on the methodology page.
**Warning signs:** a holdout per-factor drop concentrated in vs_exp.

### Pitfall 2: Offsetting season_record (+1.83) and vs_exp (−1.23) bars
corr 0.92 and VIF 19.8/9.8. A 6–2 team expected to go 6–2 gets a big + season_record bar and a moderate − vs_exp bar. Phrasebook: vs_exp+ "are beating preseason expectations", with the fade suffix because the weight is negative ("…(expectations usually catch up)"). season_record's weight more than doubles once vs_exp enters, and Phase 4's blurbs/tiers based on the old weights will shift.

### Pitfall 3: epa_traj's negative sign versus its UI label "Getting better"
Its weight is − in 19/19 folds. A team that is "getting better" in efficiency gets a small *negative* bar. Keep the label (CONTEXT), phrase it on raw direction plus the Phase 4 fade suffix ("has been trending up in efficiency (that tends to fade)"), and record it in the log. Don't flip the definition.

### Pitfall 4: qb_trend definition differs from CONTEXT's literal formula
CONTEXT says "Research finalizes". The literal formula (form − team season-to-date) is −0.0005 to −0.0010 at every half-life. The current QB's form level is +0.0028. Implement the level, keep the key `qb_trend`, label it "QB play (recent starts)", and log both deltas. The `qb_new` flag and the `<2 starts → 0` rule stay as specified.

### Pitfall 5: Leakage paths unique to this phase
- **Opponent adjustment:** shift(1) on the opponent's EWMA, as in Pattern 2.
- **Simulator:** known results must be `played & asof_week <= week`. Everything else is simulated, even if it was played later. The fake-future leakage test sets results without adding rows, so with per-snapshot RNG streams past sims are bit-identical (same remaining-game set and order). Verify with the existing `test_fake_future_games_change_nothing` and `test_truncating_future_keeps_past` once `playoff_prob`, `exp_wins`, `vs_exp`, `po_trend`, `epa_traj` and `qb_trend` are in `FEATURE_COLUMNS`/FLOAT_EXACT.
- **pbp in leakage tests:** `derive(raw)` currently only sees schedules. Pass `pbp_games` (team_game_epa) as an optional input. In the fake-future test, future games have no pbp rows, so EPA factors are unaffected by construction. Also add a test that appends fake pbp aggregates for future games and asserts the past is unchanged.
- **Vegas lines:** preseason by definition. Never derive expectations from in-season spreads (PITFALLS 1).
- **σ and the tiebreak chain** are hyperparameters chosen on ≤2021 data only.

### Pitfall 6: The 3 games with no pbp, and early-year gaps
1999_01_BAL_STL, 2000_03_SD_KC and 2000_06_BUF_MIA have scores but no plays. Use an inner join, so these games are absent from EWMA sequences (not 0). Checks should allow exactly this known list, the way `EXPECTED_GAME_EXCEPTIONS` does, and fail on any new gap. `qb_dropback` is null on ~1.2% of 1999–2000 plays, so treat null as not-a-dropback. These are the documented `low_confidence` years.

### Pitfall 7: Week 0 semantics differ per factor
At week 0: epa_traj → 0 (no in-season games), qb_trend → 0 (unknown starter), vs_exp → 0 (gp = 0), po_trend → 0 (p(0) − p(0)). playoff_prob/exp_wins at week 0 are the *preseason* sim. All four new factors therefore have z = 0 at week 0 (zero variance; `zscore` handles it). The week-0 blurb lead from Phase 4 still applies.

### Pitfall 8: Playoff-week snapshots
The grid includes weeks after REG (19–22). The sim there has no games left and is deterministic, but 13 coin-flip ties show 50% after the season ended. Recommendation (discretion): for display, once all of a season's REG games are played, override `playoff_prob` with actual participation (team appears in any non-REG game that season). It is known at that moment and fixes the visible mismatches. Keep the raw sim value as the factor input for consistency, or use the override for both (the difference is negligible).

### Pitfall 9: Alpha regime change
The CV-chosen alpha moves to 0.01·n once vs_exp joins. Several Phase 4 weights shrink (elo 3.76 → 2.59, sow −1.03 → −0.56). Every historical score and blurb shifts once. The frozen 1999–2021 reference is recomputed from the new composites, which is leak-free. This is expected and not a bug.

### Pitfall 10: Run time of leakage/backtest tests
Each `derive` on real data now includes ~10 s of sims (full history) unless cached. The leakage test derives three times. Pass a precomputed `sim` frame where possible, or accept ~30–40 s. Don't drop n_sims in tests below 500: the Σ checks still hold, but results get noisy.

## Code Examples

### New FACTORS entries (score.py)
```python
"epa_traj": {"label": "Getting better (efficiency trend)",
             "description": "Recent opponent-adjusted EPA per play (weighted toward the last ~4 games) minus this season's average"},
"qb_trend": {"label": "QB play (recent starts)",
             "description": "Current starting QB's EPA per dropback over his recent starts, on any team; 0 for a QB with under 2 starts or before week 1"},
"vs_exp":   {"label": "Vs preseason expectations",
             "description": "Win % so far minus the win % expected before the season (Vegas win total 2003-2020, otherwise the model's preseason projection)"},
"po_trend": {"label": "Playoff odds trend",
             "description": "Change in simulated playoff odds over the last 3 weeks"},
```

### Refresh flow (cli)
```python
# refresh: schedules (as today) -> pbp.load_pbp_season(current, refresh=True) (~1 s) -> team_game_epa (all cached seasons, 0.2 s)
#          -> derive (replay) -> sim: load cache[model_version], recompute seasons with changed input_digest (~0.2 s)
#          -> features/score/export
# build:   downloads missing pbp seasons (26 s cold), win_totals once, full sims (~10 s cold)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 7 factors (Phase 4 interim) | 11 factors | Phase 5 | Every score shifts. Alpha 0.001·n → 0.01·n |
| No pbp | 28 seasons of slim pbp cached (26 MB) | Phase 5 | First `fgs build` +26 s |
| No playoff odds | Sim cache per model_version | Phase 5 | Team page small stat "Playoff odds 87%" (integer) |

**Deprecated/outdated:** nflfastR's `passer_player_id` as QB identity for dropback stats (misses scrambles). Use `passer_id`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `qb_trend` implemented as the current QB's form *level* (not CONTEXT's literal "minus team season-to-date") is within "Research finalizes" | Pitfall 4 | Low. If the user insists on the literal form, Δ is −0.0005 and the weight is +0.20 |
| A2 | Per-sim rating offset σ=100 is compatible with "ratings fixed within a sim run, no hot updates" | Pattern 4 | Low. σ=0 is a one-line change. Brier 0.1263 → 0.1292, and overconfidence returns |
| A3 | Normalizing Vegas lines per season (Σ = games/2 × teams) is acceptable as "use win_totals" | Pattern 5 | Negligible (r unchanged) |
| A4 | Week-0 qb_trend = 0 (CONTEXT is silent on week 0) | Pattern 3 | Negligible (+0.0002 vs carry) |
| A5 | Post-REG playoff_prob display override with actual participation | Pitfall 8 | Cosmetic |
| A6 | The opponent adjustment uses the opponent's prior EWMA (h=4) of *raw* net EPA, not an iterated/fully adjusted rating | Pattern 2 | Low. The Elo-based adjustment was −0.0003, effectively equal |

## Open Questions (RESOLVED)

1. **Which opponent adjustment for epa_traj?**
   - RESOLVED: net_epa + opponent's EWMA(h=4) of raw net EPA over its games *strictly before* this game (shift 1, crossing seasons). Best Δ in the sweep (−0.0000 vs −0.0003 for the Elo-based adjustment and −0.0004 raw), leak-free by construction.
2. **EWMA half-life for epa_traj?**
   - RESOLVED: h=4 (CONTEXT default, best of 2/3/4/6/8). Trajectory beats level. Log the level delta (−0.0019) as CONTEXT requests.
3. **Trajectory has no signal. Switch to level or level + trajectory?**
   - RESOLVED: no. Both are worse (level −0.0019, level+traj −0.0020). Keep the trajectory as defined. Its fitted weight is negative (−0.20, 19/19 folds). Report this honestly.
4. **qb_trend final definition?**
   - RESOLVED: current QB's dropback-weighted EWMA (h=4) of EPA/dropback over his own starts (any team, any season, incl. playoffs). Current QB = primary passer of the team's latest game as of the snapshot. <2 starts → 0 with `qb_new=true`. Week 0 → 0. Δ +0.0028. Log the literal-definition Δ (−0.0005).
5. **How to identify the primary passer?**
   - RESOLVED: most wp-filtered dropbacks per (game, team), with id = coalesce(passer_id, passer_player_id, rusher_player_id on dropbacks), ties broken by id. Agreement with the schedule starter is 96–98%. Keep the schedule `*_qb_id` as a check-only metric (e.g. an informational `checks` line), not a hard failure.
6. **Simulator runtime: is caching needed for performance?**
   - RESOLVED: no (15 ms per snapshot, <10 s full history). Cache anyway (CONTEXT) with model_version + per-season input digest so incremental refresh recomputes only changed seasons.
7. **Tiebreaker fidelity: add more rules?**
   - RESOLVED: no. The CONTEXT chain gives 17 wrong slots in 27 seasons at end of REG. Adding conference record gave 19. Disclose "simplified tiebreakers, about one playoff spot every three seasons differs" on the methodology page.
8. **Fixed ratings are overconfident. Fix?**
   - RESOLVED: per-sim team rating offset N(0, 100 Elo), drawn once per sim (ratings constant within the run). Brier 0.1292 → 0.1263. The 0.8–0.9 bin goes 0.850/0.771 → 0.849/0.858.
9. **Where do win totals come from?**
   - RESOLVED: `nflverse/nfldata` `data/win_totals.csv` over raw GitHub (not in nflreadpy). 2003–2020, legacy codes mapped via RAW_TO_FRANCHISE, lines normalized per season. Model-vs-Vegas r = 0.863 (target 0.7–0.8 met).
10. **vs_exp works only with Vegas. What do we do in v1?**
    - RESOLVED: keep it as locked. Log Δ mixed (+0.0019), Δ model-only (−0.0006) and deployment-condition (−0.0011). Raise it as a Phase 6 decision item and as evidence for MODEL-V2-03.
11. **po_trend ≈ 0. Keep it?**
    - RESOLVED: yes, per CONTEXT. Weight −0.01, Δ −0.0003. corr with the 3-week Elo change is 0.70 (lower than PITFALLS' >0.9 guess, because the schedule and division races add variance).
12. **Display of playoff odds?**
    - RESOLVED: export `playoff_prob` as an integer percent per row (no decimals rule). Team page small stat. Post-REG override as in Pitfall 8 (discretion).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | pipeline | ✓ | 0.10.12 | — |
| Python | pipeline | ✓ | 3.13 | — |
| nflreadpy `load_pbp` (network → GitHub releases) | DATA-05 | ✓ | 0.1.5 | — |
| raw.githubusercontent.com (win_totals) | MODEL-08 | ✓ | — | vendor the 12.8 KB CSV into the repo |
| Disk for pbp cache | DATA-05 | ✓ | 26 MB | — |
| Node (web) | team-page stat | ✓ via nvm (22) | — | — |

**Missing dependencies:** none. **Side effects of this research:** none in the project. Downloads went only to the scratch dir.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.2 (pipeline); vitest + svelte-check (web) |
| Config file | `pipeline/pyproject.toml [tool.pytest.ini_options]`; `web/package.json` |
| Quick run command | `cd pipeline && uv run pytest -q tests/test_pbp.py tests/test_efficiency.py tests/test_sim.py tests/test_features.py` |
| Full suite command | `cd pipeline && uv run pytest -q && cd ../web && source ~/.nvm/nvm.sh && nvm use && npm test && npm run check && npm run build` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-05 | `scrimmage` keeps pass/rush in wp [0.05, 0.95], drops spikes, kneels, no_play, null EPA, empty posteam | unit (synthetic plays) | `uv run pytest tests/test_pbp.py -k scrimmage -x` | ❌ Wave 0 |
| DATA-05 | `team_game_epa`: off/def/net hand-computed; primary QB = most dropbacks, scramble counted via passer_id fallback, tie → lowest id; low_confidence iff season ≤ 2000 | unit | `uv run pytest tests/test_pbp.py -k team_game -x` | ❌ Wave 0 |
| DATA-05 | Real cache: codes ⊆ CANONICAL; played games without pbp == known 3; rows == 2 × pbp games | integration (real_cache, skip if absent) | `uv run pytest tests/test_pbp.py -k real -x` | ❌ Wave 0 |
| MODEL-05 | adj_epa uses the opponent's *prior* EWMA (game 1 → opp term 0); epa_traj = EWMA − season mean; week 0 / no in-season games → 0; no-pbp game skipped | unit (hand-computed 3-game league) | `uv run pytest tests/test_efficiency.py -k epa_traj -x` | ❌ Wave 0 |
| MODEL-11 | qb_form follows the QB across teams/seasons; dropback-weighted; <2 starts → 0 + qb_new; week 0 → 0; QB change switches history | unit | `uv run pytest tests/test_efficiency.py -k qb -x` | ❌ Wave 0 |
| MODEL-13 | Σp == playoff_teams(season) for 1999 (31 teams, 12), 2010, 2020 (14), 2021 (17 games); Σexp_wins == REG games; deterministic for same (seed, season, week); input-order independent | unit (synthetic + real) | `uv run pytest tests/test_sim.py -x` | ❌ Wave 0 |
| MODEL-13 | Tiebreak chain on a hand-built 4-team division with forced outcomes (Elo ±2000, σ=0): h2h decides, then division %, then random ≈50/50 | unit | `uv run pytest tests/test_sim.py -k tiebreak -x` | ❌ Wave 0 |
| MODEL-13 | End-of-REG real seasons: ≥ 97% of team-slots match actual playoff participants (1999–2021) | integration (real) | `uv run pytest tests/test_sim.py -k field -x` | ❌ Wave 0 |
| MODEL-13 | model_version changes when n_sims/σ/Elo K/HFA changes; cache recomputes only digest-changed seasons | unit | `uv run pytest tests/test_sim.py -k version -x` | ❌ Wave 0 |
| MODEL-08 | win_totals mapping (OAK→LV, SD→LAC, STL→LA), per-season normalization, source tag vegas 2003–2020 / model otherwise; vs_exp formula hand-computed incl. ties, week 0 → 0 | unit | `uv run pytest tests/test_features.py -k vs_exp -x` | ❌ Wave 0 |
| MODEL-08 | r(model wk-0 exp_wins, Vegas) on 2003–2020 ≥ 0.7 | integration (real) | `uv run pytest tests/test_sim.py -k vegas_corr -x` | ❌ Wave 0 |
| MODEL-12 | po_trend = p(w) − p(max(w−3, 0)) same season; week 0 → 0 | unit | `uv run pytest tests/test_features.py -k po_trend -x` | ❌ Wave 0 |
| All | Fake-future/truncation leave epa_traj, qb_trend, vs_exp, po_trend, playoff_prob, exp_wins unchanged; fake future pbp aggregates change nothing; sim/efficiency/pbp never import backtest | integration | `uv run pytest tests/test_leakage.py -x` | ✅ extend |
| All | Report has ridge:+epa_traj … +po_trend; final N=8 Spearman in [0.523, 0.529]; BACKTEST_LOG has 4 new rows; weights.yaml loads 11 keys | integration + grep | `uv run pytest tests/test_backtest.py -x` | ✅ extend |
| Export | rows carry playoff_prob (int 0–100) + expectation_source; meta.factors has 11 entries; Σ points still == score − baseline | contract | `uv run pytest tests/test_export.py -x` | ✅ extend |

### Sampling Rate
- **Per task commit:** the quick run command.
- **Per factor step:** `uv run fgs backtest --propose-weights`, then compare against the Prototype Results table (±0.002).
- **Per wave merge:** full pipeline suite plus web tests.
- **Phase gate:** full suite green. `uv run fgs build` (cold: pbp 26 s + sims ~10 s) and `uv run fgs refresh` complete in under 2 min. Team page shows 11 factor bars and the playoff-odds stat. Then `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_pbp.py`: synthetic play frame fixture (≈20 plays over 2 games incl. spike, kneel, no_play, scramble with null passer_player_id, wp 0.97 play)
- [ ] `tests/test_efficiency.py`: 3-team, 2-season per-game fixture with known EPA values and a QB who changes teams
- [ ] `tests/test_sim.py`: tiny-league fixture with monkeypatched `divisions`/`playoff_teams` (the conftest pattern already monkeypatches season_config)
- [ ] Extend `test_leakage.py` FLOAT_EXACT via `features.FEATURE_COLUMNS`; extend the firewall list with `pbp.py`, `efficiency.py`, `sim.py`, `expectation.py`
- [ ] No framework installs

## Security Domain

`security_enforcement: false` in `.planning/config.json`, so this section is omitted. The only external fetches are nflverse GitHub assets over HTTPS into the gitignored cache.

## Sources

### Primary (HIGH confidence)
- Prototype runs in this session (scratchpad/p5): pbp download/quality, team-game aggregation, ~40 epa_traj variants, 16 qb variants, simulator runtime/sums/determinism/calibration/σ sweep/tiebreak accuracy, win totals r, walk-forward chain, fold signs, alpha sensitivity, VIF, deployment-mismatch test
- `nflreadpy.load_pbp` signature and docstring via `inspect` (v0.1.5); data dictionary link https://nflreadr.nflverse.com/articles/dictionary_pbp.html
- nflverse/nfldata `data/win_totals.csv` (downloaded; GitHub API: last commit 2021-07-29 "Automated data update") — https://github.com/nflverse/nfldata
- Codebase: `pipeline/src/fgs/{season_config,elo,features,score,backtest,games,snapshots,ingest,franchises,cli}.py`, `tests/{test_leakage,conftest}.py`, `weights.yaml`, `BACKTEST_LOG.md`; 04-RESEARCH.md; PITFALLS.md (Pitfalls 1, 7, 9)

### Secondary (MEDIUM confidence)
- Web search for win-totals provenance (no direct hit; confirmed via the GitHub repo listing instead): e.g. [Rotowire win-totals analysis](https://www.rotowire.com/article/nfl-win-totals-what-data-tells-us-105750) and [numberFire on predictiveness of win totals](https://m.numberfire.com/nfl/news/37309/nfl-betting-how-predictive-are-preseason-win-totals-and-super-bowl-odds). Context only, not used for any number

## Metadata

**Confidence breakdown:**
- pbp facts and aggregation: HIGH (measured on all 1.3M plays)
- Factor deltas and signs: HIGH for the harness (base reproduces exactly). Effects are small (±0.003), so planners should expect the implementation to reproduce them within ±0.001 only if definitions match exactly
- Simulator design/runtime/calibration: HIGH
- vs_exp deployment risk: HIGH (measured directly)

**Research date:** 2026-11-11
**Valid until:** weights/factor definitions change (Phase 6 refit), or nflverse changes the pbp schema

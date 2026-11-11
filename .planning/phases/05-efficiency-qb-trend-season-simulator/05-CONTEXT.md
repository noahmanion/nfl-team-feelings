# Phase 5: Efficiency, QB Trend & Season Simulator - Context

**Gathered:** 2026-11-11
**Status:** Ready for planning (research REQUIRED — flagged in ROADMAP)
**Mode:** Autonomous — recommended answers auto-accepted (user granted full autonomy)

<domain>
## Phase Boundary

Add play-by-play efficiency data and four more factors — efficiency trajectory (the "WAR improvement" proxy), starting-QB trend, performance vs preseason expectation, playoff-odds trend — plus a Monte Carlo season simulator that produces weekly playoff odds and preseason expected wins. Each factor is added one at a time with a recorded backtest delta and fitted sign (training ≤2021; 2022–2025 holdout sealed). Weight freeze + holdout evaluation is Phase 6.

</domain>

<decisions>
## Implementation Decisions

### Play-by-play data (DATA-05)
- Load via `nflreadpy.load_pbp(season)` per season 1999→current; immediately slim to needed columns and cache as `pipeline/data/cache/pbp/{season}.parquet` (refresh re-downloads only the current season). Never commit pbp.
- Per team-game aggregates in `pipeline/data/derived/team_game_epa.parquet`: offensive EPA/play, defensive EPA/play allowed, net EPA/play, plays count; garbage-time filter keeps plays with win probability between 0.05 and 0.95 (use `wp`; exclude QB kneels/spikes, no-plays). QB: for the team's primary passer that game (most dropbacks): dropback EPA/play, success rate, dropbacks, passer id/name.
- 1999–2000 flagged `low_confidence=true` (nflfastR dropped official support; ~1% null EPA) — included but flagged in data and methodology.
- Map pbp team codes through the existing franchise map (pbp is already normalized per Phase-1 research — assert it).

### Efficiency trajectory factor `epa_traj` (MODEL-05)
- Opponent-adjusted net EPA/play per game = team net EPA/play − (opponent's as-of season-to-date net EPA/play allowed-adjustment); exact adjustment chosen by research (must be as-of, no leakage).
- Factor = EWMA of adjusted net EPA/play (half-life ~4 games, crossing season boundary) MINUS the team's season-to-date mean (trajectory, not level). Week 0 / no games → 0. Research may propose level+trajectory if trajectory alone has no signal — record both deltas.

### QB trend factor `qb_trend` (MODEL-11)
- Tracks the CURRENT starting QB (from the latest game's primary passer; schedule `home_qb_name/away_qb_name` as cross-check): EWMA of his dropback EPA over his last ~6 starts (any team, any season) minus the team's season-to-date QB dropback EPA. If the QB changed, the new QB's own history drives it (QB with <2 career starts in data → 0 with a `qb_new` flag). Research finalizes.

### Season simulator (MODEL-13)
- Vectorized NumPy Monte Carlo per (season, week): simulate all remaining REG games using as-of Elo win probabilities with era HFA (ratings fixed within a sim run, no hot updates in v1), then apply era rules from `season_config` (divisions, 12 vs 14 playoff teams, 16 vs 17 games) with simplified tiebreakers: division winner by win% → head-to-head win% → division win% → random; wildcards by win% → head-to-head (if applicable) → random. Default 2,000 sims; seeded RNG for determinism.
- Outputs per (season, week, franchise): `playoff_prob`, `exp_wins` (final REG wins). Week-0 sim = preseason expected wins. Cached in `pipeline/data/derived/sim/{model_version}.parquet` keyed by (season, week, franchise); `model_version` = hash of Elo params + era config + n_sims + simulator code version.
- Sanity checks: per week Σ playoff_prob ≈ number of playoff spots; exp_wins sums to total games/2 per season (ties aside).

### vs-expectation factor `vs_exp` (MODEL-08)
- Expected win% to date = preseason expected wins / games in season (constant per season); factor = actual REG win% to date − expected win% (weighted by games played: (wins − exp_wins_per_game × games)/max(games,1)). Week 0 → 0.
- Expectation source: nflverse `win_totals` (2003–2020) where available (tag `vegas`), else model week-0 sim (tag `model`). Every row carries `expectation_source`. Validate model-vs-Vegas correlation on 2003–2020 (target r ≈ 0.7–0.8) and report it.
- No hand-entered 2021+ Vegas totals in v1 (v2 requirement).

### Playoff-odds trend factor `po_trend` (MODEL-12)
- Factor = playoff_prob(now) − playoff_prob(3 weeks earlier within season; week 0 if fewer). Included in the score with its fitted weight reported even if ≈0.

### Process
- Add order: epa_traj → qb_trend → vs_exp → po_trend, each: feature + hand-computed test, refit interim walk-forward Ridge (≤2021), `fgs backtest`, append BACKTEST_LOG row (Δ, sign), update weights.yaml, regenerate site data. Team page shows new factors automatically (Phase 4 made it factor-agnostic); meta.factors gets labels/descriptions; blurb phrasebook gains entries for the 4 new factors.
- Leakage test must cover new factors (pbp/sim as-of). Simulator runtime must keep `fgs refresh` reasonable (target < 2 min incremental; full historical sim may be longer but cached).
- `fgs refresh` downloads current-season pbp + recomputes current season sims only.

### Claude's Discretion
- Module layout (`pbp.py`, `efficiency.py`, `sim.py`), exact EWMA spans after research, sim vectorization strategy, cache format.

</decisions>

<code_context>
## Existing Code Insights

- Phase 4 makes the team page and blurbs factor-agnostic; `explain.py` phrasebook keyed by factor; `features.py` + `score.py` + walk-forward Ridge + `weights.yaml` + `BACKTEST_LOG.md`; `season_config` has era rules incl. divisions and playoff team counts; `elo.replay` gives as-of ratings and pre-game ratings.

</code_context>

<specifics>
## Specific Ideas

- `epa_traj` is the user's "WAR improvements" idea — label it "Getting better (efficiency trend)" in the UI.
- Playoff odds can also be displayed on the team page (small stat), since they're computed anyway.

</specifics>

<deferred>
## Deferred Ideas

- Hand-entered 2021+ Vegas win totals (v2), free agency (v2), in-sim Elo hot updates (later).

</deferred>

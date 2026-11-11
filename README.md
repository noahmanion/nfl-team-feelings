# feel-good-score

How should NFL fans *actually* feel about their team? This project builds a momentum-weighted, Elo-like "feel-good score" for every team since 1999 and backtests it against future results. It's a reality check for fanbases that think their team is worse (or better) than it is. Right now the score is a weighted, backtested blend of eleven factors (results, efficiency, QB play, preseason expectations and playoff odds), shown as a mood board, a mood-over-time chart and a page per team in a small local site.

## Run it

**Refresh data** (once a week, after games finish):

```bash
cd pipeline
uv run fgs refresh    # re-download nflverse, run every check, regenerate web/public/data (writes nothing if a check fails)
uv run fgs export     # rebuild the site JSON from the local cache, no network
```

**Start the site:**

```bash
cd web
nvm use && npm install   # once; Node >=22.12, pinned by web/.nvmrc
npm run dev              # the one command after that
```

The generated JSON in `web/public/data/` is committed, so the site runs without Python.

**Other pipeline commands:**

```bash
cd pipeline
uv run fgs build                         # download (once) + derive games, team_games, elo_snapshots, sims, features
                                         # first run also downloads nflverse play-by-play 1999+ (~26 s)
uv run fgs check                         # data-trust checks; exit 1 on failure
uv run fgs elo                           # ranked Elo + W-L-T for the latest played week, with a "data through" date
uv run fgs elo --season 2008 --week 5    # as of any (season, week); week 0 = preseason (regressed) ratings
uv run fgs backtest                      # walk-forward backtest (2003–2021) of the score vs baselines
uv run fgs backtest --propose-weights    # also print ridge weights fit on 1999–2021, ready for weights.yaml
```

`fgs backtest --include-holdout` also scores the sealed 2022–2025 seasons. It's reserved for Phase 6.

- Data is cached in `pipeline/data/` (gitignored). `fgs refresh` or `uv run fgs ingest --refresh` re-downloads it.
- Records are regular-season only. Playoff games move Elo but not W-L-T, and ties count as half a win.
- nflverse `location` coding is used as-is, so the Bills' Toronto games (2009–2012) and the Saints' 2005 relocation games count as home games.

## How the score works today

- The score is an integer from 0 to 100. Each factor is z-scored across all teams in the same week, multiplied by its weight in `pipeline/weights.yaml`, and the products are summed. The score is that sum's percentile.
- Factors and frozen weights (points of future adjusted margin per standard deviation). They were fit on 1999–2021 and frozen on 2026-11-11 (`pipeline/weights.yaml`, `frozen: true`). The weekly refresh never refits them. The fold counts say how many of the 19 walk-forward seasons (2003–2021) agree with the final sign. The methodology page at `#/methodology` shows the evidence.
  - **Elo** (`elo`) 2.59 (19/19): game-by-game strength rating.
  - **Season record** (`season_record`) 1.84 (19/19): this season's regular-season win %, ties count half.
  - **Last 16 games** (`last16`) −0.21 (14/19): win % over the last 16 games, across seasons, playoffs included.
  - **Margin of victory** (`mov`) 1.24 (19/19): average point margin over the last 8 games, each capped at 24.
  - **Quality of results** (`sow`) −0.56 (14/19): results over the last 8 games vs what an average team would do against the same opponents.
  - **Streak** (`streak`) −0.03 (12/19): current win or loss streak, ties end it, capped at 8.
  - **Close-game luck** (`luck`) −0.35 (19/19): one-score wins minus one-score losses (8 points or fewer) over the last 16 games.
  - **Efficiency trend** (`epa_traj`) −0.33 (19/19): recent opponent-adjusted EPA per play (weighted to the last ~4 games) minus this season's average. Honest verdict: it adds about nothing to the backtest and its sign is negative (an efficiency upswing slightly fades once everything else is known). It stays in so its weight is on record.
  - **QB play** (`qb_trend`) 0.63 (19/19): the current starter's EPA per dropback over his recent starts, on any team. The biggest Phase 5 gain (+0.0028 Spearman). 0 for a QB with fewer than 2 starts.
  - **Vs preseason expectations** (`vs_exp`) −1.22 (18/19): win % so far minus the preseason expectation's pace. Read it together with season record (they correlate 0.92): beating expectations tends to fade. Caveat: the expectation is the Vegas win total for 2003–2020 and the model's own preseason projection otherwise, so the signal is learned mostly on Vegas years while 2021+ is always model-sourced. On model-only inputs it is slightly negative. On the holdout, zeroing it barely changes the result (see below).
  - **Playoff odds trend** (`po_trend`) −0.05 (17/19): change in simulated playoff odds over the last 3 weeks. ≈0: it mostly repeats the 3-week Elo change (correlation 0.70). Kept so its weight is reported.
- Several weights are negative on purpose. Once Elo and margins are known, a record that runs ahead of them (hot last 16, results beating margins, a long streak, lots of coin-flip wins) tends to regress, so it predicts slightly *worse* future margins. An 8-2 team that won six one-score games should feel a little worried. Each factor's backtest gain and fitted sign are logged in `pipeline/BACKTEST_LOG.md`.
- The efficiency and QB factors use nflverse play-by-play since 1999. The 1999–2000 seasons are flagged low-confidence (thinner data, a few games missing).
- **Playoff odds.** Each week, 2,000 simulations play out the rest of the season from Elo, with per-simulation rating noise (σ = 100 Elo points) so a team's strength is uncertain too. Era rules apply (6 playoff teams per conference through 2019, 7 from 2020; 16 or 17 games). Tiebreakers are simplified (win % → head-to-head → division record → coin flip), so the simulated field differs from the real one about one spot every three seasons. The model's preseason expected wins correlate 0.86 with Vegas win totals (2003–2020). Once the regular season is over, the team page shows the actual result (100% or 0%) instead of a simulation.
- Percentiles compare against every preseason and regular-season team-week from 1999–2021. That reference is fixed, so a historical score never shifts after a refresh. A test checks that future games can't move a past score.
- Seven mood bands turn the score into a label. A team's label only changes once its score is 2 points into the new band, going up or down. For the 60 edge, a team rises to the higher label at 61 and drops to the lower one at 58. Scores of 59 and 60 keep whatever label it already had, so labels don't flicker.
- **Team page.** Click any row on the board (or open `#/team/{ABBR}`, e.g. `#/team/BUF`) to see why a team's score is what it is. The bars are score points: they start at "Average team {baseline}" and add up to the team's score. The header also shows the playoff odds as a whole percent and the current starting QB. A one-line blurb names the biggest reasons (e.g. a skid, or coin-flip luck that tends to even out), with recent games and a score sparkline below.
- A partially played week (e.g. Monday night still to come) is flagged. Teams that haven't played yet keep last week's Elo.

## Backtest target

This target was written down before any score weights were fit. Weights get tuned against it, not the other way round.

- **What it predicts.** For every team at every (season, week), the target is the mean **adjusted margin** over the team's next N games in the same season, regular season and playoffs. N = 8 is the headline number; N = 4 is reported too. Snapshots with fewer than 2 games left that season are skipped.
- **Adjusted margin** = actual point margin + (opponent's pre-game Elo − 1505) / 25 − (signed home-field Elo) / 25. Home-field is +HFA at home, −HFA away, 0 at a neutral site. Beating a strong team on the road counts for more than beating a weak one at home.
- **Only who you played and where.** The adjustment never uses the team's own rating. Subtracting your own Elo turns the target into "beat Elo's expectation", and then plain Elo scores a Spearman of about 0.02 instead of about 0.51 (research measurement, 2003–2021, N=8). That would make every rating look useless by construction.
- **Metrics.** Spearman rank correlation and R² (squared Pearson) between the score and the target, pooled over test seasons and per season. Next-game Brier score is a secondary metric. Everything is also split into week 0, weeks 1–6, 7–12 and 13+ (including playoffs).
- **Walk-forward by season.** Anything fit for test season S uses only earlier seasons. The first test season is 2003.
- **Sealed holdout.** Seasons 2022–2025 were held out of every fit. They were evaluated once, on 2026-11-11T21:22:06Z, by `uv run fgs holdout` under the rules in `pipeline/PREREGISTRATION.md` (see below). `fgs backtest --include-holdout` is allowed now only because that result exists. The 2026 season in progress is never a test season.

## Does it work? (2022–2025 holdout)

**Yes, slightly: better than Elo alone on 2022–25, but within the noise of four seasons.** BACK-06: PASS (the score − Elo Spearman at N=8 is > 0). The rules and the wording of this verdict were committed before the run.

| Candidate | Spearman N=8 [team-season 95% CI] | Next-game Brier |
|---|---|---|
| Feel-good score (frozen) | 0.485 [0.385, 0.572] | 0.2242 |
| Elo alone | 0.481 [0.377, 0.569] | 0.2228 |
| Season win % | 0.389 [0.294, 0.470] | 0.2364 |
| Last 16 games | 0.439 [0.336, 0.531] | 0.2261 |
| Point differential | 0.450 [0.347, 0.533] | 0.2342 |
| Vegas spread | — | 0.2097 |

- **Score − Elo, Spearman N=8:** +0.004. Season-block CI [−0.023, +0.029], team-season CI [−0.021, +0.031]. The score beat Elo in 2 of 4 seasons (2022 +0.029, 2023 +0.033, 2024 −0.013, 2025 −0.027). At N=4 it is −0.001.
- **Next-game Brier:** the score is slightly worse than Elo (+0.0014, season-week CI [−0.0018, +0.0044]) and clearly worse than the Vegas spread (+0.0145). Lower is better.
- **vs_exp diagnostic (pre-registered):** with vs_exp zeroed, Spearman N=8 is 0.485 and the gap over Elo is +0.003 (CI [−0.025, +0.032]). The vs_exp source switch doesn't explain the narrow margin.
- Bottom line: the score ranks teams about as well as Elo, and a hair better at N=8. Nothing was re-tuned after the result.
- Full result: `pipeline/HOLDOUT_RESULT.md`.
- **Provenance gap.** The result records the sha256 of `PREREGISTRATION.md` and `weights.yaml`, the git HEAD and a clean `pipeline/src`. It does not fingerprint the input data (the nflverse cache and sim cache) or `uv.lock`, so it can't be re-verified against the exact bytes it ran on. Future `fgs holdout` runs record those hashes too.
- `fgs holdout --force` exists but don’t: re-running the holdout breaks the pre-registration.

**Status:** Phase 6 is done: weights frozen, 2022–2025 holdout evaluated once (verdict: slight), methodology page. Next is Phase 7: draft-aware offseason.

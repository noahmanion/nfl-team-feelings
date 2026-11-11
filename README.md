# feel-good-score

How should NFL fans *actually* feel about their team? This project builds a momentum-weighted, Elo-like "feel-good score" for every team since 1999 and backtests it against future results. It's a reality check for fanbases that think their team is worse (or better) than it is. Right now the score is a weighted, backtested blend of seven factors, shown as a mood board, a mood-over-time chart and a page per team in a small local site.

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
uv run fgs build                         # download (once) + derive games, team_games, elo_snapshots, features
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
- Factors and current weights (points of future adjusted margin per standard deviation, interim until Phase 6):
  - **Elo** (`elo`) 3.75: game-by-game strength rating.
  - **Season record** (`season_record`) 0.90: this season's regular-season win %, ties count half.
  - **Last 16 games** (`last16`) −0.56: win % over the last 16 games, across seasons, playoffs included.
  - **Margin of victory** (`mov`) 1.34: average point margin over the last 8 games, each capped at 24.
  - **Quality of results** (`sow`) −1.07: results over the last 8 games vs what an average team would do against the same opponents.
  - **Streak** (`streak`) −0.14: current win or loss streak, ties end it, capped at 8.
  - **Close-game luck** (`luck`) −0.30: one-score wins minus one-score losses (8 points or fewer) over the last 16 games.
- Four weights are negative on purpose. Once Elo and margins are known, a record that runs ahead of them (hot last 16, results beating margins, a long streak, lots of coin-flip wins) tends to regress, so it predicts slightly *worse* future margins. An 8-2 team that won six one-score games should feel a little worried. Each factor's backtest gain and fitted sign are logged in `pipeline/BACKTEST_LOG.md`.
- Percentiles compare against every preseason and regular-season team-week from 1999–2021. That reference is fixed, so a historical score never shifts after a refresh. A test checks that future games can't move a past score.
- Seven mood bands turn the score into a label. A team's label only changes once its score is 2 points into the new band, going up or down. For the 60 edge, a team rises to the higher label at 61 and drops to the lower one at 58. Scores of 59 and 60 keep whatever label it already had, so labels don't flicker.
- **Team page.** Click any row on the board (or open `#/team/{ABBR}`, e.g. `#/team/BUF`) to see why a team's score is what it is. The bars are score points: they start at "Average team {baseline}" and add up to the team's score. A one-line blurb names the biggest reasons (e.g. a skid, or coin-flip luck that tends to even out), with recent games and a score sparkline below.
- A partially played week (e.g. Monday night still to come) is flagged. Teams that haven't played yet keep last week's Elo.

## Backtest target

This target was written down before any score weights were fit. Weights get tuned against it, not the other way round.

- **What it predicts.** For every team at every (season, week), the target is the mean **adjusted margin** over the team's next N games in the same season, regular season and playoffs. N = 8 is the headline number; N = 4 is reported too. Snapshots with fewer than 2 games left that season are skipped.
- **Adjusted margin** = actual point margin + (opponent's pre-game Elo − 1505) / 25 − (signed home-field Elo) / 25. Home-field is +HFA at home, −HFA away, 0 at a neutral site. Beating a strong team on the road counts for more than beating a weak one at home.
- **Only who you played and where.** The adjustment never uses the team's own rating. Subtracting your own Elo turns the target into "beat Elo's expectation", and then plain Elo scores a Spearman of about 0.02 instead of about 0.51 (research measurement, 2003–2021, N=8). That would make every rating look useless by construction.
- **Metrics.** Spearman rank correlation and R² (squared Pearson) between the score and the target, pooled over test seasons and per season. Next-game Brier score is a secondary metric. Everything is also split into week 0, weeks 1–6, 7–12 and 13+ (including playoffs).
- **Walk-forward by season.** Anything fit for test season S uses only earlier seasons. The first test season is 2003.
- **Sealed holdout.** Seasons 2022–2025 are a holdout that `fgs backtest` only touches with `--include-holdout`. The 2026 season in progress is never a test season.

**Status:** Phase 4 is done: game-result factors (margin, quality of results, streak, close-game luck) and team pages. Next is Phase 5: efficiency, QB trend and a season simulator.

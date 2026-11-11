# feel-good-score

How should NFL fans *actually* feel about their team? This project builds a momentum-weighted, Elo-like "feel-good score" for every team since 1999 and backtests it against future results. It's a reality check for fanbases that think their team is worse (or better) than it is. Right now the score is Elo only, shown as a mood board in a small local site.

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
uv run fgs build                         # download (once) + derive games, team_games, elo_snapshots
uv run fgs check                         # data-trust checks; exit 1 on failure
uv run fgs elo                           # ranked Elo + W-L-T for the latest played week, with a "data through" date
uv run fgs elo --season 2008 --week 5    # as of any (season, week); week 0 = preseason (regressed) ratings
```

- Data is cached in `pipeline/data/` (gitignored). `fgs refresh` or `uv run fgs ingest --refresh` re-downloads it.
- Records are regular-season only. Playoff games move Elo but not W-L-T, and ties count as half a win.
- nflverse `location` coding is used as-is, so the Bills' Toronto games (2009–2012) and the Saints' 2005 relocation games count as home games.

## How the score works today

- The score is an integer from 0 to 100: the percentile of a team's Elo against every preseason and regular-season team-week since 1999.
- Seven mood bands turn the score into a label. A team has to move 2 points past a band edge to change label, so labels don't flicker.
- The reference set includes the current season, so a historical score can shift by 1 point after a refresh.
- A partially played week (e.g. Monday night still to come) is flagged. Teams that haven't played yet keep last week's Elo.

**Status:** Phase 2 is done: an Elo-only mood board with week scrubbing and deep links. Next is Phase 3: the backtest harness and the additive score.

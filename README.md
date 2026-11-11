# feel-good-score

How should NFL fans *actually* feel about their team? A momentum-weighted, Elo-like "feel-good score" for every team since 1999, built from record, last-16 games, efficiency trend, strength of win, opponent quality, expectations and more, then backtested so it predicts future performance. It's a reality check for fanbases that think their team is worse (or better) than it is.

## Pipeline

```bash
cd pipeline
uv run fgs build                         # download (once) + derive games, team_games, elo_snapshots
uv run fgs check                         # data-trust checks (team counts, games, codes, continuity, Elo, weekly grid); exit 1 on failure
uv run fgs elo                           # ranked Elo + W-L-T for the latest played week, with a "data through" date
uv run fgs elo --season 2008 --week 5    # as of any (season, week); week 0 = preseason (regressed) ratings
```

- `fgs elo` refuses weeks that haven't been played yet, and flags a partially played week (e.g. Monday night still to come).
- Records are regular-season only; playoff games move Elo but not W-L-T. Ties count as half a win.

- Data is cached in `pipeline/data/` (gitignored). Re-runs read the cache; `uv run fgs ingest --refresh` re-downloads.
- nflverse `location` coding is used as-is, so the Bills Toronto games (2009–2012) and the 2005 Saints relocation games count as home games.

Later: a Vite + Svelte site (`web/`) renders static JSON written by the pipeline.

**Status:** Phase 1 done: clean 1999→now data, data checks, and a weekly Elo grid; next is the Elo mood board site (Phase 2).

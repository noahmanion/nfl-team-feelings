# feel-good-score

How should NFL fans *actually* feel about their team? A momentum-weighted, Elo-like "feel-good score" for every team since 1999, built from record, last-16 games, efficiency trend, strength of win, opponent quality, expectations and more, then backtested so it predicts future performance. It's a reality check for fanbases that think their team is worse (or better) than it is.

## Pipeline

```bash
cd pipeline
uv run fgs build                                # download (once) + derive games, team_games, elo_snapshots
uv run fgs elo --season 2026 --week 9 --top 10  # ranked Elo + W-L-T as of that week
```

- Data is cached in `pipeline/data/` (gitignored). Re-runs read the cache; `uv run fgs ingest --refresh` re-downloads.
- nflverse `location` coding is used as-is, so the Bills Toronto games (2009–2012) and the 2005 Saints relocation games count as home games.

Later: a Vite + Svelte site (`web/`) renders static JSON written by the pipeline.

**Status:** Phase 1 in progress: Elo walking skeleton runs.

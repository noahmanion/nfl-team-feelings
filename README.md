# feel-good-score

How should NFL fans *actually* feel about their team? This project builds a momentum-weighted, Elo-like "feel-good score" (0–100) for every team since 1999 and backtests it against future results. It's a reality check for fanbases that think their team is worse (or better) than it is. The score is a weighted blend of eleven factors (Elo, record, last 16 games, margins, close-game luck, efficiency, QB play, preseason expectations, playoff odds and more), shown in a small static site: a mood board, mood over time, a page per team, records and a "how it works" page.

## Run it

**Refresh data** (once a week, after games finish):

```bash
cd pipeline
uv run fgs refresh    # re-download nflverse, run every check, regenerate web/public/data (writes nothing if a check fails)
```

**Start the site:**

```bash
cd web
nvm use && npm install   # once; Node >=22.12, pinned by web/.nvmrc
npm run dev
```

The generated JSON in `web/public/data/` is committed, so the site runs without Python.

`web/public/data/teams/{ABBR}.json` (e.g. `teams/BUF.json`) is a public per-team data file: the team's name, colors and full score/Elo/label history since 1999. The site itself doesn't fetch it; it's there for anyone who wants one team's series. A pipeline test pins its last entry to the latest board row.

**Other pipeline commands** (all from `pipeline/`):

```bash
uv run fgs export         # rebuild the site JSON from the local cache, no network
uv run fgs build          # download (once) + derive games, Elo, sims, features; first run pulls pbp 1999+ (~26 s)
uv run fgs ingest --refresh   # re-download only the schedules file (`fgs refresh` re-downloads everything)
uv run fgs check          # data-trust checks; exit 1 on failure
uv run fgs elo [--season 2008 --week 5]   # ranked Elo table; week 0 = preseason
uv run fgs backtest       # walk-forward backtest (2003–2021) of the score vs baselines
uv run fgs backtest --include-holdout     # also score 2022–2025 (allowed only because the one-time holdout result exists)
uv run fgs evidence       # dev-only: recompute callout base rates into pipeline/callout_evidence.json; commit it
```

- Data is cached in `pipeline/data/` (gitignored).
- `fgs export`/`refresh` also rewrite `pipeline/RECORDS_CHECK.md`, the hand-check list for the records page. Don't hand-edit it.

**Weights are permanently frozen for v1.** They were fit on 1999–2021 (`pipeline/weights.yaml`, `frozen: true`) and the sealed 2022–2025 holdout has been evaluated once under `pipeline/PREREGISTRATION.md`. The weekly refresh never refits. `fgs backtest --propose-weights` and `fgs freeze` are refused, and `fgs holdout` must not be re-run. A new model version would need a new pre-registration and a fresh holdout.

## How it works

The site's **How it works** page (`#/methodology`) explains the factors, their frozen weights and the walk-forward evidence. In short: each factor is z-scored across teams in the same week, weighted, summed, and turned into a percentile against a fixed 1999–2021 reference, so a historical score never shifts. Seven mood bands with a 2-point hysteresis turn the score into a label.

**Backtest target.** For every team-week, the mean *adjusted margin* over the team's next N games that season (N = 8 headline, N = 4 too): point margin + (opponent pre-game Elo − 1505)/25 − signed home-field Elo/25. It uses only who you played and where, never the team's own rating. Walk-forward by season from 2003; 2022–2025 sealed until the one-time holdout.

**Holdout verdict (2022–2025): slight.** The score ranks teams a hair better than Elo alone at N=8 (Spearman 0.485 vs 0.481, gap +0.004, CI includes 0) and is slightly worse on next-game Brier. Full result: `pipeline/HOLDOUT_RESULT.md`. Per-factor evidence: `pipeline/BACKTEST_LOG.md`.

## Status

v1 is complete (all 8 phases): mood board, mood over time, team pages, callouts with base-rate evidence, biggest movers, a records page, a "my team" pin, and a draft-aware offseason. Weights frozen; holdout consumed.

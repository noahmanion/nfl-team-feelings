# NFL Team Feelings: the Feel-Good Score

**Live site:** https://nfl-team-feelings.vercel.app/

**How should NFL fans *actually* feel about their team?**

Fans routinely think their team is worse (or better) than the evidence says. This project builds a momentum-weighted, Elo-like **feel-good score (0–100)** for every team, every week since 1999, and backtests it against future results. The score is a weighted blend of eleven factors: Elo, current record, the last 16 games across season boundaries, margins, close-game luck, efficiency (EPA), QB play, preseason expectations, playoff odds, and more. A playful mood label sits on top of serious charts.

The site has:

- **Mood board**: all 32 teams ranked by score, with mood labels, weekly movement and callouts backed by historical base rates
- **Mood over time**: score history since 1999 with per-team highlighting
- **Team pages**: factor breakdown, Elo, and full history for each team
- **Records**: historical extremes and the longest misery and joy streaks
- **How it works**: factors, frozen weights, and the walk-forward evidence

## Stack

| Layer | Tech |
|---|---|
| Data | [nflverse](https://github.com/nflverse) via `nflreadpy` (schedules, lines, play-by-play with EPA, draft picks) |
| Pipeline | Python 3.13 + `uv`, Polars, NumPy (hand-rolled Elo + Monte Carlo playoff sims), scikit-learn, SciPy |
| Output | Static JSON committed to `web/public/data/` |
| Frontend | Vite + Svelte 5 + Observable Plot, hash routing, fully static |

Fonts: Inter and IBM Plex Mono, self-hosted via Fontsource, both under the SIL OFL 1.1.

Team logos are nominative identifiers served from local files in `web/public/logos/` (nothing is hotlinked). To take them down, set `VITE_LOGOS=off` in the build environment (for example the Vercel project env) and redeploy; every logo then renders as the team's color chip, and the build deletes `dist/logos/` so no logo file is deployed or served. The source files stay in `web/public/logos/`.

## Repository layout

```
pipeline/            Python: ingest → games → Elo → sims → features → score → JSON export
  src/fgs/           the `fgs` CLI and model code
  tests/             pipeline tests and data-trust checks
  weights.yaml       frozen v1 factor weights
  PREREGISTRATION.md, HOLDOUT_RESULT.md, BACKTEST_LOG.md   model evidence
web/                 static Svelte site; reads web/public/data/*.json
.planning/           design and planning history (roadmap, phases, research)
```

## Run it

**Start the site.** No Python is needed because the generated JSON is committed:

```bash
cd web
nvm use && npm install   # once; Node 24, pinned by web/.nvmrc
npm run dev
```

**Refresh data** once a week, after games finish:

```bash
cd pipeline
uv run fgs refresh    # re-download nflverse, run every check, regenerate web/public/data (writes nothing if a check fails)
```

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
- `fgs export` and `fgs refresh` also rewrite `pipeline/RECORDS_CHECK.md`, the hand-check list for the records page. Don't hand-edit it.

**Tests:** `uv run pytest` in `pipeline/`, and `npm test` / `npm run check` in `web/`.

**Deploy:** `web/` builds to a static `dist/` (`npm run build`). On Vercel, use the Vite preset with root directory `web`. Hash routing means no rewrites are needed.

### Per-team data files

`web/public/data/teams/{ABBR}.json` (e.g. `teams/BUF.json`) is a public per-team file with the team's name, colors, and full score/Elo/label history since 1999. The site itself doesn't fetch it; it's there for anyone who wants one team's series.

## How it works

Each factor is z-scored across teams in the same week, weighted, and summed. The sum becomes a percentile against a fixed 1999–2021 reference, so a historical score never shifts. Seven mood bands with a 2-point hysteresis turn the score into a label.

**Backtest target.** For every team-week, the target is the mean *adjusted margin* over the team's next N games that season (N = 8 headline, N = 4 too): point margin + (opponent pre-game Elo − 1505)/25 − signed home-field Elo/25. It uses only who you played and where, never the team's own rating. The backtest is walk-forward by season from 2003, with 2022–2025 sealed until a one-time holdout.

**Weights are permanently frozen for v1.** They were fit on 1999–2021 (`pipeline/weights.yaml`, `frozen: true`), and the sealed 2022–2025 holdout was evaluated once under `pipeline/PREREGISTRATION.md`. The weekly refresh never refits, and `fgs backtest --propose-weights`, `fgs freeze` and a second `fgs holdout` are refused. A new model version would need a new pre-registration and a fresh holdout.

**Holdout verdict (2022–2025): slight.** At N=8 the score ranks teams a hair better than Elo alone (Spearman 0.485 vs 0.481, gap +0.004, CI includes 0) and is slightly worse on next-game Brier. In other words, it's an honest read on how a team is doing, not a betting edge. Full result: `pipeline/HOLDOUT_RESULT.md`. Per-factor evidence: `pipeline/BACKTEST_LOG.md`.

## Status

**v2.0 "Public Site" shipped (2026-11-12, tag `v2.0`).** The site is live at https://nfl-team-feelings.vercel.app/. It redeploys on Vercel whenever `web/` changes on `main`.

- **v1 model:** mood board, mood over time, team pages, callouts with base-rate evidence, movers, records, a "my team" pin and a draft-aware offseason. Weights are frozen forever, and a golden test pins every score for seasons up to 2025.
- **Look:** an editorial redesign (Inter and IBM Plex Mono, one shared chart theme) with local team logos and era-correct names (e.g. San Diego Chargers in 2010).
- **Explore** (`#/explore`): an offense-vs-defense EPA scatter and a record-vs-evidence scatter, both using logos as marks. Team pages also show the preseason Vegas win total against actual pace (display-only from 2021 on).
- **Share links:** each build renders 1200×630 cards and static `/s/` share pages for every team and every current-season callout (from 2026 week 9). Copy-link buttons use these pages, so links unfurl with a card.
- **v2 model:** pre-registered, but not built yet. `pipeline/PREREGISTRATION_V2.md` (one commit, never edited; errata in `PREREGISTRATION_V2_DEVIATIONS.md`) covers good-loss luck and Vegas win totals in the score. Free agency was dropped. The model must be frozen before 2027 Week 1, and it is judged on the 2027 season as a fresh holdout.

Still open: manual checks of link previews on real platforms (Slack, iMessage, X, the Facebook and LinkedIn debuggers).

## Credits

NFL data comes from [nflverse](https://github.com/nflverse) (`nflreadpy`, `nfldata`). Elo methodology draws on FiveThirtyEight's published NFL Elo approach. This is an unofficial fan project, not affiliated with the NFL or any team.

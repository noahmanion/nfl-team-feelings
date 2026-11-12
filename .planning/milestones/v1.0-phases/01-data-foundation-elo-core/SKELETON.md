# Walking Skeleton: Feel-Good Score

**Phase:** 1
**Generated:** 2026-11-11

## Capability Proven End-to-End

From `pipeline/`, `uv run fgs build` followed by `uv run fgs elo --season 2026 --week 9` downloads every NFL game since 1999 (once), normalizes franchises, replays a 538-style Elo, and prints all 32 teams ranked with their record as of that week.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Language / runtime | Python 3.13, uv project at `feel-good-scorew/pipeline/`, package `fgs` (src layout) | Locked in CONTEXT; self-contained per repo CLAUDE.md |
| Data source | `nflreadpy==0.1.5` `load_schedules()` (all seasons, one file) | Free nflverse data; official loader |
| Data layer | Parquet files. Raw cache `pipeline/data/cache/schedules.parquet`; derived `pipeline/data/derived/{games,team_games,elo_snapshots}.parquet` (all gitignored) | No database needed; full replay takes milliseconds |
| Table library | Polars throughout; NumPy array for the sequential Elo ratings | nflreadpy returns Polars; locked in CONTEXT |
| Franchise identity | Canonical `franchise_id` = current nflverse code; `OAK→LV, SD→LAC, STL→LA` applied right after load | One unbroken history per franchise |
| Era rules | `fgs.season_config` lookup module (team count, REG games/weeks, playoff teams, HFA, divisions), validated against data by `fgs check` | Static, versioned, outcome-free |
| Rating core | Hand-rolled 538 `forecast.py` Elo: K=20, MOV multiplier (HFA inside), era HFA 65/58/30/45, eager 1/3 regression to 1505, CLE/HOU seeded 1300 | Verified to 0.1 Elo against 538's published ratings |
| Interface | stdlib argparse CLI `fgs` with `ingest`, `build`, `check`, `elo` | No extra dependency |
| Tests | Light pytest in `pipeline/tests/`; synthetic fixtures for math, real-cache tests skip if cache is absent | Light process per repo rules; no CI |
| Deployment | Local only. Documented run: `cd pipeline && uv run fgs build && uv run fgs elo` | Site and Vercel come later |
| Contract to later phases | `elo_snapshots.parquet` columns `season, week, franchise_id, elo, wins, losses, ties, win_pct`; `games.parquet` keeps `elo_pre_*`, `elo_post_*`, `p_home` for Phase 3 baselines | Phase 2 turns this into JSON for the site |

## Stack Touched in Phase 1

- [x] Project scaffold: uv project, `fgs` console script, pytest (plan 01)
- [x] Routing: CLI subcommands as the "routes" (`ingest`, `build`, `check`, `elo`) (plans 01–03)
- [x] Data: real write (cache + derived parquet) and real read (`fgs elo` reads snapshots) (plan 01)
- [x] Interaction: `fgs elo --season S --week W` returns a ranked table for any played week (plans 01, 03)
- [x] Run: documented local command in README (plan 01, updated in plan 03)

## Out of Scope (Deferred to Later Slices)

- Web frontend (Vite + Svelte + Observable Plot) and the JSON contract: Phase 2
- Mood labels, one-command weekly refresh to JSON: Phase 2
- Backtest harness, baselines, additive factor score: Phase 3
- Momentum factors (record, last-16, margin, opponent quality, streak, luck): Phases 3–4
- Play-by-play EPA aggregates (DATA-05) and season simulator: Phase 5
- Draft data (DATA-06) and offseason draft reaction: Phase 7
- Overrides for nflverse `location` quirks (Toronto 2009–2012, 2005 Saints): accepted as-is
- HFA/K tuning: Phase 3 at the earliest; Phase 1 constants are outcome-free lookups

## Subsequent Slice Plan

- Phase 2: Elo mood board site, reading JSON generated from `elo_snapshots.parquet`
- Phase 3: backtest harness + additive score + mood-over-time chart
- Phase 4: game-result factors + team deep-dive page
- Phase 5: efficiency, QB trend, season simulator
- Phase 6: weight freeze + methodology page
- Phase 7: draft-aware offseason
- Phase 8: callouts, records, "my team"

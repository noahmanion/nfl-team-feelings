# Phase 1: Data Foundation & Elo Core - Context

**Gathered:** 2026-11-11
**Status:** Ready for planning
**Mode:** Autonomous — recommended answers auto-accepted (user granted full autonomy)

<domain>
## Phase Boundary

Load every NFL game 1999→current 2026 week via nflreadpy, cache locally, normalize to stable franchise IDs, encode era rules, validate with data checks, and replay chronologically into a base Elo for every franchise at every (season, week) — exposed via a CLI. No frontend, no momentum factors, no backtest (those are Phases 2–3).

</domain>

<decisions>
## Implementation Decisions

### Project layout & tooling
- Python lives in `pipeline/` as a uv project (Python 3.13), package `fgs` (src layout: `pipeline/src/fgs/`), CLI entry point `fgs` via `[project.scripts]` → run as `uv run fgs <cmd>` from `pipeline/`.
- Use Polars throughout (nflreadpy returns Polars); NumPy for the sequential Elo loop. Pin `nflreadpy==0.1.5`.
- CLI built with stdlib `argparse` (no Typer/Click dependency) — keep it light.
- Cache: raw nflverse pulls written as parquet under `pipeline/data/cache/` (gitignored). Re-runs read from cache; `fgs ingest --refresh` forces re-download (refresh only current season by default; `--all` for everything).
- Derived tables written to `pipeline/data/derived/` (gitignored): `games.parquet`, `team_games.parquet`, `elo_snapshots.parquet`.
- Light pytest suite in `pipeline/tests/` covering data checks and Elo invariants — no CI.

### Franchise identity & era rules
- Canonical `franchise_id` = current nflverse abbreviation (LV, LAC, LA, WAS, ARI, etc.). Mapping table in code: OAK→LV, SD→LAC, STL→LA, plus any legacy WAS/WSH variants, applied to every loaded table before anything else.
- Season-config table (`season_config.py` or CSV in repo): per season → team count (31 for 1999–2001, 32 from 2002), regular-season games per team (16 through 2020, 17 from 2021), playoff teams (12 through 2019, 14 from 2020), divisions/conference membership per franchise per season (2002 realignment).
- Expansion/new franchises: CLE (1999) and HOU (2002) enter with a seeded rating of 1300 (538 convention); everyone else starts 1505 in 1999.

### Game handling
- Ties score 0.5 for Elo actual result and count as 0.5 wins in records.
- Neutral-site games (`location == "Neutral"`) get zero home-field advantage.
- Games with no result (BUF–CIN 2022 cancelled; future unplayed 2026 games) are kept in `games` with `played=false` and skipped by Elo and record calculations — never crash, never counted.
- Playoff games are included in Elo (as 538 did) but flagged `game_type != REG`; regular-season-only counts are used for data checks.

### Elo model (538-style, verify constants in research)
- K = 20; margin-of-victory multiplier `ln(|MOV|+1) × 2.2 / (elo_diff_winner × 0.001 + 2.2)`.
- Era-aware home-field advantage as a per-season lookup in season-config: 65 (1999–2009), 58 (2010–2019), 30 (2020), 45 (2021+) Elo pts — per RESEARCH.md (derived from betting lines, holdout-safe). MOV multiplier uses elo_diff including HFA, and ties use 538's fixed denominator (see RESEARCH.md).
- Offseason: regress 1/3 toward 1505 at each season boundary; week-0 snapshot = post-regression rating.
- Elo is zero-sum: league mean stays ~1505 (test invariant, adjusting for expansion seeds).

### Snapshot grid & CLI
- Records (W-L-T) in snapshots count regular-season games only; playoff games still move Elo.
- Regress all teams at the season boundary (not lazily) so every team has a week-0 rating.
- `fgs elo` for a week beyond the latest played week errors clearly (non-zero exit). Latest played week comes from cached data, not get_current_week().
- Own parquet cache (not nflreadpy's 24h cache); schedules are one file, so `--refresh` re-downloads it whole.
- Data check exception: BUF and CIN 2022 have 16 regular-season games (cancelled game absent from data).
- Snapshot grid keyed by (season, week, franchise_id) covering week 0 through final postseason week of each season, filled forward over bye weeks; `elo_post` = rating after all games with week ≤ w.
- "Current week" from `nflreadpy.get_current_week()` / latest played game.
- CLI commands: `fgs ingest [--refresh] [--all]`, `fgs check` (runs all data checks, non-zero exit on failure), `fgs elo --season S --week W [--top N]` (prints ranked table with franchise, Elo, record as of that week), `fgs build` (ingest + derive + elo in one go).

### Claude's Discretion
- Exact module breakdown inside `fgs`, test fixture choices, table printing format, and whether HFA constants are hand-set or estimated once from historical home margins.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield. Research in `.planning/research/STACK.md` and `ARCHITECTURE.md` has verified nflreadpy 0.1.5 API (schedules with spread_line/total_line/starting QB columns, Polars output, `get_current_week()` = 10).

### Established Patterns
- Repo convention (root CLAUDE.md): self-contained project dir, own deps, brief README, light process.

### Integration Points
- Phase 2 consumes `elo_snapshots.parquet` (season, week, franchise_id, elo, wins, losses, ties) to emit JSON for the site. Keep that schema stable.

</code_context>

<specifics>
## Specific Ideas

- "Current 2026 ranking looks plausible" — sanity check top/bottom 5 against intuition and nfelo-style rankings in verification.
- Researcher flagged: verify per-loader historical team codes (schedules vs pbp vs draft) and `spread_line` sign convention against `result` — capture findings for later phases.

</specifics>

<deferred>
## Deferred Ideas

- Play-by-play EPA aggregates (DATA-05) and draft data (DATA-06) are mapped to Phases 5 and 7.

</deferred>

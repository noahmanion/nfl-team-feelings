# Phase 1: Data Foundation & Elo Core - Research

**Researched:** 2026-11-11
**Domain:** nflverse schedule ingest, franchise normalization, 538-style NFL Elo replay, (season, week) snapshot grid, CLI
**Confidence:** HIGH. Almost every claim below was checked by running code against live nflverse data (nflreadpy 0.1.5, polars 2.1.0) and against 538's published reference implementation.

## Summary

I loaded every game from 1999 through 2026 with `nflreadpy.load_schedules()` in a scratch uv env: 7,548 rows, 46 columns, ~355 KB as parquet, 0.5 s to download. **nflverse does NOT normalize relocated-team codes in schedules.** Raw codes include `OAK` (1999–2019) → `LV` (2020+), `SD` (1999–2016) → `LAC` (2017+), and `STL` (1999–2015) → `LA` (2016+). Washington is `WAS` in every season, with no `WSH` variant. That gives exactly 35 raw codes. With the 3-entry map applied, team counts are exactly 31 for 1999–2001 and 32 from 2002 onward. Every team-season has exactly 16 (≤2020) or 17 (≥2021) regular-season games, with one exception: **BUF and CIN 2022 have 16. The cancelled Hamlin game is not in the dataset at all.** It has no row and no null result, so nothing will crash on it. The data check needs an explicit allow-list entry for those two team-seasons. Before 2026 there are zero null-result games. The only `played=false` rows are the 2026 week 10–18 games still to be played.

I re-implemented 538's published `forecast.py` (K=20, HFA=65 flat, REVERT=1/3 toward 1505, CLE 1999 and HOU 2002 seeded at 1300, MOV multiplier with the autocorrelation term). Seeded with 538's own 1999 ratings and replayed over nflverse games, it reproduces 538's published pre-game Elo for 5,822 matched games with a **mean absolute difference of 0.10 Elo points**. The residual differences come from 2005 Saints displacement games and neutral-site home/away ordering. The algorithm is therefore verified, not assumed. The full 1999–2026 replay takes about 10 ms in plain Python, so a full replay on every run is free.

Home-field advantage estimated from the data, using market-implied HFA (mean `spread_line` on non-neutral games × 25 Elo/pt): about **65 (1999–2009), 58 (2010–2019), 30 (2020), 45 (2021–2026)**. Realized home margins agree everywhere except 2020, where the realized value is ~0. Out-of-sample-ish Brier (2002+) is almost flat across HFA choices: 0.2194–0.2204 for every variant tried, including the CONTEXT default of 48/10/35. Plain Elo Brier is 0.2196, against 0.2115 for the Vegas spread. The 2026 ranking after week 9 is plausible (BUF 7-1 top; TEN 1-7, NYJ, MIA 1-7, LAC 0-8 bottom), and Elo correlates 0.89 with 2026 point differential.

**Primary recommendation:** Cache the schedules to `pipeline/data/cache/schedules.parquet` yourself rather than relying on nflreadpy's cache. Map `{"OAK":"LV","SD":"LAC","STL":"LA"}` immediately after load. Sort by `(season, week, gameday, gametime, game_id)`. Replay a pure-Python Elo that exactly mirrors 538's `forecast.py`, but do the offseason regression eagerly at each season boundary so week 0 exists. Fill the snapshot grid forward. Pin a pytest test to the 538 MOV formula and to the BUF/CIN 2022 exception.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Project layout & tooling**
- Python lives in `pipeline/` as a uv project (Python 3.13), package `fgs` (src layout: `pipeline/src/fgs/`), CLI entry point `fgs` via `[project.scripts]` → run as `uv run fgs <cmd>` from `pipeline/`.
- Use Polars throughout (nflreadpy returns Polars); NumPy for the sequential Elo loop. Pin `nflreadpy==0.1.5`.
- CLI built with stdlib `argparse` (no Typer/Click dependency) — keep it light.
- Cache: raw nflverse pulls written as parquet under `pipeline/data/cache/` (gitignored). Re-runs read from cache; `fgs ingest --refresh` forces re-download (refresh only current season by default; `--all` for everything).
- Derived tables written to `pipeline/data/derived/` (gitignored): `games.parquet`, `team_games.parquet`, `elo_snapshots.parquet`.
- Light pytest suite in `pipeline/tests/` covering data checks and Elo invariants — no CI.

**Franchise identity & era rules**
- Canonical `franchise_id` = current nflverse abbreviation (LV, LAC, LA, WAS, ARI, etc.). Mapping table in code: OAK→LV, SD→LAC, STL→LA, plus any legacy WAS/WSH variants, applied to every loaded table before anything else.
- Season-config table (`season_config.py` or CSV in repo): per season → team count (31 for 1999–2001, 32 from 2002), regular-season games per team (16 through 2020, 17 from 2021), playoff teams (12 through 2019, 14 from 2020), divisions/conference membership per franchise per season (2002 realignment).
- Expansion/new franchises: CLE (1999) and HOU (2002) enter with a seeded rating of 1300 (538 convention); everyone else starts 1505 in 1999.

**Game handling**
- Ties score 0.5 for Elo actual result and count as 0.5 wins in records.
- Neutral-site games (`location == "Neutral"`) get zero home-field advantage.
- Games with no result (BUF–CIN 2022 cancelled; future unplayed 2026 games) are kept in `games` with `played=false` and skipped by Elo and record calculations — never crash, never counted.
- Playoff games are included in Elo (as 538 did) but flagged `game_type != REG`; regular-season-only counts are used for data checks.

**Elo model (538-style, verify constants in research)**
- K = 20; margin-of-victory multiplier `ln(|MOV|+1) × 2.2 / (elo_diff_winner × 0.001 + 2.2)`.
- Era-aware home-field advantage as a per-season constant from season-config (default ~48 Elo pts pre-2020, ~10 for 2020, ~35 from 2021) — planner/researcher may refine by estimating from data, but keep it a lookup, not fitted live.
- Offseason: regress 1/3 toward 1505 at each season boundary; week-0 snapshot = post-regression rating.
- Elo is zero-sum: league mean stays ~1505 (test invariant, adjusting for expansion seeds).

**Snapshot grid & CLI**
- Snapshot grid keyed by (season, week, franchise_id) covering week 0 through final postseason week of each season, filled forward over bye weeks; `elo_post` = rating after all games with week ≤ w.
- "Current week" from `nflreadpy.get_current_week()` / latest played game.
- CLI commands: `fgs ingest [--refresh] [--all]`, `fgs check` (runs all data checks, non-zero exit on failure), `fgs elo --season S --week W [--top N]` (prints ranked table with franchise, Elo, record as of that week), `fgs build` (ingest + derive + elo in one go).

### Claude's Discretion
- Exact module breakdown inside `fgs`, test fixture choices, table printing format, and whether HFA constants are hand-set or estimated once from historical home margins.

### Deferred Ideas (OUT OF SCOPE)
- Play-by-play EPA aggregates (DATA-05) and draft data (DATA-06) are mapped to Phases 5 and 7.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | Load all games 1999→present (schedules, scores, spreads, starting QBs) via nflreadpy, cache locally | `load_schedules()` returns 1999–2026 in one file (no per-season download). Columns verified (see Data Facts). Cache as our own parquet; nflreadpy's fs cache expires after 24h and is opaque (md5 filenames). |
| DATA-02 | Stable franchise ID across relocations/renames | Raw codes verified: exactly 35. Map `OAK→LV, SD→LAC, STL→LA`; WAS never varies in schedules. After the map: 32 IDs, 31 in 1999–2001. `game_id` embeds raw codes (`2012_10_STL_SF`), so never parse teams from it. |
| DATA-03 | Season-config table (team counts, games, playoff teams, divisions) | Divisions verified by building connected components of the `div_game==1` graph: 1999–2001 identical (6 divisions), 2002–2026 identical (8 divisions). Exact memberships listed below. Week layout: REG weeks 1–17 and playoffs 18–21 (≤2020); REG 1–18 and playoffs 19–22 (≥2021). |
| DATA-04 | Ties 0.5, neutral sites, cancelled games without crash/miscount | 16 ties (`result==0`), all REG. 103 Neutral games (75 REG, 27 SB, 1 WC: 2024 MIN–LA in Glendale). BUF–CIN 2022 is absent. Future 2026 games have null scores/result. |
| DATA-07 | Data checks: franchise counts, games per team-season, no unmatched abbreviations | All checks were prototyped and pass on live data. The one allow-list exception is `{(2022,"BUF"),(2022,"CIN")}` → 16. |
| MODEL-01 | Base Elo with MOV, era HFA, offseason regression | 538 `forecast.py` fetched and replicated. Cross-check mean |Δ| is 0.10 Elo over 5,822 games. HFA lookup estimated from spreads. |
| MODEL-02 | (season, week, franchise) snapshot grid incl. byes and week 0 | Prototype: 19,710 grid rows, 0 nulls after per-(franchise, season) forward-fill. Week 0 = post-regression / seed rating. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Self-contained in `feel-good-scorew/`. No root-level package manifests, no shared deps. The uv project lives at `feel-good-scorew/pipeline/`.
- Light process: quick prototype, no CI, and only a light test suite. pytest is fine, as CONTEXT allows.
- The project needs a brief `README.md` (what / how to run / status). Phase 1 should add a "pipeline" run section.
- Work only inside `feel-good-scorew/`.
- Stack: Python 3.13 + uv + nflreadpy (pinned 0.1.5) + Polars + NumPy. Hand-rolled Elo, no Elo library.
- GSD workflow: edits go through GSD commands (a planner/executor concern).

## Architectural Responsibility Map

Batch pipeline only; there are no web tiers in this phase.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Download + raw cache | Ingest (`fgs.ingest`) | Filesystem (`data/cache/`) | The only network-touching module |
| Franchise normalization | Ingest/normalize (`fgs.franchises`) | — | Must run before any other transform |
| Era rules / divisions / HFA | Config (`fgs.season_config`) | — | Static lookup data, versioned in git |
| games / team_games tables | Derive (`fgs.games`) | `data/derived/` | Pure transforms of cached raw data |
| Elo replay | Model core (`fgs.elo`), pure functions | — | Sequential loop, no I/O |
| Snapshot grid + records | Model core (`fgs.snapshots`) | `data/derived/elo_snapshots.parquet` | Phase 2 contract |
| Data checks | `fgs.checks` | pytest + `fgs check` | Same functions, two entry points |
| CLI | `fgs.cli` (argparse) | — | Thin orchestration |

## Verified Data Facts (live probe, 2026-11-11)

All of these come from `nflreadpy 0.1.5` `load_schedules()` with no args (all seasons). [VERIFIED: live probe]

**Shape:** 7,548 games, seasons 1999–2026. `game_id` is unique (7,548 distinct).

**Columns and dtypes you'll use:**
`game_id: str` (`"1999_01_MIN_ATL"`, raw codes), `season: i32`, `game_type: str` (`REG, WC, DIV, CON, SB`), `week: i32`, `gameday: str` (`"YYYY-MM-DD"`, 0 nulls), `gametime: str` (null in early years), `away_team, home_team: str`, `away_score, home_score: i32` (null if unplayed), `location: str` (`"Home"` / `"Neutral"`), `result: i32` (= home_score − away_score; 0 mismatches), `total: i32`, `overtime: i32`, `spread_line: f64` (0 nulls through 2025), `total_line`, `home_moneyline`/`away_moneyline`, `div_game: i32` (0 nulls), `home_qb_id/home_qb_name/away_qb_id/away_qb_name`, `home_rest/away_rest`, `roof, surface, stadium, stadium_id`, and others (46 total).

**Spread sign:** `spread_line > 0` means the **home team is favored**. Mean `result` is +5.95 when spread>0 and −4.53 when spread<0, and corr(spread_line, result) = 0.43. Win prob = Φ(spread_line / 13.5). [VERIFIED: live probe]

**Raw team codes in schedules (35):** the 32 current codes plus `OAK` (1999–2019), `SD` (1999–2016), and `STL` (1999–2015). `LA` starts 2016, `LAC` 2017, `LV` 2020, and `HOU` 2002. `WAS` covers 1999–2026; there is no WSH or WFT. [VERIFIED: live probe]

**Other loaders use different codes** (for later phases, recorded now) [VERIFIED: live probe]:
- `load_pbp()` **already normalizes** `posteam` to LA/LAC/LV, even for 1999 and 2015. Note that 1999 contains empty-string `''` posteam values.
- `load_draft_picks()` uses **PFR codes**: `GNB, KAN, NWE, NOR, SFO, TAM, LVR, SDG, LAR, OAK, STL`, and others. Phase 7 needs a second mapping.
- `load_teams()` returns 36 `team_abbr` values including legacy `OAK, SD, STL` and **both `LA` and `LAR`**. Filter to the 32 canonical IDs before joining.

**Team counts after mapping:** 31 for 1999–2001, 32 for 2002–2026. [VERIFIED]

**Games per team-season (REG):** exactly 16 for 1999–2020 and 17 for 2021–2026, **except BUF 2022 = 16 and CIN 2022 = 16**. Every 2026 team has 17 scheduled. [VERIFIED]

**BUF–CIN 2022:** **no row exists.** No game in 2022 week 17 has BUF or CIN at home against the other. There are 0 null-result games in 1999–2025. [VERIFIED]

**Ties (16, all REG):** 2002_10_ATL_PIT, 2008_11_PHI_CIN, 2012_10_STL_SF, 2013_12_MIN_GB, 2014_06_CAR_CIN, 2016_07_SEA_ARI, 2016_08_WAS_CIN, 2018_01_PIT_CLE, 2018_02_MIN_GB, 2019_01_DET_ARI, 2020_03_CIN_PHI, 2021_10_DET_PIT, 2022_01_IND_HOU, 2022_13_WAS_NYG, 2025_04_GB_DAL, and 2026_05_NYG_WAS. [VERIFIED]

**Neutral sites (103):** every SB (27), 1 WC (`2024_19_MIN_LA`, State Farm Stadium, LA wildfires), and 75 REG (international games plus one-offs such as 2003 Sun Devil, 2010/2014 Ford Field, 2020 SF games in Glendale, and 2021 TIAA Bank). 2026 has 9 neutral REG games (Melbourne, Maracanã, and others). [VERIFIED]

**`location` quirks (accept as-is, document):** [VERIFIED]
- Bills Toronto Series: 2008 and 2013 are `Neutral`, but 2009–2012 are `Home` for BUF.
- 2005 Saints (Katrina) "home" games are all `Home`, including `2005_02_NYG_NO`, which was played at Giants Stadium. 538 coded these differently, which is the source of the largest Elo cross-check differences (up to 15 pts in 2005, washing out after regression).

**Week numbering:** ≤2020 has REG weeks 1–17 (17 weeks, one bye) and playoffs WC=18, DIV=19, CON=20, SB=21. ≥2021 has REG 1–18 and playoffs 19, 20, 21, 22. **2001 (9/11) is renumbered chronologically.** Week 2 is the 9/23 slate and the postponed games are folded into week 17. In every season, no week starts before the previous week ends, and no team plays twice in a week. Sorting by `(season, week)` is therefore chronologically correct, and the order of games within a week doesn't affect Elo. [VERIFIED]

**2026 state at research time:** weeks 1–9 are fully played; weeks 10–18 have 0 played (today is Wed Nov 11). There are no playoff rows yet for 2026. `get_current_season()` = 2026 and `get_current_week()` = 10. [VERIFIED]

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| nflreadpy | ==0.1.5 (pinned per CONTEXT) | `load_schedules()` | Official nflverse Python loader [VERIFIED: PyPI + live use] |
| polars | 2.1.0 (installed transitively; declare explicitly) | All table work, parquet I/O | nflreadpy returns Polars [VERIFIED: live use] |
| numpy | 2.5.4 | Optional for the Elo loop | CONTEXT names it. A plain Python dict loop already runs the whole replay in ~10 ms, so NumPy is optional here. [VERIFIED: timing] |
| Python | 3.13 | Runtime | 3.13.1 is installed locally [VERIFIED] |
| uv | 0.10.12 installed | Project/env/lock | [VERIFIED] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.2.0 | Light test suite | `uv add --dev pytest` [VERIFIED: PyPI] |
| argparse, json, math, pathlib (stdlib) | — | CLI, Elo math | Always |

nflreadpy pulls in `requests, pydantic, pydantic-settings, platformdirs, tqdm, polars` transitively. [VERIFIED: uv install log]

**Installation (from `feel-good-scorew/pipeline/`):**
```bash
uv init --package --name fgs --python 3.13   # creates src/fgs layout + [project.scripts]
uv add nflreadpy==0.1.5 polars numpy
uv add --dev pytest
```
`pyproject.toml` must contain `[project.scripts] fgs = "fgs.cli:main"`.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Own parquet cache | `NFLREADPY_CACHE=filesystem` | nflreadpy's fs cache uses md5 filenames and **expires after 24h** (`cache_duration=86400` default), which would re-download daily. Our own `schedules.parquet` is explicit, offline-safe, and matches CONTEXT. |
| `get_current_week()` | Derive from cache | `get_current_week()` makes a network call and returns the week of the **next unplayed** game (10 today). Derive "latest played week" from cached data: `max(week) where played and season == max(season)`. Keep `get_current_week()` only as an optional display hint. |

## Package Legitimacy Audit

slopcheck could not be installed in this environment. Per protocol, packages are tagged by provenance below; all were already vetted in project-level STACK.md.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| nflreadpy | PyPI (0.1.5) | ~1 yr | n/a | github.com/nflverse/nflreadpy (official nflverse, linked from nflverse docs) | unavailable | Approved: official org, verified live use [ASSUMED per protocol] |
| polars | PyPI (2.1.0) | 5+ yrs | very high | github.com/pola-rs/polars | unavailable | Approved [ASSUMED per protocol] |
| numpy | PyPI (2.5.4) | 15+ yrs | very high | github.com/numpy/numpy | unavailable | Approved [ASSUMED per protocol] |
| pytest | PyPI (9.2.0) | 15+ yrs | very high | github.com/pytest-dev/pytest | unavailable | Approved [ASSUMED per protocol] |

**Packages removed:** none. **Flagged [SUS]:** none. These are all household-name packages, so a human-verify checkpoint is low-value. The planner may skip it or make it a single combined checkpoint.

## Architecture Patterns

### System Architecture Diagram

```
 nflverse-data GitHub release (schedules/games.parquet)
        │  nflreadpy.load_schedules()   [only network call]
        ▼
 fgs ingest ──► data/cache/schedules.parquet  (raw, untouched; re-run reads this)
        │            ▲ --refresh re-downloads (whole file, ~0.5s)
        ▼
 normalize: replace OAK/SD/STL → LV/LAC/LA; assert codes ⊆ CANON(32)
        ▼
 derive games.parquet  (one row/game: franchise ids, neutral, played, game_type, result…)
        │                    └──► team_games.parquet (2 rows/game: team perspective)
        ▼
 sort (season, week, gameday, gametime, game_id)
        ▼
 Elo replay (pure) ── per season: regress all → seed entrants → week-0 snapshot
        │                         → for each played game: p, MOV mult, shift (±)
        │  writes elo_pre/elo_post/p_home onto games
        ▼
 snapshot grid: teams_in_season × weeks 0..last_week  ⟵ left-join last rating per (season,week,team)
        │        forward-fill within (franchise, season); add cumulative REG W/L/T
        ▼
 data/derived/elo_snapshots.parquet ──► fgs elo --season S --week W  (ranked table)
        │
        └──► fgs check (franchise counts, games/team-season, unmatched codes, continuity, zero-sum)
```

### Recommended Project Structure
```
feel-good-scorew/pipeline/
├── pyproject.toml            # name=fgs, requires-python>=3.13, [project.scripts] fgs="fgs.cli:main"
├── uv.lock
├── .gitignore                # data/
├── data/{cache,derived}/     # gitignored
├── src/fgs/
│   ├── __init__.py
│   ├── paths.py              # PIPELINE_ROOT, CACHE_DIR, DERIVED_DIR (resolve from __file__, not CWD)
│   ├── franchises.py         # RAW_TO_FRANCHISE, CANONICAL (frozenset of 32), normalize()
│   ├── season_config.py      # SEASONS dict / rows; DIVISIONS_1999, DIVISIONS_2002; HFA_BY_ERA; SEEDS
│   ├── ingest.py             # load_or_fetch_schedules(refresh: bool) -> pl.DataFrame
│   ├── games.py              # build_games(raw) -> games df; build_team_games(games)
│   ├── elo.py                # EloParams dataclass; replay(games, params) -> (games_with_elo, snapshots_sparse)
│   ├── snapshots.py          # build_grid(games, sparse) -> elo_snapshots df with W/L/T
│   ├── checks.py             # check_*() -> list[str] failures; run_all()
│   └── cli.py                # argparse: ingest/check/elo/build
└── tests/
    ├── conftest.py           # tiny synthetic games fixture; `real_games` fixture that skips if cache absent
    ├── test_elo.py           # pure unit tests on synthetic games
    ├── test_franchises.py
    └── test_checks.py        # data checks against cached real data
```

### Pattern 1: Elo replay that mirrors 538 exactly, with eager season regression
**What:** Before a season's first game, regress **all** existing teams toward 1505, then add entrants at their seed. Record week 0. Then process played games in order. This is mathematically identical to 538's lazy regression at each team's first game, and it gives every team a week-0 value. Prototyped and verified.

```python
# Source: adapted from github.com/fivethirtyeight/nfl-elo-game/blob/master/forecast.py (verified 2026-11-11)
import math
from dataclasses import dataclass

@dataclass(frozen=True)
class EloParams:
    k: float = 20.0
    mean: float = 1505.0
    revert: float = 1/3            # fraction pulled toward mean each offseason
    seeds: dict = None             # {("CLE",1999):1300.0, ("HOU",2002):1300.0}

def win_prob(diff: float) -> float:          # diff includes HFA
    return 1.0 / (10 ** (-diff / 400.0) + 1.0)

def mov_mult(margin: int, diff: float, res: float) -> float:
    # 538: ln(max(|pd|,1)+1) * 2.2 / (winner_elo_diff*0.001 + 2.2); ties use denominator 1.0
    pd = abs(margin)
    if res == 0.5:
        return math.log(max(pd, 1) + 1.0) * 2.2          # = ln(2)*2.2 ≈ 1.525
    winner_diff = diff if res == 1.0 else -diff           # diff INCLUDES HFA
    return math.log(max(pd, 1) + 1.0) * (2.2 / (winner_diff * 0.001 + 2.2))

def update(elo_h, elo_a, margin, hfa, k):
    diff = elo_h - elo_a + hfa
    p = win_prob(diff)
    res = 1.0 if margin > 0 else 0.0 if margin < 0 else 0.5
    shift = k * mov_mult(margin, diff, res) * (res - p)
    return elo_h + shift, elo_a - shift, p
```
Replay loop shape (verified prototype):
```python
for season in seasons:                       # ascending
    for t in elo: elo[t] = p.mean*p.revert + elo[t]*(1-p.revert)
    for t in teams_in(season):
        elo.setdefault(t, p.seeds.get((t, season), p.mean))
    emit week-0 rows for teams_in(season)
    for g in played_games(season):            # sorted; skip played == False
        hfa = 0.0 if g.neutral else hfa_for(season)
        ...update, store elo_pre/elo_post/p_home on game row, emit (season, week, team, elo_post)
```
**Note the CONTEXT formula wording:** `elo_diff_winner` must **include HFA** and be signed from the winner's view, and the minimum margin is `max(|MOV|,1)`. Ties use a denominator of 1.0. These details come from 538's code. [VERIFIED: forecast.py]

### Pattern 2: Snapshot grid via sparse emit + forward fill
```python
# Verified prototype: 19,710 rows, 0 null elo
sparse = (pl.DataFrame(rows, schema=["season","week","franchise_id","elo"], orient="row")
            .group_by("season","week","franchise_id").last())   # one game/team/week anyway
last_week = games.filter("played").group_by("season").agg(pl.col("week").max().alias("wmax"))
teams = team_games.select("season","franchise_id").unique()   # 31 or 32 per season
grid = (teams.join(last_week, on="season")
          .with_columns(pl.int_ranges(0, pl.col("wmax")+1).alias("week")).explode("week")
          .with_columns(pl.col("week").cast(pl.Int32)).drop("wmax"))
snap = (grid.join(sparse, on=["season","week","franchise_id"], how="left")
            .sort("franchise_id","season","week")
            .with_columns(pl.col("elo").forward_fill().over("franchise_id","season")))
```
- Use **last played week**, not last scheduled week, for `wmax`. That way the current season grid ends at week 9 now and gains week 10 after the partial-week refresh. The CLI should reject or clamp a week beyond `wmax` with a clear message.
- Records: cumulative **REG-only** W/L/T per (franchise, season) as of week w, joined the same way and forward-filled, with 0 at week 0. Ties count as a separate `ties` column, and `win_pct = (W + 0.5T)/(W+L+T)`.
- Include `elo_pre`/`elo_post`/`p_home` on `games.parquet`. Phase 3 baselines (Elo Brier) need pre-game probabilities, and storing them now costs nothing.

### Pattern 3: Data checks as plain functions returning failure lists
`checks.py` functions take DataFrames and return `list[str]`. `fgs check` prints them and exits 1 if any are returned, and pytest asserts `== []`. That gives one implementation with two entry points.

### Season config (verified content)

```python
# Divisions derived from div_game graph components; identical every season within era [VERIFIED]
DIVISIONS_1999_2001 = {
  "AFC East":    ["BUF","IND","MIA","NE","NYJ"],
  "AFC Central": ["BAL","CIN","CLE","JAX","PIT","TEN"],
  "AFC West":    ["DEN","KC","LAC","LV","SEA"],
  "NFC East":    ["ARI","DAL","NYG","PHI","WAS"],
  "NFC Central": ["CHI","DET","GB","MIN","TB"],
  "NFC West":    ["ATL","CAR","LA","NO","SF"],
}
DIVISIONS_2002_ON = {
  "AFC East":  ["BUF","MIA","NE","NYJ"],   "AFC North": ["BAL","CIN","CLE","PIT"],
  "AFC South": ["HOU","IND","JAX","TEN"],  "AFC West":  ["DEN","KC","LAC","LV"],
  "NFC East":  ["DAL","NYG","PHI","WAS"],  "NFC North": ["CHI","DET","GB","MIN"],
  "NFC South": ["ATL","CAR","NO","TB"],    "NFC West":  ["ARI","LA","SEA","SF"],
}
# Per season: n_teams (31 | 32), reg_games (16 | 17), reg_weeks (17 | 18),
# playoff_teams (12 ≤2019 | 14 ≥2020), hfa (see below)
```
Division names/conference labels for 1999–2001 come from training knowledge [ASSUMED]. Memberships are [VERIFIED] from `div_game`. Add a check that recomputes the `div_game` components and compares them to the table.

### HFA lookup (Claude's discretion → recommendation)

| Era | Market-implied (mean spread_line×25) | Realized home margin×25 | Brier-grid optimum (2002+) | **Recommend** |
|-----|------|------|------|------|
| 1999–2009 | 65 | 68 | 60 | **65** (= 538's constant) |
| 2010–2019 | 59 | 58 | 55 | **58** |
| 2020 | 29 | 4 | 5 | **30** |
| 2021+ | 44 | 52 | 25 | **45** |

Brier (2002–2026 games) by variant [VERIFIED: prototype]: const65 0.2204, const48 0.2198, CONTEXT 48/10/35 0.2195, market 65/58/30/45 0.2196, grid-optimum 0.2194. The differences are within noise.

**Recommend the market-implied values** because they are **outcome-free**: they're derived from closing lines, not fitted to results. That keeps the Phase 6 2022–2025 holdout clean, whereas the Brier-grid values were fitted on all seasons, holdout included. Store `hfa` per season in season_config with a comment explaining its derivation, and optionally ship a tiny `scripts/estimate_hfa.py` that prints the table. Phase 3 may tune it. The CONTEXT default (48/10/35) is an acceptable alternative with identical Brier. Note that 538's published file used a flat 65 through 2020 [VERIFIED: back-solved from 538 `elo_prob1`]. The "48" figure attributed to 538 could not be confirmed [ASSUMED/unverified].

### Anti-Patterns to Avoid
- **Parsing teams out of `game_id`.** It contains raw codes (`STL`, `OAK`, `SD`).
- **Using `get_current_week()` as "last completed week".** It returns the next game's week and needs the network.
- **Lazy (per-team-first-game) regression only.** You lose week-0 snapshots for teams on a week-1 bye. Regress everyone eagerly at the season boundary.
- **Computing HFA or K by fitting on all seasons in Phase 1.** That leaks the holdout. Keep the lookup outcome-free.
- **Filtering on week number to find "played" games.** Use `result.is_not_null()`, since the current week can be partial.
- **Joining `load_teams()` without filtering.** It has 36 rows, including both `LA` and `LAR`, and legacy codes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fetching nflverse data | Custom HTTP to GitHub releases | `nflreadpy.load_schedules()` | Handles URL/format; already pinned |
| Bye-week fill | Python loops per team/week | Polars `int_ranges` + `explode` + `forward_fill().over(...)` | 20k rows, one expression |
| Division membership derivation | Hand-typing from memory only | Typed table **validated** by `div_game` graph check | Catches typos |
| Normal CDF (spread → prob, later) | Lookup table | `pl.col(...).erf()` or `math.erf` | Already built in |
| CLI | Typer/Click | stdlib `argparse` (locked) | No dependency |

**Key insight:** The Elo math itself should be hand-rolled (about 15 lines), but it must match 538's reference code exactly. The subtle details (HFA inside the autocorrelation term, `max(pd,1)`, tie denominator 1.0) are where hand-rolled versions usually drift. Pin each one with a unit test.

## Common Pitfalls

### Pitfall 1: Expecting a BUF–CIN 2022 row
**What goes wrong:** A test for "the cancelled game is skipped" finds nothing to skip, or a check expects 17 games for BUF/CIN 2022 and fails.
**Why:** nflverse dropped the game entirely.
**Avoid:** Allow-list `{(2022,"BUF"):16, (2022,"CIN"):16}` in the games-per-team check. Exercise the `played=false` path with a synthetic null-result game in a unit test, and with real 2026 future games.
**Warning sign:** A check failing on exactly BUF/CIN 2022.

### Pitfall 2: Mean ≠ 1505 is not a bug in 1999–2003
**What goes wrong:** A "league mean == 1505" assertion fails.
**Why:** With CLE seeded at 1300, the 1999 week-0 mean is 1498.39 (= (30·1505+1300)/31). HOU in 2002 drops it to ~1496.7. The 1/3 regression closes the gap geometrically.
**Avoid:** Test **zero-sum per game** exactly (|Δh+Δa| < 1e-9; prototype max 2.3e-13). Test that the league mean deviation after season S equals the seed deficit decayed by (2/3)^k. The simple version is `abs(mean-1505) < 0.5` for seasons ≥ 2012.

### Pitfall 3: Raw vs normalized codes leaking into joins
**What goes wrong:** LV history starts in 2020, or a Raiders Elo reset appears.
**Avoid:** Normalize inside `ingest`/`games` before anything else. Check that every franchise except HOU has a week-0 row in every season 1999–2026 (HOU from 2002). Check Elo continuity: `week0(S) == 1505/3 + 2/3·final(S−1)` for all franchises, especially LV 2020, LAC 2017, and LA 2016.

### Pitfall 4: Week semantics across the 2021 change and playoffs
**What goes wrong:** Hardcoding 17 weeks or treating week 18 as REG for pre-2021 seasons.
**Avoid:** Derive weeks from data and use `game_type` for REG vs postseason. The grid's max week is 21 (≤2020) or 22 (≥2021). Eliminated teams forward-fill through the remaining playoff weeks.

### Pitfall 5: Partial current week
**What goes wrong:** Running on a Friday puts the week-10 snapshot in a state where some teams have played and some haven't.
**Avoid:** That's fine by definition (rating after all *played* games with week ≤ w), but record it. Store `data_through = max(gameday where played)` and a `week_complete` flag (all scheduled games in the week played) in a small meta output or the CLI header.

### Pitfall 6: nflreadpy config side effects
`NflreadpyConfig` reads a `.env` file in the CWD (`env_file=".env"`) and `NFLREADPY_*` env vars. The default cache is memory, valid for 24h. **Avoid** by calling `nflreadpy.config.update_config(cache_mode="off")` in ingest, since we own the cache. [VERIFIED: source of nflreadpy/config.py]

### Pitfall 7: Neutral-site edge cases in `location`
The Toronto 2009–2012 games are coded `Home` and the 2005 Saints relocation games are coded `Home`. CONTEXT locks `location` as the rule, so accept the coding and note it in the README. It only shifts a few ratings by a few points (≤15, verified against 538). Don't build an override list in Phase 1.

## Code Examples

### Ingest with own cache
```python
# fgs/ingest.py (pattern; nflreadpy API verified)
import nflreadpy as nfl, polars as pl
from nflreadpy.config import update_config
from fgs.paths import CACHE_DIR

def load_schedules(refresh: bool = False) -> pl.DataFrame:
    path = CACHE_DIR / "schedules.parquet"
    if path.exists() and not refresh:
        return pl.read_parquet(path)
    update_config(cache_mode="off")
    df = nfl.load_schedules()          # all seasons, single file (~0.5s, ~355KB parquet)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.write_parquet(path)
    return df
```
`--refresh` vs `--all`: schedules arrive as **one file for all seasons**, so "refresh only current season" is meaningless for schedules. Re-download the whole thing. Keep the `--all` flag in the CLI (it's in the locked CLI spec) for future per-season loaders like PBP in Phase 5. For now, document `--all` as equivalent to `--refresh` for schedules.

### Normalize
```python
RAW_TO_FRANCHISE = {"OAK": "LV", "SD": "LAC", "STL": "LA"}
CANONICAL = frozenset("ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LA LAC LV "
                      "MIA MIN NE NO NYG NYJ PHI PIT SEA SF TB TEN WAS".split())
KNOWN_RAW = CANONICAL | RAW_TO_FRANCHISE.keys()

games = raw.with_columns(
    pl.col("home_team").replace(RAW_TO_FRANCHISE).alias("home_id"),
    pl.col("away_team").replace(RAW_TO_FRANCHISE).alias("away_id"),
    (pl.col("location") == "Neutral").alias("neutral"),
    pl.col("result").is_not_null().alias("played"),
    (pl.col("game_type") == "REG").alias("is_reg"),
).sort("season", "week", "gameday", "gametime", "game_id", nulls_last=True)
```

### Data checks (all prototyped and pass on live data)
```python
EXPECTED_EXCEPTIONS = {(2022, "BUF"): 16, (2022, "CIN"): 16}   # cancelled Hamlin game, absent from data

def check_codes(raw) -> list[str]:            # unknown raw codes, unmatched after mapping
def check_team_counts(games) -> list[str]:    # n_unique franchise per season == 31 (≤2001) / 32
def check_games_per_team(games) -> list[str]: # REG scheduled per team-season == 16/17 (+exceptions);
                                              # REG played == scheduled for completed seasons
def check_continuity(games) -> list[str]:     # each franchise present every season since entry
def check_divisions(games) -> list[str]:      # div_game components == season_config divisions
def check_result_consistency(games):          # result == home_score - away_score where played
def check_elo_zero_sum(games_with_elo):       # |Δhome+Δaway| < 1e-9 for every played game
def check_snapshot_grid(snaps):               # rows == n_teams × (wmax+1) per season, no null elo
```

### CLI output target
```
$ uv run fgs elo --season 2026 --week 9 --top 5
2026 week 9 (data through 2026-11-09)
 #  Team   Elo    W-L-T
 1  BUF   1697    7-1-0
 2  DEN   1647    7-2-0
 ...
```
(Values above come from the prototype using market HFA 65/58/30/45 and will change slightly with the final constants.)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `nfl_data_py` (pandas) | `nflreadpy` (Polars) | 2025 | Native Polars; no `clean_team_abbrs` helper exists in nflreadpy, so we map ourselves [VERIFIED: grep of package source] |
| 538 constant HFA 65 | Era-aware HFA (market ~45 now) | Visible in data from ~2019/2020 | Lookup per season |
| 538 site/methodology page | Gone (redirects to abcnews.com) | 2025 | Use `fivethirtyeight/nfl-elo-game` GitHub `forecast.py` as the authoritative reference |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 1999–2001 division *names* (AFC Central, NFC Central, etc.) | Season config | Cosmetic only; memberships are verified |
| A2 | 538 later used HFA=48 | HFA lookup | None: the recommendation doesn't depend on it |
| A3 | Spread→prob SD 13.5 points | Data facts | Only used for the Vegas Brier reference (0.2115); not used in Phase 1 code |
| A4 | Package legitimacy (slopcheck unavailable) | Audit | Very low: all are major packages |
| A5 | Playoff-team counts (12 ≤2019, 14 ≥2020) | Season config | Low; well known and not used by Phase 1 logic. Could be checked against WC game counts (4/season ≤2019, 6/season ≥2020) |

## Open Questions

1. **Should playoff games count in the snapshot W/L/T?**
   - What we know: CONTEXT says REG-only counts for data checks. The Phase 2 schema lists wins/losses/ties.
   - Recommendation: REG-only W/L/T in snapshots (the record fans quote). Playoff games still move Elo. Optionally add `po_wins/po_losses` later.
2. **Current-season grid beyond last played week.**
   - Recommendation: Stop at the last played week. `fgs elo` for a later week prints "not played yet; latest is week N" and exits non-zero.
3. **Higher K for playoffs?**
   - 538's `forecast.py` uses the same K for playoffs [VERIFIED]. Keep K=20 everywhere in Phase 1 and leave it to Phase 3 tuning.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | pipeline | ✓ | 3.13.1 | — |
| uv | env/lock | ✓ | 0.10.12 | — |
| Network to github.com (nflverse-data releases) | first ingest / refresh | ✓ | — | Cached parquet after first run |
| pytest | tests | via `uv add --dev` | 9.2.0 | — |

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.2.0 (dev dependency) |
| Config file | none yet. Add `[tool.pytest.ini_options] testpaths=["tests"]` to `pipeline/pyproject.toml` (Wave 0) |
| Quick run command | `cd feel-good-scorew/pipeline && uv run pytest -q tests/test_elo.py tests/test_franchises.py` (synthetic, no network, <2s) |
| Full suite command | `cd feel-good-scorew/pipeline && uv run fgs build && uv run fgs check && uv run pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | First `fgs ingest` writes `data/cache/schedules.parquet`; second run does no network (monkeypatch `nflreadpy.load_schedules` to raise) and returns same frame | unit | `uv run pytest tests/test_ingest.py -x` | ❌ Wave 0 |
| DATA-01 | Cached frame covers seasons 1999..current and has the required columns | integration (needs cache) | `uv run pytest tests/test_checks.py -k columns` | ❌ Wave 0 |
| DATA-02 | `normalize` maps OAK/SD/STL; unknown code raises/returns failure; 32 canonical | unit | `uv run pytest tests/test_franchises.py` | ❌ Wave 0 |
| DATA-02 | LV/LAC/LA/WAS present every season 1999–2026, Elo continuous across 2016/2017/2020 | integration | `uv run pytest tests/test_checks.py -k continuity` | ❌ Wave 0 |
| DATA-03 | season_config covers 1999..current; 31/32 teams; 16/17 games; 12/14 playoff teams; divisions match `div_game` graph | integration | `uv run pytest tests/test_checks.py -k "config or divisions"` | ❌ Wave 0 |
| DATA-04 | Tie → res 0.5 and both teams' ties+1; neutral → zero HFA (p=0.5 for equal teams); null-result game skipped without error | unit (synthetic) | `uv run pytest tests/test_elo.py -k "tie or neutral or unplayed"` | ❌ Wave 0 |
| DATA-04 | BUF/CIN 2022 = 16 REG games accepted; all other team-seasons 16/17 | integration | `uv run pytest tests/test_checks.py -k games_per_team` | ❌ Wave 0 |
| DATA-07 | `fgs check` exits 0 on real data; exits 1 when a fake `XXX` code is injected | integration | `uv run fgs check; echo $?` + `pytest -k check_cli` | ❌ Wave 0 |
| MODEL-01 | MOV mult exact values (e.g. margin 7, diff +65, win → ln8·2.2/2.265); zero-sum per game; regression `1505/3+2/3·x`; seeds CLE1999/HOU2002 = 1300 | unit | `uv run pytest tests/test_elo.py` | ❌ Wave 0 |
| MODEL-01 | 2026 latest ranking: top-5 all winning records, bottom-5 all losing; mean(seasons≥2012) within 0.5 of 1505 | integration | `uv run pytest tests/test_checks.py -k elo_sanity` | ❌ Wave 0 |
| MODEL-02 | Grid rows = n_teams×(wmax+1) per season; no null elo; bye-week team's elo equals prior week; week 0 = post-regression | unit + integration | `uv run pytest tests/test_snapshots.py` | ❌ Wave 0 |
| MODEL-02 | `fgs elo --season 2026 --week 0` and a bye week print 32 rows | smoke | `uv run fgs elo --season 2026 --week 0 --top 32 \| wc -l` | ❌ Wave 0 |

Optional one-off validation (not in the suite, needs network): replay with 538's 1999 starting ratings and HFA=65 and compare to `fivethirtyeight/nfl-elo-game/data/nfl_games.csv`. Expect mean |Δ| ≈ 0.1 Elo. This validated the prototype and could ship as `scripts/crosscheck_538.py`.

### Sampling Rate
- **Per task commit:** quick run (synthetic unit tests)
- **Per wave merge:** full suite command
- **Phase gate:** `fgs build && fgs check && pytest` green, plus a manual eyeball of `fgs elo --season 2026 --week 9`

### Wave 0 Gaps
- [ ] `pipeline/pyproject.toml` with pytest config and the `fgs` script entry
- [ ] `tests/conftest.py`: `synthetic_games()` fixture (3–4 teams, 2 seasons, one tie, one neutral, one null-result game, one bye) and `real_games` fixture with `pytest.skip` if `data/cache/schedules.parquet` is missing
- [ ] `tests/test_elo.py`, `tests/test_franchises.py`, `tests/test_snapshots.py`, `tests/test_checks.py`, `tests/test_ingest.py`

## Security Domain

`security_enforcement: false` in `.planning/config.json`, so this section is omitted. There is no auth, no user input beyond local CLI args, and only public data.

## Sources

### Primary (HIGH confidence)
- Live probe of `nflreadpy==0.1.5` + `polars==2.1.0` in scratch uv env: `load_schedules`, `load_teams`, `load_draft_picks`, `load_pbp([1999,2015,2019])`, `get_current_season/week`, and nflreadpy source (`config.py`, `cache.py`, `load_schedules.py`, `utils_date.py`, `downloader.py`)
- https://github.com/fivethirtyeight/nfl-elo-game/blob/master/forecast.py: K=20, HFA=65, REVERT=1/3, REVERSIONS CLE1999=1300, MOV formula with tie denominator 1.0
- https://github.com/fivethirtyeight/nfl-elo-game/blob/master/data/initial_elos.csv: CLE=1300, HOU=1300
- https://github.com/fivethirtyeight/nfl-elo-game/blob/master/data/nfl_games.csv: back-solved HFA=65 for every non-neutral game 1999–2020; used for the 0.10-Elo cross-check
- PyPI JSON API: nflreadpy 0.1.5, polars 2.1.0, numpy 2.5.4, pytest 9.2.0

### Secondary (MEDIUM confidence)
- https://raw.githubusercontent.com/fivethirtyeight/data/master/nfl-elo/README.md: column semantics (`neutral`, `playoff`, `elo1_pre`); the archived `nfl_elo.csv` itself now 404s
- FiveThirtyEight articles via search (HFA historically 2.5–3 points; 2020 home teams 127-128-1): https://fivethirtyeight.com/features/why-did-nfl-teams-score-so-much-this-season , https://www.nbcsports.com/nfl/profootballtalk/rumor-mill/news/home-field-was-no-advantage-home-teams-went-127-128-1-in-2020-season , https://operations.nfl.com/gameday/analytics/stats-articles/what-does-the-nfl-s-home-field-advantage-look-like-in-2020

### Tertiary (LOW confidence)
- "538 HFA = 48" claim: not found in any source; treat as unverified

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (installed and run)
- Data facts: HIGH (every number above came from a live query)
- Elo algorithm: HIGH (reproduces 538's published ratings to 0.1 Elo)
- HFA values: MEDIUM-HIGH (data-derived; Brier is insensitive, so the exact choice matters little)
- Pitfalls: HIGH (each observed in data)

**Research date:** 2026-11-11
**Valid until:** ~2026-12-11 (nflverse data shape is stable; 2026 counts change weekly)

Scratch artifacts (not part of project): probe scripts in `/private/tmp/claude-501/-Users-noahmanion-Dropbox-code-idea-graveyard-feel-good-scorew/e9aca8f6-0367-4770-bd90-f3eef6a0daef/scratchpad/scripts/` (`probe2.py`–`probe7.py`, `elo_proto.py`, `elo_proto2.py`, `probe538.py`).

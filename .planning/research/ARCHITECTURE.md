# Architecture Research

**Domain:** Sports rating system (Elo + momentum composite) with offline Python pipeline and static visualization site
**Researched:** 2026-11-11
**Confidence:** MEDIUM-HIGH (pipeline/static-site patterns are standard and HIGH; specific model formulas are MEDIUM and must be validated by the backtest; external-data availability items flagged individually)

## Standard Architecture

Sports rating sites (FiveThirtyEight NFL Elo, nfelo, Massey, ESPN FPI-style public clones) almost universally follow the same shape: **a batch pipeline that replays every game in chronological order, emits a ratings table keyed by (team, as-of game), and publishes precomputed artifacts that a dumb frontend renders.** No server, no database at read time. This project fits that shape exactly. What's unusual here is (a) a composite score built from many factors instead of one rating, and (b) the need to *prove* the composite predicts the future. So the backtest harness is a core part of the system, not an afterthought.

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 1. INGEST (network boundary — only layer that touches the internet)      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│  │ schedules    │ │ pbp (per     │ │ draft_picks  │ │ external CSVs    │ │
│  │ (nflreadpy)  │ │ season)      │ │ (nflreadpy)  │ │ (win totals,     │ │
│  │              │ │ → aggregated │ │              │ │  draft chart)    │ │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └────────┬─────────┘ │
│         └────────────────┴──────┬─────────┴──────────────────┘           │
│                                 ▼                                         │
│               data/interim/*.parquet  (canonical, franchise-normalized)   │
├──────────────────────────────────────────────────────────────────────────┤
│ 2. MODEL CORE (pure functions, no I/O; chronological replay)             │
│  ┌───────────────┐   ┌────────────────────┐   ┌──────────────────────┐   │
│  │ Base strength │──▶│ Feature builder    │──▶│ Score combiner       │   │
│  │ (Elo replay,  │   │ (as-of features    │   │ (z-score per         │   │
│  │  offseason    │   │  per team-game:    │   │  snapshot × weights  │   │
│  │  regression + │   │  last16, EPA trend,│   │  → score, mood,      │   │
│  │  draft bump)  │   │  margin, opp qual, │   │  contributions)      │   │
│  └───────┬───────┘   │  vs-expectation,   │   └──────────┬───────────┘   │
│          │           │  streak, luck, QB, │              │               │
│          │           │  playoff odds)     │              │               │
│          │           └─────────┬──────────┘              │               │
│          │   ┌─────────────────┴───────┐                 │               │
│          └──▶│ Season simulator        │ (playoff odds,  │               │
│              │ (Monte Carlo on Elo)    │  expected wins) │               │
│              └─────────────────────────┘                 │               │
├──────────────────────────────────────────────────────────┼───────────────┤
│ 3. EVALUATION (offline, dev-time)                        ▼               │
│  ┌──────────────────────┐   ┌─────────────────────┐  ┌────────────────┐  │
│  │ Backtest harness     │──▶│ Weight tuner        │─▶│ weights.yaml   │  │
│  │ (walk-forward,       │   │ (ridge/NNLS on      │  │ (committed,    │  │
│  │  next-N targets,     │   │  train seasons,     │  │  opinionated,  │  │
│  │  baselines)          │   │  then human-rounded)│  │  versioned)    │  │
│  └──────────────────────┘   └─────────────────────┘  └────────────────┘  │
├──────────────────────────────────────────────────────────────────────────┤
│ 4. PUBLISH                                                               │
│  ┌──────────────────┐   ┌────────────────────┐                           │
│  │ Callout detector │──▶│ JSON exporter      │──▶ site/public/data/*.json│
│  │ (rule-based      │   │ (snapshots, teams, │                           │
│  │  "aha" finder)   │   │  history, meta)    │                           │
│  └──────────────────┘   └────────────────────┘                           │
├──────────────────────────────────────────────────────────────────────────┤
│ 5. FRONTEND (static; fetch JSON, render; zero model logic)               │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐   │
│  │ Mood board │  │ Team page    │  │ Mood-over-time│  │ Callout cards│   │
│  │ (home)     │  │ (breakdown,  │  │ chart (all    │  │ (shareable)  │   │
│  │            │  │  history)    │  │  teams)       │  │              │   │
│  └────────────┘  └──────────────┘  └───────────────┘  └──────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

Data flows strictly downward. The frontend never calls back into Python. The model core never touches the network. The backtest reads the same model core the exporter uses, so there is one code path, not two.

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Ingest / cache** | Pull nflverse data, aggregate heavy PBP into team-game rows, normalize franchise codes, write canonical parquet | `nflreadpy` (returns **Polars** DataFrames) with `NFLREADPY_CACHE=filesystem`; per-season PBP aggregate parquet files |
| **Team-game table** | One long-format row per (team, game): date, season, week, opponent, home/away, points for/against, result, spread, team EPA/play off/def, QB EPA | Built once in ingest; the "fact table" everything else reads |
| **Base strength (Elo)** | Chronological replay producing pre-game and post-game Elo per team-game; offseason regression + draft bump | Plain Python loop over ~7.5k games (fast enough; no need to vectorize) |
| **Season simulator** | Given ratings as of a snapshot, simulate the rest of the season → playoff odds, projected wins; also preseason expected wins | NumPy Monte Carlo (e.g. 5–10k sims), simplified tiebreakers |
| **Feature builder** | For each team-game, compute every factor using **only information available at that moment** | Polars/pandas rolling windows over the team-game table sorted by date, grouped by franchise |
| **Score combiner** | Standardize factors within each league snapshot, apply weights, produce score (0–100), mood label, per-factor contributions | Pure function: `features_df, weights → scores_df` |
| **Backtest harness** | Walk-forward evaluation: score at time t vs outcomes in games t+1..t+N; compare against baselines | Script producing a metrics table + a few plots |
| **Weight tuner** | Fit weights on training seasons, report out-of-sample performance; human rounds to final "opinionated" weights | `sklearn` Ridge / `scipy.optimize.nnls` |
| **Callout detector** | Scan full score history for notable patterns, emit structured callouts with templated copy | Rule functions, each returning `list[Callout]` |
| **JSON exporter** | Shape score tables into frontend-friendly, split JSON files | Small module; the ONLY place that knows the JSON schema |
| **Frontend** | Load JSON, route between board/team/history views, draw charts | Static SPA, no backend (framework choice → STACK.md) |

## Recommended Project Structure

```
feel-good-scorew/
├── README.md
├── CLAUDE.md                     # project conventions (optional)
├── pipeline/                     # Python package — everything up to JSON
│   ├── pyproject.toml            # uv-managed; self-contained deps
│   ├── weights.yaml              # committed, opinionated final weights + mood bands
│   ├── fgs/
│   │   ├── __init__.py
│   │   ├── cli.py                # `fgs ingest | build | backtest | tune | export | all`
│   │   ├── config.py             # paths, seasons range, constants (K, HFA, N horizon)
│   │   ├── ingest/
│   │   │   ├── schedules.py      # load_schedules → games.parquet
│   │   │   ├── pbp_agg.py        # load_pbp per season → team_game_epa_{season}.parquet
│   │   │   ├── draft.py          # load_draft_picks + value chart → draft_capital.parquet
│   │   │   ├── expectations.py   # win totals CSV (optional) → preseason_expect.parquet
│   │   │   └── franchises.py     # OAK→LV, SD→LAC, STL→LA mapping; canonical franchise_id
│   │   ├── model/
│   │   │   ├── team_games.py     # build long team-game fact table
│   │   │   ├── elo.py            # replay; offseason regression; draft bump
│   │   │   ├── simulate.py       # Monte Carlo season sim (playoff odds, exp. wins)
│   │   │   ├── features.py       # all as-of factors
│   │   │   ├── combine.py        # z-score, weights, score, mood, contributions
│   │   │   └── snapshots.py      # expand team-game rows → (season, week, team) grid
│   │   ├── evaluate/
│   │   │   ├── targets.py        # next-N win%, next-N margin, per-game outcomes
│   │   │   ├── backtest.py       # walk-forward folds, metrics, baselines
│   │   │   └── tune.py           # fit weights on train folds
│   │   ├── publish/
│   │   │   ├── callouts.py       # "aha" detectors
│   │   │   └── export.py         # JSON writer (schema lives here only)
│   │   └── checks.py             # cheap invariants (32 teams/snapshot, no NaN, no leakage)
│   ├── data/                     # gitignored
│   │   ├── cache/                # nflreadpy filesystem cache
│   │   ├── interim/              # canonical parquet (games, team_game_epa_*, draft)
│   │   └── processed/            # features.parquet, scores.parquet, backtest/
│   └── external/                 # small hand-sourced CSVs committed (win totals, draft chart)
└── site/                         # static frontend
    ├── package.json
    ├── index.html
    ├── src/
    │   ├── data.ts               # fetch + cache JSON, typed
    │   ├── routes/               # board, team/:abbr, history, callouts
    │   ├── charts/               # mood-over-time, factor breakdown bars, sparkline
    │   └── copy/                 # mood label → playful text (or read from meta.json)
    └── public/data/              # pipeline output target (generated; can be committed for deploy)
```

### Structure Rationale

- **`pipeline/` vs `site/` split:** two self-contained toolchains (Python, JS) with a single contract between them: the JSON files in `site/public/data/`. Either side can be rewritten without touching the other. This also fits the repo rule that each project is self-contained.
- **`ingest/` is the only network-touching code.** Everything in `model/` and `evaluate/` takes DataFrames in and returns DataFrames out. That makes the backtest deterministic and fast to rerun.
- **`model/` is shared by `evaluate/` and `publish/`.** The backtest must score the exact code that ships. A separate "backtest version" of feature logic is the most common way leakage and drift sneak in.
- **`weights.yaml` committed, not computed at export time.** The project calls for fixed, opinionated weights. The tuner *proposes*, a human *commits*. Export reads the file, so the weekly refresh never silently changes the model.
- **`external/` for small hand-curated CSVs.** Preseason win totals and draft value charts aren't in nflverse, so they're versioned inputs.

## Architectural Patterns

### Pattern 1: Long team-game fact table + chronological replay

**What:** Convert schedules (one row per game, home/away columns) into two rows per game, one from each team's perspective (`franchise_id, opp_id, is_home, pf, pa, margin, result, date, season, week, game_seq`). All features are rolling ops over this table grouped by franchise and sorted by `date`. Elo is a single forward loop over games sorted by date that writes `elo_pre` / `elo_post` into it.
**When to use:** Always. This is the standard shape for team rating systems.
**Trade-offs:** Duplicates game rows (trivial at ~15k rows). Makes "last 16 regardless of season" a plain `rolling(16)` with no season grouping.

**Example:**
```python
# features.py — as-of rolling: shift(1) so the row for game g only "knows" games < g
# when computing PRE-game features; post-game score uses games <= g.
tg = tg.sort(["franchise_id", "date"])
tg = tg.with_columns(
    pl.col("win").rolling_mean(16, min_samples=4).over("franchise_id").alias("last16_win_pct"),
    pl.col("off_epa_pp").ewm_mean(half_life=4).over("franchise_id").alias("off_epa_ewm"),
)
```

**Pre- vs post-game convention (decide once, document in config):** the feel-good score after game g describes the team *after* g (uses games ≤ g). The backtest target is games g+1..g+N. Elo inputs for game g use `elo_pre` (≤ g-1). Getting this wrong is the main leakage risk. See Pattern 4.

### Pattern 2: Two-speed rating = slow base + fast momentum terms

**What:** Split the score into (a) a **base strength term**, an Elo with margin-of-victory multiplier, modest K, and offseason regression toward the mean, and (b) **momentum/trajectory terms** that are deliberately faster-moving: last-16 record, EPA EWMA slope, streak, QB trend, change in playoff odds. Every term is a column. The combiner standardizes and weights them.

Reference Elo parameters to start from (FiveThirtyEight's published NFL Elo, from training knowledge, **MEDIUM confidence**; their methodology page now redirects and the GitHub repo only confirms HFA=65): K≈20, HFA≈48–65 Elo points, MOV multiplier `ln(|MOV|+1) * 2.2 / (elo_diff_winner*0.001 + 2.2)` (the autocorrelation correction), mean 1505, regress 1/3 toward mean each offseason. Treat these as starting values for the backtest, not facts to defend.

**Factor definitions (as-of after game g):**

| Factor | Definition | Notes |
|--------|-----------|-------|
| `elo` | post-game Elo | slow base term |
| `season_win_pct` | current-season W% (ties = 0.5) | resets each season; early-season shrink toward 0.5 (e.g. add 2 phantom .500 games) |
| `last16_win_pct` | rolling 16 team-games, crossing seasons | the project's signature input |
| `epa_trend` | EWMA of (off EPA/play − def EPA/play allowed), plus optionally slope over last ~6 games | from PBP aggregates; use the level, not only the slope (slope alone is noisy) |
| `margin` | EWMA of point margin, capped (e.g. ±21) | separate from opponent quality, per the decision log |
| `opp_quality` | mean of opponents' **pre-game** Elo over the window, signed by result (beat good teams = +) | never use opponents' later ratings |
| `vs_expectation` | (actual wins − expected wins to date) where expectation comes from the preseason projection | see Integration Points for the source |
| `playoff_odds_delta` | change in simulated playoff odds over last ~3 weeks (and/or the level) | from simulator |
| `streak` | signed current streak, crossing seasons, capped (e.g. ±6) | low weight expected; mostly flavor |
| `close_game_luck` | (one-score wins − expected one-score wins) over the window; **negative weight or regressed** | luck should *temper* feel-good, since close-game records regress |
| `qb_trend` | EWMA of the team's QB EPA/dropback (or EPA+CPOE composite) | aggregate from PBP by `passer_player_id`; detect QB changes |

**Trade-offs:** Many correlated inputs (last16, margin, epa, elo all overlap). Ridge regularization in the tuner and a sensible human prior handle this. Don't chase a "clean" orthogonal decomposition.

### Pattern 3: Snapshot-standardized linear combiner with contributions

**What:** For each league snapshot (season, week), z-score each factor across the 32 teams. `score_raw = Σ wᵢ · zᵢ`. Map to 0–100 (e.g. `50 + 15 * score_raw / sd_ref`, clipped, or a logistic). Store `contribᵢ = wᵢ · zᵢ` per factor. Those contributions *are* the factor breakdown on the team page, and they sum exactly to the score, which keeps the explanation honest.
**When to use:** Always for this project. Linear-with-contributions is the simplest model that is both tunable and explainable.
**Trade-offs:**
- Per-snapshot z-scoring makes the score **relative to the league that week**, which is good for ranking and mood but makes cross-era comparison ("saddest fanbase ever") relative too. That's acceptable and arguably right.
- In week 1 and the offseason, many factors are degenerate (season W% is undefined). Handle with an explicit **phase-aware weight set**: `weights.offseason`, `weights.early` (weeks 1–4), `weights.regular`. Or simpler: shrink early-season factors toward 0 by sample size before z-scoring. Prefer the shrinkage approach because it keeps one weight set.

**Example:**
```python
def combine(feat: pl.DataFrame, w: dict[str, float]) -> pl.DataFrame:
    z = feat.with_columns([
        ((pl.col(f) - pl.col(f).mean().over("snap")) / pl.col(f).std().over("snap")).alias(f"z_{f}")
        for f in w
    ])
    z = z.with_columns([(pl.col(f"z_{f}") * w[f]).alias(f"c_{f}") for f in w])
    return z.with_columns(pl.sum_horizontal([f"c_{f}" for f in w]).alias("score_raw"))
```

### Pattern 4: Snapshot grid + as-of join (leakage firewall)

**What:** The frontend and backtest think in league snapshots `(season, week)`, but teams have byes and the playoffs drop teams. Build a full grid `(season, week, franchise_id)` and **as-of join** each team's latest team-game row with `date <= snapshot_cutoff`. Byes carry forward; eliminated teams carry their final in-season score into the offseason. Define the snapshot cutoff as the Tuesday after the week's games.
**Why it matters:** One consistent "as of" timestamp gives you (1) leakage-free backtests, (2) 32 teams in every snapshot, and (3) a clean week axis for the mood-over-time chart.
**Snapshot keys:** `week 0` = post-draft offseason snapshot (late April/May); weeks 1–18 (or 1–17 pre-2021) regular; 19–22 playoffs. Add a pre-season "week 0" per season so the draft bump has somewhere to live.

### Pattern 5: Offseason transition as an explicit step

**What:** Between the last game of season S and week 1 of S+1, run a named `offseason_transition(ratings, draft_capital)` function:
1. Elo: `elo ← mean + (1 − r)(elo − mean)`, with r ≈ 1/3 as a tunable.
2. Draft bump: `elo += k_draft · f(draft_capital)`. To honor **"no tanking reward"**, use capital *relative to slot expectation* (net value gained via trades/compensatory picks) or a heavily capped absolute term, so the worst team doesn't automatically get the biggest bump. Tune k_draft in the backtest. It may well come out near zero, which is a fine and honest result.
3. Momentum terms crossing the boundary: last16 and streak continue as-is (by design). EPA/QB EWMAs get an extra decay toward league mean (rosters change). `season_win_pct` and `vs_expectation` reset.
4. Recompute preseason expected wins (simulator on the new ratings) → feeds `vs_expectation` for S+1.

**Trade-offs:** Explicit and testable, versus hiding regression inside the Elo loop. The extra function is worth it because offseason behavior is a visible product feature ("score reacts to the draft").

### Pattern 6: Walk-forward backtest with baselines

**What:** Folds by season. For test season Y: tune weights on seasons `[start, Y−1]`, score season Y with those weights, record metrics. Report the mean across Y = 2005..2025. Hold out the last 2–3 seasons entirely until weights are final.
**Targets (compute all, pick one primary):**
- **Primary: next-N-games win% (N=4 and N=8)** and **next-N average point margin**. Margin is less noisy, so it's the better tuning target. Report win% because it's the story.
- **Per-game:** convert score difference (+HFA) into a win prob via a 1-parameter logistic fit on train folds; report **Brier / log loss** on each subsequent game.
- Targets crossing season boundaries are allowed (they're the point of last16) but should be reported separately for "within-season" vs "across-offseason".

**Baselines (the score must beat these or the story fails):**
1. Pure Elo (no momentum).
2. Current-season W%.
3. Last-16 W% alone.
4. Vegas closing spread (`spread_line` in nflverse schedules): the ceiling, not something to beat. It shows how close you get.

**Tuning:** standardized features → `Ridge` (or NNLS if you want sign constraints matching intuition, e.g. luck ≤ 0) against next-N margin. Then a human rounds to "opinionated" weights and confirms the out-of-sample metric barely moves. Write the rounded weights to `weights.yaml` along with the backtest metrics they achieved.

## Data Flow

### Pipeline Flow (weekly refresh, `fgs all`)

```
nflverse (GitHub releases) ──nflreadpy──▶ data/cache/ (filesystem cache)
        │
        ▼
ingest: schedules → games.parquet
        pbp(season) → team_game_epa_{season}.parquet   (only CURRENT season re-aggregated weekly)
        draft_picks → draft_capital.parquet
        external/*.csv → preseason_expect.parquet
        │
        ▼
model: team_games (long fact table, franchise-normalized)
        → elo replay (+ offseason_transition)       → elo_pre/elo_post
        → simulate (per snapshot)                   → playoff_odds, exp_wins
        → features (as-of)                          → features.parquet
        → snapshots (grid + as-of join)             → snapshot_features.parquet
        → combine(weights.yaml)                     → scores.parquet (score, mood, c_*)
        │
        ├──▶ evaluate (dev only): backtest/tune     → processed/backtest/*.csv, proposed weights
        ▼
publish: callouts(scores)                           → callouts list
         export(scores, callouts, meta)             → site/public/data/*.json
        │
        ▼
site: fetch JSON → render (local `vite dev` / static host)
```

Full replay from 1999 is cheap once PBP is aggregated (~7.5k games, a Python Elo loop runs in well under a second). The only expensive step is PBP download/aggregation. Cache the per-season aggregates and recompute everything downstream from scratch every run. **Don't build incremental model updates.** The complexity isn't worth it at this size.

Simulation cost: ~28 seasons × ~22 snapshots × 5k sims ≈ 3M simulated seasons. Vectorized NumPy over the remaining schedule handles this in minutes. Cache the sim outputs keyed by (season, week, model_version) so backtest iterations on *weights* don't re-simulate. Weights don't affect Elo, so sims stay valid.

### Frontend Data Flow

```
App boot ──fetch──▶ data/meta.json      (factors, weights, mood bands, data_through, latest snapshot key)
         ──fetch──▶ data/latest.json    (current league snapshot → Mood board)
Team click ─fetch─▶ data/teams/{ABBR}.json  (full history + latest breakdown)
History tab ─fetch▶ data/history.json   (compact matrix: every team × every snapshot score)
Callouts  ──fetch─▶ data/callouts.json
Week picker ─fetch▶ data/snapshots/{season}-{week}.json  (lazy; any historical board)
```

Hash-based routing (`#/team/KC`) works on any static host with zero config. No state library is needed: each route fetches its file and renders it.

### JSON Export Shape

Estimated volume: ~28 seasons × ~22 snapshots × 32 teams ≈ 20k team-snapshots. With ~11 factor contributions each, a single file would be several MB, so split by access pattern.

**`meta.json`** (~5 KB)
```json
{
  "model_version": "2026.11.1",
  "generated_at": "2026-11-11T09:00:00Z",
  "data_through": {"season": 2026, "week": 10},
  "latest": {"season": 2026, "week": 10},
  "factors": [
    {"key": "last16_win_pct", "label": "Last 16 games", "weight": 0.22, "description": "..."}
  ],
  "mood_bands": [
    {"min": 85, "label": "Planning the parade"},
    {"min": 0,  "label": "Refreshing draft mocks"}
  ],
  "backtest": {"target": "next8_margin", "r": 0.41, "brier_next_game": 0.221,
               "baselines": {"elo": 0.224, "season_wpct": 0.236, "vegas": 0.208}},
  "teams": [{"abbr": "KC", "name": "Chiefs", "colors": ["#E31837", "#FFB81C"], "franchise_id": "KC"}]
}
```

**`latest.json` / `snapshots/{season}-{week}.json`** (~10 KB each)
```json
{
  "season": 2026, "week": 10, "phase": "regular",
  "teams": [
    {"abbr": "DET", "rank": 1, "score": 88.4, "delta_1w": 2.1, "mood": "Planning the parade",
     "record": "8-1", "last16": "13-3", "playoff_odds": 0.97,
     "contrib": {"elo": 9.1, "last16_win_pct": 6.2, "epa_trend": 4.0, "close_game_luck": -1.3}}
  ]
}
```

**`teams/{ABBR}.json`** (~60–120 KB each; 32 files)
```json
{
  "abbr": "DET",
  "latest": { "...same as snapshot row plus raw factor values...": true,
              "raw": {"last16_win_pct": 0.8125, "epa_trend": 0.14}},
  "history": {
    "keys":  ["1999-0", "1999-1", "..."],
    "score": [41.2, 43.0, "..."],
    "rank":  [22, 20, "..."],
    "contrib": {"elo": [ ... ], "last16_win_pct": [ ... ]}
  },
  "games": [{"season": 2026, "week": 9, "opp": "GB", "home": true, "pf": 27, "pa": 20, "score_after": 88.4}],
  "callouts": ["det-2026-w10-record-vs-score"]
}
```
Use column-oriented arrays (`keys` plus parallel arrays) for history. They're ~3–5x smaller than arrays of objects and map directly onto chart libraries.

**`history.json`** (~250–400 KB): `{"keys": [...snapshot keys...], "teams": {"DET": [scores...], ...}}`, scores only, rounded to 1 decimal. Powers the all-teams mood-over-time chart.

**`callouts.json`**
```json
[{"id": "pit-2026-w10-record-vs-score", "type": "record_vs_score", "team": "PIT",
  "season": 2026, "week": 10, "severity": 0.9,
  "headline": "7-2 but you should feel worried",
  "detail": "Record ranks 4th; feel-good score ranks 19th. 3-0 in one-score games, EPA trend falling.",
  "evidence": {"record_rank": 4, "score_rank": 19, "close_game_luck": 2.3}}]
```

**Precomputed "aha" detectors** (in `publish/callouts.py`, each a pure function over `scores.parquet`):
- `record_vs_score`: |rank(season W%) − rank(score)| ≥ threshold → "8-2 but worried" / "3-6 but feel better".
- `misery_streak`: longest run of consecutive snapshots below a mood band, measured in **calendar days** from game dates → "miserable for 600 straight days".
- `historical_extremes`: all-time lowest/highest score, biggest single-week drop/rise, longest top-5 run.
- `vs_expectation`: biggest over/under-performers vs preseason projection this season.
- `luck_warning`: high close-game luck with a weak EPA trend.
Each returns structured evidence. Text is generated from templates in Python, so the frontend just renders strings. Rank by `severity` and cap at ~3 per team per season.

### Key Data Flows

1. **Weekly refresh:** `fgs all` → re-aggregate current-season PBP → full replay → export → (optional) commit `site/public/data` and deploy. Idempotent: running it twice gives identical output.
2. **Model iteration (dev):** edit `features.py` → `fgs backtest` (reads cached interim + cached sims) → compare metrics table → update `weights.yaml` → `fgs export`.
3. **User navigation:** board (latest.json) → team click (teams/X.json) → history chart (history.json), with each file fetched at most once per session.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Local / handful of friends | Everything as described; JSON served by `vite dev` or `python -m http.server` |
| Public static deploy (1k–100k visitors) | Same files on Vercel/Netlify CDN; static JSON scales for free. Add long cache headers and include `model_version` in the path or a query param to bust caches |
| Viral share moment | Still static. Only add prerendered OG images per callout (build-time) if share previews matter |

### Scaling Priorities

1. **First bottleneck: PBP ingest time/size.** ~28 seasons of PBP is large (hundreds of MB to GB, 370+ columns). Fix: aggregate to team-game rows immediately with column projection, persist per-season aggregates, and never reload historical PBP on weekly runs.
2. **Second bottleneck: simulation in the backtest loop.** Fix: cache sim results keyed by Elo parameters; weight tuning never re-simulates.
3. **Frontend payload:** keep `history.json` scores-only and lazy-load team files. Not a real problem at this size.

## Anti-Patterns

### Anti-Pattern 1: Feature logic duplicated between backtest and export

**What people do:** Write a quick vectorized version for the backtest and a "real" version for export.
**Why it's wrong:** The two drift, so the published score isn't the one you validated, and leakage hides in one of them.
**Do this instead:** One `model/` package. Backtest = `combine(features, weights)` on historical snapshots plus target join.

### Anti-Pattern 2: Using end-of-season or future information in features

**What people do:** Opponent quality = opponent's *final* Elo or final record. Expectation = "actual" playoff seeds. Z-score using the whole season's mean.
**Why it's wrong:** Inflates backtest accuracy, so "you should feel better" becomes false advertising.
**Do this instead:** Opponent's `elo_pre` at game time. Snapshot-only z-scores. A `checks.py` assertion that every feature's source max date ≤ snapshot cutoff (cheap to implement via an `asof_date` column).

### Anti-Pattern 3: Tuning weights on all seasons and reporting in-sample fit

**What people do:** Fit ridge on 1999–2025 and report its R².
**Why it's wrong:** Overstates predictive power, and with ~11 correlated factors it overfits.
**Do this instead:** Walk-forward by season plus a final untouched holdout (2023–2025). Report out-of-sample only.

### Anti-Pattern 4: Frontend computes the model

**What people do:** Ship raw factors and weights, then compute score/mood/callouts in JS.
**Why it's wrong:** Two implementations, and user-tunable weights are explicitly out of scope.
**Do this instead:** Frontend renders precomputed `score`, `mood`, `contrib`, and callout text. It may *display* raw factor values for tooltips.

### Anti-Pattern 5: Keying history by team abbreviation as displayed

**What people do:** Group by `team` straight from nflverse.
**Why it's wrong:** Relocations (OAK→LV 2020, SD→LAC 2017, STL→LA 2016) split franchise histories. That breaks last-16 across seasons, the "600 straight days" calculations, and the history chart. Historical abbreviations in nflverse datasets differ by table (verify per dataset; LOW–MEDIUM confidence on exact codes).
**Do this instead:** `franchises.py` maps every raw code to a canonical `franchise_id` at ingest. Display uses current abbr/name from `meta.json`.

### Anti-Pattern 6: Absolute draft capital as the offseason bump

**What people do:** Add Σ(draft chart value) to the rating.
**Why it's wrong:** The worst team always gets the most capital, which is exactly the tanking reward the project rules out.
**Do this instead:** Capital relative to slot-expected capital (trades/comp picks), or a small capped term, with k tuned and allowed to land at ~0.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| nflverse via `nflreadpy` | `load_schedules(seasons=True)`, `load_pbp(season)`, `load_draft_picks(seasons=True)`, `load_teams()`. All return **Polars** DataFrames (HIGH, official API docs) | Set `NFLREADPY_CACHE=filesystem`, `NFLREADPY_CACHE_DIR=pipeline/data/cache`; default cache mode is memory-only (HIGH, official config docs). Schedules include `spread_line`/`total_line` (MEDIUM, training knowledge; verify column names) |
| Preseason win totals | Hand-curated `external/win_totals.csv` | **Not in nflverse.** No clean free CSV found back to 1999. Sources like sportsoddshistory.com and nfeloapp (2003+) are browsable but not packaged (LOW). **Recommended architecture:** primary expectation = model's own preseason projection (simulator on post-offseason Elo vs. the schedule), which is always available and leakage-free. Optional override with real win totals where the CSV has them. Keep `vs_expectation` source-agnostic behind `preseason_expect.parquet` |
| Playoff odds | Computed by `simulate.py` | No free historical weekly playoff-odds archive is assumed. Simulate with simplified tiebreakers (division record → conference record → coin flip). Error is small for a trend input. Seeding/field rules change by era: 12 teams pre-2020, 14 from 2020 |
| Draft value chart | `external/draft_value.csv` (e.g. Jimmy Johnson or a modern surplus-value chart) | Static 1–262 pick table; choice of chart is a tuning detail |
| Static hosting | Build `site/` → `dist/`; Vercel static | Commit generated JSON or run the pipeline locally before deploy. No server functions needed |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| ingest ↔ model | Parquet files in `data/interim/` | Model never imports nflreadpy. Makes the model testable offline |
| model ↔ evaluate | Direct function calls (DataFrames) | Same functions, so no drift |
| evaluate ↔ publish | `weights.yaml` (human-in-the-loop) | Tuner writes `weights.proposed.yaml`; a human promotes it |
| publish ↔ site | JSON files in `site/public/data/` | **The only contract between Python and JS.** Mirror it as TypeScript types in `site/src/data.ts` |

## Suggested Build Order

Dependencies drive this order. The backtest has to exist before momentum terms get tuned, and the frontend needs a stable JSON contract before real data shows up.

1. **Ingest + team-game fact table + franchise mapping.** Everything depends on it. Deliverable: `games.parquet`, `team_game_epa_*.parquet` for 1999→2026, sanity-checked (32 teams, game counts per season).
2. **Base Elo + offseason regression (no draft yet) + snapshot grid.** Gives a working end-to-end score with one factor. Validate against known results (Brier ≈ published Elo-class numbers, roughly 0.22–0.23; MEDIUM).
3. **Backtest harness with baselines (Elo, season W%, last-16, Vegas spread).** Build it *before* adding momentum factors, so every new factor is justified by a metric delta. This is the project's core-value gate.
4. **Thin JSON export + skeleton frontend (board + team page) on Elo-only scores.** Locks the contract early and surfaces display needs (mood bands, ranks, deltas) before the model gets complex. Can run in parallel with step 5.
5. **Momentum features, in roughly decreasing expected value:** last16 → epa_trend → margin → opp_quality → qb_trend → close_game_luck → streak. Each one gets added, backtested, and kept or down-weighted.
6. **Season simulator → playoff_odds_delta + preseason expected wins → vs_expectation.** Its own step because it's the heaviest compute and needs caching. Optional external win totals land here.
7. **Weight tuning (walk-forward, ridge/NNLS) → rounded `weights.yaml` → final holdout check.**
8. **Offseason draft bump (week-0 snapshots)**, tuned with k allowed to be ~0. Depends on 2, 3, and 7.
9. **Callout detectors + full export (history.json, snapshots, callouts.json).**
10. **Frontend polish:** mood-over-time chart, callout cards, playful copy, week picker. Then the weekly refresh script/README, and optional Vercel deploy.

**Phase grouping suggestion for the roadmap:** (A) Data foundation = 1; (B) Base model + backtest = 2–3; (C) Contract + skeleton UI = 4; (D) Momentum model = 5–7; (E) Offseason + insights = 8–9; (F) Viz polish + refresh = 10.

**Phases likely needing deeper research:** D (factor definitions, QB attribution, close-game luck formula), E (draft bump that doesn't reward tanking; playoff-format history for the sim), and the preseason-expectation data source.

## Sources

- nflreadpy load function reference (all loaders return Polars DataFrames): https://nflreadpy.nflverse.com/api/load_functions/ (HIGH)
- nflreadpy configuration (cache_mode memory/filesystem/off, `NFLREADPY_CACHE`, `NFLREADPY_CACHE_DIR`, `NFLREADPY_CACHE_DURATION`): https://nflreadpy.nflverse.com/api/configuration/ (HIGH)
- FiveThirtyEight nfl-elo-game repo (HFA default 65, MOV multiplier parameter): https://github.com/fivethirtyeight/nfl-elo-game (MEDIUM; their methodology page now redirects away, so K=20 / 1/3 regression / MOV formula come from training knowledge, MEDIUM-LOW)
- FiveThirtyEight NFL Elo dataset mirror: https://datahub.io/fivethirtyeight/nfl-elo (reference ratings for sanity checks through 2022/23; LOW-MEDIUM)
- Win totals availability: https://www.nfeloapp.com/nfl-power-ratings/nfl-win-totals , https://www.sportsoddshistory.com/about-us (no packaged CSV found; LOW)
- Historical win-totals research context: https://www.rotowire.com/article/nfl-win-totals-what-data-tells-us-105750 (LOW)

---
*Architecture research for: NFL momentum-weighted feel-good score + static viz*
*Researched: 2026-11-11*

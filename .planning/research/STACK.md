# Stack Research

**Domain:** NFL team rating model (momentum-weighted Elo variant) + backtest pipeline in Python that outputs static JSON, read by a static chart-heavy frontend
**Researched:** 2026-11-11
**Confidence:** HIGH for data and library versions (checked live against PyPI, npm, and nflverse data on 2026-11-11). MEDIUM for the expectations and playoff-odds data strategy (preseason win totals have gaps, see below).

## TL;DR (prescriptive)

- **Data:** `nflreadpy` 0.1.5. It returns **Polars** DataFrames. One package covers schedules (with spread, total, moneyline, and starting QB), play-by-play with EPA from 1999, draft picks, and team metadata.
- **Compute:** Python 3.13, managed with `uv`. Use **Polars 2.x** for the data work and **NumPy** for the Elo loop and Monte Carlo. Write the Elo yourself; don't use an Elo library. Fit factor weights with **scikit-learn**, and tune the few non-linear hyperparameters (K, decay half-lives, regression-to-mean) with **Optuna**.
- **Expectations:** Use the nflverse `win_totals.csv` (Vegas lines, **2003–2020 only**). Fill 2021–2026 by hand from sportsoddshistory (now on covers.com), about 192 numbers. For 1999–2002, fall back to a model-derived preseason expectation.
- **Playoff odds:** **Compute them yourself** with a Monte Carlo season simulation driven by your own ratings. There is no free historical playoff-odds dataset. The only mature implementation, nflseedR, is R-only and has no Python port.
- **Output:** Plain `json` from the standard library, with rounded floats. Split into a small "latest" file, one file per team, and one compact columnar history file.
- **Frontend:** **Vite 8 + Svelte 5 (plain, not SvelteKit) + Observable Plot 0.6.19**, with hash routing. Vercel serves the `dist/` output as a static site with zero config.

## Recommended Stack

### Core Technologies

| Technology | Version (verified) | Purpose | Why Recommended | Confidence |
|------------|-------------------|---------|-----------------|------------|
| Python | 3.13 (local machine has 3.13.1) | Pipeline runtime | NumPy 2.5 needs >=3.12 and Polars/pandas need >=3.11. 3.13 is installed locally and every package below supports it. | HIGH |
| uv | 0.13.7 latest (0.10.12 installed locally) | Env, deps, lockfile, `uv run` | nflreadpy's own README recommends it. One `pyproject.toml` plus `uv.lock` inside `feel-good-scorew/pipeline/` keeps the project self-contained, which the repo rule requires. | HIGH |
| nflreadpy | 0.1.5 (released 2025-11-19; Python >=3.10) | Every NFL data load | The official nflverse Python loader, ported from nflreadr. It has caching and returns Polars. **Verified live:** `load_schedules()` returns 7,548 games for 1999–2026 with `spread_line`, `total_line`, `home_moneyline`/`away_moneyline`, `home_qb_id`/`away_qb_name`, `div_game`, and rest days. `load_pbp([1999, 2026])` loaded in 2.2s with 372 columns, and `epa` is populated in 1999 (1.1% null). `load_draft_picks()` runs through the 2026 draft. `get_current_week()` returned 10. | HIGH |
| Polars | 2.1.0 | DataFrame work: rolling windows, joins, group-bys | nflreadpy returns Polars natively, so pandas would mean converting every load. Rolling-window and group-by expressions (`rolling_mean().over("team")`) fit the "last 16 games across season boundaries" input directly. Live probe: nflreadpy 0.1.5 works with polars 2.1.0. | HIGH |
| NumPy | 2.5.4 | Sequential Elo update loop, Monte Carlo season sims | Elo is inherently sequential, game by game, which DataFrames handle badly. Write it as a plain loop over a NumPy array or Python dicts. About 7.5k games runs in well under a second. Vectorize the Monte Carlo as (sims × games) matrices. | HIGH |
| Vite | 8.3.8 | Frontend dev server and static build | The standard static-SPA bundler. `vite build` produces a `dist/` folder that Vercel auto-detects. Requires Node `^20.19.0 \|\| >=22.12.0`. | HIGH |
| Svelte | 5.57.3 (with `@sveltejs/vite-plugin-svelte` 7.3.1) | UI components | The least boilerplate for a small, mostly static, data-driven UI: a mood board, a team page, and a few charts. Observable Plot returns plain DOM nodes, and those mount in Svelte with a two-line action. Runes (`$state`, `$derived`) make it easy to wire team selection to charts. | MEDIUM (React would work just as well; this is a taste call) |
| Observable Plot | 0.6.19 (released 2026-11-05) | All charts | You get grammar-of-graphics charts in a few lines, D3 quality without D3 effort. It handles the core visuals: multi-series line charts for mood over time with 32 teams and per-team highlighting, ranked bar charts, factor breakdowns, and tooltips via the `tip` mark. Built on D3. | HIGH |

### Supporting Libraries

| Library | Version (verified) | Purpose | When to Use | Confidence |
|---------|-------------------|---------|-------------|------------|
| scikit-learn | 1.9.1 | Fitting factor weights (`RidgeCV` / `LogisticRegression`), Brier and log-loss metrics, CV splits grouped by season | The backtest weight fit. Standardize each factor, then regress it on a target like next-8-games win% or next-game win/loss. Use leave-seasons-out or forward-chaining CV. Ridge keeps the weights stable and easy to read. | HIGH |
| Optuna | 5.0.0 | Tuning non-differentiable hyperparameters: Elo K, home-field Elo, MOV multiplier shape, season regression fraction, momentum half-lives | When you have more than about 3 interacting hyperparameters. TPE plus a fixed seed gives reproducible results. With 3 or fewer, a `itertools.product` grid is enough and you can drop the dependency. | HIGH (version), MEDIUM (necessity) |
| SciPy | 1.18.1 | `scipy.stats.norm.cdf` to turn spreads into win probabilities, `scipy.optimize` for small one-off fits (e.g. the Elo-to-points scale) | Converting spreads to probabilities (NFL margin SD is about 13.5) and fitting single parameters. | HIGH |
| pyarrow | 26.0.1 | Parquet read/write for the slimmed raw-data snapshot | Only if you persist intermediate parquet with pandas. Polars has its own parquet writer, so you can usually skip it. | HIGH |
| pandas | 3.1.1 | Optional. Only for libraries that need it. | Avoid as the main frame library. pandas 3.x changed defaults (Copy-on-Write always on, Arrow-backed strings), so older nflfastR/pandas tutorials will break in small ways. | HIGH |
| matplotlib (optional) | latest | Quick backtest diagnostic plots in notebooks or scripts | Only for model-dev sanity plots. These aren't shipped. | MEDIUM |

### Data Sources (free)

| Need | Source | Coverage (verified) | Notes | Confidence |
|------|--------|---------------------|-------|------------|
| Games, scores, OT, home/away, div games, rest | `nfl.load_schedules()` | 1999–2026 (136 of 272 2026 games had results on 2026-11-11) | Raw codes mix eras: `OAK`/`LV`, `SD`/`LAC`, `STL`/`LA`. Map them to a franchise ID or team histories break. HOU starts in 2002, and 1999–2001 had 31 teams. | HIGH |
| Closing spread / total | same, `spread_line`, `total_line` | Spreads for every game since 1999 | `spread_line` is positive when the home team is favored. Check the sign convention against `result` (home score minus away score) before using it. These are closing lines, not opening lines. | HIGH |
| Moneylines | same, `home_moneyline`/`away_moneyline` | Starts in 2006 (partial), full from 2007 | Don't rely on these for 1999–2005. Spreads cover every year. | HIGH |
| Starting QB per game | same, `home_qb_id`, `home_qb_name` | 1999+ | Join to pbp `passer_player_id` to compute QB EPA per dropback or CPOE trends (CPOE is only reliable from 2006 onward). | HIGH |
| Play-by-play with EPA, WP, success | `nfl.load_pbp(seasons)` | 1999–current (2026 data through week 9 at research time) | 372 columns, so select about 15 right after loading and save a slim parquet. Filter on `pass==1 \| rush==1` and drop garbage-time plays for EPA/play. | HIGH |
| Team-level game stats | `nfl.load_team_stats(seasons, summary_level="week")` | 1999+ | A possible shortcut that skips aggregating pbp yourself. Check its EPA columns before relying on it. | MEDIUM |
| Draft picks | `nfl.load_draft_picks()` | 1980–2026 | `season, round, pick, team, ...`. | HIGH |
| Draft value chart | nflverse `nfldata/data/draft_values.csv` (raw GitHub URL; nflreadpy has no loader) | Picks 1–262, columns `stuart, johnson, hill, otc, pff` | Use `stuart` (AV-based) or `otc`. The Johnson chart overvalues top picks. | HIGH |
| Preseason win totals | nflverse `nfldata/data/win_totals.csv` (raw GitHub URL; nflreadpy has no loader) | **2003–2020 only** (576 rows = 18 × 32); `season, team, line, over_odds, under_odds` | **Gap for 1999–2002 and 2021–2026.** See the strategy below. | HIGH (on the gap) |
| Team colors, logos, names | `nfl.load_teams()` | current franchises | Use the colors for chart highlighting. Logos are on external URLs; hotlinking is fine for a prototype. | HIGH |
| Historical playoff odds | **None free and structured** | — | 538's archived `nfl-elo` data covers Elo and game probabilities (to about 2022), not week-by-week playoff odds. Compute playoff odds yourself. | MEDIUM |

#### Preseason expectations strategy (recommended)

1. **2003–2020:** Use `win_totals.csv` as is. Adjust the line for juice: compute the implied expected wins from `over_odds`/`under_odds`, or just use `line`.
2. **2021–2026:** Copy the lines by hand into `pipeline/data/manual/win_totals_2021_2026.csv` from sportsoddshistory.com's NFL win totals pages, which now redirect to covers.com/sportsoddshistory/nfl-win/. That's 32 × 6 = 192 numbers, about 20 minutes of work, and much less fragile than a scraper. (The page returned 503 to automated fetch during research, so plan on doing this by hand.) nfeloapp.com/nfl-power-ratings/nfl-win-totals also claims win totals history from 2003 onward, which you can use to cross-check.
3. **1999–2002:** Use a **model-derived expectation**: the team's preseason Elo (last season's final rating regressed toward the mean), run through the season simulator to get expected wins. On 2003–2020, check that this tracks the Vegas lines (expect r ≈ 0.7–0.8). If it does, you could use it as the fallback everywhere.
4. In the JSON, mark each expectation's source (`vegas` / `manual_vegas` / `model`) so the UI can be honest about it.

Don't build the preseason expectation by summing spread-implied win probabilities from in-season `spread_line`s. Those are closing lines set after the market has seen the team play, so they leak in-season information into a "preseason" input.

#### Playoff odds strategy (recommended: compute)

- After every week, simulate the rest of the regular season about 10k times. Each game's probability comes from your strength rating plus home field (or from `spread_line` via `norm.cdf(spread/13.5)` for games the market has priced). Then seed with simplified tiebreakers: win%, then head-to-head, then division record, then conference record, then a coin flip. Simplified tiebreakers land within a percent or two of full NFL tiebreakers almost always, which is fine for a "trend" input.
- **The rules vary by era, so encode them:** 6 divisions and 31 teams in 1999–2001; 8 divisions and 32 teams from 2002; 12 playoff teams until 2019 and 14 from 2020; 16 games until 2020 and 17 from 2021.
- Vectorized NumPy makes this fast: about 28 seasons × 18 weeks × 10k sims is fine on a laptop if you vectorize across sims. You only compute it once historically, then add one week at a time.
- nflseedR (R, MIT) is the reference implementation if you ever want full tiebreakers. Don't add R to the stack for this.

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | `uv init`, `uv add`, `uv run python -m pipeline.build` | Pin `requires-python = ">=3.13"`. |
| nflreadpy filesystem cache | Avoid re-downloading pbp every run | `NFLREADPY_CACHE=filesystem`, `NFLREADPY_CACHE_DIR=./pipeline/.cache` (gitignored). Better still, write a slim `raw/pbp_slim.parquet` once and only re-pull the current season each week. |
| Node | Frontend toolchain | Node 20.19 is installed locally and meets Vite 8's floor, but Node 20 reached EOL in April 2026. Use **Node 22 or 24 LTS** (`nvm install 24`). Vercel builds on 22/24 by default. |
| pnpm or npm | JS package manager | Both are installed. Either is fine; npm is simpler for a casual repo. |
| svelte-check | Type-checking `.svelte` files | **Pins TypeScript to ~6.0.** svelte-check 4.7.8 peers on `typescript ^5 \|\| ^6`. The create-vite Svelte template ships `typescript ~6.0.3`, while the React template already ships TS 7. Don't bump to TS 7 in the Svelte app. |
| Jupyter / marimo (optional) | Model exploration | Optional. Keep the real pipeline in `.py` scripts so the weekly refresh is a single command. |

## Installation

```bash
# --- pipeline (Python) ---
cd feel-good-scorew
mkdir pipeline && cd pipeline
uv init --python 3.13 --no-workspace
uv add nflreadpy polars numpy scipy scikit-learn optuna
uv add --dev matplotlib ipykernel   # optional, model dev only

# --- web (static frontend) ---
cd ..
npm create vite@latest web -- --template svelte-ts
cd web
npm install
npm install @observablehq/plot
# d3 only if you need d3-scale-chromatic/d3-format etc. directly (Plot already bundles d3 internally)
# npm install d3
```

Suggested layout:

```
feel-good-scorew/
  pipeline/            # uv project: load -> features -> elo -> sim -> score -> export
    data/manual/       # hand-entered win totals 2021+
    .cache/            # nflreadpy cache (gitignored)
  web/                 # Vite + Svelte
    public/data/       # pipeline writes JSON here (latest.json, teams/DET.json, history.json)
```

The pipeline writes straight into `web/public/data/`, so `vite build` copies the JSON into `dist/` and Vercel serves it statically. No API and no serverless functions.

### JSON emission

- Use the standard library `json.dump`. Round floats to 1–3 decimals before writing; this cuts file size by more than half.
- **Files:**
  - `latest.json`: 32 teams, current score, mood label, factor contributions. A few KB, enough for the home page by itself.
  - `teams/{TEAM}.json`: full weekly history plus factor breakdown, loaded when someone clicks a team.
  - `history.json`: **columnar** (`{"team":[...],"week_idx":[...],"score":[...]}`) for the all-teams mood-over-time chart. About 28 seasons × 32 teams × 22 weeks ≈ 20k points, which is a few hundred KB gzipped.
  - `meta.json`: generated_at, last season and week, weight vector, backtest metrics.
- `polars.DataFrame.write_json()` writes row-oriented JSON. That's fine for the small files, but build the columnar history with `{c: df[c].to_list() for c in cols}`.
- orjson and msgspec aren't needed at this size.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| nflreadpy | nfl_data_py 0.3.3 | Never for new work. It's the older community loader and still on PyPI. It has `import_win_totals()`, but that only reads the same 2003–2020 nfldata CSV. nflverse now points Python users to nflreadpy. |
| Polars | pandas 3.1 | If you're much more fluent in pandas. Call `.to_pandas()` once at load time. Expect friction from pandas 3 Copy-on-Write and string-dtype changes with older tutorials. |
| Hand-rolled Elo | `elote` 1.5.1, `skelo` 0.1.5, `elo` 0.1.1 | Basically never. The model needs MOV multipliers, season regression to the mean, home field, rest, QB adjustments, and separate momentum terms. Generic Elo libraries model chess-style bouts and fight all of that. The core update is about 15 lines. Reference: 538's NFL Elo methodology (K=20, MOV multiplier `ln(|MOV|+1) × 2.2/(Δelo×0.001+2.2)`, regress 1/3 toward 1505 between seasons, HFA about 48 Elo points, lower post-2020) and nfelo's open-source write-ups. |
| scikit-learn ridge for weights | Optuna on all weights directly | If the score has to be a non-linear transform of the factors. Even then, fitting the linear weights with Ridge and tuning only the hyperparameters with Optuna is faster and less prone to overfitting. |
| Svelte 5 + Vite | React 19.3 + Vite (`@vitejs/plugin-react` 6.3) | If you'd rather stay in React, or want Recharts or Nivo. It's equally deployable, with a bit more boilerplate for wiring up a DOM-returning chart lib (`useRef` + `useEffect`). |
| Plain Vite SPA with hash routing | SvelteKit + `adapter-static` | If you later want real per-team URLs with prerendered `<meta>` tags for social share cards (the "aha" moments). That's a reasonable upgrade in a later phase. Start plain. |
| Observable Plot | D3 7.9.2 directly | For one bespoke visual Plot can't do, such as a custom animated "mood ring" or a beeswarm with heavy interaction. You can mix them because Plot is D3 underneath. |
| Observable Plot | Recharts 3.10 | Only in a React app where you want declarative JSX charts. Its line charts get sluggish and verbose with 32 × 500+ points and highlight-on-hover. |
| Observable Framework | — | It's a strong fit on paper (data loaders in Python feeding a static site), but it's a separate opinionated build system, and its development pace has slowed. Vite + Plot gives you the same charts with a more conventional app structure for team drill-down. LOW confidence on its current maintenance status, so recheck before adopting. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| nfl_data_py | Legacy loader that nflverse has superseded. pandas-based and slower. | nflreadpy |
| Scraping PFR, ESPN, or sportsbooks for game data | Brittle, rate-limited, and against their terms. nflverse already has all of it. | nflreadpy |
| Generic Elo packages | Wrong abstraction; you'd fight them to add MOV and momentum terms. | ~15-line hand-rolled Elo in NumPy or plain Python |
| Random K-fold CV in the backtest | It leaks the future: games in the same season and week end up on both sides of the split. | Forward-chaining or leave-one-season-out CV, grouped by season |
| Summing in-season closing spreads as the "preseason expectation" | Look-ahead leakage | Vegas preseason win totals, or a model-derived preseason expectation |
| Next.js / SvelteKit SSR / any server runtime | Unneeded. The data changes weekly and is fully static. | Vite static build |
| Chart.js / ECharts | Workable, but more config-heavy for analytical small-multiples and highlight-one-of-32 line charts | Observable Plot |
| TypeScript 7 in the Svelte app | svelte-check 4.7.8 only supports TS 5/6 | `typescript ~6.0.3` (the template default) |
| Adding R (nflseedR, nflfastR) | Splits the stack for a marginal gain in tiebreaker accuracy | Simplified-tiebreaker Monte Carlo in NumPy |

## Stack Patterns by Variant

**If the full pbp history (about 1.3M plays × 372 cols) is slow or memory-heavy:**
- Load one season at a time, `select()` about 15 columns (`game_id, season, week, posteam, defteam, epa, success, pass, rush, qb_dropback, passer_player_id, cpoe, wp, qtr, score_differential`), and append to a slim parquet.
- After that, a weekly refresh only re-pulls `get_current_season()`.

**If the backtest shows the weights overfit (they swing a lot across CV folds):**
- Increase the Ridge alpha, or cut the factor set down. Several inputs are highly collinear: current record, last-16 record, and streak.

**If you deploy to Vercel later:**
- Framework preset "Vite", build `npm run build`, output `dist`, root directory `feel-good-scorew/web`. No `vercel.json` is needed with hash routing. With history-mode routing, add a SPA rewrite to `/index.html`.

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| nflreadpy 0.1.5 | polars 2.1.0, Python 3.13 | **Verified by live install and data load on 2026-11-11.** It requires `polars>=0.20` and uses pandas only through the `[pandas]` extra. Its lifecycle badge still says "experimental", so pin the exact version in `uv.lock`. |
| numpy 2.5.4 / scipy 1.18.1 | Python >=3.12 | This is the binding Python floor. |
| polars 2.1.0 / pandas 3.1.1 / scikit-learn 1.9.1 | Python >=3.11 | — |
| vite 8.3.x + @sveltejs/vite-plugin-svelte 7.3.x | Node ^20.19 or >=22.12 | Use Node 22/24 LTS. |
| svelte-check 4.7.8 | typescript ^5 or ^6 | Not TS 7. |
| @observablehq/plot 0.6.19 | any modern bundler (ESM) | Pre-1.0, so pin a minor version. The API has been stable across 0.6.x. |

## Sources

- PyPI JSON API (live, 2026-11-11): versions and `requires_python` for nflreadpy, polars, pandas, pyarrow, numpy, scipy, optuna, scikit-learn, statsmodels, nfl_data_py, uv, elote, skelo, elo. HIGH
- npm registry (live): vite, svelte, @sveltejs/vite-plugin-svelte, @vitejs/plugin-react, react, @observablehq/plot, d3, recharts, typescript, svelte-check (versions, engines, peers). HIGH
- nflreadpy README on PyPI, and https://nflreadpy.nflverse.com/api/load_functions/ for function list and parameters. HIGH
- Live probe in a scratch env: `nfl.load_schedules()`, `nfl.load_pbp([1999, 2026])`, `nfl.load_draft_picks()`, `nfl.get_current_week()` with nflreadpy 0.1.5 + polars 2.1.0. HIGH
- https://github.com/nflverse/nfldata, files `data/games.csv`, `data/win_totals.csv` (2003–2020), `data/draft_values.csv`, downloaded and inspected. HIGH
- create-vite templates (`template-svelte-ts`, `template-react-ts` package.json on vitejs/vite main): the TS 6 vs TS 7 split. HIGH
- nflseedR (CRAN / nflverse r-universe): an R-only playoff simulator with tiebreakers; no Python port found (also checked PyPI `nflseedr` and `nflseedpy`, both 404). MEDIUM
- sportsoddshistory.com/nfl-win/, which now 301-redirects to covers.com/sportsoddshistory/nfl-win/ (503 to automated fetch): manual source for 2021+ win totals. MEDIUM
- https://www.nfeloapp.com/nfl-power-ratings/nfl-win-totals: win totals history from 2003, for cross-checking. LOW to MEDIUM (from search results only)
- 538 NFL Elo methodology (K, MOV multiplier, regression to the mean): training knowledge plus the archived fivethirtyeight `nfl-elo` dataset references. MEDIUM. Re-derive the parameters through the backtest anyway.

---
*Stack research for: NFL momentum-weighted team rating + static data-viz site*
*Researched: 2026-11-11*

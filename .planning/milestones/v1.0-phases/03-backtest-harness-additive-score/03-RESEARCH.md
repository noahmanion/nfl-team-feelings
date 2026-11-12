# Phase 3: Backtest Harness & Additive Score - Research

**Researched:** 2026-11-11
**Domain:** Walk-forward sports-rating evaluation (Python/Polars/NumPy) + additive z-score composite + Observable Plot line chart (Svelte 5)
**Confidence:** HIGH. Every number below was measured on the real cached data with a scratch prototype. Nothing in the project was edited.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Backtest target (BACK-01), written into README BEFORE any tuning
- Primary target per (season, week, franchise) snapshot: mean **adjusted margin** over the team's next N games within the same season (regular season + playoffs), N ∈ {4, 8} (N=8 is the headline; 4 reported too). Adjusted margin for a game = actual point margin − expected margin, where expected margin = (pre-game Elo diff incl. HFA) / 25 (538 points-per-Elo convention). Snapshots with fewer than 2 remaining games are excluded from that N's evaluation.
- Primary metric: Spearman rank correlation and R² of the candidate score vs target, pooled over test seasons, plus per-season values. Secondary: next-game Brier score from a logistic map of score difference (fit on training seasons only).
- Reporting buckets: early (wk 1–6), mid (7–12), late (13+), and week 0 (across-offseason) separately.

#### Walk-forward & data splits
- Walk-forward by season: for test season S, anything fit (z-score stats are per-snapshot so need no fitting; interim weights; logistic maps) uses only seasons < S. First test season 2003 (training 1999–2002).
- **Holdout 2022–2025 is sealed** in this phase: the backtest command defaults to test seasons 2003–2021; 2022+ evaluation requires an explicit `--include-holdout` flag that Phase 6 uses once. 2026 (in progress) is never a test season.

#### Baselines (BACK-02)
- `fgs backtest` prints a table (per-N, per-bucket) for: plain Elo, season-to-date win % (REG), last-16 win %, season-to-date point differential per game, and the Vegas spread (next-game Brier only, as the ceiling; `spread_line` positive = home favored). Plain Elo next-game Brier should land ≈ 0.22–0.23 (Phase 1 research measured 0.2196).
- Output also written to `pipeline/data/derived/backtest.json` (consumed by Phase 6 methodology page; shape: metrics per candidate × N × bucket, plus per-season series).

#### Leakage test (BACK-03)
- Pytest that appends fake future games (after the latest played game) to the schedule, rebuilds, and asserts every existing snapshot's factor values, contributions, and score are unchanged; also a test that truncating the future (dropping games after week W) leaves snapshots ≤ W unchanged.

#### Additive score (MODEL-14) + first factors (MODEL-03, MODEL-04)
- New `features.py` builds per-snapshot raw factor values as-of each (season, week) using only games with asof_week ≤ week: `elo` (rating), `season_record` (REG win% with ties 0.5; week 0 → 0.5), `last16` (win% over the last 16 played games including prior season(s), REG+playoffs, ties 0.5).
- `score.py`: z-score each factor across the teams in that (season, week) snapshot; composite = Σ w_f · z_f; store per-factor `contrib_f = w_f · z_f` columns; composite feeds the existing percentile → 0–100 score → mood bands pipeline (mood.py unchanged in behavior; the percentile reference is now the composite).
- Interim weights live in `pipeline/weights.yaml` (committed): fit by walk-forward Ridge (standardized inputs, alpha via CV within training seasons) on 1999–2021 against the N=8 target, then rounded to 2 decimals by hand-rule (code proposes, file is the source of truth). Phase 6 refits/freezes after all factors exist. Each factor addition records its backtest delta (vs the composite without it) in `pipeline/BACKTEST_LOG.md` (append-only table: date, factor, ΔSpearman N=8, ΔR², fitted sign).
- JSON contract additions (backwards-compatible): `meta.score_kind = "composite"`, `meta.factors` = [{key, label, weight, description}]; season rows get `contribs: {factor_key: number rounded 2dp}`; history.json unchanged shape (score is now composite-based).

#### Mood-over-time chart (SITE-03)
- New route `#/history` (reserved in Phase 2 router) with a simple top nav ("Board" · "Mood over time").
- Observable Plot 0.6.19 line chart from `history.json`: x = time index (season-week), y = score fixed 0–100, all teams as thin muted lines, one highlighted team (selector; default = current #1; hash `#/history/{ABBR}`) in its team color with label, plus mood-band background stripes. Lines break at season boundaries (gap between seasons, using Plot's `z`/NaN gap). Season ticks on x-axis. Phone-width: horizontally fit (no page scroll), fewer ticks.
- Follow UI-SPEC "Design System for later phases" rules from Phase 2 (tokens, no new fonts/weights, no logos, no decimals in UI).

### Claude's Discretion
- Exact Ridge alpha grid, logistic fit method, module layout, chart sizing, how team selector is presented (select vs chips).

### Deferred Ideas (OUT OF SCOPE)
- Team deep-dive page & factor bars (Phase 4); methodology page rendering backtest.json (Phase 6); final weight freeze + holdout (Phase 6).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BACK-01 | Primary target (opponent- and HFA-adjusted average margin over the next 4–8 games) documented in README before tuning | **Conflict found:** the CONTEXT formula subtracts the team's *own* Elo too, which makes the target an Elo residual (plain Elo Spearman +0.018). The requirement's wording (opponent + HFA adjustment only) works: Elo Spearman +0.51. See Pitfall 1 and Open Question 1 (RESOLVED). Target code is in Code Examples §1. |
| BACK-02 | Walk-forward backtest vs plain Elo, season W%, last-16 W%, point differential, Vegas spread | All five baselines prototyped on 2003–2021 (table in Summary). Elo next-game Brier is 0.2194 (538 formula) and 0.2197 (walk-forward logistic), which matches Phase 1's 0.2196. The spread ceiling is 0.2112. |
| BACK-03 | Leakage test: appending fake future games changes no past score | **The current `mood.score_frame` fails this.** Its percentile reference is "all week-0+REG snapshots 1999→now", so fake 2026 games changed 1,743 past scores and 110 bands. Fix: a frozen reference window (Pattern 4). Test design is in Code Examples §5. |
| MODEL-14 | Strictly additive Σ w·z with stored contributions | Per-snapshot z with a zero-variance guard (Pattern 2). Contributions sum to the composite exactly. Percentile → score → band unchanged downstream. |
| MODEL-03 | Factor: current-season record | `win_pct.fill_null(0.5)` from the existing grid. Week 0 and week-1 byes are null, so they become 0.5 and z=0 (Pitfall 3). Walk-forward ΔSpearman(N=8) is +0.0008, fitted sign **+**. |
| MODEL-04 | Factor: rolling last-16 across season boundaries | Cumsum over a per-franchise chronological game index plus `join_asof` on key `season*100+asof_week` (Code Examples §2). Walk-forward ΔSpearman(N=8) is +0.0033, fitted sign **− (negative)**. |
| SITE-03 | Mood-over-time chart, every team 1999→now, one highlighted, fixed y, season breaks | Prototyped headless with Plot 0.6.19 + jsdom on the real history.json. It renders in 31 ms at 960 px and 16 ms at 343 px. The highlight path has exactly 28 sub-paths (one per season), so the breaks work. Code Examples §6. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Work only inside `feel-good-scorew/`. Keep it self-contained with no root-level manifests or shared code across projects.
- Keep it light: favor prototypes over polish, and skip heavy process (CI, extensive tests) unless asked. The locked leakage pytest is explicitly asked for.
- Any stack is fine. The project already uses Python 3.13 + uv + Polars + NumPy and Svelte 5 + Vite + Node 22 (nvm `.nvmrc` = 22).
- Keep the project `README.md` current: what it is, how to run it, where it stands. BACK-01 requires the target to be written there before tuning.
- Concurrency note for this research session only: a code-fixer agent was editing `cli.py`, `mood.py`, `export.py` and `web/src` while this was written. The planner should re-read those files before writing task actions, because line-level details may have moved.

## Summary

The harness is cheap. On the real cache (7,548 games, 19,422 snapshots), the whole prototype ran in **2.1 s** with NumPy + Polars only: both targets, four features, per-snapshot z-scores, 19 walk-forward ridge folds × 4 factor combos with leave-one-season-out alpha CV, and walk-forward logistic Brier for five candidates. `derive()` takes 0.05 s and `score_frame()` 0.08 s. There is no reason to add scikit-learn or scipy. Closed-form ridge, Newton logistic, and Spearman via `polars.rank` + `np.corrcoef` are each about 10 lines. The leakage pytest can rebuild the whole pipeline twice in well under a second.

Two locked details don't hold up against the real data, and the planner must handle both:

1. **The target formula as written in CONTEXT is circular.** "Expected margin = (pre-game Elo diff incl. HFA)/25" subtracts the team's *own* Elo, so the target becomes "how much the team beats its Elo expectation". Plain Elo then scores Spearman **+0.018**, close to zero by construction, and the "beats plain Elo" goal (BACK-06) stops meaning anything. REQUIREMENTS.md BACK-01 says "opponent- and HFA-adjusted", meaning adjust for *who you played and where*, not for your own rating. With expected margin = (1505 − opp_elo_pre + signed_HFA)/25, the expected margin of a league-average team against that opponent at that venue, plain Elo gets Spearman **+0.513** and R² **0.264** (N=8, 2003–2021). That is a sensible, non-degenerate target. Recommendation: implement the requirement's definition and record the reason in the README.
2. **The current percentile reference leaks.** Appending fake future games (filling unplayed 2026 games with 60–0 results) left Elo, wins and rank unchanged but changed **1,743 past integer scores and 110 bands**, because the reference pool grew. The locked leakage test asserts unchanged scores, so it will fail unless the reference becomes a frozen window. Recommendation: week-0 + REG composites of seasons **1999–2021** only.

**Prototype results (target = opponent+HFA-adjusted margin, test seasons 2003–2021, N=8; nothing from 2022+ was evaluated):**

| Candidate | Spearman | R² | wk0 | early | mid | late | Next-game Brier (walk-forward logistic) |
|---|---|---|---|---|---|---|---|
| Plain Elo (raw) | +0.513 | 0.264 | +0.425 | +0.480 | +0.558 | +0.502 | 0.2197 (538 formula: 0.2194) |
| Season W% (REG) | +0.403 | 0.143 | n/a (constant) | +0.330 | +0.500 | +0.447 | 0.2320 |
| Last-16 W% | +0.449 | 0.199 | +0.371 | +0.403 | +0.491 | +0.456 | 0.2260 |
| Point diff / game | +0.462 | 0.185 | n/a (constant) | +0.403 | +0.555 | +0.476 | 0.2282 |
| Vegas spread (ceiling) | — | — | — | — | — | — | **0.2112** |
| WF ridge: z_elo | +0.5114 | 0.2601 | | | | | |
| WF ridge: + season_record | +0.5122 (Δ +0.0008) | 0.2614 (Δ +0.0013) | | | | | |
| WF ridge: + last16 | +0.5155 (Δ +0.0033) | 0.2656 (Δ +0.0042) | | | | | |

The full 1999–2021 ridge fit (the weights.yaml proposal) gives elo **+4.58**, season_record **+0.63**, last16 **−1.25** (points of adjusted margin per SD, alpha=0.001·n). The N=4 numbers are lower across the board, as expected (Elo 0.466).

**Primary recommendation:** Build one `features.py → score.py → mood.py` path used by both `export` and `backtest`. Define the target as opponent+HFA-adjusted margin. Freeze the percentile reference to 1999–2021. Write ridge, logistic and Spearman in NumPy. Draw the chart as a Plot line mark with `z: "team"` plus a NaN row at every season boundary.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Target construction (future adjusted margins) | Pipeline: `backtest.py` | — | Uses future games. It must never be imported by `features.py`/`score.py` (leakage firewall). |
| As-of factor values (elo, season_record, last16) | Pipeline: `features.py` | `snapshots.build_grid` (supplies elo, W-L-T) | One code path for export and backtest (ARCHITECTURE Anti-Pattern 1). |
| Per-snapshot z, Σ w·z, contribs | Pipeline: `score.py` | `weights.yaml` (data) | Pure function of features + weights. No fitting at runtime (BACK-04: refresh never refits). |
| Percentile → 0–100 → band/hysteresis/rank | Pipeline: `mood.py` | — | Unchanged behavior, but the input column becomes `composite` and the reference is frozen. |
| Ridge/logistic fitting, metrics, baselines | Pipeline: `backtest.py` + `fgs backtest` CLI | — | Dev-only. Writes `data/derived/backtest.json`. |
| JSON contract (meta.factors, contribs) | Pipeline: `export.py` | `web/src/lib/types.ts` mirror | JSON is the only interface. |
| Mood-over-time chart, team selector, route | Browser: Svelte + Plot | `history.json` (static) | Static SPA, no backend. |

## Standard Stack

### Core (already installed; no new Python deps needed except optionally PyYAML)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| polars | 2.1.0 (installed) | Feature/target frames, `join_asof`, `rank`, window `over()` | Already the project's frame library [VERIFIED: `uv pip list`] |
| numpy | 2.5.4 (installed) | Closed-form ridge, Newton logistic, corrcoef | Already a dependency [VERIFIED: `uv pip list`] |
| pytest | 9.2.0 (installed) | Leakage + feature tests | Existing suite: 128 tests pass in 1.6 s [VERIFIED: ran it] |
| PyYAML | 6.0.3 | Read `pipeline/weights.yaml` | The YAML filename is locked, and the stdlib has no YAML parser [VERIFIED: `pip index versions pyyaml` → 6.0.3] [ASSUMED: legitimacy; slopcheck unavailable] |
| @observablehq/plot | 0.6.19 (published 2026-11-05, `latest` tag) | History chart | Locked by CONTEXT. Deps: d3 ^7.9.2, isoformat, interval-tree-1d. No postinstall script [VERIFIED: `npm view`] |

### Supporting (dev/prototype only, NOT for the web app)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| jsdom | 31.0.0 | Headless Plot render in a vitest test (optional) | Only if the planner wants an automated "line has 28 sub-paths" check. Plot accepts a `document` option [VERIFIED: used in prototype] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| NumPy closed-form ridge | scikit-learn `RidgeCV` | Pulls in scipy + joblib (~50 MB) for a 3–10 column problem solved in 0.85 s total. Not worth it in a "keep it light" repo. |
| NumPy Newton logistic | statsmodels / sklearn `LogisticRegression` | Same reason. 2–3 parameters, converges in under 10 iterations. |
| PyYAML | Hand-written `key: value` parser, or `weights.json` | The filename `weights.yaml` is locked and REQUIREMENTS BACK-04 names it. A hand-rolled parser breaks on comments or quoting. Use PyYAML `safe_load`. |
| Plot `z` + NaN gaps | One `Plot.line` per team-season (~900 marks) | Slower and more verbose. `z` + NaN gives 1 path per team (verified). |

**Installation:**
```bash
cd pipeline && uv add pyyaml==6.0.3
cd web && nvm use && npm install @observablehq/plot@0.6.19   # pin exact (pre-1.0)
```

## Package Legitimacy Audit

slopcheck is not installed in this environment, so every package below is `[ASSUMED]` per protocol, even though all of them are long-established.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| @observablehq/plot | npm | ~5 yrs (0.6.19 on 2026-11-05) | high | github.com/observablehq/plot | unavailable | Approved [ASSUMED]: already chosen in STACK.md; no postinstall |
| pyyaml | PyPI | ~20 yrs | very high | github.com/yaml/pyyaml | unavailable | Approved [ASSUMED] |
| jsdom (optional, dev) | npm | ~15 yrs | very high | github.com/jsdom/jsdom | unavailable | Optional [ASSUMED]: only if a headless chart test is added |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none. The planner may gate installs behind a light human-verify because slopcheck was unavailable.

## Architecture Patterns

### System Architecture Diagram

```
schedules.parquet (cache)
      │
      ▼
build_games → elo.replay ──► games (elo_pre_*, asof_week) ──► build_team_games
      │                                   │                         │
      │                                   ▼                         ▼
      │                         snapshots.build_grid ◄──────── team_games
      │                         (season,week,franchise, elo, W-L-T)
      │                                   │
      ▼                                   ▼
                              features.py (as-of: elo, season_record, last16[, pd_pg for baseline])
                                          │
                                          ▼
               weights.yaml ──► score.py: z per (season,week) → contrib_f = w_f·z_f → composite = Σ contrib
                                          │
                    ┌─────────────────────┴───────────────────────┐
                    ▼                                             ▼
   mood.score_frame(value="composite",              backtest.py (dev only)
     ref = week0+REG composites 1999–2021)            ├─ target(N) from FUTURE team_games (never imported upstream)
     → score/rank/band/hysteresis                     ├─ walk-forward folds S=2003..2021 (train < S)
                    │                                 │    ridge (LOSO-CV alpha) · logistic Brier · baselines
                    ▼                                 └─ backtest.json + printed table (+ --include-holdout)
   export.py → meta.json (score_kind, factors),
               snapshots/{season}.json (rows + contribs),
               history.json (same shape) ──► web: #/history → Plot chart (spaghetti + highlight + bands)
```

### Recommended Project Structure
```
pipeline/
├── weights.yaml              # committed; source of truth for weights (+ provenance comment)
├── BACKTEST_LOG.md           # append-only factor delta table
├── src/fgs/
│   ├── features.py           # NEW: as-of factor values per snapshot (pure)
│   ├── score.py              # NEW: zscore, load_weights, composite + contrib_* (pure)
│   ├── backtest.py           # NEW: targets, folds, ridge, logistic, metrics, report dict (pure)
│   ├── mood.py               # score_frame takes the value column + frozen reference seasons
│   ├── export.py             # meta.score_kind/factors, rows.contribs
│   └── cli.py                # derive() adds features+score; new `backtest` subcommand
└── tests/
    ├── test_features.py      # synthetic: last16 crosses seasons, ties 0.5, week-0 0.5
    ├── test_score.py         # zero-variance guard, additivity Σcontrib == composite
    ├── test_backtest.py      # target on synthetic games, holdout sealed by default
    └── test_leakage.py       # BACK-03 (real_cache fixture + synthetic variant)
web/src/
├── lib/history.ts            # pure: keys→x positions, tidy rows with NaN breaks, contrast fn (vitest)
├── lib/router.ts             # add {kind:'history', team?: string}
└── components/HistoryChart.svelte, HistoryPage.svelte, SiteNav.svelte
```

### Pattern 1: Target = next-N opponent+HFA-adjusted margin (per team-game, then window)
**What:** For each played team-game, `adj = margin − (1505 − opp_elo_pre + hfa_signed)/25`, where `hfa_signed` = +HFA at home, −HFA away, 0 neutral, using `season_config.hfa_for`. For snapshot (s, w, f): mean of `adj` over the first N games of season s with `asof_week > w`. Drop the row when fewer than 2 remain.
**When:** Backtest only. Lives in `backtest.py`.
**Note:** Use the opponent's `elo_pre` at game time, which is already on `team_games` via a self-join on `(game_id, opponent_id)`. Using the target's future info is legitimate.

### Pattern 2: Per-snapshot z-score with a zero-variance guard
**What:** `z = (x − mean)/std(ddof=0)` over `(season, week)`. If `std ≤ 1e-12`, z = 0.
**Why:** At week 0, `season_record` is 0.5 for every team, so the std is 0 and z would be NaN or inf. In 1999 week 0, `last16` is also 0.5 for all teams (no prior games). The guard turns these into "no information", contributing 0, which is honest and keeps the composite additive.

### Pattern 3: Walk-forward folds
For S in 2003..2021: train = rows with season < S, test = season S. Inside train, pick alpha by leave-one-season-out CV (grid `[0, 1e-3, 1e-2, 1e-1, 1]` × n). Fit ridge with an unpenalized intercept on the z-columns. Predict test. Pool predictions over all test seasons for Spearman/R², and keep per-season values. Logistic maps for Brier use the same folds. Plain Elo needs no fit for Spearman, and its Brier uses the logistic map on (elo_h − elo_a, home_indicator) fit on seasons < S.

### Pattern 4: Frozen percentile reference (leakage fix)
`mood.score_frame(df, value="composite", ref_seasons=(1999, 2021))`: reference = week ≤ reg_weeks rows of seasons 1999–2021. Then appending or truncating anything in 2022+ cannot move any score. Rank by `composite` (not Elo), tie-break by franchise_id. Put `REF_SEASONS = (1999, 2021)` in `season_config.py` next to the holdout constants.

### Pattern 5: Chart = one tidy array, Plot `z` + NaN breaks
Convert `history.json` (`keys` + per-team arrays, nulls for HOU pre-2002) into rows `{team, x, y}`. x is the key index plus one empty slot per season boundary, so seasons are visually separated. Insert `{y: NaN}` at each boundary per team. Spaghetti = `Plot.line(rows, {z: "team", ...})`. Highlight = a second `Plot.line` on that team's rows. Bands = `Plot.rect(meta.bands, {x1: 0, x2: xMax, y1, y2})`. Season boundaries = `Plot.ruleX`.

### Anti-Patterns to Avoid
- **Target code imported by features/score:** keep `backtest.py` downstream-only, and grep in a test that `features.py`/`score.py` don't import it.
- **Fitting anything in `refresh`/`export`:** weights come only from `weights.yaml` (BACK-04).
- **Evaluating 2022+ while choosing weights:** the default `test_seasons = range(2003, 2022)`. The ridge-proposal fit uses `season <= 2021`, and target rows for 2022+ are filtered out *before* any fit or metric unless `--include-holdout` is passed.
- **Ranking by Elo after the switch:** rank and score would disagree. Rank by composite.
- **Pooling raw (non-z) values for composite candidates:** compare like with like. Baselines use raw values (they're single-factor and rank-invariant within snapshot except across snapshots). Raw vs z Elo differ negligibly (0.5132 vs 0.5116).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML parsing | Line-split parser | `yaml.safe_load` | Comments/quoting edge cases; filename is locked |
| Average ranks with ties (Spearman) | Custom ranker | `pl.Series(x).rank("average")` + `np.corrcoef` | Ties are common (W% at 0.5, week-1 0/1) |
| As-of lookups | Python loops over snapshots | `pl.join_asof(..., by=..., strategy="backward")` | Already the established pattern. Verified fast |
| Line gaps / multi-series | Manual SVG paths | Plot `line` + `z` + NaN | Verified 28 sub-paths for 28 seasons |
| Color contrast | Eyeballing | WCAG relative-luminance formula (≈10 lines, pure, vitest-able) | UI-SPEC requires a runtime 3:1 check with secondary/text fallback |

(Ridge, logistic and Spearman *are* hand-written, but each is the textbook closed form in under 15 lines of NumPy. That's acceptable because pulling in sklearn/scipy for three columns is heavier than the code.)

## Common Pitfalls

### Pitfall 1: Circular target (own-Elo residual)
**What goes wrong:** Using expected margin = (own_elo − opp_elo + HFA)/25 makes the target "margin beyond Elo's expectation". Measured result: Elo Spearman +0.018, season W% +0.030, last16 −0.012, pd/game +0.080 (N=8). Ridge then puts negative weight on elo and noise on everything else.
**How to avoid:** Expected margin of a *league-average* team: (1505 − opp_elo_pre + hfa_signed)/25. This matches REQUIREMENTS BACK-01's wording. Write the definition and the reason into the README before any tuning.
**Warning signs:** Plain-Elo Spearman under 0.1 on the headline target.

### Pitfall 2: Global percentile reference = leakage
**What goes wrong:** A reference built from "all snapshots 1999→now" grows with every new week, which shifts past integer scores (measured: 1,743 rows, 110 band changes after fake games).
**How to avoid:** Frozen reference seasons 1999–2021 (Pattern 4). The truncation test must truncate within 2026 (or any season > 2021).
**Warning signs:** The leakage test passes on elo/contribs but fails on `score`.

### Pitfall 3: Zero-variance z at week 0 and early weeks
**What goes wrong:** At week 0, season_record (and pd/game) is constant → std 0 → NaN that propagates into the composite, the percentile, and then JSON `NaN`, which is invalid JSON. Also: 5 snapshots at week 1 have null `win_pct` (bye in week 1), and 893 week-0 rows are null.
**How to avoid:** `fill_null(0.5)` and a std guard → z=0. Also report the wk0 bucket's Spearman as `null` (constant predictor) instead of NaN, and make `json.dumps(..., allow_nan=False)` in the backtest writer to catch any slip.

### Pitfall 4: Single-outlier z explosions
**What:** 1999 week 0: 30 teams at 1505 plus CLE at 1300 gives z_elo(CLE) ≈ −5.4 and every other team ≈ +0.18. 2002 HOU is similar. This is harmless for the score (CLE gets 0), but contribs show extreme values.
**How to avoid:** Accept it for now (CLE really was an expansion team). Don't clip in this phase. Clipping would silently change the additivity story. Note it for the Phase 4 factor bars.

### Pitfall 5: last16 sign comes out negative
**What:** Given Elo, a hot last-16 W% predicts *worse* future adjusted margin (ridge weight −1.25, stable across late folds). That's plausible regression of record-luck that Elo's MOV already discounts.
**How to avoid:** Not a bug. Per PITFALLS #3 ("let the backtest set the sign"), keep the fitted sign, log it in BACKTEST_LOG.md, and flag it for Phase 4 copy. The planner should **not** add a positivity constraint.

### Pitfall 6: Next-game snapshot alignment
**What:** For Brier, the pre-game snapshot must be `(season, asof_week − 1)`, not `week − 1`, for postponed games. The current cache has 0 games with asof_week ≠ week, but the code must use asof_week. Verified: 0 games lack a pre-game snapshot.

### Pitfall 7: Plot default styling violates UI-SPEC
**What:** Plot's default SVG uses `font-size: 10` and `currentColor`. UI-SPEC requires Label 14 in `--text-muted` with `--border` axes.
**How to avoid:** `style: {fontSize: "14px", color: "var(--text-muted)", background: "transparent"}`. Rules/lines with `stroke: "var(--border)"`. Plot passes `var(...)` strings through as literal colors (verified in the rendered SVG: `fill="var(--mood-0)"`).

### Pitfall 8: Node version
Default shell node is v20.19.0. The project requires >=22.12 (`web/.nvmrc` = 22, and v22.23.3 is installed under nvm). Every web task command must start with `nvm use`.

## Code Examples

All examples were run in the scratch prototype (`.../scratchpad/p3/proto.py`, `leak.py`, `plotproto/chart.mjs`) against the real cache.

### §1 Target (backtest.py)
```python
def adjusted_margins(team_games: pl.DataFrame) -> pl.DataFrame:
    opp = team_games.select("game_id", pl.col("franchise_id").alias("opponent_id"),
                            pl.col("elo_pre").alias("opp_elo_pre"))
    hfa = pl.col("season").map_elements(hfa_for, return_dtype=pl.Float64)
    return (team_games.filter(pl.col("played")).join(opp, on=["game_id", "opponent_id"])
        .with_columns((pl.col("points_for") - pl.col("points_against")).cast(pl.Float64).alias("margin"),
                      pl.when(pl.col("neutral")).then(0.0).when(pl.col("is_home")).then(hfa).otherwise(-hfa).alias("hfa_s"))
        .with_columns((pl.col("margin") - (MEAN_ELO - pl.col("opp_elo_pre") + pl.col("hfa_s")) / 25).alias("adj"))
        .sort("franchise_id", "season", "asof_week"))
# window: k = #games with asof_week <= w in (f, s); m = min(N, n_tot - k); y = (cs[k+m]-cs[k])/m if m >= 2 else None
```

### §2 last16 across seasons (features.py)
```python
g = (tg.filter(pl.col("played"))
       .with_columns((pl.col("season") * 100 + pl.col("asof_week")).alias("key"))
       .sort("franchise_id", "key")
       .with_columns(pl.int_range(1, pl.len() + 1).over("franchise_id").alias("n")))  # games so far
s = snap.with_columns((pl.col("season") * 100 + pl.col("week")).alias("key")).sort("key")
s = s.join_asof(g.select("franchise_id", "key", "n").sort("key"), on="key", by="franchise_id")
# last16 = (cum_outcome[n] - cum_outcome[max(0, n-16)]) / min(n, 16); n null/0 -> 0.5
```
(At most one game per team per asof_week, verified, so `key` is unique per team. A pure-Polars version uses `outcome.rolling_sum(16, min_samples=1)` on the per-team game series, then the as-of join.)

### §3 z-score + composite (score.py)
```python
def zscore(df, cols):
    by = ["season", "week"]
    return df.with_columns(
        pl.when(pl.col(c).std(ddof=0).over(by) > 1e-12)
          .then((pl.col(c) - pl.col(c).mean().over(by)) / pl.col(c).std(ddof=0).over(by))
          .otherwise(0.0).alias(f"z_{c}") for c in cols)

def composite(df, weights: dict[str, float]):
    df = zscore(df, list(weights))
    df = df.with_columns((weights[f] * pl.col(f"z_{f}")).alias(f"contrib_{f}") for f in weights)
    return df.with_columns(pl.sum_horizontal([f"contrib_{f}" for f in weights]).alias("composite"))
```

### §4 Ridge + logistic (NumPy only)
```python
def ridge_fit(X, y, alpha):            # X already standardized; intercept unpenalized
    xm, ym = X.mean(0), y.mean(); Xc, yc = X - xm, y - ym
    w = np.linalg.solve(Xc.T @ Xc + alpha * len(y) * np.eye(X.shape[1]), Xc.T @ yc)
    return w, ym - xm @ w
def logit_fit(X, y, iters=25):         # Newton/IRLS; X gets a ones column
    X = np.column_stack([X, np.ones(len(y))]); b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X @ b)); W = p * (1 - p)
        b += np.linalg.solve(X.T @ (X * W[:, None]) + 1e-9 * np.eye(len(b)), X.T @ (y - p))
    return b
spearman = lambda x, y: float(np.corrcoef(pl.Series(x).rank("average").to_numpy(),
                                          pl.Series(y).rank("average").to_numpy())[0, 1])
```
Brier inputs: `x = [score_home − score_away, home_indicator(0 if neutral)]`, ties excluded (`result != 0`). Spread: `x = [spread_line]`.

### §5 Leakage test (tests/test_leakage.py)
```python
def _pipeline(raw):   # the exact production path
    d = derive(raw)                                    # games, team_games, snapshots(+features+composite)
    return score_frame(d["snapshots"], value="composite")
def test_fake_future_games_change_nothing(real_cache):
    raw = pl.read_parquet(real_cache)
    fake = raw.with_columns(  # every unplayed game becomes a 60-0 home win
        pl.when(pl.col("result").is_null()).then(60).otherwise(pl.col("result")).alias("result"),
        pl.when(pl.col("home_score").is_null()).then(60).otherwise(pl.col("home_score")).alias("home_score"),
        pl.when(pl.col("away_score").is_null()).then(0).otherwise(pl.col("away_score")).alias("away_score"))
    a, b = _pipeline(raw), _pipeline(fake)
    j = a.join(b, on=["season", "week", "franchise_id"], suffix="_f")   # inner: only pre-existing snapshots
    assert j.height == a.height
    for c in ["elo", "season_record", "last16", "composite", *contrib_cols, "score", "band", "rank"]:
        assert (j[c] == j[f"{c}_f"]).all(), c          # floats: exact equality is expected (same ops, same order)
```
Truncation variant: drop 2026 games with `week > W` (set result/scores null, or remove rows), then assert snapshots `(2026, ≤W)` and all earlier snapshots are unchanged. There's also a synthetic-fixture version (conftest `make_games`) so the test runs without the cache. Prototype measured: fake 2026 completion → elo/wins/rank 0 changes, score 1,743 changes under the current global ref. That proves the test detects the leak, and the frozen ref fixes it.

### §6 Chart (verified with Plot 0.6.19 + jsdom)
```ts
// lib/history.ts (pure, vitest-able)
const seasonOf = (k: string) => Number(k.split('-')[0])
export function toRows(h: { keys: string[]; teams: Record<string, (number | null)[]> }) {
  const xs: number[] = []; let x = 0
  h.keys.forEach((k, i) => { if (i && seasonOf(k) !== seasonOf(h.keys[i - 1])) x += 1; xs.push(x++) })
  const rows: { team: string; x: number; y: number }[] = []
  for (const [team, s] of Object.entries(h.teams))
    s.forEach((v, i) => {
      if (i && seasonOf(h.keys[i]) !== seasonOf(h.keys[i - 1])) rows.push({ team, x: xs[i] - 1, y: NaN })
      rows.push({ team, x: xs[i], y: v ?? NaN })
    })
  return { rows, xs }
}
// HistoryChart.svelte: build in $effect, container.replaceChildren(plot); width from bind:clientWidth
Plot.plot({
  width, height: width < 500 ? 280 : 400,
  style: { fontSize: '14px', color: 'var(--text-muted)', background: 'transparent' },
  x: { domain: [0, xMax], ticks: seasonStartXs.filter(everyNth), tickFormat: xToSeason, label: null },
  y: { domain: [0, 100], ticks: [0, 20, 40, 60, 80, 100], label: null },
  marks: [
    Plot.rect(bands, { x1: 0, x2: xMax, y1: 'min', y2: (d) => (d.max === 100 ? 100 : d.max + 1),
                       fill: (d, i) => `var(--mood-${i})`, fillOpacity: 0.1 }),
    Plot.ruleX(seasonStarts.slice(1), { x: (d) => d.x - 0.5, stroke: 'var(--border)', strokeDasharray: '2,3' }),
    Plot.line(rows, { x: 'x', y: 'y', z: 'team', stroke: 'var(--text-muted)', strokeOpacity: 0.25, strokeWidth: 1 }),
    Plot.line(hiRows, { x: 'x', y: 'y', stroke: teamColor, strokeWidth: 2.5 }),
    Plot.text(hiRows.filter((d) => !Number.isNaN(d.y)).slice(-1), { x: 'x', y: 'y', text: () => abbr, dx: 6, textAnchor: 'start' }),
  ],
})
```
Measured: 20,352 rows, render 31 ms at 960 px and 16 ms at 343 px, SVG ≈ 253 KB of DOM. Highlight path = 28 `M` sub-paths for 28 seasons. Band rects span the frame (x=40, width 900). Tick spacing: every 2nd season ≥ 500 px, every 5th on phones. Dark mode: use 14% opacity there, either via `fillOpacity` read from a CSS var at render time or by re-rendering on a `prefers-color-scheme` change. Hover-independent summary line (UI-SPEC): "{Team} now {score} · {label}; low {min} ({season} {week label})".

## Runtime State Inventory
Not a rename or migration phase. One stateful item needs care: **`web/public/data/*` is committed**. After the composite ships, `fgs export` must be rerun and the regenerated JSON committed. Otherwise the site keeps showing Elo-only scores with `score_kind:"elo"`. `pipeline/data/derived/*.parquet` is gitignored and rebuilt by `build`/`refresh`. Nothing else holds state (verified: no OS registrations, services or secrets).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Score = percentile of Elo, reference 1999→now | Score = percentile of Σ w·z composite, reference frozen 1999–2021 | This phase | Scores and bands shift once at the switch; tests pinned to `score_kind == "elo"` (test_export.py:74) and to the Elo reference (test_mood.py:118) need updating |
| Rank by Elo | Rank by composite | This phase | BoardHeading count line drops " · Elo-based score" automatically when `score_kind != 'elo'` (BoardHeading.svelte:25) |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The CONTEXT "expected margin = Elo diff/25" was meant as an opponent+HFA adjustment (REQUIREMENTS wording), not an own-Elo residual | Summary, Pitfall 1 | If the user really wanted the residual target, plain Elo is ~0 by construction and BACK-06 becomes trivial or meaningless. Low risk: the requirement text is explicit |
| A2 | A frozen percentile reference (1999–2021) is an acceptable reading of "mood.py unchanged in behavior" | Pattern 4 | Scores shift slightly vs Phase 2. Required for the locked leakage test to pass |
| A3 | PyYAML/Plot/jsdom legitimacy (slopcheck unavailable) | Package audit | Negligible: these are long-established packages |
| A4 | CSS `var()` in SVG fill/stroke attributes renders in target browsers | Pitfall 7 | Verified only that Plot emits it. Observable Framework relies on this pattern. If it fails, resolve tokens with `getComputedStyle` before rendering |

## Open Questions (RESOLVED)

1. **Which target formula? (RESOLVED)** Use expected margin = (MEAN_ELO − opp_elo_pre + hfa_signed)/25 (opponent + HFA only), per REQUIREMENTS BACK-01's wording. Evidence: the CONTEXT formula gives Elo Spearman +0.018, while the requirement-faithful formula gives +0.513. Record both numbers and the rationale in the README's target section, and optionally keep the residual target as a secondary diagnostic ("does the score know something Elo doesn't?"). That's useful later but not the headline.
2. **How to make the leakage test pass on `score`? (RESOLVED)** Freeze the percentile reference to week-0+REG composites of seasons 1999–2021 (`REF_SEASONS` constant). The truncation test operates on 2026.
3. **Interim weights for weights.yaml? (RESOLVED)** The proposal from a ridge fit on 1999–2021 (N=8, alpha by LOSO CV = 0.001·n) is `elo: 4.58, season_record: 0.63, last16: -1.25`. `fgs backtest --propose-weights` should print this. A human copies it into weights.yaml with a provenance comment (fit date, seasons, target, alpha). Because ridge alphas chosen are tiny, ridge ≈ OLS here. That's fine at n≈9.8k rows × 3 columns.
4. **Keep last16 despite its negative sign? (RESOLVED)** Yes. It improves walk-forward Spearman (+0.0033) and R² (+0.0042). Log the sign as "−" in BACKTEST_LOG.md. Phase 4 copy must explain it as "recent record ran ahead of underlying strength".
5. **What do baselines show at week 0? (RESOLVED)** season W% and pd/game are constant at week 0, so their Spearman is undefined. Emit `null` and print "—". Elo and last16 are defined at week 0 (0.425, 0.371).
6. **R² definition? (RESOLVED)** Report R² as squared Pearson correlation (the linear-map R², valid for raw baselines and composites alike). Optionally add out-of-sample 1 − SSE/SST for ridge predictions in backtest.json, labeled `r2_oos`.
7. **Nav label conflict (RESOLVED):** UI-SPEC says "Board · History · Records · How it works". CONTEXT (locked, newer) says "Board · Mood over time". Ship only the two existing views, labeled per CONTEXT. Keep the UI-SPEC nav styling (2px accent underline, `aria-current`).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv + Python | pipeline | ✓ | Python 3.13 venv | — |
| polars / numpy / pytest | pipeline | ✓ | 2.1.0 / 2.5.4 / 9.2.0 | — |
| PyYAML | weights.yaml | ✗ (not installed) | 6.0.3 on PyPI | `uv add pyyaml` |
| scikit-learn / scipy | — | ✗ | — | Not needed (NumPy closed forms) |
| Node | web | ✓ via nvm | 22.23.3 (default shell is 20.19.0) | `nvm use` |
| @observablehq/plot | SITE-03 | ✗ in web/ | 0.6.19 on npm | `npm install @observablehq/plot@0.6.19` |
| Cached data | backtest, leakage test | ✓ | schedules 1999–2026 wk9 | Tests skip via `real_cache` fixture |

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.2.0 (pipeline), vitest 5.1 + svelte-check (web) |
| Config file | `pipeline/pyproject.toml [tool.pytest.ini_options]`, `web/package.json` scripts |
| Quick run command | `cd pipeline && uv run pytest -q tests/test_features.py tests/test_score.py tests/test_leakage.py` |
| Full suite command | `cd pipeline && uv run pytest -q && cd ../web && nvm use && npm test && npm run check && npm run build` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BACK-01 | Target = opponent+HFA-adjusted next-N mean; <2 remaining excluded; README documents it | unit (synthetic) + grep | `uv run pytest tests/test_backtest.py -k target -x` ; `grep -n "adjusted margin" README.md` | ❌ Wave 0 |
| BACK-02 | `fgs backtest` prints all 5 baselines; Elo Brier in [0.215, 0.23]; spread Brier < Elo Brier; backtest.json has candidate×N×bucket + per-season; default seasons 2003–2021 | integration (real_cache) | `uv run pytest tests/test_backtest.py -k "baselines or holdout" -x` | ❌ Wave 0 |
| BACK-02 | Holdout sealed: no 2022+ rows in metrics without `--include-holdout` | unit | `uv run pytest tests/test_backtest.py -k holdout -x` | ❌ Wave 0 |
| BACK-03 | Fake future games / truncation leave elo, factors, contribs, composite, score, band, rank unchanged | integration (real + synthetic) | `uv run pytest tests/test_leakage.py -x` | ❌ Wave 0 |
| MODEL-14 | Σ contrib_f == composite (≤1e-9); z=0 on zero variance; no NaN anywhere | unit | `uv run pytest tests/test_score.py -x` | ❌ Wave 0 |
| MODEL-03 | season_record: REG only, ties 0.5, week-0/bye → 0.5 | unit (synthetic conftest) | `uv run pytest tests/test_features.py -k season_record -x` | ❌ Wave 0 |
| MODEL-04 | last16 spans season boundary, includes playoffs, <16 games uses available, none → 0.5 | unit (synthetic) | `uv run pytest tests/test_features.py -k last16 -x` | ❌ Wave 0 |
| MODEL-14 | Export: meta.score_kind=="composite", meta.factors weights match weights.yaml, rows.contribs keys == factor keys | contract (real) | `uv run pytest tests/test_export.py -x` (update line 74 assertion) | ✅ (needs update) |
| SITE-03 | `toRows` inserts NaN at each season boundary; x-gap; null→NaN; router parses `#/history` and `#/history/BUF`; contrast fallback | unit (vitest) | `cd web && npm test` | ❌ Wave 0 (`lib/history.test.ts`, router.test.ts additions) |
| SITE-03 | Chart renders at 375 px with no horizontal scroll; fixed 0–100 y | manual (visual) | `npm run dev` → `#/history`, `#/history/DET` | manual-only |

### Sampling Rate
- **Per task commit:** the quick run command (under 2 s).
- **Per wave merge:** full pipeline suite plus `npm test && npm run check`.
- **Phase gate:** full suite green, `uv run fgs backtest` prints the table with Elo Brier ≈ 0.22, `uv run fgs export` regenerates committed JSON, then `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `pipeline/tests/test_features.py`, `test_score.py`, `test_backtest.py`, `test_leakage.py`
- [ ] Update `tests/test_export.py:74` (score_kind) and `tests/test_mood.py:118` (reference now frozen/composite)
- [ ] `web/src/lib/history.test.ts`. Extend `router.test.ts` for `#/history[/ABBR]` (currently in RESERVED)
- [ ] `uv add pyyaml`. `npm install @observablehq/plot@0.6.19`

## Security Domain
`security_enforcement: false` in config.json, so this section is omitted. (Static site, no auth, no user input beyond the hash route. The router must still validate `{ABBR}` against `meta.teams` and fall back to `#/history`.)

## Sources

### Primary (HIGH confidence)
- Real-data prototype on `pipeline/data/derived/*.parquet` + `data/cache/schedules.parquet` (scripts in the scratchpad `p3/`): every metric, runtime, leakage count and chart measurement above.
- Project code: `elo.py`, `snapshots.py`, `games.py`, `mood.py`, `export.py`, `cli.py`, `season_config.py`, `web/src/lib/*`, `02-UI-SPEC.md` §Design System for Later Phases.
- Observable Plot v0.6.19 docs (GitHub raw `docs/marks/line.md`, `rect.md`, `rule.md`): `z` grouping; "If some channel values are undefined (or null or NaN), gaps will appear between adjacent points".
- `npm view @observablehq/plot` (0.6.19, latest, 2026-11-05; deps d3 ^7.9.2), `pip index versions pyyaml` (6.0.3).

### Secondary (MEDIUM)
- `.planning/research/ARCHITECTURE.md` (Patterns 3/4/6, Anti-Patterns 1/2/4) and `PITFALLS.md` (#1 leakage test, #3 sign by backtest, #10 target choice).

### Tertiary (LOW)
- CSS `var()` inside SVG presentation attributes in all target browsers: inferred from Observable Framework usage, not directly verified (A4).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (installed and verified; only PyYAML/Plot are new)
- Architecture: HIGH (prototyped end to end on real data)
- Pitfalls: HIGH (target circularity and percentile leakage reproduced numerically)

**Research date:** 2026-11-11
**Valid until:** 2026-12-11 (stable domain; recheck the Plot version before install)

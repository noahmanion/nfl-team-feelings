# Phase 4: Game-Result Factors & Team Deep-Dive - Research

**Researched:** 2026-11-11
**Domain:** As-of rolling game factors (Polars), walk-forward ridge add-one-at-a-time, score-point attribution and integer apportionment, deterministic text generation, Svelte 5 team page
**Confidence:** HIGH (every numeric claim below was produced by a prototype run on the real cached data in this session)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Factor definitions (as-of: only games with asof_week ≤ week; REG + playoffs; spans season boundaries where noted)
- `mov` (MODEL-06, strength of win): mean point margin over the team's last 8 played games (crossing season boundaries), each game's margin capped at ±24 (blowout cap). No games → 0.
- `sow` (MODEL-07, opponent quality / strength of win by opponent): mean over last 8 played games of (result − p_avg), where result ∈ {1, 0.5, 0} and p_avg = Elo win prob of a league-average (1505) team vs that opponent's PRE-GAME Elo at the same venue/HFA. Beating good teams scores high; losing to bad teams scores low. Kept separate from `mov`.
- `streak` (MODEL-09): signed current streak (+k for k straight wins, −k for losses), ties end streaks (→0), carries across seasons, capped at ±8.
- `luck` (MODEL-10): net one-score record over last 16 games: (# wins with |margin| ≤ 8) − (# losses with |margin| ≤ 8). Expect a NEGATIVE fitted sign (lucky teams regress) — that is the honest outcome; do not constrain.
- Add order: mov → sow → streak → luck. After each: refit interim walk-forward Ridge (same procedure as Phase 3), run `fgs backtest`, append row to `pipeline/BACKTEST_LOG.md` (factor, ΔSpearman N=8, ΔR², fitted sign, kept/dropped note), update `pipeline/weights.yaml`. A factor whose ΔSpearman is negative is still kept in v1 (single score, data decides weight; Phase 6 finalizes), but note it.
- All factors exported in `meta.factors` with human labels + one-sentence descriptions.

#### Score-point attribution (bars sum to the displayed score)
- For each snapshot row, pipeline computes `points` per factor: points_f = contrib_f × (score(c) − score(0)) / c where c = composite and score(·) is the frozen-reference percentile map; when |c| < 1e-6 use the derivative of score at 0. Baseline = score(0) (≈50, "an average team"). Round to integers with largest-remainder so Σ points = displayed score − baseline exactly (baseline also integer). Exported per row as `points: {factor: int}` + `meta.baseline`.

#### One-liner (INSIGHT-05)
- Pipeline generates `blurb` per row from the top 2 factors by |points| using a phrasebook keyed by (factor, sign, magnitude tier) — e.g. mov+ "has been blowing teams out", luck+ "has won a lot of coin-flip games (that rarely lasts)", streak− "is stuck in a 4-game skid", sow+ "has beaten good teams". Template: "{Team} {phrase1}{, and/but} {phrase2}." ("but" when signs differ). Deterministic; no LLM. Week 0 blurb: explains preseason carryover.

#### Team page (SITE-02)
- Route `#/team/{ABBR}` (latest) and `#/team/{ABBR}/{season}/{week}`; board rows and history chart team label link to it; nav still shows Board · Mood over time.
- Content: header (color chip, full name, record, rank, big score, mood label + emoji, delta), blurb, factor breakdown (diverging horizontal bars: baseline marker labeled "Average team {baseline}", one bar per factor in points, sorted by |points|, positive right/negative left, final "= {score}" total line), recent games list (last 6 played as-of that week: week label, opponent chip/abbr, home/away, W/L/T, score, margin), small sparkline of this season's score (Plot, optional) and link to `#/history/{ABBR}`.
- Data: extend `teams/{ABBR}.json` with `recent_games` per (season, week) is too big — instead export `games/{season}.json` (compact game list) OR include last-6 games inline in each season-file row? Decision: per-season `games/{season}.json` (columnar: week, home, away, home_score, away_score, game_type, gameday) and the frontend derives recent games; season rows carry `points` + `blurb`.
- Follow 02-UI-SPEC "Design System for Later Phases" (factor breakdown + team page rules), no decimals, no logos.

### Claude's Discretion
- Phrasebook wording, bar chart implementation (plain SVG/CSS vs Plot), magnitude tiers, component structure.

### Deferred Ideas (OUT OF SCOPE)
- Perception-gap callouts (Phase 8), "good loss" modeling (v2), efficiency/QB factors (Phase 5).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MODEL-06 | Factor: strength of win, margin of victory as its own input | `mov` prototype (Pattern 1). Walk-forward ΔSpearman N=8 **+0.0026**, ΔR² +0.0015, fitted sign **+** in every fold (19/19) |
| MODEL-07 | Factor: opponent quality, opponent's pre-game rating as its own input | `sow` prototype (Pattern 1). ΔSpearman **+0.0047**, ΔR² +0.0048 (the largest gain). Fitted sign is **−** once Elo and mov are in the model (Pitfall 1) |
| MODEL-09 | Factor: current win/loss streak | `streak` prototype. ΔSpearman **+0.0000**, ΔR² −0.0001, sign − (−0.14), ~0 as STATE.md predicted |
| MODEL-10 | Factor: close-game luck (one-score results) | `luck` prototype. ΔSpearman **−0.0008** after sow (but +0.0029 when added alone to the base). Sign − in 19/19 folds |
| SITE-02 | Team deep-dive with score, mood, one-liner, diverging factor bars summing to the score, recent games | Attribution (Pattern 3) verified on all 19,422 rows: Σ points == score − baseline exactly. `games/{season}.json` is ~11 KB raw / ~2 KB gzip. Route/component plan in Pattern 5 |
| INSIGHT-05 | Auto-generated plain-English one-liner per team | Phrasebook draft (Pattern 4), checked against real 2026 week 9 top and bottom teams, lucky DEN, 2009 LAC and 2003 CAR |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Work only inside `feel-good-scorew/`. The project is self-contained, with no shared code or dependencies and no root-level manifests.
- Keep it light: quick prototypes over polish, and no heavy process (CI, extensive tests) unless asked. The existing pytest + vitest gates are the project norm, so extend them; don't add new frameworks.
- The README must say what the idea is, how to run it, and where it stands. Update the Status line at phase end.
- Stack (from the project CLAUDE.md stack section): Python 3.13 + uv + Polars + NumPy in `pipeline/`; Vite + Svelte 5 + Observable Plot 0.6.19 in `web/`. JSON in `web/public/data/` is the only contract. No logos, no decimals in the UI, TypeScript stays ~6.0.
- Workflow: edits go through GSD execute-phase. This research made no project edits (see the side-effect note in Environment Availability).

## Summary

All four factors were built on the real cache exactly as CONTEXT defines them and run through the Phase 3 walk-forward ridge harness: test seasons 2003–2021, training < S, holdout sealed, alpha by leave-one-season-out CV. The base (elo + season_record + last16) reproduces Phase 3 exactly (Spearman 0.5155, R² 0.2656), so the harness reuse is sound. Adding mov → sow → streak → luck gives N=8 Spearman 0.5181 → 0.5228 → 0.5228 → 0.5219. The game-result factors together add +0.0064 Spearman and +0.0057 R², and next-game Brier improves from 0.2195 to 0.2190. Signs from the 1999–2021 proposal fit are mov +, **sow −**, streak −, luck −. The sow sign is the surprise. It is positive alone (univariate Spearman 0.428) but turns negative as soon as Elo is in the model (elo+sow: sow = −0.28). Elo already prices in wins against strong opponents, so the leftover sow signal means "results running ahead of margins", which regresses. That affects phrasing and bars, not the decision to keep the factor.

The literal attribution formula has a numerical trap. If score(·) is the displayed integer percentile map, then (score(c) − score(0))/c reaches 47× when c is tiny. In 174 rows with |c| < 0.15, every bar becomes 0 even when large factors offset each other. Using the same frozen percentile map but unrounded and smoothed (piecewise-linear through 101 quantile knots) keeps the slope in [2.4, 10.3]. Reconciling to the integer total by spreading the residual by magnitude and then applying largest-remainder gives an exact sum in all 19,422 rows, with no sign flips and at most 1.25 points of rounding movement. Baseline = score(0) = **49**, not 50, because the reference median composite is +0.135.

On the web side, Elo is the largest bar in 84% of rows. A strict "top 2 by |points|" blurb therefore almost always starts with the Elo phrase. That works if the Elo phrase is tiered ("one of the best teams in football"), and the second clause carries the insight. No new packages are needed. The team page is a new route, three small components, one new JSON family (`games/{season}.json`, about 11 KB each) and two new row fields (`points`, `blurb`).

**Primary recommendation:** Implement the four factors in `features.py` exactly as prototyped (code below) and replay the add-one-at-a-time loop, expecting the numbers in the Prototype Results table. Compute points with the **smoothed** frozen-reference map plus residual-spread largest-remainder in a new pure `fgs/explain.py`. Key blurb phrases on the factor's raw direction (sign of z), with a "(that tends to fade / even out)" suffix whenever the bar points against that direction, so the text stays honest even if Phase 6 flips a sign.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| mov / sow / streak / luck values | Pipeline (`features.py`) | — | As-of, leakage-tested, and consumed by both score and backtest |
| Add-one-at-a-time evaluation, weight proposal | Pipeline dev harness (`backtest.py`) | `weights.yaml`, `BACKTEST_LOG.md` | Firewall: only backtest sees future targets |
| Points attribution and baseline | Pipeline (`explain.py`, new) | `mood.py` (frozen reference) | Needs the frozen 1999–2021 reference composite. The browser must never re-derive it |
| Blurb text | Pipeline (`explain.py`) | `export.py` (team nick) | Deterministic, testable in pytest. The frontend just renders a string |
| Compact game list | Pipeline (`export.py` → `games/{season}.json`) | — | JSON contract is the only interface |
| Recent-games derivation, bar layout, routing | Browser (`lib/team.ts`, `router.ts`) | — | Pure TS helpers, vitest-covered |
| Team page rendering | Browser (Svelte components) | Observable Plot (sparkline only) | Static site, hash routes |

## Standard Stack

No new dependencies. Everything uses what Phases 1–3 installed.

### Core
| Library | Version (installed) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| polars | 2.1.0 (pyproject `>=2.1.0`) | Rolling windows via cumsum − shifted cumsum, `join_asof` backward | Same pattern as `features._last16` [VERIFIED: codebase] |
| numpy | 2.5.4 | Streak loop, attribution, largest remainder, `np.quantile`/`np.interp` | Already used for the ridge and percentiles [VERIFIED: codebase] |
| pyyaml | 6.0.3 | weights.yaml | Phase 3 [VERIFIED: codebase] |
| svelte | 5.57.x | Team page components | Phase 2 [VERIFIED: web/package.json] |
| @observablehq/plot | 0.6.19 (exact pin) | Optional season sparkline | Phase 3, UI-SPEC rule 3 [VERIFIED: web/package.json] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| CSS/HTML factor bars | Plot `barX` | Plot is heavier, harder to make accessible per bar, and gives you a chart where you want a list. CSS bars are list items with text, so screen readers and the no-hover rule come for free. **Use CSS.** |
| Plot sparkline | Inline SVG polyline | Either works. Plot follows UI-SPEC rule 3 and is already bundled. Inline SVG is ~20 lines with no Plot setup. Discretion: pick one. |
| Smoothed percentile map (101 knots) | Every reference point as a knot | 13,226 knots still give a noisy local slope near 0. 101 knots are stable and deterministic. |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed in this phase. slopcheck was not run because there was nothing to check.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| (none) | — | — | — | — | — | — |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Prototype Results (real data, this session)

Prototype scripts are in `/private/tmp/claude-501/-Users-noahmanion-Dropbox-code-idea-graveyard-feel-good-scorew/e9aca8f6-0367-4770-bd90-f3eef6a0daef/scratchpad/p4/` (`factors.py`, `bt.py`, `folds.py`, `attrib.py`, `blurb2.py`). They run against a frozen copy of `pipeline/src/fgs` and the derived parquet files.

### Walk-forward, test 2003–2021, holdout sealed, N=8 target [VERIFIED: prototype run]

| Candidate | Spearman N=8 | R² N=8 | Spearman N=4 | Brier | wk0 | early | mid | late |
|-----------|-------------|--------|--------------|-------|-----|-------|-----|------|
| ridge:+last16 (Phase 3 base) | 0.5155 | 0.2656 | 0.4664 | 0.2195 | 0.425 | 0.484 | 0.562 | 0.503 |
| ridge:+mov | 0.5181 | 0.2672 | 0.4681 | 0.2192 | 0.422 | 0.489 | 0.569 | 0.498 |
| ridge:+sow | 0.5228 | 0.2720 | 0.4716 | 0.2188 | 0.425 | 0.493 | 0.574 | 0.505 |
| ridge:+streak | 0.5228 | 0.2719 | 0.4712 | 0.2189 | 0.426 | 0.493 | 0.573 | 0.504 |
| ridge:+luck | 0.5219 | 0.2713 | 0.4706 | 0.2190 | 0.425 | 0.493 | 0.573 | 0.503 |

**BACKTEST_LOG rows to expect** (if the implementation matches the prototype definitions, these should reproduce to about 4 dp, the same way Phase 3 matched its prototype exactly):

| Factor | ΔSpearman N=8 | ΔR² N=8 | Fitted sign (1999–2021 proposal) | Note |
|--------|---------------|---------|------------------|------|
| mov | +0.0026 | +0.0015 | + (1.04 at this step) | + in 19/19 folds |
| sow | +0.0047 | +0.0048 | − (−1.29 at this step) | Positive alone, negative given Elo + mov (Pitfall 1) |
| streak | +0.0000 | −0.0001 | − (−0.15) | ~0. Kept per CONTEXT |
| luck | −0.0008 | −0.0006 | − (−0.30) | Negative Δ because sow already holds most of the signal. Alone vs base it is +0.0029. Kept and noted |

**Proposed weights.yaml after each step** (ridge, alpha = 0.001·n chosen by LOSO CV, n = 12,331):

| Step | elo | season_record | last16 | mov | sow | streak | luck |
|------|-----|---------------|--------|-----|-----|--------|------|
| +mov | 3.76 | 0.42 | −1.16 | 1.04 | | | |
| +sow | 3.92 | 0.79 | −0.90 | 1.54 | −1.29 | | |
| +streak | 3.96 | 0.87 | −0.94 | 1.55 | −1.25 | −0.15 | |
| +luck (final interim) | **3.75** | **0.90** | **−0.56** | **1.34** | **−1.07** | **−0.14** | **−0.30** |

**Sign stability across the 19 walk-forward folds:** elo, season_record and mov are + in all folds. luck is − in all 19 folds (−0.73 to −0.17). sow, last16 and streak are − in 16/19; the early folds with small training sets are positive. Alpha sensitivity: at alpha ≥ 0.1·n, sow flips to + and last16 to +. The CV-chosen 0.001·n is what the harness picks, so keep the procedure. Phase 6 owns any change.

**Collinearity** (Pearson on raw values, 1999–2021 REG weeks ≥ 1): mov–elo 0.85, mov–pd_pg 0.79, mov–sow 0.86, sow–elo 0.85, sow–last16 0.84, streak–last16 0.56, streak–season_record 0.70, luck–last16 0.69. VIF for the final 7-factor z set: elo 12.2, last16 13.2, sow 7.9, mov 6.8, season_record 4.4, luck 3.8, streak 2.2. That is high but ridge-stable, and it explains the offsetting bars (Pitfall 2).

**Raw factor ranges** (REG weeks): mov in [−24, 24], 5–95% [−10.6, 10.1]. sow in [−0.61, 0.63], 5–95% [−0.37, 0.37]. streak in [−8, 8]. luck in [−10, 10], 5–95% [−5, 5].

### Attribution check (all 19,422 snapshot rows 1999–2026, final interim weights) [VERIFIED: prototype run]

| Method | Exact Σ points == score − baseline | Slope (pts per composite unit) range | Rows with \|c\|<0.15 showing all-zero bars | max \|int − real\| | Sign flips vs contrib |
|--------|----|----|----|----|----|
| Literal (rounded integer map) | 19,422 / 19,422 | 0 to **47.3** | **174 of 527** | 0.78 | 0 |
| **Smoothed map (101 knots)** | 19,422 / 19,422 | 2.37 to 10.3 | **0 of 527** | 1.25 | 0 |

Baseline = `percentile_scores([0.0], ref)` = **49** (ref n = 13,226, ref median composite = +0.135, std 4.03). |points| per factor (median / p90 / max): elo 23/42/68, mov 8/16/26, sow 7/13/25, season_record 6/11/19, last16 3/7/13, luck 2/4/10, streak 1/2/4. Individual bars can exceed 50 (1999 week-0 CLE expansion seed) while offsetting bars bring the total back inside 0–100.

### Payload [VERIFIED: prototype run]
- `games/{season}.json` (columnar, 7 columns): 10.1–11.2 KB raw, 1.5–1.9 KB gzip per season. 28 files ≈ 310 KB raw total.
- Per-row additions (7-key `contribs` + 7-key `points` + ~85–135 char blurb) ≈ 345 bytes × ~670 rows ≈ +230 KB raw per season file, taking it from ~170 KB to ~400 KB. Blurbs repeat a lot, so gzip shrinks this well. Acceptable for a local, static site.

## Architecture Patterns

### System Architecture Diagram

```
nflverse cache ──► derive_games: replay ─► team_games (elo_pre both sides) ─► build_grid
                                                    │
                                                    ▼
                         features.build_features: season_record, last16, pd_pg,
                           + mov, sow, streak, luck  (per-game rolling → join_asof backward)
                                                    │
                                    ┌───────────────┴────────────────┐
                                    ▼                                ▼
                     score.composite(weights.yaml)          backtest (dev-only, firewall)
                     z_f, contrib_f, composite              RIDGE_SETS +mov,+sow,+streak,+luck
                                    │                        → BACKTEST_LOG.md, weights.yaml proposal
                                    ▼
                     mood.score_frame (frozen 1999–2021 ref) → score, rank, band, label
                                    │
                                    ▼
                     explain.attribute_points(scored, ref) → points_f (int), baseline
                     explain.blurb(row, points, nick)      → blurb (str)
                                    │
                                    ▼
                     export: snapshots/{s}.json rows + points + blurb; meta.baseline; meta.factors (7)
                             games/{s}.json (columnar)
                                    │
                                    ▼
   browser: #/team/ABBR[/s/w] ─► router ─► TeamPage: loadSeason(s) + loadGames(s) [+ loadGames(s-1) if <6 games]
                                            ├─ header (row: score, label, rank, delta, record)
                                            ├─ blurb
                                            ├─ FactorBars(points, meta.factors, baseline) → "= score"
                                            ├─ RecentGames(lib/team.recentGames(...))
                                            └─ sparkline (season rows) + link #/history/ABBR
```

### Recommended Structure (new/changed files)
```
pipeline/src/fgs/
├── features.py     # + _game_rolls(): mov, sow, streak, luck; FEATURE_COLUMNS extended
├── score.py        # FACTORS += mov, sow, streak, luck (label, description)
├── backtest.py     # RIDGE_SETS += 4 steps; PROPOSAL_FACTORS = last set
├── mood.py         # extract reference_values(df, value, ref_seasons) from score_frame (no behavior change)
├── explain.py      # NEW, pure: smooth_map, attribute_points, largest_remainder, PHRASES, blurb
└── export.py       # rows: points, blurb; meta.baseline; games/{season}.json
pipeline/tests/
├── test_features.py  # + mov/sow/streak/luck hand-computed on synthetic league
├── test_explain.py   # NEW: exact sum, near-zero, largest remainder, phrasebook
├── test_leakage.py   # FLOAT_EXACT += mov, sow, streak, luck; EXACT += points, blurb
└── test_export.py    # ROW_KEYS += points, blurb; META_KEYS += baseline; games files
web/src/
├── lib/router.ts     # {kind:'team', team, season?, week?}; teamHash(); remove team from RESERVED
├── lib/team.ts       # NEW pure: recentGames(), barRows(), findTeamRow()
├── lib/data.ts       # loadGames(meta, season) cached like loadSeason
├── lib/types.ts      # Row.points?, Row.blurb?, Meta.baseline?, GamesFile
└── components/
    ├── TeamPage.svelte, FactorBars.svelte, RecentGames.svelte (+ optional Sparkline.svelte)
    ├── BoardRow.svelte   # row becomes <a href=teamHash(...)> inside the <li>
    └── HistoryPage.svelte # summary line gets a "See {Team}" link to the team page
```

### Pattern 1: As-of rolling game factors (mirror `_last16`)
**What:** Compute per-game quantities over played team-games sorted by (franchise, season*100+asof_week, game_id). Use cumsum minus a shifted cumsum for last-N windows and a tiny loop for the streak. Keep the last row per key, then `join_asof` backward onto snapshot keys. Week 0 of season S picks up the final game of S−1, so values carry across the offseason. Fill nulls with 0, meaning no prior games.
**Example (verified in prototype):**
```python
# Source: scratchpad/p4/factors.py (prototype run against real cache)
MOV_N, MOV_CAP, SOW_N, STREAK_CAP, LUCK_N, ONE_SCORE = 8, 24, 8, 8, 16, 8

def _per_game(team_games):
    played = team_games.filter(pl.col("played"))
    opp = played.select("game_id", pl.col("franchise_id").alias("opponent_id"),
                        pl.col("elo_pre").alias("opp_elo_pre"))
    hfa = _hfa_table(played["season"].unique().to_list())  # season -> hfa_for(season)
    return (played.join(opp, on=["game_id", "opponent_id"], how="left")
        .join(hfa, on="season", how="left")
        .with_columns(
            (pl.col("points_for") - pl.col("points_against")).cast(pl.Float64).alias("margin"),
            pl.when(pl.col("neutral")).then(0.0).when(pl.col("is_home")).then(pl.col("hfa"))
              .otherwise(-pl.col("hfa")).alias("hfa_s"),
            (pl.col("season").cast(pl.Int64) * 100 + pl.col("asof_week").cast(pl.Int64)).alias("key"))
        .with_columns(
            pl.col("margin").clip(-MOV_CAP, MOV_CAP).alias("m_cap"),           # cap per game, then average
            (1 / (1 + 10 ** (-(MEAN_ELO - pl.col("opp_elo_pre") + pl.col("hfa_s")) / 400))).alias("p_avg"),
            ((pl.col("margin").abs() <= ONE_SCORE) & (pl.col("margin") > 0)).cast(pl.Float64).alias("cw"),
            ((pl.col("margin").abs() <= ONE_SCORE) & (pl.col("margin") < 0)).cast(pl.Float64).alias("cl"))
        .with_columns((pl.col("outcome") - pl.col("p_avg")).alias("sow_g"))
        .sort("franchise_id", "key", "game_id"))

def _win(col, n):   # sum over the last n rows per franchise (cumsum - shifted cumsum)
    c = pl.col(col).cum_sum().over("franchise_id")
    return c - c.shift(n).over("franchise_id").fill_null(0.0)

def _cnt(n):
    return pl.int_range(1, pl.len() + 1).over("franchise_id").clip(upper_bound=n)

# mov  = _win("m_cap", 8) / _cnt(8)
# sow  = _win("sow_g", 8) / _cnt(8)
# luck = _win("cw", 16) - _win("cl", 16)
# streak: per-franchise loop over outcome: 1 -> max(cur,0)+1, 0 -> min(cur,0)-1, 0.5 -> 0; clip to ±8
# then .group_by("franchise_id","key", maintain_order=True).last() and join_asof(by="franchise_id",
# strategy="backward", check_sortedness=False) onto snapshot key season*100+week; fill_null(0.0)
```
`_hfa_table` already exists in backtest.py. **Do not import it from backtest** because of the firewall. Duplicate the two-line helper in features.py, or move it to `season_config`.

### Pattern 2: Add-one-at-a-time backtest loop (extend Phase 3 harness, no new machinery)
```python
# backtest.py
RIDGE_SETS = {
    "ridge:elo": ["elo"],
    "ridge:+season_record": ["elo", "season_record"],
    "ridge:+last16": ["elo", "season_record", "last16"],
    "ridge:+mov":    ["elo", "season_record", "last16", "mov"],
    "ridge:+sow":    [..., "mov", "sow"],
    "ridge:+streak": [..., "mov", "sow", "streak"],
    "ridge:+luck":   [..., "mov", "sow", "streak", "luck"],
}
PROPOSAL_FACTORS = RIDGE_SETS[list(RIDGE_SETS)[-1]]   # the last set added
```
Per factor, as one atomic step: (1) add the column in features.py with a hand-computed test, (2) add the FACTORS entry in score.py, (3) add the RIDGE_SETS step, (4) `uv run fgs backtest --propose-weights`, (5) paste the 2-dp proposal into weights.yaml and update its header provenance, (6) append the BACKTEST_LOG row (delta = new ridge row minus previous ridge row). Order mov → sow → streak → luck. `_z_frame` z-scores `PROPOSAL_FACTORS`, so the last RIDGE_SETS entry must include every factor of every set. That holds automatically if each set extends the previous one.

### Pattern 3: Points attribution (smoothed frozen map + exact integer reconciliation)
```python
# Source: scratchpad/p4/attrib.py (verified: exact sums on 19,422 rows, slope 2.37..10.3)
def smooth_map(ref: np.ndarray, knots: int = 101):
    qs = np.linspace(0.0, 100.0, knots)
    xs = np.quantile(ref, qs / 100.0)           # ref = frozen 1999-2021 wk0+REG composites
    return xs, qs

def slope(c, xs, qs):
    """Average slope of the smoothed map from 0 to c; derivative at 0 when |c| < 1e-6."""
    i = int(np.searchsorted(xs, 0.0)); d0 = (qs[i] - qs[i-1]) / (xs[i] - xs[i-1])
    with np.errstate(divide="ignore", invalid="ignore"):
        s = (np.interp(c, xs, qs) - np.interp(0.0, xs, qs)) / c
    return np.where(np.abs(c) < 1e-6, d0, s)

def largest_remainder(real: np.ndarray, total: int) -> np.ndarray:
    """Integers summing exactly to total. Spread the residual by |real| first, so the
    leftover k after flooring is always in [0, n)."""
    resid = total - real.sum(); mag = np.abs(real)
    real = real + (resid * mag / mag.sum() if mag.sum() > 0 else resid / len(real))
    fl = np.floor(real); k = int(round(total - fl.sum()))
    out = fl.astype(np.int64)
    out[np.argsort(-(real - fl), kind="stable")[:k]] += 1   # stable => deterministic ties (factor order)
    return out

# per row: T = score - baseline (displayed ints); real_f = contrib_f * slope(c); points = largest_remainder(real, T)
# baseline = int(percentile_scores(np.array([0.0]), ref)[0])   # 49 with current weights
```
Why it is safe: score is monotone in c, so T always has the sign of c (or is 0). The residual spread is bounded at ≤1.25 points. Points use only the composite and the frozen reference, so they are leak-free.

### Pattern 4: Blurb phrasebook (deterministic, robust to sign flips)
Select the top 2 factors by |points| (ties broken by factor order). Skip factors with 0 points, skip season_record at week 0, and skip streak when |raw| < 2. Each phrase is the **fact** keyed by (factor, raw direction = sign(z), tier = |points| ≥ 10 ? strong : mild). Append a regression suffix when sign(points) ≠ direction, which happens for the negative-weight factors. The connector is "and" when the two points share a sign and "but" otherwise. The subject is `The {nick}` with **plural verbs**: every current `team_nick` is plural (Bills, 49ers, Commanders), so CONTEXT's "{Team} has" becomes "The {nick} have".

```python
FACT = {  # (strong, mild)
 ("elo","hi"): ("are one of the best teams in football", "are a good team on paper"),
 ("elo","lo"): ("are one of the worst teams in football", "are a below-average team on paper"),
 ("season_record","hi"): ("are {rec}", "are {rec}"),
 ("season_record","lo"): ("are just {rec}", "are {rec}"),
 ("last16","hi"): ("have won a lot over their last 16 games", "have a winning last 16 games"),
 ("last16","lo"): ("have lost a lot over their last 16 games", "have a losing last 16 games"),
 ("mov","hi"): ("have been blowing teams out", "have been winning by comfortable margins"),
 ("mov","lo"): ("have been getting blown out", "have been losing by wide margins"),
 ("sow","hi"): ("have a record that runs ahead of their margins", "have results a bit ahead of their margins"),
 ("sow","lo"): ("have a record that lags behind their margins", "have results a bit behind their margins"),
 ("streak","hi"): ("have won {k} straight", "have won {k} straight"),
 ("streak","lo"): ("are stuck in a {k}-game skid", "have lost {k} straight"),
 ("luck","hi"): ("have won a lot of coin-flip games", "have won more than their share of close games"),
 ("luck","lo"): ("have lost a lot of coin-flip games", "have lost more than their share of close games"),
}
FADE = {"hi": " (that tends to fade)", "lo": " (that tends to even out)"}
# week 0 lead: "Preseason, carrying last season's form: the {nick} ..."; nothing nonzero: "... are about as average as it gets right now."
```
Real output (prototype, 2026 week 9; the sow wording here is the earlier draft and has since been replaced by "record that runs ahead of their margins"):
- BUF 7-1, 96: "The Bills are one of the best teams in football, but have been winning games their margins say were close calls (that tends to fade)."
- JAX 6-2, 94: "The Jaguars are one of the best teams in football, and have been blowing teams out."
- LAC 0-8, 7: "The Chargers are one of the worst teams in football, and have been getting blown out."
- TEN 1-7, 5: "The Titans are one of the worst teams in football, but have been losing games their margins say they should win (that tends to even out)."
- DET 6-2, 80: "The Lions are one of the best teams in football, and are 6-2."
- 2003 week 8 CAR 6-1, 50 (the "8-2 but worried" hook): "The Panthers have been winning games their margins say were close calls (that tends to fade), but are 6-1."
- 2026 week 0 SEA: "Preseason, carrying last season's form: the Seahawks are one of the best teams in football, and have been blowing teams out."
- Length: median 85, p90 135, max 179 characters.

### Pattern 5: Team page (web)
- **Router:** add `{ kind: 'team'; team: string; season?: number; week?: number }` with regex `^/team/([A-Za-z]{2,3})(?:/(\d{4})/(\d{1,2}))?/?$`, uppercased. Remove the team pattern from `RESERVED` (keep records/methodology). Add `teamHash(abbr, season?, week?)`. App validates against meta: an unknown team gets `replace('#/')` plus a notice, and a bad season/week gets `replace(teamHash(abbr))`.
- **Data:** `#/team/ABBR` uses `meta.latest`. Load `snapshots/{season}.json` with the existing `loadSeason`, which is also needed for the sparkline, and `games/{season}.json` with a new `loadGames`, cached per season and evicted on failure. When fewer than 6 played games exist in that season as of the week (always true at week 0), also load `games/{season-1}.json` if that season exists.
- **`lib/team.ts` (pure, vitest):** `recentGames(files, team, season, week, n=6)` keeps games where team ∈ {home, away}, scores are non-null, and (season < S or week ≤ W). It sorts by (season, gameday, week) descending, takes n, and maps to {season, week, opp, home: bool, neutral?, result 'W'|'L'|'T', pf, pa, margin}. `barRows(points, factors, baseline, top=4)` sorts by |points| desc with factor order as the tiebreak, splits into the top 4 and the rest for `<details>`, and returns `scale = max(1, max|points|)` for the bar widths.
- **FactorBars:** each factor is an `<li>` with label, signed integer text (`+12`, `−7`, `0`), and a CSS bar from the center line (width = |p|/scale·50%, `--up` right / `--down` left). The baseline marker reads "Average team {baseline}" and the total line reads "= {score}", always visible even when some factors are inside `<details>` "All factors". Rule 4 of the UI-SPEC: show the top 4 and collapse the rest.
- **BoardRow:** wrap the row contents in `<a class="row" href={teamHash(...)}>` inside the `<li>`. Use `teamHash(abbr)` on the latest board and `teamHash(abbr, season, week)` on historical boards. Hover background `--bg`, accent focus ring (UI-SPEC rule 5). The visually-hidden sr text stays inside the link.
- **Header:** TeamChip at 24px (an allowed variant, so add a `size` prop), name in Display 28, score in Display 28, MoodLabel in Heading 20, record, "#rank", Delta. Neither nav item is `aria-current` on the team page.

### Anti-Patterns to Avoid
- **Using the rounded integer map for the attribution ratio:** blows up to 47×/c and zeroes 174 near-average rows (Prototype Results).
- **Phrasing by points sign alone:** last16, sow, streak and luck have negative weights, so a positive bar means a *bad* raw value. Key phrases on raw direction and add the fade suffix.
- **Importing `_hfa_table` from backtest into features:** breaks the leakage firewall test (`test_backtest_not_imported_upstream`).
- **Adding a factor to weights.yaml before score.FACTORS:** `load_weights` raises on unknown keys.
- **Deriving recent games from `week` alone without considering the snapshot week:** the page as of week W must not show week W+1 games even though `games/{season}.json` contains the whole schedule.
- **Recomputing points in the browser:** the reference set is not shipped. Points come only from the pipeline.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ridge, alpha CV, walk-forward folds, Brier | New fitting code | `backtest._ridge_walk_forward`, `choose_alpha`, `propose_weights`, `format_proposal` | Already verified against the Phase 3 prototype. Just extend RIDGE_SETS |
| Next-N target | Anything new | `backtest.targets` | Locked target (BACK-01) |
| Per-snapshot z, contribs | New z code | `score.zscore`, `score.composite` | Zero-variance guard already handled |
| Percentile reference | Another reference filter | Extract `mood.reference_values()` from `score_frame` and call it from both | One frozen reference avoids silent drift |
| Rolling windows | Python loops (except streak) | cumsum − shifted cumsum + `join_asof` (as `_last16`) | Already proven leak-free |
| Hash routing, season caching | New router or fetch layer | `router.ts`, `route.svelte.ts`, `data.ts` patterns | Stale-response and eviction rules already solved |
| Contrast fallback for team colour | New colour logic | `history.ts pickHighlight` | Sparkline line colour |

**Key insight:** this phase is mostly extension. The only genuinely new algorithms are the attribution reconciliation (about 20 lines) and the phrasebook.

## Common Pitfalls

### Pitfall 1: sow fits negative, so bars and words read backwards from CONTEXT's example
**What goes wrong:** CONTEXT expects sow+ to read as "has beaten good teams" in a positive way. With elo and mov in the model, the fitted sow weight is −1.07, so a team that beat good teams gets a **negative** sow bar.
**Why:** Elo's update already rewards wins over strong opponents. Given Elo and mov, high sow means W/L results running ahead of margins, which regresses. Evidence: sow alone has weight +3.32; elo+sow gives −0.28; elo+mov+sow gives −1.06.
**How to avoid:** Keep the factor (CONTEXT: the data decides). Keep its raw-meaning label in `meta.factors` ("Quality of results"). Use the raw-direction phrase plus the "(that tends to fade)" suffix. Record the sign and this explanation in the BACKTEST_LOG note.
**Warning signs:** blurbs saying "has beaten good teams" next to a red bar.

### Pitfall 2: Offsetting bars from collinear factors
**What goes wrong:** 2026 week 9 BUF shows mov +12 and sow −13, and elo +49 with last16 −7. A fan may read "Last 16 games −7" for a 7-1 team as a bug.
**How to avoid:** Each factor's description in meta (shown on the page as a tooltip-free secondary line, or under `<details>`) explains the direction. The negative-weight factors' descriptions should say that a hot value counts against the score. The page's "= {score}" total keeps it honest. Don't orthogonalize: that would change the locked definitions.

### Pitfall 3: Literal attribution near c ≈ 0
See Pattern 3 and Prototype Results. Unit-test a row with c = 1e-9 and offsetting contribs: points must be finite, sum to T (usually 0), and not all be zero.

### Pitfall 4: Leakage test doesn't cover the new columns
`test_leakage.FLOAT_EXACT` lists `elo, season_record, last16, composite` explicitly. z_ and contrib_ columns are picked up automatically, but raw mov/sow/streak/luck, `points` and `blurb` are not. Add the raw columns (or derive the list from `features.FEATURE_COLUMNS`), and compare points/blurb on the export path (or on an `explain` frame) for exact equality.

### Pitfall 5: Elo dominates the top slot
Elo has the largest |points| in 83.8% of rows. The second slot is mov 46%, sow 21%, season_record 20%, last16 4%, luck 1.5% and streak 0.1%. Streak and luck will almost never appear in blurbs, which is honest given their weights. Make the Elo phrase tiered so the sentence still informs.

### Pitfall 6: Streak phrase with k = 0 or 1
"have won 0 straight" can appear when z > 0 but the raw value is 0. Skip streak when |raw| < 2 and fall through to the next factor.

### Pitfall 7: Week 0
season_record z = 0 at week 0 (zero variance), so its points are 0. mov, sow, streak and luck carry last season's final values with no regression (Elo alone regresses ⅓). The blurb lead must say "Preseason, carrying last season's form". Recent games at week 0 come entirely from `games/{season-1}.json`. For 1999 week 0 there are none, so show "No games yet".

### Pitfall 8: Points vs contribs rounding
contribs are exported at 2 dp, but compute points from the **unrounded** contrib columns. Otherwise a browser re-sum check can disagree. Never test Σcontribs == composite on exported values with a tolerance under 0.01·n.

### Pitfall 9: Hysteresis label vs score
The bars sum to the **score**. The mood label is hysteresis-adjusted and can sit one band off the raw score. That is expected (Phase 2), so don't "fix" it on the team page.

### Pitfall 10: BoardRow as a link
The `<a>` must sit inside the `<li>` (list semantics) and wrap the whole grid. Moving the grid styles from `li.row` to `a.row` means `color: inherit; text-decoration: none`. The existing mobile layout must not change.

## Code Examples

### Export additions (sketch)
```python
# export.py
from fgs import explain
ref = mood.reference_values(derived["features"], "composite")          # frozen 1999-2021
scored = explain.add_points(scored, weights, ref)                       # -> pts_{f} int columns
baseline = explain.baseline(ref)
nicks = {k: v["nick"] for k, v in teams.items()}
# _row: "points": {k: int(r[f"pts_{k}"]) for k in factor_keys}, "blurb": explain.blurb(r, factor_keys, nicks[...])
files["meta.json"]["baseline"] = baseline
for season in seasons:
    g = games.filter(pl.col("season") == season).sort("gameday", "gametime", "game_id")
    files[f"games/{season}.json"] = {"season": season, **{
        "week": g["week"].to_list(), "asof_week": g["asof_week"].to_list(),
        "home": g["home_id"].to_list(), "away": g["away_id"].to_list(),
        "home_score": g["home_score"].to_list(), "away_score": g["away_score"].to_list(),
        "game_type": g["game_type"].to_list(), "gameday": g["gameday"].to_list(),
        "neutral": g["neutral"].to_list()}}
```
`asof_week` and `neutral` are small additive columns beyond CONTEXT's list. `asof_week` makes the as-of filter correct for postponed games (all 7,548 cached games currently have asof_week == week). `neutral` lets the page say "neutral" instead of home/away. Both are optional, and the planner may drop them.

### New FACTORS entries (score.py)
```python
"mov":    {"label": "Margin of victory", "description": "Average point margin over the last 8 games (each capped at 24), including last season and playoffs"},
"sow":    {"label": "Quality of results", "description": "Results over the last 8 games compared with what an average team would do against the same opponents"},
"streak": {"label": "Streak", "description": "Current win or loss streak (ties end it), up to 8, carried across seasons"},
"luck":   {"label": "Close-game luck", "description": "One-score wins minus one-score losses (8 points or fewer) over the last 16 games"},
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Row `contribs` only (3 factors) | `contribs` + `points` + `blurb` (7 factors) | Phase 4 | `types.ts` optional fields. Board unaffected |
| `#/team/...` reserved → redirect | Real team route | Phase 4 | router.test "reserved" case for team must change |
| weights: elo 4.58 / season_record 0.63 / last16 −1.25 | 7 weights (final interim above) | Phase 4 | Every historical score shifts once. The frozen reference is recomputed from new composites (still 1999–2021 only), so it stays leak-free |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The smoothed (unrounded, 101-knot) percentile map counts as "the frozen-reference percentile map" under CONTEXT's attribution decision | Pattern 3 | Low: the sum-to-displayed-score guarantee is unchanged. If the user insists on the literal integer map, near-average teams show all-zero bars |
| A2 | Plural-verb subject "The {nick} have…" instead of "{Team} has…" | Pattern 4 | Cosmetic |
| A3 | Optional `asof_week` and `neutral` columns in games files are acceptable additive contract changes | Code Examples | Low. Drop them if the planner wants the exact CONTEXT column list |
| A4 | Recent games cross the season boundary (load the prior season's games file) | Pattern 5 | Low. Otherwise week 0–5 pages show fewer than 6 games |
| A5 | Ridge alpha grid / LOSO CV unchanged (picks 0.001·n) | Prototype Results | Weights move if Phase 6 changes the procedure. That is expected |

## Open Questions (RESOLVED)

1. **Literal integer map vs smoothed map for the attribution ratio?**
   - RESOLVED: use the smoothed, unrounded frozen-reference map for the ratio, and reconcile exactly to the displayed integer score − baseline. Evidence is in the attribution table. This satisfies the decision's invariant (Σ points = score − baseline, baseline = score(0) integer).
2. **Baseline is 49, not 50. Fix it?**
   - RESOLVED: no. Export the computed `meta.baseline` (49 now) and label it "Average team 49". It is honest: the reference median composite is slightly above 0. Tests must read it from meta, never hardcode 50.
3. **sow's negative sign contradicts CONTEXT's "beating good teams scores high" example. Redefine?**
   - RESOLVED: no. The definition is locked and the raw value does score high. Only the *weight* is negative given Elo + mov. Keep it, phrase it honestly (Pattern 4), and log the explanation in BACKTEST_LOG.
4. **luck's ΔSpearman is negative (−0.0008) in the locked order. Drop it?**
   - RESOLVED: keep it (CONTEXT). Note in the log: "+0.0029 when added alone to base. sow absorbs most of the signal. Sign − in 19/19 folds."
5. **Top-2 rule picks Elo first 84% of the time. Exclude Elo from blurbs?**
   - RESOLVED: keep the literal rule (locked) with tiered Elo phrases. The second clause carries the insight, and real outputs read well. Excluding Elo would deviate from CONTEXT, so don't.
6. **Where do points live: score.py, mood.py, or new module?**
   - RESOLVED: new pure `fgs/explain.py`, with `mood.reference_values()` extracted and shared. Add explain.py to the firewall test's module list.
7. **Plot or CSS for bars? Sparkline?**
   - RESOLVED: CSS bars. Sparkline is optional. If built, use Plot `lineY` with y domain [0,100] and no axes, coloured by `pickHighlight`.
8. **Does the exported `games/{season}.json` include unplayed games?**
   - RESOLVED: yes, with null scores. It costs nothing and a later phase can use it for "next game". The frontend filters out games with null scores and games after the as-of week.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | pipeline | ✓ | 0.10.12 | — |
| Python | pipeline | ✓ | 3.13 (via uv) | — |
| Node | web | ✓ via nvm | 22.23.3 (`.nvmrc` = 22; default shell node is 20.19, so run `nvm use` first) | — |
| Cached schedules / derived parquet | prototype + real-cache tests | ✓ | latest 2026 week 9 | — |
| `fgs backtest` runtime | per-factor loop | ✓ | ~1.3 s | — |

**Side effect during research:** while timing it, `uv run fgs backtest` was run once from `pipeline/`. It rewrote `pipeline/data/derived/backtest.json` at 13:20, a deterministic regeneration from the current committed code and weights. No source files were touched. `feel-good-scorew` does not appear to be a git working tree from this shell (`git status` reported "not a git repository"), so the orchestrator should check repo state before committing.

**Missing dependencies:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.2 (pipeline); vitest 5.1 + svelte-check (web) |
| Config file | `pipeline/pyproject.toml [tool.pytest.ini_options]`; `web/package.json` scripts |
| Quick run command | `cd pipeline && uv run pytest -q tests/test_features.py tests/test_explain.py tests/test_leakage.py` |
| Full suite command | `cd pipeline && uv run pytest -q && cd ../web && source ~/.nvm/nvm.sh && nvm use && npm test && npm run check && npm run build` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODEL-06 | mov = mean capped margin over last 8 played (REG+PO), crosses seasons, cap ±24, none → 0 | unit (synthetic, hand-computed) | `uv run pytest tests/test_features.py -k mov -x` | ❌ Wave 0 |
| MODEL-07 | sow = mean(result − p_avg) with opponent pre-game Elo, HFA sign, neutral = 0, tie = 0.5 | unit (hand-computed p_avg) | `uv run pytest tests/test_features.py -k sow -x` | ❌ Wave 0 |
| MODEL-09 | streak sign/length, tie → 0, carries across seasons, cap ±8 | unit | `uv run pytest tests/test_features.py -k streak -x` | ❌ Wave 0 |
| MODEL-10 | luck = one-score W − L over last 16, \|m\| ≤ 8 inclusive, ties excluded | unit | `uv run pytest tests/test_features.py -k luck -x` | ❌ Wave 0 |
| MODEL-06/07/09/10 | Report has ridge:+mov … +luck rows; N=8 Spearman of +luck in [0.519, 0.525]; holdout still sealed | integration (real_cache) | `uv run pytest tests/test_backtest.py -k "ridge_composites or holdout" -x` | ✅ (extend) |
| MODEL-06/07/09/10 | BACKTEST_LOG has 4 new rows; weights.yaml has 7 keys that load | grep + unit | `grep -cE "^\| .* \| (mov\|sow\|streak\|luck) \|" BACKTEST_LOG.md` ; `uv run pytest tests/test_backtest.py -k weights_yaml -x` | ✅ (extend) |
| MODEL-06/07/09/10 | New factor values unchanged by fake future / truncation | integration | `uv run pytest tests/test_leakage.py -x` | ✅ (extend columns) |
| SITE-02 | Σ points == score − baseline for every exported row; baseline == meta.baseline; points keys == factor keys; ints | contract (real) | `uv run pytest tests/test_export.py -k points -x` | ❌ Wave 0 |
| SITE-02 | largest_remainder exact and deterministic; near-zero c finite; all-zero contribs → zeros | unit | `uv run pytest tests/test_explain.py -x` | ❌ Wave 0 |
| SITE-02 | games/{season}.json exists per season, columns equal length, scores null iff unplayed | contract | `uv run pytest tests/test_export.py -k games -x` | ❌ Wave 0 |
| SITE-02 | router parses `#/team/BUF`, `#/team/buf/2024/5`; teamHash; reserved no longer includes team | unit (vitest) | `cd web && npm test` | ✅ router.test.ts (extend) |
| SITE-02 | recentGames: as-of filter, prior-season fill, W/L/T, margin sign, max 6; barRows sorting/top-4/scale | unit (vitest) | `cd web && npm test` | ❌ Wave 0 (`lib/team.test.ts`) |
| SITE-02 | Page renders at 375 px, bars sum label "= score", no horizontal scroll, row links work | manual (visual) | `npm run dev` → `#/team/BUF`, `#/team/DEN/2026/9`, `#/team/CLE/1999/0` | manual-only |
| INSIGHT-05 | Every row has a non-empty blurb ending in "."; plural subject; "but" iff top-2 signs differ; week-0 lead; no "0 straight" | unit + contract | `uv run pytest tests/test_explain.py -k blurb -x` ; `uv run pytest tests/test_export.py -k blurb -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the quick run command (a few seconds).
- **Per factor step:** `uv run fgs backtest` (~1.3 s), then compare against the Prototype Results table (±0.002).
- **Per wave merge:** full pipeline suite plus `npm test && npm run check`.
- **Phase gate:** full suite green, `uv run fgs export` regenerates committed JSON with 7 factors, then a browser check of the team page at 375 px and 1280 px in light and dark, before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `pipeline/tests/test_explain.py`: attribution, largest remainder, phrasebook
- [ ] `tests/test_features.py`: synthetic cases for the 4 factors. The conftest `_ROWS` league has a tie (NE–NYJ), a neutral game, a playoff game and a season boundary, enough to hand-compute mov/sow/streak/luck.
- [ ] Extend `tests/test_leakage.py` columns and `tests/test_export.py` ROW_KEYS/META_KEYS (+points, blurb, baseline)
- [ ] `web/src/lib/team.test.ts`. Update the router.test.ts reserved-team case.
- [ ] No framework installs needed.

## Security Domain

`security_enforcement` is `false` in `.planning/config.json`, so this section is omitted. The only relevant note: blurbs are plain strings rendered as Svelte text (never `{@html}`), so there is no injection surface.

## Sources

### Primary (HIGH confidence)
- Codebase: `pipeline/src/fgs/{features,score,backtest,mood,export,elo,games,season_config,cli}.py`, `pipeline/tests/{conftest,test_leakage}.py`, `pipeline/weights.yaml`, `pipeline/BACKTEST_LOG.md`, `web/src/lib/*.ts`, `web/src/components/{BoardRow,TeamChip,SiteHeader,HistoryPage}.svelte`, `web/public/data/*`
- Planning: 04-CONTEXT.md, 03-CONTEXT.md, 03-0{1,2,3,4}-SUMMARY.md, 03-03-PLAN.md, 03-VALIDATION.md, 02-UI-SPEC.md "Design System for Later Phases", REQUIREMENTS.md, STATE.md
- Prototype runs in this session (scratchpad/p4): walk-forward deltas, fold signs, alpha sensitivity, collinearity/VIF, attribution over 19,422 rows, blurbs on real teams, payload sizes

### Secondary / Tertiary
- None needed. No external library behaviour beyond what is already installed and exercised by the codebase.

## Metadata

**Confidence breakdown:**
- Factor definitions and backtest numbers: HIGH. Reproduced the Phase 3 base exactly, then measured each addition.
- Attribution algorithm: HIGH. Exact sum verified on every row, with edge behaviour measured.
- Phrasebook: MEDIUM. Reads well on sampled teams, but the wording is subjective (Claude's discretion).
- Web plan: HIGH for structure (follows existing patterns), MEDIUM for visual details, which need a browser check.

**Research date:** 2026-11-11
**Valid until:** until weights.yaml or the factor definitions change (Phase 5 adds factors and changes every number above)

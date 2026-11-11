# Phase 4: Game-Result Factors & Team Deep-Dive - Context

**Gathered:** 2026-11-11
**Status:** Ready for planning
**Mode:** Autonomous — recommended answers auto-accepted (user granted full autonomy)

<domain>
## Phase Boundary

Add four schedule-derived factors to the additive composite — strength of win (margin), opponent quality of results, current streak, close-game luck — ONE AT A TIME, each with a recorded walk-forward backtest delta and fitted sign (training 1999–2021 only; 2022–2025 holdout stays sealed). Ship the team deep-dive page: score, mood, one-liner, diverging factor bars that sum exactly to the displayed score, and recent games. Efficiency/QB/simulator factors are Phase 5; weight freeze is Phase 6.

</domain>

<decisions>
## Implementation Decisions

### Factor definitions (as-of: only games with asof_week ≤ week; REG + playoffs; spans season boundaries where noted)
- `mov` (MODEL-06, strength of win): mean point margin over the team's last 8 played games (crossing season boundaries), each game's margin capped at ±24 (blowout cap). No games → 0.
- `sow` (MODEL-07, opponent quality / strength of win by opponent): mean over last 8 played games of (result − p_avg), where result ∈ {1, 0.5, 0} and p_avg = Elo win prob of a league-average (1505) team vs that opponent's PRE-GAME Elo at the same venue/HFA. Beating good teams scores high; losing to bad teams scores low. Kept separate from `mov`.
- `streak` (MODEL-09): signed current streak (+k for k straight wins, −k for losses), ties end streaks (→0), carries across seasons, capped at ±8.
- `luck` (MODEL-10): net one-score record over last 16 games: (# wins with |margin| ≤ 8) − (# losses with |margin| ≤ 8). Expect a NEGATIVE fitted sign (lucky teams regress) — that is the honest outcome; do not constrain.
- Add order: mov → sow → streak → luck. After each: refit interim walk-forward Ridge (same procedure as Phase 3), run `fgs backtest`, append row to `pipeline/BACKTEST_LOG.md` (factor, ΔSpearman N=8, ΔR², fitted sign, kept/dropped note), update `pipeline/weights.yaml`. A factor whose ΔSpearman is negative is still kept in v1 (single score, data decides weight; Phase 6 finalizes), but note it.
- All factors exported in `meta.factors` with human labels + one-sentence descriptions.

### Score-point attribution (bars sum to the displayed score)
- For each snapshot row, pipeline computes `points` per factor: points_f = contrib_f × (score(c) − score(0)) / c where c = composite and score(·) is the frozen-reference percentile map; when |c| < 1e-6 use the derivative of score at 0. Baseline = score(0) (≈50, "an average team"). Round to integers with largest-remainder so Σ points = displayed score − baseline exactly (baseline also integer). Exported per row as `points: {factor: int}` + `meta.baseline`.

### One-liner (INSIGHT-05)
- Pipeline generates `blurb` per row from the top 2 factors by |points| using a phrasebook keyed by (factor, sign, magnitude tier) — e.g. mov+ "has been blowing teams out", luck+ "has won a lot of coin-flip games (that rarely lasts)", streak− "is stuck in a 4-game skid", sow+ "has beaten good teams". Template: "{Team} {phrase1}{, and/but} {phrase2}." ("but" when signs differ). Deterministic; no LLM. Week 0 blurb: explains preseason carryover.

### Team page (SITE-02)
- Route `#/team/{ABBR}` (latest) and `#/team/{ABBR}/{season}/{week}`; board rows and history chart team label link to it; nav still shows Board · Mood over time.
- Content: header (color chip, full name, record, rank, big score, mood label + emoji, delta), blurb, factor breakdown (diverging horizontal bars: baseline marker labeled "Average team {baseline}", one bar per factor in points, sorted by |points|, positive right/negative left, final "= {score}" total line), recent games list (last 6 played as-of that week: week label, opponent chip/abbr, home/away, W/L/T, score, margin), small sparkline of this season's score (Plot, optional) and link to `#/history/{ABBR}`.
- Data: extend `teams/{ABBR}.json` with `recent_games` per (season, week) is too big — instead export `games/{season}.json` (compact game list) OR include last-6 games inline in each season-file row? Decision: per-season `games/{season}.json` (columnar: week, home, away, home_score, away_score, game_type, gameday) and the frontend derives recent games; season rows carry `points` + `blurb`.
- Follow 02-UI-SPEC "Design System for Later Phases" (factor breakdown + team page rules), no decimals, no logos.

### Claude's Discretion
- Phrasebook wording, bar chart implementation (plain SVG/CSS vs Plot), magnitude tiers, component structure.

</decisions>

<code_context>
## Existing Code Insights

- Phase 3 (in progress) provides `features.py` (season_record, last16, pd_pg), `score.py` (z-scores, Σ w·z, contribs, zero-variance guard), walk-forward Ridge + `--propose-weights`, `weights.yaml`, `BACKTEST_LOG.md`, frozen 1999–2021 percentile reference, export with `meta.factors` + row `contribs`, `#/history` chart page, router with reserved `#/team/...`.
- Elo replay gives pre-game ratings per game (needed for `sow` p_avg).

</code_context>

<specifics>
## Specific Ideas

- The "8-2 but worried" hook starts here: a high-record team whose `luck` and `sow` points are negative should read clearly on its team page.

</specifics>

<deferred>
## Deferred Ideas

- Perception-gap callouts (Phase 8), "good loss" modeling (v2), efficiency/QB factors (Phase 5).

</deferred>

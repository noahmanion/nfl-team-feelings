# Project Research Summary

**Project:** Feel-Good Score
**Domain:** NFL team rating (momentum-weighted Elo variant) + backtest harness + static "how should fans feel" visualization site
**Researched:** 2026-11-11
**Confidence:** MEDIUM-HIGH (data/tooling HIGH; factor-evidence and expectation-data MEDIUM)

## Executive Summary

An offline batch pipeline: Python replays every game since 1999 chronologically, builds a per-team per-snapshot rating, exports static JSON, and a model-free frontend renders it — the 538/nfelo/FPI pattern. The twist: the headline number is a ~10-factor composite whose core value is being *predictively true*, so the backtest harness is a core component, not QA. Market gap: nobody headlines "record vs. evidence," and with 538 gone there is no free long-history "every team over time" chart.

**Approach:** Python 3.13 + `uv`, nflreadpy (Polars), hand-rolled NumPy Elo, scikit-learn Ridge for weights, vectorized NumPy Monte Carlo; Vite + Svelte 5 + Observable Plot with hash routing; the only contract is JSON in `web/public/data/`. The model must be strictly additive (score = Σ weight × per-snapshot z-score, contributions stored) — decided in the model phase, because it enables the breakdown, one-liners, and honest explanations. Build backtest + baselines before any momentum factor so each factor earns its place by metric delta.

**Main risk:** user-requested inputs (streaks, close-game results) are known to be mostly non-predictive. Mitigation: backtest decides every sign, and "how it is" vs "how it feels" becomes the product. Other critical risks — look-ahead leakage, overfitting ~10 collinear weights on a few hundred effective team-seasons, franchise-identity breaks — need early structural prevention.

## Conflicts & Resolutions (treat as decisions)

1. **Streak / close-game luck likely non-predictive → sign is empirical.** Don't constrain signs; backtest decides and fitted signs are reported. If they don't earn weight, move them to a "vibes" layer shown as "how it feels" beside the predictive "how it is" score — the gap is the signature feature. If the user insists on a positive streak weight: cap ~5% of score variance and disclose the measured accuracy cost. Define momentum as trajectory (EWMA of opponent-adjusted EPA minus season-to-date level, ~4–8 games), not streak length.
2. **Draft bump vs. no-tanking → surplus over slot expectation.** Raw draft capital rewards worst teams. Use (value of picks held) − (value expected for original slot), flatter `stuart`/`otc` chart, cap, and let `k_draft` land near 0. Acceptance check: worst team doesn't jump just for owning pick #1. If no signal: draft is display text only.
3. **Win-total gaps → model-derived expectation by default, optional CSV override.** nflverse `win_totals.csv` covers 2003–2020 only. Primary expectation = post-regression preseason Elo run through the simulator (always available, leakage-free); Vegas/manual lines override where present; every row carries `expectation_source`. Validate model vs Vegas on 2003–2020 (expect r ≈ 0.7–0.8). Never sum in-season closing spreads as "preseason."
4. **Playoff odds need a custom Monte Carlo — and the input is probably circular.** No free historical odds; nflseedR is R-only. NumPy sim with simplified tiebreakers and era rules from a season-config table (31 teams 1999–2001; 12 playoff teams → 14 from 2020; 16 → 17 games from 2021). 2–5k sims, vectorized, cached by (season, week, model_version). Expect ~0 weight; keep for display/callouts. Same sim yields preseason expected wins → build once.
5. **Backtest target = next-N opponent-adjusted margin, not win%.** Primary: opponent- and HFA-adjusted average margin over the next 4–8 games within season — written in README before tuning. Secondary: next-game Brier/log-loss vs Elo and spread; rest-of-season win%. Next-8 win% is the shareable story number. Report by week bucket and in-season vs across-offseason.

Smaller resolutions: Polars not pandas; `pipeline/` + `web/` directory names; ties = 0.5 and end streaks; BUF–CIN 2022 has no result and must not crash; draft reaction stays v1 but is sequenced after the in-season model is validated.

## Key Findings

### Recommended Stack
Verified live 2026-11-11 (real nflreadpy 0.1.5 loads with Polars 2.1.0). nflreadpy is "experimental" — pin it.
- Python 3.13 + uv — self-contained env in `pipeline/`
- nflreadpy 0.1.5 — schedules (spreads, starting QB), pbp EPA from 1999, draft picks, teams
- Polars 2.1 + NumPy 2.5 — rolling windows; sequential Elo + Monte Carlo in NumPy; hand-roll Elo (~15 lines)
- scikit-learn RidgeCV (+ optional Optuna for non-linear hyperparams) — walk-forward weight fits
- Vite 8 + Svelte 5 + Observable Plot 0.6.19 — static SPA; Node 22/24; TypeScript ~6.0
- JSON split: `meta`, `latest`, `snapshots/`, `teams/{ABBR}`, columnar `history`, `callouts`

Data notes: spreads for all games since 1999; moneylines reliable only from 2007; CPOE only from 2006 (use EPA/dropback + success rate for QB); raw team codes mix eras → franchise mapping required.

### Expected Features
**Table stakes:** 32-team mood board, team deep-dive with breakdown + recent games, methodology page, "last updated" stamp, mobile layout, hash deep links.
**Differentiators (P1 here):** perception-gap callout (record-implied rank as naive baseline + base-rate evidence line); percentile-tiered mood labels with hysteresis; multi-season mood-over-time chart; records page with misery streaks in calendar days; backtest transparency chart; diverging-bar breakdown with a one-liner.
**Defer:** scrubber, movers strip, "my team" pin, OG share images, EPA scatter, FA reaction, "good loss" modeling.
**Never:** weight sliders, betting picks, sentiment ingestion, live updates, accounts, decimal-precision scores.

### Architecture Approach
Strictly downward data flow: ingest → model core → evaluate/publish → frontend with no model logic. Backtest and exporter share one `model/` package. Weights in committed `weights.yaml` (tuner proposes, human promotes). Full replay each run.
Components: ingest + franchise mapping; long team-game fact table; Elo + `offseason_transition()`; as-of feature builder; season simulator; additive combiner; backtest/tuner; callout detector + exporter; static frontend. Pattern: `(season, week, franchise)` snapshot grid with as-of join, plus week-0 post-draft snapshot.

### Critical Pitfalls
1. **Look-ahead leakage** — opponents' pre-game Elo, per-snapshot z-scores, preseason-only expectations; fake-future-games unit test; beating the Vegas spread = leak.
2. **Overfitting ~10 collinear weights** — baselines first, Ridge on standardized inputs, walk-forward by season, 2022–2025 holdout looked at once, season-level bootstrap, collapse record/last-16/streak block.
3. **Rewarding non-predictive inputs** — empirical signs + score-vs-vibes split.
4. **Franchise identity / era rules** — relocations, HOU from 2002, 31 teams 1999–2001, 16 vs 17 games, ties, neutral sites, era-varying HFA → `franchise_id`, season-config table, count assertions.
5. **Offseason continuity / noisy EPA** — regress Elo at boundary, decay prior-season games in window, starting-QB-changed adjustment; filter garbage time, opponent-adjust as-of, EWMA trend, flag 1999–2000 low-confidence.

Also: manual top-10 review of every "aha" extreme (multiple comparisons and data bugs).

## Implications for Roadmap

1. **Data Foundation** — games + team-game tables, PBP aggregates, draft capital, season-config, franchise mapping, `checks.py`. Gate: 32 franchises post-2002 (31 for 1999–2001), unbroken LV/LAC/LA, correct games per team-season.
2. **Base Rating + Backtest Harness** (core-value gate) — Elo with MOV, era-aware HFA, regression, expansion seeding; snapshot grid; baselines (Elo, season W%, last-16, point diff, spread); primary target in README; leakage test. Gate: Elo Brier ≈ 0.22–0.23, leakage test passes.
3. **JSON Contract + Skeleton UI** — lock contract on Elo-only scores; Vite + Svelte skeleton with board + team page; dated-event timeline. Can run parallel with 4.
4. **Momentum Model, Simulator & Tuning** — factors one at a time; simulator (playoff odds + expected wins); optional win-total override; additive combiner; Ridge tuning, rounded `weights.yaml`, bootstrap intervals, holdout. Gate: beats Elo baseline out of sample.
5. **Offseason, Labels & Insights** — surplus-over-slot draft term with cap, QB-change adjustment, week-0 snapshots, percentile mood bands, perception-gap detector, calendar-day streaks, historical extremes, `callouts.json`.
6. **Viz Polish & Weekly Refresh** — mood-over-time chart (highlight one team, fixed y, season breaks), diverging bars, callout cards, records + methodology pages, mobile, one-command weekly refresh, README, optional Vercel deploy.

**Research flags:** Phase 4 (factor definitions, playoff sim era rules, model-vs-Vegas expectation) and Phase 5 (surplus-over-slot formula, perception-gap baseline) need research. Phases 1, 2, 3, 6 are standard patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified live; expectation-data strategy MEDIUM |
| Features | MEDIUM | Competitor sets checked; value judgments are synthesis |
| Architecture | MEDIUM-HIGH | Standard patterns; Elo constants from training knowledge |
| Pitfalls | MEDIUM | Data/leakage HIGH; momentum evidence MEDIUM; early win totals LOW |

### Gaps to Address
- Which factors earn weight is unknown until Phase 4 — near-zero weights are a valid outcome.
- Hand-entering 2021+ win totals (~192 numbers; covers.com/sportsoddshistory blocks automated fetch) — decide in Phase 4.
- No ground truth for playoff odds — cross-check a few seasons, disclose the approximation.
- Verify per-loader historical team codes (Phase 1); NaN audit 1999–2000, consider tuning from 2001–2002.
- Verify training-knowledge claims (538 Elo constants, Pythagorean exponent, Massey-Thaler, Baldwin/OTC chart).
- Pin nflreadpy and Observable Plot (pre-1.0). Use color chips not NFL logos on public deploy.

## Sources
**Primary (HIGH):** PyPI/npm metadata; nflreadpy docs + live probes; nflverse/nfldata (`win_totals.csv`, `draft_values.csv`, `games.csv`); nflreadr abbreviation docs; nflfastR NEWS/README; nflseedR divisions; create-vite templates.
**Secondary (MEDIUM):** nfelo, FPI, Neil Paine, Silver Bulletin, ESPN Misery Index, PFF; 538 mirrors/repo; streak/hot-hand studies; sportsoddshistory/covers.
**Tertiary (LOW):** 538 Elo constants (K=20, 1/3 regression, MOV formula, expansion seed ~1300); one-score regression; Pythagorean exponent; Massey-Thaler; Baldwin/OTC (training knowledge); nfeloapp win-total history (search results only).

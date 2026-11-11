# Requirements: Feel-Good Score

**Defined:** 2026-11-11
**Core Value:** A single, honest, momentum-weighted "feel-good score" per team that is backtested to predict future performance — so "you should feel better than you do" is actually true.

## v1 Requirements

### Data Foundation

- [x] **DATA-01**: Pipeline loads all games 1999→present (schedules, scores, spreads, starting QBs) from nflverse via nflreadpy and caches them locally
- [x] **DATA-02**: Every team maps to a stable franchise ID so relocated teams (OAK→LV, SD→LAC, STL→LA) and renames (Washington) have one unbroken history
- [x] **DATA-03**: A season-config table encodes era rules (31 teams 1999–2001, HOU from 2002, 16→17 games in 2021, 12→14 playoff teams in 2020, divisions)
- [x] **DATA-04**: Ties (0.5), neutral sites, and cancelled games (BUF–CIN 2022) are handled without crashes or miscounts
- [x] **DATA-05**: Per-team-game play-by-play aggregates (EPA/play, garbage-time filtered; QB EPA/dropback + success rate) are computed for 1999→present, with 1999–2000 flagged low-confidence
- [x] **DATA-06**: Draft picks and a draft-value chart are loaded for every season
- [x] **DATA-07**: Data checks assert franchise counts per season, games per team-season, and no unmatched team abbreviations

### Rating Model

- [x] **MODEL-01**: A base Elo rating (margin-of-victory, era-aware home-field advantage, offseason regression to mean) is computed chronologically for every team after every game
- [x] **MODEL-02**: A (season, week, franchise) snapshot grid holds every team's as-of state each week, including bye weeks and a week-0 preseason snapshot
- [x] **MODEL-03**: Factor: current-season record
- [x] **MODEL-04**: Factor: rolling last-16-games record across season boundaries
- [x] **MODEL-05**: Factor: efficiency trajectory (EWMA of opponent-adjusted EPA vs season-to-date level) as the "WAR improvement" proxy
- [x] **MODEL-06**: Factor: strength of win — margin of victory, as its own input
- [x] **MODEL-07**: Factor: opponent quality — opponent's pre-game rating, as its own input
- [x] **MODEL-08**: Factor: performance vs preseason expectation (model-derived expected wins; Vegas win totals override where available, with source tagged)
- [x] **MODEL-09**: Factor: current win/loss streak
- [x] **MODEL-10**: Factor: close-game luck (one-score game results)
- [x] **MODEL-11**: Factor: QB play trend for the current starting QB
- [x] **MODEL-12**: Factor: playoff-odds trend
- [x] **MODEL-13**: A Monte Carlo season simulator with era rules and simplified tiebreakers produces weekly playoff odds and preseason expected wins, cached per (season, week, model version)
- [x] **MODEL-14**: The feel-good score is a strictly additive sum of weight × per-snapshot z-score, with each factor's contribution stored
- [x] **MODEL-15**: Single score — the backtest decides every weight and sign (streak and luck included, even if negative or ~0)
- [x] **MODEL-16**: Between seasons, the score reacts to the draft via draft value *above* what the team's original slot would yield (capped), so tanking is never rewarded

### Backtest & Tuning

- [x] **BACK-01**: The primary target (opponent- and HFA-adjusted average margin over the next 4–8 games) is documented in the README before any tuning
- [x] **BACK-02**: A walk-forward-by-season backtest compares the score against baselines: plain Elo, season win %, last-16 win %, point differential, and the Vegas spread as a ceiling
- [x] **BACK-03**: A leakage test (appending fake future games changes no past score) passes
- [x] **BACK-04**: Weights are fit with Ridge on standardized inputs, rounded by a human, and committed to `weights.yaml`; the weekly refresh never refits
- [x] **BACK-05**: 2022–2025 is held out and evaluated once after weights are frozen, with season-level bootstrap confidence intervals and the fitted sign of every factor reported
- [x] **BACK-06**: The final score beats the plain-Elo baseline out of sample

### Insights

- [x] **INSIGHT-01**: Every score maps to a playful mood label from historical percentile bands, with hysteresis so labels don't flicker week to week
- [x] **INSIGHT-02**: Perception-gap callouts flag teams whose record-implied rank differs sharply from their score rank ("8-2 but you should feel worried")
- [x] **INSIGHT-03**: Misery and joy streaks are measured in calendar days ("miserable for 600 straight days")
- [ ] **INSIGHT-04**: Historical extremes (saddest and happiest fanbases ever) are computed and the top 10 of each are manually sanity-checked
- [x] **INSIGHT-05**: Each team gets an auto-generated plain-English one-liner explaining its biggest score drivers
- [x] **INSIGHT-06**: Week-over-week biggest movers are computed

### Site

- [x] **SITE-01**: User sees a league-wide mood board of all 32 teams ranked by feel-good score, with record, mood label, and weekly change
- [x] **SITE-02**: User can click a team for a deep-dive: score, mood label, one-liner, factor breakdown (diverging bars summing to the score), and recent games
- [x] **SITE-03**: User can view a mood-over-time chart of every team from 1999→present, with one team highlighted, a fixed y-axis, and breaks at season boundaries
- [x] **SITE-04**: User can scrub the mood board to any season/week since 1999
- [x] **SITE-05**: User sees a biggest-movers strip for the current week
- [x] **SITE-06**: User can browse a records page of historical extremes and longest misery/joy streaks
- [x] **SITE-07**: User can read a methodology page explaining the factors, fitted weights and signs, and a backtest chart vs baselines
- [x] **SITE-08**: User can pin "my team" and see it highlighted across views (remembered locally)
- [x] **SITE-09**: Shareable callouts are surfaced on the board and team pages
- [x] **SITE-10**: Site works on mobile and shows a "last updated" stamp; every view has a hash deep link

### Pipeline

- [x] **PIPE-01**: One command refreshes data and regenerates all JSON after each week's games (full replay), tested on a partial week
- [x] **PIPE-02**: The JSON contract (meta, latest, snapshots, teams, history, callouts) is the only interface between the pipeline and the site
- [x] **PIPE-03**: The site runs locally with a single command, and the README documents what the idea is, how to run it, and where it stands

## v2 Requirements

### Model

- **MODEL-V2-01**: "Good loss" / deserved-to-win luck modeling
- **MODEL-V2-02**: Offseason reaction to free agency
- **MODEL-V2-03**: Hand-entered 2021+ Vegas win totals (~192 values) to override the model-derived expectation

### Site

- **SITE-V2-01**: Auto-generated share images (OG cards) for callouts
- **SITE-V2-02**: EPA scatter / additional exploratory charts
- **SITE-V2-03**: Deploy to Vercel as a static site

## Out of Scope

| Feature | Reason |
|---------|--------|
| Fan sentiment inputs (Reddit, Trends, polls) | The point is to correct fan perception, not mirror it |
| Tanking "hope" bump | Never reward tanking |
| User-tunable weight sliders | Fixed, backtested weights are the product |
| Betting picks / against-the-spread recommendations | Not a gambling tool |
| Live / in-game updates | Weekly refresh is enough |
| Accounts / logins | Local "my team" pin is sufficient |
| Paid data (PFF WAR, etc.) | Free data only |
| Decimal-precision scores in the UI | False precision |
| NFL logos on a public deploy | Licensing; use team color chips |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Complete |
| DATA-02 | Phase 1 | Complete |
| DATA-03 | Phase 1 | Complete |
| DATA-04 | Phase 1 | Complete |
| DATA-05 | Phase 5 | Complete |
| DATA-06 | Phase 7 | Complete |
| DATA-07 | Phase 1 | Complete |
| MODEL-01 | Phase 1 | Complete |
| MODEL-02 | Phase 1 | Complete |
| MODEL-03 | Phase 3 | Complete |
| MODEL-04 | Phase 3 | Complete |
| MODEL-05 | Phase 5 | Complete |
| MODEL-06 | Phase 4 | Complete |
| MODEL-07 | Phase 4 | Complete |
| MODEL-08 | Phase 5 | Complete |
| MODEL-09 | Phase 4 | Complete |
| MODEL-10 | Phase 4 | Complete |
| MODEL-11 | Phase 5 | Complete |
| MODEL-12 | Phase 5 | Complete |
| MODEL-13 | Phase 5 | Complete |
| MODEL-14 | Phase 3 | Complete |
| MODEL-15 | Phase 6 | Complete |
| MODEL-16 | Phase 7 | Complete |
| BACK-01 | Phase 3 | Complete |
| BACK-02 | Phase 3 | Complete |
| BACK-03 | Phase 3 | Complete |
| BACK-04 | Phase 6 | Complete |
| BACK-05 | Phase 6 | Complete |
| BACK-06 | Phase 6 | Complete (PASS by prereg rule: +0.0039 Spearman N=8, CI incl. 0; verdict "slight") |
| INSIGHT-01 | Phase 2 | Complete |
| INSIGHT-02 | Phase 8 | Complete |
| INSIGHT-03 | Phase 8 | Complete |
| INSIGHT-04 | Phase 8 | Pending (computed + RECORDS_CHECK.md generated; manual top-10 sanity check not yet signed off) |
| INSIGHT-05 | Phase 4 | Complete |
| INSIGHT-06 | Phase 8 | Complete |
| SITE-01 | Phase 2 | Complete |
| SITE-02 | Phase 4 | Complete |
| SITE-03 | Phase 3 | Complete |
| SITE-04 | Phase 2 | Complete |
| SITE-05 | Phase 8 | Complete |
| SITE-06 | Phase 8 | Complete |
| SITE-07 | Phase 6 | Complete |
| SITE-08 | Phase 8 | Complete |
| SITE-09 | Phase 8 | Complete |
| SITE-10 | Phase 2 | Complete |
| PIPE-01 | Phase 2 | Complete |
| PIPE-02 | Phase 2 | Complete |
| PIPE-03 | Phase 2 | Complete |

**Coverage:**
- v1 requirements: 48 total
- Mapped to phases: 48
- Unmapped: 0 ✓

---
*Requirements defined: 2026-11-11*
*Last updated: 2026-11-11 after roadmap creation*

# Roadmap: Feel-Good Score

## Overview

The project is built as vertical slices. Each one adds something you can see and run. First, a clean 1999-to-present data foundation and a plain Elo rating. Next, an Elo-only mood board and a weekly refresh, so the whole pipeline-to-site loop works early. Then comes the backtest harness, which must exist before any momentum factor. After that, the model gets deeper one factor at a time, each factor earning its place by backtest: schedule-derived factors first, then efficiency/QB trajectory and the season simulator. The weights are then frozen and checked against a held-out set of seasons. Once the in-season model is validated, the score starts reacting to the draft in the offseason. The final slice adds the shareable insights: perception-gap callouts, misery streaks, historical records, movers, and the "my team" pin.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Data Foundation & Elo Core** - Clean 1999→present game data with stable franchise IDs, era rules, and a chronological Elo snapshot grid
- [ ] **Phase 2: Elo Mood Board** - JSON contract, one-command weekly refresh, and a runnable site showing all 32 teams ranked with mood labels
- [ ] **Phase 3: Backtest Harness & Additive Score** - Documented target, baselines, leakage test, additive combiner with record factors, and the mood-over-time chart
- [ ] **Phase 4: Game-Result Factors & Team Deep-Dive** - Margin, opponent quality, streak, and close-game luck factors plus a team page with diverging-bar breakdown and one-liner
- [ ] **Phase 5: Efficiency, QB Trend & Season Simulator** - PBP-based efficiency and QB trajectory factors, Monte Carlo simulator, expectations and playoff-odds factors
- [ ] **Phase 6: Weight Freeze & Methodology** - Ridge-fit, human-rounded weights, one-time 2022–2025 holdout, beats plain Elo, methodology page
- [ ] **Phase 7: Draft-Aware Offseason** - Between seasons the score reacts to draft surplus over slot expectation, without rewarding tanking
- [ ] **Phase 8: Callouts, Records & My Team** - Perception-gap callouts, calendar-day misery/joy streaks, historical extremes, movers strip, records page, "my team" pin

## Phase Details

### Phase 1: Data Foundation & Elo Core
**Goal**: Every NFL game since 1999 is loaded, cleaned, and replayed chronologically into a trustworthy Elo rating for every franchise at every week
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-07, MODEL-01, MODEL-02
**Success Criteria** (what must be TRUE):
  1. Running the pipeline pulls every game from 1999 to the current 2026 week via nflreadpy, caches it locally, and a re-run reads from the cache.
  2. The data checks pass: 31 franchises for 1999–2001 and 32 after that, the right games per team-season (16, or 17 from 2021), no unmatched team abbreviations, and LV/LAC/LA/WAS each have one unbroken history.
  3. Ties count as 0.5, neutral-site games get no home-field advantage, and the cancelled BUF–CIN 2022 game is skipped without crashing or miscounting.
  4. A CLI command prints the Elo ranking of all teams as of any (season, week), including bye weeks and week 0. The current 2026 ranking looks plausible.
**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md — Walking skeleton: uv project, cached ingest, franchise map, 538 Elo, snapshot grid, `fgs build`/`fgs elo`
- [ ] 01-02-PLAN.md — Era rules in season_config + `fgs check` data checks (counts, games/team, codes, continuity, divisions, zero-sum)
- [ ] 01-03-PLAN.md — Snapshot grid semantics tests, honest as-of `fgs elo` (latest week, beyond-latest error, data-through), owner plausibility check

### Phase 2: Elo Mood Board
**Goal**: Users can open a local site and see how every fanbase should feel right now (Elo-only for now), refreshed by a single command after each week
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: PIPE-01, PIPE-02, PIPE-03, SITE-01, SITE-04, SITE-10, INSIGHT-01
**Success Criteria** (what must be TRUE):
  1. User opens the home page and sees all 32 teams ranked by score, each with its record, a playful mood label, and its change from last week.
  2. User can scrub the board to any season/week since 1999 and get a URL hash that reopens the same view.
  3. Mood labels come from historical percentile bands and don't flicker for teams near a band boundary across consecutive weeks.
  4. One command refreshes the data and regenerates all JSON (meta, latest, snapshots, teams, history, callouts). Running it on a partially completed 2026 week works, and the site shows a "last updated" stamp.
  5. The site starts locally with one command, works on a phone-sized screen, and the README explains the idea, how to run it, and where it stands.
**Plans**: TBD
**UI hint**: yes

### Phase 3: Backtest Harness & Additive Score
**Goal**: The score becomes an additive, backtested composite that can be compared honestly against baselines, and users can watch every team's mood over time
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: BACK-01, BACK-02, BACK-03, MODEL-14, MODEL-03, MODEL-04, SITE-03
**Success Criteria** (what must be TRUE):
  1. The README states the primary backtest target (opponent- and HFA-adjusted average margin over the next 4–8 games), committed before any weight tuning.
  2. A single backtest command prints walk-forward-by-season metrics for plain Elo, season win %, last-16 win %, point differential, and the Vegas spread ceiling. Plain Elo lands in the expected Brier range (about 0.22–0.23).
  3. The leakage test passes: adding fake future games changes no past score.
  4. The score is now a sum of weight × z-score with each factor's stored contribution, and the current-season record and rolling last-16 factors (across season boundaries) show a measured backtest delta.
  5. User can view a mood-over-time chart of all teams from 1999 to now, with one team highlighted, a fixed y-axis, and breaks at season boundaries.
**Plans**: TBD
**UI hint**: yes

### Phase 4: Game-Result Factors & Team Deep-Dive
**Goal**: Users can click any team and understand exactly why its score is what it is, with schedule-derived factors added one at a time and each one backtested
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: MODEL-06, MODEL-07, MODEL-09, MODEL-10, SITE-02, INSIGHT-05
**Success Criteria** (what must be TRUE):
  1. Margin of victory, opponent pre-game rating, current streak, and close-game luck are separate factors, and each was added one at a time with its own backtest delta and fitted sign recorded.
  2. User can click a team and see its score, mood label, a plain-English one-liner naming its biggest drivers, and its recent games.
  3. The team page shows diverging factor bars that visibly sum to the displayed score.
**Plans**: TBD
**UI hint**: yes

### Phase 5: Efficiency, QB Trend & Season Simulator
**Goal**: The score captures real trajectory (efficiency and QB play) and expectations (preseason expected wins, playoff odds), so "better than your record says" is grounded in evidence
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: DATA-05, MODEL-05, MODEL-11, MODEL-13, MODEL-08, MODEL-12
**Success Criteria** (what must be TRUE):
  1. Per-team-game aggregates (garbage-time-filtered EPA/play, QB EPA/dropback and success rate) exist for 1999 to now, with 1999–2000 flagged low-confidence.
  2. The efficiency-trajectory factor (EWMA of opponent-adjusted EPA vs the season-to-date level) and the starting-QB trend factor each appear in the team breakdown with a recorded backtest delta.
  3. A Monte Carlo simulator using era rules gives weekly playoff odds and preseason expected wins for any (season, week), cached by model version. Model-derived expected wins correlate reasonably with the 2003–2020 Vegas win totals (target r of about 0.7–0.8).
  4. The vs-expectation factor tags each row's expectation source (model or Vegas), and the playoff-odds-trend factor is in the score with its fitted weight reported, even if it lands near 0.
**Plans**: TBD
**Research**: Needed. Factor definitions (EWMA window, opponent adjustment, QB-change handling), playoff simulator era rules and simplified tiebreakers, and model-vs-Vegas expectation validation.

### Phase 6: Weight Freeze & Methodology
**Goal**: The final in-season score is shown to predict future performance better than plain Elo, and users can see the evidence
**Mode:** mvp
**Depends on**: Phase 5
**Requirements**: BACK-04, BACK-05, BACK-06, MODEL-15, SITE-07
**Success Criteria** (what must be TRUE):
  1. `weights.yaml` holds Ridge-fit, human-rounded weights on standardized inputs. The backtest set every weight and sign, including streak and luck, and the weekly refresh reads the file without refitting.
  2. A one-time evaluation on the 2022–2025 holdout reports season-level bootstrap confidence intervals and every factor's fitted sign.
  3. The final score beats the plain-Elo baseline out of sample on the documented target.
  4. User can open a methodology page that explains each factor, shows the fitted weights and signs, and charts the backtest against the baselines.
**Plans**: TBD
**UI hint**: yes

### Phase 7: Draft-Aware Offseason
**Goal**: Between seasons the score keeps moving and reacts to how well each team drafted, without ever rewarding tanking
**Mode:** mvp
**Depends on**: Phase 6
**Requirements**: DATA-06, MODEL-16
**Success Criteria** (what must be TRUE):
  1. Draft picks and a draft-value chart are loaded for every season since 1999.
  2. The week-0 post-draft snapshot moves each team by draft value *above* what its original slot would yield, capped. The worst team does not move up just for holding pick #1.
  3. The mood-over-time chart and board show offseason movement instead of a flat line. The draft term's fitted weight is reported, and if it shows no signal it falls back to display-only text.
**Plans**: TBD
**Research**: Needed. Surplus-over-slot formula, choice of draft-value chart (flatter stuart/otc), cap size, and how to backtest across the offseason.

### Phase 8: Callouts, Records & My Team
**Goal**: Users find the shareable "aha" moments: teams whose record is lying, the longest misery, the saddest and happiest fanbases ever, and this week's biggest swings, all centered on their own team
**Mode:** mvp
**Depends on**: Phase 7
**Requirements**: INSIGHT-02, INSIGHT-03, INSIGHT-04, INSIGHT-06, SITE-05, SITE-06, SITE-08, SITE-09
**Success Criteria** (what must be TRUE):
  1. The board and team pages show perception-gap callouts (e.g. "8-2 but you should feel worried") for teams whose record-implied rank differs sharply from their score rank.
  2. User sees a biggest-movers strip for the current week on the board.
  3. User can browse a records page with the saddest and happiest fanbases ever and the longest misery/joy streaks in calendar days ("miserable for 600 straight days"). The top 10 of each list has been hand-checked for data bugs.
  4. User can pin "my team". The pin is remembered after reload and highlights that team on the board, the mood-over-time chart, and the records.
**Plans**: TBD
**UI hint**: yes
**Research**: Needed. Perception-gap baseline (record-implied rank, threshold, base-rate evidence line).

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Foundation & Elo Core | 0/3 | Not started | - |
| 2. Elo Mood Board | 0/TBD | Not started | - |
| 3. Backtest Harness & Additive Score | 0/TBD | Not started | - |
| 4. Game-Result Factors & Team Deep-Dive | 0/TBD | Not started | - |
| 5. Efficiency, QB Trend & Season Simulator | 0/TBD | Not started | - |
| 6. Weight Freeze & Methodology | 0/TBD | Not started | - |
| 7. Draft-Aware Offseason | 0/TBD | Not started | - |
| 8. Callouts, Records & My Team | 0/TBD | Not started | - |

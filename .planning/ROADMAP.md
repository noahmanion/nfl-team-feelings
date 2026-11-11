# Roadmap: Feel-Good Score

## Overview

The project is built as vertical slices. Each one adds something you can see and run. First, a clean 1999-to-present data foundation and a plain Elo rating. Next, an Elo-only mood board and a weekly refresh, so the whole pipeline-to-site loop works early. Then comes the backtest harness, which must exist before any momentum factor. After that, the model gets deeper one factor at a time, each factor earning its place by backtest: schedule-derived factors first, then efficiency/QB trajectory and the season simulator. The weights are then frozen and checked against a held-out set of seasons. Once the in-season model is validated, the score starts reacting to the draft in the offseason. The final slice adds the shareable insights: perception-gap callouts, misery streaks, historical records, movers, and the "my team" pin.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Data Foundation & Elo Core** - Clean 1999→present game data with stable franchise IDs, era rules, and a chronological Elo snapshot grid (completed 2026-11-11)
- [x] **Phase 2: Elo Mood Board** - JSON contract, one-command weekly refresh, and a runnable site showing all 32 teams ranked with mood labels (completed 2026-11-11)
- [x] **Phase 3: Backtest Harness & Additive Score** - Documented target, baselines, leakage test, additive combiner with record factors, and the mood-over-time chart (completed 2026-11-11)
- [x] **Phase 4: Game-Result Factors & Team Deep-Dive** - Margin, opponent quality, streak, and close-game luck factors plus a team page with diverging-bar breakdown and one-liner (completed 2026-11-11)
- [x] **Phase 5: Efficiency, QB Trend & Season Simulator** - PBP-based efficiency and QB trajectory factors, Monte Carlo simulator, expectations and playoff-odds factors (completed 2026-11-11)
- [x] **Phase 6: Weight Freeze & Methodology** - Ridge-fit, human-rounded weights, one-time 2022–2025 holdout, beats plain Elo, methodology page (completed 2026-11-11)
- [x] **Phase 7: Draft-Aware Offseason** - Between seasons the score reacts to draft surplus over slot expectation, without rewarding tanking (completed 2026-11-11)
- [x] **Phase 8: Callouts, Records & My Team** - Perception-gap callouts, calendar-day misery/joy streaks, historical extremes, movers strip, records page, "my team" pin (completed 2026-11-11)

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
**Wave 1**

- [x] 01-01-PLAN.md — Walking skeleton: uv project, cached ingest, franchise map, 538 Elo, snapshot grid, `fgs build`/`fgs elo`

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Era rules in season_config + `fgs check` data checks (counts, games/team, codes, continuity, divisions, zero-sum)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03-PLAN.md — Snapshot grid semantics tests, honest as-of `fgs elo` (latest week, beyond-latest error, data-through), owner plausibility check

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

**Plans**: 4 plans

Plans:
**Wave 1**

- [x] 02-01-PLAN.md — End-to-end slice: mood.py (percentile, bands, ±2 hysteresis) + export.py full JSON contract via `fgs export` + web/ scaffold rendering the latest board

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-02-PLAN.md — Scrubber (season select, week slider, Latest) + hash router deep links + bad-link notice
- [x] 02-03-PLAN.md — `fgs refresh` (check-then-write), partial-week + abort tests, regenerated JSON, README

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 02-04-PLAN.md — Loading/fatal/empty states, desktop column header + sticky scrubber, 320–375px polish

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

**Plans**: 4 plans

Plans:
**Wave 1**

- [x] 03-01-PLAN.md — README backtest target (committed first), as-of season_record/last16/pd_pg features, `fgs backtest` walk-forward baselines + backtest.json with sealed holdout
- [x] 03-04-PLAN.md — Mood-over-time chart: `#/history[/ABBR]` route, top nav, Observable Plot spaghetti + highlight + season breaks + band stripes

**Wave 2** *(blocked on 03-01)*

- [x] 03-02-PLAN.md — score.py additive engine (per-snapshot z, contribs), walk-forward ridge composites, `--propose-weights`, weights.yaml, BACKTEST_LOG.md

**Wave 3** *(blocked on 03-02)*

- [x] 03-03-PLAN.md — Composite on the board: frozen 1999–2021 percentile reference, leakage test, meta.factors + row contribs, regenerated site data, README

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

**Plans:** 4/4 plans complete

Plans:
**Wave 1**

- [x] 04-01-PLAN.md — Points attribution, blurbs, meta.baseline, games/{season}.json export (existing 3 factors)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 04-02-PLAN.md — Team deep-dive page: route, factor bars, recent games, sparkline, board-row links
- [x] 04-03-PLAN.md — Add mov then sow one at a time (backtest delta, sign, weights, log, regen)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 04-04-PLAN.md — Add streak then luck one at a time; final 7-factor export + README

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

**Plans**: 5 plans
**Research**: Done (05-RESEARCH.md). Factor definitions (EWMA window, opponent adjustment, QB-change handling), playoff simulator era rules and simplified tiebreakers, and model-vs-Vegas expectation validation.

Plans:
**Wave 1**

- [x] 05-01-PLAN.md — pbp ingest: slim per-season cache, team_game_epa aggregates, coverage check, build/refresh wiring (DATA-05)
- [x] 05-02-PLAN.md — Vectorized season simulator (era rules, tiebreaks, sigma=100, model_version cache) + win totals and source-tagged expectations (MODEL-13, MODEL-08)

**Wave 2**

- [x] 05-03-PLAN.md — epa_traj then qb_trend, one at a time: backtest delta, sign, weights, log, phrases, site data (MODEL-05, MODEL-11)

**Wave 3**

- [x] 05-04-PLAN.md — Simulator wired into derive/refresh/checks/leakage; vs_exp factor with three logged deltas (MODEL-13, MODEL-08)

**Wave 4**

- [x] 05-05-PLAN.md — po_trend factor + final interim 11 weights; playoff odds stat on team page; README + phase gate (MODEL-12)

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

**Plans**: 5 plans
**UI hint**: yes

Plans:
**Wave 1**

- [x] 06-01-PLAN.md — Commit PREREGISTRATION.md first (model, pass rule, CIs, verdict wording, vs_exp diagnostic) + pure paired bootstrap module

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 06-02-PLAN.md — `fgs freeze` (fold signs, Δ, walk-forward CIs) + refit guards; run it, commit frozen weights.yaml + FREEZE_RESULT.json

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 06-03-PLAN.md — Holdout evaluator + guarded `fgs holdout`, tested only on the 2018–2021 stand-in and mocks
- [x] 06-04-PLAN.md — methodology.json (holdout: null) + `#/methodology` page, nav link, dot-and-whisker charts

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 06-05-PLAN.md — ONE-TIME `fgs holdout` run, commit HOLDOUT_RESULT.md/.json, re-export, README verdict

### Phase 7: Draft-Aware Offseason

**Goal**: Between seasons the score keeps moving and reacts to how well each team drafted, without ever rewarding tanking
**Mode:** mvp
**Depends on**: Phase 6
**Requirements**: DATA-06, MODEL-16
**Success Criteria** (what must be TRUE):

  1. Draft picks and a draft-value chart are loaded for every season since 1999.
  2. The week-0 post-draft snapshot moves each team by draft value *above* what its original slot would yield, capped. The worst team does not move up just for holding pick #1.
  3. The mood-over-time chart and board show offseason movement instead of a flat line. The draft term's fitted weight is reported, and if it shows no signal it falls back to display-only text.

**Plans**: 4 plans

Plans:
**Wave 1**

- [x] 07-01-PLAN.md — Draft data (picks + stuart chart) and surplus-over-original-slot engine, `fgs draft`, DATA-06 checks, derived['draft']
- [x] 07-02-PLAN.md — Web: dashed offseason connector, week-0 "vs end of last season", draft line on team page (contract-first)

**Wave 2** *(blocked on 07-01)*

- [x] 07-03-PLAN.md — Training-only draft walk-forward + gate on the frozen composite (`fgs backtest --draft`), offseason.draft in weights.yaml, scoring path (weight 0 = display only)

**Wave 3** *(blocked on 07-02, 07-03)*

- [x] 07-04-PLAN.md — Cross-season week-0 deltas, draft fields/text/labels in export, methodology draft note, regenerate data, README

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

**Plans**: 5 plans

Plans:
**Wave 1**

- [x] 08-01-PLAN.md — Pipeline: perception-gap callouts + movers (insights.py), frozen 1999–2021 evidence (`fgs evidence` → callout_evidence.json), callouts in the JSON contract

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 08-02-PLAN.md — Web: callout cards + Copy link and biggest-movers strip on the board (latest and scrubbed weeks), team callouts on the team page
- [x] 08-03-PLAN.md — Pipeline: snapshot dates, calendar-day misery/joy streaks, team-season extremes, records.json, streak callouts, RECORDS_CHECK.md

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 08-04-PLAN.md — Web: #/records page + "Records" nav, team-page active streak line

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 08-05-PLAN.md — Web: "my team" pin (localStorage) highlighted on board, chart, records and callouts

**UI hint**: yes
**Research**: Needed. Perception-gap baseline (record-implied rank, threshold, base-rate evidence line).

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Foundation & Elo Core | 3/3 | Complete    | 2026-11-11 |
| 2. Elo Mood Board | 4/4 | Complete    | 2026-11-11 |
| 3. Backtest Harness & Additive Score | 4/4 | Complete    | 2026-11-11 |
| 4. Game-Result Factors & Team Deep-Dive | 4/4 | Complete    | 2026-11-11 |
| 5. Efficiency, QB Trend & Season Simulator | 5/5 | Complete    | 2026-11-11 |
| 6. Weight Freeze & Methodology | 5/5 | Complete    | 2026-11-11 |
| 7. Draft-Aware Offseason | 4/4 | Complete    | 2026-11-11 |
| 8. Callouts, Records & My Team | 5/5 | Complete   | 2026-11-11 |

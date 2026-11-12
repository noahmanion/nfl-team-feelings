# Feel-Good Score

## What This Is

A visualization of how NFL fans *should* be feeling about their team — a momentum-focused, Elo-like rating that blends current record, the last 16 games (across season boundaries), efficiency trends, strength of wins, opponent quality, expectations, and more. It exists as a corrective: fans routinely think their team is worse (or better) than the evidence says, and this score shows them the truth, with a playful mood label on top of serious charts.

## Core Value

A single, honest, momentum-weighted "feel-good score" per team that is backtested to predict future performance — so "you should feel better than you do" is actually true.

## Current Milestone: v2.0 Public Site

**Goal:** Take the site public. Deploy it, restyle it as FiveThirtyEight-inspired data journalism with team logos, make callouts shareable, add exploratory EPA charts, and close the v1 data loose ends. The frozen v1 model stays untouched, and the v2 model is pre-registered against a fresh 2026–27 holdout.

**Target features:**
- Deploy to Vercel as a static site (from github.com/noahmanion/nfl-team-feelings)
- Editorial redesign inspired by FiveThirtyEight (typography, chart styling, clean layout), without copying its branding
- Team logos from a free source (nflverse `load_teams` logo URLs), with a graceful fallback
- Auto-generated share images (OG cards) for callouts and team pages
- EPA scatter and other exploratory charts
- Loose ends: verify the 18 draft-forfeit entries entered from memory; hand-entered 2021+ Vegas win totals as display-only data
- v2 model pre-registration (good-loss luck, free agency, win totals into the score), holdout 2026–2027, written up front with no model changes this milestone

## Requirements

### Validated

- ✓ Per-team feel-good score after every game, 1999→present (additive 11-factor composite, percentile 0–100, mood bands) — v1.0
- ✓ Inputs: Elo, season record, last-16 (cross-season), margin, opponent-quality of results, streak, close-game luck, efficiency trend (EPA), QB form, vs preseason expectation, playoff-odds trend — v1.0 (weights + signs set by backtest; momentum-type inputs ≈0/negative)
- ✓ Monte Carlo season simulator (playoff odds, preseason expected wins) — v1.0
- ✓ Offseason draft reaction (surplus over original slot, anti-tanking) — v1.0, display-only (gate found no predictive signal)
- ✓ Fixed, backtested weights (Ridge, frozen) with pre-registered one-time 2022–25 holdout — v1.0 (verdict: "Yes, slightly", within noise)
- ✓ Mood board, team deep-dive with factor bars + blurbs, mood-over-time chart, week scrubber, records page, methodology page, perception-gap callouts, movers, calendar-day streaks, my-team pin — v1.0
- ✓ One-command weekly refresh → static JSON → static site — v1.0
- ✓ v2 model pre-registered before any v2 code (`pipeline/PREREGISTRATION_V2.md` + closed pre-data errata in `PREREGISTRATION_V2_DEVIATIONS.md`): holdout = games kicking off after the v2 freeze commit, 2027 primary (2028 if the freeze misses 2027 Week 1); dev data ≤2025; free agency DROPPED (no signing dates in `load_contracts`) — Validated in Phase 9: v2 Pre-registration (INTEG-02, INTEG-03)
- ✓ Site is public at https://nfl-team-feelings.vercel.app/. Vercel builds it from `web/` on Node 24.x, and a push to main redeploys it. The ignored-build step skips commits that don't touch `web/`. Pages carry a "data through" stamp, site-wide og/twitter share tags and a "not affiliated with the NFL" footer. Validated in Phase 10: Deploy (DEPLOY-01, DEPLOY-02, DEPLOY-03)

### Active

(Defined in REQUIREMENTS.md for v2.0.)

### Out of Scope

- Fan sentiment inputs (Reddit, Google Trends, polls) — the whole point is to correct fan perception, not mirror it
- "Good loss" / deserved-to-win luck modeling — deferred to v2
- Tanking "hope" bump for bad teams with high draft picks — explicitly don't reward tanking
- Free-agency reaction in offseason — deferred to v2 (data is messy)
- Live/in-game updates — weekly refresh is enough
- User-tunable weight sliders — fixed, backtested weights instead
- Paid data (PFF WAR etc.) — free data only

## Context

- **v1.0 shipped 2026-11-11:** 8 phases, ~30 plans; 584 pipeline tests + 149 web tests. Holdout 2022–25: composite ≈ Elo (+0.004 Spearman, CI includes 0); Vegas still best on single games. The product's value is explanation (record vs evidence), backed by callout base rates (worried teams −3.5 pts/game vs record peers).

- Inspiration: fans perceiving their team as worse than it really is. The score is a reality check grounded in predictive evidence.
- Think "Elo, but momentum": a slow strength term plus faster recent-form/trajectory terms.
- Data: nflverse (via nflreadpy) — schedules, play-by-play with EPA, draft picks back to 1999. Preseason win totals and playoff odds need a source (may need to compute playoff odds via simulation if not available historically).
- Lives in an idea-graveyard repo of casual experiments: keep it light, favor prototype over polish.
- Current date: November 2026 (2026 season in progress).

## Constraints

- **Stack**: Python (nflreadpy/pandas) to compute scores → static JSON; lightweight static frontend for the viz — chosen by Claude, user deferred
- **Data**: free sources only — nflverse primary
- **Hosting**: Vercel static site at https://nfl-team-feelings.vercel.app/ (project nfl-team-feelings, root web, Node 24.x, ignored-build step scoped to web/); repo at github.com/noahmanion/nfl-team-feelings
- **Scope**: self-contained within `feel-good-scorew/`; no shared deps with other repo projects
- **Process**: light — no heavy CI/test suites beyond backtest validation of the model

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| EPA/play trend as "WAR improvement" proxy | Free, team-level, predictive; PFF WAR is paywalled | ✓ Good |
| Margin and opponent quality as separate inputs | User wants each weighted independently | ✓ Good |
| Expectations measured vs preseason (Vegas win totals) | A 6-4 team picked to go 4-13 should feel better than one picked to win it all | ✓ Good |
| Backtest target = future performance, not sentiment | Score is a corrective to fan perception; must be predictively true | ✓ Good |
| Full history 1999→present | Enables historical extremes ("saddest fanbase ever") | ✓ Good |
| Offseason reacts to draft (v1); FA deferred | Draft value is cleanly available; FA value is messy | ✓ Good |
| No tanking reward | Don't encourage tanking | ✓ Good |
| v2 holdout by kickoff time after the freeze commit, 2027 primary | 2026 weeks 1–10 were already watched; season-label holdouts would leak | — Pending (eval ~Feb 2028) |
| Free agency dropped from v2 | `load_contracts` has no signing date (year-level only), current-team only, UFA coverage complete only from 2012 | ✓ Good |
| Pre-registration fixes go to closed errata, never the prereg file | The prereg must stay at one commit; errata route is in its section 1.3 | ✓ Good |
| Python pipeline → static JSON → static frontend | Simple, weekly cadence, free hosting | ✓ Good |
| Deploy via Vercel Git integration, root web, Node 24.x, ignore step diffs web/ against last deployed SHA | Zero-config static hosting; pipeline/docs-only commits don't rebuild; Standard deployment protection keeps the production domain public | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-11-11, after Phase 10 (deploy)*

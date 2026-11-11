# Feel-Good Score

## What This Is

A visualization of how NFL fans *should* be feeling about their team — a momentum-focused, Elo-like rating that blends current record, the last 16 games (across season boundaries), efficiency trends, strength of wins, opponent quality, expectations, and more. It exists as a corrective: fans routinely think their team is worse (or better) than the evidence says, and this score shows them the truth, with a playful mood label on top of serious charts.

## Core Value

A single, honest, momentum-weighted "feel-good score" per team that is backtested to predict future performance — so "you should feel better than you do" is actually true.

## Requirements

### Validated

(None yet — ship to validate)

### Active

**Scoring model**
- [ ] Compute a per-team feel-good score after every game, for every season nflverse covers (1999→present)
- [ ] Inputs: current-season record; rolling last-16-games record regardless of season boundary
- [ ] Input: efficiency trend (EPA/play trend from nflverse play-by-play) as the free stand-in for "WAR improvement"
- [ ] Input: strength of win — margin of victory (separate from opponent quality)
- [ ] Input: opponent quality — strength of the opponent beaten/lost to (separate input, own weight)
- [ ] Input: performance vs preseason expectations (e.g. Vegas preseason win totals)
- [ ] Input: playoff odds trend
- [ ] Input: current win/loss streak
- [ ] Input: close-game luck (nail-biter wins/heartbreak losses)
- [ ] Input: QB play trend
- [ ] Offseason: score reacts to the draft (draft capital via draft-value charts) instead of freezing
- [ ] Weights are fixed and opinionated, but tuned via backtest against future performance (e.g. next-N-games win %)
- [ ] Per-team breakdown explaining which factors drive the score

**Visualization**
- [ ] League-wide mood board: all 32 teams ranked by feel-good score (home page)
- [ ] Team deep-dive on click: score, mood label, factor breakdown, history
- [ ] Mood-over-time chart: every team's score week by week, across seasons
- [ ] Playful mood labels/copy (e.g. "Planning the parade", "Refreshing draft mocks") over clean, serious charts
- [ ] Shareable "aha" moments surfaced: e.g. "8-2 but you should feel worried", "miserable for 600 straight days", saddest-fanbase-ever historical extremes

**Pipeline**
- [ ] Weekly refresh: a script run after each week's games regenerates scores as static JSON

### Out of Scope

- Fan sentiment inputs (Reddit, Google Trends, polls) — the whole point is to correct fan perception, not mirror it
- "Good loss" / deserved-to-win luck modeling — deferred to v2
- Tanking "hope" bump for bad teams with high draft picks — explicitly don't reward tanking
- Free-agency reaction in offseason — deferred to v2 (data is messy)
- Live/in-game updates — weekly refresh is enough
- User-tunable weight sliders — fixed, backtested weights instead
- Paid data (PFF WAR etc.) — free data only

## Context

- Inspiration: fans perceiving their team as worse than it really is. The score is a reality check grounded in predictive evidence.
- Think "Elo, but momentum": a slow strength term plus faster recent-form/trajectory terms.
- Data: nflverse (via nflreadpy) — schedules, play-by-play with EPA, draft picks back to 1999. Preseason win totals and playoff odds need a source (may need to compute playoff odds via simulation if not available historically).
- Lives in an idea-graveyard repo of casual experiments: keep it light, favor prototype over polish.
- Current date: November 2026 (2026 season in progress).

## Constraints

- **Stack**: Python (nflreadpy/pandas) to compute scores → static JSON; lightweight static frontend for the viz — chosen by Claude, user deferred
- **Data**: free sources only — nflverse primary
- **Hosting**: local first; may deploy to Vercel as a static site later
- **Scope**: self-contained within `feel-good-scorew/`; no shared deps with other repo projects
- **Process**: light — no heavy CI/test suites beyond backtest validation of the model

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| EPA/play trend as "WAR improvement" proxy | Free, team-level, predictive; PFF WAR is paywalled | — Pending |
| Margin and opponent quality as separate inputs | User wants each weighted independently | — Pending |
| Expectations measured vs preseason (Vegas win totals) | A 6-4 team picked to go 4-13 should feel better than one picked to win it all | — Pending |
| Backtest target = future performance, not sentiment | Score is a corrective to fan perception; must be predictively true | — Pending |
| Full history 1999→present | Enables historical extremes ("saddest fanbase ever") | — Pending |
| Offseason reacts to draft (v1); FA deferred | Draft value is cleanly available; FA value is messy | — Pending |
| No tanking reward | Don't encourage tanking | — Pending |
| Python pipeline → static JSON → static frontend | Simple, weekly cadence, free hosting | — Pending |

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
*Last updated: 2026-11-11 after initialization*

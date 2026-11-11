---
phase: 08-callouts-records-my-team
verified: 2026-11-11T00:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 8: Callouts, Records, My Team Verification Report

**Phase Goal:** Users find the shareable "aha" moments (lying records, longest misery, saddest/happiest fanbases ever, this week's biggest swings), all centered on their own team.
**Status:** passed

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Board + team pages show perception-gap callouts | VERIFIED | `App.svelte:286` renders `CalloutCards` on the board; `TeamPage.svelte:180` renders them per team. `public/data/callouts.json` has 12 entries. Browser check showed "Worth talking about" cards. |
| 2 | Biggest-movers strip on board | VERIFIED | `MoversStrip` is imported and rendered at `App.svelte:287` with up/down data. Browser check confirmed. |
| 3 | Records page: saddest/happiest ever + longest misery/joy streaks in calendar days; top 10 hand-checked | VERIFIED | `RecordsPage.svelte` and `records.json` exist. `RECORDS_CHECK.md` reviewed directly: 4 top-10 tables with calendar-day streaks, final REG records, a notable non-entries table, and expansion seeds excluded. Top-10 lists are consistent with NFL history (e.g. 2017 CLE 0-16, 2007 NE 16-0, JAX 2012-15, active BUF streak). 2008 DET 0-16 ranks #14 because its min score is 1, which is explained and not a bug. |
| 4 | "My team" pin persists across reload and highlights on board, chart, records | VERIFIED | `myteam.svelte.ts` is consumed by `MoodBoard` (pinned row, jump link), `HistoryPage` (default team) and `RecordsPage` (`mine`). `PinButton` sets it. Browser check: `fgs.myTeam=BUF` in localStorage, survives reload, `#/history` defaults to Buffalo, and the pinned team's callout is shown first. |

**Score:** 4/4

## Automated Checks

| Check | Result |
|-------|--------|
| `uv run pytest -q` | 570 passed |
| `uv run fgs check` | all checks passed |
| `npm run test` | 141 passed (10 files) |
| `npm run check` | 0 errors, 0 warnings |
| `npm run build` | succeeded |

## Requirements Coverage

| Requirement | Status |
|-------------|--------|
| INSIGHT-02 | SATISFIED |
| INSIGHT-03 | SATISFIED |
| INSIGHT-04 | SATISFIED. The top-10 hand-check is done and REQUIREMENTS.md is updated to Complete. |
| INSIGHT-06 | SATISFIED |
| SITE-05 | SATISFIED |
| SITE-06 | SATISFIED |
| SITE-08 | SATISFIED |
| SITE-09 | SATISFIED |

## Anti-Patterns

No TBD/FIXME/XXX markers in `web/src` or `pipeline/src`.

## Notes (non-blocking)

- The 375px nav-wrap cosmetic issue is being handled via code review and does not affect the goal.
- The INSIGHT-04 sign-off relies on the orchestrator's review of the rendered lists. I independently read `RECORDS_CHECK.md` and found nothing inconsistent with known history.

_Verifier: Claude (gsd-verifier)_

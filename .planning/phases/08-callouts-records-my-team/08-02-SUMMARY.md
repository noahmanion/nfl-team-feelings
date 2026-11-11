---
phase: 08-callouts-records-my-team
plan: 02
subsystem: web
tags: [svelte, callouts, movers, clipboard, share]
requires:
  - phase: 08-01
    provides: callouts.json + snapshots/{season}.json `callouts` key (Callout contract)
provides:
  - Callout/CalloutType types, SeasonFile.callouts, loadCallouts()
  - lib/callouts.ts (forWeek, forTeam, cardCallouts, moverCallouts, orderCallouts, calloutHref)
  - lib/copyLink.ts (copyText 3-tier fallback, deepLink)
  - CalloutCard / CalloutCards / MoversStrip components
  - Board + TeamPage wiring
affects: [08-05 (pins my team via orderCallouts second arg)]
tech-stack:
  added: []
  patterns: [injectable env for browser APIs so node vitest needs no jsdom]
key-files:
  created:
    - web/src/lib/callouts.ts
    - web/src/lib/callouts.test.ts
    - web/src/lib/copyLink.ts
    - web/src/lib/copyLink.test.ts
    - web/src/components/CalloutCard.svelte
    - web/src/components/CalloutCards.svelte
    - web/src/components/MoversStrip.svelte
  modified:
    - web/src/lib/types.ts
    - web/src/lib/data.ts
    - web/src/App.svelte
    - web/src/components/TeamPage.svelte
key-decisions:
  - "Card headline uses --text-heading 20/600 (locked CONTEXT 'big headline' beats UI-SPEC rule 6 Body 16)"
  - "callouts.json load is non-fatal (catch -> []); callouts ride in the `shown` snapshot so they stay in sync with the dimmed board"
  - "Movers strip shows 'None this week' in an empty column when the other column has items"
requirements-completed: [SITE-05, SITE-09]
duration: ~5min
completed: 2026-11-11
---

# Phase 8 Plan 02: Callout cards, movers strip and Copy link Summary

**Board now shows "Worth talking about" callout cards (perception gap, later streaks) and a Risers/Fallers movers strip for latest and scrubbed weeks, team pages show their own callouts, and every card has a Copy link button that copies the stable `#/team/ABBR/season/week` link, falling back to execCommand and then to a readonly URL field.**

## Tasks

| # | Task | Commit |
|---|------|--------|
| 1 | Types, loadCallouts, callouts.ts, copyLink.ts + 17 vitest cases | 67f7646 |
| 2 | CalloutCard, CalloutCards, MoversStrip | a7d72dc |
| 3 | App (latest + scrubbed) and TeamPage wiring | 5223335 |

## Verification

- `npm run check`: 0 errors, 0 warnings
- `npx vitest run`: 108/108 (including sep.test.ts; TeamPage still has exactly 3 `<Sep />`)
- `npm run build`: green
- Data check: `snapshots/2008.json` week 10 has 6 card callouts + 3/3 movers, so `#/board/2008/10` will render them
- Browser check at 375px and 1280px is left to the orchestrator (dev server :5199)

## Deviations from Plan

- **TDD commit granularity:** Task 1 was tdd="true". Tests and implementation went in one `feat` commit instead of separate RED/GREEN commits, to keep this quick prototype light (per CLAUDE.md). All 17 tests pass.
- **MoversStrip:** if one column is empty while the other has items, it shows "None this week" so the two-column layout stays balanced. This is a small addition beyond the plan.

## Known Stubs

- `orderCallouts(..., null)` in App.svelte is intentionally null; plan 08-05 replaces it with the pinned team.

## Self-Check: PASSED

- All created files exist; commits 67f7646, a7d72dc, 5223335 present in `git log`.

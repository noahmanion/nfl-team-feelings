---
phase: 04-game-result-factors-team-deep-dive
plan: 02
subsystem: web
tags: [svelte, routing, team-page, factor-bars, vitest]
requires:
  - phase: 04-01
    provides: "Row.points/blurb, meta.baseline, games/{season}.json"
provides:
  - "#/team/ABBR[/season/week] route + teamHash"
  - "lib/team.ts: recentGames, barRows, findTeamRow, seasonSeries, signed"
  - "loadGames(meta, season) session cache"
  - "TeamPage, FactorBars, RecentGames, Sparkline components"
  - "Board rows and history summary link to the team page"
affects: [04-03, 04-04, 05]
tech-stack:
  added: []
  patterns:
    - "Factor-agnostic bars: driven entirely by meta.factors + row.points"
    - "Section-level failure for games files; page-level failure only for the season file"
key-files:
  created:
    - web/src/lib/team.ts
    - web/src/lib/team.test.ts
    - web/src/components/FactorBars.svelte
    - web/src/components/RecentGames.svelte
    - web/src/components/Sparkline.svelte
    - web/src/components/TeamPage.svelte
  modified:
    - web/src/lib/router.ts
    - web/src/lib/router.test.ts
    - web/src/lib/types.ts
    - web/src/lib/data.ts
    - web/src/components/TeamChip.svelte
    - web/src/components/MoodLabel.svelte
    - web/src/components/BoardRow.svelte
    - web/src/components/MoodBoard.svelte
    - web/src/components/HistoryPage.svelte
    - web/src/components/SiteHeader.svelte
    - web/src/App.svelte
decisions:
  - "Recent-game eligibility uses asof_week <= page week (same season) so the week-N page never shows a later result"
  - "History chart -> team link is a 'See {Team} →' link in the summary line (HistoryChart.svelte untouched)"
  - "A games-file failure only affects the Recent games section, with its own Try again"
  - "Team route whose season/week equals meta.latest is treated as the latest page (no 'Now' link)"
metrics:
  duration: "~12 min"
  completed: 2026-11-11
---

# Phase 4 Plan 02: Team Deep-Dive Page Summary

This plan adds the team deep-dive page at `#/team/ABBR[/season/week]`. It shows a header (24px chip, name and score in Display, mood in Heading, record, rank and delta), the blurb, and diverging CSS factor bars from "Average team {baseline}" that sum to "= {score}". It also lists the last 6 played games as of that week, crossing into last season when needed, and draws a season sparkline. Every board row and the history summary now link to the page.

## Tasks

| # | Task | Commits |
|---|------|---------|
| 1 | Team route, types, loadGames, pure lib/team.ts helpers (TDD) | a01f5d7 (RED test), d325402 (GREEN feat) |
| 2 | TeamPage, FactorBars, RecentGames, Sparkline (+ TeamChip 24, MoodLabel heading) | a85bee8 |
| 3 | App routing, BoardRow as `<a>`, MoodBoard season/latest, history link, header state | 7498e8f |

Verification: `npm test` (60 tests), `npm run check` (0 errors) and `npm run build` all pass. The dev server on :5199 serves the new modules.

## Notes for the browser check

- `#/team/XYZ` falls back to the board with the notice "We don’t know that team, so here’s the latest board." The existing bad-board notice keeps its original text. `notice` is now a string instead of a boolean.
- `#/team/BUF/1800/3` (bad season/week) does `replace(teamHash('BUF'))`.
- If the team has no row for that season/week (e.g. HOU before 2002), the page shows a "No {Team} data for {season}" panel with a link to the team's latest page.
- Historical board rows link to `#/team/ABBR/season/week`. Latest-board rows link to `#/team/ABBR`.
- The sparkline only shows weeks up to the page week, and is hidden when there are fewer than 2 points.

## Deviations from Plan

### Auto-fixed / minor adjustments

1. **[Rule 2 - UX] Scroll to top on team change.** Clicking a row low on the board used to keep the scroll position. TeamPage now calls `window.scrollTo(0, 0)` when `team` changes. Commit 7498e8f.
2. **[Rule 2 - Robustness] Games load failure is scoped to its section.** A missing `games/*.json` (for example while 04-03 regenerates data) shows a Try-again panel in Recent games only, and the header and bars still render. Commit a85bee8.
3. **Heading levels.** The team name is the `h2`, since the site header already owns the `h1`. "Score breakdown", "Recent games" and "This season" are `h3`s, still styled Heading 20, rather than the plan's `h2` for Recent games. This keeps the outline correct.
4. **History link.** Per the orchestrator note, the "See {Team} →" link goes on the HistoryPage summary line. HistoryChart.svelte and history.ts were not edited.
5. **[Rule 1] svelte-check narrowing error** in App's `{:else if}` chain (a redundant `status !== 'error'`) was removed before the Task 3 commit.

## Known Stubs

None. When `meta.baseline` is absent, FactorBars falls back to 50. That only covers older exports, since 04-01 always emits a baseline.

## TDD Gate Compliance

The RED commit `test(04-02)` a01f5d7 comes before the GREEN commit `feat(04-02)` d325402. No refactor commit was needed.

## Self-Check: PASSED

- All 6 created files exist on disk.
- Commits a01f5d7, d325402, a85bee8 and 7498e8f are present in `git log`.

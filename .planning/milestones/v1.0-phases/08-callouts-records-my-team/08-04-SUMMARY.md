---
phase: 08-callouts-records-my-team
plan: 04
subsystem: web
tags: [records, streaks, routing, svelte]
requires: [08-02, 08-03]
provides:
  - "#/records route + Records nav link"
  - "RecordsPage (saddest/happiest team-seasons, longest misery/joy streaks, expansion footnote)"
  - "records.ts helpers: formatDays, UTC-safe formatDate, dateRange, streakLine, seasonsSpan"
  - "loadRecords(meta) and RecordsFile types"
  - "Team page (latest) active streak line"
affects: [08-05]
tech-stack:
  added: []
  patterns: ["single-file loader cached by meta.generated_at, evicted on failure", "Svelte 5 snippets for repeated list sections"]
key-files:
  created:
    - web/src/lib/records.ts
    - web/src/lib/records.test.ts
    - web/src/components/RecordsPage.svelte
  modified:
    - web/src/lib/router.ts
    - web/src/lib/router.test.ts
    - web/src/lib/types.ts
    - web/src/lib/data.ts
    - web/src/components/SiteHeader.svelte
    - web/src/App.svelte
    - web/src/components/TeamPage.svelte
decisions:
  - "Kept the 'reserved' Route kind with an empty RESERVED list, because App's redirect effect still references it"
  - "Records page title is an h2 at display size and the four section headings are h3 at Heading 20, matching TeamPage's hierarchy under the site h1"
  - "Extreme rows show the score as the big number and add 'Season avg N' to the meta line, because all 10 saddest have score 0 and the average is what orders them"
  - "Extreme row stripes use the score's mood band. Streak stripes use mood-0 (misery) and mood-6 (joy)"
  - "Team-page streak line hides that team's misery/joy callout cards only while the line is showing"
metrics:
  duration: "~10 min"
  completed: 2026-11-11
  tasks: 2
  files: 10
---

# Phase 8 Plan 04: Records page and team streak line Summary

`#/records` is a real route, linked from the nav as "Board · Mood over time · Records · How it works". The page lists the 10 saddest and 10 happiest team-seasons and the 10 longest misery and joy streaks in calendar days, with a footnote about the excluded expansion seasons. On the latest view, team pages with an active streak show a line such as "Miserable for 758 straight days, since Oct 14, 2024".

## Tasks

| # | Task | Commit |
|---|------|--------|
| 1 (RED) | Failing tests for the records route and records helpers | 951b7ba |
| 1 (GREEN) | Route, RecordsFile types, loadRecords, records.ts helpers | b3b4819 |
| 2 | RecordsPage, nav link, App route, TeamPage streak line | 65409e9 |

## What was built

- **router.ts**: added the `{ kind: 'records' }` route and `recordsHash`. `#/records` is no longer reserved.
- **types.ts / data.ts**: added `RecordsFile` with its entry types, and `loadRecords(meta)`, which is cached per `generated_at` and evicted on failure.
- **records.ts**:
  - `formatDays` gives "1,231 days" or "1 day".
  - `formatDate` parses the date and formats it in UTC, so it shows the same date in every time zone. Tests pass under `TZ=America/Los_Angeles` and `Pacific/Kiritimati`.
  - `dateRange` gives "… – now" for streaks that are still going.
  - `streakLine` gives "Miserable for N straight days" or "Buying the jersey for N straight days".
  - `seasonsSpan` gives "2005–2009", or "2024" for a single season.
- **RecordsPage.svelte**:
  - Uses a 680px reading column with board-style surface rows (1px border, radius 8, 8px gap, mood stripe).
  - Each row shows the rank, TeamChip with the name and season (or season span for streaks), the big number, and a muted meta line separated with `<Sep />`. A "Still going" accent Badge marks active streaks.
  - Rows link to the team page at the extreme's week, at the streak's end week, or to the latest page if the streak is still active.
  - If loading fails, it shows a StatusPanel with "Try again".
- **TeamPage.svelte**: on the latest view only, loads records without failing the page if they don't load, and shows the streak line under the header. While the line is showing, it removes that team's misery/joy callout cards. The `<Sep />` count is still 3.

## Verification

- `npm run check`: 0 errors and 0 warnings.
- `npx vitest run`: 119 passed.
- `npm run build`: OK.
- Acceptance greps all met.

## Deviations from Plan

**1. [Rule 2 - UX clarity] Added "Season avg N" to the extreme rows' meta line.** All 10 saddest entries have a score of 0, so without the REG average the order looks arbitrary. The average is an integer, so "integers only" still holds.

**2. [Minor] Heading levels.** The page title is an h2 and the section headings are h3 at Heading-20 size. The plan asked for an h1-level title with h2 sections, but the site header already owns the h1. This follows TeamPage's h2/h3 structure.

**3. [Minor] The footnote also explains the ranking rule and the streak thresholds (under 20 / 80 or higher).** The expansion sentence is word-for-word what the plan specified.

## Known Stubs

None.

## TDD Gate Compliance

RED (`test(08-04)` 951b7ba) is followed by GREEN (`feat(08-04)` b3b4819). No refactor was needed.

## Self-Check: PASSED

All created files exist, and commits 951b7ba, b3b4819 and 65409e9 are present in git log.

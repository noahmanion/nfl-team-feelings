---
phase: 02-elo-mood-board
plan: 02
subsystem: web
tags: [hash-router, svelte5-runes, scrubber, deep-links]
requires:
  - web/src/lib/{types,data,format}.ts (02-01)
  - web/public/data/snapshots/{season}.json (02-01)
provides:
  - web/src/lib/router.ts (parseHash, boardHash, Route)
  - web/src/lib/route.svelte.ts (route store, go, replace)
  - format.tickLabel, data.loadSeason/findSeason/isLatest
  - components/Scrubber.svelte, components/StatusPanel.svelte (notice/error/empty)
affects:
  - 02-04 (states/polish reuse StatusPanel error/empty variants)
  - Phase 4 (team routes are already parsed as 'reserved')
tech-stack:
  added: []
  patterns:
    - route.current is the single source of truth; go() pushes history, replace() uses replaceState and sets the route directly
    - season files are cached per session as promises; rejected ones are evicted; stale responses are dropped via a requested-season token
key-files:
  created:
    - web/src/lib/router.ts
    - web/src/lib/router.test.ts
    - web/src/lib/route.svelte.ts
    - web/src/components/Scrubber.svelte
    - web/src/components/StatusPanel.svelte
  modified:
    - web/src/lib/format.ts
    - web/src/lib/format.test.ts
    - web/src/lib/data.ts
    - web/src/App.svelte
decisions:
  - "Reserved later-phase routes (#/team/..., #/history, #/records, #/methodology) parse to 'reserved' and are rewritten to #/ without a notice"
  - "go(hash) sets the route directly when the hash is already current, so Latest/season changes never get stuck"
  - "The bad-link notice clears when the user navigates to a valid non-latest board"
metrics:
  duration: 4min
  completed: 2026-11-11
  tasks: 2
  files: 9
---

# Phase 2 Plan 02: Week Scrubber and Hash Deep Links Summary

The board now has a season select, a week slider and a Latest button. With them you can move to any week from 1999 through the latest. A small hash router (`#/` and `#/board/{season}/{week}`) gives every view a URL that reopens it. Bad links fall back to the latest board and show a notice that can be dismissed.

## What was built

**Task 1 (TDD): router, route store, tick labels, season loader**
- `router.ts`: `parseHash` is a pure function that returns latest, board, reserved or invalid. `boardHash` builds the hash string.
- `route.svelte.ts`: a `$state` object that `hashchange` updates. `go()` assigns `location.hash`, which adds a history entry. `replace()` calls `history.replaceState` and also sets `route.current` itself, because `replaceState` does not fire `hashchange` (Pitfall 6).
- `format.tickLabel`: returns Pre / Wk N / WC / Div / Conf / SB, based only on `reg_weeks`. There is no hardcoded 2021.
- `data.ts`:
  - `loadSeason(meta, season)` caches season files in a `Map` of promises and adds `?v=generated_at` to the URL. A failed fetch is removed from the cache, so "Try again" fetches it again.
  - New helpers: `findSeason` and `isLatest`.
  - `loadMeta` and `loadLatest` still use `no-store`. Season files use the normal browser cache, since the `?v=` changes on every refresh.

**Task 2: Scrubber, StatusPanel, App routing**
- **Scrubber:**
  - It is a `form role="search"`. It has a labelled season select (newest season first, 44px tall).
  - A Week label sits next to an `<output>` and the "In progress" badge, which only appears for a partial latest week.
  - The slider is a native range from 0 to `max_week` with `aria-valuetext`. Its hit area is 44px and it uses `accent-color`.
  - Three tick labels sit under the track. The last regular-season week only gets a tick when it falls inside `max_week`.
  - The Latest button is disabled on the latest week.
  - Mobile uses a stacked grid. At 1024px and up it is a single sticky row. There are no key handlers.
- **App:**
  - `target` is derived from `route.current` and `meta`. A board route that matches `meta.latest` renders as the latest view without rewriting the hash.
  - An `$effect` handles redirects. Invalid links and out-of-range board routes run `replace('#/')` and show the notice. Reserved routes run `replace('#/')` with no notice.
  - Season loading has a stale-response guard. While a season loads, the previous board stays visible at opacity 0.6 with `aria-busy`, and the heading already shows the new season and week.
  - If a season fails to load, a panel shows "Try again" and "Go to latest". If a week has no rows, an empty-state panel shows.
  - Changing the season keeps the current week, or clamps it to the new season's max.
- **StatusPanel:** has `notice`, `error` and `empty` variants. The notice has a 44px × dismiss button. Error panels use `role="alert"` only when `fatal` is set.

## Verification

- `npm run test`: 23 passed (router and tickLabel cases added).
- `npm run check`: 0 errors, 0 warnings.
- `npm run build`: succeeds (56 KB JS, 21.8 KB gzip).
- All grep gates pass. The `range`, `aria-valuetext`, aria-label, `loadSeason`, `route.current` and ’-apostrophe notice gates all match. Scrubber has no key handlers. format.ts has no 2021 outside comments.
- Data sanity: `snapshots/1999.json` week 0 has 31 rows, and the max week is 21.
- The browser checks are left to the orchestrator: `#/board/2007/21`, `#/board/1999/0`, `#/board/1800/3`, `#/team/BUF`, the slider and history, and reloading.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Added an empty-state panel for a week with no rows**
- **Found during:** Task 2
- **Issue:** Once `weeks[String(week)]` could be missing or empty, the board would have rendered as a blank list.
- **Fix:** The App now renders StatusPanel `empty` ("No moods to report" plus "Go to latest"), using the UI-SPEC copy.
- **Files modified:** web/src/App.svelte
- **Commit:** 18e844e

**2. [Rule 1 - Bug] `go()` with the current hash did nothing**
- **Found during:** Task 1
- **Issue:** Assigning `location.hash` its current value doesn't fire `hashchange`. For example, Latest while the hash is already `#/` would not update the route.
- **Fix:** In that case `go()` sets `route.current` itself.
- **Files modified:** web/src/lib/route.svelte.ts
- **Commit:** 3f1478f

Otherwise the plan was executed as written. The fatal-error panel from 02-01 stays inline in App, because its body contains `<code>` markup. 02-04 can move it onto StatusPanel.

## TDD Gate Compliance

- Task 1: RED `58a1509` (test), then GREEN `3f1478f` (feat). No refactor was needed.

## Known Stubs

None.

## Self-Check: PASSED

---
phase: 02-elo-mood-board
plan: 04
subsystem: web
tags: [svelte5-runes, states, skeleton, responsive, a11y]
requires:
  - components/StatusPanel.svelte, Scrubber.svelte, route go() (02-02)
  - components/BoardRow.svelte, MoodBoard.svelte, app.css tokens (02-01)
provides:
  - App boot() with loading/ready/error status and a fatal "Try again" retry
  - MoodBoard loading (8-row static skeleton), busy (dimmed season switch) and empty-week modes
  - StatusPanel children snippet (markup bodies without {@html}) and a literal role="alert" fatal branch
  - BoardRow fallbacks ("–") for missing or non-finite numbers
affects:
  - Phase 4+ (new views reuse StatusPanel/MoodBoard states)
tech-stack:
  added: []
  patterns:
    - StatusPanel takes `body` for plain text or `children` for markup; the shared content snippet keeps the alert and status branches identical
    - MoodBoard owns every board-area state (skeleton, busy, empty, rows); App only decides which data to pass
key-files:
  created: []
  modified:
    - web/src/App.svelte
    - web/src/components/MoodBoard.svelte
    - web/src/components/StatusPanel.svelte
    - web/src/components/BoardRow.svelte
    - web/src/app.css
    - web/src/lib/format.ts
    - web/src/lib/format.test.ts
decisions:
  - "The fatal panel's body is passed as a children snippet so `uv run fgs refresh` renders in <code> without {@html}"
  - "Failed boot clears meta/latest, so the scrubber, board and footer all drop out together"
  - "The custom range-thumb styling (optional in UI-SPEC) was skipped. appearance:none would lose the native accent-color fill, so accent-color remains the baseline"
metrics:
  duration: 9min
  completed: 2026-11-11
  tasks: 2
  files: 7
---

# Phase 2 Plan 04: Board States and Responsive Polish Summary

The mood board now has a deliberate render for every data state: a static skeleton while loading, a fatal panel with a working "Try again", an empty-week panel, and "–" for missing numbers. It has no horizontal overflow at 320 or 375px and aligns its column header at desktop width.

## What was built

**Task 1: loading, fatal-error and empty states** (`944cdcc`)
- `App.svelte`: `boot()` sets a status of `'loading' | 'ready' | 'error'`. While loading, the header shows, the Scrubber is disabled, and MoodBoard shows its skeleton. On error, `StatusPanel variant="error" fatal` replaces the scrubber and board, and the footer is hidden. The panel uses the spec copy, and its "Try again" button calls `boot`. The 02-02 season-error and bad-link notice flows are unchanged.
- `MoodBoard.svelte`: new props `rows`, `meta`, `week`, `loading` and `busy`.
  - Skeleton: 8 static 64px surface rows with a 16px `--border` bar, `aria-busy="true"`, and a visually hidden "Loading the mood board…". There is no animation.
  - `busy`: the board dims to opacity 0.6 and sets `aria-busy`.
  - An empty week shows "No moods to report" with a "Go to latest" button that calls `go('#/')`.
  - The desktop column header is shared by all modes.
- `StatusPanel.svelte`: adds an optional `children` snippet and a literal `role="alert"` branch for fatal errors (`role="status"` otherwise). Buttons get a hover state and the accent `:focus-visible` ring. `<code>` has its own styling.
- The 02-02 inline fatal panel and its CSS were removed from App.

**Task 2: mobile, desktop and accessibility polish** (`76d4241`)
- `BoardRow.svelte`:
  - Missing or non-finite rank, score, record and Elo now render "–", and missing scores are muted. The screen-reader sentence never contains "NaN", "null" or "undefined".
  - Rank, score and change cells are `white-space: nowrap`. Name and label are still the only cells that can shrink (`min-width: 0` plus ellipsis).
- `format.ts`: `formatDelta(NaN)` now returns "–". A test was added (24 tests in total).
- `app.css`: global 120ms `background-color`/`color` transition on buttons. The existing reduced-motion rule turns it off. There is a comment on why we don't use an overflow-x guard.
- Already met by 02-01/02-02, so no change was needed:
  - Scrubber: sticky at ≥1024px with a surface background, a border and `z-index: 1`. Every control is at least 44px and has the focus ring.
  - Page wrapper: 640px wide on mobile, `--content-max` on desktop, with 2xl/3xl padding.
  - BoardRow: abbreviation letter-spacing, tabular-nums, and row padding.

## Verification

- `npm run test`: 24/24 pass. `npm run check`: 0 errors, 0 warnings. `npm run build`: OK.
- Every grep acceptance check passes:
  - "Try again" → `boot` in App
  - `role="alert"` in StatusPanel
  - no `{@html` anywhere
  - `sticky` inside the 1024px block
  - `text-overflow: ellipsis` and `min-width: 0` in BoardRow
  - no `overflow-x: hidden` in app.css
- Headless Chrome against `vite preview`:
  - 320px and 375px iframes: `scrollWidth == clientWidth` (320/320, 375/375), and no element extends past the viewport. Names and labels ellipsize at 320px.
  - 1280px: the column header lines up with the row cells, and the scrubber sits on a single row.
  - With `dist/data/meta.json` hidden: the fatal panel renders with the `<code>` command and "Try again". The scrubber and footer are hidden. The file was restored afterwards; `public/` was never touched.
- Left for the orchestrator's browser pass: dark theme, sticky scrubber while scrolling, "Try again" recovering after the file is restored, and keyboard Tab order.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] StatusPanel could not render a `<code>` body**
- **Found during:** Task 1
- **Issue:** `body` was a plain string, so the fatal copy's `<code>` command couldn't be shown without `{@html}`, which the plan forbids.
- **Fix:** added an optional `children` snippet. `body` is now optional.
- **Files modified:** web/src/components/StatusPanel.svelte
- **Commit:** 944cdcc

**2. [Rule 1 - Bug] Non-finite numbers could render as "NaN"/"undefined"**
- **Found during:** Task 2
- **Issue:** `formatDelta(NaN)` returned "▼ NaN". A missing score, rank or record would also have rendered raw.
- **Fix:** added a finite-number guard in `formatDelta` and `ok()`/`num()` helpers in BoardRow, plus a test.
- **Files modified:** web/src/lib/format.ts, web/src/lib/format.test.ts, web/src/components/BoardRow.svelte
- **Commit:** 76d4241

**Scope note:** `Scrubber.svelte` is listed in the plan's files but needed no change. Its sticky behavior, 44px controls and focus rings already met the spec.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: web/src/components/MoodBoard.svelte, web/src/components/StatusPanel.svelte, web/src/App.svelte
- FOUND: commits 944cdcc, 76d4241

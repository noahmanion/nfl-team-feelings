---
phase: 08-callouts-records-my-team
plan: 05
subsystem: web
tags: [svelte5, runes, localStorage, my-team, a11y]
requires:
  - phase: 08-02
    provides: orderCallouts(list, myTeam) and the board card strip
  - phase: 08-04
    provides: RecordsPage, records.json active streaks, streakLine
provides:
  - Remembered "my team" pin (fgs.myTeam) highlighted on board, chart, records and callout strip
affects: []
tech-stack:
  added: []
  patterns:
    - "Pure storage helpers with injected StorageLike + thin $state wrapper (myteam.ts / myteam.svelte.ts)"
    - "Raw pinned value always passed through validMyTeam(abbr, meta.teams) before use"
key-files:
  created:
    - web/src/lib/myteam.ts
    - web/src/lib/myteam.test.ts
    - web/src/lib/myteam.svelte.ts
    - web/src/components/PinButton.svelte
  modified:
    - web/src/lib/history.ts
    - web/src/lib/history.test.ts
    - web/src/components/Badge.svelte
    - web/src/components/BoardRow.svelte
    - web/src/components/MoodBoard.svelte
    - web/src/components/TeamPage.svelte
    - web/src/components/HistoryPage.svelte
    - web/src/components/RecordsPage.svelte
    - web/src/App.svelte
    - README.md
    - .planning/REQUIREMENTS.md
key-decisions:
  - "BoardRow receives the validated pin as a prop from MoodBoard (one validation per board, not per row)"
  - "PinButton sits absolutely positioned as a sibling of the row link; rows reserve tap-min + space-sm on the right, and the desktop column header padding matches"
  - "setMyTeam updates in-memory state before writing storage, so a pin still works for the session when storage throws"
  - "storage event with key null (localStorage.clear in another tab) also re-reads the pin"
requirements-completed: [SITE-08]
duration: ~6min
completed: 2026-11-11
---

# Phase 8 Plan 05: My Team Pin Summary

**You can pin a team with a ☆/★ button on any board row or team page header. The pin is saved under the `fgs.myTeam` localStorage key, and invalid stored values are ignored. The pinned team gets the accent tint and a "My team" badge on the board (rows keep their order) and on records rows. It is also the default team on the history chart, and its callouts come first in the card strip.**

## Performance
- Duration: ~6 min
- Tasks: 3/3
- Files: 4 created, 11 modified

## Accomplishments
- `myteam.ts`: `MY_TEAM_KEY`, `readMyTeam`, `writeMyTeam` and `validMyTeam`. None of them ever throw. `validMyTeam` checks own keys only, so values like `__proto__` and `<script>` are rejected. 18 vitest cases cover normal, throwing and missing storage.
- `myteam.svelte.ts`: the exported `myTeam` $state object, plus `setMyTeam`, `toggleMyTeam` and a listener that syncs the pin across tabs.
- `defaultTeam(latestRows, myTeam?)` uses my team when it is on the board, otherwise the top team. The existing behaviour is unchanged.
- `PinButton`: 44px button with `aria-pressed` and a label that changes between Pin and Unpin. `Badge` gets a new `neutral` variant.
- BoardRow: the row is now `li#row-ABBR` containing the link with the PinButton as its sibling. The pinned row gets the `color-mix` tint, the "My team" badge, and "My team." added to its screen-reader text.
- MoodBoard: a "Jump to my team" button that scrolls to the row and focuses its link, with no fragment link.
- HistoryPage: a team in the hash wins, then my team, then the top team. RecordsPage: pinned entries are tinted and badged, and a "Your team: …" streak line links to the team page. App: `orderCallouts(..., validMyTeam(...))`.
- README status: v1 complete (all 8 phases).

## Task Commits
1. Task 1 RED: `30f0717` test(08-05): add failing tests for my-team storage and defaultTeam preference
2. Task 1 GREEN: `c954110` feat(08-05): storage-safe my-team state and defaultTeam preference
3. Task 2: `f0f7dc0` feat(08-05): pin button, my-team row highlight, jump to my team, team page pin
4. Task 3: `25c44a5` feat(08-05): my team across chart, records and callout strip; README status

## Verification
- `npm run check`: 0 errors, 0 warnings. vitest: 141/141. `npm run build`: OK. Pipeline `uv run pytest -q`: 570 passed.
- All grep and awk acceptance checks pass: PinButton is not inside the `<a>`, the tint appears exactly once in BoardRow, MoodBoard has no `#row-`, and nothing calls `orderCallouts(..., null)`.
- Not yet done: the orchestrator's browser check at 375px and 1280px.

## Deviations from Plan
- **[Rule 2 - Correctness] Desktop column header padding.** Rows now reserve space on the right for the pin, so the right padding of the `.columns` header in MoodBoard was widened to match. Without this the headers would be misaligned at 1024px and wider. Files: MoodBoard.svelte. Commit: `f0f7dc0`.
- **REQUIREMENTS.md.** All Phase 8 plans now have passing summaries, so the orchestrator note allowed marking INSIGHT-02/03/06 and SITE-05/06/08/09 Complete. INSIGHT-04 stays Pending because it requires a manual top-10 sanity check, which no one has signed off yet. That traceability row is annotated.

## Known Stubs
None.

## TDD Gate Compliance
The RED commit (`30f0717`) comes before the GREEN commit (`c954110`). No refactor commit was needed.

## Self-Check: PASSED
- Files exist: myteam.ts, myteam.test.ts, myteam.svelte.ts, PinButton.svelte
- Commits exist: 30f0717, c954110, f0f7dc0, 25c44a5

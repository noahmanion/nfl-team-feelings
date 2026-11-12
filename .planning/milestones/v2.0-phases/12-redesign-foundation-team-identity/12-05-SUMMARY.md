---
phase: 12-redesign-foundation-team-identity
plan: 05
subsystem: web
tags: [board, callouts, movers, chrome, logos, era-names, editorial]
requires:
  - phase: 12-01
    provides: editorial tokens (--rule-strong, --surface-hover, --cell-tint, --score-cell, --font-mono, --text-micro, --weight-bold)
  - phase: 12-02
    provides: TeamLogo component and teamNames helpers (eraName, eraAbbr, isActiveFranchise, eraText)
provides:
  - Editorial standings-table board (rule-separated rows, mono micro header over a strong rule, band-shaded score cell)
  - TeamLogo on board rows, callouts and movers, with era-correct names and abbreviations for the viewed season
  - Washington callout/mover copy rewritten through eraText for seasons <= 2021
  - HOU hidden from boards before 2002 (D-17)
  - Footer trademark disclaimer
affects: [12-06, 12-07, 13, 14]
tech-stack:
  added: []
  patterns:
    - "Shaded score cell: style:--band={stripe}; color-mix(in srgb, var(--band) var(--cell-tint), var(--bg)) + inset 4px band edge"
    - "eraName shim for components holding only one TeamMeta: { teams: team ? { [F]: team } : {} }"
key-files:
  created: []
  modified:
    - web/src/components/BoardRow.svelte
    - web/src/components/MoodBoard.svelte
    - web/src/components/BoardHeading.svelte
    - web/src/components/CalloutCard.svelte
    - web/src/components/CalloutCards.svelte
    - web/src/components/MoversStrip.svelte
    - web/src/components/SiteHeader.svelte
    - web/src/components/SiteFooter.svelte
    - web/src/components/Scrubber.svelte
    - web/src/components/Badge.svelte
    - web/src/components/Delta.svelte
    - web/src/components/PinButton.svelte
    - web/src/components/StatusPanel.svelte
    - web/src/components/MoodLabel.svelte
key-decisions:
  - "Board score cell spans full row height via negative block margin equal to the row padding (both breakpoints)"
  - "Missing score renders '–' in --text inside the cell (no muted text on a tint); the v1 .missing muted class was dropped"
  - "Mobile BoardRow uses a 4-column grid (28px | 1fr | auto | score-cell) so the Delta sits on line 2 right-aligned just before the cell"
  - "Row focus ring is inset -2px (UI-SPEC focus contract for rows); movers rows likewise"
  - "Board empty state keys off visibleRows (after the HOU filter)"
patterns-established:
  - "Era identity on board surfaces: name/abbr from teamNames for the viewed season; PinButton keeps the current name"
requirements-completed: [DESIGN-03, DESIGN-04, LOGO-02, LOGO-03]
duration: 8min
completed: 2026-11-12
---

# Phase 12 Plan 05: Board and Site Chrome Editorial Restyle Summary

**Board restyled as a standings table: 24px team logos, era-correct names and abbreviations (SD/OAK/STL), and band-tinted mono score cells. Callouts are now rule-topped blocks with Washington copy rewritten by era, movers are unboxed rows, and the header, footer and primitives use the editorial tokens. The footer now carries the trademark disclaimer.**

## Performance

- Duration: ~8 min
- Tasks: 3/3
- Files modified: 14

## Accomplishments

- BoardRow uses TeamLogo 24 with eraName/eraAbbr for the viewed season. Rows are separated by bottom rules with transparent backgrounds and a hover tint. The score cell is band-shaded with the 4px band edge, and the Elo line moved under the record at 1024px and up.
- MoodBoard has a mono micro uppercase column header over `--rule-strong`, with numeric headers right-aligned. Rows sit with no gap, skeleton rows are square, and the `isActiveFranchise` filter feeds the rows, jump-to-mine and the empty state.
- CalloutCard uses TeamLogo 20 and the era name, and its headline, detail and evidence go through `eraText`. Each block has a 2px band rule on top and no box. The copy-link, manual fallback and `role="status"` live region are untouched.
- MoversStrip uses TeamLogo 20 and eraAbbr, with screen-reader text from eraName/eraText. Rows are unboxed with bottom rules, and the Risers/Fallers titles are mono micro.
- Chrome: SiteHeader gets a bold wordmark and h1 plus a strong bottom rule, with the nav markup byte-identical. SiteFooter gets a top rule and the new trademark copy. Scrubber is a square bar with a bottom rule and mono output and ticks. Badge is mono micro uppercase, Delta is mono, and PinButton and StatusPanel now use tokens.

## Task Commits

1. Task 1, board table: `155f228`
2. Task 2, callouts and movers: `205d89c`
3. Task 3, chrome and primitives: `2b3097f`

## Verification

- `npm test`: 212/212 passing (sep, myteam, nohotlink, callouts and copyLink unchanged)
- `npm run check`: 0 errors, 0 warnings
- `npm run build`: OK
- `grep -l TeamChip` on BoardRow, CalloutCard and MoversStrip: none

## Deviations from Plan

**1. [Acceptance-grep mismatch, no code change] SiteHeader nav single-line grep**
- The criterion `grep -c '<span class="item"><Sep /><a '` = 3 returns 0. The existing nav markup (unchanged since v1, and the plan forbids changing it) splits the tag as `<span class="item"\n      ><Sep /><a `. The real guard, `sep.test.ts`, matches `<span class="item"\s*><Sep \/><a ` and passes with 3. Following the plan's "do NOT change nav markup", I left it alone.

Otherwise the plan executed as written.

## Known Stubs

None.

## Self-Check: PASSED

- All 14 modified files exist; commits 155f228, 205d89c and 2b3097f are present in git log.

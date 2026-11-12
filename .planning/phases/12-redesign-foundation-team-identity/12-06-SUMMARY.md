---
phase: 12-redesign-foundation-team-identity
plan: 06
subsystem: web
tags: [team-page, records, methodology, logos, era-names, editorial, chart-frame]
requires:
  - phase: 12-01
    provides: editorial tokens (--cell-tint, --score-cell, --prose-max, --rule-strong, --surface-hover, --font-mono, --weight-bold)
  - phase: 12-02
    provides: TeamLogo component and teamNames helpers (eraName, eraAbbr, eraText)
  - phase: 12-03
    provides: ChartFrame wrapper (headline, dek, notes, level, id)
provides:
  - Editorial team page with a 32/48px TeamLogo header, era-correct h2/status copy, a band-shaded score cell and rule-topped sections
  - FactorBars framed in ChartFrame (id "why-heading") with the "Where the {score} comes from" headline and dek
  - RecentGames opponent logos with that game's era abbreviation and era name
  - Records lists with 24px logos, era names per row season / streak start season (active streaks use the current name), band-shaded value cells
  - Methodology "How it works" head and dek, 680px prose column, relocation note
affects: [12-07, 13, 14]
tech-stack:
  added: []
  patterns:
    - "Team page band: bandIndex(row.band, meta.bands) -> var(--mood-N) via moodToken, same derivation as BoardRow"
    - "Header logo size via <svelte:window bind:innerWidth />, wide = innerWidth >= 1024 (first paint 32)"
key-files:
  created: []
  modified:
    - web/src/components/TeamPage.svelte
    - web/src/components/FactorBars.svelte
    - web/src/components/RecentGames.svelte
    - web/src/components/RecordsPage.svelte
    - web/src/components/MethodologyPage.svelte
key-decisions:
  - "Records value cell draws its 4px band edge with border-left instead of the inset box-shadow, because the plan's acceptance check bans box-shadow on RecordsPage; the result looks the same"
  - "Records streak day counts are set at body size (16) in mono, not 20: 'N days' strings at 20px squeeze the name column at 320px"
  - "The methodology page head renders outside the load states, so 'How it works' shows during loading and on error"
  - "hasPoints = !!row?.points, which matches the condition FactorBars uses before it shows 'Factor breakdown unavailable'"
requirements-completed: [DESIGN-02, DESIGN-03, DESIGN-04, LOGO-02, LOGO-03]
duration: 6min
completed: 2026-11-11
---

# Phase 12 Plan 06: Team, Records and Methodology Editorial Restyle Summary

The team, records and methodology pages now use the editorial layout. The team header shows the team logo and the team's name for the viewed season (LAC 2010 reads "San Diego Chargers"). The score breakdown sits in a ChartFrame, recent games show opponent logos with that game's abbreviation (OAK, SD, STL), and records rows have era names and band-tinted value cells. Methodology gained a "How it works" head and the relocation note.

## Performance

- **Duration:** about 6 min
- **Tasks:** 3/3
- **Files modified:** 5

## Accomplishments
- TeamPage: TeamLogo 32/48 replaces TeamChip. `eraName(team, season, meta)` feeds the h2, the loading line and the error/empty copy. PinButton keeps the current name. Record and rank numbers sit in `.num`. The score is a band-shaded cell, at least 72x56px, mono 28. The blurb goes through `eraText` for Washington. Sections are rule-topped. Exactly 5 `<Sep />` remain, 2 of them in the week nav.
- FactorBars: square 8px bars, a 1px muted center baseline, a mono value/baseline/total, and a `--rule-strong` total rule. It sits in `<ChartFrame id="why-heading" level={3}>`.
- RecentGames: 20px opponent logo, `eraAbbr(g.opp, g.season)`, an era name in the screen-reader line, and a mono outcome.
- RecordsPage: unboxed rows with bottom rules, `--surface-hover` hover, a mono rank, a 24px logo, era names, and a `.num` meta line. The shaded value cell spans the row height. The as-of line is mono micro uppercase. The footnote uses era names.
- MethodologyPage: a page head with dek, rule-topped sections, a `--prose-max` cap on prose, square 8px swatches, mono ranges and unboxed rows. The local `.num` rule was dropped because app.css owns it. No 538 text was added.

## Task Commits
1. **Task 1: TeamPage, FactorBars in ChartFrame, RecentGames logos:** `69260db` (feat)
2. **Task 2: RecordsPage logos, era names, shaded cells:** `c77f7ae` (feat)
3. **Task 3: MethodologyPage head, prose column, relocation note:** `89f536d` (feat)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Records band edge uses border-left, not box-shadow**
- **Found during:** Task 2
- **Issue:** The shaded-cell recipe uses `box-shadow: inset`, but the acceptance criteria require 0 `box-shadow` matches in RecordsPage.
- **Fix:** The 4px band edge is a `border-left` in the band color. It looks the same.
- **Files modified:** web/src/components/RecordsPage.svelte
- **Commit:** c77f7ae

**2. [Rule 2 - Missing] TeamPage band derivation added**
- **Found during:** Task 1
- **Issue:** The plan refers to "the existing band/stripe derivation", but TeamPage had none.
- **Fix:** Added the same `bandIndex` + `moodToken` derivation that BoardRow uses, so the band comes from the exported label and not the raw score.
- **Commit:** 69260db

## Verification
- `npm test`: 212/212 tests pass across 19 files, including sep, records, methodology and brand. `npm run check`: 0 errors and 0 warnings. `npm run build` passes.
- All acceptance greps pass. `grep -l TeamChip web/src/components/*.svelte` lists only TeamLogo.svelte; TeamChip.svelte never names itself.

## Self-Check: PASSED
- All 5 modified files exist. Commits 69260db, c77f7ae and 89f536d are present in git log.

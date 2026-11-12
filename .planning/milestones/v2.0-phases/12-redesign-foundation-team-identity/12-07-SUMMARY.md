---
phase: 12-redesign-foundation-team-identity
plan: 07
subsystem: web
tags: [verification, playwright, screenshots, readme, kill-switch]
requires:
  - phase: 12-01..12-06
    provides: fonts, plotTheme, logos, era names, ChartFrame, editorial pages
provides:
  - Re-runnable Playwright sweep (verify_ui.py, default + --logos-off modes)
  - 24 screenshots (6 pages x 1280/375 x light/dark) as DESIGN-03 evidence
  - README font credit (SIL OFL 1.1) and VITE_LOGOS=off takedown note
  - Signed-off 12-VALIDATION.md (nyquist_compliant: true)
affects: [13, 14]
tech-stack:
  added: []
  patterns:
    - "Python Playwright sweep against vite preview :4173; ?r=1 before the hash forces a fresh data load"
key-files:
  created:
    - .planning/phases/12-redesign-foundation-team-identity/verify_ui.py
    - .planning/phases/12-redesign-foundation-team-identity/screenshots/ (24 PNGs)
  modified:
    - README.md
    - web/src/components/TeamPage.svelte
    - .planning/phases/12-redesign-foundation-team-identity/12-VALIDATION.md
key-decisions:
  - "Week-nav separators travel with the following link (same no-wrap item pattern as the site nav), so a wrapped 375px line never ends in a dangling dot"
  - "Screenshots are committed as phase evidence (about 10 MB)"
requirements-completed: [DESIGN-01, DESIGN-02, DESIGN-03, DESIGN-04, LOGO-02, LOGO-03]
duration: 12min
completed: 2026-11-11
---

# Phase 12 Plan 07: Phase Verification Sweep Summary

The README now credits the fonts (SIL OFL 1.1) and documents the `VITE_LOGOS=off` takedown switch. A re-runnable Python Playwright sweep took 24 screenshots and passed every behavior check against both the normal build and the logos-off build. One small 375px defect (a stray dot at the end of a wrapped week-nav line) was found and fixed.

## Performance
- **Duration:** about 12 min
- **Tasks:** 2/2
- **Files:** 3 modified, 1 script and 24 screenshots created

## Task Commits
1. **Task 1: README credits and logo kill-switch note:** `f721c3d` (docs)
2. **Visual fix, week-nav separator at 375px:** `00d2a74` (fix)
3. **Task 2: Playwright sweep, screenshots, validation sign-off:** `dc00d32` (test)

## Gate results
- `npm test`: 212/212 pass across 19 files (baseline was 167 tests in 13 files). `npm run check`: 0 errors, 0 warnings. `npm run build` passes, both before and after the fix.
- `VITE_LOGOS=off npm run build` passes.
- `git status --porcelain pipeline/` is empty.

### `verify_ui.py --logos-off` (VITE_LOGOS=off build)
```
PASS kill switch: no logo imgs on board - 0 imgs
PASS kill switch: >=30 chips on board - 44 chips
PASS all requests same-origin
ALL PASS
```

### `verify_ui.py` (normal build, final run after the fix)
```
PASS no h-scroll {board, team-era, team-current, history, records, methodology} 375 {light, dark} - scrollWidth 375 vs 375  (12 checks)
PASS 24 screenshots - 24 files
PASS LAC 2010 shows 'San Diego Chargers'
PASS KC header logo img - 1 imgs
PASS body font Inter Variable
PASS .num font IBM Plex Mono
PASS document.fonts.check Inter Variable
PASS grid groups on history - 1 groups
PASS HistoryChart has exactly one svg image - 1 images
PASS grid groups on methodology - 2 groups
PASS pin survives reload (My team badge) - pinned JAX
PASS Jump to my team focuses pinned row - row-JAX
PASS scrubber ArrowLeft -> #/board/ hash - #/board/2026/8
PASS copy link status text - 'Link copied'
PASS logo 404 -> chip in #row-KC - chips 1, visible imgs 0
PASS all requests same-origin
ALL PASS
```

## Requirement -> evidence map
| Req | Evidence |
|-----|----------|
| DESIGN-01 | brand.test.ts (Fontsource, no CDN, no 538). Sweep: body font resolves to Inter Variable, `.num` to IBM Plex Mono, and `document.fonts.check` is true. All requests stay same-origin. README credits OFL 1.1. |
| DESIGN-02 | plotTheme.test.ts and chartFrame.test.ts. Sweep: value-axis grid groups on history (1) and methodology (2). Screenshots show the ChartFrame headline, dek and SOURCE/NOTES footer, with gray background lines and one highlighted line. |
| DESIGN-03 | 24 screenshots in `screenshots/`. I reviewed board, team-era, history, records and methodology at 1280 and the 375 crops. Rows are separated by rules, score cells are band-shaded, and logos sit on light discs in dark mode. |
| DESIGN-04 | 212/212 tests. Sweep: no horizontal scroll at 375 on any route in either scheme. Pin survives reload, Jump to my team works, scrubber ArrowLeft updates the hash, Copy link shows "Link copied". |
| LOGO-02 | logos.test.ts and teamLogo.test.ts. Sweep: a 404 on one logo falls back to that team's chip. The `--logos-off` build shows 0 logo images and 44 chips. The KC header shows the local logo. |
| LOGO-03 | teamNames.test.ts. Sweep: the LAC 2010 page reads "San Diego Chargers", also visible in the team-era screenshots. |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Week-nav separator dangled at the end of a wrapped line at 375px**
- **Found during:** Task 2 visual review (team-era-375)
- **Issue:** "← Prev week · Next week → ·" wrapped and left a trailing dot, with "See the board for this week" on the next line.
- **Fix:** Each separator is now in a no-wrap `.item` span with the link after it (the WR-10 pattern the site nav already uses). The Sep count is unchanged, so sep.test.ts still passes.
- **Files modified:** web/src/components/TeamPage.svelte
- **Commit:** 00d2a74

**2. [Rule 3 - Blocking] Playwright headless shell build 1194 was missing**
- **Fix:** Ran `python3 -m playwright install chromium` with the system Python 3.13. Nothing was added to the project.

## Notes for verify-work
- In dark mode the highlighted HistoryChart line for JAX renders near-white, which is the `teamStroke` contrast adjustment for a dark team color. That is intentional behavior from 12-04 and was left as is.
- On narrow widths the site nav wraps to "· How it works". This is the leading-dot pattern WR-10 deliberately chose.

## Self-Check: PASSED
- README.md, verify_ui.py, screenshots/team-era-1280-light.png and screenshots/board-375-dark.png exist (24 PNGs in total).
- Commits f721c3d, 00d2a74 and dc00d32 are present in git log.

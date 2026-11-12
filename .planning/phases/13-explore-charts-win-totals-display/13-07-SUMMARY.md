---
phase: 13-explore-charts-win-totals-display
plan: 07
subsystem: web (phase gate)
tags: [verification, playwright, explore, win-totals]
requires: [13-01, 13-02, 13-03, 13-04, 13-05, 13-06]
provides: [phase-13-evidence, verify_ui.py]
affects: [web/src/lib/scatterMarks.ts, web/src/components/RecordScatter.svelte, web/src/components/ChartFrame.svelte]
tech-stack:
  added: []
  patterns: ["Read Plot's svg.value one requestAnimationFrame after click (Plot updates it in rAF)"]
key-files:
  created:
    - .planning/phases/13-explore-charts-win-totals-display/verify_ui.py
    - .planning/phases/13-explore-charts-win-totals-display/screenshots/ (6 PNGs, 724 KB total)
  modified:
    - README.md
    - .planning/phases/13-explore-charts-win-totals-display/13-VALIDATION.md
    - web/src/lib/scatterMarks.ts
    - web/src/components/RecordScatter.svelte
    - web/src/components/ChartFrame.svelte
    - web/src/components/ExplorePage.svelte
    - web/src/lib/chartFrame.test.ts
decisions:
  - "Scatter click handler defers its decision one animation frame because Plot sets svg.value in rAF; without this, the first touch tap was lost"
  - "The OLS line label draws after the logos with a --bg halo so the top-right cluster can't hide it"
  - "ChartFrame takes a footer prop (default true); Explore loading frames pass footer={false}"
metrics:
  duration: ~25min
  completed: 2026-11-11
---

# Phase 13 Plan 07: Phase gate and visual sweep Summary

All static gates pass. A 38-check Playwright sweep (`verify_ui.py`) reports ALL PASS three runs in a row, and the six screenshots were reviewed by eye. The sweep found two real defects (touch double-tap and a hidden OLS label), and I fixed both along with the ChartFrame loading-footer gap from plan 06.

## Gates (D-26)

- `npm test`: 23 files, 275 tests passed (274 before this plan, plus 1 new ChartFrame footer test).
- `npm run check`: 0 errors, 0 warnings across 365 files.
- `npm run build`: OK.
- `uv run pytest -q`: 642 passed, including `tests/test_golden_scores.py`. The golden pin is unchanged and `pipeline/` was not touched.

## verify_ui.py output (final run)

```
PASS latest 2026/9: EPA scatter >= 28 logos - 32
PASS latest 2026/9: record scatter >= 28 logos - 32
PASS nav Explore aria-current=page - page
PASS headline 'How efficiently every team plays'
PASS headline 'Record vs evidence'
PASS no 'luck' on Explore
PASS table >= 28 rows - 32
PASS table team link -> #/team/ - #/team/JAX
PASS 2025/10: EPA scatter >= 28 logos - 32
PASS 2025/10: record scatter >= 28 logos - 32
PASS EPA dek mentions 2025
PASS week 0 empty state in both frames - 2 frames
PASS #/explore/2099/3 -> #/explore - #/explore
PASS mouse click logo -> #/team/ - #/team/DET/2025/10
PASS rank delta readable (spot / no change)
PASS no '#▲' / '#▼' delta text
PASS records list > 700px wide - 960px
PASS BUF 2026: Preseason expectations
PASS BUF 2026: opening-line suffix
PASS BUF 2023: Vegas display only
PASS BUF 2023: Model used in score
PASS BUF 2015: Vegas used in score
PASS BUF 2015: normalized note
PASS BUF 2000: no Vegas before 2003
PASS 2025/10 dark: EPA scatter >= 28 logos - 32
PASS 2025/10 dark: record scatter >= 28 logos - 32
PASS dark mode logo discs present - 32 circles
PASS no h-scroll explore / explore-2025-10 / team-2023 at 375, light and dark (6 checks)
PASS touch tap 1 keeps hash
PASS touch tap 1 shows tip
PASS touch tap 2 -> #/team/ - #/team/DET/2025/10
PASS exactly 6 screenshots - 6 files
PASS all requests same-origin
ALL PASS
```

## Requirement to evidence map

| Requirement | Evidence |
|-------------|----------|
| EXPL-02 (EPA offense vs defense scatter) | 32 logos at latest, 2025/10 and dark; week 0 empty state; 2099 fallback; mouse click and touch double-tap navigate; table with 32 rows and links; `explore-1280-light.png`, `explore-2025-10-1280-dark.png`, `explore-375-dark.png`; explore.test.ts and router.test.ts |
| EXPL-03 (record vs evidence scatter) | 32 logos; dek names the over- and under-performers; OLS line and mood bands visible in the screenshots; no "luck" in page text (also covered by noLuck.test.ts) |
| DATA-03 (preseason win totals display) | BUF 2026 opening-line suffix; 2023 "display only, not used in score" plus the model row; 2015 "used in score" plus the normalized note; 2000 "No Vegas line on file before 2003"; `team-2026-1280-light.png`, `team-2023-375-light.png`, `team-2015-1280-dark.png`; golden pin green |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The first touch tap on a scatter logo was lost**
- **Found during:** Task 2. The touch check failed on rerun; it had passed once by timing luck.
- **Issue:** Plot sets `svg.value` inside a `requestAnimationFrame` after the pointer event. With no prior hover, the value was still null when `click` fired. The first tap was dropped, so a phone needed three taps instead of two.
- **Fix:** `attachClick` now runs its tapAction decision inside `requestAnimationFrame`.
- **Files:** web/src/lib/scatterMarks.ts. **Commit:** 1d4cb57

**2. [Rule 1 - Bug] The OLS label "Typical score for this record" was hidden under logos**
- **Found during:** Task 2 screenshot review. The label sits at the top-right end of the line, where the best teams cluster, and it was drawn before the logos.
- **Fix:** The label is pushed after the logo marks with a `var(--bg)` stroke halo (`paintOrder: stroke`).
- **Files:** web/src/components/RecordScatter.svelte. **Commit:** 1d4cb57

**3. [Rule 1 - Spec gap from 13-06] ChartFrame showed its footer while a chart was loading**
- **Fix:** New `footer` prop (default true). Explore loading frames pass `footer={false}`. Added an SSR test.
- **Files:** ChartFrame.svelte, ExplorePage.svelte, chartFrame.test.ts. **Commit:** 1d4cb57

**4. [Rule 3] Shrank the screenshots** from 1.5 MB to 724 KB using Pillow 128-color quantization, to keep repo growth small. pngquant isn't installed.

## Visual review notes

- In dark mode the logos sit on light discs and stay legible. The crosshairs and diagonals are faint, and the quadrant and zone labels clear the axes.
- The win-totals markers sit on the number line. The records rows are full width (960px).
- At 375 the EPA scatter is dense in the middle cluster, but nothing clips or causes horizontal scroll. The table view is the accessible fallback.

## Still deferred (Phase 12 UI review)

- #5: saddest/happiest lead on the board
- #6: unbalanced team page, beyond the win-totals placement into the right column, which helps at wide widths (see `team-2015-1280-dark.png`)
- #10: callout count at 375
- #11: methodology table

## Human verification (manual only)

- On a real phone, open `#/explore` and tap a logo. The first tap should show the tip without navigating, and a second tap on the same logo should open the team page. Chromium touch emulation passes this; real hardware has not been checked.

## Commits

- ca46048 docs(13-07): README status line for Explore page and win totals
- 1d4cb57 fix(13-07): touch double-tap, OLS label legibility, no footer while loading
- b851c72 test(13-07): Phase 13 Playwright sweep, 6 screenshots, validation sign-off

## Self-Check: PASSED
- verify_ui.py, 6 PNGs, and 13-VALIDATION.md (nyquist_compliant: true) exist.
- Commits ca46048, 1d4cb57, and b851c72 are present in git log.

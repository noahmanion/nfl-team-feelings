---
phase: 13-explore-charts-win-totals-display
plan: 05
subsystem: web
tags: [explore, observable-plot, svelte, scatter, logos]
requires: ["13-02"]
provides: [EpaScatter, RecordScatter, logoMarks, attachClick]
affects: ["13-06", "13-07"]
tech-stack:
  added: []
  patterns: ["Plot.image logo marks with pinned-last draw order", "plot.value + tapAction touch arming for click-through", "explicit scale domains + inset for edge logos"]
key-files:
  created:
    - web/src/lib/scatterMarks.ts
    - web/src/components/EpaScatter.svelte
    - web/src/components/RecordScatter.svelte
  modified: []
decisions:
  - "Record chart mood-band rects omit the x channel so they span the full frame (including the logo inset) rather than stopping at x 0..1"
  - "Band labels anchor with frameAnchor 'right' + dx 10 so they sit in the gutter regardless of the x inset"
  - "EPA domains include the league means so the crosshairs always fall inside the frame"
metrics:
  duration: "~6 min"
  completed: 2026-11-11
  tasks: 2
  files: 3
---

# Phase 13 Plan 05: Explore scatters Summary

Two Observable Plot scatters for the Explore page: offense vs defense EPA (reversed y, clipped 0.1 net diagonals, dashed league crosshairs, quadrant labels) and win % vs feel-good score (mood bands, dashed OLS "typical" segment, better/worse zone labels). Both use shared logo marks (pin ring + 0.5 dimming, dark disc, logos-off dot + era abbreviation) and a shared click helper with touch arming via `tapAction`.

## Tasks

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Shared logo marks + click helper, EpaScatter | b60c08a | web/src/lib/scatterMarks.ts, web/src/components/EpaScatter.svelte |
| 2 | RecordScatter | cb5eff3 | web/src/components/RecordScatter.svelte |

## Verification

- `npm run check`: 0 errors, 0 warnings
- `npm test`: 266/266 pass
- `npm run build`: succeeds
- Acceptance greps: `reverse: true`, `clip: true`, single `Plot.tip`, `attachClick`, `tapAction(`, `d.src`, the record copy strings and `domain: [0, 100]` are all present. No "luck" and no `http` in these files.
- Rendering and interaction are checked in plan 07, after plan 06 mounts the components.

## Deviations from Plan

None. The plan executed as written. The small layout choices are listed under decisions in the frontmatter.

## Known Stubs

None. The components are presentational, and plan 06 supplies their data.

## Self-Check: PASSED

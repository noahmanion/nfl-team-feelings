---
phase: 12-redesign-foundation-team-identity
plan: 03
subsystem: web
tags: [charts, observable-plot, theme, components]
requires: []
provides:
  - plotTheme.ts (CHART_FONT_PX, LABEL_FONT_PX, HIGHLIGHT_WIDTH, BACKGROUND_STROKE, GRID_STROKE, LOGO_MARK_PX, themeStyle, teamStroke, valueAxis, baseAxis, withTheme)
  - ChartFrame.svelte (HTML headline/dek/body/SOURCE-NOTES footer, figure aria-labelledby heading)
affects: [wave 2 migration of HistoryChart, MethodologyChart, Sparkline, FactorBars]
tech-stack:
  added: []
  patterns: ["withTheme shallow style merge, caller wins", "createRawSnippet children in SSR render tests"]
key-files:
  created:
    - web/src/lib/plotTheme.ts
    - web/src/lib/plotTheme.test.ts
    - web/src/components/ChartFrame.svelte
    - web/src/lib/chartFrame.test.ts
  modified: []
decisions:
  - "withTheme tests cast out.style to Record<string,string>: T is inferred from the input, so merged theme keys are runtime-only (svelte-check would otherwise fail)"
  - "createRawSnippet works under svelte/server SSR; no ChartFrameProbe fixture needed"
metrics:
  duration: ~3min
  completed: 2026-11-11
  tasks: 2
  files: 4
requirements: [DESIGN-02]
---

# Phase 12 Plan 03: Chart Theme and Frame Summary

The shared Observable Plot theme module and the ChartFrame wrapper are both unit tested. Wave 2 charts can now migrate onto them. The theme module sets mono 12px muted text, a transparent background, grid on the value axis only, no ticks and no domain lines. ChartFrame renders an HTML headline, a dek and a mono "SOURCE: NFLVERSE · FEEL-GOOD SCORE" footer.

## Tasks

| Task | Name | Commits | Files |
|------|------|---------|-------|
| 1 | plotTheme.ts shared chart theme | 8b8ee83 (RED), 146e7f4 (GREEN) | web/src/lib/plotTheme.ts, plotTheme.test.ts |
| 2 | ChartFrame.svelte with SSR tests | 2129c69 (RED), d20a2ed (GREEN) | web/src/components/ChartFrame.svelte, web/src/lib/chartFrame.test.ts |

## Verification

- `npx vitest run src/lib/plotTheme.test.ts src/lib/chartFrame.test.ts src/lib/sep.test.ts`: all pass (8 + 3 + 4 tests)
- Full `npm test`: 19 files, 206 tests pass. `npm run check`: 0 errors, 0 warnings
- Acceptance greps: 11 theme exports, 0 svelte imports in plotTheme.ts; ChartFrame has 1 SOURCE literal, 1 svelte:element, 1 aria-labelledby, 0 box-shadow/border-radius

## Deviations from Plan

**1. [Rule 3 - Blocking] Test typing for withTheme merged style**
- **Found during:** Task 1 (`npm run check`)
- **Issue:** `out.style.fontFamily` was a TS error because T is inferred as `{ style: { fontSize: string } }`
- **Fix:** The test casts `out.style` to `Record<string, string>`. The runtime assertions are unchanged.
- **Commit:** 146e7f4

**2. [Rule 2 - Spec fidelity] Dek line-height**
- Added `line-height: var(--lh-body)` to `.cf-dek`. The UI-SPEC anatomy specifies 16px/1.5, but the plan's style list left the line-height out.

## TDD Gate Compliance

Both tasks have a `test(...)` RED commit followed by a `feat(...)` GREEN commit. No refactor was needed.

## Known Stubs

None.

## Self-Check: PASSED

- All 4 created files exist; commits 8b8ee83, 146e7f4, 2129c69, d20a2ed are present in git log

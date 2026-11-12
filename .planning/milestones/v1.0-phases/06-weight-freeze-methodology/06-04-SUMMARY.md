---
phase: 06-weight-freeze-methodology
plan: 04
subsystem: pipeline-export + web
tags: [methodology, site-07, model-15, plot, export]
requires: [06-02]
provides: [methodology.json, "#/methodology page"]
affects: [06-05 (re-export picks up HOLDOUT_RESULT.json automatically)]
tech-stack:
  added: []
  patterns: [evidence-file templated notes, Plot faceted dot-and-whisker, per-generated_at cached loader]
key-files:
  created:
    - pipeline/src/fgs/methodology.py
    - pipeline/tests/test_methodology.py
    - web/src/lib/methodology.ts
    - web/src/lib/methodology.test.ts
    - web/src/components/MethodologyChart.svelte
    - web/src/components/MethodologyPage.svelte
    - web/public/data/methodology.json
  modified:
    - pipeline/src/fgs/export.py
    - pipeline/tests/test_export.py
    - pipeline/tests/test_leakage.py
    - web/src/lib/router.ts
    - web/src/lib/router.test.ts
    - web/src/lib/types.ts
    - web/src/lib/data.ts
    - web/src/components/SiteHeader.svelte
    - web/src/App.svelte
    - web/public/data/meta.json
decisions:
  - "methodology.json is built inside build_export from committed weights.yaml + FREEZE_RESULT.json + optional HOLDOUT_RESULT.json; never runs a backtest"
  - "Note text uses Unicode minus and is formatted only from each note's values (2 dp weights, 4 dp metrics/deltas, k of n folds)"
  - "Momentum note wording derives from the rounded weight signs (negative / about zero / positive), never hard-coded"
  - "Chart axis label rendered as an HTML figcaption (not a Plot axis label) so it wraps at 375px; facet titles drawn as a text mark above each facet"
metrics:
  duration: ~25min
  completed: 2026-11-11
  tasks: 3
  files: 19
---

# Phase 6 Plan 04: Methodology page Summary

`methodology.json` is now built in `build_export` from the committed freeze evidence. It shows 11 factors with signed weights, fold signs and deltas, the walk-forward 2003–21 metrics, and `holdout: null` plus a pending note. The data feeds a new `#/methodology` page ("How it works" in the nav), which has a factor table, Plot dot-and-whisker charts (Spearman N=8 and Brier with the Vegas spread ceiling), a numeric fallback table, and honest notes templated from the evidence.

## Tasks

| # | Task | Commit |
|---|------|--------|
| 1 | methodology.py + export wiring + tests | a3458a7 |
| 1b | regenerate site data (methodology.json, holdout null) | 9b65f8c |
| 2 | route, types, loader, formatting helpers (vitest) | 3f6c11d |
| 3 | MethodologyPage + MethodologyChart, nav, App wiring | 128b419 |

## Verification

- Pipeline: full `uv run pytest -q` passed (354 tests), including the new `test_methodology.py` (10 tests) and `test_contract_methodology`. That test checks that the factor keys and weights in methodology.json, meta.json and weights.yaml all match.
- `web/public/data/methodology.json`: 11 factors, non-null walk_forward, `holdout: null`.
- Web: vitest 79/79 passed, svelte-check reported 0 errors and the build passed.
- Browser check used headless Chromium against the dev server on :5199, at 375×812 and 1280×900:
  - no horizontal scroll at either width (scrollWidth equals innerWidth)
  - the nav stays on one line, and "How it works" is the only link with `aria-current="page"`
  - the holdout-pending sentence is shown
  - all four h2 sections and both chart SVGs render, with no console errors
  - whiskers and dots line up on their rows
- No raw hex in Methodology*.svelte. methodology.py has no harness imports; the leakage test now also guards `bootstrap`.
- Holdout discipline: no `fgs holdout` run, nothing computed on 2022–2025, no HOLDOUT_RESULT file written. The holdout path is tested only with a synthetic dict of made-up numbers.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Wrapped chart labels overlapped at 375px**
- **Found during:** Task 3 screenshot check
- **Issue:** At 375px, "Point differential" and "Feel-good score" wrap onto two lines inside the 120px margin, and with 28px rows the two labels overlapped.
- **Fix:** Rows are now 40px tall below 500px (30px otherwise). Candidate names wrap with `Plot.axisY({lineWidth})`.
- **Files:** web/src/components/MethodologyChart.svelte. **Commit:** 128b419

**2. Plan-text adjustments (no behavior change)**
- The nav separator uses the shared `<Sep />` instead of a hand-rolled `<span class="sep">`. The orchestrator asked for this, and sep.test.ts guards it.
- Added a `refit_vs_frozen` and `not_betting` value set, with walk-forward Brier spread vs composite numbers, so those notes are evidence-backed too.
- Added a walk-forward sentence with no decimals: "ranked teams better than Elo alone in 14 of 19 seasons", taken from `diff.spearman_n8.seasons_won/of`.

### TDD note
Tasks 1 and 2 were written test and implementation together, then run green. There are no separate RED commits.

## Known Stubs
None. `holdout: null` is intentional until 06-05 runs `fgs holdout` and re-exports; the page then picks it up with no code change.

## Self-Check: PASSED
- Files exist: methodology.py, test_methodology.py, methodology.ts, methodology.test.ts, MethodologyChart.svelte, MethodologyPage.svelte, web/public/data/methodology.json
- Commits exist: a3458a7, 9b65f8c, 3f6c11d, 128b419

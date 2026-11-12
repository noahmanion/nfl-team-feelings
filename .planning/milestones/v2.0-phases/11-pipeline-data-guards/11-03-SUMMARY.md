---
phase: 11-pipeline-data-guards
plan: 03
subsystem: pipeline-export + web-data
tags: [epa, export, web, EXPL-01]
requires: ["11-02"]
provides: ["epa/{season}.json", "meta.epa_seasons", "meta.teams[].conf/division", "loadEpa", "seasonToDate"]
affects: ["phase 13 explore charts"]
tech-stack:
  added: []
  patterns: ["columnar per-season JSON + client-side play-weighted aggregation", "generated_at|season promise cache evicted on rejection"]
key-files:
  created: [web/src/lib/epa.ts, web/src/lib/epa.test.ts]
  modified: [pipeline/src/fgs/export.py, pipeline/tests/test_export.py, web/src/lib/types.ts, web/src/lib/data.ts]
decisions:
  - "def_sr is the opponent's off_sr in the same game (consistent with def_epa/def_plays scrimmage filter)"
  - "conf/division are current alignment, not era-correct; optional on TeamMeta"
  - "seasonToDate skips zero-play rows from the weighted sums and returns null means when the weight sum is 0"
requirements: [EXPL-01]
metrics:
  duration: ~20min
  completed: 2026-11-11
---

# Phase 11 Plan 03: EPA export + web season-to-date helper Summary

Per-team-game EPA files (`epa/{season}.json`: off/def EPA/play, success rate, play counts, def_sr = opponent off_sr, 4 dp, no -0.0), `meta.epa_seasons`, conf/division in team meta, plus a cached `loadEpa` and a play-weighted `seasonToDate(file, week)` helper in the web app. No UI.

## Tasks

| # | Name | Commit |
|---|------|--------|
| 1 | Export epa files, epa_seasons, conf/division + 4 tests | ac4e8f7 |
| 2 | Web EpaFile type, loadEpa, lib/epa.ts + 5 tests | 264d8fb |

## Verification

- `uv run pytest -q`: 624 passed (golden included); `-k "epa or meta"`: 6 passed
- web: `npm test` 163 passed (12 files), `npm run check` 0 errors / 0 warnings, `npm run build` ok
- No fingerprinted files, pbp.py, win_totals_2021plus.csv, PREREGISTRATION*.md or weights.yaml touched; `fgs evidence`/`refresh` not run

## Deviations from Plan

- Plan text suggested committing Task 1 + Task 2 together; committed each task separately per the executor's atomic-commit rule. No code deviation.
- `test_no_pbp_no_epa_files` reuses the existing synthetic `_draft_export` helper (derive_games without pbp) rather than a new fixture.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: web/src/lib/epa.ts, web/src/lib/epa.test.ts
- FOUND commits: ac4e8f7, 264d8fb

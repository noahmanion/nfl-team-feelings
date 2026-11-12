---
phase: 13-explore-charts-win-totals-display
plan: 01
subsystem: pipeline-export
tags: [export, data, expectation, display-only, DATA-03]
requires: [scored frame exp_total/expectation_source, season_config.EXPECTED_GAME_EXCEPTIONS]
provides: ["teams/{F}.json expectation block {season, exp_total, source, reg_games}"]
affects: [web/public/data/teams/*.json, phase 13 win-totals display plans]
tech-stack:
  added: []
  patterns: ["display-only columnar block per team file (same shape as vegas_win_totals)"]
key-files:
  created: []
  modified:
    - pipeline/src/fgs/export.py
    - pipeline/tests/test_export.py
    - web/public/data/teams/*.json (32)
    - web/public/data/meta.json
    - web/public/data/records.json
    - web/public/data/callouts.json
    - web/public/data/snapshots/2026.json
decisions:
  - "expectation block is display-only: built from week-0 rows of the scored frame, never read back into the score"
  - "reg_games uses EXPECTED_GAME_EXCEPTIONS keyed (season, fid), falling back to season_config.reg_games"
metrics:
  duration: ~12m
  completed: 2026-11-12
  tasks: 2
  files: 38
---

# Phase 13 Plan 01: Display-only expectation block Summary

Each `teams/{F}.json` now has an `expectation` block with one entry per team-season: `season`, `exp_total` (week-0 preseason expectation, 1 dp), `source` ('vegas' for 2003–2020, 'model' otherwise) and `reg_games` (16 through 2020, 17 from 2021, 16 for BUF/CIN 2022). The site data was regenerated from cache, and the golden pin did not change.

## Tasks

| Task | Name | Commit |
|------|------|--------|
| 1 (RED) | Failing tests for expectation block | 7791795 |
| 1 (GREEN) | `EXPECTATION_KEYS` + `_expectation(scored, fid)` wired into team files | 495c3a8 |
| 2 | Regenerate `web/public/data` from cache | 381edb5 |

## Verification

- Golden (`tests/test_golden_scores.py`): before regeneration 2 passed; after 2 passed (pin `3ac3c2b5…9472` unchanged, not edited).
- `uv run fgs export`: 122 files, latest 2026 week 9, records hand-check unchanged.
- `git diff --stat -- web/public/data`: 36 files, 36 insertions / 36 deletions. 32 team files, plus meta.json (`generated_at`), records.json (`as_of` 2026-11-11 → 2026-11-12), and callouts.json and snapshots/2026.json (active streak day counts +1). No snapshot for 2025 or earlier changed. latest.json was unchanged.
- 32/32 team files contain `"expectation"`. BUF 2022 reg_games = 16, BUF 2015 source = "vegas".
- Full `uv run pytest -q`: 642 passed, 0 failed.
- No changes to pipeline model code, `pipeline/inputs/` or PREREGISTRATION files. Only export.py and test_export.py changed under `pipeline/`.

## Deviations from Plan

**1. [Rule 1 - Bug in test assumption] The synthetic export does produce exp_total**
- **Found during:** Task 1 GREEN
- **Issue:** The plan and research expected `exp_total` to be all None in the synthetic `_draft_export` frame. In fact the synthetic derive computes a model expectation (e.g. BUF `[2.5, 2.6]`, source 'model').
- **Fix:** `test_expectation_shape_without_sim` now checks shape, seasons [2023, 2024], source all 'model', and values at 1 dp. I added `test_expectation_nulls_without_columns`, which calls `_expectation` directly on a frame without the columns and checks for nulls and correct reg_games (BUF 2022 = 16).
- **Commit:** 495c3a8

## TDD Gate Compliance

RED `test(13-01)` 7791795 comes before GREEN `feat(13-01)` 495c3a8. No refactor was needed.

## Self-Check: PASSED
- pipeline/src/fgs/export.py contains `def _expectation` and `"expectation": _expectation(scored, fid)`
- Commits 7791795, 495c3a8, 381edb5 exist

---
phase: 04-game-result-factors-team-deep-dive
plan: 01
subsystem: pipeline/export
tags: [attribution, blurb, export, leakage]
requires: [phase-03 export contract, mood.score_frame]
provides: [fgs.explain, mood.reference_values, row.points, row.blurb, meta.baseline, games/{season}.json]
affects: [04-02 team page, 04-03/04-04 factor plans]
tech-stack:
  added: []
  patterns: [smoothed frozen percentile map + largest-remainder integer reconciliation, deterministic phrasebook keyed on raw direction]
key-files:
  created:
    - pipeline/src/fgs/explain.py
    - pipeline/tests/test_explain.py
    - web/public/data/games/*.json (28 files)
  modified:
    - pipeline/src/fgs/mood.py
    - pipeline/src/fgs/export.py
    - pipeline/tests/test_export.py
    - pipeline/tests/test_leakage.py
    - web/public/data/** (regenerated)
decisions:
  - "Points use the smoothed (101-knot) frozen-reference map for the slope; integers are reconciled by largest remainder so sum(points) == score - baseline exactly"
  - "meta.baseline = score(0) on the frozen reference; with the current 3 factors it is 49"
  - "games/{season}.json includes asof_week and neutral; unplayed games are forced to null scores via the played flag"
metrics:
  duration: ~15m
  completed: 2026-11-11
  tasks: 2
  files: 7 source/test + regenerated data
---

# Phase 4 Plan 01: Points attribution, blurbs and games export Summary

Every exported snapshot row now has integer score-point attribution (`points`, which sums exactly to score − `meta.baseline`) and a deterministic plain-English `blurb`. Each season also has a columnar `games/{season}.json`. All of it comes from a new pure module, `fgs/explain.py`, which is generic over factor keys.

## What was built

- **`mood.reference_values()`**: the frozen 1999–2021 week-0+REG reference, pulled out of `score_frame`, which now calls it. Behaviour is unchanged and all 42 mood tests pass.
- **`fgs/explain.py`**:
  - `smooth_map`, `slope` (vectorized; at |c| < 1e-6 it uses the derivative at 0 and steps outward past coincident knots), `largest_remainder` (exact sum, stable ties, with a final safety correction), `baseline`, `add_points` (Int64 `pts_*` built from the unrounded contribs).
  - `PHRASES` covers all 7 planned factors (14 entries), plus `FADE`, tiered strength (Elo ≥ 20, others ≥ 10) and `blurb()`.
- **Export**:
  - Each row gains `points` and `blurb`, and `meta.json` gains `baseline` (49).
  - New `games/{season}.json` per season, with fields season, week, asof_week, home, away, home_score, away_score, game_type, gameday, neutral. `latest.json` picks up the new row fields automatically.
- **Tests**:
  - `test_explain.py` (35 cases).
  - `test_export.py`: ROW/META keys, games seasons, plus `test_points_sum_to_score`, `test_blurbs` and `test_games_files` over all real rows.
  - `test_leakage.py`: FLOAT_EXACT is now derived from `features.FEATURE_COLUMNS`, the pipeline adds points, every `pts_*` column is compared exactly, and `explain.py` is in the firewall tuple.
- **Site data regenerated**: 92 files, 28 games files (matching the 28 snapshot files), `games/2026.json` at 13.5 KB raw.

Sample (2026 week 9, #1 BUF): points `{elo: 55, season_record: 7, last16: -14}`, blurb: "The Bills are one of the best teams in football, but have won a lot over their last 16 games (that tends to fade)."

## Verification

- `uv run pytest -q`: 210 passed (all real-cache tests ran, none skipped)
- latest.json: sum(points) == score − baseline for every row, and baseline is an int
- The web vitest suite still passes (44) against the regenerated data

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | e670fec | explain module, mood.reference_values, test_explain |
| 2 | 4a7d16c | export points/blurb/baseline/games, contract + leakage tests |
| 2 | 87f4783 | regenerated web/public/data |

## Deviations from Plan

Two small hardening additions, not behaviour changes:
- `largest_remainder` clamps k and applies a final residual correction to the largest-|real| factor, so float noise can never ship a row that doesn't sum.
- `_games_file` nulls the scores of unplayed games using `played`, and fills null `neutral` with False, so the "home_score None iff away_score None" contract holds no matter how the source encodes things.

## Known Stubs

None.

## Self-Check: PASSED
- FOUND: pipeline/src/fgs/explain.py, pipeline/tests/test_explain.py, web/public/data/games/2026.json
- FOUND commits: e670fec, 4a7d16c, 87f4783

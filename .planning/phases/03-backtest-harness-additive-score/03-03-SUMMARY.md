---
phase: 03-backtest-harness-additive-score
plan: 03
subsystem: pipeline/score-export
tags: [composite, percentile, leakage, json-contract]
requires: [03-01, 03-02]
provides:
  - "derive/derive_games -> features frame with composite + contrib_*"
  - "score_frame(df, value='composite', ref_seasons=REF_SEASONS) frozen reference"
  - "meta.score_kind composite, meta.factors, rows.contribs"
  - "BACK-03 leakage tests"
affects: [web/public/data, README.md]
tech-stack:
  added: []
  patterns: ["frozen percentile reference read at call time", "production-path leakage test"]
key-files:
  created:
    - pipeline/tests/test_leakage.py
  modified:
    - pipeline/src/fgs/mood.py
    - pipeline/src/fgs/cli.py
    - pipeline/src/fgs/export.py
    - pipeline/tests/test_mood.py
    - pipeline/tests/test_cli.py
    - pipeline/tests/test_export.py
    - web/public/data/**
    - README.md
decisions:
  - "Leakage tests treat 'the future' as weeks after the latest week with any played game, so a mid-week cache refresh never trips them"
  - "Partial-week export test no longer expects score_delta 0 for idle teams: composite z-scores are relative to the whole week"
metrics:
  duration: ~20min
  completed: 2026-11-11
  tasks: 2
  files: 8 (+ regenerated web data)
---

# Phase 3 Plan 03: Composite on the Mood Board Summary

The board's score, rank and label now come from the weighted composite (4.58·z_elo + 0.63·z_season_record − 1.25·z_last16). Percentiles use a frozen 1999–2021 week-0 + REG reference, and a leakage test shows future games cannot move any past snapshot.

## What was done

**Task 1 (0910825):**
- `derive_games(games, params, weights)` runs replay → team_games → grid → `build_features` → `score.composite`. `derive(raw, ...)` wraps it.
- `features.parquet` is written next to the existing parquet files.
- `score_frame(df, value="composite", ref_seasons=None)` reads `REF_SEASONS` at call time, raises on an empty reference, and ranks by the value (ties broken by franchise).
- Added `tests/test_leakage.py`:
  - fake future: every unplayed game after the latest played week becomes a 60-0 home win
  - truncation: weeks after W−2 are un-played
  - synthetic case with an explicit weights dict and the reference patched to 2023
  - import firewall
- Leak-detection check: the fake-future test was run in a scratchpad copy with `REF_SEASONS` forced to (1999, 2026). It failed, with `score` changed in 5661 rows. Run normally, it passes.

**Task 2 (5ca37e5, 10d025c, 8b2591c):**
- The export now emits `score_kind: "composite"`, plus `factors` (key, label, weight, description, in weights.yaml order).
- Every row now has `contribs` (2 dp). `allow_nan=False` is set on the JSON writer.
- Site data was regenerated: 64 files, latest is 2026 week 9.
- README updated: factors, weights, why last16 is negative, the fixed reference, and `fgs backtest` / `--propose-weights` / `--include-holdout`. Status is Phase 3 done.

## Verification

- `uv run pytest -q`: 169 passed, 0 skipped.
- meta.json contains `"score_kind":"composite"` and 3 factors.
- Every latest row has contribs {elo, season_record, last16}.
- history.json keys are exactly ["keys", "teams"].
- Web: `npm test` (43 passed), `npm run check` (0 errors) and `npm run build` all pass on the new data.

## Deviations from Plan

**1. [Rule 3 - Blocking] export switched to `score_frame(derived["features"])` in Task 1**
- The new default `value="composite"` broke export, and so `test_cli` refresh, until the export used the features frame. This one-line change moved from Task 2 into the Task 1 commit.

**2. [Rule 1 - Bug in test expectation] test_partial_next_week_one_game_played**
- The test asserted `score_delta == 0` for teams that had not played yet. Composite z-scores are relative to every team that week, so another team's game shifts everyone slightly.
- It now asserts unchanged Elo and W-L-T instead (commit 0910825).

**3. Orchestrator note applied:** both leakage real-cache tests only modify games after the latest week with any played game (truncation: after W−2). They also compare only rows that exist in both frames. They stay green when the cache is refreshed mid-week.

**4. Synthetic leakage fixture:** the conftest's unplayed 2024 game is in week 2, which is partly played. The test moves it to week 3 so it is genuinely in the future. Filling it in week 2 would legitimately change the week-2 snapshot.

**5. Rank-vs-contrib test:** consecutive rounded sums may break order by at most 3 × 0.005 (rounding tolerance). The plan's strict "equal to 2dp" rule would fail on rounding alone.

## Known Stubs

None.

## Self-Check: PASSED
- pipeline/tests/test_leakage.py exists; commits 0910825, 5ca37e5, 10d025c, 8b2591c in git log.

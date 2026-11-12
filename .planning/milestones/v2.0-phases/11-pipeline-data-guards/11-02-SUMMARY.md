---
phase: 11-pipeline-data-guards
plan: 02
subsystem: pipeline
tags: [win-totals, vegas, display-only, guards, export, DATA-02]
requires: ["11-01"]
provides:
  - "Write-once sourced 2021-2025 win totals (A3.4 pin) + 2026 display file"
  - "fgs.wintotals validator/loader/display_frame (not fingerprinted)"
  - "cli._cached_vegas <=2020 ValueError guard"
  - "teams/{F}.json vegas_win_totals on export and refresh paths"
affects: [pipeline/src/fgs/cli.py, pipeline/src/fgs/export.py, pipeline/src/fgs/paths.py]
tech-stack:
  added: []
  patterns: ["display-only inputs wired around derive(): cli helper -> build_export(win_totals=) -> team file only"]
key-files:
  created:
    - pipeline/inputs/win_totals_2021plus.csv
    - pipeline/inputs/win_totals_display_2026plus.csv
    - pipeline/src/fgs/wintotals.py
    - pipeline/tests/test_wintotals.py
  modified:
    - pipeline/src/fgs/paths.py
    - pipeline/src/fgs/cli.py
    - pipeline/src/fgs/export.py
    - pipeline/tests/test_export.py
    - pipeline/tests/test_cli.py
decisions:
  - "A3.4 pin: pipeline/inputs/win_totals_2021plus.csv sha256 338450a3c70cc47b6ec4379dc6d72b0fe343a8a2737b2666e1535a8fc9995449, single commit a3135cb"
  - "Sourced CSVs keep their CRLF line endings byte-for-byte (no .gitattributes / autocrlf in repo, committed blob verified identical)"
  - "export.py does not import wintotals; cli.py is the only importer (guard c allows cli.py + export.py)"
  - "Fingerprinted code untouched: code_fingerprint stays 07c33dd92639, matching callout_evidence.json"
metrics:
  duration: "~20 min"
  completed: 2026-11-12
  tasks: 3
  files: 9
---

# Phase 11 Plan 02: Display-only 2021+ Vegas Win Totals Summary

This plan adds the 2021-2026 Vegas preseason win totals as committed, sourced, validated inputs. They are display-only, and guards prove they cannot reach `vegas_expectations`, `vs_exp` or the score. Every team file now carries `vegas_win_totals`: the 2003-2020 nflverse lines with `used_in_score=true`, and the 2021-2026 lines with `used_in_score=false`.

## A3.4 pin

| Item | Value |
|------|-------|
| File | `pipeline/inputs/win_totals_2021plus.csv` (161 lines, seasons 2021-2025, CRLF) |
| sha256 | `338450a3c70cc47b6ec4379dc6d72b0fe343a8a2737b2666e1535a8fc9995449` |
| Single commit | `a3135cb` (touches only this file) |
| Byte-identical to | `.planning/phases/11-pipeline-data-guards/sources/win_totals_2021_2025.sourced.csv` (checked with cmp, on both the working file and the committed blob) |

## Tasks

| # | Task | Commit |
|---|------|--------|
| 1 | Commit the 2021-2025 file alone, byte-for-byte | a3135cb |
| 2 | 2026 display file, `INPUTS_DIR`, `wintotals.py` validator, `_cached_vegas` guard, guard tests | ee3fd10 (combined with Task 3, per the plan) |
| 3 | `build_export(win_totals=)` and `vegas_win_totals` on the export and refresh paths | ee3fd10 |

## What was built

- **`wintotals.validate`** reads an all-string frame and checks: exact column order, the season range for each file, 32 canonical teams per season, no duplicates, positive half-point lines, season sum within `reg_games*16 ± 8`, absolute `https` sources, odds that are an integer or empty, and a known `line_type`. It returns a typed frame. It raises `ValueError` naming the file, row or season.
- **`load_display_win_totals()`** returns 192 rows, 2021-2026, 32 per season.
- **`display_frame(nflverse_raw, display)`** maps nflverse 2003-2020 rows through `RAW_TO_FRANCHISE` (OAK->LV and so on) with `line_type="nflverse"`, `source=expectation.WIN_TOTALS_URL` and `used_in_score=True`. The 2021+ rows get `used_in_score=False`. It raises if the two overlap.
- **`cli._cached_vegas`** raises `ValueError` if the frame has a season after 2020.
- **`cli._display_win_totals(cache_dir)`** is shared by `_cmd_export` and `_cmd_refresh` (2 call sites with `win_totals=`).
- **`export._vegas_win_totals`** produces a columnar dict with the keys season, line, over_odds, under_odds, line_type, source and used_in_score. The lists are empty when `win_totals` is None.

## Tests

- `tests/test_wintotals.py`: 29 tests. Six are guards: (a) the real cache stops at 2020, (a2) a post-2020 row is refused, (b) score-path source scan, (c) importer regex, not fingerprinted, and (d) the file has a single git commit. All ran with no skips.
- `tests/test_export.py`: `test_vegas_win_totals_empty_without_frame` (synthetic) and `test_vegas_win_totals_real`. The real test checks all 32 teams for 2003-2026, LV 2003-2019 equal to raw OAK, and KC lines equal to `derived["vegas"]`.
- `tests/test_cli.py`: the refresh happy path asserts that KC's team file has 2021 with `used_in_score` false, plus 2026.
- Full suite: **620 passed** in 146s, golden test included.

## Deviations from Plan

None in behavior. Two minor notes:
- `test_guard_wintotals_importers` failed briefly between Task 2 and Task 3, because cli.py didn't import wintotals yet. The plan commits Tasks 2 and 3 together, so no red state was committed.
- The `real_files` fixture in test_export.py now passes `win_totals=cli._display_win_totals(CACHE_DIR)`, the same way the CLI does, so the real contract tests exercise the populated field.

## Known Stubs

None.

## Threat Flags

None. No new network access: the display inputs are local committed files, and the nflverse file is still read from the existing cache.

## Self-Check: PASSED

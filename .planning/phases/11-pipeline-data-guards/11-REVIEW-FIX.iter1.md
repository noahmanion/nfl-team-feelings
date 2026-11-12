---
phase: 11-pipeline-data-guards
fixed_at: 2026-11-12T03:20:19Z
review_path: .planning/phases/11-pipeline-data-guards/11-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 11: Code Review Fix Report

**Fixed at:** 2026-11-12T03:20:19Z
**Source review:** .planning/phases/11-pipeline-data-guards/11-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (WR-01..WR-05; Info findings out of scope)
- Fixed: 5
- Skipped: 0

Verification after all fixes:
- `cd pipeline && uv run pytest -q`: 635 passed, including `tests/test_golden_scores.py`.
- `cd web && npm test && npm run check && npm run build` (Node 24): 167 tests passed, 0 svelte-check errors, build OK.

No fingerprinted code changed. `fingerprint.CODE_FILES`, `cli.derive_games` and `cli.draft_winsor` are untouched, so no `fgs evidence` rerun is needed. `inputs/win_totals_2021plus.csv`, `PREREGISTRATION*.md` and `weights.yaml` are untouched. The exported JSON shape didn't change: today's data has no null EPA sides, and play counts were already ints. So no re-export was needed.

## Fixed Issues

### WR-01: A display-only win-totals failure aborts the whole weekly refresh/export

**Files modified:** `pipeline/src/fgs/cli.py`, `pipeline/src/fgs/wintotals.py`, `pipeline/tests/test_wintotals.py`
**Commit:** 6cc2f91
**Applied fix:** `_display_win_totals` now catches `ValueError`, `OSError` and `PolarsError` from loading or merging the display-only files. It prints a WARNING on stderr and falls back to `display_frame(raw, wintotals.empty_display())`, so the nflverse 2003-2020 rows are still exported and only the 2021+ rows are dropped. Added `wintotals.VALIDATED_SCHEMA` and `empty_display()`. A new test breaks the input files and checks that a warning is printed and that the 2020 row survives. The tests on the committed files are unchanged and still enforce strict validation.

### WR-02: The `<=2020` guard hard-fails where it could safely filter

**Files modified:** `pipeline/src/fgs/cli.py`, `pipeline/tests/test_wintotals.py`
**Commit:** 03b65ad
**Applied fix:** `_cached_vegas` now filters the raw cached CSV to `season <= 2020` before `vegas_expectations`, and prints a stderr warning when rows are dropped. The `ValueError` stays as a post-condition on the filtered frame. `test_guard_cached_vegas_refuses_post_2020` is replaced by `test_guard_cached_vegas_drops_post_2020`. The new test checks three things:
- a 2021 row in the cached CSV is dropped and a warning is printed;
- the output max season is <= 2020;
- the output equals the frame built from the same file without the 2021 row.

`test_guard_cached_vegas_stops_at_2020` and the AST guards are unchanged.

### WR-03: The logo skip path writes the current URL into the manifest, not the URL the file was fetched from

**Files modified:** `pipeline/src/fgs/logos.py`, `pipeline/tests/test_logos.py`
**Commit:** 479f1cb
**Applied fix:** An existing PNG is now skipped only when its manifest entry records the current `logo_url(f)`. A changed URL or a missing entry triggers a re-fetch. In the new test, LA has a stale URL and WAS has no entry; only those two are re-fetched, and the other entries keep their original fetched date.

### WR-04: A mid-run download failure leaves the PNGs and `manifest.json` out of sync

**Files modified:** `pipeline/src/fgs/logos.py`, `pipeline/tests/test_logos.py`
**Commit:** bb5f4a2
**Applied fix:** Downloads are fetched and validated into an in-memory `staged` dict. The PNGs and then the manifest are written only after all 32 teams succeed. In the new test, a forced run fails on the 15th fetch after a full first run, and every file in the directory, manifest included, is byte-identical afterwards.

### WR-05: The `EpaFile` TypeScript contract says values are never null, but the export can emit `null`

**Files modified:** `pipeline/src/fgs/export.py`, `pipeline/tests/test_export.py`, `web/src/lib/types.ts`, `web/src/lib/epa.ts`, `web/src/lib/epa.test.ts`
**Commit:** ca1c84b
**Status:** fixed: requires human verification (this changes aggregation logic)
**Applied fix:** This uses the reviewer's option 2, with one change: the exporter now writes null play counts as `0`, so `off_plays` and `def_plays` are never null. The rates stay null for a side with no plays. Rows aren't dropped, so every game still appears twice. `EpaFile` now types the rate arrays as `(number | null)[]`. `seasonToDate` skips null rates and keeps a separate denominator for each rate, so a null success rate no longer drags the mean toward 0. Added a synthetic pytest case (one null offense side) and a vitest case (null `off_sr`/`def_sr` are skipped). The real-cache contract test still asserts that today's committed data has no nulls and positive play counts.

---

_Fixed: 2026-11-12T03:20:19Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

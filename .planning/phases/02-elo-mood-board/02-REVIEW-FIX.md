---
phase: 02-elo-mood-board
fixed_at: 2026-11-11T00:00:00Z
review_path: .planning/phases/02-elo-mood-board/02-REVIEW.md
iteration: 1
findings_in_scope: 7
fixed: 7
skipped: 0
status: all_fixed
---

# Phase 2: Code Review Fix Report

**Fixed at:** 2026-11-11
**Source review:** .planning/phases/02-elo-mood-board/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 7 (WR-01, WR-02, IN-02, IN-03, IN-04, IN-06 as requested, plus IN-01 because the fix was trivial)
- Fixed: 7
- Skipped: 0
- Out of scope: IN-05. It needs a JSON contract change (a new `week_ticks` field), so it isn't trivial.

**Verification after all fixes:**
- `cd pipeline && uv run pytest -q`: 128 passed.
- `uv run fgs export`: 64 files.
- `cd web && npm run test`: 28 passed.
- `npm run check`: 0 errors, 0 warnings.
- `npm run build`: OK.

## Fixed Issues

### WR-01: `fgs refresh` overwrites the raw schedule/team cache before checks run

**Files modified:** `pipeline/src/fgs/ingest.py`, `pipeline/src/fgs/cli.py`, `pipeline/tests/test_cli.py`
**Commit:** bc429b1
**Applied fix:**
- `load_schedules` and `load_teams` take a new `write_cache` parameter (default `True`).
- A new `save_cache(df, name, cache_dir)` writes `name.tmp` and then calls `os.replace`, so a crash can't leave a half-written cache file.
- `_cmd_refresh` downloads with `write_cache=False`, runs the checks and builds the export. Only after that does it save the raw cache, then the derived parquet, then the site JSON.
- The cache dir comes from `cli.CACHE_DIR`, so tests can monkeypatch it.
- The abort message is now "checks failed; cache and JSON not updated".
- The abort test seeds a temp cache dir with known bytes and asserts both files are byte-identical afterwards.
- The happy-path test asserts the loaders are called with `write_cache=False` and that the saved cache equals the downloaded frames.

### WR-02: Hysteresis is asymmetric: entering a band takes 3 points of overshoot, leaving takes 2

**Files modified:** `pipeline/src/fgs/mood.py`, `pipeline/tests/test_mood.py`, `README.md`, `web/public/data/**`
**Commits:** f31d895 (logic, tests, explanation), 3168ed8 (regenerated site data)
**Status:** fixed: requires human verification (logic change)
**Applied fix:** The rule is now symmetric. Scores are integers, so the edge between band k-1 and band k lies between T[k]-1 and T[k]. A label changes only once the score is at least `buf` scores into the new band, in either direction:
- **Up into band k:** `score >= T[k] + buf - 1`. With buf=2 and T=60, that is 61 or more.
- **Down out of band k:** `score <= T[k] - buf`. With buf=2 and T=60, that is 58 or less.

Scores of 59 and 60 keep whatever label the team already had. Multi-band jumps still go to the furthest band whose edge is cleared.

Tests:
- The parametrized cases were rewritten.
- `test_hysteresis_is_symmetric` checks every edge.
- `test_hysteresis_oscillation` covers 58↔61, which now follows the score both ways, and 59↔60, which holds either starting label.
- The week-0 freshness test now uses a score of 60, the only dead-zone score above T=60.

The docstring and the README "How the score works" bullet now state the rule precisely. Site data was regenerated because labels change. `meta.hysteresis` is still 2.

### IN-06: Hysteresis alignment depends on an implicit sort invariant

**Files modified:** `pipeline/src/fgs/mood.py`, `pipeline/tests/test_mood.py`
**Commit:** df3974b
**Applied fix:**
- Bands are now computed per `(franchise_id, season)` from week-sorted lists, exploded with their `week` key and joined back on `(franchise_id, season, week)` with `validate="1:1"`.
- Label and emoji are joined from a small band table.
- An assertion guards against missing bands.
- On the real snapshots, the output is identical to the old implementation. It is also identical when the input is shuffled.
- Added `test_score_frame_independent_of_input_order`.

### IN-03: `write_export` is not atomic

**Files modified:** `pipeline/src/fgs/export.py`, `pipeline/tests/test_export.py`
**Commit:** b66ba6c
**Applied fix:**
- All files are written into a sibling temp dir (`.data.new-*`, chmod 755). If anything fails, the temp dir is deleted and the old export is left untouched.
- The swap is two renames: the old dir goes to `.data.old-*`, then the new dir becomes `data`. If the second rename fails, the old dir is moved back. The old dir is deleted after a successful swap.
- `out_dir` is now fully owned by the export, which already matched practice.
- Added a test: a failure mid-write keeps the previous files and leaves no temp dirs behind, and a later export replaces the dir contents exactly.

### IN-04: The frontend derives the band from the label string and ignores `row.band`

**Files modified:** `web/src/lib/format.ts`, `web/src/lib/format.test.ts`, `web/src/components/BoardRow.svelte`
**Commit:** 84fdb0c
**Applied fix:**
- Replaced `bandIndexForLabel` with `bandIndex(band, bands)`. It returns `row.band` when that is an integer in `[0, bands.length)`, and -1 otherwise, which falls back to the `--border` stripe.
- `BoardRow` uses `row.band`.
- Tests cover out-of-range and malformed values.

### IN-02: Season change clamps the week by number, not by meaning

**Files modified:** `web/src/lib/format.ts`, `web/src/lib/format.test.ts`, `web/src/App.svelte`
**Commit:** 126bf9f
**Applied fix:** Added `carryWeek(week, fromSeason, toSeason)`:
- Preseason maps to 0.
- A regular week clamps to the new season's `reg_weeks`.
- A playoff round keeps its offset past `reg_weeks`: Super Bowl maps to Super Bowl, Wild Card to Wild Card.
- The result is then clamped to `max_week`, so an in-progress season lands on its latest week.

`onSeasonChange` now uses it. Tests cover 2010↔2021 in both directions, the 18→17 finale case, and an in-progress target season.

### IN-01: Stale-response guard misses the A→B→A path

**Files modified:** `web/src/App.svelte`
**Commit:** ec13b9b
**Applied fix:** The season-loading effect now sets `requestedSeason` before any early return: `null` for latest or no target, otherwise the target season. A pending fetch for B can no longer land after the user returns to A or to latest. There is no automated test; `svelte-check` passes.

---

_Fixed: 2026-11-11_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

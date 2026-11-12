---
phase: 02-elo-mood-board
reviewed: 2026-11-11T00:00:00Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - pipeline/src/fgs/mood.py
  - pipeline/src/fgs/export.py
  - pipeline/src/fgs/asof.py
  - pipeline/src/fgs/cli.py
  - pipeline/src/fgs/ingest.py
  - pipeline/src/fgs/paths.py
  - pipeline/tests/test_mood.py
  - pipeline/tests/test_export.py
  - pipeline/tests/test_cli.py
  - web/src/App.svelte
  - web/src/main.ts
  - web/src/lib/types.ts
  - web/src/lib/data.ts
  - web/src/lib/format.ts
  - web/src/lib/router.ts
  - web/src/lib/route.svelte.ts
  - web/src/components/Badge.svelte
  - web/src/components/BoardHeading.svelte
  - web/src/components/BoardRow.svelte
  - web/src/components/Delta.svelte
  - web/src/components/MoodBoard.svelte
  - web/src/components/MoodLabel.svelte
  - web/src/components/Scrubber.svelte
  - web/src/components/SiteFooter.svelte
  - web/src/components/SiteHeader.svelte
  - web/src/components/StatusPanel.svelte
  - web/src/components/TeamChip.svelte
findings:
  critical: 0
  warning: 2
  info: 6
  total: 8
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-11-11
**Depth:** standard
**Files Reviewed:** 27
**Status:** issues_found

## Summary

I reviewed the Phase 2 diff (`5ba36fb~1..HEAD`) across `pipeline/` and `web/src`. The focus was the areas the orchestrator asked about:
- percentile and hysteresis logic
- whether the export.py JSON contract matches `web/src/lib/types.ts`
- router edge cases
- stale responses in season loading
- the sign of `rank_delta`

**Verified correct:**
- **Percentile:** mid-rank `searchsorted` is correct. The reference set (week 0 plus REG rows) is correct, and so is the clip.
- **`band_of`:** correct at every boundary (0, 4, 5, 94, 95, 100).
- **Rank:** ranks come from Elo with ties broken by franchise id, and `int_range().over()` follows the frame's sort order.
- **`rank_delta`:** `prev − cur`, so positive means the team moved up. The site renders it as ▲. Signs agree end to end.
- **`score_delta` and `rank_delta` partitioning:** both are partitioned by (franchise, season). Week 0 gets null, which renders as "–".
- **Hysteresis grouping:** `group_by(maintain_order=True)` concatenation matches row order, because the frame is sorted by the group keys first.
- **Contract shape:** the JSON matches `types.ts` exactly for Meta, SeasonMeta, Row, WeekFile and SeasonFile.
- **Router:** handles `#`, `#/`, a trailing slash, out-of-range weeks and reserved routes. `go()` covers the case where the hash is already current. `replace()` sets the route itself, because `replaceState` doesn't fire `hashchange`.
- **Season loader:** evicts rejected promises, so Try again refetches.

No blockers. Two warnings:
- `fgs refresh` breaks its "writes nothing on failure" promise for the raw cache.
- Hysteresis is asymmetric by one point. The tests encode this, but it is probably not what D-04 meant.

## Warnings

### WR-01: `fgs refresh` overwrites the raw schedule/team cache before checks run

**File:** `pipeline/src/fgs/cli.py:143-145` (with `pipeline/src/fgs/ingest.py:10-23, 26-39`)
**Issue:** `_cmd_refresh` calls `load_schedules(refresh=True)` and `load_teams(refresh=True)`. Both write `data/cache/*.parquet` straight away, before `_checked_derive` runs. When nflverse serves a bad file, refresh exits 1 and leaves the derived parquet and site JSON alone, as designed. But the bad raw data has already replaced the good cache. After that, `fgs export`, `fgs build` and `fgs check` (which read the cache) all run on the poisoned data. `fgs export` doesn't run checks, so it will regenerate the site from it. The abort test only checks `DERIVED_DIR` and `WEB_DATA_DIR`, so it misses this.
**Fix:** Download without writing, check, and only then persist the cache. For example, add a `write_cache: bool = True` parameter to the loaders:
```python
raw = load_schedules(refresh=True, write_cache=False)
teams = load_teams(refresh=True, write_cache=False)
ok, derived, _ = _checked_derive(raw)
if not ok:
    ...; return 1
files = export.build_export(derived, teams, generated_at=generated_at)
save_cache(raw, "schedules.parquet"); save_cache(teams, "teams.parquet")
_write_derived(derived)
export.write_export(files, WEB_DATA_DIR)
```
Also extend `test_refresh_aborts_without_writing_on_bad_code` to assert that the cache files are byte-identical.

### WR-02: Hysteresis is asymmetric: entering a band takes 3 points of overshoot, leaving takes 2

**File:** `pipeline/src/fgs/mood.py:46-70`
**Issue:** Scores are integers and band k covers `T[k]..T[k+1]-1`, so the real boundary sits between `T[k]-1` and `T[k]`.
- **Moving up:** the label changes only at `s >= T[k]+2`. For T=60, scores 60 and 61 are already in band 4 by `band_of` but keep the old label. The label flips at the third score inside the new band.
- **Moving down:** the label changes at `s <= T[k]-2`. For T=60, 59 stays in band 4 and 58 flips. That is the second score inside the new band.

So the dead zone is 2 scores wide on the way up and 1 on the way down, which biases labels downward. A team oscillating 58↔61 flips to the lower label and never recovers. D-04 says "moves past the band boundary by ≥2 points", which reads as symmetric. The summary calls this the "literal" reading, and the test cases (`[58, 61] -> [3, 3]`, `[58, 62, 59] -> [3, 4, 4]`) lock the asymmetry in.
**Fix:** Pick a symmetric rule and update the tests to match. For example, require 2 points past the band's own edge in both directions:
```python
# up into k:   s >= T[k] + buf - 1   (T+1: second score inside band k)
# down out of k: s <= T[k] - buf     (T-2: second score inside band k-1)
```
Or keep up at `T[k]+buf` and make down `s <= T[k]-1-buf`. Either way, add a 58↔61 oscillation test to `test_hysteresis`.

## Info

### IN-01: Stale-response guard misses the A→B→A path, which causes a busy flicker (it self-heals)

**File:** `web/src/App.svelte:79-95`
**Issue:** The early return at line 83 (`seasonFile?.season === s`) and the `target.latest` return at line 81 both skip updating `requestedSeason`. Sequence: season A is loaded, the user selects B (fetch pending, `requestedSeason = B`), then switches back to A (early return, so `requestedSeason` stays B). When B resolves, `seasonFile = B` while the target is A. `currentRows` becomes undefined, so the board dims as busy. The effect then re-runs on `seasonFile` and swaps A back in from the cache. The result is never wrong data, just a needless busy flicker.
**Fix:** Set `requestedSeason = target?.latest ? null : target.season` before any early return. Or use a monotonically increasing request token that every effect run bumps.

### IN-02: Season change clamps the week by number, not by meaning

**File:** `web/src/App.svelte:117-122`
**Issue:** The week is carried over by number, and `reg_weeks` differs across eras (17 vs 18). Week 21 in 2010 is the Super Bowl, but in 2021 week 21 is the Conference round. Week 18 in 2021 is the regular-season finale, but in 2020 it is the Wild Card. The scrubber jumps between rounds without saying so.
**Fix:** For postseason weeks, map the offset: `w > reg ? newReg + (w - reg) : Math.min(w, newReg)`, then clamp to `max_week`.

### IN-03: `write_export` is not atomic

**File:** `pipeline/src/fgs/export.py:113-121`
**Issue:** It `rmtree`s `snapshots/` and `teams/`, then writes about 64 files one by one. A crash or Ctrl-C partway through leaves a mixed set: for example, a new `meta.json` (written after `latest.json`) next to missing season files. The dev server can also serve a half-written file to a page that is open.
**Fix:** Write everything into a sibling temp directory, then swap it in with `os.replace` or a rename. That is fine for a local experiment.

### IN-04: The frontend derives the band from the label string and ignores `row.band`

**File:** `web/src/components/BoardRow.svelte:11-12`, `web/src/lib/format.ts:43-45`
**Issue:** The export already emits `band` (the hysteresis-adjusted index), and `types.ts` declares it. `bandIndexForLabel` instead looks up the label text. If a label is ever renamed in `BANDS` without a re-export, every stripe silently falls back to `--border`.
**Fix:** Use `row.band` directly, with a bounds check against `bands.length`.

### IN-05: Postseason label lists are duplicated in three places

**File:** `pipeline/src/fgs/export.py:17`, `web/src/lib/format.ts:4, 52`
**Issue:** The pipeline emits `week_labels`, but `format.ts` keeps its own `POSTSEASON` fallback and `POSTSEASON_TICKS`. That partly undercuts the rule that "frontend never hardcodes" round names. The tick labels can't come from meta because no short form is emitted.
**Fix:** Emit a short label per week as well (for example `week_ticks`) and drop the frontend copies. Low priority.

### IN-06: Hysteresis alignment depends on an implicit sort invariant

**File:** `pipeline/src/fgs/mood.py:88-101`
**Issue:** `bands` is built by concatenating `group_by(...)` parts and then attached positionally with `pl.Series`. This is correct only because line 88 sorts by `(franchise_id, season, week)` right before. Any refactor that drops or reorders that sort would mislabel teams silently, with no error.
**Fix:** Compute the bands in a way that carries its keys. One option is `df.group_by(grp, maintain_order=True).agg(pl.col("score"), pl.col("week"))`, then run hysteresis on each list, `explode`, and join back on `(franchise_id, season, week)`. Or assert that `df` is sorted before attaching.

---

_Reviewed: 2026-11-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

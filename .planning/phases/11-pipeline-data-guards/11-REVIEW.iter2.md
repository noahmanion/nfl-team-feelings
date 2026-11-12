---
phase: 11-pipeline-data-guards
reviewed: 2026-11-12T03:30:00Z
depth: standard
iteration: 2
files_reviewed: 10
files_reviewed_list:
  - pipeline/src/fgs/cli.py
  - pipeline/src/fgs/export.py
  - pipeline/src/fgs/logos.py
  - pipeline/src/fgs/wintotals.py
  - pipeline/tests/test_export.py
  - pipeline/tests/test_logos.py
  - pipeline/tests/test_wintotals.py
  - web/src/lib/epa.ts
  - web/src/lib/epa.test.ts
  - web/src/lib/types.ts
findings:
  critical: 0
  warning: 1
  info: 10
  total: 11
status: issues_found
---

# Phase 11: Code Review Report (iteration 2)

**Reviewed:** 2026-11-12T03:30:00Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

This re-review covers the five fix commits in `400754c..HEAD` (6cc2f91, 03b65ad, 479f1cb, bb5f4a2, ca1c84b), which address WR-01 through WR-05 from iteration 1.

Tests run locally:
- `uv run pytest -q tests/test_wintotals.py tests/test_logos.py tests/test_export.py`: 82 passed.
- `npx vitest run src/lib/epa.test.ts`: 6 passed.

Status of the iteration-1 warnings:

| ID | Status | Notes |
|----|--------|-------|
| WR-01 | Resolved, with a new issue | The refresh no longer aborts. However, the fallback throws away *all* 2021+ rows when *any* display file fails, and refresh still exits 0. See the new WR-01 below. |
| WR-02 | Resolved | `_cached_vegas` drops seasons above 2020 and prints a warning, and the `ValueError` remains as a post-condition. I confirmed that `vegas_expectations` (`expectation.py:56`) normalizes with `.mean().over("season")`, so dropping later seasons cannot change any 2003-2020 `vegas_norm`. The new test checks this equality directly. `_display_win_totals` also filters to `<= 2020`, so the two paths are now consistent. |
| WR-03 | Resolved | A file is skipped only when `prev.get("url") == logo_url(f)`, so a stale URL or a missing manifest entry triggers a re-fetch. The test covers both cases and confirms that entries for untouched teams are preserved. |
| WR-04 | Resolved (fetch phase) | All 32 logos are fetched and validated in memory before anything is written. The test fails on the 15th fetch and confirms the directory is byte-identical afterwards. A small gap remains in the write phase (IN-10). |
| WR-05 | Resolved | Play counts are exported as `0` instead of null. The rate columns are typed `(number \| null)[]`, and `seasonToDate` keeps a separate denominator for each rate. `epa.ts` is the only consumer of `EpaFile` columns in `web/src`, so no other call site still treats null as 0. A side whose plays all have null `epa` (`off_plays > 0`, `off_epa` null, from `pl.col("epa").mean()` in `pbp.py:112`) is now handled correctly as well. One leftover: the real-data contract test still asserts the old, stricter contract (IN-09). |

The fixes introduced no blockers. No fingerprinted code was touched: `draft.py`, `cli.derive_games` and `cli.draft_winsor` are unchanged.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: One bad display file silently removes every 2021+ line, including the write-once 2021-2025 file, while refresh exits 0

**File:** `pipeline/src/fgs/cli.py:153-168`, `pipeline/src/fgs/wintotals.py:101-111`
**Issue:**
- `load_display_win_totals` validates both input files in a single list comprehension (`wintotals.py:103-105`), so a failure in either file raises for the whole load.
- The new `except` in `_display_win_totals` then falls back to `empty_display()`.

Iteration 1 named the most likely trigger: appending a partial 2027 season (fewer than 32 rows while books are still releasing lines) to `win_totals_display_2026plus.csv`. With this fix, that append quietly removes the valid, write-once 2021-2025 lines and the 2026 lines from all 32 team files.

The failure is easy to miss:
- `_cmd_refresh` prints one stderr WARNING and then its normal "refreshed in ..." success line.
- It returns 0.
- `write_export` publishes the reduced files.

Before the fix, the failure was loud and limited to a pipeline that wrote nothing. Now it is quiet and wipes all of the display data. Nothing in `checks.run_checks`/`run_warnings` or `fgs check` looks at `vegas_win_totals`, so the regression would only show up on the site.
**Fix:** Degrade per file, and make the degradation visible in the run's result:
```python
# wintotals.py
def load_display_win_totals(inputs_dir=None, strict: bool = True) -> tuple[pl.DataFrame, list[str]]:
    d = paths.INPUTS_DIR if inputs_dir is None else inputs_dir
    frames, problems = [], []
    for fname, rng in FILES.items():
        try:
            frames.append(validate(pl.read_csv(d / fname, infer_schema_length=0), rng, fname))
        except (ValueError, OSError, pl.exceptions.PolarsError) as e:
            if strict:
                raise
            problems.append(f"{fname}: {e}")
    out = pl.concat(frames).sort(["season", "franchise_id"]) if frames else empty_display()
    ...
    return out, problems
```
In `_display_win_totals`, print each problem as a WARNING, keep the files that validated, and show the skipped-file count in the final summary line of `_cmd_refresh`/`_cmd_export`. Better still, return a non-zero exit code after writing, or add a `run_warnings` entry, so a scripted weekly refresh notices. Keep the existing strict tests on the committed files. Add a test where `2021plus` is valid and `2026plus` is malformed, and assert that the 2021-2025 rows survive.

## Info

### IN-01: `FORFEIT_KIND` is dead at runtime and duplicates the `FORFEITS` keys inside a fingerprinted file (carried forward)

**File:** `pipeline/src/fgs/draft.py:196-232`
**Issue:** Only `test_draft.py` reads `FORFEIT_KIND`, and it repeats every `FORFEITS` key by hand. Because the table lives in `draft.py`, a fingerprinted file, even a label-only edit changes `code_fingerprint` and forces an `fgs evidence` rerun.
**Fix:** Move it to a non-fingerprinted module or to `forfeit_audit.json`. Do this alongside the next `draft.py` change, since the move itself also needs one evidence rerun.

### IN-02: The `used_in_score` docstrings overstate what the score consumed (carried forward)

**File:** `pipeline/src/fgs/wintotals.py:120-122`, `pipeline/src/fgs/export.py:414-416`
**Issue:** The docstrings call these "the lines the score actually used". The score actually uses `vegas_norm`, which is the line re-centered to the league mean, not the raw `line` that gets exported.
**Fix:** Reword to "the score used these lines (league-mean normalized)", or export `vegas_norm` as well.

### IN-03: The win-totals tests hard-code today's season span (carried forward)

**File:** `pipeline/tests/test_wintotals.py:45-46`, `pipeline/tests/test_export.py:687`
**Issue:** Three assertions pin the current span: `d.height == 192`, `[2021..2026]`, and `range(2003, 2027)`. All three fail on the first legitimate 2027 append.
**Fix:** Assert the structure instead: 32 rows per season, contiguous seasons starting at 2021, and the latest season at least 2026.

### IN-04: The `validate` odds and `entered_on` checks are loose (carried forward)

**File:** `pipeline/src/fgs/wintotals.py:39-44, 83`
**Issue:** `_odds` accepts American odds that cannot exist (`0`, `50`, `-99`). `entered_on` is not validated at all.
**Fix:** Reject `-100 < odds < 100`, and parse `entered_on` with `date.fromisoformat`.

### IN-05: `nohotlink.test.ts` has narrow coverage and can be evaded (carried forward)

**File:** `web/src/lib/nohotlink.test.ts:5, 17`
**Issue:**
- The test only scans `.ts` and `.svelte` files.
- Its regex needs the host and the extension in a single run of characters, so a URL built by string concatenation slips through.

**Fix:** Match the bare hosts (`espncdn\.com|wikipedia\.org|wikimedia\.org`) and widen the glob to `*.{js,css}`.

### IN-06: The golden pin covers only `snapshots/*.json` (carried forward)

**File:** `pipeline/tests/test_golden_scores.py:54-64`
**Issue:** `history.json` and `latest.json` also publish the frozen scores and labels, but the golden test does not check them.
**Fix:** Add a consistency test comparing `history.json` scores and labels against the snapshot rows for every season through 2025.

### IN-07: `loadEpa` duplicates the `loadGames` cache pattern (carried forward)

**File:** `web/src/lib/data.ts:90-103`
**Issue:**
- The memoize-and-evict-on-failure logic is duplicated from `loadGames`.
- `loadEpa` never checks `meta.epa_seasons`, so asking for a season without play-by-play data makes a request that is certain to fail.

**Fix:** Extract a `cachedJson<T>` helper, and return early when the season is not in `meta.epa_seasons`.

### IN-08: `fetch_logos` crashes on a corrupt or oddly shaped manifest (carried forward, slightly widened)

**File:** `pipeline/src/fgs/logos.py:69, 74`
**Issue:**
- A truncated or invalid manifest still raises a raw `JSONDecodeError` at line 69, even with `--force`.
- The WR-03 fix added a second way to crash: `prev = old.get(f, {})` followed by `prev.get("url")` assumes every manifest value is a dict. A hand-edited manifest, such as a string value or a top-level list, raises `AttributeError`.

**Fix:**
```python
try:
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
except json.JSONDecodeError:
    print("WARNING: corrupt logo manifest; re-fetching all", file=sys.stderr); old = {}
old = old if isinstance(old, dict) else {}
prev = old.get(f) if isinstance(old.get(f), dict) else {}
```

### IN-09: The real-data EPA contract test still asserts the pre-WR-05 contract (new)

**File:** `pipeline/tests/test_export.py:816-821`
**Issue:**
- After WR-05, the documented contract (`types.ts:98-103`, `export.py:53-56`) allows null rates and `0` play counts.
- `test_contract_epa_files` still asserts `v is not None` on every rate and `v > 0` on every play count.
- So a future nflverse release with one legitimately empty side (the exact case WR-05 now supports) fails `pytest` against real data, even though the export and the frontend are both correct.
- The test is also the only real-data check that the nulls stay rare. If it starts failing, the likely reaction is to loosen it, and then that check is gone.

**Fix:** Turn the test into the new contract plus a sanity bound:
```python
for k in ("off_epa", "off_sr", "def_epa", "def_sr"):
    for v in f[k]:
        if v is not None:
            assert math.isfinite(v) and round(v, 4) == v and not (v == 0.0 and math.copysign(1.0, v) < 0)
assert all(isinstance(v, int) and v >= 0 for v in f["off_plays"] + f["def_plays"])
assert sum(v is None for v in f["off_sr"]) <= 2, season  # nulls must stay rare
```

### IN-10: The WR-04 staging protects the fetch phase, not the write phase (new)

**File:** `pipeline/src/fgs/logos.py:86-88`
**Issue:**
- The docstring says "a mid-run failure leaves files and manifest untouched".
- Each `_atomic_write` is atomic on its own, but the loop at line 86 is not atomic as a set.
- If the disk fills or a write is interrupted partway through the 32 PNG writes, some PNGs are new while `manifest.json` still describes the old ones.

The risk is low, since it takes a local I/O failure on a one-shot command, but the docstring promises more than the code delivers.
**Fix:** Soften the docstring to "a failed download writes nothing". Alternatively, write to a sibling temp directory and swap it in with `os.replace` on the directory.

---

_Reviewed: 2026-11-12T03:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

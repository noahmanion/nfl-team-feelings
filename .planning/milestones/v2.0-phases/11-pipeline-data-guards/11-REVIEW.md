---
phase: 11-pipeline-data-guards
reviewed: 2026-11-12T04:30:00Z
depth: standard
iteration: 3
files_reviewed: 6
files_reviewed_list:
  - pipeline/src/fgs/wintotals.py
  - pipeline/src/fgs/cli.py
  - pipeline/src/fgs/logos.py
  - pipeline/tests/test_wintotals.py
  - pipeline/tests/test_export.py
  - pipeline/tests/test_logos.py
findings:
  critical: 0
  warning: 0
  info: 11
  total: 11
status: clean
---

# Phase 11: Code Review Report (iteration 3)

**Reviewed:** 2026-11-12T04:30:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** clean (0 critical, 0 warning; Info items carried forward)

## Summary

This re-review covers the three fix commits in `ca1c84b..HEAD`: 312c36a (WR-01), 31c3a18 (IN-09) and 26378ff (IN-08).

Tests run locally:
- `uv run pytest -q tests/test_wintotals.py tests/test_logos.py`: 43 passed.
- `uv run pytest -q tests/test_export.py` (real data): 43 passed.

Status of the iteration-2 findings:

| ID | Status | Notes |
|----|--------|-------|
| WR-01 | Resolved | `_load_display` validates each file in `FILES` on its own. The lenient path keeps every file that validates and reports each one that fails. `_display_win_totals` prints one stderr WARNING per skip and returns `(frame, skipped)`. Both `_cmd_refresh` and `_cmd_export` add the skip count to their final summary line. The strict loader still raises, so the tests on the committed files keep full strictness. The new test appends a 3-team 2027 season to 2026plus and confirms that all 5 x 32 rows for 2021-2025 survive. The one call site outside the CLI (the `test_export.py` fixture) was updated to `[0]`. Refresh still exits 0. That was the optional part of the suggested fix, so this is not a regression; see IN-13. |
| IN-09 | Resolved | The test now allows null rates and play counts `>= 0`, and adds a cap of at most 2 nulls per rate column per season. The `assert sum(...)` sits inside the `for k` loop, so the cap applies to every column. |
| IN-08 | Resolved, with a narrow gap | Invalid JSON, a top-level manifest that isn't a dict, and an entry that isn't a dict now all re-fetch instead of crashing. The parametrized test covers all three. A non-UTF-8 manifest still crashes (IN-12). |

The fixes introduced no Critical or Warning issues. No fingerprinted code was touched: `draft.py`, `cli.derive_games` and `cli.draft_winsor` are unchanged.

## Narrative Findings (AI reviewer)

## Info

### IN-01: `FORFEIT_KIND` is dead at runtime and duplicates the `FORFEITS` keys inside a fingerprinted file (carried forward)

**File:** `pipeline/src/fgs/draft.py:196-232`
**Issue:** Only `test_draft.py` reads `FORFEIT_KIND`, and it repeats every `FORFEITS` key by hand. Because `draft.py` is fingerprinted, even a label-only edit changes `code_fingerprint` and forces an `fgs evidence` rerun.
**Fix:** Move it to a non-fingerprinted module or to `forfeit_audit.json` the next time `draft.py` changes.

### IN-02: The `used_in_score` docstrings overstate what the score consumed (carried forward)

**File:** `pipeline/src/fgs/wintotals.py:138-140`, `pipeline/src/fgs/export.py:414-416`
**Issue:** The docstrings say "the lines the score actually used". The score uses `vegas_norm`, which is the line re-centered to the league mean, not the raw `line` that gets exported.
**Fix:** Reword to "the score used these lines (league-mean normalized)", or export `vegas_norm` as well.

### IN-03: The win-totals tests hard-code today's season span (carried forward)

**File:** `pipeline/tests/test_wintotals.py:45-46`, `pipeline/tests/test_export.py:687`
**Issue:** The assertions `d.height == 192`, `[2021..2026]` and `range(2003, 2027)` all fail on the first legitimate 2027 append.
**Fix:** Assert the structure instead: 32 rows per season, contiguous seasons starting at 2021, and the latest season at least 2026.

### IN-04: The `validate` odds and `entered_on` checks are loose (carried forward)

**File:** `pipeline/src/fgs/wintotals.py:39-44, 83`
**Issue:** `_odds` accepts American odds that cannot exist (`0`, `50`, `-99`). `entered_on` is not validated at all.
**Fix:** Reject `-100 < odds < 100`, and parse `entered_on` with `date.fromisoformat`.

### IN-05: `nohotlink.test.ts` has narrow coverage and can be evaded (carried forward)

**File:** `web/src/lib/nohotlink.test.ts:5, 17`
**Issue:** The test only scans `.ts` and `.svelte` files. Its regex needs the host and the extension in one run of characters, so a URL built by concatenation slips through.
**Fix:** Match the bare hosts (`espncdn\.com|wikipedia\.org|wikimedia\.org`) and widen the glob to `*.{js,css}`.

### IN-06: The golden pin covers only `snapshots/*.json` (carried forward)

**File:** `pipeline/tests/test_golden_scores.py:54-64`
**Issue:** `history.json` and `latest.json` also publish the frozen scores and labels, but the golden test does not check them.
**Fix:** Add a consistency test comparing `history.json` scores and labels against the snapshot rows for every season through 2025.

### IN-07: `loadEpa` duplicates the `loadGames` cache pattern (carried forward)

**File:** `web/src/lib/data.ts:90-103`
**Issue:** The memoize-and-evict-on-failure logic is copied from `loadGames`. `loadEpa` also never checks `meta.epa_seasons`, so asking for a season without play-by-play data makes a request that is certain to fail.
**Fix:** Extract a `cachedJson<T>` helper, and return early when the season is not in `meta.epa_seasons`.

### IN-10: The WR-04 staging protects the fetch phase, not the write phase (carried forward)

**File:** `pipeline/src/fgs/logos.py:62-64, 92-94`
**Issue:** The docstring says "a mid-run failure leaves files and manifest untouched". Each `_atomic_write` is atomic, but the 32 writes plus the manifest are not atomic as a set. An I/O failure partway through leaves new PNGs next to the old manifest.
**Fix:** Soften the docstring to "a failed download writes nothing", or write to a sibling temp directory and swap it in.

### IN-11: The `_display_win_totals` fallback misreports what failed and how many files were skipped (new)

**File:** `pipeline/src/fgs/cli.py:164-170`
**Issue:**
- The `except` is labelled "cross-file overlap guard", but it wraps `display_frame(raw, display)` as well. A `PolarsError` from casting a malformed cached nflverse `win_totals.csv` lands there too.
- In that case the message blames "all display files". The fallback then calls `display_frame(raw, empty_display())`, which raises the same error again, uncaught. The run still aborts loudly, so nothing is lost, but the stderr WARNING just before the traceback points at the wrong file.
- On that path, `skipped` is replaced with a single entry. Any per-file problems already collected by the lenient loader are dropped, and `_skipped_msg` reports "1 display win-totals file(s) skipped" when every display file was dropped.
- Line 164 (`pl.read_csv(wt)`) sits outside the `try`, so it is unaffected. That is correct, since a broken frozen score input should abort.

**Fix:** Narrow the `try` to the step it guards, and keep the earlier problems:
```python
display, skipped = wintotals.load_display_win_totals_lenient()  # per-file problems never raise
try:
    frame = wintotals.display_frame(raw, display)
except ValueError as e:  # nflverse/display overlap only
    skipped = skipped + [f"{f}: dropped ({e})" for f in wintotals.FILES]
    frame = wintotals.display_frame(raw, wintotals.empty_display())
```
The cross-file overlap `ValueError` inside `_load_display` (`wintotals.py:126-127`) would then propagate. That is acceptable because the check is documented as unreachable. Alternatively, catch it in `_load_display` and return `empty_display()` with a problem entry for every file.

### IN-12: A non-UTF-8 logo manifest still crashes `fetch_logos` (new, residual from IN-08)

**File:** `pipeline/src/fgs/logos.py:70-74`
**Issue:**
- `manifest_path.read_text()` raises `UnicodeDecodeError` on binary garbage, such as a manifest truncated mid-write by another tool or a stray file. That error is a `ValueError` subclass, but not a `json.JSONDecodeError`, so it escapes the new handler.
- I confirmed this with a probe: writing `b'\xff\xfe\x00garbage'` to `manifest.json` makes `fetch_logos` raise `UnicodeDecodeError` before any fetch.
- `read_text()` with no `encoding` also depends on the locale.

**Fix:** Use `read_text(encoding="utf-8")` and catch `(json.JSONDecodeError, UnicodeDecodeError)`, or simply `ValueError`. Add `b"\xff\xfe"` to the parametrized cases in `test_odd_manifest_refetches_instead_of_crashing`.

### IN-13: Per-file degradation still drops the current season's lines on a partial future append, and refresh exits 0 (new, residual from WR-01)

**File:** `pipeline/src/fgs/wintotals.py:91-93, 117-123`, `pipeline/src/fgs/cli.py:489, 512-518`
**Issue:**
- The fix works at file granularity. All 2026+ seasons share one file, and `validate` requires 32 teams per season.
- So the realistic trigger, a partial 2027 append, still drops the valid 2026 lines along with 2027. The test confirms this: its expected output contains only 2021-2025.
- The skip now shows up in stderr and on the summary line, but `_cmd_refresh` still returns 0 and `checks.run_warnings` doesn't see it, so a scripted or cron refresh won't notice.
- This is acceptable for a prototype and matches the fix iteration 2 suggested, so it is Info only.

**Fix:** Pick either option:
- Validate per season inside the open-ended file: group by season, keep the seasons that pass, and report the ones that fail.
- Allow a trailing season with fewer than 32 teams in the open-ended file, behind a `partial_ok` flag for the last season only.

Separately, add a `run_warnings` entry, or a non-zero exit code after writing, when `skipped` is non-empty.

---

_Reviewed: 2026-11-12T04:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

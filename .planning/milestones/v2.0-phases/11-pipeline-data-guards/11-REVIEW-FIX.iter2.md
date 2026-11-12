---
phase: 11-pipeline-data-guards
fixed_at: 2026-11-12T04:00:00Z
review_path: .planning/phases/11-pipeline-data-guards/11-REVIEW.md
iteration: 2
findings_in_scope: 1
fixed: 1
skipped: 0
status: all_fixed
---

# Phase 11: Code Review Fix Report

**Fixed at:** 2026-11-12T04:00:00Z
**Source review:** .planning/phases/11-pipeline-data-guards/11-REVIEW.md
**Iteration:** 2

**Summary:**
- Findings in scope: 1 (WR-01). IN-09 and IN-08 were also fixed on request.
- Fixed: 1 in scope, plus 2 Info
- Skipped: 0

Verification: `cd pipeline && uv run pytest -q` gives 639 passed, golden included. No fingerprinted code was touched: `fingerprint.CODE_FILES`, `cli.derive_games` and `cli.draft_winsor` are unchanged. `inputs/win_totals_2021plus.csv`, `PREREGISTRATION*.md` and `weights.yaml` are also unchanged. `fgs evidence` and `fgs refresh` were not run.

## Fixed Issues

### WR-01: One bad display file silently removes every 2021+ line

**Files modified:** `pipeline/src/fgs/wintotals.py`, `pipeline/src/fgs/cli.py`, `pipeline/tests/test_wintotals.py`, `pipeline/tests/test_export.py`
**Commit:** 312c36a
**Applied fix:**
- **Per-file loading.** A shared `_load_display(inputs_dir, strict)` now validates each file in `FILES` on its own.
  - `load_display_win_totals()` stays strict: it raises, and the existing tests on the committed files still use it.
  - The new `load_display_win_totals_lenient()` returns `(frame, problems)`. It keeps every file that validates and lists each file that fails.
- **Return value.** `cli._display_win_totals` now returns `(frame, skipped)`.
  - It prints one stderr `WARNING` per skipped file, naming the file and the error.
  - The old fall-back-to-empty path is kept only for the cross-file overlap guard, which can't currently trigger.
- **Summary line.** `_cmd_refresh` and `_cmd_export` add `; WARNING: N display win-totals file(s) skipped (see stderr)` to their final summary line (`_skipped_msg`). Refresh still returns 0 and still publishes.
- **New test.** `test_display_win_totals_degrades_per_file` uses the real 2021plus file plus a 2026plus file with a 3-team 2027 season appended.
  - It asserts that the strict loader raises.
  - It asserts that exactly that one file is reported, on stderr and in the skipped list.
  - It asserts that all 5 x 32 rows for 2021-2025 survive.
- **Call sites.** The `test_export.py` fixture now unpacks `[0]`.

### IN-09 (Info, fixed on request): The real-data EPA contract test asserted the pre-WR-05 contract

**Files modified:** `pipeline/tests/test_export.py`
**Commit:** 31c3a18
**Applied fix:** `test_contract_epa_files` now matches the WR-05 contract.
- It skips null rates. Rates that are present must still be finite, rounded to 4 places, and not negative zero.
- Play counts must be ints `>= 0`.
- A new sanity bound fails if any rate column has more than 2 nulls per season, so nulls must stay rare.

### IN-08 (Info, fixed on request): `fetch_logos` crashed on a corrupt or oddly shaped manifest

**Files modified:** `pipeline/src/fgs/logos.py`, `pipeline/tests/test_logos.py`
**Commit:** 26378ff
**Applied fix:**
- A `JSONDecodeError` on the manifest now prints a stderr WARNING and treats the manifest as empty.
- A top-level manifest that isn't a dict is treated as empty.
- A per-team entry that isn't a dict is treated as missing, so that logo is re-fetched.
- A parametrized test covers invalid JSON, a top-level list, and a string entry.

---

_Fixed: 2026-11-12T04:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_

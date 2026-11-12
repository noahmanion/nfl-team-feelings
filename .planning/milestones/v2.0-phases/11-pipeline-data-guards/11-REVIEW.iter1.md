---
phase: 11-pipeline-data-guards
reviewed: 2026-11-12T03:10:08Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - pipeline/src/fgs/cli.py
  - pipeline/src/fgs/draft.py
  - pipeline/src/fgs/export.py
  - pipeline/src/fgs/logos.py
  - pipeline/src/fgs/paths.py
  - pipeline/src/fgs/wintotals.py
  - pipeline/tests/test_cli.py
  - pipeline/tests/test_draft.py
  - pipeline/tests/test_export.py
  - pipeline/tests/test_golden_scores.py
  - pipeline/tests/test_logos.py
  - pipeline/tests/test_wintotals.py
  - web/src/lib/data.ts
  - web/src/lib/epa.test.ts
  - web/src/lib/epa.ts
  - web/src/lib/nohotlink.test.ts
  - web/src/lib/types.ts
findings:
  critical: 0
  warning: 5
  info: 8
  total: 13
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-11-12T03:10:08Z
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

I reviewed the phase-11 diff (`97e1f33..HEAD`): the golden score pin, the forfeit audit in `draft.py`, the display-only 2021+ win totals (`wintotals.py`, the `_cached_vegas` guard, and `_display_win_totals`), the per-team-game EPA export and the web helper for it, and the one-shot logo downloader.

The phase-11 tests pass locally: `pytest tests/test_{wintotals,logos,export,cli,draft,golden_scores}.py` gives 154 passed against the real cache. Checks against the cached data:
- The nflverse `win_totals.csv` has 576 rows covering 2003-2020. Every code maps to a canonical franchise, and there are no duplicate team-seasons.
- The committed `web/public/data/epa/*.json` files contain no nulls or NaN.
- Every game appears exactly twice in the EPA files.

The display-only win totals don't reach the score. The score's input stays behind `_cached_vegas`, which only reads `vegas_norm` from the nflverse file. The import and AST guards in `test_wintotals.py` cover this.

I found no blockers. The warnings are about robustness:
- A failure in a display-only feature can stop the weekly score refresh.
- The `<=2020` guard raises an error where it could filter.
- The logo manifest can record the wrong provenance for an image.
- The TypeScript EPA contract says values are never null, but the pipeline can emit null.

**Fingerprint note:** `draft.py` is in `fingerprint.CODE_FILES`. Any edit to it, including IN-01 below, changes `code_fingerprint`, so `fgs evidence` must be rerun and `callout_evidence.json` recommitted. `cli.py` counts only through `derive_games` and `draft_winsor`, so the fixes suggested below for `_cached_vegas`, `_display_win_totals` and `_cmd_refresh` do not change the fingerprint. Nothing below touches `pipeline/inputs/win_totals_2021plus.csv`.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: A display-only win-totals failure aborts the whole weekly refresh/export

**File:** `pipeline/src/fgs/cli.py:146-152, 462-463, 519-520`
**Issue:** `_display_win_totals` runs inside `_cmd_refresh` and `_cmd_export`, and that path has no error handling. `wintotals.load_display_win_totals()` raises `ValueError` on any validation problem. The docstring of `wintotals.py:9` invites future appends, and an append could trigger one: a 2027 season with fewer than 32 rows as books release lines, a sum outside ±8, an `http://` source, or a missing file. When that happens, `fgs refresh` exits before writing anything, so a data-entry slip in a feature that is explicitly display-only blocks the weekly score update. The display data's validation should not be able to take down the scored pipeline.
**Fix:** Keep strict validation in tests, and degrade gracefully at runtime:
```python
def _display_win_totals(cache_dir) -> pl.DataFrame | None:
    wt = cache_dir / "win_totals.csv"
    raw = pl.read_csv(wt) if wt.exists() else None
    try:
        return wintotals.display_frame(raw, wintotals.load_display_win_totals())
    except (ValueError, OSError) as e:
        print(f"WARNING: display win totals skipped ({e}); team files get empty vegas_win_totals",
              file=sys.stderr)
        return None
```
Alternatively, add a `checks.py` entry so the failure shows up through the same "checks failed" path with a clear message. (`cli.py` is fingerprinted only through `derive_games` and `draft_winsor`, so this edit needs no evidence rerun.)

### WR-02: The `<=2020` guard hard-fails where it could safely filter, so a fresh clone breaks if upstream nflverse ever extends the file

**File:** `pipeline/src/fgs/cli.py:136-141`
**Issue:** `_cached_vegas(download=True)` fetches `WIN_TOTALS_URL`, which points at the nflverse `master` branch, whenever the cache file is missing (a fresh clone or a cleared cache). If nfldata ever adds 2021+ rows upstream, the guard raises and `fgs refresh` / `fgs export` / `fgs build` can never succeed on a new machine. Raising adds no safety here: `vegas_expectations` normalizes per season (`mean().over("season")`), so dropping seasons above 2020 cannot change any 2003-2020 `vegas_norm`, and the golden scores stay intact. Filtering keeps the intent of D-12 without the brittleness. The same file feeds `_display_win_totals`, which already filters with `season <= 2020` (`wintotals.py:118`), so the two paths currently handle this case inconsistently.
**Fix:**
```python
raw = pl.read_csv(wt)
if raw.height and int(raw["season"].max()) > 2020:
    print(f"WARNING: {wt} has seasons > 2020; ignoring them (2021+ win totals are display-only)",
          file=sys.stderr)
    raw = raw.filter(pl.col("season") <= 2020)
frame = vegas_expectations(raw)
assert_le_2020(frame)  # keep the ValueError as a post-condition on the filtered frame
```
Update `test_guard_cached_vegas_refuses_post_2020` to assert that the output stops at 2020 and is unchanged for 2020. Pinning a hash of the frozen file would also guard against upstream edits to 2003-2020 rows.

### WR-03: The logo skip path writes the current URL into the manifest, not the URL the file was fetched from

**File:** `pipeline/src/fgs/logos.py:69-79`
**Issue:** If a file already exists and `force` is false, the code re-validates the PNG but always records `"url": logo_url(f)`. If `CODE_OVERRIDES` is ever corrected (the comment on lines 20-21 notes that `/500/la.png` and `/500/was.png` are valid PNGs of the wrong team), rerunning `fgs logos` without `--force` keeps the wrong image. The manifest then claims it came from the corrected URL, and `test_committed_logos` (`manifest[f]["url"] == logos.logo_url(f)`) passes. That is the silent-wrong-logo failure the mapping test was written to prevent.
**Fix:** Re-fetch when the recorded URL differs:
```python
prev = old.get(f, {})
if path.exists() and not force and prev.get("url") == url:
    data = path.read_bytes(); validate_png(data); when = prev.get("fetched", today)
else:
    data = fetch(url); validate_png(data); _atomic_write(path, data); when = today
```

### WR-04: A mid-run download failure leaves the PNGs and `manifest.json` out of sync

**File:** `pipeline/src/fgs/logos.py:67-81`
**Issue:** Each PNG is written as soon as it validates, and the manifest is written only after the loop. With `--force`, if team 15 raises (network error, 403, or an HTML error page), teams 1-14 are overwritten on disk while the committed `manifest.json` still holds their old `sha256` and `bytes`. The tree is then inconsistent until someone reruns. `test_invalid_download_raises_without_partial` only covers a failure on the first team, so it doesn't catch this. The docstring says "An invalid download raises before anything is written for that team", which is true per team but not for the set.
**Fix:** Fetch and validate all 32 into memory first (about 1-2 MB), and write only after every download succeeds:
```python
staged = {}
for f in sorted(CANONICAL):
    ...  # fetch + validate into staged[f] = (path, data, when)
for f, (path, data, when) in staged.items():
    if data is not None: _atomic_write(path, data)
```
Add a test where the fake fetch fails on the Nth team after a full first run, and assert that the files and manifest are unchanged.

### WR-05: The `EpaFile` TypeScript contract says values are never null, but the export can emit `null`

**File:** `web/src/lib/types.ts:99-101`, `pipeline/src/fgs/export.py:46-47, 77`, `web/src/lib/epa.ts:21-32`
**Issue:**
- `pbp.team_game_epa` builds its rows with a full outer join of offense and defense (`pbp.py:129`). A team-game with defensive plays but no qualifying offensive plays therefore gets `off_epa`, `off_plays` and `off_sr` as null.
- `_epa_files` passes those nulls through: `_r4(None)` returns `None`, and the plays column becomes `[None if v is None ...]`.
- `def_sr` comes from a left join (`how="left"`, line 64), so it can also be null.
- `EpaFile` declares every one of these columns as `number[]`.
- In `seasonToDate`, a null in `off_plays` is skipped harmlessly (`null > 0` is false). But a null `off_sr` or `def_sr` alongside a positive play count evaluates as `null * op === 0` in JS. That silently lowers the success rate while the plays still count in the denominator.

The current committed data has no nulls, so this is latent. `test_contract_epa_files` only asserts non-null against today's real cache. Nothing in the exporter enforces it.
**Fix:** Pick one of these:
1. Enforce non-null in the exporter by dropping or raising on null rows before the export:
   ```python
   epa = epa.drop_nulls(["off_epa", "off_plays", "off_sr", "def_epa", "def_plays", "def_sr"])
   ```
2. Make the types honest (`(number | null)[]`) and guard in `seasonToDate` with `if (op > 0 && f.off_sr[i] != null)` (and the same for defense), keeping a separate sr denominator.

## Info

### IN-01: `FORFEIT_KIND` is dead at runtime and duplicates the `FORFEITS` keys inside a fingerprinted file

**File:** `pipeline/src/fgs/draft.py:196-232`
**Issue:** Only `test_draft.py` reads `FORFEIT_KIND`. It repeats every `FORFEITS` team-line by hand, and the comments above each `FORFEITS` entry repeat it a third time. A test keeps the keys in sync, but because the table lives in `draft.py`, even a label-only fix to it changes `code_fingerprint` and forces an `fgs evidence` rerun.
**Fix:** If it stays display/audit metadata, move it out of `draft.py`, for example into a small non-fingerprinted `draft_audit.py` or the existing `forfeit_audit.json`. Note that this move is itself a `draft.py` edit, so it needs one `fgs evidence` rerun. Batch it with any other `draft.py` change.

### IN-02: The `used_in_score` docstring overstates what the score consumed

**File:** `pipeline/src/fgs/wintotals.py:113-115`, `pipeline/src/fgs/export.py:411-413`
**Issue:** The docstrings say the nflverse rows are "the lines the score actually used". The score uses `vegas_norm`, which is each line re-centered so the league mean equals `reg_games/2` (`expectation.py:56`), not the raw `line` exported here. A UI that labels the raw number "used in score" would be slightly misleading.
**Fix:** Reword the docstrings to "the score used these lines (league-mean normalized)", or also export `vegas_norm` for 2003-2020.

### IN-03: The win-totals tests hard-code today's season span and will fail on the next legitimate append

**File:** `pipeline/tests/test_wintotals.py:45-46`, `pipeline/tests/test_export.py:687`
**Issue:** `d.height == 192`, the season list `[2021..2026]`, and `list(range(2003, 2027))` will all fail the moment 2027 lines are appended to `win_totals_display_2026plus.csv`, which the module docstring says is the intended workflow.
**Fix:** Assert structure, not a count: 32 rows per season, contiguous seasons starting at 2021, and the last season at least 2026.

### IN-04: The `wintotals.validate` odds and `entered_on` checks are loose

**File:** `pipeline/src/fgs/wintotals.py:35-40, 79`
**Issue:** `_odds` accepts any integer, including American odds that can't exist such as `0`, `50` or `-99`. `entered_on` isn't validated at all, so an empty or garbage value passes even though it is part of the provenance.
**Fix:** Reject `-100 < odds < 100`, and parse `entered_on` with `date.fromisoformat`.

### IN-05: `nohotlink.test.ts` covers only `.ts` and `.svelte` sources and can be evaded by string concatenation

**File:** `web/src/lib/nohotlink.test.ts:5, 17`
**Issue:** The glob skips `.css`, `.js`, `public/**` and JSON. The regex requires the host and the `.png`/`.svg` extension in one run of characters with no whitespace, so `'https://a.espncdn.com/.../' + code + '.png'` is not caught.
**Fix:** Also match bare hosts (`/(espncdn\.com|wikipedia\.org|wikimedia\.org)/i`) and widen the glob to include `*.{js,css}`.

### IN-06: The golden pin covers only `snapshots/*.json`

**File:** `pipeline/tests/test_golden_scores.py:54-64`
**Issue:** Frozen scores and labels are also published in `history.json` (`score` and `label` per team) and `latest.json`. A divergence in how those are built would leave the snapshots unchanged and the golden test green, while the site showed different v1 numbers.
**Fix:** Add a cheap consistency test: for every season up to 2025, check that the `history.json` score and label match the snapshot rows.

### IN-07: `loadEpa` copies the `loadGames` cache pattern

**File:** `web/src/lib/data.ts:90-103`
**Issue:** The memo-plus-evict-on-failure logic is now duplicated. It also never checks `meta.epa_seasons`, so asking for a season without pbp makes a doomed request.
**Fix:** Extract a `cachedJson<T>(cache, key, path)` helper, and return early with a rejected promise when `season` isn't in `meta.epa_seasons`.

### IN-08: `fetch_logos` crashes with a raw `JSONDecodeError` on a corrupt manifest

**File:** `pipeline/src/fgs/logos.py:65`
**Issue:** `json.loads(manifest_path.read_text())` has no error handling. A truncated or hand-edited manifest makes `fgs logos` fail with a traceback, even with `--force`, which ignores the old manifest's contents anyway.
**Fix:** Catch `json.JSONDecodeError` there, and treat a corrupt manifest as `{}` with a warning.

---

_Reviewed: 2026-11-12T03:10:08Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

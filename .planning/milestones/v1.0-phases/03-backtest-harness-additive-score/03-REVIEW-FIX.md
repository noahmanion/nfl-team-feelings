---
phase: 03-backtest-harness-additive-score
fixed_at: 2026-11-11T21:26:00Z
review_path: .planning/phases/03-backtest-harness-additive-score/03-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 8
skipped: 1
status: partial
---

# Phase 3: Code Review Fix Report

**Fixed at:** 2026-11-11T21:26:00Z
**Source review:** .planning/phases/03-backtest-harness-additive-score/03-REVIEW.md
**Iteration:** 1

The orchestrator set the scope: WR-01 to WR-05, WR-07, IN-01 and IN-04. WR-06 was skipped on purpose. IN-02, IN-03 and IN-05 were left out of scope.

**Summary:**
- Findings in scope: 8 (+ WR-06, which was skipped on purpose)
- Fixed: 8
- Skipped: 1 (WR-06, deferred)

**Verification after all fixes:**
- `cd pipeline && uv run pytest -q`: 172 passed.
- `uv run fgs export`: 64 files written.
- `cd web && npm run test`: 44 passed.
- `npm run check`: 0 errors.
- `npm run build`: OK.

## Fixed Issues

### WR-01: X-axis season ticks "1999" and "2000" overlap at the left edge

**Files modified:** `web/src/lib/history.ts`, `web/src/lib/history.test.ts`
**Commit:** 4a28592
**Applied fix:** `tickSeasons` picks the seasons that are multiples of the step (2 wide, 5 narrow). It prepends the first season only if the next pick is at least one step away, or if nothing was picked. With the current data the first tick is now 2000, and 1999 is dropped. The "always the first" test now checks that no two ticks are closer than the step. A second test covers when the first season is kept.

### WR-02: Band labels sit inside the plot and collide with the lines and the team label

**Files modified:** `web/src/components/HistoryChart.svelte`
**Commit:** 2e86699
**Status:** fixed: requires human verification (visual layout, not checked in a browser)
**Applied fix:** The right margin is now a gutter with two columns:
- **Team end-label column.** Its width comes from measuring the team abbreviation with canvas, plus a 6px offset.
- **Band-label column.** Its width comes from measuring the longest band label at 12px, plus a gap.

Band labels start at `xMax + teamCol + gap` with `textAnchor: 'start'`, so they are always outside the data area. The team label always goes in its own column with `dx: 6`, and the `nearEnd` flip is removed, so it cannot run into the band labels.

Below 640px the band text labels are dropped, the gutter shrinks to the team column only, and a compact swatch legend (range + label) renders under the chart.

### WR-03: Background team lines are too heavy, especially at 375 px

**Files modified:** `web/src/components/HistoryChart.svelte`
**Commit:** f24b85f
**Status:** fixed: requires human verification (visual)
**Applied fix:** Background line stroke and opacity now scale with chart width:

| Chart width | Stroke | Opacity |
|---|---|---|
| ≥900px | 0.75px | 0.16 |
| ≥500px | 0.6px | 0.12 |
| Narrower | 0.5px | 0.08 |

The old values were 1px and 0.25 opacity at every width.

### WR-04: meta.factors weights are re-read from weights.yaml, not taken from the weights that produced the contributions

**Files modified:** `pipeline/src/fgs/cli.py`, `pipeline/src/fgs/export.py`, `pipeline/tests/test_export.py`
**Commit:** 063fb6d
**Applied fix:**
- `derive_games` now returns `"weights"`, the exact dict it scored with.
- `build_export` uses the new `_export_weights`. It takes `derived["weights"]` and falls back to `load_weights()` only when that key is absent.
- `_export_weights` checks that every factor has `z_`/`contrib_` columns, that there are no contrib columns for factors outside the weights, and that `contrib_f == w_f * z_f` everywhere. Any mismatch raises `ValueError`, which replaces the old `assert`.
- A new test covers explicit non-yaml weights, tampered weights, a missing factor and an extra factor.

### WR-05: `fgs backtest` / `--propose-weights` cannot run without a valid weights.yaml

**Files modified:** `pipeline/src/fgs/cli.py`, `pipeline/tests/test_backtest.py`, `pipeline/tests/test_cli.py`
**Commit:** b340b23
**Applied fix:** `derive_games`/`derive` take `scored=False`, which stops after the Elo grid: no features, no weights read. `_cmd_backtest` uses it. The existing CLI backtest test now points `WEIGHTS_PATH` at a missing file, and a new unit test checks that the unscored derive needs no weights file.

### WR-07: `last` is reused for two meanings in `run_backtest`

**Files modified:** `pipeline/src/fgs/backtest.py`
**Commit:** 5ace445
**Applied fix:** Renamed the holdout bound to `last_season` and the ridge fold info to `last_fold`. Behaviour is unchanged.

### IN-01: Exported contribs contain JSON `-0.0`

**Files modified:** `pipeline/src/fgs/export.py`, `pipeline/tests/test_export.py`, plus the regenerated `web/public/data/**`
**Commits:** 0a548e9 (code and test), 574af28 (regenerated site data: 27 files; the only changes are `-0.0` becoming `0.0` and `generated_at`)
**Applied fix:** `round(float(v), 2) + 0.0`. A real-cache test asserts that no contrib is a negative zero. The test failed before the fix and passes after it.

### IN-04: `loadHistory` cache ignores `meta.generated_at` changes

**Files modified:** `web/src/lib/data.ts`
**Commit:** 7cd7566
**Applied fix:** The cache entry is now `{ key: generated_at, p }`. It is reused only when `meta.generated_at` matches, and it is still evicted when the fetch is rejected.

## Skipped Issues

### WR-06: A negative-weight factor ships to users on a noise-level backtest gain

**File:** `pipeline/weights.yaml`
**Reason:** Deferred on purpose by the orchestrator to the Phase 6 weight freeze, which will add a bootstrap or per-season SE check before factors are kept. `last16: -1.25` stays shipped for now.
**Original issue:** ΔSpearman of +0.0033 with no uncertainty estimate; a hot recent record lowers the score when Elo is held fixed.

### Not in scope (left as-is)

- **IN-02:** The ridge composite "R²" is squared Pearson, not out-of-sample 1 - SSE/SST.
- **IN-03:** The ridge-composite Brier logistic is calibrated on in-sample ridge fits.
- **IN-05:** The ridge penalty acts on per-snapshot z units, not on globally standardized inputs.

---

_Fixed: 2026-11-11T21:26:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

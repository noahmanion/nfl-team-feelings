---
phase: 03-backtest-harness-additive-score
reviewed: 2026-11-11T19:20:15Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - README.md
  - pipeline/src/fgs/backtest.py
  - pipeline/src/fgs/cli.py
  - pipeline/src/fgs/export.py
  - pipeline/src/fgs/features.py
  - pipeline/src/fgs/mood.py
  - pipeline/src/fgs/paths.py
  - pipeline/src/fgs/score.py
  - pipeline/src/fgs/season_config.py
  - pipeline/tests/test_leakage.py
  - web/src/App.svelte
  - web/src/components/HistoryChart.svelte
  - web/src/components/HistoryPage.svelte
  - web/src/components/SiteHeader.svelte
  - web/src/lib/data.ts
  - web/src/lib/history.ts
  - web/src/lib/router.ts
  - web/src/lib/types.ts
findings:
  critical: 0
  warning: 7
  info: 5
  total: 12
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-11-11T19:20:15Z
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

Scope: `git diff ce5ddb9~1 -- pipeline/src pipeline/tests web/src README.md`. The other test files were skimmed for reliability only.

I traced these areas by hand and found no correctness defects in them:

- **Target and adjusted margin.** In `targets`, the global cumsum windows `[off+k, off+k+m)` are valid because `adjusted_margins` sorts by (franchise, season, asof_week, game_id) before `with_row_index`. The `adj` algebra matches the README.
- **As-of features.** `_last16` is a backward `join_asof` on `season*100+asof_week`, and the last row per key holds the window that ends there. `_pd_pg` is a backward as-of join within (franchise, season). `season_record` comes from REG-only `win_pct`.
- **Next-game frame.** It joins snapshots at `asof_week - 1`.
- **Walk-forward.** Every fit (ridge, LOSO alpha, logistic) uses `season < S`. The targets for season S-1 stay within S-1.
- **Holdout seal.** Snapshots, team_games and games are filtered to `<= last test season` before any feature, target or fit. `propose_weights` hard-caps at `TRAIN_LAST_SEASON`.
- **Zero-variance guard.** `std <= 1e-12` or null std gives `z = 0`.
- **Frozen percentile reference.** `REF_SEASONS` is read at call time, and an empty reference raises.
- **Chart season gaps.** `toRows` adds a NaN slot at `xs[i]-1` and the highlighted series keeps those NaN rows.

So the issues are concentrated in the chart UI (three issues seen by the orchestrator, plus the root cause of the tick overlap), in coupling between weights.yaml and the export/backtest, and in how the shipped interim weights are justified.

## Warnings

### WR-01: X-axis season ticks "1999" and "2000" overlap at the left edge (UI-1)

**File:** `web/src/lib/history.ts:49-52` (used by `web/src/components/HistoryChart.svelte:35,104-111`)
**Issue:** `tickSeasons` always keeps index 0 (1999) and then keeps every season with `season % every === 0`. 2000 is divisible by both 2 and 5, so the ticks for 1999 and 2000 sit about one season apart, roughly 20 px on desktop and closer on mobile. The labels "1999"/"2000" (desktop) and "'99"/"'00" (mobile) overlap. The orchestrator confirmed this in browser screenshots. The vitest suite enshrines this behaviour ("always the first").
**Fix:** Drop the forced first tick when the next selected tick is too close, or choose ticks by spacing:
```ts
export function tickSeasons(starts: SeasonStart[], width: number): SeasonStart[] {
  const every = width >= 500 ? 2 : 5
  const picked = starts.filter((d) => d.season % every === 0)
  // keep the first season only if it is at least `every` seasons from the next tick
  if (starts.length && picked[0]?.season - starts[0].season >= every) picked.unshift(starts[0])
  return picked
}
```
Update the "always the first" test to match.

### WR-02: Band labels sit inside the plot and collide with the lines and the highlighted team label (UI-2)

**File:** `web/src/components/HistoryChart.svelte:57-68, 86-95, 102`
**Issue:** The band labels are drawn with `x: xMax, textAnchor: 'end', dx: -4`, inside the data area at the right edge. That is exactly where the most recent part of every team's line is drawn and where the highlight label goes. The `nearEnd` branch (`dx: -6, dy: -10, textAnchor: 'end'`) moves the team abbreviation left, which puts it straight into the band-label column. The screenshots show "DET" drawn over "Buying the jersey". With `marginRight: 8` there is no gutter for either label.
**Fix:** Move the band labels into a dedicated right gutter, outside the x domain. For example, set `marginRight: wide ? 130 : 4` and render `Plot.text(bandRects, { x: xMax, y: 'mid', text: 'label', textAnchor: 'start', dx: 8, clip: false })` so they sit past the last data point. You could also place them in a left gutter, or render them as HTML legend chips under the chart. Then the highlight label never needs `nearEnd` flipping into the band-label area: with a gutter, keep `textAnchor: 'start', dx: 6` and leave room for it, or put the team label above the line end only.

### WR-03: Background team lines are too heavy, especially at 375 px (UI-3)

**File:** `web/src/components/HistoryChart.svelte:77-84`
**Issue:** At 1 px stroke and 0.25 opacity, 31 overlapping grey lines over about 600 x-slots become a solid grey mass. On a 280 px-tall phone chart this buries the band stripes and weakens the highlighted line. CONTEXT's "keep it legible with 32 lines (muted greys, one highlight)" is not met at phone width (orchestrator screenshots).
**Fix:** Scale the stroke down with width, for example `strokeOpacity: wide ? 0.15 : 0.08` and `strokeWidth: wide ? 0.75 : 0.5`. Optionally add `mixBlendMode: 'multiply'` (light) so overlaps darken gently rather than saturating.

### WR-04: meta.factors weights are re-read from weights.yaml, not from the weights that produced the contributions

**File:** `pipeline/src/fgs/export.py:71-79`
**Issue:** `build_export` calls `score.load_weights()` independently of the `derive_games(..., weights=...)` call that produced `contrib_*` and `composite`. It only checks that the column names exist (`assert not missing`). Two cases break this:
- If `derived` was built with explicit weights (tests, or a future `--weights` experiment), the export ships `meta.factors[].weight` values that do not match the contributions.
- If weights.yaml is edited between `build` and `export` while keeping the same keys, the same mismatch happens.

The check also uses `assert`, which is stripped under `python -O`.
**Fix:** Carry the weights through `derived`. In `derive_games`, return `{"weights": w, ...}`. In `build_export`, use `weights = derived.get("weights") or score.load_weights()`, and raise `ValueError` instead of using `assert`. Alternatively, verify that `contrib_f / z_f == w_f` on a non-zero row.

### WR-05: `fgs backtest` / `--propose-weights` cannot run without a valid weights.yaml

**File:** `pipeline/src/fgs/cli.py:199-200` (via `derive_games`, `cli.py:20-31`)
**Issue:** `_cmd_backtest` calls `derive()`, which always runs `score.composite(feats, score.load_weights())`. The backtest never uses `derived["features"]`, because `run_backtest` and `propose_weights` rebuild features from `snapshots`. Even so, a missing or malformed weights.yaml, or one containing a factor key not yet in `FACTORS`, makes the weight-*proposal* command fail. That is circular: you need valid weights to propose weights. Phase 4/5 will hit this when a new factor is added to weights.yaml before `FACTORS` has it, or the other way round.
**Fix:** Give `derive_games` a `score=False` path, or have `_cmd_backtest` build only `games/team_games/snapshots`:
```python
games, sparse = replay(build_games(load_schedules()))
tg = build_team_games(games)
derived = {"games": games, "team_games": tg, "snapshots": build_grid(games, tg, sparse)}
```

### WR-06: A negative-weight factor ships to users on a noise-level backtest gain

**File:** `pipeline/weights.yaml` (consumed by `pipeline/src/fgs/score.py:79-86`; justified in `pipeline/BACKTEST_LOG.md`)
**Issue:** `last16 = -1.25` is in the production score because the walk-forward ΔSpearman was +0.0033 (0.512 to 0.515) and ΔR² was +0.0042. No uncertainty estimate was computed, although `per_season` blocks are already in `backtest.json`. A gain of a few thousandths pooled over about 10k correlated, overlapping-window rows is well within season-to-season noise. The user-facing effect is real: holding Elo fixed, winning more recent games *lowers* the feel-good score. Phase 4's factor bars will show "Last 16 games" as a negative contribution for hot teams. That contradicts the project's stated purpose (a momentum-weighted score) and will read as a bug.
**Fix:** Before keeping the factor, report the per-season ΔSpearman distribution (mean, SE, and the count of seasons improved out of 19) in BACKTEST_LOG.md, and require for example SE-adjusted ΔSpearman > 0. Otherwise set `last16: 0` (or drop it) until Phase 6. At minimum, add a guard in `propose_weights` output that flags a factor whose delta is under 2 SE.

### WR-07: `last` is reused for two meanings in `run_backtest`

**File:** `pipeline/src/fgs/backtest.py:369, 384`
**Issue:** `last = seasons[-1]` (an int season bound used to seal the holdout) is overwritten inside the ridge loop by `pred, bs, bn, last = _ridge_walk_forward(...)`, which is a dict or None. Nothing reads `last` after line 384 today. But this function enforces the holdout seal, and any later edit that uses `last` below the loop (for example to filter `games` again or to label output) will silently compare seasons against a dict or None. That is a latent seal bypass or crash.
**Fix:** Rename one of them: `last_season = seasons[-1]` and `pred, bs, bn, last_fold = ...`.

## Info

### IN-01: Exported contribs contain JSON `-0.0`

**File:** `pipeline/src/fgs/export.py:63`
**Issue:** With a negative weight, `-1.25 * 0.0` is `-0.0`, and small negatives round to `-0.0`. These are serialized as `-0.0` (confirmed: `"last16":-0.0` in `web/public/data/snapshots/1999.json` and others). In JS, `Intl.NumberFormat().format(-0)` renders "-0", which Phase 4 factor bars will display.
**Fix:** `round(float(v), 2) + 0.0` normalizes `-0.0` to `0.0`. Alternatively use `0.0 if abs(x) < 0.005 else round(x, 2)`.

### IN-02: Ridge composite "R²" is squared Pearson, not out-of-sample R²

**File:** `pipeline/src/fgs/backtest.py:128-133, 222-223`
**Issue:** For walk-forward ridge predictions, `corr²` ignores intercept and scale miscalibration, so it overstates out-of-sample R². The README documents it as squared Pearson. Even so, the ΔR² values in BACKTEST_LOG are read as fit improvement.
**Fix:** For `pred_*` columns, also report `1 - SSE/SST` on the test rows.

### IN-03: Ridge-composite Brier calibrates its logistic on in-sample ridge fits

**File:** `pipeline/src/fgs/backtest.py:349-354`
**Issue:** The fold's ridge was fit on targets that contain the very training games the logistic is then fit on. The calibration is slightly optimistic compared with how it is applied to the out-of-sample test season. The effect is negligible at this n, but it differs from the scheme used for the baseline candidates.
**Fix:** Document this, or fit the logistic on LOSO ridge predictions.

### IN-04: `loadHistory` cache ignores `meta.generated_at` changes

**File:** `web/src/lib/data.ts:29-39`
**Issue:** The cache is a single promise regardless of `meta`. If meta is reloaded in-session with a new `generated_at`, the stale history is returned even though the URL is cache-busted.
**Fix:** Key the cache by `generated_at`: `if (historyCache && historyKey === meta.generated_at) return historyCache`.

### IN-05: Ridge "standardized inputs" are per-snapshot z, not globally standardized

**File:** `pipeline/src/fgs/backtest.py:245-252, 280-282`
**Issue:** CONTEXT asks for standardized ridge inputs. The pooled variance of `z_season_record` is below 1 because it is identically 0 at week 0 and compressed early in the season. So the same `alpha*n*I` penalizes it more than `z_elo`. This is harmless at the chosen alpha = 0.001·n, but it matters if the CV picks larger alphas once more factors exist.
**Fix:** Rescale the columns by their pooled training SD inside `ridge_fit`, then map the weights back. Or document that the penalty acts on per-snapshot z units.

---

_Reviewed: 2026-11-11T19:20:15Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

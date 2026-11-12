---
phase: 06-weight-freeze-methodology
reviewed: 2026-11-11T22:30:00Z
depth: standard
files_reviewed: 26
files_reviewed_list:
  - pipeline/src/fgs/backtest.py
  - pipeline/src/fgs/bootstrap.py
  - pipeline/src/fgs/cli.py
  - pipeline/src/fgs/export.py
  - pipeline/src/fgs/freeze.py
  - pipeline/src/fgs/holdout.py
  - pipeline/src/fgs/methodology.py
  - pipeline/src/fgs/paths.py
  - pipeline/src/fgs/score.py
  - pipeline/tests/test_backtest.py
  - pipeline/tests/test_bootstrap.py
  - pipeline/tests/test_export.py
  - pipeline/tests/test_freeze.py
  - pipeline/tests/test_holdout.py
  - pipeline/tests/test_leakage.py
  - pipeline/tests/test_methodology.py
  - web/src/App.svelte
  - web/src/components/MethodologyChart.svelte
  - web/src/components/MethodologyPage.svelte
  - web/src/components/SiteHeader.svelte
  - web/src/lib/data.ts
  - web/src/lib/methodology.test.ts
  - web/src/lib/methodology.ts
  - web/src/lib/router.test.ts
  - web/src/lib/router.ts
  - web/src/lib/types.ts
findings:
  critical: 0
  warning: 8
  info: 8
  total: 16
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-11-11T22:30:00Z
**Depth:** standard
**Files Reviewed:** 26
**Status:** issues_found

## Summary

Scope: `git diff 42e57aa~1 -- pipeline/src pipeline/tests web/src`. I checked the code against PREREGISTRATION.md, FREEZE_RESULT.json, HOLDOUT_RESULT.{md,json} and the exported `web/public/data/methodology.json`.

**Constraint followed:** none of the fixes below re-run, re-tune or refit the holdout. Findings about the holdout run itself are documentation fixes or guards for future runs only.

**Checked and found correct (no finding):**
- **Bootstrap pairing.** `paired_bootstrap` draws one index array per replicate and evaluates every stat on it, so the diffs are truly paired. Adding the `composite_novsexp` diagnostic stat does not change the RNG stream, because the draw happens before the stats are evaluated. The primary CI is therefore unaffected by the diagnostic.
- **Resampling units.** These match prereg §7: season blocks; team-season clusters (`franchise_id` within season); season-week clusters (`asof_week` within season).
- **Percentile CI.** It is a nan-aware `np.percentile` at [2.5, 97.5].
- **Verdict.** `verdict()` picks the wider CI. On the holdout, season-block width 0.0519 > team-season width 0.0517. Both include 0, so the verdict is "slight", which matches §8. PASS = point diff > 0, which matches §6.2.
- **Provenance is genuine.**
  - The PREREGISTRATION.md content at 42e57aa hashes to the recorded `f59ff7d6…`.
  - weights.yaml at 41e1e54 hashes to the recorded `44b4c7b9…`.
  - Prereg (42e57aa) comes before freeze (41e1e54), which comes before the result (f2c0273).
  - No `pipeline/src` change between the recorded HEAD c7c5ef0 and now.
- **Frozen composite.** It is `features.composite` from `derive(scored=True)` with the yaml weights, which `evaluate_frozen` checks for equality. That is Σ round(w)·z with no intercept, per §3.
- **Brier maps.** Fit only on season ≤ 2021, per §5.3.
- **Snapshot and game counts.**
  - snapshots_n4 == snapshots_n8 (2287) is expected: both targets null out at < 2 games left.
  - Walk-forward has 5082 Brier games over 19 seasons vs 1136 over 4 holdout seasons. That is 267 vs 285 games per season (the 17-game era), not a population mismatch.
- **Agreement between files.** methodology.json factors, weights, fold signs, deltas and the holdout diff block match weights.yaml, FREEZE_RESULT.json and HOLDOUT_RESULT.json exactly.

**Remaining issues:**
- Holes in the "one-time" guard.
- A built-in asymmetry in the holdout Brier comparison that the published text doesn't disclose.
- Selective reporting of the Brier-vs-Elo CI.
- CI methods mixed across chart periods without a label.
- Unsigned diff rendering on the page.
- Note text that hard-codes claims instead of deriving them from values.

## Warnings

### WR-01: The one-time holdout guard keys only on HOLDOUT_RESULT.md and records prior runs only under `--force`

**File:** `pipeline/src/fgs/cli.py:471, 506-529`
**Issue:**
- `_cmd_holdout` refuses only when `HOLDOUT_RESULT.md` exists.
- It writes `HOLDOUT_RESULT.json` first (line 524) and the `.md` second (line 525).
- It reads the previous result into `reruns` only when `args.force` is set (line 507).

So if `render_markdown` or the `.md` write fails after the JSON is written, the next `fgs holdout` (no `--force`) re-evaluates silently. The same happens if the `.md` is deleted while the JSON or `data/derived/holdout.json` remains. Either way it overwrites the JSON with `rerun: false` and an empty `reruns` list. That defeats the "evaluated exactly once" audit trail that prereg §1.2 and §13.4 rely on.

This did not happen in the actual run: there is one commit for both files, the run was not rerun, and the sha values match. It is a guard defect for the record and for Phase 7+.
**Fix (for future runs, do not re-run now):**
```python
existing = [p for p in (paths.HOLDOUT_MD_PATH, paths.HOLDOUT_JSON_PATH, DERIVED_DIR / "holdout.json") if p.exists()]
if existing and not args.force:
    print(f"error: {ALREADY_HOLDOUT_MSG} ({', '.join(map(str, existing))})", file=sys.stderr)
    return 1
...
prev = json.loads(paths.HOLDOUT_JSON_PATH.read_text()) if paths.HOLDOUT_JSON_PATH.exists() else None
```
Also write to temporary files and `os.replace` both, so a crash can't leave one file without the other.

### WR-02: The composite's Brier logistic map is fit on in-sample composite values, which biases the holdout Brier comparison against the score

**File:** `pipeline/src/fgs/holdout.py:84-93, 212-216`
**Issue:** `_brier_maps` fits `logit(y ~ Δcomposite + home)` on next-game rows from 1999–2021. The frozen composite weights were fit on those same 1999–2021 snapshots (propose_weights). So the composite's training-period discrimination is in-sample. The fitted logistic slope is slightly too steep, and probabilities are slightly overconfident out of sample.

Elo has no outcome-fitted weights, apart from a few hyperparameters, so its map is close to honest. Walk-forward avoided this problem because each fold's ridge and map were fit only on seasons before S. The holdout doesn't.

This is faithful to prereg §5.3, so the evaluation is not wrong under the contract. But the published "Brier: score slightly worse than Elo (+0.0014)" is partly an artifact of this asymmetry, and that isn't disclosed anywhere: HOLDOUT_RESULT.md, README or the methodology page.
**Fix (documentation only, no re-run):** Add a fixed note to methodology.json `_notes` when `holdout` is present, and to the README "Does it work?" section. For example: "The holdout Brier maps were fit on 1999–2021, the same seasons the score's weights were fit on, so the score's single-game probabilities are slightly overconfident out of sample. Elo's are not. Read the Brier gap with that in mind." For any future holdout, pre-register maps fit on walk-forward (out-of-fold) composite values.

### WR-03: Holdout Brier and N=4 results are reported selectively or not at all on the site and in the README

**File:** `pipeline/src/fgs/methodology.py:190-203`; `web/src/components/MethodologyPage.svelte:131-138`; `README.md:92`
**Issue:**
- **README cherry-picks the CI.** HOLDOUT_RESULT gives Brier score − Elo = +0.0014 with season-block CI [+0.0004, +0.0030], which excludes 0 (the score is worse), and season-week CI [−0.0018, +0.0044]. README line 92 quotes only the season-week CI, the one that includes 0. For the Spearman diff, the README quotes both CIs.
- **The page never states the holdout Brier gap.** The "Does it work?" text gives only the Spearman N=8 diff. The `not_betting` note always cites walk-forward Brier (0.2112 vs 0.2178), even after the holdout exists. The holdout comparison (0.2097 vs 0.2242) is never stated in text.
- **The page never states the N=4 result.** The N=4 holdout diff (−0.0014, score below Elo) is not on the page.

Prereg §9.5 lists "Brier differences vs Elo and vs the spread, each with both CIs". §12 and the CONTEXT require honest reporting.
**Fix:** Report both Brier CIs in the README. In `_notes`, when `holdout` is present, use the holdout Brier values in `not_betting`. Add a holdout sentence with the N=4 diff and the Brier-vs-Elo diff, each with both CIs. Example: `"On 2022–25 the score's next-game Brier was {fmt_delta(bve)} vs Elo (season-block {ci}, season-week {ci})"`. This is reporting only; nothing is recomputed.

### WR-04: The chart and "The numbers" mix CI methods across periods without saying so

**File:** `pipeline/src/fgs/methodology.py:234-236, 248-250`; `web/src/components/MethodologyChart.svelte:94`; `web/src/components/MethodologyPage.svelte:157-161`
**Issue:** The `ci` field means different things in the two periods:
- Walk-forward: `ci` is `ci_season` (season block).
- Holdout: `ci` is `ci_cluster` (team-season for Spearman, season-week for Brier).

The chart draws both in one figure, and the caption just says "whiskers the 95% interval". Readers will compare whisker widths across periods, but they come from different resampling schemes. The holdout Spearman whiskers (cluster) are wider than season-block would give for composite (0.385–0.572 vs 0.410–0.555), which exaggerates the apparent jump in uncertainty. Also, the verdict was decided by the season-block diff CI, which is not the one plotted.
**Fix:** Pick one method for both periods; the cluster CI exists in FREEZE_RESULT as `ci_cluster`. Alternatively, label each period: `"Walk-forward 2003–21 (refit each season; season-block 95% CI)"` / `"Holdout 2022–25 (frozen weights; team-season 95% CI)"`, and say in the figcaption that the methods differ.

### WR-05: The holdout difference renders without a sign, and the CI ranges are ambiguous

**File:** `web/src/components/MethodologyPage.svelte:134-136`; `web/src/lib/methodology.ts:32-39`
**Issue:**
- **No sign on the difference.** It is rendered with `formatMetric(hoDiff.value, 3)`, which is unsigned. The page reads "Difference in rank correlation: 0.004" where the pipeline, README and HOLDOUT_RESULT all say "+0.0039".
- **Confusing ranges.** `formatCI` joins bounds with an en dash. Mixed-sign intervals come out as "−0.023–0.029", and an all-negative interval would be "−0.030–−0.010", which is hard to read.
- **Negative zero.** `formatMetric` turns a tiny negative such as −0.0004 into "−0.000".

The brief asked specifically about sign rendering.
**Fix:**
```ts
export const formatDelta = (x: number | null | undefined, dp = 3) =>
  x == null || !Number.isFinite(x) ? '—' : signed(x, dp)
export const formatDeltaCI = (ci?: [number, number] | null, dp = 3) =>
  ci ? `[${signed(ci[0], dp)}, ${signed(ci[1], dp)}]` : '—'
```
Use these for `hoDiff.value`, `hoDiff.ci_season` and `hoDiff.ci_cluster`. In `formatMetric`, normalize `-0.000` to `0.000`.

### WR-06: "Honest notes" hard-code directional claims instead of deriving them from the values

**File:** `pipeline/src/fgs/methodology.py:123-127, 133, 143-146`
**Issue:** The 06-04 decision says note text is "formatted only from each note's values". Several claims are fixed strings:
- **momentum:** "Hot records mostly fade … tend not to last" is emitted even if `_sign_words` returns "positive". That would produce self-contradicting text after any refit.
- **efficiency:** "adds about nothing once Elo is known". The delta (−0.00005) was measured when epa_traj joined eight other factors, not "given Elo". And the factor carries a weight of −0.33 with 19/19 sign agreement. It contributes about as much to the score as luck (−0.35), so "adds about nothing" overstates the case.
- **vs_exp:** "beating expectations tends to fade" is emitted regardless of the sign of `w`.

For the current frozen values the text is defensible. The issue is that it is not guarded.
**Fix:** Branch on the values. For example, emit "fade" wording only when every momentum weight rounds to ≤ 0; use `"tends to fade" if w < 0 else "tends to persist"` for vs_exp; for efficiency, say "adding it on top of the other factors changed the walk-forward rank correlation by {delta}" instead of "once Elo is known". Add a test that flips signs in a synthetic weights dict and asserts the wording follows.

### WR-07: The prereg-ordering guard only checks the adding commit, so later edits to PREREGISTRATION.md would pass and be mislabeled in provenance

**File:** `pipeline/src/fgs/holdout.py:427-435`; `pipeline/src/fgs/holdout.py:309` (render)
**Issue:** `git_state` uses `git log --diff-filter=A`, which returns only the commit that added the file, and checks that it is an ancestor of the latest weights.yaml commit. Suppose PREREGISTRATION.md were edited and committed after the freeze, for example to adjust the success rule once interim numbers were known. The `dirty` check (uncommitted only) and the `ordered` check would both still pass. Provenance would then print `sha256 … (commit <adding commit>)`, implying the hashed content is from that commit.

I verified that this did not happen: the file has exactly one commit, 42e57aa, and its content hashes to the recorded sha. This is a guard weakness for future holdouts.
**Fix:** Also require that the last commit touching the prereg is an ancestor of the weights commit, and record that commit:
```python
last = _git(root, "log", "-1", "--format=%H", "--", prereg_rel).stdout.strip()
out["prereg_last_commit"] = last or None
out["ordered"] = out["ordered"] and _git(root, "merge-base", "--is-ancestor", last, out["weights_commit"]).returncode == 0
```
Alternatively, refuse if `git log --format=%H -- PREREGISTRATION.md` returns more than one commit.

### WR-08: Provenance does not fingerprint the input data or the dependency lock

**File:** `pipeline/src/fgs/cli.py:509-516`
**Issue:** Provenance records the sha256 of the prereg and weights files, HEAD, and whether src was clean. It does not record:
- the nflverse cache (`data/cache/schedules.parquet`, pbp, win totals);
- the sim cache, which feeds po_trend;
- `uv.lock`.

All of these are gitignored or unchecked. nflverse revises schedules and pbp after the fact, and a polars change can alter tie ranking. The one-time result therefore can't be verified or reproduced later from its provenance, and nothing shows it ran on the same inputs as the freeze.
**Fix (future runs; document for this one):** Add `"inputs": {name: file_sha256(p) for p in sorted(CACHE_DIR.rglob("*.parquet"))}` and `"uv_lock_sha256"` to provenance. For the existing result, add a sentence to the README noting that input data was not fingerprinted.

## Info

### IN-01: Fold-sign consistency uses the raw sign while the displayed sign uses the rounded weight

**File:** `pipeline/src/fgs/freeze.py:61-68, 268-270`
**Issue:** `fold_sign_consistency` compares `np.sign(raw)`, but `sign` is `sign_of(round_weight(raw))`. If a weight rounds to 0.00, the page would show sign "0" / "No effect" next to "Same sign in k of n seasons", where k counts agreement with the raw nonzero sign. No current factor triggers this (the smallest is streak at −0.03).
**Fix:** Document the convention, or report fold agreement against `sign_of(raw)` explicitly in the label.

### IN-02: The bootstrap evaluation logic is duplicated, and private helpers are used across modules

**File:** `pipeline/src/fgs/holdout.py:112-132, 216`; `pipeline/src/fgs/freeze.py:159-217`
**Issue:**
- `holdout._spearman_eval` and `freeze._spearman_block` largely duplicate each other.
- `_ci` is defined twice.
- holdout calls private functions: `freeze._brier_block`, `backtest._p538` and `backtest._clean`.

Any drift between the copies would make walk-forward and holdout numbers incomparable.
**Fix:** Pull a single public `spearman_paired(d, y_col, xcols, diffs, B, seed)` into bootstrap or freeze and use it from both.

### IN-03: The page does not show `holdout.rerun` / `pass`

**File:** `web/src/lib/methodology.ts:90-93`
**Issue:** If a result were ever regenerated with `--force`, methodology.json would carry `rerun: true`, but the page would show the headline with no warning.
**Fix:** In `verdictLead` or the page, append "(re-run with --force; breaks the pre-registration)" when `m.holdout.rerun`.

### IN-04: `DiffMetric.value` is typed as non-null

**File:** `web/src/lib/types.ts` (DiffMetric)
**Issue:** The pipeline can emit `null` (`_sub` returns None, and `_clean` maps NaN to None), but the type is `number`.
**Fix:** Change it to `value: number | null`.

### IN-05: Hard-coded 2003 in the weights.yaml template

**File:** `pipeline/src/fgs/freeze.py:323`
**Issue:** The template contains `"(test seasons 2003-{hi}, …"` instead of using `season_config.FIRST_TEST_SEASON`.
**Fix:** Interpolate the constant.

### IN-06: The composite silently treats a null factor as 0

**File:** `pipeline/src/fgs/score.py:142`; `pipeline/src/fgs/holdout.py:158-173`
**Issue:** `pl.sum_horizontal` skips nulls. A partially missing factor in holdout seasons would quietly drop out of the frozen composite. In training, the ridge fit would have produced NaN for such rows. A read-only check of `data/derived/features.parquet` found 0 nulls for 2022–2025 in the factor columns, so this didn't affect the run.
**Fix:** In `evaluate_frozen`, assert there are no null `z_<factor>` values on the evaluated rows.

### IN-07: The `_weights_frozen` guard doesn't handle malformed YAML

**File:** `pipeline/src/fgs/score.py:98-106`; `pipeline/src/fgs/cli.py:381-386`
**Issue:** `load_weights_doc` catches only `FileNotFoundError`. A `yaml.YAMLError` propagates as a traceback out of the guard.
**Fix:** Catch `yaml.YAMLError` and re-raise it as a `ValueError` with a clear message.

### IN-08: `HOLDOUT_PENDING` text is duplicated

**File:** `pipeline/src/fgs/methodology.py:16`; `web/src/lib/methodology.ts:7`
**Issue:** The same sentence is defined in Python and TS, so the two can drift.
**Fix:** Have the page use the `holdout_pending` note from methodology.json only.

---

_Reviewed: 2026-11-11T22:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

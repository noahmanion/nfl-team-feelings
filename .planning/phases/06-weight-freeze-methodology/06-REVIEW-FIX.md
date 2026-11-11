---
phase: 06-weight-freeze-methodology
fixed_at: 2026-11-11T21:47:09Z
review_path: .planning/phases/06-weight-freeze-methodology/06-REVIEW.md
iteration: 1
findings_in_scope: 16
fixed: 14
skipped: 2
status: partial
---

# Phase 6: Code Review Fix Report

**Fixed at:** 2026-11-11T21:47:09Z
**Source review:** .planning/phases/06-weight-freeze-methodology/06-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 16 (8 warnings, 8 info)
- Fixed: 14 (all 8 warnings, plus IN-01, IN-03, IN-05, IN-06, IN-07, IN-08)
- Skipped: 2 (IN-02, IN-04)

**What was not touched:** `fgs holdout` was not re-run and `--force` was never used. These files are byte-identical to 04770c0: `pipeline/HOLDOUT_RESULT.md`, `pipeline/HOLDOUT_RESULT.json`, `pipeline/PREREGISTRATION.md`, `pipeline/weights.yaml` and `pipeline/FREEZE_RESULT.json`. Each holdout finding was fixed either in documentation (README, methodology.json notes, page text) or by hardening the guards for future runs.

**Checks after the fixes:**
- `uv run pytest -q`: 403 passed, up from the 387 baseline.
- `uv run fgs export`: regenerated `methodology.json`. In `meta.json` only `generated_at` changed. Committed as 183be37.
- Web on Node 22: `npm run test` passed 90 tests, `npm run check` reported 0 errors and `npm run build` succeeded.

## Fixed Issues

### WR-01: The one-time holdout guard keys only on HOLDOUT_RESULT.md

**Files modified:** `pipeline/src/fgs/cli.py`, `pipeline/tests/test_holdout.py`, `pipeline/tests/test_freeze.py`
**Commit:** 6de90ad
**Applied fix:**
- New `_holdout_artifacts()` helper. Three guards now count any existing result file as "already evaluated": `fgs holdout`, `fgs freeze` (post-holdout) and `backtest --include-holdout` (the unseal check). The files checked are `HOLDOUT_RESULT.md`, `HOLDOUT_RESULT.json` and `data/derived/holdout.json`, except that the unseal check skips the derived copy.
- The previous result is read from whichever JSON exists, so `reruns` is recorded even if the `.md` is gone.
- The markdown is rendered before anything is written. All three files are written to `.tmp` files and then moved into place with `os.replace`.
- Tests cover a JSON-only refusal, a derived-only refusal, a freeze refused on JSON only, a rerun recorded without the `.md`, and a render failure that writes nothing.
- The `test_freeze` guard fixture now also points `HOLDOUT_JSON_PATH` at tmp. Before, it would have read the real result.

### WR-07: The prereg-ordering guard only checks the adding commit

**Files modified:** `pipeline/src/fgs/holdout.py`, `pipeline/src/fgs/cli.py`, `pipeline/tests/test_holdout.py`
**Commit:** 794e27b
**Applied fix:**
- `git_state` now records `prereg_last_commit` and `prereg_commits`.
- It sets `prereg_unchanged` only when two things hold: exactly one commit touches the file, and the working file's sha256 equals the sha256 of `git show <adding commit>:./PREREGISTRATION.md`.
- `ordered` now requires both the adding commit and the last commit to be ancestors of the weights commit.
- `fgs holdout` refuses when `prereg_unchanged` is false, and provenance records both new fields.
- Tests cover an edit committed after the freeze, an edit committed before the freeze (ordered, but not the original text), and the CLI refusal.
- A read-only check on the real repo gives `prereg_unchanged=True`: one commit, 42e57aa, `ordered=True`.

### WR-08: Provenance does not fingerprint input data or the dependency lock

**Files modified:** `pipeline/src/fgs/holdout.py`, `pipeline/src/fgs/cli.py`, `pipeline/tests/test_holdout.py`, `README.md`
**Commit:** 22f09f5
**Applied fix:**
- New `holdout.input_fingerprints()` records, for future runs, `provenance.inputs = {cache: {relpath: sha256}, sim_cache: {...}, uv_lock_sha256}`.
- `render_markdown` prints a summary line for it.
- **The existing HOLDOUT_RESULT.json/.md were NOT altered.** They have no input fingerprints, and that can't be fixed after the fact. A README "Provenance gap" bullet discloses this.

### WR-06: "Honest notes" hard-code directional claims

**Files modified:** `pipeline/src/fgs/methodology.py`, `pipeline/tests/test_methodology.py`, `README.md`
**Commit:** 03005ee
**Applied fix:**
- New `describe_weight(w, folds)` builds the wording from the rounded size (near-zero, small, moderate or large), the sign, and the fold agreement (consistent, mostly consistent or inconsistent). Example: epa_traj now reads "a small but consistent negative weight (−0.33, same sign in 19 of 19 seasons)".
- The momentum note branches on sign: fade, carry on, mixed, or about nothing.
- The vs_exp note says fade, persist or about nothing to match its sign.
- The efficiency note no longer says "once Elo is known". It says the delta was measured "on top of the factors before it".
- The refit note's "2003–21" now comes from the FREEZE_RESULT seasons.
- Tests flip every sign and check that the wording follows. Further tests cover the mixed and near-zero cases and `describe_weight`.
- The README epa_traj line was reworded to match.

**Status: fixed, requires human verification.** This is wording logic, so please read the regenerated notes.

### WR-02: The composite's Brier map is fit on in-sample composite values

**Files modified:** `pipeline/src/fgs/methodology.py`, `pipeline/tests/test_methodology.py`, `README.md`
**Commit:** 1ef566d
**Applied fix:** A new `brier_maps` note appears when a holdout exists, and a matching README caveat was added. Both state:
- The maps were fit once on seasons ≤ 2021, as pre-registered.
- The score's weights were fit on the same seasons (1999–2021), so its map is in-sample. It is likely a little too steep, and its 2022–25 single-game chances are expected to be slightly overconfident.
- Elo's map was also fit on 1999–2021. Elo itself has no weights fit to those results: 538-style default K and season regression (`EloParams` defaults, never tuned) and a market-implied home edge. So only Elo's two-number map is in-sample.
- The walk-forward Brier numbers don't have this asymmetry.

The README also recommends out-of-fold maps for any future holdout.

### WR-05: Unsigned holdout difference and ambiguous CI ranges

**Files modified:** `web/src/lib/methodology.ts`, `web/src/lib/methodology.test.ts`, `web/src/components/MethodologyPage.svelte`
**Commit:** 55813f0
**Applied fix:**
- New `formatDelta` (+0.004) and `formatDeltaCI` ("−0.023 to +0.029").
- `formatCI` now joins bounds with " to " rather than an en dash.
- `formatMetric` normalizes −0.000 to 0.000.
- The holdout difference and both of its intervals now use the signed formatters.
- The helpers live in the existing `methodology.ts`, so `format.ts` was not touched; another executor is editing it.

### WR-03: Holdout Brier and N=4 results reported selectively

**Files modified:** `pipeline/src/fgs/methodology.py`, `pipeline/tests/test_methodology.py`, `README.md`, `web/src/components/MethodologyPage.svelte`
**Commit:** 941555e
**Applied fix:**
- **New `holdout_detail` note.** It gives the N=4 difference, −0.0014, with season-block CI −0.0187 to +0.0161 and team-season CI −0.0234 to +0.0203. It also gives Brier vs Elo: 0.2242 vs 0.2228, a difference of +0.0014, with season-block CI +0.0004 to +0.0030 and season-week CI −0.0018 to +0.0044. It says when an interval excludes zero.
- **`not_betting` uses holdout Brier values when a holdout exists.**
- **README** reports both Brier CIs, says the season-block one excludes 0, and adds an N=4 bullet with both CIs.
- **Page** "Does it work?" gains a sentence with the N=4 difference and the Brier-vs-Elo difference, each with both intervals and an "excludes zero" flag.

### WR-04: Mixed CI methods across chart periods without a label

**Files modified:** `pipeline/src/fgs/methodology.py`, `pipeline/tests/test_methodology.py`, `web/src/lib/methodology.ts`, `web/src/lib/methodology.test.ts`, `web/src/components/MethodologyChart.svelte`, `web/src/components/MethodologyPage.svelte`
**Commit:** b77ed8e
**Applied fix:**
- methodology.json now has a `ci_method` per period: walk-forward is season-block for both metrics; the holdout is team-season for Spearman and season-week for Brier.
- New `intervalCaption()` builds the figcaption. It names the method for each period and warns that whisker widths aren't comparable when the methods differ.
- "The numbers" list shows the method next to each interval.
- `types.ts` was not edited because another executor owns it. `ci_method` is read structurally inside `methodology.ts`.

### IN-01: Fold-sign uses raw sign, displayed sign uses rounded weight

**Files modified:** `web/src/components/MethodologyPage.svelte`
**Commit:** 5aa95c9
**Applied fix:** This was documented, not changed. The factor explainer now says "Same sign" is measured against the final unrounded fit, so a weight that rounds to 0.00 can still show a count.

### IN-03: Page does not show `holdout.rerun`

**Files modified:** `web/src/lib/methodology.ts`, `web/src/lib/methodology.test.ts`
**Commit:** 9c569ea
**Applied fix:** When `rerun` is true, `verdictLead` appends "(Re-run with --force, which breaks the pre-registration.)". A test covers it.

### IN-05: Hard-coded 2003 in the weights.yaml template

**Files modified:** `pipeline/src/fgs/freeze.py`
**Commit:** d96b048
**Applied fix:** The template now uses `season_config.FIRST_TEST_SEASON`. Rendering the existing FREEZE_RESULT still gives the same "test seasons 2003-2021" line, and weights.yaml was not rewritten.

### IN-06: Composite silently treats a null factor as 0

**Files modified:** `pipeline/src/fgs/holdout.py`, `pipeline/tests/test_holdout.py`
**Commit:** b0ac385
**Applied fix:**
- `evaluate_frozen` raises `ValueError` when a `z_<factor>` column is missing, or when any evaluated row has a null or NaN in one.
- The test nulls one factor for a stand-in season and expects the raise.
- `score.composite` was left as is, to avoid changing live-season behaviour.

### IN-07: `_weights_frozen` guard doesn't handle malformed YAML

**Files modified:** `pipeline/src/fgs/score.py`, `pipeline/src/fgs/cli.py`, `pipeline/tests/test_holdout.py`
**Commit:** f94b589
**Applied fix:**
- `load_weights_doc` turns `yaml.YAMLError` into `ValueError("weights file is not valid YAML: ...")`.
- `_weights_frozen` prints that error as a warning when the file exists, so a guard's "not frozen" message isn't misleading.
- A test covers it.

### IN-08: `HOLDOUT_PENDING` text duplicated

**Files modified:** `web/src/lib/methodology.ts`, `web/src/lib/methodology.test.ts`, `web/src/components/MethodologyPage.svelte`
**Commit:** 9c569ea
**Applied fix:**
- The TS `HOLDOUT_PENDING` constant was removed. `verdictLead` now uses the `holdout_pending` note from methodology.json, so the Python constant is the only copy.
- The page skips the paragraph when the lead is empty.

### Regenerated data

**Files modified:** `web/public/data/methodology.json`, `web/public/data/meta.json` (only `generated_at` changed)
**Commit:** 183be37

## Skipped Issues

### IN-02: Bootstrap evaluation logic duplicated, private helpers used across modules

**File:** `pipeline/src/fgs/holdout.py:112-132`, `pipeline/src/fgs/freeze.py:159-217`
**Reason:** This refactor is not trivial. The two Spearman evaluators differ in their inputs: the holdout one handles the diagnostic `composite_novsexp` and its diffs. Merging them means touching the code that produced the frozen walk-forward and holdout numbers, so it was skipped as instructed.
**Original issue:** `holdout._spearman_eval` and `freeze._spearman_block` largely duplicate each other, `_ci` is defined twice, and holdout calls private `freeze`/`backtest` helpers.

### IN-04: `DiffMetric.value` typed as non-null

**File:** `web/src/lib/types.ts`
**Reason:** `types.ts` is being edited concurrently by the Phase 7 executor (07-02) and is off-limits for this run. The new `formatDelta` / `formatDeltaCI` helpers already accept `null`/`undefined` and render "—", so the runtime is safe. The one-line change to `value: number | null` should be made once 07-02 releases the file.
**Original issue:** The pipeline can emit `null` for `DiffMetric.value`, but the TS type says `number`.

---

_Fixed: 2026-11-11T21:47:09Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

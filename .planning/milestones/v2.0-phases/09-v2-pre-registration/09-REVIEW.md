---
phase: 09-v2-pre-registration
reviewed: 2026-11-11T19:30:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - pipeline/PREREGISTRATION_V2.md
findings:
  critical: 4
  warning: 9
  info: 3
  total: 16
status: issues_found
---

# Phase 9: Code Review Report

**Reviewed:** 2026-11-11T19:30:00Z
**Depth:** standard
**Files Reviewed:** 1
**Status:** issues_found

## Summary

I reviewed `pipeline/PREREGISTRATION_V2.md` (adding commit 9c32319, committed alone, 1 commit) as a buildable contract. I checked it against `pipeline/src/fgs/**`, git history, and `09-CONTEXT.md`.

**What checks out.** These references match the code or git exactly:

- `backtest.TARGET_TEXT`, verbatim.
- `ALPHA_GRID = (0.0, 1e-3, 1e-2, 1e-1, 1.0)`, multiplied by n inside `ridge_fit`.
- `choose_alpha`: LOSO, pooled SSE, strict `<` so ties keep the earlier and smaller alpha.
- `logit_fit`: Newton/IRLS, 25 iterations, intercept last, fractional y.
- `_ridge_walk_forward`: fits on `season < S` with y8 present.
- `pbp.scrimmage`: every filter as listed. `WP_LO, WP_HI = 0.05, 0.95` via `is_between`, which is inclusive.
- `team_game_epa.net_epa = off_epa - def_epa`.
- `KNOWN_NO_PBP`: the three game ids.
- `LUCK_N, ONE_SCORE = 16, 8`.
- The `_vs_exp` formula.
- `vegas_expectations` normalization, with polars `mean().over("season")` ignoring nulls, so "teams that have a line" is right.
- `RAW_TO_FRANCHISE` = OAK/SD/STL.
- `DRAFT_GATE_FOLDS = 0.60`. 14/23 = 0.609 is the smallest count that is at least 0.60.
- `season_config` constants.
- `git_state(prereg_rel, weights_rel)`.
- The bootstrap API names.
- The sha256 of `weights.yaml` at 41e1e54 (`44b4c7b9…6320`). Later commits only append `offseason:`.
- The sha256 and adding commit of `PREREGISTRATION.md`.
- Every v1 holdout number: +0.0039, [-0.0211, +0.0306], 2287, Brier 0.2242/0.2228/0.2097, vs_exp -1.22 with 18/19 folds.
- The calendar dates: Thu 2027-09-09 and Sun 2028-02-13.

**The problems are in the contract logic, not the citations:**

- **Freeze-commit hole.** "Freeze commit" is defined two different ways, and post-freeze weight or code changes are not void.
- **Forking paths in the drop rules.** It is ambiguous what "without MODEL-V2-03" means, and what the final model is after a drop.
- **Undefined 2028 contingency.** The pre-registered fallback season has no vs_exp_v2 input source.
- **Weaker integrity points.** The preseason-line inputs are not pinned, the timestamp witness is self-reported, and H3 has no defined metric.

**Constraint on every fix.** The file can't be edited (sections 1.3 and 20). Section 17.2 lists only four deviation types, and none of them is "clarification". Section 1.3 does say "Errata and allowed deviations are recorded only in … DEVIATIONS.md", but it never defines what an erratum is (see WR-09). So for each finding below I give a remedy that leaves the file alone.

The most defensible route, while **no v2 number exists yet**, is a committed interpretation note in the v2 implementation milestone's planning docs, such as that milestone's CONTEXT.md. It should:

- be committed and pushed before any v2 feature or metric code runs,
- choose the most conservative reading,
- be enforced by a code guard plus a test,
- be copied into `HOLDOUT_V2_RESULT.md` as "pre-data interpretations".

This doesn't amend the contract. It records which reading was chosen, before any data could have influenced the choice. Whether the same text can also go in `PREREGISTRATION_V2_DEVIATIONS.md` as an "erratum" depends on how WR-09 is read. I recommend not using DEVIATIONS.md for this, because 17.2 is a closed list.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: "Freeze commit" has two definitions, and post-freeze weight or code changes are not void (holdout leakage hole)

**File:** `pipeline/PREREGISTRATION_V2.md:19-21, 44-47, 244-251, 276-279`

**Issue:** The two definitions disagree:

- Section 1.4 defines the freeze commit as "the commit that **adds**" `weights_v2.yaml`.
- Section 19.4 says the guards are "the same checks as `fgs.holdout.git_state` … `weights_rel="weights_v2.yaml"`". `git_state` sets `weights_commit` from `git log -1 --format=%H -- weights_rel` (holdout.py:476), which is the **latest** commit touching the file, not the adding commit.

Nothing in the file requires `weights_v2.yaml` to have exactly one commit, unlike the prereg itself. Section 16.1 voids changes only to "the v2 definitions, the fit procedure, the target or the frozen (a, b)". It does not void changes to the 12 weights, the alpha, the drop-rule outcomes, or the v2 source code.

**Attack path:**

1. Freeze in August 2027.
2. Watch weeks 1–6.
3. "Fix a bug" in the good_loss_luck implementation. The prose definition is unchanged, so 16.1 is not triggered.
4. Re-run `fgs freeze-v2` and recommit `weights_v2.yaml`.

Under the 1.4 definition, the adding commit's timestamp still predates kickoff, so all of 2027 stays eligible.

Under the `git_state` definition, the freeze moves past kickoff and section 3.5 pushes the holdout to 2028. That outcome is safe, but the two readings give different holdouts. The implementer gets to pick one after seeing 2027 data.

`freeze-v2` also has no "refuse a second run" guard; only `holdout-v2` has one (19.3).

**Materiality:** Material. It decides which season is the holdout, and whether a post-peek refit is legal.

**Fix (no edit to the prereg):** In the v2 milestone's pre-data interpretation note, adopt the conservative union of both readings and enforce it in code:

```python
# fgs/holdout_v2.py (future milestone)
st = holdout.git_state(root, prereg_rel="PREREGISTRATION_V2.md", weights_rel="weights_v2.yaml")
adds = _git(root, "log", "--diff-filter=A", "--format=%H", "--", "weights_v2.yaml").stdout.split()
touch = _git(root, "log", "--format=%H", "--", "weights_v2.yaml").stdout.split()
if len(adds) != 1 or len(touch) != 1:
    raise SystemExit("weights_v2.yaml must have exactly one commit (freeze commit); evaluation void")
freeze = adds[0]
# also: `git diff --quiet <freeze> HEAD -- src/fgs` for the v2 + v1-comparator code paths, else void
```

`freeze-v2` must refuse when `weights_v2.yaml` already exists in history. Record the freeze-to-HEAD diff of `src/` in `HOLDOUT_V2_RESULT.json`, so any post-freeze code change is visible.

### CR-02: The MODEL-V2-03 ablation has two incompatible readings ("without it" = no vs_exp, or v1 vs_exp)

**File:** `pipeline/PREREGISTRATION_V2.md:158-165, 169-170`

**Issue:** The two rules point different ways:

- Section 9.1/9.2.2 judges each candidate "leave-one-input-out", using ΔSpearman of "the full set with the input minus the set without it". For MODEL-V2-03, the literal "set without it" is the 11-factor set with **no** vs_exp column.
- Section 9.4 says that if V2-03 is dropped, the factor reverts to v1 `vs_exp`. So the counterfactual the rule actually decides between is vs_exp_v2 versus v1 vs_exp, a swap, not vs_exp_v2 versus nothing.

The two readings test different hypotheses.

- **Reading A:** "does any expectation term help?" v1 found vs_exp strongly useful: -1.22, 18/19 folds. So reading A almost guarantees V2-03 passes, even if Vegas-sourcing is worse than v1's mixed sourcing.
- **Reading B:** "is the Vegas re-sourcing better?"

Criterion 9.2.3 (fold-sign agreement) means the same thing under both readings, but 9.2.2 does not. An implementer who runs both and sees which one passes has a forking path.

**Materiality:** Material. It can change whether vs_exp_v2 or v1 vs_exp ships in the frozen model.

**Fix (no edit):** Pick reading B (the swap) in the pre-data interpretation note. It is the only reading consistent with 9.4's fallback, and with H3's framing in 12.3 ("vs_exp_v2 versus v1 `vs_exp`"). Implement `without(V2-03)` as the factor list with `vs_exp_v2` replaced by `vs_exp`, and add a unit test that pins this list. Report reading A's number in the result file, labelled non-gating, so it is transparent and cannot be cherry-picked.

### CR-03: After a drop, the final model is unspecified (zero a weight, or refit without the factor)

**File:** `pipeline/PREREGISTRATION_V2.md:19-21, 149-151, 168-173`

**Issue:** The file says three things that don't fit together:

- **1.4:** `weights_v2.yaml` holds "the **12** factor weights".
- **9.3:** a failed candidate is "set to weight 0".
- **9.5 and 9.4:** a dropped V2-01 is "removed from the factor list", and a dropped V2-03 "reverts to v1 vs_exp".

9.4 cannot be done by zeroing: v1 vs_exp has no fitted weight in the 12-factor fit, so a refit is required.

For V2-01, "weight 0" in the 12-factor ridge fit and "removed, then refit 11 factors with a re-chosen alpha" give different weights for every correlated factor. good_loss_luck is correlated with luck, sow, mov and epa_traj, so those weights would differ. Only 9.6, where both inputs are dropped, explicitly says "refit".

**Materiality:** Material. It changes the frozen weights that reach the holdout.

**Fix (no edit):** In the interpretation note, choose "refit the full section 8.2 procedure on the surviving factor list". Fresh `choose_alpha`, 2 dp rounding, and the remaining factors in section 8.1 order. This is the only rule that 9.4, 9.5 and 9.6 all agree with.

Record in `weights_v2.yaml`:

- the surviving factor list,
- each dropped candidate with its ΔSpearman and fold-sign count,
- a note that the "12 factor weights" of 1.4 means "the factor weights of the surviving list".

`freeze-v2` should assert `len(weights) in {10, 11, 12}`, consistent with which drops happened.

### CR-04: The pre-registered 2028 fallback holdout has no vs_exp_v2 input source

**File:** `pipeline/PREREGISTRATION_V2.md:56-57, 126-130, 199-200, 261-264`

**Issue:** Section 3.5 makes the full 2028 season the primary holdout if the freeze misses the 2027 deadline. But:

- **7.2** lists Vegas sources only for 2003–2020, 2021–2025, and "2026 and 2027". It has nothing for 2028.
- **7.3** allows the model expectation only for 1999–2002, or for a missing line as an "allowed deviation (section 17)".
- **17.2.3** allows only "a missing **2027** preseason line".
- **12.3 / H3** checks for "more than 4 teams lack a **2027** preseason line".

So under the 3.5 contingency, vs_exp_v2 for 2028 has no defined source. Whether 2028 uses Vegas lines (committed when?) or model expectations would be decided after the 2027 freeze. That is a forking path inside a contingency the file itself pre-registers.

**Materiality:** Material, conditional on missing the 2027 deadline. Under the contingency it changes a factor in the primary model's holdout inputs.

**Fix (no edit):** The simplest safe remedy is operational: freeze well before the first 2027 kickoff, so 3.5 never fires, and make the guard fail loudly if it would.

If the contingency becomes plausible, write a pre-data interpretation note before any v2 code exists. It should state that every "2027" in 7.2, 12.3 and 17.2.3 means "the primary holdout season", which is the reading that 14's `{season}` placeholder implies.

Whether that substitution is an "allowed deviation" is unclear. 17.2.4 allows "the section 3.5 move", and the move arguably implies the substitution, but the file never says so. If this is ever invoked, record it in DEVIATIONS.md under 17.2.4, citing the note.

## Warnings

### WR-01: The 2026 preseason-line requirement can't be met, and 7.3 cites a deviation that section 17 doesn't grant

**File:** `pipeline/PREREGISTRATION_V2.md:71, 126-130, 261-262`

**Issue:** 7.2 requires 2026 lines "committed before that season's Week 1 kickoff". 2026 Week 1 has already passed (today is week 10), and `pipeline/inputs/` does not exist. So the rule can't be satisfied for 2026.

7.3 routes any missing line to the model expectation "as an allowed deviation, section 17". But 17.2.3 covers only 2027. 2026 rows feed:

- the never-gating secondary slice (3.7, 15.5),
- the shadow display (18),
- 2027 week-0 features only through cross-season windows. vs_exp is per-season, so the 2027 vs_exp_v2 values are not affected.

**Materiality:** Cosmetic for the H1 verdict. Material for the 2026 secondary slice and shadow values.

**Fix (no edit):** Pre-data interpretation note: 2026 vs_exp_v2 uses the model expectation for every team, and the result file labels it this way. Do not backfill 2026 Vegas lines and present them as "committed before kickoff". Do not file this as a 17.2 deviation, because 17.2.3 does not cover it.

### WR-02: H3 has no metric, and its holdout meaning when V2-03 is dropped is undefined

**File:** `pipeline/PREREGISTRATION_V2.md:198-200, 233`

**Issue:** H3 says "vs_exp_v2 versus v1 `vs_exp` … in the dev walk-forward and on the holdout" and names no statistic. Candidates include:

- the single-factor Spearman,
- ΔSpearman of the composite with one or the other,
- a frozen-weight swap,
- a refit swap.

It also doesn't say what H3 means on the holdout when V2-03 has been dropped. In that case vs_exp_v2 has no frozen weight.

**Materiality:** Material for a secondary hypothesis (never gating). It is a forking path.

**Fix (no edit):** Pre-data note. Define H3 as the paired ΔSpearman N=8 on identical eligible rows between two models:

- the frozen v2 model,
- the same section 8.2 procedure refit on ≤2025 with `vs_exp_v2` swapped for `vs_exp`.

The refit uses dev data only and is done at freeze time. Store both sets of weights in `weights_v2.yaml`, so no holdout refit is needed. This holds regardless of the drop outcome.

### WR-03: Preseason-line inputs are not pinned before the ablations, and the source is unspecified (dev leakage hole)

**File:** `pipeline/PREREGISTRATION_V2.md:71, 123-128, 24-25`

**Issue:** `win_totals_2021plus.csv` does not exist yet; Phase 11 creates it. The prereg pins neither its content (sha256) nor its source rules. Unspecified are:

- which book or aggregator,
- opening versus closing preseason total,
- whether to use `line` alone or adjust for over/under juice (v1 uses `line` only),
- the column schema and team codes (`LV` vs `OAK`, `LA`/`LAR`).

None of those rules exist for the 2026/2027 lines either, nor does a file path. Nothing in section 19 verifies "committed before Week 1 kickoff".

The file feeds vs_exp_v2 for 2021–2025, and so the drop-rule ablation. An implementer could revise those 20 seasons×teams numbers after seeing the ΔSpearman results, and no rule would be broken.

Section 1.2's "sha256 of the evaluation data" is also undefined. v1's `fingerprint` covers the nflverse cache, the sim cache and `uv.lock`. It would not cover `pipeline/inputs/*.csv`.

**Materiality:** Material. These are inputs to the drop rules and the holdout features.

**Fix (no edit):** Make the v2 milestone's first commit record the sha256 of `win_totals_2021plus.csv` before any v2 code runs. Have `freeze-v2` refuse if the file's hash differs. Include `pipeline/inputs/` in the result's input fingerprints.

For 2027 lines, require a separate file such as `pipeline/inputs/win_totals_2027.csv`. Its adding-commit committer time must be before the first 2027 kickoff and before or equal to the push witness, and `holdout-v2` should check this. Document the source rule (book, opening or closing, `line` only) in the pre-data note.

### WR-04: Kickoff eligibility relies on a self-reported committer timestamp, and the "independent witness" is never recorded

**File:** `pipeline/PREREGISTRATION_V2.md:44-47, 58-59, 24-25`

**Issue:** `%cI` can be set arbitrarily (`GIT_COMMITTER_DATE`). Section 3.6 says the push time is "an independent witness", but:

- no rule records it,
- 1.2 doesn't list it among the result-file fields,
- no void condition fires if the push happens after the deadline.

GitHub's events API keeps push events for only about 90 days. By February 2028, the push time of an August 2027 freeze can't be recovered unless it was captured at the time.

**Materiality:** Material for integrity. It doesn't change the build.

**Fix (no edit):** When `freeze-v2` runs, immediately push and capture the witness. Use either the `gh api repos/{owner}/{repo}/activity` / events entry for the push, or a signed tag. Write it into a committed `FREEZE_V2_WITNESS.json`. `holdout-v2` should read that file and use `min(...)` / `max(committer, witness)` as the effective freeze time.

### WR-05: "Following the draft_gate precedent" can be read as importing its extra conditions; sign-tie handling is unspecified

**File:** `pipeline/PREREGISTRATION_V2.md:166-167`

**Issue:** `backtest.draft_gate` also requires:

- `final_w > 0`,
- `round(final_w, 2) > 0`,
- wk0 Δ > 0.

9.2's "if and only if all three hold" suggests those are not imported, but "following the precedent" leaves the question open.

Two edge cases are also unspecified:

- `np.sign(0.0)` matches neither sign.
- If `_ridge_walk_forward` skips a fold (`continue` when `tr` or `te` is empty), there are fewer than 23 folds. "14 of 23" is then ambiguous: keep the absolute 14, or switch to at least 60% of n?

**Materiality:** Material at the margin, for whether a candidate is kept.

**Fix (no edit):** Pre-data note covering four points:

- only the three listed criteria apply;
- the comparison is `np.sign(fold_w) == np.sign(final_w)` exactly as in `draft_gate`, so a zero final weight passes only on zero fold weights;
- fewer than 23 folds is a hard error, not a reweighted threshold;
- a final weight that rounds to 0.00 is kept as 0.00, per 8.2.5.

### WR-06: Frozen (a, b) fit on 1999–2025 is used inside the 2003–2025 walk-forward folds (accepted look-ahead in the drop-rule evidence)

**File:** `pipeline/PREREGISTRATION_V2.md:90-96`

**Issue:** For fold S=2003, p_deserved uses (a, b) learned from 2003–2025 game outcomes. Section 5.8 accepts this. It is still look-ahead, and it leans toward keeping V2-01. Because each game contributes two symmetric rows, the intercept is exactly 0 at the MLE, so the leak is confined to b. That makes it small, but it is nonzero.

**Materiality:** Cosmetic for the build, since it is pre-accepted and cannot change. It is material to how the 9.2.2 evidence should be read.

**Fix (no edit):** In the drop-rule report, also show ΔSpearman with a per-fold (a, b) fit on `season < S`, labelled diagnostic and non-gating. That quantifies the look-ahead without changing the contract.

### WR-07: The verdict rule doesn't cover an undefined or degenerate CI

**File:** `pipeline/PREREGISTRATION_V2.md:222-224`

**Issue:** `slight` is defined as "diff > 0 and CI includes 0". Two cases have no wording:

- diff > 0 with a `None` CI (every bootstrap draw undefined; `percentile_ci` returns None),
- a percentile CI that lies entirely below 0 while the point diff is > 0.

v1's `holdout.verdict` falls through to "slight" in both cases. A v2 implementer could reasonably code "not determinable" instead.

**Materiality:** Material only in edge cases.

**Fix (no edit):** Pre-data note: reuse v1 `holdout.verdict` semantics with the single team-season CI, so `yes` iff diff > 0 and the CI is present and `ci[0] > 0`, and otherwise `slight` when diff > 0. Add a unit test for the None-CI path.

### WR-08: "Metric" in 16.2/19.2 is undefined, while section 18 requires v2 to run in shadow on 2026–2027

**File:** `pipeline/PREREGISTRATION_V2.md:246, 267-268, 273`

**Issue:** Shadow mode computes v2 scores on 2026 and 2027 seasons. Existing v1-style tooling (`insights`, the export-side callouts, the methodology page) may compute rank comparisons or accuracy figures on the live season. It is unclear whether those count as "a metric on a season >= 2026", which would void the evaluation. One reading is "anything compared against a target or outcome". Another is "only `backtest`/`holdout`-module statistics".

**Materiality:** Material. A careless shadow job could void the evaluation, or the void condition could be argued away.

**Fix (no edit):** Pre-data note: a "metric" is any function of v2 values together with game outcomes after the snapshot. That covers targets, results, Brier, Spearman, and win/loss tallies. The shadow pipeline may compute only as-of scores, and it must not import `fgs.backtest` or `fgs.holdout`. Enforce this with a `test_leakage.py`-style import firewall for the v2 shadow module.

### WR-09: Section 1.3 mentions "errata" but section 17 defines no errata category, so pre-freeze clarifications have no sanctioned channel

**File:** `pipeline/PREREGISTRATION_V2.md:27-28, 253-263`

**Issue:** 1.3 says "Errata and allowed deviations are recorded only in … DEVIATIONS.md (section 17)". But 17.2 is a closed list of four deviations, and the file never defines an erratum. CR-01 through WR-08 all need some clarification. One reading says errata are allowed, by 1.3. The other says they are not, by 17.2. This meta-ambiguity is itself a forking path.

**Materiality:** Material, because it determines how every other finding can be resolved.

**Fix (no edit):** Treat 17.2 as closed. Resolve ambiguities only through the pre-data interpretation note. It must be committed and pushed before any v2 feature or metric code exists, as covered by the v2 milestone's CONTEXT/PLAN, and be quoted in the result files. Do not write DEVIATIONS.md entries for clarifications. If a clarification would change what gets evaluated in a way the note can't settle without data, the only clean route is section 6.4's mechanism: a new pre-registration (v3). Under 1.3 this file can never be re-added or replaced.

## Info

### IN-01: `features.composite` does not exist; the comparator column should be `composite_inseason`

**File:** `pipeline/PREREGISTRATION_V2.md:184-188`

**Issue:** The function is `score.composite` (score.py:137). `derive(scored=True)` then runs `score.apply_offseason`, which overwrites `composite` whenever the offseason draft weight is nonzero. Today `offseason.draft.weight` is 0.00, so `composite == composite_inseason`. The text says "the comparator is the in-season composite", so the exact column is `composite_inseason`. holdout.py's docstring uses the same `features.composite` shorthand.

**Materiality:** Cosmetic today.

**Fix:** The v2 evaluator should read `composite_inseason`, or call `score.composite` with `load_weights()` directly, and assert that `weights.yaml`'s `weights:` block hashes to the 41e1e54 values.

### IN-02: "-0.00 is normalized to 0.00" is not v1 behavior, so it is not "verbatim"

**File:** `pipeline/PREREGISTRATION_V2.md:142, 149`

**Issue:** v1 `format_proposal` uses `f"{round(v, 2):.2f}"`, which prints `-0.00`. The normalization is new, though harmless (−0·z = 0).

**Materiality:** Cosmetic.

**Fix:** Implement the normalization as written. It has no numeric effect.

### IN-03: The window ordering for good_loss_luck should reuse v1's `_per_game` sort

**File:** `pipeline/PREREGISTRATION_V2.md:75-79, 87-89`

**Issue:** "Keyed on `season*100 + asof_week`" does not settle the order within one key. A postponed game can share a key with a later game. v1 sorts by `["franchise_id", "key", "gameday", "gametime", "game_id"]` (`features._PLAY_ORDER`). The rule that games without net_epa "drop out without extending the window" also requires the window to be taken over *played* games first, with the filter applied afterwards. Filtering to games with pbp first and then taking the last 16 gives a different window.

**Materiality:** Cosmetic. The prose implies the correct order.

**Fix:** Implement this as `_win`/`_cnt`-style sums over all played team-games, sorted exactly as in `features._per_game`. The numerator sums `(outcome - p_deserved)` where net_epa is present. The denominator counts games with net_epa among the last 16 played. When the denominator is 0, return 0.0.

---

_Reviewed: 2026-11-11T19:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

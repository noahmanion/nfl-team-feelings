# Pre-registration v2: errata and deviations

Companion to `PREREGISTRATION_V2.md` (adding commit 9c32319, its only commit). Section 1.3 of that
file routes errata and allowed deviations here, and only here. `PREREGISTRATION_V2.md` itself is never
edited.

This file is append-only. Part A is closed at the commit that adds this file: it is never edited or
extended. Part B only grows, one dated entry at a time, and only with the deviations that section 17.2
allows.

## Part A. Pre-data errata (2026-11-11, closed)

Status when Part A was committed:
- It is the same day as `PREREGISTRATION_V2.md`.
- No v2 feature, model, guard or test code exists.
- No v2 number has been computed on any season.
- `pipeline/inputs/` does not exist.

Part A came out of a read-only review of `PREREGISTRATION_V2.md` (`.planning/phases/09-v2-pre-registration/09-REVIEW.md`). Every entry resolves an ambiguity
by taking the more conservative reading, meaning the one that makes leakage or a favorable choice
harder. Each entry binds exactly as if it were part of `PREREGISTRATION_V2.md`. Where an entry and the
original text disagree, the entry governs. Any further change of meaning needs a new
pre-registration (v3, section 6.4), never a Part A edit.

### A1. One freeze commit, and nothing changes after it (review CR-01)

1. `pipeline/weights_v2.yaml` has exactly one commit, ever. The freeze commit is that commit: the
   adding commit and the latest commit are the same commit. Guards check that the commit count is 1,
   in the same way as for the prereg.
2. Section 16.1 is widened. The evaluation is void if, after the freeze commit, any commit touches:
   - `weights_v2.yaml`;
   - any v2 feature, model or evaluation module, or its tests;
   - the v2 input files listed in A3.

   Exceptions:
   - an allowed Part B deviation;
   - the `FREEZE_V2_WITNESS.json` commit of A4;
   - the primary-season preseason-line file of A3.5;
   - `HOLDOUT_V2_RESULT.*`, written by the single `fgs holdout-v2` run.
3. A re-freeze is impossible. The only route after a freeze is a new pre-registration.

### A2. The two ablations (review CR-02, CR-03)

1. MODEL-V2-01 ablation: the full v2 set compared with the same set minus `good_loss_luck` (11
   factors).
2. MODEL-V2-03 ablation: a swap. The full v2 set is compared with the same set in which `vs_exp_v2`
   is replaced by v1 `vs_exp`, sourced exactly as in v1. It is never compared with a set that has no
   expectation factor.
3. After the drop rules have run, the frozen model is refit by the section 8.2 procedure on the
   surviving factor set:
   - V2-01 dropped: `good_loss_luck` is removed (11 factors).
   - V2-03 dropped: v1 `vs_exp` is used in its place.
   - Both dropped: v1's 11 factors refit on 1999–2025.

   "Weight 0" in sections 1.4, 9.3 and 4 means "dropped and documented in `weights_v2.yaml`". It
   never means "zeroed in the 12-factor fit while the other weights stay as fitted".
4. Both ablations are leave-one-input-out against the full set and are run once. Their outcomes are
   applied together. A second round of ablations on the reduced set never happens.

### A3. Preseason-line inputs, sources and pinning (review CR-04, WR-01, WR-03)

1. All references to "2027" in sections 3, 7.2, 12.3 and 17.2.3 mean "the primary holdout season".
   That is 2027, or 2028 under section 3.5. That season's preseason lines must be committed before
   its first REG kickoff.
2. Source rule for every hand-entered line (2021–2025 and the primary season):
   - the preseason regular-season win total (`line` only, ignoring over/under juice, as in v1);
   - the last pre-Week-1 line from one named public source, recorded per row with a source URL and
     retrieval date;
   - the same columns as the nflverse `win_totals.csv` (`season, team, line, over_odds,
     under_odds`) plus `source, entered_on`;
   - team codes mapped through `RAW_TO_FRANCHISE`.
3. Files:
   - `pipeline/inputs/win_totals_2021plus.csv` (2021–2025; Phase 11 creates it as display-only data);
   - `pipeline/inputs/win_totals_<season>.csv`, one file per primary holdout season.
4. Pinning: the sha256 of `win_totals_2021plus.csv` is committed to the v2 milestone's planning
   docs before any v2 code runs, and is written into `weights_v2.yaml` at freeze. `fgs freeze-v2`
   refuses if the file's hash differs. A change to that file after the pin, and before the freeze,
   voids the evaluation, because it would let the 2021–2025 lines be tuned against ablation results.
5. The primary-season file's adding-commit committer time must be before the first REG kickoff of
   that season. It must also be pushed to `origin` before that kickoff, with the push witnessed as
   in A4. `fgs holdout-v2` checks both.
6. 2026: the preseason-line requirement cannot be met, because 2026 Week 1 has passed. Every 2026
   team-season therefore uses the model week-0 expectation for `vs_exp_v2`, and the result files
   label it that way. 2026 Vegas lines are never backfilled into a v2 input. 2026 rows only feed the
   never-gating secondary slice (sections 3.7 and 15.5) and the shadow scores (section 18).
7. Section 1.2's "sha256 of the evaluation data" covers:
   - the v1 `fingerprint` inputs (the nflverse cache, the sim cache, `uv.lock`);
   - every file under `pipeline/inputs/` that v2 reads;
   - `weights_v2.yaml`.

### A4. Freeze-time witness (review WR-04)

1. Right after the freeze commit, `fgs freeze-v2`, or the operator, pushes it to `origin`. Within
   24 hours it then records an independent witness in a committed
   `pipeline/FREEZE_V2_WITNESS.json`. That file is the one commit A1.2 allows to follow the freeze
   commit. The witness is one of:
   - the GitHub push event from `gh api` (events and activity endpoints), with its timestamp and
     head SHA;
   - a GitHub-verified signed tag.
2. The effective freeze time is the later of:
   - the committer time;
   - the witness time.
3. If no witness exists, or the witness time is after the first REG kickoff of the intended primary
   season, the deadline counts as missed (section 3.5).

### A5. Drop-rule mechanics (review WR-05, WR-06)

1. Only the three criteria of section 9.2 apply. Nothing else from `backtest.draft_gate` is
   imported: there is no `final_w > 0`, no rounding test and no week-0 Δ test.
2. Sign agreement is `np.sign(fold_w) == np.sign(final_w)` on unrounded weights. A final weight of
   exactly 0.0 agrees only with fold weights of exactly 0.0.
3. Fewer than 23 walk-forward folds is a hard error, and no verdict is produced. The threshold is
   never re-scaled.
4. A kept factor whose final weight rounds to 0.00 is kept at 0.00, as section 8.2.5 says.
5. Diagnostic, never gating: the drop-rule report also shows the V2-01 ΔSpearman with a per-fold
   (a, b) fit on season < S. This quantifies the look-ahead that section 5.8 accepts.

### A6. H3 statistic (review WR-02)

H3 is the paired ΔSpearman N=8 on identical eligible rows between two models, with the same
team-season CI as H1. It is reported and never gates. The two models are:

- the frozen v2 model;
- the A2.2 swap model: the same surviving factor set with `vs_exp_v2` replaced by v1 `vs_exp`,
  refit by section 8.2 on ≤2025 at freeze time. Its weights are stored in `weights_v2.yaml`.

When V2-03 is dropped, the frozen model already uses v1 `vs_exp`. The swap model then uses
`vs_exp_v2`, also refit at freeze time, and H3 is reported with its sign flipped so that it still
reads "vs_exp_v2 minus vs_exp".

### A7. Verdict edge cases (review WR-07)

The verdict follows v1 `fgs.holdout.verdict` semantics, with the single team-season CI:

- `yes` iff diff > 0, the CI exists, and its lower bound is > 0;
- `slight` iff diff > 0 otherwise, including a missing CI or a CI that lies entirely below 0;
- `no` iff diff ≤ 0, or diff is undefined.

### A8. What counts as a "metric" (review WR-08)

1. In sections 16.2 and 19.2, a metric is any computation that combines v2 values (inputs, scores
   or ranks) with game outcomes after the snapshot. That includes targets, results, margins, Brier,
   Spearman, accuracy, and win/loss tallies against predictions.
2. Shadow mode (section 18) may compute and store as-of v2 scores for 2026+. It must not combine
   them with later outcomes.
3. The v2 shadow module must not import `fgs.backtest` or `fgs.holdout`. This is enforced by an
   import-firewall test.

### A9. Errata channel (review WR-09)

Section 1.3 is the authority for errata living here. Section 17.2 lists the deviations that Part B
may record, and it is closed. Part A is the only set of errata, and it is closed now.

### A10. Precision notes (review IN-01..IN-03)

1. The frozen v1 comparator is the `composite_inseason` column. It is computed by `score.composite`
   with the in-season `weights:` block of `weights.yaml`, and the evaluator asserts that block
   equals the 41e1e54 values. It is never `composite` after `score.apply_offseason`.
2. The rule that "-0.00 is normalized to 0.00" (section 8.2.4) is new relative to v1. It has no
   numeric effect, and it applies as written.
3. good_loss_luck window: take the last 16 played team-games, ordered as v1 `features._per_game`
   (`franchise_id, key, gameday, gametime, game_id`). Then:
   - the numerator sums `(outcome - p_deserved)` over the games in that window that have `net_epa`;
   - the denominator counts those games;
   - the value is 0.0 when the denominator is 0.

## Part B. Deviations (section 17.2 only, append-only)

None.

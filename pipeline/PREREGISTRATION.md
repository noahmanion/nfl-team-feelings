# Pre-registration: one-time 2022–2025 holdout evaluation

Date: 2026-11-11

This file is a contract. It fixes, before any number is computed on seasons 2022–2025, how the
frozen model is built and how the one-time holdout is judged. Every rule below is meant to be
checkable against the code and the committed result files. No metric has been computed on
2022–2025 at the time this file is committed.

## 1. Status and order

1. This file is committed before `fgs freeze` runs and before `fgs holdout` exists.
2. The holdout runs exactly once, after this file and the frozen `weights.yaml` are both committed.
3. `HOLDOUT_RESULT.md` and `HOLDOUT_RESULT.json` record this file's sha256 and the git commit it was
   evaluated against.

## 2. The model (MODEL-15: the data decides every weight and sign)

1. The model uses all 11 factors, in this order: elo, season_record, last16, mov, sow, streak, luck,
   epa_traj, qb_trend, vs_exp, po_trend.
2. Each factor is z-scored per (season, week) snapshot.
3. The fit is ridge regression with an unpenalized intercept, on every training snapshot 1999–2021
   that has the N=8 target.
4. Alpha is chosen by `choose_alpha`: leave-one-season-out CV over 1999–2021, grid
   {0, 1e-3, 1e-2, 1e-1, 1}·n, minimum pooled squared error. This is the existing procedure used by
   `propose_weights`. Nothing new is invented.
5. Weights are rounded to 2 decimals. −0.00 is normalized to 0.00.
6. There is no positivity constraint, no clipping, and no pruning. Factors whose weight rounds to
   0.00 stay in the file.
7. Negative or ≈0 weights for streak, luck, last16, or any other factor are the data's verdict and
   are kept as fitted.

## 3. The frozen composite

"Frozen composite" means `features.composite` from `derive(scored=True)` with the frozen weights:
Σ round(w)·z over the 11 factors, with no intercept. It is exactly the score the site ships. It is the
continuous composite, not the integer percentile.

## 4. Target

Primary target is N=8; N=4 is secondary. The target is `backtest.TARGET_TEXT`:

> mean adjusted margin over the team's next N same-season games (REG + playoffs);
> adj = margin + (opp_elo_pre - 1505)/25 - hfa_signed/25; snapshots with < 2 games left skipped

## 5. Holdout data

1. Seasons 2022–2025: the snapshots with season in [2022, 2025] that have the target.
2. Targets are computed on data with season <= 2025. The 2026 season is never part of the holdout.
3. No refits on holdout data. The Brier logistic maps (score → next-game win probability) are fit
   once, on next-game rows with season <= 2021.

## 6. Primary metric and BACK-06 pass rule

1. Primary metric: pooled Spearman correlation (average ranks, `backtest.spearman`) between the
   frozen composite and the N=8 target, minus the same Spearman for plain Elo (the snapshot `elo`
   column). This is the paired point difference.
2. BACK-06 PASS if the paired point difference is > 0. FAIL otherwise.

## 7. Uncertainty

1. Paired percentile bootstrap: B = 2000, seed 20221, 95% level. In each draw every candidate is
   evaluated on the same resampled indices, so differences are paired.
2. Spearman CIs use two methods:
   - (a) season-block: draw 4 seasons with replacement and concatenate their rows. This gives only
     35 distinct resamples.
   - (b) team-season cluster stratified by season: within each season, draw that season's
     team-season clusters with replacement (same count per season).
3. Brier CIs use two methods:
   - (a) season-block, as above.
   - (b) season-week cluster stratified by season: within each season, draw that season's
     (season, week) clusters with replacement.
4. Also reported: the per-season Spearman differences and "composite won k of 4 seasons".
5. Known limitation, stated before the run: on 16 rolling 4-season training windows, the season-block
   CI covered the long-run difference in 69% of windows and the stratified cluster CI in 88%. Both
   understate uncertainty with only 4 seasons.

## 8. Verdict wording (fixed now)

The verdict keys on the WIDER of the two Spearman-difference CIs, where "wider" means the larger
hi − lo. The three sentences are fixed:

- `yes` (diff > 0 and the wider CI's lower bound > 0):
  "Yes: on 2022–25 the score ranked teams' next 8 games better than Elo alone."
- `slight` (diff > 0 and the wider CI includes 0):
  "Yes, slightly: better than Elo alone on 2022–25, but within the noise of four seasons."
- `no` (diff ≤ 0):
  "Not on 2022–25: Elo alone did as well or better. We kept the weights anyway (no re-tuning)."

## 9. Secondary metrics (reported, never gating)

1. Spearman with the N=4 target.
2. Spearman by bucket: wk0, early, mid, late.
3. Baselines: season win %, last 16, point differential per game.
4. Next-game Brier for the composite, Elo, the baselines, the Vegas spread (expected to win; it is the
   market ceiling) and the Elo-538 closed form.
5. Brier differences vs Elo and vs the spread, each with both CIs.

## 10. Pre-registered diagnostic

1. "Composite with vs_exp zeroed" = composite − contrib_vs_exp, evaluated the same way (Spearman N=8
   and its difference vs Elo, with the cluster CI).
2. Purpose: vs_exp switches from Vegas-sourced (2003–2020) to model-sourced at the holdout boundary,
   and Phase 5 measured the deployment condition at about −0.0011.
3. This is a diagnostic only. It never changes the frozen model or the verdict.

## 11. Known risks, stated before the run

1. The vs_exp source switch at the holdout boundary (section 10).
2. Only 4 seasons, so every interval is wide and both bootstrap methods understate uncertainty.
3. The training stand-in (weights fit 1999–2017, tested 2018–2021) gave a composite − Elo difference
   of +0.019. The season-block CI was [+0.004, +0.042] and the cluster CI was [−0.002, +0.040].
   These are training data and show scale only, not a forecast.

## 12. If it fails

The result is reported honestly on the methodology page and in the README. There is no re-tuning,
no pruning, no refit, and no second holdout run. Verification records it as a gap for the user.

## 13. Guards

1. `fgs freeze` refuses once `HOLDOUT_RESULT.md` exists.
2. `fgs backtest --propose-weights` refuses when the weights are frozen.
3. `fgs backtest --include-holdout` refuses until the holdout result exists.
4. `fgs holdout` refuses if any of these hold:
   - the result already exists (unless `--force`, documented as "don't");
   - the weights are not frozen;
   - this file or `weights.yaml` is uncommitted or modified;
   - this file's adding commit is not an ancestor of the latest `weights.yaml` commit.

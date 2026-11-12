# Pre-registration v2: candidate inputs and the 2027 holdout

Date: 2026-11-11

This file is a contract. It fixes, before any v2 model code exists and before any v2 metric has been
computed on any season, how the three v2 candidate inputs (MODEL-V2-01, MODEL-V2-02, MODEL-V2-03)
are defined, which of them may be built, how the v2 model is fit and frozen, and how the one-time
v2 holdout is judged. When this file is committed there is no v2 feature, model, guard or test code
in the repository, and no v2 number has been computed. Every rule below quotes the existing v1 code
by name so that it can be built without interpretation. The v1 pre-registration
(`PREREGISTRATION.md`) is not modified by this file and is never modified (section 20).

## 1. Status and order

1. Order of events:
   1. This file is committed alone, in one commit.
   2. The v2 code milestone builds the inputs, the model and the guards of section 19.
   3. The drop-rule ablations of section 9 run on seasons <= 2025 only.
   4. `fgs freeze-v2` writes the frozen v2 weights file `pipeline/weights_v2.yaml`. It holds the 12
      factor weights (2 dp), the chosen alpha, the frozen (a, b) of section 5 and the outcome of
      every drop rule of section 9. The commit that adds this file is "the freeze commit".
   5. `fgs holdout-v2` runs exactly once, after the Super Bowl that ends the primary holdout season
      (for 2027 that is Super Bowl LXII, scheduled for Feb 13, 2028).
2. `HOLDOUT_V2_RESULT.md` and `HOLDOUT_V2_RESULT.json` record this file's sha256, this file's adding
   commit, the freeze commit, the sha256 of `weights_v2.yaml` and the sha256 of the evaluation data.
3. This file has exactly one commit, ever. It is never edited, amended, reformatted, renamed,
   deleted or re-added. Errata and allowed deviations are recorded only in the append-only
   `pipeline/PREREGISTRATION_V2_DEVIATIONS.md` (section 17).

## 2. Development data ceiling

1. All v2 feature design, fitting, alpha selection, (a, b) fitting, drop-rule ablations and sanity
   checks use seasons <= 2025 only.
2. Seasons 2022–2025 were the v1 holdout. That holdout is consumed, so 2022–2025 is legal v2
   training data. Consequently any "v2 beats v1 on 2022–2025" statement is in-sample and is always
   labeled in-sample.
3. v2 gets its own constants (dev ceiling 2025, test seasons 2003–2025) in a v2-only module. The v1
   constants `TRAIN_LAST_SEASON` (2021), `HOLDOUT_SEASONS` (2022, 2025), `FIRST_TEST_SEASON` (2003)
   and `REF_SEASONS` (1999, 2021) in `fgs.season_config` stay unchanged, because they drive the v1
   guards.

## 3. Holdout

1. Eligibility is by kickoff time, not by season label. An N=8 snapshot is eligible only if EVERY
   game in its N=8 target window kicks off strictly after the committer timestamp of the freeze
   commit, `git log -1 --format=%cI <freeze>`, AND the freeze commit descends from this file's
   adding commit (`git merge-base --is-ancestor <this file's adding commit> <freeze>`).
2. Kickoff = nflverse `load_schedules()` `gameday` + `gametime`, read as local time in
   America/New_York and converted to UTC before the comparison.
3. A next-game Brier row is eligible only if its next game kicks off after the freeze commit's
   committer timestamp.
4. Primary holdout: the full 2027 season (REG + playoff targets), provided the freeze commit lands
   before the first 2027 REG kickoff as recorded in nflverse `load_schedules()`. The deadline is that
   recorded kickoff, not a hard-coded date (it is expected around Thu Sept 9, 2027 and has not been
   announced).
5. If the freeze commit misses that deadline, the primary holdout becomes the full 2028 season. This
   is a recorded deviation (section 17). A partial 2027 season is never the primary holdout.
6. The freeze commit is pushed to `origin` before the deadline, so the remote's push time is an
   independent witness to the self-reported committer time.
7. Eligible 2026 snapshots, if any exist, form a secondary slice that is reported and never gates
   the verdict. None are expected.

## 4. Feasibility of each input (leak-free, free data only)

Any input that cannot be built without leakage from free data is dropped (weight 0, not built).

| Input | Data | Leak-free buildable? | Status |
|---|---|---|---|
| MODEL-V2-01 good_loss_luck | `fgs.pbp` `net_epa` (nflverse pbp, already ingested 1999+) and `fgs.games` `outcome` | Yes. Every game's value is known when the game ends, and the as-of rule of v1 applies. | Candidate; judged by section 9 |
| MODEL-V2-02 free agency | nflreadpy `load_contracts()` | No. There is no signing date (section 6), so any as-of-week value leaks. | DROPPED (weight 0, not built) |
| MODEL-V2-03 vs_exp_v2 | nflverse `win_totals.csv` 2003–2020; Phase 11's `pipeline/inputs/win_totals_2021plus.csv` for 2021–2025; 2026 and 2027 preseason lines committed before that season's Week 1 kickoff; model expectation for 1999–2002 | Yes. Preseason lines are fixed before Week 1, so a line recorded before kickoff cannot leak. | Candidate; judged by section 9 |

## 5. MODEL-V2-01 good_loss_luck

1. Value for a team at snapshot (season, week): the mean, over the team's last 16 played games, of
   `(result - p_deserved)`.
2. Window: the last 16 played games, REG + playoffs, crossing season boundaries, with the as-of rule
   identical to v1: "Every value uses only games with asof_week <= week", the window keyed on
   `season*100 + asof_week` (the same window length as v1 `luck`, `LUCK_N` = 16).
3. `result` = the `fgs.games` `outcome` column: 1 for a win, 0.5 for a tie, 0 for a loss.
4. `p_deserved = logistic(a + b*d)` with `logistic(x) = 1 / (1 + exp(-x))`.
5. `d` = the game's `net_epa` from `fgs.pbp` (`team_game_epa`): `off_epa - def_epa`, each a per-play
   mean over the plays kept by `fgs.pbp.scrimmage`: `(pass == 1 | rush == 1)`, `qb_kneel == 0`,
   `qb_spike == 0`, `play_type != "no_play"`, `epa` not null, `posteam` present (not null, not
   empty), and `wp` in [`WP_LO`, `WP_HI`] = [0.05, 0.95] inclusive. `d` is raw and NOT
   opponent-adjusted. The opponent-adjusted `adj_epa` used by `epa_traj` is not used.
6. Games without `net_epa` (for example the `KNOWN_NO_PBP` games 1999_01_BAL_STL, 2000_03_SD_KC,
   2000_06_BUF_MIA) drop out of the mean; the window is not extended to replace them. The value is
   0.0 when the team has no played games, or when none of the games in the window has `net_epa`.
7. (a, b) are fit exactly once with `backtest.logit_fit` (Newton/IRLS, 25 iterations, intercept
   last, fractional y allowed) on one row per played team-game (both sides of every game), seasons
   <= 2025, `net_epa` non-null, y = `outcome` (ties 0.5), X = `net_epa` only, no home term. a and b
   are rounded to 4 dp and frozen in `weights_v2.yaml`. Because each game contributes two
   symmetric rows, a ≈ 0 is expected and acceptable.
8. The same frozen (a, b) is used inside every walk-forward fold of section 9 and in the final fit.
   This is accepted: (a, b) is a fixed transform fit once (not a per-fold model parameter).
9. good_loss_luck is ADDED as the 12th factor. v1 `luck` (one-score W-L over `LUCK_N` = 16 games,
   one-score = abs(margin) <= `ONE_SCORE` = 8, ties excluded) stays in the factor list unchanged.

## 6. MODEL-V2-02 free agency: DROPPED

1. Probe evidence (nflreadpy 0.1.5 `load_contracts()`, probed 2026-11-11):
   - 53,701 rows.
   - No signing-date column at all; the only timing field is the integer `year_signed`.
   - The top-level `team` is the player's current team, not the signing team.
   - `contract_history` gives team / contract_type / year_signed at year level only, so an October
     in-season UFA signing cannot be told apart from a March one, and any as-of-week feature leaks.
   - UFA coverage reaches all 32 teams only from 2012. In 1999–2010 it covers 1–25 teams per year,
     which is survivorship-biased.
2. Verdict: MODEL-V2-02 is DROPPED. Its weight is fixed at 0 and it is not built.
3. For the record only, the definition it would have had: net incoming UFA value as of week 0 of
   season S = the sum of APY as a share of season S's salary cap for UFAs signed by the team in the
   offseason before season S, minus the same sum for the team's own UFAs signed elsewhere in that
   offseason, held constant through season S. It is never built under this file.
4. Re-entry requires a new pre-registration (v3). It can never re-enter through an amendment or a
   deviation of this file.

## 7. MODEL-V2-03 vs_exp_v2

1. Formula identical to v1 `features._vs_exp`:
   `((wins + 0.5*ties) - exp_total / reg_games(season) * gp) / max(gp, 1)`, where gp = the team's
   as-of REG games played. The value is 0.0 at week 0.
2. `exp_total` = the normalized Vegas preseason win total, with the `vegas_expectations`
   normalization: `vegas_norm = line - mean(line over the season's teams that have a line) +
   reg_games(season)/2`, team codes mapped through `RAW_TO_FRANCHISE` (OAK -> LV, SD -> LAC,
   STL -> LA). It is used for every team-season with a recorded preseason line: 2003–2020 from the
   nflverse `win_totals.csv`, 2021–2025 from `pipeline/inputs/win_totals_2021plus.csv`, and 2026 and
   2027 from preseason lines committed before that season's Week 1 kickoff.
3. The model week-0 expectation (`exp_wins`) is used only for 1999–2002 and for a team-season whose
   preseason line is missing (an allowed deviation, section 17).
4. vs_exp_v2 REPLACES `vs_exp` in the v2 factor list.
5. It lives in a v2-only module. It never calls or modifies v1 `vegas_expectations` or
   `expectations()`, and v1 never reads `win_totals_2021plus.csv`.
6. The frozen v1 comparator keeps v1's model-sourced `vs_exp` for 2021+ exactly as frozen. If the
   2021+ inputs file ever feeds v1 `expectations()`, the comparator is no longer frozen v1, and the
   evaluation is void (section 16).

## 8. The v2 model

1. Factors, in this order: elo, season_record, last16, mov, sow, streak, luck, epa_traj, qb_trend,
   vs_exp_v2, po_trend, good_loss_luck.
2. The fit procedure is v1's, verbatim:
   1. Each factor is z-scored per (season, week) snapshot.
   2. Ridge regression with an unpenalized intercept, on every snapshot 1999–2025 that has the N=8
      target.
   3. Alpha is chosen by `choose_alpha`: leave-one-season-out over 1999–2025, grid `ALPHA_GRID` =
      (0.0, 1e-3, 1e-2, 1e-1, 1.0), multiplied by n_train inside `ridge_fit`, minimum pooled squared
      error, ties keep the smaller alpha.
   4. Weights are rounded to 2 dp; -0.00 is normalized to 0.00.
   5. No sign constraints, no clipping, no pruning. A weight that rounds to 0.00 stays in the file.
3. The v2 composite = Σ round(w)·z over the 12 factors, with no intercept. It is the continuous
   composite, not the percentile.
4. Model-selection budget: this one specification, plus the leave-one-input-out ablations of
   section 9. No other variant reaches the holdout.

## 9. Drop rules (decided now, dev data only)

1. Each candidate (MODEL-V2-01, MODEL-V2-03) is judged leave-one-input-out against the full v2 set
   of section 8, not sequentially.
2. A candidate is kept if and only if all three hold:
   1. It is feasible leak-free per section 4.
   2. Walk-forward per `backtest._ridge_walk_forward`, test seasons 2003–2025 (23 folds; each fold
      runs `choose_alpha` + ridge on the rows with season < S and the N=8 target present, then
      predicts season S), gives pooled ΔSpearman N=8 (full set with the input minus the set without
      it, each refit per fold) > 0.
   3. Following the `draft_gate` precedent (`DRAFT_GATE_FOLDS` = 0.60), the input's fold weight has
      the same sign as its weight in the final 1999–2025 fit in at least 14 of 23 folds.
3. A candidate that fails is set to weight 0, and the failure is documented in `weights_v2.yaml`.
4. If MODEL-V2-03 is dropped, the factor reverts to v1 `vs_exp` (model + Vegas sourced exactly as in
   v1), not to "no vs_exp".
5. If MODEL-V2-01 is dropped, good_loss_luck is removed from the factor list.
6. If both are dropped, v2 = the v1 procedure (v1's 11 factors) refit on 1999–2025, still frozen and
   evaluated as-is.
7. MODEL-V2-02 is already dropped by rule 2.1.

## 10. Target

Primary target is N=8; N=4 is secondary. Unchanged from v1. The target is `backtest.TARGET_TEXT`:

> mean adjusted margin over the team's next N same-season games (REG + playoffs); adj = margin + (opp_elo_pre - 1505)/25 - hfa_signed/25; snapshots with < 2 games left skipped

## 11. Comparators (in order)

1. Frozen v1 composite (primary): `features.composite` from `derive(scored=True)` with the frozen
   in-season `weights:` of `weights.yaml` as frozen at commit 41e1e54 (blob sha256
   44b4c7b9115ca620dbe5ffb588792aecf51c05ca2b86cc440845a6b40cf76320), computed by the v1 code path
   with v1 semantics. Later commits to `weights.yaml` only appended the `offseason:` section, which
   `load_weights` ignores; the comparator is the in-season composite.
2. Plain Elo (secondary): the snapshot `elo` column.
3. Vegas closing spread: the next-game Brier reference ceiling only.

## 12. Hypotheses and primary metric

1. H1 (primary): v2 ranks teams' next 8 games better than the frozen v1 composite. Metric: pooled
   Spearman (`backtest.spearman`, average ranks) between the v2 composite and the N=8 target, minus
   the same Spearman for the frozen v1 composite, paired on identical eligible rows.
2. H2 (secondary): v2 minus plain Elo, same metric, same rows.
3. H3 (secondary): vs_exp_v2 versus v1 `vs_exp`, in the dev walk-forward (in-sample for 2022–2025)
   and on the holdout. H3 is reported as "not tested" if more than 4 teams lack a 2027 preseason
   line.

## 13. Uncertainty

1. Paired percentile bootstrap with `paired_bootstrap`, `stratified_clusters`, `draw_stratified`
   and `percentile_ci`: B = 2000, seed 20271 (v1 used 20221), 95% level. Every candidate is
   evaluated on the same resampled indices in each draw.
2. Spearman CIs use team-season clusters (franchise within season). Brier CIs use season-week
   clusters. A season-block CI is impossible with one season and is not reported.
3. Power, stated before the run: v1's 4-season team-season CI half-width was ≈0.026 (score minus
   Elo +0.0039, CI [-0.0211, +0.0306], 2287 N=8 snapshots). One season has about 1/4 of the
   clusters, so the CI is about 2 times wider, roughly ±0.05. A `yes` verdict would need v2 minus
   v1 of roughly more than +0.05. The expected verdict is slight or no.
4. Caveat: v2 and v1 share most factors, so their paired difference is likely less noisy than v1
   versus Elo was. ±0.05 is the conservative planning figure.

## 14. Verdict wording (fixed now)

The verdict keys on the team-season CI of the H1 difference (the only CI available with one
season). {season} is the primary holdout season number (2027, or 2028 under section 3.5). The
three sentences are fixed:

- `yes` (diff > 0 and CI lower bound > 0): "Yes: on {season} the v2 score ranked teams' next 8 games better than the frozen v1 score."
- `slight` (diff > 0 and CI includes 0): "Yes, slightly: v2 beat the frozen v1 score on {season}, but within the noise of one season."
- `no` (diff ≤ 0): "Not on {season}: the frozen v1 score did as well or better. We kept v2 as frozen (no re-tuning)."

Ship rule: only a yes verdict replaces v1 on the public site. A slight or no verdict keeps v1
public, and v2 is reported on the methodology page.

## 15. Secondary metrics (reported, never gating)

1. Spearman with the N=4 target.
2. Spearman by bucket: wk0, early, mid, late.
3. H2 and H3 (section 12).
4. Next-game Brier for v2, frozen v1, Elo and the Vegas spread. The logistic maps (score -> next-game
   win probability) are fit once with `logit_fit` on next-game rows with season <= 2025, mirroring
   v1 section 5.3. Reference v1 holdout Brier: score 0.2242, Elo 0.2228, spread 0.2097.
5. The eligible-2026 slice (section 3.7), if any.
6. The 2022–2025 v2 versus v1 comparison, labeled in-sample.

## 16. Void conditions

The v2 evaluation is void if any of these hold:

1. Any change to the v2 definitions, the fit procedure, the target or the frozen (a, b) after the
   freeze commit.
2. Any v2 code computes a metric on a season >= 2026 before `fgs holdout-v2` runs.
3. The freeze commit is not a descendant of this file's adding commit.
4. This file has more than one commit.
5. The evaluation data is not pinned by sha256 in the result files.
6. The frozen v1 comparator is computed with anything other than v1 semantics (for example, v1
   `expectations()` reading `win_totals_2021plus.csv`).

## 17. Deviations

1. Deviations are recorded only in the append-only `pipeline/PREREGISTRATION_V2_DEVIATIONS.md`,
   never in this file.
2. Allowed deviations:
   1. nflverse schema changes (renamed or moved columns with the same meaning).
   2. Schedule-format changes, for example an 18-game season: the target stays the next 8
      same-season games, and `fgs.season_config` only gains the new season length.
   3. A missing 2027 preseason line: that team-season falls back to the model expectation, and H3
      is reported as "not tested" if more than 4 teams are missing.
   4. The section 3.5 move of the primary holdout to 2028.

## 18. What ships during the holdout

The public site keeps the frozen v1 score. v2 runs shadow-only and is not displayed until the
verdict (and then only under the section 14 ship rule).

## 19. Guards (built in the v2 model milestone, not now)

1. `fgs freeze-v2` refuses unless this file is committed, unchanged and at exactly one commit.
2. Every v2 command refuses to compute a metric on a season >= 2026, except `fgs holdout-v2`.
3. `fgs holdout-v2` refuses before the primary-season Super Bowl result exists, refuses a second
   run, and records the sha256s and commits like v1 (section 1.2).
4. These are the same checks as `fgs.holdout.git_state`, with `prereg_rel="PREREGISTRATION_V2.md"`
   and `weights_rel="weights_v2.yaml"`: the adding commit (`--diff-filter=A`), a commit count of
   exactly 1, the committed blob's sha256 equal to the working file, and `merge-base --is-ancestor`
   ordering against the freeze commit.
5. The v1 guards are untouched.

## 20. v1 is untouched

`PREREGISTRATION.md` (sha256 f59ff7d6601f2e21986aaa8b6b399df30b34e95631c2098998fabacba5b36205,
adding commit 42e57aa148c3e679e1bed169a0d4b829df7ea6a5) stays at one commit. The frozen in-season
weights in `weights.yaml` (commit 41e1e54) and the v1 score are frozen forever. The v1 holdout
result (score minus Elo Spearman N=8 +0.0039, verdict slight; fitted vs_exp weight -1.22 with 18/19
folds negative) stands as recorded.

## 21. If it fails

The result is reported honestly on the methodology page and in the README. There is no re-tuning,
no refit and no second `fgs holdout-v2` run.

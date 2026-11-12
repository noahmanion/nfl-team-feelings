# Phase 9: v2 Pre-registration - Research

**Researched:** 2026-11-11
**Domain:** Pre-registration contract (docs only); exact citation of v1 procedures; git-provable integrity
**Confidence:** HIGH (every code fact below was read from the repo in this session; the calendar facts are MEDIUM/ASSUMED)

## Summary

This phase writes one Markdown file, `pipeline/PREREGISTRATION_V2.md`, and commits it in a single commit. It adds no code, no tests and no packages. Two things decide whether it succeeds. First, the definitions have to be buildable verbatim from the existing v1 code: same function names, same constants, same target text. A future milestone should be able to implement v2 without interpreting anything. Second, the file has to be right the first time. Like v1, the contract is void if the file ever has more than one commit (D-15). Any fix after commit, including a code-review typo fix, breaks it. Verification must therefore be read-only, and the plan should treat "commit once, never touch" as a hard rule.

Adding `PREREGISTRATION_V2.md` cannot disturb the v1 guard. `fgs.holdout.git_state` runs `git log -- PREREGISTRATION.md` with an exact, non-glob pathspec. A probe today returned `prereg_commits=1, prereg_unchanged=True, ordered=True`. The baseline suite is `584 passed` in about 2m15s.

**Primary recommendation:** Write PREREGISTRATION_V2.md in v1's numbered-section style. Quote the v1 names and constants listed in "v1 Procedures to Cite" exactly. Settle the four under-specified details listed under Open Questions (with the recommended answers) inside the file itself. Commit it alone in one commit. Verify only with the read-only shell checks in Validation Architecture.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
**Area 1: Holdout & data ceiling**
- D-01 Holdout eligibility is by kickoff time, not by season label. A snapshot is eligible only if EVERY game in its N=8 target window kicks off after the committer timestamp of the v2 freeze commit (the commit that writes the frozen v2 weights file), and that commit descends from the PREREGISTRATION_V2.md adding commit. Rationale: research Pitfall 5. Weeks 1–10 of 2026 have already been watched, and the v2 ideas may have been inspired by them.
- D-02 Primary holdout = the full 2027 season (REG + playoffs targets), provided the freeze commit lands before the first 2027 regular-season kickoff. If the freeze misses that deadline, the primary holdout moves to the full 2028 season. That is a recorded deviation, not a partial 2027. Rationale: a clean full season beats a truncated one, and it removes any incentive to rush.
- D-03 Eligible 2026 snapshots (if any) are reported only as a secondary, never-gating slice. Given no model code this milestone, expect none.
- D-04 Development ceiling: all v2 feature design, fitting, alpha selection and sanity checks use seasons ≤ 2025 only. 2022–2025, the consumed v1 holdout, becomes legal training data, and the file says so: any "v2 beats v1 on 2022–25" claim is in-sample.
- D-05 The evaluation runs once, after the 2027 Super Bowl (~Feb 2028), through a guarded `fgs holdout-v2` command (specified here, built later).

**Area 2: Candidate input definitions**
- D-06 MODEL-V2-01 good-loss luck = mean over the team's last 16 played games (REG + playoffs, crossing seasons, as-of rule identical to v1) of (result − p_deserved), where result is 1/0.5/0 and p_deserved = logistic(a + b·d). d is the game's net EPA/play differential (team offense EPA/play minus opponent offense EPA/play, using v1 `fgs.efficiency` play filters: pass|rush, garbage time dropped, not opponent-adjusted). (a, b) are fit once by logistic regression on all games with season ≤ 2025 and then frozen. It is 0.0 with no games or no pbp. It is ADDED as a 12th factor; v1 `luck` stays. Rationale: "deserved to win" from efficiency is the standard good-loss construct and uses data v1 already ingests. Keeping v1 luck lets the data decide.
- D-07 MODEL-V2-03 = re-sourced vs_exp (`vs_exp_v2`): the same formula as v1 vs_exp, but exp_total = normalized Vegas preseason win total for every season with a recorded preseason line (2003–2020 nflverse, 2021–2025 from Phase 11's `pipeline/inputs/` file, 2026/2027 preseason lines committed before that season's Week 1 kickoff). Model week-0 expectation is used only for 1999–2002. It REPLACES vs_exp in the v2 factor list. It lives in a v2-only module and never touches v1 `vegas_expectations` (DATA-02 guard). Rationale: it fixes the v1 train/deploy source switch (Vegas rows train, model rows deploy).
- D-08 MODEL-V2-02 free agency is DROPPED (weight 0, not built), pre-committed now. Probe evidence (nflreadpy 0.1.5 `load_contracts()`, 2026-11-11): 53,701 rows; no signing-date column at all (only integer `year_signed`); top-level `team` is the current team; `contract_history` gives team / contract_type / year_signed at year level only, so an October in-season UFA signing cannot be told apart from a March one, and any as-of-week feature leaks. UFA coverage reaches all 32 teams only from 2012 (1999–2010: 1–25 teams per year, so it is survivorship-biased). The file records the would-have-been definition for the record, and that re-entry requires a new pre-registration (v3), never an amendment.
- D-09 Model spec for v2 = the v1 procedure verbatim (per-snapshot z-scores, ridge with unpenalized intercept, `choose_alpha` LOSO grid, 2-dp rounding, no sign constraints), refit on 1999–2025, with factors = v1's 11 with vs_exp → vs_exp_v2, plus good_loss_luck. Model-selection budget: this one spec, plus the drop-rule ablations. No other variants reach the holdout.

**Area 3: Comparators, metrics & drop rules**
- D-10 Primary hypothesis: the v2 composite ranks teams' next 8 games better than the frozen v1 composite. Primary metric: pooled Spearman(v2, N=8 target) − Spearman(frozen v1 composite, N=8), paired on identical rows. The target is v1 `backtest.TARGET_TEXT` unchanged.
- D-11 Comparators in order: frozen v1 composite (primary), plain Elo (secondary), and the Vegas closing spread (next-game Brier reference ceiling only).
- D-12 Uncertainty: paired percentile bootstrap, B = 2000, seed 20271, 95%. Spearman uses team-season clusters, Brier uses season-week clusters (season-block is impossible with one season). Power stated up front: v1's 4-season team-season CI half-width was ~0.026, so one season is ~×2, about ±0.05. Expect "slight" or "no".
- D-13 Drop rules on dev data only, decided before any v2 code. An input is kept iff (1) it is feasible leak-free (V2-02 already fails), (2) a walk-forward check (test seasons 2003–2025, each refit on earlier seasons) gives pooled ΔSpearman N=8 (with input − without) > 0, and (3) its fitted sign agrees in ≥ 60% of folds. Otherwise the weight is fixed at 0 and documented. If every input is dropped, v2 = the v1 procedure refit on 1999–2025, still frozen and evaluated as-is.
- D-14 Verdict wording fixed in advance (yes / slight / no, keyed on the team-season CI, the only CI available with one season): yes = diff > 0 and CI lower bound > 0; slight = diff > 0 and CI includes 0; no = diff ≤ 0. Ship rule: only "yes" replaces v1 on the public site. "slight" and "no" keep v1 public, and v2 is reported on the methodology page.

**Area 4: Integrity, void conditions & guards**
- D-15 Void conditions: any change to v2 definitions, fit procedure, target or frozen (a, b) after the freeze commit; any v2 code computing a metric on season ≥ 2026 before `fgs holdout-v2`; a freeze commit that isn't a descendant of the prereg commit; PREREGISTRATION_V2.md with more than one commit; the evaluation data not pinned by sha256.
- D-16 Deviations go in a separate append-only `pipeline/PREREGISTRATION_V2_DEVIATIONS.md`, never in the prereg itself (it must stay at one commit, mirroring v1). Allowed deviations: nflverse schema changes, schedule-format changes (e.g. an 18-game season; the target stays the next 8 same-season games and season_config only gains the new length), and a missing 2027 preseason line (that team-season falls back to the model expectation; H3 reported as "not tested" if more than 4 teams are missing).
- D-17 What ships during the holdout: the site keeps the frozen v1 score; v2 runs shadow-only and is not displayed.
- D-18 Guards spec (built in the v2 model milestone): `fgs freeze-v2` refuses unless the prereg is committed, unchanged and at one commit; v2 commands refuse season ≥ 2026 metrics; `fgs holdout-v2` refuses before 2027 Super Bowl results exist, refuses on a second run, and records the sha256s and commits like v1.
- D-19 Verification for this phase: the v1 guard condition (PREREGISTRATION.md at exactly 1 commit with sha256 `f59ff7d6…5205`) checked by command; existing pipeline tests pass; `git log` shows no v2 model code before the prereg commit.

**Out of bounds:** any edit to `pipeline/PREREGISTRATION.md`, `pipeline/src/**`, `weights.yaml`, `web/**`, and any v2 feature or model code, including new constants in `paths.py`.

### Claude's Discretion
- Section layout and prose of PREREGISTRATION_V2.md (mirror v1's numbered-section contract style).
- Exact rounding and reporting tables for the eventual result file.

### Deferred Ideas (OUT OF SCOPE)
- Implementing v2 features, the model, freeze-v2 and holdout-v2 guards (future milestone, ~2027).
- Free agency as a v3 candidate if a free dated transaction source appears.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INTEG-02 | New `PREREGISTRATION_V2.md` (v1 untouched) commits, before any v2 code, to: exact candidate definitions (V2-01/02/03), dev ceiling ≤2025, holdout (post-freeze kickoffs, 2027 primary), comparators (frozen v1 + Elo), metrics, per-input drop rules, verdict wording | "v1 Procedures to Cite" gives the exact names and constants each definition must quote. Open Questions closes the four gaps that would otherwise force a future implementer to interpret. Validation checks 1–5 prove the "v1 untouched" and "before any v2 code" parts mechanically. |
| INTEG-03 | States whether each input is buildable leak-free from free data (e.g. FA signing dates) and pre-commits to dropping any that can't | D-08 probe evidence (already established, quoted verbatim). Feasibility per input: V2-01 is feasible (pbp `net_epa` already ingested). V2-03 is feasible for 2003–2025 once Phase 11's file exists, with the preseason-timing rule. V2-02 is infeasible and DROPPED. Validation check 6 greps for the feasibility statements. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Work only inside `feel-good-scorew/`. Keep it light, with no heavy process. Each project is self-contained.
- Process is light: no CI or test suites beyond backtest validation. This phase adds no tests.
- Use GSD workflow entry points for edits. Execution happens via `/gsd-execute-phase`.
- Memory: v1 holdout consumed, weights frozen forever. Full autonomy: decide, don't ask.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Contract text (definitions, rules, verdicts) | Repo docs (`pipeline/PREREGISTRATION_V2.md`) | — | A frozen document. Its integrity comes from git history. |
| Integrity proof (one commit, ancestry, sha256) | Git | Future `fgs` guards (D-18) | This phase proves integrity with shell git commands. The code guards come later. |
| v1 baseline protection | `fgs.holdout.git_state` (existing) | — | Untouched. Verified by a probe. |

## v1 Procedures to Cite (exact names, verified in code)

| Concept | Exact source | Exact value / text to quote |
|---|---|---|
| Target | `fgs.backtest.TARGET_TEXT` (backtest.py:111) | "mean adjusted margin over the team's next N same-season games (REG + playoffs); adj = margin + (opp_elo_pre - 1505)/25 - hfa_signed/25; snapshots with < 2 games left skipped" |
| Spearman | `fgs.backtest.spearman` | Pearson on average ranks (`rank("average")`) |
| Alpha grid | `fgs.backtest.ALPHA_GRID` + `choose_alpha` (backtest.py:243, 279) | `(0.0, 1e-3, 1e-2, 1e-1, 1.0)`, multiplied by n_train inside `ridge_fit`. Leave-one-season-out within the training rows, minimizing pooled squared error. Ties keep the earlier (smaller) alpha (`sse < best_sse - 1e-12`). |
| Walk-forward | `fgs.backtest._ridge_walk_forward` | Per test season S: `choose_alpha` and ridge on rows with season < S and y8 present, then predict S. In v1 the folds ran 2003–2021 (19 folds; HOLDOUT_RESULT shows "x/19"). For v2, 2003–2025 gives **23 folds**, so ≥60% means **≥14 of 23** (13.8 rounded up). |
| Fold-sign precedent | `fgs.backtest.draft_gate` | Sign consistency is measured **against the FINAL fit's sign**, with ≥ 60% of folds (`DRAFT_GATE_FOLDS`). D-13(3) should cite this rule. |
| Logistic fit | `fgs.backtest.logit_fit` / `logit_predict` | Newton/IRLS, 25 iterations, intercept last. It accepts fractional y (ties = 0.5) because the IRLS score is `X'(y − p)`. |
| Bootstrap | `fgs.bootstrap.paired_bootstrap`, `stratified_clusters`, `draw_stratified`, `percentile_ci` | v1 used B_DEFAULT=2000, SEED=20221, LEVEL=0.95. v2 uses seed **20271**. Cluster keys: team-season = franchise_id within season; season-week = as-of week within season. |
| Play filters (for `d`) | `fgs.pbp.scrimmage` (the filters live in **pbp.py**, not efficiency.py) | `(pass==1 \| rush==1)`, qb_kneel==0, qb_spike==0, play_type != "no_play", epa not null, posteam not null/empty, **`wp` in [0.05, 0.95] inclusive** (`WP_LO, WP_HI`). |
| `d` itself | `fgs.pbp` team_game_epa column **`net_epa`** = `off_epa − def_epa` (each a per-play mean over the filtered plays) | It is raw, not opponent-adjusted. That matches D-06. Note that `epa_traj`'s `adj_epa` is the opponent-adjusted one, and good-loss must NOT use it. |
| Result | `fgs.games` `outcome` column | 1 / 0.5 / 0 |
| As-of rule | `features.py` docstring | "Every value uses only games with asof_week <= week". Windows key on `season*100 + asof_week`, crossing seasons. The v1 `luck` window is `LUCK_N=16`, one-score = abs(margin) ≤ 8 (`ONE_SCORE`), ties excluded. |
| vs_exp formula | `features._vs_exp` / docstring | `((wins + 0.5*ties) - exp_total / reg_games(season) * gp) / max(gp, 1)`, where gp = as-of REG games. It is 0.0 at week 0 and without sim. |
| Vegas normalization | `fgs.expectation.vegas_expectations` | `vegas_norm = line - mean(line over season) + reg_games(season)/2`. Legacy codes OAK/SD/STL map via `RAW_TO_FRANCHISE`. In `expectations()`: `exp_total = coalesce(vegas_norm, exp_wins)`. |
| Era rules | `fgs.season_config` | `reg_games` = 16 (≤2020) else 17. `reg_weeks` = 17/18. `n_teams` = 31 (≤2001) else 32. `playoff_teams` = 12 (≤2019) else 14. HFA by era: 65/58/30/45. `EXPECTED_GAME_EXCEPTIONS` covers BUF/CIN 2022 = 16. v1 constants: `FIRST_TEST_SEASON=2003`, `TRAIN_LAST_SEASON=2021`, `HOLDOUT_SEASONS=(2022, 2025)`, `REF_SEASONS=(1999, 2021)`. The v2 prereg must say that v2 uses its own ceiling (2025), not by editing these constants (see Pitfall 4). |
| Frozen composite | v1 PREREGISTRATION §3 | `features.composite` from `derive(scored=True)` with frozen `weights.yaml`: Σ round(w)·z, no intercept, continuous (not the percentile). |
| v1 provenance guard | `fgs.holdout.git_state` | Checks the adding commit (`--diff-filter=A`), counts the commits touching the file (must be 1), compares the sha256 of the committed blob to the working file, and checks with `merge-base --is-ancestor` that both the prereg's adding and last commits are ancestors of the latest weights commit. **The v2 guards (D-18) should be specced as "the same checks as `git_state`, with `prereg_rel=PREREGISTRATION_V2.md` and the v2 weights file".** |
| Missing pbp | `fgs.pbp.KNOWN_NO_PBP` | `1999_01_BAL_STL`, `2000_03_SD_KC`, `2000_06_BUF_MIA`. 1999–2000 rows are marked `low_confidence`. |

## Numbers to Quote

**v1 holdout (HOLDOUT_RESULT.md, 2022–2025, 2287 N=8 snapshots, about 572 per season):**
- Score − Elo Spearman N=8: **+0.0039**. Team-season CI [−0.0211, +0.0306], half-width **≈0.026**. Season-block CI [−0.0225, +0.0294]. Won 2 of 4 seasons (2022 +0.0292, 2023 +0.0335, 2024 −0.0132, 2025 −0.0266). Verdict: slight.
- The per-season differences range from −0.027 to +0.034 (SD ≈ 0.03). That confirms that a single season's ΔSpearman carries noise of about ±0.05 at 95%.
- Power statement: one season gives about 1/4 the clusters, so the CI is about √4 = ×2 wider, roughly **±0.05**. To earn "yes", v2 − v1 would need to be about **> +0.05**, which is more than 10× v1's whole edge over Elo. Caveat worth stating: v2 and v1 share 10 of 11 factors, so their paired difference should be *less* noisy than v1-vs-Elo was. ±0.05 is therefore a conservative (wide) planning figure. [VERIFIED: HOLDOUT_RESULT.md; scaling is reasoning]
- Pre-registered vs_exp diagnostic (motivates H3): the score with vs_exp zeroed scored 0.4846 vs 0.4853. The fitted vs_exp weight was **−1.22** (18/19 folds negative).
- Brier: score 0.2242, Elo 0.2228, spread 0.2097 (the ceiling).

**v1 provenance to cite:** PREREGISTRATION.md sha256 `f59ff7d6601f2e21986aaa8b6b399df30b34e95631c2098998fabacba5b36205`, adding commit `42e57aa148c3e679e1bed169a0d4b829df7ea6a5`. weights.yaml sha256 `44b4c7b9…6320`, commit `41e1e54`.

**2027 calendar:**
- Super Bowl LXII: **Sunday, Feb 13, 2028**, Mercedes-Benz Stadium, Atlanta. That date implies 17 games in 2027. [CITED: nbcsports.com PFT "super bowl lxii will be played on february 13 2028"] MEDIUM
- First 2027 REG kickoff: **approximately Thursday, Sept 9, 2027** (by convention the Thursday after Labor Day, and Labor Day 2027 is Mon Sept 6). It has not been announced. [ASSUMED] The prereg should state the deadline as "the first 2027 REG kickoff as recorded in nflverse `load_schedules()` (`gameday` + `gametime`)", not as a hard-coded date.
- nflverse `gameday`/`gametime` are US Eastern local time. [ASSUMED] The prereg should state that the comparison converts kickoff to UTC (America/New_York) and compares it to the freeze commit's committer timestamp (`git log -1 --format=%cI`, which includes the timezone offset).

## Common Pitfalls

### Pitfall 1: A second commit voids the contract
**What goes wrong:** a code-review or verifier "fix" (typo, wording) edits PREREGISTRATION_V2.md after the first commit. That gives it 2 commits, which voids it under D-15 and means the future `freeze-v2` guard refuses.
**How to avoid:** Write the whole file in one task and commit it alone. The plan must tell reviewers and verifiers they may not edit the file. Any errata go to a later `PREREGISTRATION_V2_DEVIATIONS.md`, and that file is NOT created in this phase. If the file is wrong before commit, fix it before commit. After commit there is no undo, except deleting it and re-adding before any freeze, which also breaks the one-commit rule. Treat that as forbidden.
**Warning signs:** `git log --format=%H -- pipeline/PREREGISTRATION_V2.md | wc -l` > 1.

### Pitfall 2: Bundling other files into the prereg commit
v1's prereg commit `42e57aa` touched exactly one file. Keep the GSD SUMMARY/STATE metadata in a separate, later commit so the prereg commit is clean and easy to audit (Validation check 3).

### Pitfall 3: Definitions that need interpretation later
The places where D-06 and D-13 leave choices open (Open Questions 1–4). If the file doesn't pin them, the future implementer makes a choice after seeing data. That is a forking path. The file must answer each one.

### Pitfall 4: Spec'ing v2 by editing v1 constants
`TRAIN_LAST_SEASON=2021` and `HOLDOUT_SEASONS` drive v1 guards (`backtest --include-holdout`, `freeze`). The prereg should say that v2 gets its own constants (e.g. a v2 dev ceiling of 2025) in a v2-only module, and that v1 constants stay unchanged. Otherwise v1's guards silently change.

### Pitfall 5: v1 reading the new win-totals file
D-07/DATA-02: the frozen v1 composite on 2027 must keep `vs_exp` model-sourced for 2021+ (as frozen). If Phase 11's `inputs/` file ever feeds `fgs.expectation.expectations`, the comparator stops being "frozen v1". The prereg should state this as a void-adjacent rule. The comparator is recomputed with the v1 code path at the v1 freeze commit's semantics.

### Pitfall 6: Normalizing with missing lines
`vegas_norm` subtracts the season mean over the rows present. If 2027 is missing some lines (D-16 allows ≤4), the mean is taken over the available teams. Say so, or say "mean over teams with a line". Recommend the latter, because it matches the existing code behavior.

### Pitfall 7: Committer time is self-reported
A local clock can be wrong, and committer dates can be set by hand. The remote `origin` (GitHub) exists. Recommend that the prereg require pushing the freeze commit before the deadline, because GitHub's push/event timestamp is an independent witness. LOW-cost and optional. This phase does not push. [ASSUMED: practice, not a locked decision]

## Open Questions (recommend resolving inside the prereg)

1. **Good-loss window with missing pbp.** Recommend: take the last 16 played games (same window as v1 `luck`) and average (result − p_deserved) over those that have `net_epa`. A game without pbp drops out of the mean, mirroring `epa_traj`, where "a game without pbp is absent". The value is 0.0 if none of the games has pbp.
2. **(a, b) fit sample.** Recommend: `backtest.logit_fit` on one row per played team-game (both sides) with season ≤ 2025 and non-null `net_epa`, y = `outcome` (ties 0.5), X = `net_epa`, no home term. Round (a, b) to 4 dp and freeze them in the v2 weights file. Symmetric rows imply a ≈ 0. That is expected and fine. Note that the in-sample fit is acceptable because (a, b) is a fixed transform: the v2 walk-forward folds use the same frozen (a, b). State that explicitly. The alternative, per-fold (a, b) refits, is more leak-proof, but the decision D-06 says "fit once".
3. **"Fitted sign agrees in ≥60% of folds", agrees with what?** Recommend the `draft_gate` precedent: compare against the sign of the final 1999–2025 fit, with k ≥ 14 of 23 folds. Rule (2)'s ΔSpearman is computed on pooled walk-forward predictions for 2003–2025 test seasons, with input vs without, each refit per fold with its own `choose_alpha`.
4. **Ablation order with two inputs.** Recommend: evaluate each input against the full v2 set minus that input (leave-one-input-out), not sequentially. If V2-03 is dropped, the factor reverts to v1 `vs_exp` (model+Vegas as in v1), not to "no vs_exp". Say so explicitly. Then define H3 as `vs_exp_v2` vs `vs_exp` in the walk-forward, plus on the holdout as a secondary result.

Smaller items to state: the eligible-row rule applies to Brier too (next game kicks off after freeze). The Brier logistic maps are fit on next-game rows with season ≤ 2025 (mirroring v1 §5.3). The comparator Elo is the snapshot `elo` column.

## Don't Hand-Roll

| Problem | Don't build | Use instead |
|---|---|---|
| Integrity proof | New scripts or test files | Read-only `git`/`shasum` commands (below), plus the existing `fgs.holdout.git_state` |
| New procedures in prose | Paraphrased re-definitions | Quote the v1 function names and constants verbatim |

## Package Legitimacy Audit

No packages are installed in this phase (docs only). Nothing to audit.

## Environment Availability

| Dependency | Required by | Available | Version |
|---|---|---|---|
| git | provenance checks | ✓ | repo with `origin` remote |
| uv + pipeline env | `uv run pytest -q` | ✓ | 584 passed, about 133 s |
| shasum | sha256 check | ✓ | macOS |

## Validation Architecture

There is no new code, so validation is entirely shell commands, run from the project root (`feel-good-scorew/`). `C` = the prereg commit, `C=$(git log --diff-filter=A --format=%H -- pipeline/PREREGISTRATION_V2.md)`.

| # | Proves | Command | Expected |
|---|---|---|---|
| 1 | v1 prereg has exactly 1 commit | `git log --format=%H -- pipeline/PREREGISTRATION.md \| wc -l` | `1` |
| 2 | v1 prereg unchanged | `shasum -a 256 pipeline/PREREGISTRATION.md` and `git diff --quiet HEAD -- pipeline/PREREGISTRATION.md && echo clean` | `f59ff7d6601f2e21986aaa8b6b399df30b34e95631c2098998fabacba5b36205`, `clean` |
| 2b | v1 code guard agrees | `cd pipeline && uv run python -c "from fgs.holdout import git_state; s=git_state('.'); print(s['prereg_commits'], s['prereg_unchanged'], s['ordered'])"` | `1 True True` (verified today) |
| 3 | v2 prereg is one commit, alone | `git log --format=%H -- pipeline/PREREGISTRATION_V2.md \| wc -l`; `git show --name-only --format= $C` | `1`; only `pipeline/PREREGISTRATION_V2.md` |
| 4 | no v2 code at or before C | `git grep -n -I -i -E "good_loss\|vs_exp_v2\|holdout.v2\|freeze.v2\|PREREGISTRATION_V2\|win_totals_2021" $C -- pipeline/src pipeline/tests pipeline/weights.yaml web` | empty output |
| 5 | phase touched nothing out of bounds | `git diff --name-only 515cfb3 HEAD -- pipeline web \| grep -v '^pipeline/PREREGISTRATION_V2.md$'` | empty (515cfb3 = HEAD at research time) |
| 6 | content covers INTEG-02/03 | `for s in MODEL-V2-01 MODEL-V2-02 MODEL-V2-03 DROPPED "53,701" 2025 2027 20271 2000 "next N same-season games" "opp_elo_pre - 1505" choose_alpha holdout-v2 freeze-v2 PREREGISTRATION_V2_DEVIATIONS.md f59ff7d6 "leak"; do grep -qF -- "$s" pipeline/PREREGISTRATION_V2.md \|\| echo MISSING "$s"; done` | no `MISSING` lines |
| 7 | verdict sentences present | `grep -c -E '^- .(yes\|slight\|no). ' pipeline/PREREGISTRATION_V2.md` (adapt to the chosen format) | ≥ 3 |
| 8 | existing tests still pass | `cd pipeline && uv run pytest -q` | `584 passed` (about 2m15s) |

**Sampling:** run checks 1–2b before writing (baseline) and 1–8 after the commit. All checks are read-only. Verification must never edit the prereg.

**Wave 0 gaps:** none. The existing infrastructure covers the phase.

## Security Domain

`security_enforcement: false` in config. Omitted.

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | First 2027 REG kickoff ≈ Thu Sept 9, 2027 | Calendar | Low. The prereg references the nflverse schedule, not a date. |
| A2 | nflverse `gameday`/`gametime` are US Eastern | Calendar | Medium. An eligibility comparison off by hours near the deadline. State the tz assumption in the prereg, or compare dates with a margin. |
| A3 | Push-before-deadline as an independent timestamp witness | Pitfall 7 | Low. Optional hardening. |
| A4 | v2-vs-v1 paired CI is narrower than v1-vs-Elo | Numbers | Low. ±0.05 is stated as the conservative figure. |

## Sources

### Primary (HIGH)
- Repo, read this session: `pipeline/PREREGISTRATION.md`, `HOLDOUT_RESULT.md`, `src/fgs/{backtest,holdout,bootstrap,features,efficiency,pbp,expectation,season_config}.py`. Live `git_state` probe and `uv run pytest -q` (584 passed).
- `git log`/`git show` on commits 42e57aa, 41e1e54.

### Secondary (MEDIUM)
- [NBC Sports PFT: Super Bowl LXII will be played on February 13, 2028](https://www.nbcsports.com/nfl/profootballtalk/rumor-mill/news/super-bowl-lxii-will-be-played-on-february-13-2028)
- [Fox 5 Atlanta: Date set for Super Bowl LXII](https://www.fox5atlanta.com/news/date-set-super-bowl-lxii-atlanta)
- [Awful Announcing: NFL keeping door open to 18-game schedule in 2027](https://awfulannouncing.com/nfl/keeping-door-open-18-game-schedule-2027.html), the reason D-16's schedule-format deviation stays relevant.

## Metadata
- Code citations: HIGH (read directly). Power numbers: HIGH (from the result file), with the scaling as reasoning. Calendar: MEDIUM/ASSUMED.
- Valid until: the v2 freeze (the code facts are stable while `pipeline/src` is frozen).

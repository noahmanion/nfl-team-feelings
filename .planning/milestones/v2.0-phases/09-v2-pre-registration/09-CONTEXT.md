# Phase 9: v2 Pre-registration - Context

**Gathered:** 2026-11-11
**Status:** Ready for planning
**Mode:** Smart discuss, FULL AUTONOMY: every grey area auto-accepted at the recommended answer (no AskUserQuestion). Each decision below is logged with its rationale.

<domain>
## Phase Boundary

Docs only. Deliver ONE new file, `pipeline/PREREGISTRATION_V2.md`, committed before any v2 model code exists. It pre-registers MODEL-V2-01 (good-loss luck), MODEL-V2-02 (free agency) and MODEL-V2-03 (Vegas win totals into the score), plus the dev ceiling, holdout, comparators, metrics, drop rules, verdict wording, void conditions and the guards that a future milestone must build.

Out of bounds: any edit to `pipeline/PREREGISTRATION.md` (the v1 holdout guard in `fgs/holdout.py` requires exactly one commit and an unchanged sha256), any change to `pipeline/src/**`, `weights.yaml`, `web/**`, and any v2 feature or model code (including new constants in `paths.py`; those land with the v2 model milestone).

</domain>

<decisions>
## Implementation Decisions

### Area 1: Holdout & data ceiling
- D-01 Holdout eligibility is by kickoff time, not by season label. A snapshot is eligible only if EVERY game in its N=8 target window kicks off after the committer timestamp of the v2 freeze commit (the commit that writes the frozen v2 weights file), and that commit descends from the PREREGISTRATION_V2.md adding commit. Rationale: research Pitfall 5. Weeks 1–10 of 2026 have already been watched, and the v2 ideas may have been inspired by them.
- D-02 Primary holdout = the full 2027 season (REG + playoffs targets), provided the freeze commit lands before the first 2027 regular-season kickoff. If the freeze misses that deadline, the primary holdout moves to the full 2028 season. That is a recorded deviation, not a partial 2027. Rationale: a clean full season beats a truncated one, and it removes any incentive to rush.
- D-03 Eligible 2026 snapshots (if any) are reported only as a secondary, never-gating slice. Given no model code this milestone, expect none.
- D-04 Development ceiling: all v2 feature design, fitting, alpha selection and sanity checks use seasons ≤ 2025 only. 2022–2025, the consumed v1 holdout, becomes legal training data, and the file says so: any "v2 beats v1 on 2022–25" claim is in-sample.
- D-05 The evaluation runs once, after the 2027 Super Bowl (~Feb 2028), through a guarded `fgs holdout-v2` command (specified here, built later).

### Area 2: Candidate input definitions
- D-06 MODEL-V2-01 good-loss luck = mean over the team's last 16 played games (REG + playoffs, crossing seasons, as-of rule identical to v1) of (result − p_deserved), where result is 1/0.5/0 and p_deserved = logistic(a + b·d). d is the game's net EPA/play differential (team offense EPA/play minus opponent offense EPA/play, using v1 `fgs.efficiency` play filters: pass|rush, garbage time dropped, not opponent-adjusted). (a, b) are fit once by logistic regression on all games with season ≤ 2025 and then frozen. It is 0.0 with no games or no pbp. It is ADDED as a 12th factor; v1 `luck` stays. Rationale: "deserved to win" from efficiency is the standard good-loss construct and uses data v1 already ingests. Keeping v1 luck lets the data decide.
- D-07 MODEL-V2-03 = re-sourced vs_exp (`vs_exp_v2`): the same formula as v1 vs_exp, but exp_total = normalized Vegas preseason win total for every season with a recorded preseason line (2003–2020 nflverse, 2021–2025 from Phase 11's `pipeline/inputs/` file, 2026/2027 preseason lines committed before that season's Week 1 kickoff). Model week-0 expectation is used only for 1999–2002. It REPLACES vs_exp in the v2 factor list. It lives in a v2-only module and never touches v1 `vegas_expectations` (DATA-02 guard). Rationale: it fixes the v1 train/deploy source switch (Vegas rows train, model rows deploy).
- D-08 MODEL-V2-02 free agency is DROPPED (weight 0, not built), pre-committed now. Probe evidence (nflreadpy 0.1.5 `load_contracts()`, 2026-11-11): 53,701 rows; no signing-date column at all (only integer `year_signed`); top-level `team` is the current team; `contract_history` gives team / contract_type / year_signed at year level only, so an October in-season UFA signing cannot be told apart from a March one, and any as-of-week feature leaks. UFA coverage reaches all 32 teams only from 2012 (1999–2010: 1–25 teams per year, so it is survivorship-biased). The file records the would-have-been definition for the record, and that re-entry requires a new pre-registration (v3), never an amendment.
- D-09 Model spec for v2 = the v1 procedure verbatim (per-snapshot z-scores, ridge with unpenalized intercept, `choose_alpha` LOSO grid, 2-dp rounding, no sign constraints), refit on 1999–2025, with factors = v1's 11 with vs_exp → vs_exp_v2, plus good_loss_luck. Model-selection budget: this one spec, plus the drop-rule ablations. No other variants reach the holdout.

### Area 3: Comparators, metrics & drop rules
- D-10 Primary hypothesis: the v2 composite ranks teams' next 8 games better than the frozen v1 composite. Primary metric: pooled Spearman(v2, N=8 target) − Spearman(frozen v1 composite, N=8), paired on identical rows. The target is v1 `backtest.TARGET_TEXT` unchanged.
- D-11 Comparators in order: frozen v1 composite (primary), plain Elo (secondary), and the Vegas closing spread (next-game Brier reference ceiling only).
- D-12 Uncertainty: paired percentile bootstrap, B = 2000, seed 20271, 95%. Spearman uses team-season clusters, Brier uses season-week clusters (season-block is impossible with one season). Power stated up front: v1's 4-season team-season CI half-width was ~0.026, so one season is ~×2, about ±0.05. Expect "slight" or "no".
- D-13 Drop rules on dev data only, decided before any v2 code. An input is kept iff (1) it is feasible leak-free (V2-02 already fails), (2) a walk-forward check (test seasons 2003–2025, each refit on earlier seasons) gives pooled ΔSpearman N=8 (with input − without) > 0, and (3) its fitted sign agrees in ≥ 60% of folds. Otherwise the weight is fixed at 0 and documented. If every input is dropped, v2 = the v1 procedure refit on 1999–2025, still frozen and evaluated as-is.
- D-14 Verdict wording fixed in advance (yes / slight / no, keyed on the team-season CI, the only CI available with one season): yes = diff > 0 and CI lower bound > 0; slight = diff > 0 and CI includes 0; no = diff ≤ 0. Ship rule: only "yes" replaces v1 on the public site. "slight" and "no" keep v1 public, and v2 is reported on the methodology page.

### Area 4: Integrity, void conditions & guards
- D-15 Void conditions: any change to v2 definitions, fit procedure, target or frozen (a, b) after the freeze commit; any v2 code computing a metric on season ≥ 2026 before `fgs holdout-v2`; a freeze commit that isn't a descendant of the prereg commit; PREREGISTRATION_V2.md with more than one commit; the evaluation data not pinned by sha256.
- D-16 Deviations go in a separate append-only `pipeline/PREREGISTRATION_V2_DEVIATIONS.md`, never in the prereg itself (it must stay at one commit, mirroring v1). Allowed deviations: nflverse schema changes, schedule-format changes (e.g. an 18-game season; the target stays the next 8 same-season games and season_config only gains the new length), and a missing 2027 preseason line (that team-season falls back to the model expectation; H3 reported as "not tested" if more than 4 teams are missing).
- D-17 What ships during the holdout: the site keeps the frozen v1 score; v2 runs shadow-only and is not displayed.
- D-18 Guards spec (built in the v2 model milestone): `fgs freeze-v2` refuses unless the prereg is committed, unchanged and at one commit; v2 commands refuse season ≥ 2026 metrics; `fgs holdout-v2` refuses before 2027 Super Bowl results exist, refuses on a second run, and records the sha256s and commits like v1.
- D-19 Verification for this phase: the v1 guard condition (PREREGISTRATION.md at exactly 1 commit with sha256 `f59ff7d6…5205`) checked by command; existing pipeline tests pass; `git log` shows no v2 model code before the prereg commit.

### Claude's Discretion
- Section layout and prose of PREREGISTRATION_V2.md (mirror v1's numbered-section contract style).
- Exact rounding and reporting tables for the eventual result file.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pipeline/PREREGISTRATION.md`: the v1 template (status/order, model, composite, target, data, metric, uncertainty, verdict, secondary, diagnostic, risks, if-it-fails, guards).
- `fgs/backtest.py` (`TARGET_TEXT`, `spearman`, `choose_alpha`), `fgs/bootstrap.py`, `fgs/holdout.py` (`_provenance` ancestry/one-commit checks): referenced by name as the procedures v2 reuses.
- `fgs/efficiency.py` play filters; `fgs/features.py` (luck = one-score W−L over 16; vs_exp formula); `fgs/expectation.py` (`vegas_expectations` normalization).

### Established Patterns
- Contract files are committed once and never edited; results record the prereg sha256 and commit.
- Frozen-model protections are code guards with commit-ancestry checks.

### Integration Points
- Phase 11 creates `pipeline/inputs/win_totals_2021plus.csv` (display-only in v2.0). V2-03 names it as the future source, read only by a v2 module.

</code_context>

<specifics>
## Specific Ideas

- The FA probe numbers (53,701 rows; UFA team coverage by year) go into the prereg as evidence.
- Use seed 20271 (v1 used 20221).

</specifics>

<deferred>
## Deferred Ideas

- Implementing v2 features, the model, freeze-v2 and holdout-v2 guards (future milestone, ~2027).
- Free agency as a v3 candidate if a free dated transaction source appears.

</deferred>

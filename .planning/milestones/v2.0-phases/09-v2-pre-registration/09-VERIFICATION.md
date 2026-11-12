---
phase: 09-v2-pre-registration
verified: 2026-11-11T00:00:00Z
status: passed
score: 4/4 roadmap success criteria verified (7/7 plan must-haves)
overrides_applied: 0
re_verification: false
---

# Phase 9: v2 Pre-registration Verification Report

**Phase Goal:** The v2 model is pre-registered in writing before any v2 model code exists, so the 2026-27 holdout stays clean.
**Status:** passed. All checks were read-only. Nothing under `pipeline/**` was touched.

## Observable Truths

| # | Truth (ROADMAP SC) | Status | Evidence |
|---|---|---|---|
| 1 | `PREREGISTRATION_V2.md` committed; v1 byte-identical at exactly 1 commit | VERIFIED | `git log -- pipeline/PREREGISTRATION_V2.md` gives 1 commit (9c32319, committed 2026-11-11T18:55:37-06:00), and that commit touches only that file. v1 file: 1 commit, sha256 `f59ff7d6...36205`, `git diff HEAD` clean. `fgs.holdout.git_state` prints `1 True True`. |
| 2 | Defines V2-01/02/03, the dev ceiling, holdout, comparators, metrics, drop rules and verdicts precisely | VERIFIED | 293-line file with sections 1-21: §2 ceiling ≤2025; §3 kickoff-time holdout (2027 primary, 2028 fallback); §5/6/7 are the three MODEL-V2 definitions, quoting v1 names (`net_epa`, `logit_fit`, `WP_LO`, `vegas_expectations`); §8 model spec using `choose_alpha`; §9 drop rules ("14 of 23"); §10 target (`TARGET_TEXT`); §11 comparators; §12-13 metric, bootstrap B=2000 seed 20271; §14 three verdict bullets (grep count = 3). The 17-string coverage loop (check 6) printed no MISSING lines. |
| 3 | Per-input leak-free feasibility, with a pre-committed drop for any that fails | VERIFIED | §4 feasibility table. §6 records MODEL-V2-02 as DROPPED with the `load_contracts` probe evidence (53,701 rows, no signing date, year-level `contract_history`, 32-team coverage from 2012). It also records that re-entry needs a v3 pre-registration. |
| 4 | No v2 model code before the pre-registration commit | VERIFIED | `git grep` for `good_loss\|vs_exp_v2\|holdout.v2\|freeze.v2\|PREREGISTRATION_V2\|win_totals_2021` at 9c32319 in `pipeline/src`, `pipeline/tests`, `weights.yaml` and `web` returns empty. The same grep at HEAD is also empty. `git diff --name-only 515cfb3 HEAD -- pipeline web` lists only the two prereg docs (`PREREGISTRATION_V2.md` and `PREREGISTRATION_V2_DEVIATIONS.md`). |

Plan must-have "existing tests pass": `uv run pytest -q` gives **584 passed in 146s**.

## Requirements Coverage

| Requirement | Status | Evidence |
|---|---|---|
| INTEG-02 | SATISFIED | Truths 1, 2 and 4. REQUIREMENTS.md maps it to Phase 9 only, so there are no orphans. |
| INTEG-03 | SATISFIED | Truth 3 (§4 and §6). Both IDs appear in the PLAN frontmatter and in REQUIREMENTS.md. |

## Assessment of the post-commit errata (4da61a5, `PREREGISTRATION_V2_DEVIATIONS.md`)

- It is a new docs-only file. `git show --name-only` on 4da61a5 lists only that file. It is not v2 model code, and it introduces no v2 code and no v2 number.
- Original §1.3 and §17.1 explicitly route errata and deviations to this append-only file, so the mechanism was pre-registered.
- It was committed the same day, 10 minutes after the prereg, before any freeze or data. Its header states that no v2 code or number existed. The repo confirms this.
- `PREREGISTRATION_V2.md` stayed at exactly 1 commit, so SC1 and the one-commit contract hold. The prereg file was not edited.
- Verdict: consistent with the phase goal. The holdout cleanliness (no v2 code or numbers before the commit) is unaffected.

**Warning (non-blocking, transparency):** §17.2 lists only 4 allowed deviations (schema, schedule format, missing 2027 line, move to 2028). Part A errata go beyond those. They rest only on the general wording of §1.3 ("Errata and allowed deviations"). Part A also says "where an entry and the original text disagree, the entry governs", and it widens void conditions (e.g. A1.2). It does so conservatively, but a strict reader could argue that it modifies the contract. This is a governance judgment, not a goal failure, because it happened pre-data. The future v2 milestone must treat the prereg and Part A as a single binding contract. The residual items in 09-REVIEW-FIX.md (Phase 11 `pipeline/inputs/` write-once constraint, guard hashing of Part A, witness rules) need to be carried into Phase 11 and the v2 model milestone.

## Anti-Patterns

TBD/TODO/FIXME/XXX/placeholder: 0 matches in both docs. No blockers.

## Human Verification

None required.

## Gaps Summary

No gaps. Goal achieved: the v2 contract was committed alone and exactly once before any v2 code, and v1's guard still passes.

_Verifier: Claude (gsd-verifier)_

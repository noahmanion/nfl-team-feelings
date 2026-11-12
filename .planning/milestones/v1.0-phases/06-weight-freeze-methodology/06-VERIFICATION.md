---
phase: 06-weight-freeze-methodology
verified: 2026-11-11T21:40:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 6: Weight Freeze and Methodology Verification Report

**Phase Goal:** The final in-season score is shown to predict future performance better than plain Elo, and users can see the evidence
**Status:** passed (with a weak-evidence caveat on SC3, see below)
**Re-verification:** No, initial verification

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | weights.yaml is Ridge-fit, rounded, standardized inputs; backtest set all weights/signs incl. streak and luck; refresh reads without refitting | VERIFIED | `pipeline/weights.yaml` header: FROZEN, ridge on per-snapshot z-scores, alpha chosen by LOSO CV on 1999-2021, 2 dp, no clipping or pruning. All 11 factors present. streak is -0.03 and luck is -0.35, kept as fitted. `cli.py` guards: `fgs backtest --propose-weights` and `fgs freeze` refuse when frozen (`FROZEN_MSG`). Refresh and export only read weights via `score.load_weights`. |
| 2 | One-time 2022-2025 holdout with season-level bootstrap CIs and every factor's fitted sign | VERIFIED | `HOLDOUT_RESULT.md` has a season-block CI (35 distinct resamples, B=2000), team-season and season-week CIs, and a table of all 11 factors with weight, sign and fold agreement. `uv run fgs holdout` run without `--force` printed "the holdout was already evaluated once ... --force exists but don't" and exited 1 (confirmed with `echo $?`). |
| 3 | Final score beats plain Elo out of sample on the documented target | VERIFIED (weak) | Pre-registered rule (PREREGISTRATION.md section 6, BACK-06): paired point difference in Spearman N=8 > 0. Result is +0.0039 (0.4853 vs 0.4814), so it passes the rule. See the caveat below. |
| 4 | Methodology page explains factors, weights/signs, and charts backtest vs baselines | VERIFIED | `web/src/components/MethodologyPage.svelte` is routed from `App.svelte`. It is fed by `web/public/data/methodology.json`, which has frozen, factors, candidates, walk_forward, holdout and notes. Tests, check and build pass. The orchestrator's 1280px browser check already confirmed all sections, both charts with whiskers, the verdict and the honest notes. |

**Score:** 4/4

### SC3 caveat (honest reading)

The pass is real by the pre-registered rule but the evidence is weak.

- Spearman N=8 difference is +0.0039. The season-block CI is [-0.0225, +0.0294] and the team-season CI is [-0.0211, +0.0306]. Both include 0.
- The score won 2 of 4 seasons (2022 and 2023 up, 2024 and 2025 down).
- N=4 difference is -0.0014 (secondary target).
- Brier is worse than Elo: +0.0014 (season-block CI [+0.0004, +0.0030]). The spread beats both by a wide margin.
- Diagnostic with vs_exp zeroed: +0.0032.
- The shipped verdict is "Yes, slightly ... within the noise of four seasons". The site states it that way, not as a clear win.

This is a legitimate pass of BACK-06 as defined. It is not strong evidence of improvement over Elo. The wording on the site is calibrated to that.

## Commit Order

`git log` timestamps and commit hashes match the provenance recorded in HOLDOUT_RESULT.md:

1. `42e57aa` 14:54:58, docs(06-01): pre-registration (PREREGISTRATION.md sha `f59ff7d6...` in the result)
2. `41e1e54` 15:09:21, feat(06-02): freeze weights.yaml + FREEZE_RESULT.json (sha `44b4c7b9...`)
3. `f2c0273` 15:22:17, feat(06-05): HOLDOUT_RESULT (evaluated 21:22:06Z, which is 15:22 CST)

Order is correct. The result records pipeline/src clean at run time and no refits on 2022-2025.

## Behavioral Checks

| Check | Result | Status |
|-------|--------|--------|
| `cd pipeline && uv run pytest -q` | 387 passed | PASS |
| `uv run fgs check` | all checks passed | PASS |
| `uv run fgs holdout` (no --force) | refuses, exit 1 | PASS |
| `web: npm run test` | 79/79 pass | PASS |
| `web: npm run check` | 0 errors, 0 warnings | PASS |
| `web: npm run build` | built successfully | PASS |

## Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| BACK-04 | SATISFIED | Frozen ridge weights file, rounded, refit refused, refresh reads only. |
| BACK-05 | SATISFIED | One-time holdout, season-level bootstrap CIs, all 11 factor signs reported. |
| BACK-06 | SATISFIED (weak) | Passes the pre-registered point-estimate rule (+0.0039); CIs include 0. |
| MODEL-15 | SATISFIED | All 11 weights and signs are data-determined; streak and luck are kept as fitted (negative). |
| SITE-07 | SATISFIED | Methodology page with factors, weights/signs, and backtest and holdout charts. |

No orphaned requirements; REQUIREMENTS.md maps exactly these five IDs to Phase 6.

## Anti-Patterns

No TBD, FIXME or XXX markers in `pipeline/src` or `web/src`. No stubs found. The methodology data is a real export, not hardcoded empty values.

## Human Verification Required

None outstanding. The visual check was done by the orchestrator at 1280px.

## Gaps Summary

No gaps. The phase goal is met as pre-registered. The strength of the claim is "slightly better than Elo, within noise", and the evidence is not a decisive improvement.

---

_Verified: 2026-11-11_
_Verifier: Claude (gsd-verifier)_

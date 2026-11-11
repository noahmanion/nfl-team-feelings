---
phase: 06-weight-freeze-methodology
plan: 05
subsystem: pipeline/holdout + web/methodology + README
tags: [holdout, preregistration, back-06, methodology, readme]
requires: [06-01 PREREGISTRATION.md, 06-02 frozen weights.yaml, 06-03 fgs holdout, 06-04 methodology page]
provides: [pipeline/HOLDOUT_RESULT.md, pipeline/HOLDOUT_RESULT.json, methodology.json holdout block, README "Does it work?" section]
affects: [Phase 7 (weights stay frozen; holdout cannot be re-run)]
tech-stack:
  added: []
  patterns: [one-time guarded evaluation, sha256 provenance, numbers copied verbatim from result JSON]
key-files:
  created:
    - pipeline/HOLDOUT_RESULT.md
    - pipeline/HOLDOUT_RESULT.json
  modified:
    - web/public/data/methodology.json
    - web/public/data/meta.json
    - README.md
    - .planning/REQUIREMENTS.md
decisions:
  - "Holdout verdict is 'slight': BACK-06 PASS by the pre-registered rule (diff > 0), but both CIs include 0. Recorded verbatim, with no re-tuning"
  - "BACK-06 is marked Complete in REQUIREMENTS.md, and the traceability row notes the CI includes 0"
metrics:
  duration: ~10 min
  completed: 2026-11-11
  tasks: 2
  files: 6
---

# Phase 6 Plan 05: One-time 2022–2025 holdout run Summary

The frozen feel-good score was evaluated once on the sealed 2022–2025 holdout. The pre-registered verdict is **"slight"**: "Yes, slightly: better than Elo alone on 2022–25, but within the noise of four seasons." BACK-06 is **PASS** (score − Elo Spearman N=8 = +0.0039 > 0). Both 95% CIs include 0, so the edge over Elo is not distinguishable from noise.

## Tasks

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Pre-flight + one-time `fgs holdout`; commit result | f2c0273 | pipeline/HOLDOUT_RESULT.md, pipeline/HOLDOUT_RESULT.json |
| 2a | Re-export site data with the holdout | 2b48d82 | web/public/data/methodology.json, meta.json |
| 2b | README: frozen weights, holdout section, status | 539d293 | README.md |

## Pre-flight (all passed)

1. Neither HOLDOUT_RESULT file existed.
2. `git status --porcelain` was empty for PREREGISTRATION.md, weights.yaml and pipeline/src.
3. The commit order checks out:
   - Prereg adding commit `42e57aa` (2026-11-11 14:54:58 −0600) is an ancestor of the weights commit `41e1e54` (2026-11-11 15:09:21 −0600).
   - `^frozen: true` appears once.
4. The gate was green: pytest 387 passed; vitest 79 passed; svelte-check 0 errors.
5. Recorded values:
   - sha256 PREREGISTRATION.md `f59ff7d6…b36205`
   - sha256 weights.yaml `44b4c7b9…cf76320`
   - HEAD `c7c5ef0d9d902c285470667f195df187229f99e1`

## The run

- `uv run fgs holdout` was run **exactly once**, without `--force`, at 2026-11-11T21:22:06Z. It did not crash, so it was not re-run.
- Result checks:
  - The result is strict JSON.
  - B=2000, seed 20221, seasons [2022, 2025], rerun false, 11 factors.
  - The provenance sha256s equal the pre-flight values, and src_clean is true.
- HOLDOUT_RESULT.md shows the same verdict.
- Guard check: a second `uv run fgs holdout` without the flag exited **1** with "already evaluated once … --force exists but don't". Nothing was computed.
- After the task, the sha256s of PREREGISTRATION.md and weights.yaml are unchanged. HOLDOUT_RESULT.md is `242eb6eb…6722` and the .json is `088817b2…40aa`.
- Commit order: prereg 42e57aa → freeze 41e1e54 → holdout f2c0273.

## Result (copied from HOLDOUT_RESULT.json)

Snapshots: 2287 (N=8 and N=4); 1136 next games.

| Candidate | Spearman N=8 [team-season CI] | N=4 | Brier [season-week CI] |
|---|---|---|---|
| Feel-good score (frozen) | 0.4853 [0.3852, 0.5719] | 0.4480 | 0.2242 [0.2155, 0.2335] |
| Elo alone | 0.4814 [0.3774, 0.5689] | 0.4494 | 0.2228 [0.2146, 0.2313] |
| Season win % | 0.3889 [0.2939, 0.4698] | 0.3579 | 0.2364 |
| Last 16 | 0.4391 [0.3363, 0.5311] | 0.4142 | 0.2261 |
| Point differential | 0.4496 [0.3473, 0.5328] | 0.4001 | 0.2342 |
| Vegas spread | — | — | 0.2097 [0.2015, 0.2187] |
| Elo 538 closed form | — | — | 0.2222 |

- **Score − Elo, Spearman N=8:** +0.0039.
  - Season-block CI [−0.0225, +0.0294]; team-season CI [−0.0211, +0.0306].
  - Won **2 of 4** seasons: 2022 +0.0292, 2023 +0.0335, 2024 −0.0132, 2025 −0.0266.
- **Score − Elo, Spearman N=4:** −0.0014. Season-block CI [−0.0187, +0.0161]; team-season CI [−0.0234, +0.0203].
- **Brier vs Elo:** +0.0014, so the score is slightly worse. Season-block CI [+0.0004, +0.0030]; season-week CI [−0.0018, +0.0044].
- **Brier vs spread:** +0.0145. Season-block CI [+0.0131, +0.0159]; season-week CI [+0.0099, +0.0192].
- **vs_exp-zeroed diagnostic:** Spearman N=8 0.4846; − Elo +0.0032, cluster CI [−0.0252, +0.0320]. Zeroing vs_exp makes the gap slightly smaller, not bigger, so the source switch is not what holds the score back.
- **Context only, not a forecast:** the training stand-in in prereg §11.3 gave +0.019 (cluster CI [−0.002, +0.040]). The holdout gap is about a fifth of that.

### Factor signs (frozen)

| Factor | Weight | Sign | Folds |
|---|---|---|---|
| elo | 2.59 | + | 19/19 |
| season_record | 1.84 | + | 19/19 |
| last16 | −0.21 | − | 14/19 |
| mov | 1.24 | + | 19/19 |
| sow | −0.56 | − | 14/19 |
| streak | −0.03 | − | 12/19 |
| luck | −0.35 | − | 19/19 |
| epa_traj | −0.33 | − | 19/19 |
| qb_trend | 0.63 | + | 19/19 |
| vs_exp | −1.22 | − | 18/19 |
| po_trend | −0.05 | − | 17/19 |

## Note for the user

BACK-06 passes the literal pre-registered rule, so there is no formal gap. In practice, though, the score is about tied with plain Elo out of sample:
- the N=8 gap is +0.004 with CIs straddling 0;
- N=4 is −0.001;
- next-game Brier is slightly worse than Elo.

No explanation is claimed. The pre-registered vs_exp diagnostic does not account for it. Nothing was re-tuned.

## Task 2 outputs

- `fgs export`:
  - methodology.json `holdout` has the verdict and headline equal to the result.
  - The `holdout_pending` note is gone.
  - The vs_exp note now carries the diagnostic numbers.
- README:
  - The frozen weights replace the stale interim list (with fold counts), which resolves the deferred item from 06-02.
  - The "Sealed holdout" bullet now says it was evaluated once.
  - New "## Does it work? (2022–2025 holdout)" section with the headline verbatim and BACK-06 PASS. It has the table (Spearman 3 dp, Brier 4 dp), the diff with both CIs, won 2 of 4, the diagnostic, a link to the full result, and the `--force` warning.
  - The Status line now says Phase 6 is done.
- Gate: pytest 387 passed; vitest 79 passed; svelte-check 0/0; `npm run build` OK.
- Screenshots: Python Playwright, using the cached chromium-headless-shell-1248 binary via `executable_path`. They were taken against `vite preview` at 375×812 and 1280×900, and the preview server was stopped afterwards.
  - Both widths: no horizontal scroll (scrollWidth == clientWidth), the "Does it work?" lead equals the headline, and the walk-forward and holdout facets both show CI whiskers.
  - The screenshots are in the session scratchpad (not committed).

## Deviations from Plan

1. **[Rule 3] Screenshot tooling.** Python Playwright expected the browser build 1194, which is not installed, so I passed the installed headless shell (1248) explicitly. This has no effect on the product.
2. **meta.json** changed in the export because of its timestamp, so it was committed with methodology.json.
3. **REQUIREMENTS.md:** MODEL-15, BACK-04, BACK-05, BACK-06 and SITE-07 are marked complete. The BACK-06 row records that the CI includes 0 and the verdict is "slight". STATE.md and ROADMAP.md were not touched, per the orchestrator.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: pipeline/HOLDOUT_RESULT.md, pipeline/HOLDOUT_RESULT.json, the README section, methodology.json holdout
- FOUND commits: f2c0273, 2b48d82, 539d293

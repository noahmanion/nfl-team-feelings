# Holdout result (2022–2025), evaluated once on 2026-11-11T21:22:06+00:00

Written by `uv run fgs holdout`. Do not edit. The rules are fixed in pipeline/PREREGISTRATION.md.

**Verdict: slight** — Yes, slightly: better than Elo alone on 2022–25, but within the noise of four seasons.

BACK-06: PASS (score − Elo Spearman N=8 > 0)

## Provenance

- PREREGISTRATION.md sha256: `f59ff7d6601f2e21986aaa8b6b399df30b34e95631c2098998fabacba5b36205` (commit `42e57aa148c3e679e1bed169a0d4b829df7ea6a5`)
- weights.yaml sha256: `44b4c7b9115ca620dbe5ffb588792aecf51c05ca2b86cc440845a6b40cf76320` (commit `41e1e54ac411aa650692953eeee9c3f22bac9039`)
- git HEAD: `c7c5ef0d9d902c285470667f195df187229f99e1`
- pipeline/src clean at run time: True
- Brier logistic maps fit on seasons <= 2021; no refits on 2022–2025

## Candidates

Snapshots: 2287 (N=8), 2287 (N=4). Next games: 1136.

| Candidate | Spearman N=8 [95% CI, team-season] | Spearman N=4 | wk0 | early | mid | late | Brier [95% CI, season-week] |
|---|---|---|---|---|---|---|---|
| Feel-good score (frozen) | 0.4853 [0.3852, 0.5719] | 0.4480 | 0.4286 | 0.4870 | 0.4977 | 0.4757 | 0.2242 [0.2155, 0.2335] |
| Elo alone | 0.4814 [0.3774, 0.5689] | 0.4494 | 0.4575 | 0.4894 | 0.4794 | 0.4784 | 0.2228 [0.2146, 0.2313] |
| Season win % | 0.3889 [0.2939, 0.4698] | 0.3579 | — | 0.3027 | 0.4650 | 0.4507 | 0.2364 [0.2289, 0.2448] |
| Last 16 games | 0.4391 [0.3363, 0.5311] | 0.4142 | 0.4476 | 0.4310 | 0.4218 | 0.4574 | 0.2261 [0.2185, 0.2335] |
| Point differential | 0.4496 [0.3473, 0.5328] | 0.4001 | — | 0.3815 | 0.5170 | 0.4982 | 0.2342 [0.2262, 0.2428] |
| Vegas spread (Brier only) | — | — | — | — | — | — | 0.2097 [0.2015, 0.2187] |
| Elo 538-style (Brier only) | — | — | — | — | — | — | 0.2222 |

## Difference (score − Elo)

- Spearman N=8: +0.0039; season-block CI [-0.0225, +0.0294]; team-season CI [-0.0211, +0.0306]; won 2 of 4 seasons (2022 +0.0292, 2023 +0.0335, 2024 -0.0132, 2025 -0.0266)
- Spearman N=4: -0.0014; season-block CI [-0.0187, +0.0161]; team-season CI [-0.0234, +0.0203]
- Brier vs Elo: +0.0014; season-block CI [+0.0004, +0.0030]; season-week CI [-0.0018, +0.0044] (negative = the score is better)
- Brier vs Vegas spread: +0.0145; season-block CI [+0.0131, +0.0159]; season-week CI [+0.0099, +0.0192] (the spread is the market ceiling)

Diagnostic (pre-registered diagnostic, not used for the verdict): score with vs_exp zeroed, Spearman N=8 0.4846; − Elo +0.0032, team-season CI [-0.0252, +0.0320].

## Factors (frozen weights.yaml)

| Factor | Weight | Sign | Folds with this sign |
|---|---|---|---|
| elo | 2.59 | + | 19/19 |
| season_record | 1.84 | + | 19/19 |
| last16 | -0.21 | - | 14/19 |
| mov | 1.24 | + | 19/19 |
| sow | -0.56 | - | 14/19 |
| streak | -0.03 | - | 12/19 |
| luck | -0.35 | - | 19/19 |
| epa_traj | -0.33 | - | 19/19 |
| qb_trend | 0.63 | + | 19/19 |
| vs_exp | -1.22 | - | 18/19 |
| po_trend | -0.05 | - | 17/19 |

Bootstrap: B=2000, seed=20221, percentile 95% intervals, paired across candidates; season block has 35 distinct resamples. Cluster CIs: team-season stratified by season (Spearman), season-week stratified by season (Brier).

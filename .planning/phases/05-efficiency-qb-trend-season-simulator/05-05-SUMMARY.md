---
phase: 05-efficiency-qb-trend-season-simulator
plan: 05
subsystem: pipeline + web
tags: [po_trend, playoff-odds, A5-override, expectation-source, qb, weights, readme, phase-gate]
requires:
  - phase: 05-04
    provides: features playoff_prob/exp_wins/vs_exp + expectation_source/qb_name display columns, derived["sim"], 10 weights
provides:
  - po_trend factor (MODEL-12), 11th and last factor; final interim 11-factor weights
  - export rows carry playoff_prob (int 0-100 or null, A5 post-season override), expectation_source, qb
  - team page "Playoff odds NN%" + "QB name" stat line
  - README closing Phase 5
affects: [phase-06]
tech-stack:
  added: []
  patterns:
    - "display-only override in export (_playoff_display) keeps the raw sim value as the factor input"
key-files:
  created: []
  modified:
    - pipeline/src/fgs/features.py
    - pipeline/src/fgs/score.py
    - pipeline/src/fgs/backtest.py
    - pipeline/src/fgs/explain.py
    - pipeline/src/fgs/export.py
    - pipeline/weights.yaml
    - pipeline/BACKTEST_LOG.md
    - pipeline/tests/test_features.py
    - pipeline/tests/test_backtest.py
    - pipeline/tests/test_explain.py
    - pipeline/tests/test_export.py
    - web/src/lib/types.ts
    - web/src/lib/team.ts
    - web/src/lib/team.test.ts
    - web/src/components/TeamPage.svelte
    - web/public/data/**
    - README.md
    - .planning/REQUIREMENTS.md
key-decisions:
  - "po_trend kept at weight -0.01 (dSpearman -0.0003, dBrier +0.00006); corr 0.70 with 3-week dElo, so Elo already carries it"
  - "Final interim 11 weights: elo 2.59, season_record 1.83, last16 -0.20, mov 1.24, sow -0.56, streak -0.05, luck -0.35, epa_traj -0.33, qb_trend 0.63, vs_exp -1.23, po_trend -0.01 (N8 Spearman 0.5262)"
  - "A5 override is export-only: playoff_display = 100/0 once all REG games are played (asof <= week) and a non-REG game row exists; raw playoff_prob untouched"
requirements-completed: [MODEL-12, MODEL-13, MODEL-08, MODEL-11]
duration: ~25min
completed: 2026-11-11
---

# Phase 5 Plan 05: po_trend, playoff odds on team pages, Phase 5 close-out Summary

**po_trend (3-week change in raw simulated playoff odds, same season) is the 11th factor, with a reported weight of −0.01. Every exported row now carries integer playoff odds (the actual 100/0 once the regular season is over), the expectation source and the current QB. The team page shows "Playoff odds NN% · QB name", and the README closes Phase 5.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-11-11
- **Tasks:** 3 (9 commits)

## Accomplishments

- **po_trend (MODEL-12):** `PO_LAG = 3`, a self-join of the sim frame on (season, franchise, max(week − 3, 0)). It uses the raw sim value. A null current or lagged value gives 0, as do week 0 and running without a sim. Hand-built tests check the 0.25 case (p5 − p2), the week-2 → week-0 lag, a week-1 lag that does not cross into the prior season, and the no-sim case.
- **Backtest reproduced research exactly.** No fallback was needed.

| step | Spearman N=8 | R² N=8 | ΔSpearman | ΔBrier |
|---|---|---|---|---|
| ridge:+vs_exp (base) | 0.526532 | 0.276856 | | |
| ridge:+po_trend | 0.526188 | 0.276352 | −0.0003 | +0.00006 (0.217805 → 0.217865) |

  Proposal at 2 dp matches research: elo 2.59, season_record 1.83, last16 −0.20, mov 1.24, sow −0.56, streak −0.05, luck −0.35, epa_traj −0.33, qb_trend 0.63, vs_exp −1.23, po_trend −0.01. The last fold (2021) gives po_trend −0.0057. Re-run in scratch: corr(po_trend, 3-week ΔElo) = 0.697 over 1999–2021, week > 0, 15,425 rows (research 0.70).
- **Export:** `_playoff_display` adds the displayed int (round(100·p)). The A5 override applies once a season's REG games are all played with asof_week ≤ week and at least one non-REG row exists: playoff teams show 100 and the rest 0. Rows also gain `expectation_source` and `qb` (from qb_name). `playoff_prob` is null when derived has no sim.
- Real-data checks: every completed season (1999–2025) at its last REG week shows exactly `playoff_teams(season)` rows at 100 and the rest at 0. In latest.json (2026 week 9), Σ playoff_prob = 1401 (target 1400 ± 32) and every source is `{'model'}`.
- **Web:** `Row` gains `playoff_prob?`, `expectation_source?` and `qb?`. `playoffText(p)` returns "Playoff odds 87%" for 87, "Playoff odds 0%" for 0, and null for null/undefined. TeamPage adds a third muted `.sub` line under the record/rank line. It shows the odds and `QB {name}`, separated by the existing `.sep` dot, with no new CSS.
- **README:** all 11 factors with their current weights and honest notes: epa_traj ≈0 and negative, qb_trend is the biggest Phase 5 gain, vs_exp is Vegas-dependent, po_trend ≈0. It adds a playoff odds paragraph (2,000 sims, σ=100, era rules, simplified tiebreakers, about one spot off every three seasons, model-vs-Vegas r 0.86, actual result after the REG), the low-confidence 1999–2000 pbp, the first-run pbp download note, and a Status line saying Phase 5 is done.

## BACKTEST_LOG Phase 5 rows (in order)

| factor | ΔSpearman | ΔR² | sign (w) |
|---|---|---|---|
| epa_traj | −0.0000 | −0.0003 | − (−0.20) |
| qb_trend | +0.0028 | +0.0037 | + (0.63) |
| vs_exp | +0.0019 | +0.0021 | − (−1.24) |
| po_trend | −0.0003 | −0.0005 | − (−0.01) |

Final N=8 Spearman is 0.5262, inside [0.523, 0.529].

## Phase gate

- `uv run pytest -q`: 298 passed (~67 s)
- `uv run fgs refresh`: **refreshed in 2.3 s** (wall 2.53 s), all checks passed including sim_sums. It only changed meta.json `generated_at`, which I restored, so the committed data is the `fgs export` output.
- web: vitest 66 passed, svelte-check 0 errors / 0 warnings, vite build OK

## Browser check data (latest 2026 week 9, baseline 49)

| # | team | score | W-L | PO | QB | points | blurb |
|---|---|---|---|---|---|---|---|
| 1 | JAX | 96 | 6-2 | 97% | T.Lawrence | elo 23, season_record 13, last16 −2, mov 15, sow −4, streak 0, luck −1, epa_traj 4, qb_trend 6, vs_exp −7, po_trend 0 | The Jaguars are one of the best teams in football, and have been blowing teams out. |
| 2 | BUF | 93 | 7-1 | 99% | J.Allen | elo 35, season_record 21, last16 −2, mov 12, sow −7, streak 0, luck −4, epa_traj −2, qb_trend 3, vs_exp −12, po_trend 0 | The Bills are one of the best teams in football, and are 7-1. |
| 3 | SF | 93 | 7-1 | 93% | B.Purdy | elo 24, season_record 22, last16 −3, mov 14, sow −6, streak 0, luck −4, epa_traj 4, qb_trend 6, vs_exp −13, po_trend 0 | The 49ers are one of the best teams in football, and are 7-1. |
| 30 | MIA | 7 | 1-7 | 0% | M.Willis | elo −23, season_record −20, last16 1, mov −12, sow 5, streak 0, luck −1, epa_traj −3, qb_trend −1, vs_exp 12, po_trend 0 | The Dolphins are one of the worst teams in football, and are just 1-7. |
| 31 | LAC | 6 | 0-8 | 0% | J.Herbert | elo −21, season_record −26, last16 1, mov −16, sow 7, streak 1, luck 1, epa_traj −3, qb_trend −7, vs_exp 20, po_trend 0 | The Chargers are just 0-8, and are one of the worst teams in football. |
| 32 | TEN | 5 | 1-7 | 0% | C.Ward | elo −32, season_record −19, last16 2, mov −9, sow 6, streak 0, luck 4, epa_traj −2, qb_trend −2, vs_exp 8, po_trend 0 | The Titans are one of the worst teams in football, and are just 1-7. |

Check `#/team/JAX` and `#/team/TEN` at 375px and 1280px: 11 bars, then the line "Playoff odds 97% · QB T.Lawrence". A past completed season (e.g. `#/team/BUF` at 2021 week 18) should show 100%.

## Task Commits

1. **Task 1: po_trend**
   - `7ecad44` test: failing po_trend tests
   - `4a7367f` feat: po_trend feature, FACTORS, PHRASES, ridge set, test lists
   - `9c51be4` feat: final interim 11 weights + BACKTEST_LOG row
   - `c915e53` chore: regenerated data (11 factors)
2. **Task 2: export + team page**
   - `761504b` test: failing export tests (A5 unit, range, override on real data)
   - `2db62b1` feat: export playoff_prob/expectation_source/qb
   - `bb034bd` feat: web playoffText + TeamPage stat
   - `a6b4320` chore: regenerated data
3. **Task 3: README** - `d96569c` docs

## Deviations from Plan

- **REQUIREMENTS.md:** besides this plan's IDs, I also marked DATA-05 (05-01) and MODEL-05 (05-03) complete. Both were delivered earlier in the phase but were still Pending, and the orchestrator allowed marking Phase 5 requirements complete.
- **po_trend description:** it always carries the "adds about nothing…" suffix because the weight came out ≈0 and negative, as the plan specified.
- Otherwise the plan was executed as written. Every number is within ±0.002 of research, so the fallback rule did not apply.

## TDD Gate Compliance

RED commits `7ecad44` and `761504b` precede their GREEN `feat` commits `4a7367f` and `2db62b1`. No refactor commits were needed.

## Known Stubs

None. `callouts.json` stays `[]` from earlier phases and is out of scope.

## Self-Check: PASSED

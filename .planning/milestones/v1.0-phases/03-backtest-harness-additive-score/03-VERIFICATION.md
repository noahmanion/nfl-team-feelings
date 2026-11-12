---
phase: 03-backtest-harness-additive-score
verified: 2026-11-11T19:30:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 3: Backtest Harness & Additive Score Verification Report

**Phase Goal:** The score becomes an additive, backtested composite that can be compared honestly against baselines, and users can watch every team's mood over time
**Status:** passed (initial verification)

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | README states the backtest target, committed before weight tuning | VERIFIED | README "Backtest target" section added in 40ea3bd (2026-11-11 13:08:45); weights.yaml/ridge fit in fc4f65d (13:13:43). 40ea3bd is an ancestor of fc4f65d. |
| 2 | One command prints walk-forward metrics for Elo, season win %, last-16, point diff, Vegas spread; Elo Brier ~0.22-0.23 | VERIFIED | `uv run fgs backtest` ran: rows for elo, season_wpct, last16, pd_pg, spread (plus elo_538 and ridge composites), N=8 and N=4, test seasons 2003-2021, holdout sealed. Elo Brier 0.2197 (just under the 0.22 edge, consistent with "about"); spread 0.2112. |
| 3 | Leakage test passes | VERIFIED | `pipeline/tests/test_leakage.py` (fake future games, truncation, synthetic, import firewall); `uv run pytest -q` gave 169 passed. |
| 4 | Score is sum of weight x z with stored contributions; season record and last-16 show measured delta | VERIFIED | `score.py` additive engine; `weights.yaml` (elo 4.58, season_record 0.63, last16 -1.25); `BACKTEST_LOG.md` records dSpearman +0.0008/+0.0013 (season_record) and +0.0033/+0.0042 (last16) with fitted signs; `latest.json` rows carry `contribs` per factor and `meta.json` carries `factors`. |
| 5 | Mood-over-time chart for all teams, highlighted team, fixed y-axis, season breaks | VERIFIED | `HistoryChart.svelte` y domain fixed [0,100], highlight line, season-aware x; `history.json` generated; web tests 43 passed, svelte-check 0 errors, build OK; orchestrator browser check confirmed render at 1280px dark and 375px fallback. |

**Score:** 5/5

## Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| BACK-01 | SATISFIED | Truth 1 |
| BACK-02 | SATISFIED | Truth 2 |
| BACK-03 | SATISFIED | Truth 3 |
| MODEL-14 | SATISFIED | Truth 4 (score.py, contribs in data) |
| MODEL-03 | SATISFIED | season_record factor, log delta |
| MODEL-04 | SATISFIED | last16 factor, log delta |
| SITE-03 | SATISFIED | Truth 5 |

No orphaned requirements. BACK-04/05/06 are mapped to Phase 6 in REQUIREMENTS.md and are out of scope here.

## Behavioral Spot-Checks

| Check | Result | Status |
|-------|--------|--------|
| `cd pipeline && uv run pytest -q` | 169 passed | PASS |
| `uv run fgs backtest` | prints tables, writes backtest.json | PASS |
| `npm run test` / `check` / `build` | 43 passed / 0 errors / built | PASS |

## Notes (non-blocking)

- Ridge composites beat plain Elo by only a tiny margin (Spearman 0.515 vs 0.513); the goal is honest measurement, not a large win. Beating Elo out of sample (BACK-06) is a Phase 6 requirement.
- Last-16 weight is negative by design and documented in weights.yaml.
- Minor chart cosmetics (tick overlap, band label collision) are being handled in code review fixes.
- Anti-pattern/debt-marker scan was not exhaustive; no blockers surfaced in the checks run.

## Human Verification Required

None. Browser check was already performed by the orchestrator.

_Verified: 2026-11-11_
_Verifier: Claude (gsd-verifier)_

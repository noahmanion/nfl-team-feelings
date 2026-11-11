---
phase: 04-game-result-factors-team-deep-dive
verified: 2026-11-11T00:00:00Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
---

# Phase 4: Game-Result Factors & Team Deep-Dive Verification Report

**Phase Goal:** Users can click any team and understand exactly why its score is what it is, with schedule-derived factors added one at a time and each one backtested.
**Status:** passed
**Re-verification:** No (initial)

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Factors mov, sow, streak, luck each added and backtested individually (MODEL-06/07/09/10) | VERIFIED | BACKTEST_LOG.md has one row per factor with ΔSpearman, ΔR² and fitted sign: mov +0.0026/+0.0015 (+), sow +0.0047/+0.0048 (−), streak +0.0000/−0.0001 (−), luck −0.0008/−0.0006 (−). `fgs backtest` output shows ridge:+mov, +sow, +streak and +luck candidates at N=8 and N=4. |
| 2 | Each factor landed in its own commit | VERIFIED | git log: 04e2aba (mov), aaada37 (sow), a433d5d (streak), 8457998 (luck). Each is followed by its own weights-proposal commit (13feaea, 9e29e52, 1a20e90, 1c3fc5d) and a data regeneration commit. |
| 3 | Factor points sum to score minus baseline | VERIFIED | Script over every row in web/public/data/snapshots/*.json: 19422 rows, 0 mismatches, baseline 49 from meta.json. |
| 4 | Team deep-dive shows score, mood label, one-liner, factor bars, recent games (SITE-02) | VERIFIED | Orchestrator browser check of #/team/BUF. Code: components/TeamPage.svelte, route `team` in lib/router.ts, lib/team.ts helpers with tests. |
| 5 | Auto-generated plain-English one-liner per team (INSIGHT-05) | VERIFIED | `blurb` present on snapshot rows (e.g. GB 2021 wk0), exported by the pipeline explain module and rendered in TeamPage. |
| 6 | Test suites and build pass | VERIFIED | pytest: 217 passed. web tests: 60 passed. svelte-check: 0 errors, 0 warnings. vite build succeeded. |

**Score:** 6/6

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Pipeline tests | `uv run pytest -q` | 217 passed | PASS |
| Backtest | `uv run fgs backtest` | all 7 factor candidates reported, wrote backtest.json | PASS |
| Web tests, check, build | `npm run test`, `check`, `build` | 60 passed, 0 errors, built | PASS |
| Points sum invariant | python script over snapshots | 0 / 19422 mismatches | PASS |

## Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| MODEL-06 | SATISFIED | mov factor, own commit, own log row |
| MODEL-07 | SATISFIED | sow factor, own commit, own log row |
| MODEL-09 | SATISFIED | streak factor, own commit, own log row |
| MODEL-10 | SATISFIED | luck factor, own commit, own log row |
| SITE-02 | SATISFIED | TeamPage with bars summing to score, recent games, label, blurb |
| INSIGHT-05 | SATISFIED | blurbs exported and displayed |

MODEL-08 is mapped to Phase 5 and is not part of this phase. No orphaned requirements.

## Anti-Patterns

No TBD, FIXME or XXX markers in web/src or pipeline source (the only XXX hits are test fixtures for an invalid team code).

## Notes (non-blocking)

- Streak and luck have a near-zero or slightly negative Δ. The log records this and the factors were kept per CONTEXT, with an explicit sign. This is an honest backtest result, not a gap.
- Cosmetic issues from the browser check are being handled separately by the code review fixes and do not affect the goal.

## Human Verification Required

None. Browser verification was already done by the orchestrator.

_Verified: 2026-11-11_
_Verifier: Claude (gsd-verifier)_

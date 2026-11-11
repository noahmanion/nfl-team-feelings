---
phase: 01-data-foundation-elo-core
verified: 2026-11-11T19:00:00Z
status: passed
score: 4/4 roadmap success criteria verified
overrides_applied: 0
---

# Phase 1: Data Foundation & Elo Core Verification Report

**Phase Goal:** Every NFL game since 1999 is loaded, cleaned, and replayed chronologically into a trustworthy Elo rating for every franchise at every week
**Status:** passed
**Re-verification:** No (initial)

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Pipeline pulls all games 1999 to current week via nflreadpy, caches locally, re-run reads cache | VERIFIED | `uv run fgs build` exit 0: raw 7548 games, latest 2026 week 9. `data/cache/schedules.parquet` exists. A re-run with proxies pointed at a dead address succeeded, so it made no network call. |
| 2 | Data checks pass (31/32 franchises, games per team-season, no unmatched codes, LV/LAC/LA/WAS unbroken) | VERIFIED | `uv run fgs check` exit 0: 12 checks ok (codes, team_counts, games_per_team, continuity, divisions, snapshot_grid, ...). No OAK/SD/STL rows in team_games (0). |
| 3 | Ties 0.5, neutral no HFA, BUF-CIN 2022 skipped without crash | VERIFIED | Outcome values are {0, 0.5, 1}. A 2002 ATL-PIT tie moved Elo toward expectation (ATL +7.5, PIT -7.5). 206 neutral team-games are present. BUF and CIN each show 16 played 2022 REG games, with no crash and no week-17 BUF game row. |
| 4 | CLI prints Elo ranking for any (season, week) incl. bye and week 0; 2026 ranking plausible | VERIFIED | `fgs elo --season 2026 --week 0` prints 32 teams. 1999 wk0 shows CLE 1300 and the rest 1505. 2025 wk7 prints 32 teams, and BUF/BAL (on bye) hold the same Elo as wk6. `--week 12` gives "not played yet; latest played week is 9", rc=1. |

Plausibility: the 2026 preseason top is SEA 1676, followed by DEN, LA, HOU and BUF. The bottom is LV, TEN and NYJ. This is consistent with the 2025 season results (a SEA-led top, weak bottom teams). The week-9 table has BUF 7-1-0 on top. The ratings are in a sensible range and the regression to the mean is visible.

**Score:** 4/4

## Tests and Checks

| Command | Result |
|---------|--------|
| `uv run fgs build` | exit 0 |
| `uv run fgs check` | 12/12 ok, "all checks passed" |
| `uv run pytest -q` | 74 passed |
| `uv run fgs elo --season 2026 --week 0` | 32 rows, plausible |
| bye-week query (2025 wk 7, BUF/BAL Elo and W-L-T carried over from wk 6) | pass |

## Requirements Coverage

Requirement IDs across the three PLANs: DATA-01, DATA-02, DATA-03, DATA-04, DATA-07, MODEL-01, MODEL-02. All appear in REQUIREMENTS.md and are marked [x].

| Requirement | Status | Evidence |
|-------------|--------|----------|
| DATA-01 | SATISFIED | build and cache verified; 7548 games from 1999 |
| DATA-02 | SATISFIED | franchise continuity check passes; no OAK/SD/STL |
| DATA-03 | SATISFIED | season_config; config_coverage and divisions checks pass |
| DATA-04 | SATISFIED | ties, neutral sites, BUF-CIN verified |
| DATA-07 | SATISFIED | `fgs check` covers counts, games per team and codes |
| MODEL-01 | SATISFIED | chronological replay; zero-sum, league_mean and continuity checks pass |
| MODEL-02 | SATISFIED | snapshot grid with bye weeks and week 0 verified |

No orphaned requirements. The other Phase 1-adjacent IDs (DATA-05, DATA-06, MODEL-03 and later) belong to later phases.

## Anti-Patterns

No TBD/FIXME/XXX markers in `pipeline/src`. The review-fix report (9 of 9 fixed) is consistent with the observed behavior. WR-02, the date-ordered replay with `asof_week`, is flagged "requires human verification" in the fix report. The `week_date_order` check passes on real data and `asof_week == week` for all games, so there is no observable regression.

## Human Verification Required

None.

## Gaps Summary

No gaps. The phase goal is achieved.

_Verifier: Claude (gsd-verifier)_

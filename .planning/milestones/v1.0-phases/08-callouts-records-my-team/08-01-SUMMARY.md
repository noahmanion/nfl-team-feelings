---
phase: 08-callouts-records-my-team
plan: 01
subsystem: pipeline
tags: [callouts, insights, evidence, export, polars]
requires:
  - phase 6 frozen weights (weights.yaml frozen: true)
  - phase 7 offseason.draft block and week-0 cross-season deltas
provides:
  - fgs.insights (record_ranks, gap_flags, gap_callouts, movers, callouts_by_week, copy helpers, weights fingerprint)
  - fgs.evidence + `fgs evidence` (dev-only)
  - pipeline/callout_evidence.json (committed, 1999-2021 only)
  - JSON contract: snapshots/{season}.json `callouts` keyed by week; callouts.json = latest week list
affects:
  - 08-02 (renders the cards and movers strip)
  - 08-03 (adds misery/joy to callouts_by_week)
tech-stack:
  added: []
  patterns:
    - frozen dev-time evidence JSON + fingerprint staleness guard in the export (ValueError)
    - firewall extended: insights.py never imports backtest; export/insights never import evidence
key-files:
  created:
    - pipeline/src/fgs/insights.py
    - pipeline/src/fgs/evidence.py
    - pipeline/callout_evidence.json
    - pipeline/tests/test_insights.py
    - pipeline/tests/test_evidence.py
  modified:
    - pipeline/src/fgs/season_config.py
    - pipeline/src/fgs/paths.py
    - pipeline/src/fgs/cli.py
    - pipeline/src/fgs/export.py
    - pipeline/tests/test_export.py
    - pipeline/tests/test_leakage.py
    - web/public/data/**
decisions:
  - "Evidence fingerprint covers the in-season weights plus offseason.draft weight and display_only (insights.fingerprint_weights)"
  - "Peers group over every 1999-2021 team-week with a defined y8 (not only the eligible window); cases are the uncapped flags"
  - "Evidence percentages use Python round(100*x) as specified (banker's rounding at exact .5)"
metrics:
  duration: ~35 min
  completed: 2026-11-11
  tasks: 3
  files: 13 source/test + regenerated data
---

# Phase 8 Plan 01: Perception-gap and movers callouts (pipeline) Summary

Perception-gap callouts ("5-4, but you should feel worried") and weekly top-3 risers and fallers are now computed in a pure `fgs.insights` module. Each gap callout carries a base-rate line from a committed `callout_evidence.json`. That file comes from the dev-only `fgs evidence` command, which reads seasons 1999–2021 only. The export ships the callouts per week and refuses to run if the evidence file is stale.

## Evidence numbers (committed, fingerprint 57fdb0045b4e)

| Flavor | n | d_margin vs peers | next-8 win team / peers |
|--------|---|-------------------|-------------------------|
| hopeful (gap >= +8) | 594 | +3.58 | 54.9% / 44.8% |
| worried (gap <= -8) | 631 | -3.51 | 45.0% / 54.6% |

Neither sign flipped. n is larger than the prototype's (504/556) because the frozen Phase 6 weights give different score ranks. The effect sizes match the prototype.

Shipped copy example: "Teams with a gap this big won 55% of their next 8 games; teams with the same record won 45% (594 cases, 1999–2021)."

## Callout volume

- 1401 gap callouts over 362 eligible weeks (4..reg_weeks-1, 1999–2026): **3.87 per week**, never more than 3 per flavor.
- 3435 mover callouts in total.
- Latest week (2026 week 9) `callouts.json` has 10 items: 1 worried (CLE), 3 hopeful (SEA, LA, HOU), 3 mover_up, 3 mover_down.

## Tasks

| # | Task | Commits |
|---|------|---------|
| 1 | insights.py + constants + firewall | 45fe02e (RED), a12604e (GREEN) |
| 2 | evidence.py + `fgs evidence` + callout_evidence.json | cf61c33 (RED), e8c34d4 (GREEN) |
| 3 | Export callouts + staleness guard + regenerated data | 550d578 (RED), f5a0e83 (GREEN) |

## Verification

- `uv run pytest -q`: 544 passed. The real-data seal, the CLI and the callout-rate tests all ran; none were skipped.
- Acceptance one-liners pass: callouts.json matches meta.latest, snapshots/2008.json has callouts, and no backtest or evidence imports appear in export.py or insights.py.
- The holdout seal holds: changing every 2022+ result to 60-0 and reversing every 2022+ rank leaves compute_evidence unchanged.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Synthetic draft export test needed matching evidence**
- **Found during:** Task 3
- **Issue:** `_draft_export` in test_export.py builds an export with synthetic weights `{elo: 2.0, season_record: 1.0}`. The plan assumed every build_export caller uses weights.yaml, but this one doesn't, so its fingerprint can't match the committed evidence.
- **Fix:** Added a test helper `_matching_evidence(weights, cfg)` that re-fingerprints the committed evidence for those weights, and passed it as `evidence=`.
- **Files modified:** pipeline/tests/test_export.py
- **Commit:** 550d578

**2. [Rule 2 - Correctness] Fingerprint mapping helper**
- Added `insights.fingerprint_weights(weights, offseason_cfg)` so the CLI and the export hash exactly the same mapping: the in-season weights plus `offseason.draft` and `offseason.draft.display_only`, as the orchestrator asked.

**3. Test fixture rounding**
- One copy-test fixture value (0.465) landed on an exact .5 boundary with Python's banker's rounding. I changed the fixture to 0.4654 and kept the specified `round(100*x)`.

## Known Stubs

None.

## Self-Check: PASSED

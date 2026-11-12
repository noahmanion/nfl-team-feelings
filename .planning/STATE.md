---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Public Site
status: Awaiting next milestone
stopped_at: Milestone v2.0 completed and archived
last_updated: "2026-11-12T09:45:00Z"
last_activity: 2026-11-12 — Milestone v2.0 completed and archived (tag v2.0)
progress:
  total_phases: 6
  completed_phases: 6
  total_plans: 26
  completed_plans: 26
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-11-12)

**Core value:** A single, honest, momentum-weighted "feel-good score" per team that is backtested to predict future performance — so "you should feel better than you do" is actually true.
**Current focus:** Planning next milestone (`/gsd:new-milestone`)

## Current Position

Phase: Milestone v2.0 complete (phases archived to `.planning/milestones/v2.0-phases/`)
Plan: —
Status: Awaiting next milestone
Last activity: 2026-11-12 — Milestone v2.0 completed and archived

## Performance Metrics

- v1.0: 8 phases, 34 plans (shipped 2026-11-11)
- v2.0: 6 phases, 26 plans (shipped 2026-11-12). Per-plan timings are in `milestones/v2.0-phases/*/*-SUMMARY.md`

## Accumulated Context

### Decisions

Full log in the PROJECT.md Key Decisions table. These constraints carry forward and must not be broken:

- `pipeline/PREREGISTRATION_V2.md` stays at its single commit, 9c32319. Never edit it. Errata go only in `PREREGISTRATION_V2_DEVIATIONS.md`.
- `pipeline/inputs/win_totals_2021plus.csv` (2021–2025) stays at its single commit, a3135cb (sha256 338450a3…). Never edit it. 2026+ lines live in `win_totals_display_2026plus.csv` (display-only).
- The golden test (`pipeline/tests/test_golden_scores.py`) pins v1 scores and labels for seasons ≤2025. v1 weights are frozen forever.
- The v2 model freeze commit must land before 2027 Week 1. The holdout is games kicking off after the freeze commit, 2027 primary (2028 if the freeze misses Week 1). MODEL-V2-02 (free agency) is dropped.
- Production is https://nfl-team-feelings.vercel.app/ (Vercel project `nfl-team-feelings`, root `web`, Node 24.x). The ignored-build step only rebuilds on `web/` changes. Hobby plan, so non-commercial only.

### Pending Todos

None.

### Blockers/Concerns

None blocking. The human UAT below is still open.

## Deferred Items

Items acknowledged and deferred at milestone close on 2026-11-12:

| Category | Item | Status |
|----------|------|--------|
| uat_gap | 12-HUMAN-UAT.md: editorial look light/dark at 1280/375; history chart logo end mark | partial (2 pending) |
| uat_gap | 14-HUMAN-UAT.md: Slack/iMessage/X pastes, FB debugger (Scrape Again on root), LinkedIn inspector, share URL → hash route click, week-8 copy keeps hash link | pending (7) |
| verification_gap | 12-VERIFICATION.md | human_needed |
| verification_gap | 14-VERIFICATION.md | human_needed |
| Model | MODEL-V2-01/03 implementation (freeze before 2027 Week 1) | Future milestone |
| Share | Cards for historical callouts | Deferred |
| Logos | Era-specific historical logos | Deferred |
| UI polish | UI-REVIEW 12 #5/#6/#10/#11, 13 #6 (see v2.0-MILESTONE-AUDIT.md) | Deferred |

## Session Continuity

Last session: 2026-11-12
Stopped at: v2.0 milestone archived and tagged
Resume file: None

## Operator Next Steps

- Run the human UAT in `.planning/milestones/v2.0-phases/14-share-cards-launch-verification/14-HUMAN-UAT.md` and `12-HUMAN-UAT.md`
- `/gsd:new-milestone` for the v2 model build and freeze

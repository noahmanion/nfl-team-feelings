---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Public Site
status: ready_to_plan
stopped_at: Phase 11 complete (5/5) — ready to discuss Phase 12
last_updated: 2026-11-12T03:39:47.858Z
last_activity: 2026-11-12
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 8
  completed_plans: 8
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-11-11)

**Core value:** A single, honest, momentum-weighted "feel-good score" per team that is backtested to predict future performance — so "you should feel better than you do" is actually true.
**Current focus:** Phase 12 — redesign foundation & team identity

## Current Position

Phase: 12
Plan: Not started
Status: Ready to plan
Last activity: 2026-11-12

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**

- Total plans completed: 42 (v1.0)
- Average duration: -
- Total execution time: -

**By Phase (v2.0):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 9 | 1 | - | - |
| 10 | 2 | - | - |
| 11 | 5 | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 9 P01 | 4 min | 3 tasks | 1 files |
| Phase 10 P01 | 2 min | 3 tasks | 11 files |
| Phase 11 P02 | 20 min | 3 tasks | 9 files |
| Phase 11 P03 | 20min | 2 tasks | 6 files |
| Phase 11 P05 | 6 min | 2 tasks | 68 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v2.0 Roadmap]: Pre-registration (Phase 9) goes first because holdout erosion can't be undone; it is docs only.
- [v2.0 Roadmap]: Phases 9, 10, 11 are mutually independent. Phase 12 needs 11 (logos); 13 needs 11 + 12; 14 needs 10 + 12.
- [v2.0 Roadmap]: All pipeline data work is one phase (11) so `fgs evidence` reruns at most once; the INTEG-01 golden test lands first in that phase.
- [v2.0 Research]: Share cards via satori + @resvg/resvg-js at build time; static share pages at real paths with a JS redirect to the hash route; no router change, no server runtime.
- [v2.0 Research]: Logos stored in repo from ESPN (nflverse Wikipedia URLs return HTTP 400); current logo + era-correct names; color-chip fallback.
- [v2.0 Research]: Node pinned to 24.x on Vercel (the `>=22.12` range would resolve to Node 26).
- [v2.0 Research]: 2021+ win totals are display-only; `vegas_expectations` must never read past 2020.
- [Phase 9]: v2 prereg committed alone at 9c32319; never edited; errata only in PREREGISTRATION_V2_DEVIATIONS.md
- [Phase 9]: MODEL-V2-02 free agency DROPPED (no signing dates); re-entry only via a v3 prereg
- [Phase 10-01]: Site origin resolves SITE_ORIGIN, then https:// + VERCEL_PROJECT_PRODUCTION_URL, then https://nfl-team-feelings.vercel.app (never VERCEL_URL); Vite plugin order 'pre'
- [Phase 10-01]: SiteFooter always renders (incl. error page); data stamp only when ready; nflverse source folded into the disclaimer
- [Phase 11-02]: win_totals_2021plus.csv pinned: sha256 338450a3c70cc47b6ec4379dc6d72b0fe343a8a2737b2666e1535a8fc9995449, single commit a3135cb; never edit
- [Phase 11-02]: 2021+ win totals are display-only via build_export(win_totals=) -> teams/{F}.json vegas_win_totals; cli._cached_vegas raises past 2020
- [Phase 9]: v2 primary holdout = full 2027 if freeze lands before first 2027 REG kickoff, else full 2028
- [Phase 11]: 11-03: epa/{season}.json def_sr = opponent off_sr; conf/division are current alignment (not era-correct)
- [Phase 11]: 11-05: site data regenerated once from cache; golden pin 3ac3c2b5 unchanged before/after

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 9: free-agency input may be infeasible without leakage (`load_contracts` lacks signing dates) — pre-commit to dropping it if so.
- Phase 11 (from Phase 9 review): `pipeline/inputs/win_totals_2021plus.csv` must hold 2021–2025 only and be write-once (one commit); put 2026+ display-only lines in a separate file, or the v2 pre-registration's input pin (DEVIATIONS.md A3.4) breaks. See 09-REVIEW-FIX.md.
- Phase 11: 2004 Raiders R2 forfeit may be a trade; DEN 2001 R3 and BAL 2008 R5 may be missing. 2021+ win totals must be hand-entered (covers.com only loads in a browser). Any real forfeit correction means a deliberate `fgs evidence` rerun.
- Phase 14: confirm crawlers handle the JS-redirect share pages, the emoji strategy for satori, and whether `VERCEL_PROJECT_PRODUCTION_URL` is available at build time. Test on the production domain (preview deploys sit behind Vercel login).
- Vercel Hobby plan is non-commercial only (no ads or affiliate links).

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Model | MODEL-V2-01/02/03 implementation | Future milestone (eval ~Feb 2028) | v2.0 start |
| Share | Cards for historical callouts | Deferred | v2.0 start |
| Logos | Era-specific historical logos | Deferred | v2.0 start |

## Session Continuity

Last session: 2026-11-12T03:05:16.688Z
Stopped at: Completed 11-02-PLAN.md
Resume file: None

## Operator Next Steps

- `/gsd:plan-phase 9`

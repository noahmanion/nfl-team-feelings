# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v2.0 — Public Site

**Shipped:** 2026-11-12
**Phases:** 6 | **Plans:** 26

### What Was Built
- The v2 pre-registration and 2027 holdout, committed once before any v2 code
- A public Vercel deploy with an ignored-build step, a freshness stamp, site share tags and a disclaimer
- Pipeline guards: a golden v1 score test, a sourced forfeit audit, write-once 2021–2025 win totals, an EPA export and 32 local logos
- An editorial redesign (Inter and Plex Mono, a shared Plot theme, ChartFrame, logos with era-correct names)
- An Explore page (EPA and record-vs-evidence scatters) and win totals on the team page
- Build-time satori/resvg share cards and static share pages, with copy-link wired to them

### What Worked
- Landing the guard first (prereg in Phase 9, golden test at the start of Phase 11) made every later data change safe to make
- Putting all pipeline data work in one phase kept `fgs evidence` to a single rerun
- One slug module (`share.ts`, erasable TS) imported by both the app and the Node build, so share targets and copy URLs agree by construction
- Iterated code review and UI review with fix cycles caught real a11y and crawler issues (WR-01 in-app browsers, WR-04/05 copy-button names and live region)

### What Was Inefficient
- SUMMARY frontmatter was inconsistent (`requirements` vs `requirements-completed`, or missing), so the audit's 3-source cross-check needed manual work
- The v1 milestone close deleted phase dirs without archiving them, so v2 needed an explicit copy-verify-remove step
- The CLI's auto-extracted milestone accomplishments picked up deviation notes ("1. [Rule 3 - Blocking] …") and needed a manual rewrite
- Small UI-review items deferred in Phase 14 (copy feedback, mover alt text) were cheap enough to have fixed in-phase

### Patterns Established
- Write-once data files pinned by commit and sha256, with errata in separate files
- Display-only data paths are kept separate from score inputs, and guards prove no reads past the cutoff
- Share pages: static HTML at real paths, absolute og tags, and a crawler-UA-guarded JS redirect to hash routes

### Key Lessons
1. When a holdout or freeze is at stake, commit the contract first and make it a test.
2. Archive by copy, verify with `diff -r`, then remove. Never trust a "clear" step to archive.
3. Keep requirement IDs in a single, consistent SUMMARY frontmatter key so audits are automatic.

### Cost Observations
- Model mix: mostly opus orchestration, with sonnet for integration checking
- Notable: the whole milestone ran in about a day of wall time, with phases 9/10/11 independent

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Key Change |
|-----------|--------|------------|
| v1.0 | 8 | Backtest-first model, frozen weights, one-time holdout |
| v2.0 | 6 | Guards before changes; UI and code review fix cycles; public deploy |

### Cumulative Quality

| Milestone | Pipeline tests | Web tests |
|-----------|----------------|-----------|
| v1.0 | 584 | 149 |
| v2.0 | 642 | 367 |

### Top Lessons (Verified Across Milestones)

1. Pre-registration plus a single-commit guard keeps the evaluation honest. It worked for both the v1 holdout and the v2 setup.

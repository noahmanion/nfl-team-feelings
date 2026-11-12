---
phase: 09-v2-pre-registration
status: fixed_via_errata
fix_scope: critical+warning
iterations: 1 fix + 1 re-review
---

# Phase 9 — Review fix report

## Why not `gsd-code-review --fix`

The only reviewed source was `pipeline/PREREGISTRATION_V2.md`, a one-commit contract (its section 1.3 and 16.4). Running the fixer would add a second commit to it and void the v2 evaluation, so the auto-fixer was NOT run. Instead, per that file's section 1.3 ("Errata and allowed deviations are recorded only in `pipeline/PREREGISTRATION_V2_DEVIATIONS.md`"), closed pre-data errata were committed alone in `4da61a5` (Part A, A1–A10), the same day, with no v2 code and no v2 number in existence.

## Outcome (09-REVIEW-2.md re-review)

- Original 16 findings: 13 RESOLVED, 3 PARTIAL (CR-01, WR-03, WR-04), 0 OPEN.
- `PREREGISTRATION_V2.md` still has exactly 1 commit (`9c32319`); v1 `PREREGISTRATION.md` untouched.

## Residual items: binding implementation notes for the v2 model milestone

Part A is closed, so these are carried as constraints on whoever builds v2 (they follow from the conservative readings of the prereg + Part A; none relaxes either file):

1. **Phase 11 / DATA-02 (near-term):** `pipeline/inputs/win_totals_2021plus.csv` holds seasons 2021–2025 only and is write-once (single commit) once created; 2026+ display-only lines go in a separate file (e.g. `pipeline/inputs/win_totals_display_2026plus.csv`). Otherwise the A3.4 pin breaks and 2026 rows look like backfilled v2 inputs (re-review CR-02).
2. The primary-season line file (`win_totals_<season>.csv`) must have exactly one commit, before the freeze commit and before first REG kickoff; `holdout-v2` checks this (re-review CR-01).
3. "Any v2 module" in A1.2 is implemented as: any commit after the freeze touching `pipeline/src/fgs/**`, `pipeline/uv.lock`, `weights_v2.yaml` or `pipeline/inputs/**` (except A1.2's listed exceptions) voids — i.e. shared v1 code counts too (re-review WR-01).
4. Part A integrity: guards hash `PREREGISTRATION_V2_DEVIATIONS.md` at its adding commit and require the current file to start with exactly those bytes (append-only) (re-review WR-02).
5. Witness: only a server-side GitHub push event counts (signed tags are self-dated); a missing witness or a witness after the deadline = deadline missed for that season, and the same rule applies to 2028; the witness commit and a primary-season line-file push witness are both covered by A1.2's `FREEZE_V2_WITNESS.json` exception (one file, may hold both records) (re-review WR-03/04/05).
6. Line source: one named public source for all hand-entered rows of a season, chosen and recorded in the v2 milestone CONTEXT before any v2 code runs (re-review WR-06).
7. A3.7 "v1 `fingerprint`" = `fgs.holdout.input_fingerprints` (re-review info).

---
phase: 11-pipeline-data-guards
plan: 01
subsystem: pipeline
tags: [golden-test, draft, forfeits, evidence, integrity]
requires: []
provides:
  - "INTEG-01 golden frozen-score test (export + derive checks) with guarded re-pin"
  - "Audited, cited FORFEITS table + FORFEIT_KIND labels (DATA-01)"
  - "callout_evidence.json restamped with post-audit code_fingerprint"
affects: [pipeline/src/fgs/draft.py, pipeline/callout_evidence.json]
tech-stack:
  added: []
  patterns: ["sha256 golden pin over sorted (season, week, franchise, score, label) rows, overall + per season"]
key-files:
  created:
    - pipeline/tests/test_golden_scores.py
    - pipeline/tests/golden/v1_scores_le2025.json
  modified:
    - pipeline/src/fgs/draft.py
    - pipeline/tests/test_draft.py
    - pipeline/callout_evidence.json
decisions:
  - "Golden pin generated from HEAD 5c4951b data: 19,102 rows, overall sha256 3ac3c2b5...0539472; derive pin must equal export pin before any write"
  - "FORFEITS = 30 keys / 35 team-lines; 2017 R4 keyed NO; 8 forfeits added; UNATTRIBUTED_SHORT emptied"
  - "Five sourced-but-unplaceable forfeits (2000 R4 NE, 2001 R3 PIT, 2002 R3 DEN/SF, 2005 R3 DEN) documented in draft.py, not applied"
  - "fgs evidence run exactly once: code_fingerprint 6e1958f91b8a -> 07c33dd92639, base rates unchanged; fingerprinted code is frozen for the rest of Phase 11"
metrics:
  duration: "~15 min"
  completed: 2026-11-12
  tasks: 3
  files: 5
---

# Phase 11 Plan 01: Golden Frozen-Score Test + Draft Forfeit Audit Summary

This plan adds a golden test that pins the v1 score and label for all 19,102 team-weeks in seasons 1999-2025. It then applies the audited, cited draft-forfeit table, with a penalty or supplemental label on each team-line, and reruns `fgs evidence` once. The golden hash is the same before and after.

## Golden pin

- File: `pipeline/tests/golden/v1_scores_le2025.json`. It holds 27 per-season hashes (1999-2025), `rows` = 19102, and `generated_from` = `5c4951b`.
- Overall hash **before** (Task 1): `3ac3c2b58d0bfecf2ba7641160cac7a78110265d1c209e27764c2febf0539472`
- Overall hash **after** Tasks 2-3: unchanged. The pin file has exactly one commit (c0b01ff). Both the export check and the derive check pass in the full suite after the evidence rerun.
- Re-pinning needs `FGS_GOLDEN_REGEN=1`. Without it the script exits non-zero and writes nothing (checked). It also refuses to write unless the derive pin equals the export pin.

## Forfeit audit (DATA-01)

| Outcome | Count | Items |
|---|---|---|
| Confirmed (unchanged) | 26 | every existing team-line except 2017 R4 |
| Relabeled | 1 (counted in confirmed) | 2004 R2 LV: supplemental (OAK pick traded to HOU, used on T. Hollings) |
| Corrected | 1 | 2017 R4 NE -> NO (Deflategate took the NO-original pick NE held) |
| Added | 8 | 2003 R6 HOU (supp), 2008 R5 BAL (supp), 2011 R7 DAL (supp), 2012 R6 DET, 2017 R5 SEA, 2021 R7 MIN (replaces UNATTRIBUTED_SHORT), 2022 R6 NO, 2023 R5 HOU |
| Sourced but not applied | 5 | see below |
| Rejected (not forfeits) | 3 | 2001 R3 DEN (used own pick #87), 2021 R6 LV and 2021 R7 NO (rescinded) |

Totals: 30 keys and 35 team-lines. `FORFEIT_KIND` has exactly 35 keys. `UNATTRIBUTED_SHORT == set()`. Every team-line carries the `short_reason` and citation URLs from `sources/forfeit_audit.json`. The citations were inserted by a script straight from that JSON, so none were typed by hand.

**Not applied:** these are real and sourced, but the derived pick order has no slot gap for them. Applying one would reclassify a real regular pick as a comp pick and charge an uninvolved team 3.9-7.1 points.
- 2000 R4 NE (supplemental, J'Juan Cherry)
- 2001 R3 PIT (penalty, Wolford cap violation)
- 2002 R3 DEN (penalty, deferred compensation)
- 2002 R3 SF (penalty, cap violations)
- 2005 R3 DEN (penalty, 1996-98 cap circumvention)

Test updates: the 2008 R5 test now expects `["BAL", "SF"]` gone with 30 regular picks. The 2017 R4 test is renamed to `..._no_...` and now expects `["NO"]`. New table tests cover the key-set match, the audited values, and confirm the unplaceable keys are absent. The existing `test_no_unknown_short_rounds_real` test stays green, so real data raises no warnings.

## Evidence rerun

`uv run fgs evidence` ran once. code_fingerprint went `6e1958f91b8a` -> `07c33dd92639`. The diff touches only `code_fingerprint` and `generated_at`. The base rates are unchanged: hopeful n=594 (54.9% vs 44.8%), worried n=631 (45.0% vs 54.6%). No other tracked file changed. `fgs export` was not run, as the plan says (Plan 05 regenerates the site data).

## Verification

- `uv run pytest -q`: **589 passed** (golden and test_export real-data tests included, no stale-evidence error)
- `git log --oneline -3`: golden, then forfeit, then evidence, in that order

## Commits

- c0b01ff test(11-01): pin frozen v1 scores and labels for seasons <= 2025 (INTEG-01)
- 22b36af fix(11-01): audit draft forfeits with citations, label supplemental vs penalty (DATA-01)
- 54485a7 chore(11-01): rerun fgs evidence after forfeit audit (new code fingerprint)

## Deviations from Plan

None. The plan was executed as written. The 2008 R5 test also asserts `"BAL" not in owners`, as the plan specified. The behavior bullet "surplus_table on real data raises no warnings" was already covered by the existing `test_no_unknown_short_rounds_real`, so no duplicate test was added.

## TDD Gate Compliance

Task 1 is test-only: it pins existing behavior, so the test passes on purpose. In Task 2 the table tests were written alongside the table edit in one `fix` commit. That matches the plan's single commit per task, rather than separate RED/GREEN commits.

## Self-Check: PASSED

- FOUND: pipeline/tests/test_golden_scores.py, pipeline/tests/golden/v1_scores_le2025.json
- FOUND commits: c0b01ff, 22b36af, 54485a7

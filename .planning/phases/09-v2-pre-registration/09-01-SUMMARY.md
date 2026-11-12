---
phase: 09-v2-pre-registration
plan: 01
subsystem: integrity
tags: [preregistration, holdout, v2-model, docs-only]
requires: []
provides:
  - "pipeline/PREREGISTRATION_V2.md: v2 contract (single commit 9c3231928488fbcec299abcc7bddb2470653d964, never edited)"
affects: [future v2 model milestone, fgs freeze-v2, fgs holdout-v2, Phase 11 win_totals_2021plus.csv]
tech-stack:
  added: []
  patterns: ["contract file committed alone once; errata only in an append-only DEVIATIONS file"]
key-files:
  created: [pipeline/PREREGISTRATION_V2.md]
  modified: []
decisions:
  - "v2 prereg committed 9c32319 (sha256 0b1d16ef18b9d496a19fedacde9bba401827be34d755b2dde101d25919f848cb); never edited again"
  - "MODEL-V2-02 free agency DROPPED in the contract (no signing dates in load_contracts); re-entry only via a v3 prereg"
  - "Frozen v1 comparator = in-season weights: block of weights.yaml as frozen at 41e1e54 (blob sha256 44b4c7b9...6320); later offseason: appendix is ignored by load_weights"
  - "Drop rules: leave-one-input-out, pooled walk-forward dSpearman N=8 > 0 over 23 folds (2003-2025), fold sign matches final fit in >= 14 of 23"
metrics:
  duration: "4 min"
  completed: 2026-11-12
  tasks: 3
  files: 1
---

# Phase 9 Plan 01: v2 Pre-registration Summary

`pipeline/PREREGISTRATION_V2.md` is committed alone in one commit, before any v2 code exists. In 21 numbered sections it fixes: MODEL-V2-01 good_loss_luck (raw `net_epa` and a logit_fit (a, b) fit once and frozen), MODEL-V2-02 free agency (DROPPED, with probe evidence), MODEL-V2-03 vs_exp_v2 (a Vegas-normalized replacement for vs_exp), the <= 2025 dev ceiling, the kickoff-time holdout (2027 primary, 2028 fallback), the comparators, the metrics, the bootstrap (B=2000, seed 20271), the drop rules, three verdict sentences, the void conditions and the guard specs.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Baseline checks, draft prereg, pre-commit self-check | (no commit; the draft was folded into Task 2 by design) | pipeline/PREREGISTRATION_V2.md (uncommitted draft) |
| 2 | Commit prereg alone | 9c3231928488fbcec299abcc7bddb2470653d964 | pipeline/PREREGISTRATION_V2.md |
| 3 | Post-commit read-only checks 1–8 | (read-only, no commit) | none |

## Check outputs

Baseline (before writing): `git log ... PREREGISTRATION.md | wc -l` printed `1`; shasum printed `f59ff7d6601f2e21986aaa8b6b399df30b34e95631c2098998fabacba5b36205`; git_state printed `1 True True`; the v2-name `git grep` at HEAD printed nothing.

Pre-commit self-check: the coverage loop printed 0 MISSING; the verdict-line count was `3`; all three verdict sentences were found with `grep -F`; the TBD/TODO/placeholder count was `0`; `fgs.backtest.TARGET_TEXT in file` was `True`; `git status --porcelain -- pipeline web` printed only `?? pipeline/PREREGISTRATION_V2.md`; v1 prereg `clean`. Every cited name was confirmed in code: backtest.py (8 grep lines), pbp.py (`scrimmage`, `team_game_epa`, `WP_LO`, `KNOWN_NO_PBP`, `net_epa`), features.py (`LUCK_N`, `_vs_exp`, as-of docstring), expectation.py (`vegas_expectations`, `RAW_TO_FRANCHISE`), bootstrap.py (all four functions, B_DEFAULT/SEED/LEVEL), holdout.py (`git_state`), games.py (`outcome`).

Post-commit (C = 9c3231928488fbcec299abcc7bddb2470653d964):

| # | Check | Output | Result |
|---|-------|--------|--------|
| 1 | v1 prereg commit count | `1` | PASS |
| 2 | v1 prereg sha256 / diff | `f59ff7d6601f2e21986aaa8b6b399df30b34e95631c2098998fabacba5b36205`, `clean` | PASS |
| 2b | `git_state('.')` | `1 True True` | PASS |
| 3 | v2 prereg commit count / files in C | `1` / `pipeline/PREREGISTRATION_V2.md` | PASS |
| 4 | v2-name git grep at C in src/tests/weights/web | (empty) | PASS |
| 5 | `git diff --name-only 515cfb3 HEAD -- pipeline web` minus prereg | (empty) | PASS |
| 6 | content-coverage loop on the committed file | no MISSING lines | PASS |
| 7 | verdict bullet count | `3` | PASS |
| 8 | `uv run pytest -q` | `584 passed in 146.15s (0:02:26)` | PASS |

Committed prereg sha256: `0b1d16ef18b9d496a19fedacde9bba401827be34d755b2dde101d25919f848cb`.

## Deviations from Plan

**1. [Rule 1 - Accuracy] Frozen v1 comparator pinned to the in-season weights block at 41e1e54**
- **Found during:** Task 1 baseline
- **Issue:** The working `pipeline/weights.yaml` now hashes to `1d61d3dc...7789`, not `44b4c7b9...6320`. Phase 7 commits (760da35, 5b21e20, 5297a9a) appended an `offseason:` draft section (weight 0, display only) that `load_weights` ignores. A bare citation of "weights.yaml sha256 44b4c7b9…6320" would not match the current file.
- **Fix:** §11 of the prereg cites the in-season `weights:` block as frozen at commit 41e1e54 (blob sha256 44b4c7b9115ca620dbe5ffb588792aecf51c05ca2b86cc440845a6b40cf76320). It states that later commits only appended the ignored `offseason:` section. This matches HOLDOUT_RESULT.md, which records the same blob and commit.
- **Commit:** 9c32319 (part of the prereg itself)

The rest of the plan was executed as written. Task 1 has no separate commit because the plan requires the draft to land only in the single Task 2 commit.

## Known Stubs

None. The file is a docs-only contract.

## Self-Check: PASSED

- FOUND: pipeline/PREREGISTRATION_V2.md
- FOUND: commit 9c3231928488fbcec299abcc7bddb2470653d964 (the only commit touching the file)

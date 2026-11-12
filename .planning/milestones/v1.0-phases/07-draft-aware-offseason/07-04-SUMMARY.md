---
phase: 07-draft-aware-offseason
plan: 04
subsystem: pipeline + site data
tags: [draft, offseason, export, explain, methodology, model-16, data-06]
requires:
  - "07-01: fgs.draft (equiv_pick, pick_noun, value_table), derived['draft'], derived['draft_values']"
  - "07-02: web contract (Row.draft DraftInfo, meta.offseason), dashed offseason connectors"
  - "07-03: score.load_offseason / apply_offseason / OFFSEASON_FACTORS, derived['offseason'], weights.yaml offseason.draft (weight 0)"
provides:
  - "mood.score_frame: score/rank deltas over the franchise's whole history (week 0 vs end of last season)"
  - "export: Row.draft on week-0 rows, per-season draft rank, week_labels['0'] = 'Preseason (after draft)', meta.offseason, draft factor/points only when weight != 0"
  - "explain.draft_text, PRESEASON_DRAFT_PLUS / _MINUS leads (blurb draft_threshold kwarg)"
  - "methodology: 'draft' honest note (training-only evidence); draft factor only when weight != 0"
  - "Regenerated web/public/data; README offseason + draft section"
affects: [web]
tech-stack:
  added: []
  patterns:
    - "Deltas: shift(1).over('franchise_id') across seasons; hysteresis still per team-season"
    - "Offseason term joins factor_keys only when live, so points still sum to score - baseline"
key-files:
  created:
    - .planning/phases/07-draft-aware-offseason/07-04-SUMMARY.md
  modified:
    - pipeline/src/fgs/mood.py
    - pipeline/src/fgs/export.py
    - pipeline/src/fgs/explain.py
    - pipeline/src/fgs/methodology.py
    - pipeline/src/fgs/draft.py
    - pipeline/tests/test_mood.py
    - pipeline/tests/test_export.py
    - pipeline/tests/test_explain.py
    - pipeline/tests/test_methodology.py
    - pipeline/tests/test_leakage.py
    - web/public/data/**
    - README.md
    - .planning/REQUIREMENTS.md
decisions:
  - "The methodology note stores fold sign as numeric fold_sign_k / fold_sign_of (the web Note.values type is Record<string, number>). The text still shows '8/19' as recorded."
  - "The draft preseason lead threshold is values[64] of the stuart chart. On real data 289 week-0 rows get a draft lead (141 plus, 148 minus)."
  - "meta.offseason.draft.decay comes from cfg['decay'] ([1, 0.75, 0.5, 0.25]), not a hard-coded literal"
metrics:
  duration: ~35min
  completed: 2026-11-11
  tasks: 3
  files: 13
---

# Phase 7 Plan 04: Ship the Draft-Aware Offseason Summary

The week-0 board now shows how each team moved since the end of last season. Every week-0 row from 2000 on carries a plain-English line on draft capital over the team's original slots ("doesn't move the score", because the weight is 0). The preseason blurb mentions extra or lost draft capital when it is at least the chart value of pick 64. The methodology page and README report honestly that the draft term failed its training-only gate.

## What was built

- **mood.py:** `score_delta` and `rank_delta` now use `shift(1).over("franchise_id")`, so week 0 compares with the franchise's last snapshot of the prior season. They are null only for 1999 and for HOU 2002. Hysteresis is still per team-season.
- **export.py:**
  - `_draft_ranks` ranks week-0 surplus per season (highest first, ties by franchise).
  - `_draft_info` builds `Row.draft = {surplus (1 dp), z (2 dp), equiv_pick, rank, text, moves_score}` on week-0 rows only.
  - `_row` takes a `draft_ctx` and passes `draft_threshold` (= values[64]) to `blurb`.
  - `_season_meta` labels week 0 "Preseason (after draft)". `meta.offseason.draft` = {weight, display_only, chart, decay}.
  - When weight ≠ 0 and `contrib_draft` exists, "draft" joins factor_keys (contribs and points) and `meta.factors`. `_export_weights` ignores `contrib_draft`.
- **explain.py:**
  - `draft_text(surplus, values, moves_score)` follows the spec exactly, including the U+2212 minus.
  - The week-0 "carry" lead becomes "…form plus extra draft capital: " or "…form minus some draft capital: " when |surplus| ≥ the threshold. Every other string is byte-identical.
- **methodology.py:**
  - `_draft_note` is templated from `weights.yaml offseason.draft`.
  - At weight ≠ 0 the draft also appears as a methodology factor (label and description from `OFFSEASON_FACTORS`).

## Generated data (live export, 2026 week 9)

- `meta.offseason` = `{"draft": {"weight": 0.0, "display_only": true, "chart": "stuart", "decay": [1.0, 0.75, 0.5, 0.25]}}`. `meta.factors` = the 11 frozen factors, with no draft entry.
- **CIN 2020 week 0:** `{"surplus": 0.0, "z": 0.12, "equiv_pick": 225, "rank": 13, "text": "Draft haul: right at their original slots — doesn't move the score.", "moves_score": false}`. This matches the team that kept its own #1 pick.
- **2026 top:**
  - MIA +23.5: "Draft haul: +24 over their original slots (about one extra early first-round pick) — doesn't move the score."
  - NYJ +20.7
- **2026 bottom:**
  - ATL −25.7: "Draft haul: −26 under their original slots (about one top-5 pick given up) — doesn't move the score."
  - CIN −23.4
- Every 2026 week-0 row has a draft dict and a non-null score_delta. All 1999 week-0 rows have draft null.
- Example week-0 blurbs:
  - 2026 CLE: "Preseason, carrying last season's form plus extra draft capital: the Browns are one of the worst teams in football, and have been losing by wide margins."
  - 2026 NYJ: "Preseason, carrying last season's form plus extra draft capital: the Jets are one of the worst teams in football, and have been getting blown out."
- `methodology.json` note "draft": "Draft capital over original slots was tested as an offseason term on top of the frozen score. The fitted weight was −0.28, 8/19 walk-forward folds agreed with its sign, and the week-0 change in Spearman was +0.0002, so it didn’t pass the gate and the draft doesn’t move the score (it’s shown as text only). This evidence is training-only walk-forward (2003–2021); the 2022–2025 holdout was already used to judge the in-season score."

## Verification

- `uv run pytest -q`: 483 passed.
- `uv run fgs check`: all checks passed, including draft_coverage and draft_sum.
- `uv run fgs export`: 93 files written.
- The plan's JSON one-liner checks pass: offseason present, every week-0 label correct, CIN 2020 surplus 0.0, 1999 draft null, methodology "draft" note present.
- Web: vitest 90 passed, svelte-check 0 errors, `npm run build` ok.
- `types.ts` DraftInfo fields match the exported keys exactly (the test asserts `DRAFT_KEYS`).
- The fake-weight synthetic test (weight 1.0) passes:
  - draft is in contribs and meta.factors
  - contrib_draft = z·(1 − week/4) on weeks 0–3 and 0.0 from week 4
  - points sum to score − baseline on every row
  - the plus lead appears at |surplus| ≥ values[64]
- Leakage: `_assert_draft_unchanged` compares draft_surplus and draft_z (null-aware) plus the week-0 score_delta and rank_delta. All leakage tests pass.
- `! grep -rn "great draft\|drafted well" src/fgs/` is clean.
- No frozen weights, HOLDOUT, PREREGISTRATION or FREEZE file was touched.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] explain.draft_text and the blurb threshold hook were committed with Task 1**
- **Found during:** Task 1
- **Issue:** export `_row` calls `explain.draft_text` and `blurb(..., draft_threshold=)`. Committing Task 1 without them would leave a broken intermediate commit.
- **Fix:** The explain.py source changes went into the Task 1 commit. Task 2's commit holds their tests plus the methodology note.
- **Commits:** e163737, 339d994

**2. [Rule 1 - Contract] Methodology note fold sign stored as numbers**
- **Issue:** The plan says values hold fold_sign "7/19", but the web `Note.values` type is `Record<string, number>`.
- **Fix:** Store `fold_sign_k` and `fold_sign_of`. The text shows "k/n" as recorded. Tests assert that the values equal the weights.yaml numbers.
- **Commit:** 339d994

**3. [Rule 3 - Blocking] Draft-quality phrase in comments tripped the grep gate**
- **Issue:** The verify step `! grep -rn "great draft\|drafted well" src/fgs/` matched a 07-01 docstring in draft.py (and the new explain comment).
- **Fix:** Both comments were reworded to "not a verdict on draft quality". There is no behaviour change.
- **Commit:** 339d994

## Known Stubs

None.

## Self-Check: PASSED

- Files exist: export.py, explain.py, methodology.py, mood.py, web/public/data/meta.json, README.md.
- Commits found: e163737, 339d994, 70cfde2, 9937fe0.

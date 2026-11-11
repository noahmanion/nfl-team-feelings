---
phase: 07-draft-aware-offseason
fixed_at: 2026-11-11T00:00:00Z
review_path: .planning/phases/07-draft-aware-offseason/07-REVIEW.md
iteration: 1
findings_in_scope: 12
fixed: 11
skipped: 1
status: partial
---

# Phase 7: Code Review Fix Report

**Fixed at:** 2026-11-11
**Source review:** .planning/phases/07-draft-aware-offseason/07-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 12 (all critical and warning findings, plus Info IN-02..IN-07; IN-01 was in scope but skipped as non-trivial)
- Fixed: 11
- Skipped: 1 (IN-01)

**Gate outcome (training-only, re-run twice):** still **fails**. Weight stays 0.00 and the draft is display only. The nonzero path does not ship.

| Run | Fitted | Fold sign | wk0 ΔSpearman | weeks 0-3 Δ | wk0 seasons Δ>0 |
| --- | ------ | --------- | ------------- | ----------- | --------------- |
| Original (before fixes) | -0.2828 | 8/19 | +0.0002 | +0.0003 | 6/19 |
| After CR-01 (alignment) | -0.2826 | 8/19 | +0.0003 | +0.0004 | 5/19 |
| After WR-02 (per-fold caps) | -0.2826 | 8/19 | +0.0003 | +0.0003 | 4/19 |

Winsor caps are unchanged at [-17.29, 16.19]. Only the `offseason.draft` block of weights.yaml (fitted, delta_wk0, verdict comment) and the BACKTEST_LOG "Offseason terms" table changed. The frozen `weights:`/`fit:` sections and HOLDOUT_RESULT.*, PREREGISTRATION.md and FREEZE_RESULT.json are untouched (verified by diff against 7ae0031). No 2022–2025 evaluation was run.

## Fixed Issues

### CR-01: Alignment DP invents forfeits in heavily traded rounds

**Files modified:** `pipeline/src/fgs/draft.py`, `pipeline/tests/test_draft.py`, `pipeline/weights.yaml`, `pipeline/BACKTEST_LOG.md`
**Commit:** 5b21e20
**Status:** fixed: requires human verification (logic change plus a hand-curated forfeit table)
**Applied fix:**
- Forfeits now come only from `draft.FORFEITS`, which covers every round. It holds the 6 original round 1-2 entries plus 18 new ones: supplemental-draft forfeits and penalty forfeits such as 2008 R5 SF, 2016 R5 ATL+LA, 2017 R4 NE, 2021 R3 NE and 2025 R5 ATL+SF. I cross-checked each new entry against the pick data (a short round or a slot shift).
- The DP's deletion cost now defaults to more than every substitution in the round, as the review's cost model suggests. Trades always win over a guessed forfeit.
- I kept the DP instead of pure positional pairing. Pure positional pairing broke 2002 R2, which has a mid-round extra pick (63 DAL), and would have pushed NE's own pick 65 into the comp tail. The DP handles that with an insertion.
- A forced deletion (a round with fewer picks than slots) charges nobody. It warns unless the round is listed in `UNATTRIBUTED_SHORT`, which holds only (2021, 7): one slot is missing and the data can't pin the owner.
- New tests: 2008 R5 (SF forfeited; KC and LV each own a regular pick), 2016 R5 (ATL and LA forfeited, pick 157 not owned by ATL), 2017 R4 (NE forfeited, BUF and MIA keep their picks, CIN's 138 is regular), no unknown short rounds in the real data, and synthetic trade-vs-forfeit and short-round tests.
- The slot-1-untraded = 0 invariant (CIN 2020 = 0.0) and the sum ≤ 0 checks still pass.
- Effect on surplus: 6 team-drafts move by more than 1 point (max 5.6: DET 2016, LAC 2007). Each one is a real forfeit that is now in the table.

### CR-02: Draft text ships "+0 over" / "−0 under"

**Files modified:** `pipeline/src/fgs/draft.py`, `pipeline/src/fgs/explain.py`, `pipeline/tests/test_explain.py`, `pipeline/tests/test_export.py`
**Commit:** 788e2b2
**Applied fix:** Added `draft.round_half_away` (0.5 -> 1, 2.5 -> 3) and `draft.is_even` (|s| < 0.5), using a shared `EVEN` threshold. Text below the threshold reads "Draft haul: about even with their original slots". A test covers ±0.5, ±0.49 and ±2.5. The shipped data now has no "+0"/"−0" strings.

### CR-03: Preseason blurb implies the score carries draft capital at weight 0

**Files modified:** `pipeline/src/fgs/export.py`, `pipeline/src/fgs/explain.py`, `pipeline/tests/test_export.py`
**Commit:** 792046c
**Applied fix:** The export passes `threshold` only when the draft term is live. At weight 0 the lead stays "Preseason, carrying last season's form:", and the draft appears only in its own "doesn't move the score" line. New test: a display-only export with a +50 haul has no "draft" in any week-0 blurb. The shipped data has 0 draft-capital leads, down from 289.

### WR-01: display_only and weight never cross-validated

**Files modified:** `pipeline/src/fgs/score.py`, `pipeline/src/fgs/export.py`, `pipeline/src/fgs/methodology.py`, `pipeline/src/fgs/backtest.py`, tests (score, methodology, backtest, export)
**Commit:** 0776c30
**Applied fix:**
- Added `score.offseason_live(cfg)` as the single source of truth (weight != 0). It raises ValueError unless display_only is true exactly when the weight is 0.
- `load_offseason` validates with it. `apply_offseason`, the export (draft factor and moves_score) and the methodology note and factor list all use it.
- `draft_gate` fails a fit that rounds to 0.00.

### WR-02: Walk-forward winsor bounds look ahead

**Files modified:** `pipeline/src/fgs/backtest.py`, `pipeline/tests/test_backtest.py`, `pipeline/weights.yaml` (offseason comment only), `pipeline/BACKTEST_LOG.md`
**Commit:** 5297a9a
**Applied fix:**
- `_draft_fit(..., surplus=...)` re-derives draft_z per fold S, with caps from drafts [2000, S-1] only (`_fold_x`). `draft_walk_forward` uses this unless fixed caps are passed in.
- The final fit still uses the all-training caps that ship.
- The report and log row say "per-fold winsor caps".
- A spy test checks every fold's caps use only earlier drafts, and that a 2021 outlier never sets a cap.

### IN-02: Pick-equivalent saturates at "#1 overall pick"

**Files modified:** `pipeline/src/fgs/draft.py`, `pipeline/src/fgs/explain.py`, `pipeline/tests/test_explain.py`
**Commit:** a68493c
**Applied fix:** When |s| > 1.1 × the #1 pick's value, the text reads "(more than a #1 overall pick)" or "(more than a #1 overall pick given up)". Hauls within 10% of the #1 value, such as CLE 2018 at +37.9, still read "about one extra #1 overall pick".

### IN-03: equiv_pick meaningless for zero surplus

**Files modified:** `pipeline/src/fgs/export.py`, `pipeline/tests/test_export.py`, `web/src/lib/types.ts`
**Commit:** 5839207
**Applied fix:** `equiv_pick` is null when the text says "about even". The web type is now `number | null`; nothing in the web reads the field.

### IN-04: changeText says "preseason" for any null delta

**Files modified:** `web/src/lib/format.ts`, `web/src/lib/format.test.ts`, `web/src/components/BoardHeading.svelte`, `web/src/App.svelte`
**Commit:** e2306d6
**Applied fix:**
- A null delta reads "No change, preseason." only at week 0. Otherwise it reads "No change from last week."
- BoardHeading takes a new `firstSeason` prop. In the first season of the data, the week-0 note reads "the first season in the data, so everyone starts even" instead of "Change is vs the end of last season".

### IN-05: `fgs draft` recomputes winsor bounds

**Files modified:** `pipeline/src/fgs/cli.py`
**Commit:** 1203053
**Applied fix:** `fgs draft` uses `cli.draft_winsor` (the frozen caps), so its z matches the exported draft_z. Its pick-equivalent column uses the same `is_even` / `beyond_top_pick` thresholds as the site text.

### IN-06: Missing winsor silently drops draft display data

**Files modified:** `pipeline/src/fgs/cli.py`, `pipeline/tests/test_cli.py`
**Commit:** 153ee5d
**Applied fix:** `cli.draft_winsor` returns the frozen caps. If they are missing, it recomputes caps from 2000-2021 and prints a stderr warning. `derive_games` always computes draft_z when a draft frame exists.

### IN-07: Methodology hard-codes "2003–2021"; `_fold_pair` raises

**Files modified:** `pipeline/src/fgs/methodology.py`, `pipeline/src/fgs/backtest.py`, `pipeline/tests/test_methodology.py`, `pipeline/tests/test_backtest.py`
**Commit:** 36d7c5b
**Applied fix:**
- The walk-forward range in the note comes from `test_seasons`, falling back to `season_config`. The holdout range comes from `HOLDOUT_SEASONS`.
- `_fold_pair` and `_season_range` return None on malformed input.
- `format_draft_report` returns a short message instead of raising IndexError when no folds were produced.

### Regenerated data

**Commit:** 8887d75. This is `fgs export` output (`web/public/data`, 29 files) after all of the fixes above.

## Skipped Issues

### IN-01: Exact SOS ties broken alphabetically by franchise_id

**File:** `pipeline/src/fgs/draft.py:157`
**Reason:** Skipped as instructed, because it isn't trivial. A correct fix needs either round-1 order taken from the actual draft (which interacts with trade detection) or a hand-built tiebreak override table for about 30 swaps. Each swap moves surplus by only about 0.1–0.5.
**Original issue:** Exact (grp, wp, sos) ties are ordered alphabetically, not by the real division/conference tiebreakers or coin flip. This creates small spurious surplus with an alphabetical bias.

## Verification

- `cd pipeline && uv run pytest -q`: 504 passed
- `uv run fgs check`: all checks passed (including draft_coverage and draft_sum)
- `uv run fgs export`: 93 files; the regenerated data is committed
- `cd web && npm run test` (91 passed), `npm run check` (0 errors), `npm run build` (ok)

---

_Fixed: 2026-11-11_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

---
phase: 07-draft-aware-offseason
reviewed: 2026-11-11T00:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - pipeline/src/fgs/draft.py
  - pipeline/src/fgs/checks.py
  - pipeline/src/fgs/cli.py
  - pipeline/src/fgs/backtest.py
  - pipeline/src/fgs/score.py
  - pipeline/src/fgs/mood.py
  - pipeline/src/fgs/explain.py
  - pipeline/src/fgs/export.py
  - pipeline/src/fgs/methodology.py
  - web/src/lib/format.ts
  - web/src/lib/history.ts
  - web/src/lib/types.ts
  - web/src/components/BoardHeading.svelte
  - web/src/components/BoardRow.svelte
  - web/src/components/HistoryChart.svelte
  - web/src/components/HistoryPage.svelte
  - web/src/components/TeamPage.svelte
findings:
  critical: 3
  warning: 2
  info: 7
  total: 12
status: issues_found
---

# Phase 7: Code Review Report

**Reviewed:** 2026-11-11
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Scope: the 07-01 to 07-04 changes to `pipeline/src` and `web/src` (commits b9817d0 to 339d994). The `fix(06)` commits in the same range were not reviewed. Test files were read only to check what they cover.

I checked the claims below directly, using the real cache (scratch probes, nothing written into the repo):
- **Anti-tanking holds.** A team that keeps its own picks gets exactly 0 (CIN 2020).
- **Draft sums never go above 0** (17 drafts are below 0 because of forfeits).
- **The surplus, winsor and z math is correct.**
- **The walk-forward is sealed at season 2021 or earlier.**
- **The frozen `weights:` block is untouched.** weights.yaml only gained lines (+25 / −0), and nothing changed in HOLDOUT_RESULT, PREREGISTRATION or FREEZE_RESULT.
- **The gate logic matches the locked spec.** It requires the final weight to be above 0, at least 60% of folds to share the final weight's sign, and wk0 Δ above 0.
- **Week-0 deltas are correctly null** only for 1999 rows and for HOU 2002.

The main problems are:
- The alignment DP sometimes invents forfeits in later rounds where many picks were traded, and charges them to the wrong teams.
- Two wording bugs already ship in `web/public/data`: "+0 over" / "−0 under", and a preseason lead that says the score "carries" draft capital while the draft weight is 0.

## Critical Issues

### CR-01: Alignment DP invents forfeits in heavily traded rounds 3–7, charging the wrong teams and dropping real regular picks into the free "comp" tail

**File:** `pipeline/src/fgs/draft.py:183-221` (align), `:263-272` (surplus_table)
**Issue:** In rounds 3–7, extra picks at the end of a round cost nothing (`free_tail`). A deletion costs 3, while each substitution costs 1. So when a round has many trades, the DP finds it cheaper to delete one or two slots mid-round. That shifts the rest of the alignment so traded picks "match" a neighbouring slot, and the last one or two real regular picks fall into the free tail.

Each spurious deletion charges a slot owner for a forfeit that never happened (`orig_v[o[si]] += _v(values, last_pick + 1)`). The regular picks pushed into the tail are excluded from `used_v`. Real-data examples:
- **2008 R5:** 32 slots and 31 picks. The real forfeit was SF (tampering). The DP deletes **KC and LV** instead (cost 26 vs 28 for the straight alignment).
- **2016 R5:** the DP deletes LV and WAS. ATL's real 2016 R5 forfeit is instead aligned as a trade, so TEN is credited with pick 157.
- **2017 R4:** the DP deletes BUF and MIA. CIN's pick 138 and KC's pick 139 are treated as comp picks.

I re-ran with the deletion cost set to 50. 16 team-drafts change by more than 1 point and 7 by more than 3, up to 5.6 points (CIN 2010 0.0 vs +5.6; BUF 2019, NE 2021, JAX 2024). That error is large next to the ±17 winsor bounds, and it reaches the exported `surplus`, `rank` and text. `check_draft_sum` is one-sided (sum ≤ 0), so it cannot catch value lost this way.
**Fix:** Stop letting the DP guess forfeits. Extend the forfeit table to every round (`FORFEITS: dict[(year, round), list[str]]`, covering supplemental-draft and tampering forfeits). Then take the regular picks positionally:
```python
gone = forfeits.get((y, r), [])
o = [t for t in order[r - 1] if t not in gone]
regular = list(zip(pk, act))[:len(o)]          # comp picks are always after the regular slots
for (p, user), owner in zip(regular, o):
    v = _v(values, p); orig_v[owner] += v; used_v[user] = used_v.get(user, 0.0) + v
```
Add a check that warns when `len(act) < len(o)` (an unknown forfeit), instead of letting the DP pick a victim. If you keep the DP, at least make `dele` larger than the total substitutions it could save (for example `dele = len(o)`). Then the DP only deletes when the round is actually short.

### CR-02: The draft text ships "+0 over" / "−0 under their original slots"

**File:** `pipeline/src/fgs/explain.py:247-252`
**Issue:** The check `abs(s) < 0.5` runs on the raw value, but the number comes from `round(s)`, which uses banker's rounding: `round(0.5) == 0` and `round(2.5) == 2`. Eight team-drafts have |surplus| of exactly 0.5 (e.g. 2020 CAR +0.5, 2025 TB −0.5, 2000 PHI −0.5). They render as "Draft haul: +0 over their original slots (about one extra later-round pick)". This is confirmed in the shipped `web/public/data/snapshots/2000.json`, `2020.json` and `2025.json`. The 85 half-integer surpluses are also rounded inconsistently with the 1-dp `surplus` field.
**Fix:**
```python
n = int(abs(s) + 0.5)          # round half away from zero
if n == 0:
    return f"Draft haul: right at their original slots{tail}"
if s > 0:
    return f"Draft haul: +{n} over their original slots (about one extra {noun}){tail}"
return f"Draft haul: −{n} under their original slots (about one {noun} given up){tail}"
```
Then re-export.

### CR-03: The preseason blurb says the score carries draft capital while the draft weight is 0

**File:** `pipeline/src/fgs/explain.py:168-169, 201-205`; `pipeline/src/fgs/export.py:233-234`
**Issue:** `blurb()` says what drives the score. When |surplus| ≥ the value of pick 64, the week-0 lead becomes "Preseason, carrying last season's form **plus extra draft capital**: …". That fires on 289 rows, for example "2026 CLE … plus extra draft capital: the Browns are one of the worst teams". `offseason.draft.weight` is 0, so the score contains no draft capital. The draft line right under the blurb says "— doesn't move the score", so the two sentences contradict each other. This breaks the project's core rule that the explanation must be honest about what moves the score. `draft_threshold` is passed whether or not `moves_score` is true.
**Fix:** Only use the draft lead when the term is live. Otherwise keep `PRESEASON` and let the separate draft line carry the information:
```python
"threshold": None if values is None or cfg["weight"] == 0 else float(values[64]),
```
Alternatively, write a neutral lead that doesn't claim the score includes the draft, for example "Preseason, carrying last season's form (draft capital shown below): ".

## Warnings

### WR-01: `display_only` and `weight` are never cross-validated, so the score can move while the metadata says "display only"

**File:** `pipeline/src/fgs/score.py:195-199, 218-222`; `pipeline/src/fgs/export.py:215, 233, 262`; `pipeline/src/fgs/methodology.py:181`; `pipeline/src/fgs/backtest.py:702`
**Issue:** `load_offseason` accepts `weight: 0.3, display_only: true`. `apply_offseason` ignores `display_only`, so it adds `contrib_draft` and changes the scores. The export then publishes `meta.offseason.draft.display_only = true` with `moves_score = true`.

The parts also disagree on what counts as a live weight:
- export uses `cfg["weight"] != 0`
- methodology uses `round(w, 2) == 0`

So a hand-edited weight of 0.004 adds a draft factor bar while the methodology says it "didn't pass the gate".

`draft_gate` can also produce `weight 0.00, display_only false` when the fitted weight is between 0 and 0.005.
**Fix:** In `load_offseason`, raise `ValueError` unless `display_only == (weight == 0.0)`. Use one helper, `score.offseason_live(cfg)`, everywhere (export, methodology, `apply_offseason`). In `draft_gate`, treat `round(final_w, 2) == 0` as a failure.

### WR-02: The walk-forward winsor bounds look ahead to later training seasons

**File:** `pipeline/src/fgs/backtest.py:679`
**Issue:** `draft_walk_forward` computes the winsor bounds once, from 2000–2021, and uses them for every fold. When fold S (for example 2003) is tested, its `draft_z` is clipped using percentiles that include drafts S..2021. This does not touch the 2022–2025 holdout, and the gate failed anyway. Still, the "walk-forward" evidence that methodology reports is not strictly out-of-sample, and a pass could be inflated by it.
**Fix:** Compute the bounds per fold from `[FIRST_DRAFT, S-1]` surplus, then apply `draft_z` inside the fold loop. Alternatively, document the look-ahead in the methodology note.

## Info

### IN-01: Exact SOS ties are broken alphabetically by `franchise_id`

**File:** `pipeline/src/fgs/draft.py:157`
**Issue:** On real data, 30 adjacent slot swaps come from SOS ties that are exact to the last bit (e.g. 2005 LV/SF, 2007 ATL/KC/LV, 2009 CHI/JAX and CAR/TEN, 2011 CAR/MIA). In these the alphabetically first team is placed first. The real order uses division/conference tiebreakers or a coin flip. Rotation carries the error into later rounds. Each swap creates a small spurious surplus (about 0.1–0.5) with a built-in alphabetical bias.
**Fix:** When `(grp, wp, sos)` ties exactly, take round-1 order from the actual draft when no trade is involved, or add an explicit tiebreak override table.

### IN-02: The pick-equivalent noun saturates at "#1 overall pick"

**File:** `pipeline/src/fgs/draft.py:299-305`, `explain.py:250-252`
**Issue:** Nine team-drafts have |surplus| above the stuart #1 value of 34.6 (e.g. MIA 2020 +39.8 and CLE 2018 +37.9). They read "about one extra #1 overall pick", which understates them.
**Fix:** When `abs(s) > values[1] * 1.1`, say "more than a #1 overall pick".

### IN-03: `equiv_pick` is meaningless for a zero surplus

**File:** `pipeline/src/fgs/export.py:136`
**Issue:** `Row.draft.equiv_pick` is 225 (the first pick worth 0.0) for a 0.0 surplus, e.g. CIN 2020. The web contract says "1..262", with no "not applicable" value.
**Fix:** Emit `null` when the text says "right at their original slots".

### IN-04: `changeText` says "preseason" for any null delta, including in-season weeks

**File:** `web/src/lib/format.ts:46`
**Issue:** A null `score_delta` at week > 0 reads "No change, preseason.". The BoardHeading week-0 note "Change is vs the end of last season." also shows for 1999, where every delta is null.
**Fix:** Return `'No change, preseason.'` only when `week === 0`, otherwise `'No change from last week.'`. Hide the heading suffix when the season is the first one in the data.

### IN-05: `fgs draft` recomputes winsor bounds instead of using the frozen weights.yaml values

**File:** `pipeline/src/fgs/cli.py:293, 301-302`
**Issue:** The CLI calls `draft.winsor_bounds(tbl)`, so its z column can drift from the exported `draft_z`, which uses the frozen `cfg["winsor"]`. Its "0.0" and "—" thresholds (0.05 and 1e-9) also differ from the text's 0.5.
**Fix:** Use `score.load_offseason()["winsor"]` (fall back to recomputing only when it is missing), and share one zero threshold with `draft_text`.

### IN-06: No winsor block in weights.yaml silently drops all draft display data

**File:** `pipeline/src/fgs/cli.py` (derive_games, `dz = ... if cfg.get("winsor") is not None else None`)
**Issue:** Without `offseason.draft.winsor`, `apply_offseason` gets no draft frame. Then `draft_surplus` is null on every row and the exported draft lines disappear, with no warning.
**Fix:** Fall back to `draft.winsor_bounds(base["draft"])` with a stderr warning, or keep surplus but set z to null.

### IN-07: Methodology hard-codes "2003–2021", and `_fold_pair` raises on malformed input

**File:** `pipeline/src/fgs/methodology.py:187`, `_fold_pair`
**Issue:** The note text ignores the recorded `test_seasons`. A malformed `fold_sign` such as "8 of 19" raises an unhandled `ValueError` from `int()`. Also, `format_draft_report` (`backtest.py`) raises `IndexError` on `seasons[0]` when no folds were produced.
**Fix:** Template the season range from `block["test_seasons"]`, catch `ValueError` in `_fold_pair` and return None, and guard against an empty `fold_seasons`.

---

_Reviewed: 2026-11-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---
phase: 04-game-result-factors-team-deep-dive
fixed_at: 2026-11-11T00:00:00Z
review_path: .planning/phases/04-game-result-factors-team-deep-dive/04-REVIEW.md
iteration: 1
findings_in_scope: 14
fixed: 13
skipped: 1
status: partial
---

# Phase 4: Code Review Fix Report

**Fixed at:** 2026-11-11
**Source review:** .planning/phases/04-game-result-factors-team-deep-dive/04-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 14 (scope: all, as directed by the orchestrator)
- Fixed: 13
- Skipped: 1 (IN-01, skipped on purpose as instructed)

The work was done directly on `main`, as instructed, with no worktree. Each fix has its own commit. The site data was regenerated with `uv run fgs export` and committed separately in `4adf21f`.

Verification:
- `uv run pytest -q` passed (239 tests).
- `npm run test` passed (64 tests).
- `npm run check` reported 0 errors and 0 warnings.
- `npm run build` succeeded.

## Fixed Issues

### CR-01: The `sow` blurb phrase asserts a false fact and contradicts the `mov` phrase

**Files modified:** `pipeline/src/fgs/explain.py`, `pipeline/tests/test_explain.py`, `pipeline/tests/test_export.py`
**Commit:** 2d8dd51
**Applied fix:** The `sow` phrases now describe what the factor measures: results compared with an average team against the same opponents.
- hi: "have been winning more than their schedule would predict" / "have results a bit better than their schedule"
- lo: "have come up short against beatable opponents" / "have results a bit worse than their schedule"

The FADE suffix logic is unchanged. New tests:
- A phrasebook test checks that no `sow` phrase mentions margins.
- A parametrized test over the mov and sow combinations checks that only `mov` mentions margins.
- A real-data test runs over every exported row. It checks that no blurb says "ahead of/behind their margins". It also checks that any blurb with a `mov`-hi phrase mentions "margin" at most once.

In the regenerated data, 164 blurbs pair "blowing teams out" with a schedule phrase. None of them contradict each other.

### WR-01: Week-0 blurb claims "carrying last season's form" when there is no last season

**Files modified:** `pipeline/src/fgs/explain.py`, `pipeline/src/fgs/export.py`, `pipeline/tests/test_explain.py`, `pipeline/tests/test_export.py`
**Commit:** 2c2f3d3
**Applied fix:** `blurb()` takes a new `preseason` kind: `carry`, `fresh` or `expansion`. Export picks the kind like this:
- `expansion` when `(franchise, season)` is in `season_config.SEEDS` (CLE 1999, HOU 2002).
- `fresh` for the first season in the data (1999).
- `carry` otherwise.

The two new kinds produce these sentences:
- fresh: "Preseason: no history yet, so the {nick} start even with everyone else."
- expansion: "Preseason: the {nick} are an expansion team starting below average."

Unit and real-data tests cover all three kinds.

### WR-02: Streak phrase reports the capped value, and "a 8-game skid" is ungrammatical

**Files modified:** `pipeline/src/fgs/explain.py`, `pipeline/tests/test_explain.py`
**Commit:** 4a30abe
**Applied fix:** A streak at `STREAK_CAP` now renders as "8+", e.g. "have won 8+ straight" or "have lost 8+ in a row". The strong losing phrase is now "have lost {k} in a row", so the a/an article problem is gone.

### WR-03: The factor breakdown shows only 4 of 7 bars, so the visible arithmetic doesn't add up

**Files modified:** `web/src/lib/team.ts`, `web/src/lib/team.test.ts`, `web/src/components/FactorBars.svelte`
**Commit:** 107af53
**Applied fix:** `barRows` now returns every factor as `rows`. The `top`/`shown`/`rest` split, the "All factors" `<details>` and its styles are removed. A test checks that the baseline plus all visible bars equals the score.

### WR-04: Stale "We don't know that team" notice reappears on later board visits

**Files modified:** `web/src/App.svelte`
**Commit:** 49dedcc
**Applied fix:** Any valid team or history route now clears the notice. Non-latest board routes already cleared it. The notice survives only the redirect it was raised for, so it no longer reappears on a later visit to the latest board.

### WR-05 (UI-1): Header meta line renders "7-1·#1" with no spacing or labels

**Files modified:** `web/src/components/TeamPage.svelte`
**Commit:** dd84d1d
**Applied fix:** `.sep` now gets `margin-inline: var(--space-xs)` instead of whitespace that Svelte trims. This covers both the "season · week · Now" line and the record line. The rank now reads "Rank #{rank}".

### WR-06 (UI-2): No gap between the emoji and the mood label

**Files modified:** `web/src/components/MoodLabel.svelte`
**Commit:** 550c6d6
**Applied fix:** `.emoji` now has `margin-inline-end: 0.35em`, so the gap scales with the heading size. `MoodLabel` is the shared component, so both the team page and the board rows get the fix.

### WR-07 (UI-3): Sparkline looks flat because its y-domain is a fixed 0-100 at 48px

**Files modified:** `web/src/lib/team.ts`, `web/src/lib/team.test.ts`, `web/src/components/Sparkline.svelte`, `web/src/components/TeamPage.svelte`
**Commit:** 10b7fc5
**Applied fix:** A new pure helper, `sparkDomain`, pads the season's min/max by max(3, 15% of the range) and clamps the result to 0..100. It has tests. The sparkline changes:
- Height is now 80px.
- The real min and max scores are labelled on the left in muted text.
- The aria-label includes the low and high scores.
- The reference rule uses `meta.baseline` and is drawn only when it falls inside the domain.

### IN-02: Residual spread in `largest_remainder` can flip a factor's sign

**Files modified:** `pipeline/src/fgs/explain.py`, `pipeline/tests/test_explain.py`
**Commit:** 54f57af
**Status:** fixed: requires human verification (rounding logic change)
**Applied fix:** After a largest-remainder pass, any factor whose integer has the opposite sign to its real share is set to 0 (rounded toward zero). The pass then re-runs over the remaining factors, and this repeats until no factor flips. If every factor gets fixed at 0, the leftover goes to the largest-|real| factor whose sign matches it. Sums stay exact.

The tests use a constructed case: [1, -1, 0.5] with a total of -5 used to give [-1, -3, -1] and now gives [0, -5, 0]. A random check over 500 cases confirms there are no flips whenever both signs are present.

### IN-03: Sparkline reference rule hard-coded at 50 instead of `meta.baseline`

**Files modified:** `web/src/components/Sparkline.svelte`, `web/src/components/TeamPage.svelte`
**Commit:** 10b7fc5 (shared with WR-07)
**Applied fix:** `Sparkline` takes a `baseline` prop, which `TeamPage` passes from `meta.baseline`. `Plot.ruleY([baseline])` uses it.

### IN-04: `barRows().total` is computed but never used

**Files modified:** `web/src/lib/team.ts`, `web/src/lib/team.test.ts`, `web/src/components/FactorBars.svelte`
**Commit:** 2a181bd
**Applied fix:** Removed `total` and the now-unused `baseline` parameter from `barRows`.

### IN-05: Ties within one as-of key are ordered by `game_id`, not by game date

**Files modified:** `pipeline/src/fgs/games.py`, `pipeline/src/fgs/features.py`, `pipeline/tests/test_features.py`
**Commit:** d8a5c35
**Status:** fixed: requires human verification (ordering logic change)
**Applied fix:** `build_team_games` now carries `gameday` and `gametime`. `_per_game` sorts by `franchise_id, key, gameday, gametime, game_id`, the same tiebreak the Elo replay uses. A test with two games that share an as-of key checks that the game played later sets the streak. `_last16` was left unchanged because order within a key doesn't change its windowed result there.

### IN-06: `#/team/ABBR/season` (no week) shows the board with the board notice

**Files modified:** `web/src/lib/router.ts`, `web/src/lib/router.test.ts`, `web/src/App.svelte`
**Commit:** b67c2a5
**Applied fix:** The router now parses `/team/ABBR/season` as a team route with only a season. App replaces it with `#/team/ABBR`, the team's latest page, and shows no notice.

## Skipped Issues

### IN-01: Historical rows use current nicknames

**File:** `pipeline/src/fgs/export.py:118`
**Reason:** Skipped on purpose, as the orchestrator instructed (cosmetic; needs a franchise/season nickname map).
**Original issue:** 2005 Washington rows read "the Commanders are…".

---

_Fixed: 2026-11-11_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

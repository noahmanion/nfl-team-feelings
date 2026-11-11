---
phase: 04-game-result-factors-team-deep-dive
reviewed: 2026-11-11T00:00:00Z
depth: standard
files_reviewed: 28
files_reviewed_list:
  - pipeline/src/fgs/backtest.py
  - pipeline/src/fgs/explain.py
  - pipeline/src/fgs/export.py
  - pipeline/src/fgs/features.py
  - pipeline/src/fgs/mood.py
  - pipeline/src/fgs/score.py
  - pipeline/tests/test_backtest.py
  - pipeline/tests/test_explain.py
  - pipeline/tests/test_export.py
  - pipeline/tests/test_features.py
  - pipeline/tests/test_leakage.py
  - web/src/App.svelte
  - web/src/components/BoardRow.svelte
  - web/src/components/FactorBars.svelte
  - web/src/components/HistoryPage.svelte
  - web/src/components/MoodBoard.svelte
  - web/src/components/MoodLabel.svelte
  - web/src/components/RecentGames.svelte
  - web/src/components/SiteHeader.svelte
  - web/src/components/Sparkline.svelte
  - web/src/components/TeamChip.svelte
  - web/src/components/TeamPage.svelte
  - web/src/lib/data.ts
  - web/src/lib/router.test.ts
  - web/src/lib/router.ts
  - web/src/lib/team.test.ts
  - web/src/lib/team.ts
  - web/src/lib/types.ts
findings:
  critical: 1
  warning: 7
  info: 6
  total: 14
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-11-11
**Depth:** standard
**Files Reviewed:** 28
**Status:** issues_found

## Summary

I reviewed the Phase 4 diff (`e670fec~1..HEAD`) across `pipeline/src`, `pipeline/tests` and `web/src`, and checked the claims against the regenerated data in `web/public/data`.

**What holds up:**
- **As-of correctness of the factors.** Every factor is keyed on `season*100 + asof_week` and joined backward. `sow` uses the opponent's `elo_pre`, which is the pre-game rating from `elo.replay`. HFA comes from the same `hfa_for` table the Elo replay uses. Neutral sites get 0.
- **Points attribution.** `largest_remainder` always sums exactly to `score - baseline`.
- **Recent games.** `recentGames` filters on `asof_week <= week`, so a page never shows a later result.

**Main problem:** the `sow` blurb phrase states something the factor doesn't measure. It produces self-contradictory sentences in about 13% of all shipped blurbs (CR-01).

Smaller problems:
- Week-0 blurb edge cases (1999 and expansion teams).
- The latent streak-cap and grammar bug.
- A factor-bar layout that hides the arithmetic it is meant to show.
- A stale notice.
- The three UI issues the orchestrator saw in the browser.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: The `sow` blurb phrase asserts a false fact ("record runs ahead of their margins") and contradicts the `mov` phrase

**File:** `pipeline/src/fgs/explain.py:118-119`

**Issue:** `sow` is defined in `features.py:15-17` and CONTEXT as *results against an average team's expected result versus the same opponents*. In other words, opponent quality of results. It does not compare record to margins. The phrasebook nevertheless renders `sow` hi as "have a record that runs ahead of their margins" and `sow` lo as "have a record that lags behind their margins". That wording reads the *partial* regression effect (a negative weight given mov) as if it were the raw fact.

The shipped data shows the damage:
- 2,493 of 19,422 blurbs use these phrases.
- Several directly contradict themselves, e.g. "The Bears have been blowing teams out, but have a record that runs ahead of their margins (that tends to fade)." (The same pattern appears for the Commanders and the Saints.)
- The top-of-board sample BUF (mov +12 points) reads "…but have a record that runs ahead of their margins".

For a product whose core value is "honest", the headline sentence states something the data doesn't say.

**Fix:** Phrase the fact the factor actually measures, and let `FADE` carry the regression caveat. CONTEXT already suggests "has beaten good teams".
```python
("sow", "hi"): ("have beaten good teams lately", "have results a bit better than their schedule"),
("sow", "lo"): ("have been losing to teams they should beat", "have results a bit worse than their schedule"),
```
Add a test asserting that no blurb contains both a `mov` hi phrase and a `sow` phrase that mentions margins.

## Warnings

### WR-01: Week-0 blurb claims "carrying last season's form" when there is no last season

**File:** `pipeline/src/fgs/explain.py:129,169`

**Issue:** The prefix is applied to every week-0 row. For 1999 (the first season) there is no prior form at all. Every team starts at 1505 except CLE at 1300. Because CLE drags the mean below 1505, every other team gets `z_elo > 0`, so all 30 rows read "Preseason, carrying last season's form: the Cardinals are a good team on paper." (score 55 for all). Expansion and re-entry teams are also wrong: CLE 1999 and HOU 2002 read "carrying last season's form: the Texans are one of the worst teams in football", though they have no last season.

**Fix:** Pass a "has prior games" flag (for example, the number of played games before this snapshot, or `last16` games counted > 0) into `blurb()`. When it is false, use "Preseason, before a single game: the {nick} start at an expansion-team rating." for seeded teams, and "Preseason: every team starts even." for 1999.

### WR-02: Streak phrase reports the capped value, and "a 8-game skid" is ungrammatical

**File:** `pipeline/src/fgs/explain.py:120-121,144-148` (cap at `features.py:34,164`)

**Issue:** `streak` is clipped to ±8 in `_streak`. `_phrase` reads the capped raw value, so a 12-game losing streak is described as "stuck in a 8-game skid". That is factually wrong, and the article should be "an". The current data has no such row yet (streak rarely makes the top 2), so this is latent, but it is a guaranteed bug once a long streak dominates.

**Fix:** Export the uncapped streak alongside the capped feature, or phrase k == STREAK_CAP as "{k}+". Choose the article with `"an" if str(k).startswith("8") or k in (11, 18) else "a"`, or reword it as "have lost {k} straight".

### WR-03: The factor breakdown shows only 4 of 7 bars above "= {score}", so the visible arithmetic doesn't add up

**File:** `web/src/components/FactorBars.svelte:36-52`, `web/src/lib/team.ts:69,79`

**Issue:** CONTEXT promises bars "that sum exactly to the displayed score". With `top = 4`, the default view for BUF shows "Average team 49", elo +49, sow −13, mov +12, season_record +10, and "= 96". Those visible numbers add to 107. The missing −11 (last16, luck, streak) is hidden inside a collapsed `<details>`. `barRows` computes `total` but nothing uses it.

**Fix:** Either show all factors (7 is small), or render a visible "Other factors {signed(sum(rest))}" line before the total when `rest.length > 0`. Use `bars.total` for the "=" line, or assert `bars.total === score` and fall back to the "unavailable" message when they disagree.

### WR-04: Stale "We don't know that team" notice reappears on later board visits

**File:** `web/src/App.svelte:78-99`

**Issue:** An unknown team sets `notice = TEAM_NOTICE` and redirects to `#/`. The notice is cleared only when the user navigates to a non-latest board. If the user goes from there to a valid team page and back to the latest board, the old notice is shown again.

**Fix:** Clear the notice on any successful route change that isn't the redirect itself. For example, add `else notice = null` for valid `team` and `history` routes, or key the notice to the hash it was raised for.

### WR-05 (UI-1): Header meta line renders "7-1·#1" with no spacing or labels

**File:** `web/src/components/TeamPage.svelte:116,118`

**Issue:** Svelte 5 trims leading and trailing whitespace inside elements, so `<span class="sep"> · </span>` compiles to `·` with no spaces. Line 116 has the same problem ("Week 9·Now"). The bare `#1` also isn't labelled as a rank.

**Fix:**
```svelte
<p class="sub">{record}<span class="sep" aria-hidden="true">&nbsp;·&nbsp;</span>Rank #{row.rank}</p>
```
Alternatively, give `.sep` `margin-inline: var(--space-xs)`. Apply the same fix on line 116.

### WR-06 (UI-2): No gap between the emoji and the mood label ("🎉Planning the parade") on the team page and board rows

**File:** `web/src/components/MoodLabel.svelte:5-7,10-15,21-23`

**Issue:** The only separation is `gap: var(--space-xs)` (4px) on the flex container. In the screenshot it renders as touching glyphs on both the team page (heading size) and BoardRow. Emoji with a variation selector (e.g. 🕶️) also have inconsistent advance widths, so 4px isn't reliable.

**Fix:** Give `.emoji` an explicit `margin-inline-end: 0.35em` (scales with the heading size), or raise the gap to `var(--space-sm)`. Check both sizes at 1280px.

### WR-07 (UI-3): Sparkline looks flat because its y-domain is a fixed 0–100 at 48px height

**File:** `web/src/components/Sparkline.svelte:40-47`

**Issue:** With `height: 48` and `margin: 4`, 100 score points map to 40px. A team moving between 85 and 96 changes by about 4px, so the line looks flat and conveys nothing.

**Fix:** Use a padded domain around the season's range, and label the extremes so the scale stays honest:
```ts
const lo = Math.min(...series.map(p => p.score)), hi = Math.max(...series.map(p => p.score))
const pad = Math.max(3, (hi - lo) * 0.15)
y: { domain: [Math.max(0, lo - pad), Math.min(100, hi + pad)] },
marks: [ /* … */, Plot.text([{week: series[0].week, score: hi}, {week: series[0].week, score: lo}],
  { x: 'week', y: 'score', text: d => String(d.score), textAnchor: 'start', dx: -2, fill: 'var(--text-muted)' }) ]
```
Increase `height` to about 72–96. Draw the reference rule only when the baseline falls inside the domain (see IN-03).

## Info

### IN-01: Historical rows use current nicknames

**File:** `pipeline/src/fgs/export.py:118` (`nicks` from `team_meta`)

**Issue:** 2005 Washington rows read "the Commanders are…". This is cosmetic, but it stands out in history.

**Fix:** Optional: add a small `(franchise, season_range) -> nick` override map.

### IN-02: Residual spread in `largest_remainder` can attribute points to a factor whose real share was ~0 or of the opposite sign

**File:** `pipeline/src/fgs/explain.py:63-67`

**Issue:** The residual between the smoothed-map sum and `score - baseline` (the exact percentile) is spread in proportion to |real|. When the contributions nearly cancel (composite ≈ 0), |resid| can exceed Σ|real| and flip the sign of a small factor's real share. When all reals are 0, the even split gives the first factor (elo) the whole ±1. Sums stay exact; this is only cosmetic.

**Fix:** Assign the residual to the largest-|real| factor whose sign matches the residual's sign, falling back to the largest overall.

### IN-03: Sparkline reference rule is hard-coded at 50 rather than `meta.baseline` (49)

**File:** `web/src/components/Sparkline.svelte:47`

**Fix:** Pass `baseline` as a prop and use `Plot.ruleY([baseline])`.

### IN-04: `barRows().total` is computed but never used

**File:** `web/src/lib/team.ts:78`

**Fix:** Use it for the "=" line (see WR-03) or remove it.

### IN-05: Ties within one as-of key are ordered by `game_id`, not by game date

**File:** `pipeline/src/fgs/features.py:120`

**Issue:** If a team has two games sharing an `asof_week` (a postponed game), `game_id` order follows the original week label rather than the actual play order. That could misorder `streak`. The Elo replay sorts by `gameday`.

**Fix:** Sort with `["franchise_id", "key", "gameday", "gametime", "game_id"]`.

### IN-06: `#/team/BUF/2026` (season without week) shows the board with the *board* notice

**File:** `web/src/lib/router.ts:13`, `web/src/App.svelte:94-96`

**Fix:** Optional: accept `/team/ABBR/season` and redirect it to that season's last week, or to the team's latest page.

---

_Reviewed: 2026-11-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

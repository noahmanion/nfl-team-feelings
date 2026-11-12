---
phase: 13-explore-charts-win-totals-display
reviewed: 2026-11-11T00:00:00Z
depth: standard
files_reviewed: 34
files_reviewed_list:
  - pipeline/src/fgs/export.py
  - pipeline/tests/test_export.py
  - web/src/App.svelte
  - web/src/components/BoardRow.svelte
  - web/src/components/CalloutCard.svelte
  - web/src/components/CalloutCards.svelte
  - web/src/components/ChartFrame.svelte
  - web/src/components/Delta.svelte
  - web/src/components/EpaScatter.svelte
  - web/src/components/ExplorePage.svelte
  - web/src/components/ExploreTable.svelte
  - web/src/components/HistoryChart.svelte
  - web/src/components/MoodBoard.svelte
  - web/src/components/RecordScatter.svelte
  - web/src/components/RecordsPage.svelte
  - web/src/components/SiteHeader.svelte
  - web/src/components/TeamPage.svelte
  - web/src/components/WinTotals.svelte
  - web/src/lib/data.ts
  - web/src/lib/explore.ts
  - web/src/lib/format.ts
  - web/src/lib/router.ts
  - web/src/lib/scatterMarks.ts
  - web/src/lib/types.ts
  - web/src/lib/winTotals.ts
  - web/src/lib/explore.test.ts
  - web/src/lib/winTotals.test.ts
  - web/src/lib/winTotalsRender.test.ts
  - web/src/lib/noLuck.test.ts
  - web/src/lib/router.test.ts
  - web/src/lib/format.test.ts
  - web/src/lib/chartFrame.test.ts
  - web/src/lib/sep.test.ts
  - .planning/phases/13-explore-charts-win-totals-display/verify_ui.py
findings:
  critical: 0
  warning: 4
  info: 7
  total: 11
status: issues_found
---

# Phase 13: Code Review Report

**Reviewed:** 2026-11-11
**Depth:** standard
**Files Reviewed:** 34
**Status:** issues_found

## Narrative Findings (AI reviewer)

## Summary

I reviewed the Phase 13 diff (`c574774..HEAD`): the display-only `expectation` export, the new Explore page (router, page, two Plot scatters, shared mark and click helpers, table view), the win-totals block on the team page, and the Phase 12 UI leftovers.

The core logic is sound. I checked these against the shipped data:
- OLS fit, residual dek, competition ranks, padded domains, tick thinning, and tier diagonals.
- Pace and finished logic, including the 2022 BUF/CIN 16-game seasons.
- REG-only EPA in playoff weeks. The snapshot W–L freezes at the regular-season record, which I confirmed in `snapshots/2024.json` and `2022.json`.
- Agreement between `vegas_win_totals.used_in_score` and `expectation.source`, which match for all 32 team files.
- 2026 EPA week coverage against `meta.latest`.

I found no security issues: no `{@html}` or `innerHTML`, and every href is built from franchise codes. I found no blockers.

The four warnings are user-facing. They cover wrong guidance in empty-state and note copy, a routing fallback that breaks D-01, and a rank-delta label that claims "no change" when the data is missing.

## Warnings

### WR-01: "No week" empty state tells the user to pick an *earlier* week

**File:** `web/src/lib/explore.ts:204`
**Issue:** `emptyCopy('no-week', …)` returns "No efficiency data through {week} yet. Pick an earlier week." This state happens when games have been played (`gamesPlayed > 0`) but the EPA file has no rows at or before `w`. Two examples: pbp lags the snapshot in Week 1 of a new season, or the EPA file is published before its first week's games. `seasonToDate` takes `week <= w`, so an earlier week has the same or fewer EPA rows. Following the advice can never show the chart, and the only earlier week is week 0, which shows the "no games" state. The test at `explore.test.ts:267` locks in the wrong copy.
**Fix:** Point the user at the latest week or a later one, or just state the situation:
```ts
return `No efficiency data through ${weekLabelText} yet. Check back after the play-by-play update.`
```
Update the `explore.test.ts` expectation to match.

### WR-02: Malformed explore week (3+ digits) redirects to the board with a board-specific notice, breaking D-01

**File:** `web/src/lib/router.ts` (EXPLORE regex `\d{1,2}`), `web/src/App.svelte:127`
**Issue:** D-01 says an invalid season or week falls back to `#/explore` silently. `#/explore/2025/123` (asserted in `router.test.ts:123`) and `#/explore/abc` parse as `{kind:'invalid'}`. App then runs `replace('#/')` and shows `BOARD_NOTICE` ("We don't have a board for that week…"). The user leaves the Explore page and sees a message about a board they never asked for. Only in-range-format but out-of-range values like `#/explore/2099/3` hit the D-01 path.
**Fix:** Have the regex accept any digits (`(\d+)`) or a trailing garbage segment and return `{kind:'explore'}` for the malformed tail, so App's existing explore branch does `replace('#/explore')`. Alternatively, special-case `h.startsWith('/explore')` before the `invalid` fallthrough:
```ts
const EXPLORE = /^\/explore(?:\/(\d+)(?:\/(\d+))?)?\/?$/
// ...
if (/^\/explore(\/|$)/.test(h)) return { kind: 'explore' } // any other explore-ish path → latest, silently
```

### WR-03: Win-totals note hardcodes "before 2003" for any season without a Vegas line

**File:** `web/src/lib/winTotals.ts:87-88`
**Issue:** `vi < 0` (no Vegas row for the season) always produces "No Vegas line on file before 2003." Per CLAUDE.md, lines from 2021 onward are typed in by hand from covers.com. When the next season starts (2027) before someone enters its line, `winTotalsView` falls into this branch. The team page would then tell users the 2027 line is missing because it is "before 2003". The same applies to any 2021+ team-season left out by mistake. Nothing tests this branch for a season ≥ 2003.
**Fix:** Branch on the season:
```ts
const notes = vi < 0
  ? season < 2003
    ? 'No Vegas line on file before 2003. The score uses the model’s preseason expectation.'
    : 'No Vegas line on file for this season yet. The score uses the model’s preseason expectation.'
  : ...
```
Add a `winTotals.test.ts` case for a 2027 file with only an `expectation` entry.

### WR-04: Missing rank delta now renders as visible "no change" while the score delta beside it renders "–"

**File:** `web/src/lib/format.ts:42`, `web/src/components/Delta.svelte`, `web/src/components/BoardRow.svelte:83-84`
**Issue:** `formatRankDelta(null|undefined)` returns `'no change'`. A null `rank_delta` means there is no prior snapshot: 1999 week 0, HOU 2002 week 0, or rows without a previous week. That is unknown, not unchanged. The neighboring `<Delta kind="score">` renders `formatDelta(null)` as `–`, so the same row shows "– / no change". On the 1999 preseason board, all 31 rows claim "no change". The `format.test.ts:146-151` case locks this in.
**Fix:** Keep the en-dash for missing data and use words only for a real zero:
```ts
if (!isNum(value)) return { text: '–', dir: 'none', aria: 'No prior rank' }
if (value === 0) return { text: 'no change', dir: 'none', aria: 'No change in rank' }
```

## Info

### IN-01: `aria-label` on rank `Delta` is dead

**File:** `web/src/components/Delta.svelte` (rank branch)
**Issue:** The only rank `Delta` (BoardRow:84) sits inside `<span class="change" aria-hidden="true">`. ARIA 1.2 also prohibits naming a generic `<span>`. Screen readers never announce the new `aria-label`; BoardRow's `srText`/`changeText` already covers this information.
**Fix:** Drop `aria-label` and the `aria` field, or add `role="img"` if the component is ever used outside an aria-hidden container.

### IN-02: `leagueMeans` weights by total plays, not by plays with non-null EPA

**File:** `web/src/lib/explore.ts:61-62`
**Issue:** `seasonToDate` averages `off_epa` over `oep` (plays in games with non-null EPA), but `leagueMeans` weights each team by `off_plays` (all plays). If a team-game ever has `off_plays > 0` with `off_epa == null`, the crosshair stops being the true play-weighted mean of the plotted rates. This is latent: the current EPA files have 0 such rows.
**Fix:** Have `seasonToDate` expose `off_epa_plays`/`def_epa_plays` (`oep`/`dep`) and weight by those.

### IN-03: Number-line markers overflow the track at 0 and reg_games

**File:** `web/src/components/WinTotals.svelte:108-113`
**Issue:** `.mk` uses `translate(-50%, -50%)` at `left: 0%` or `100%`. A 0-win pace (e.g. 0–3) or a 17–0 finish puts half of the 12px dot outside the number line. Tick labels got `.first`/`.last` edge handling; markers didn't.
**Fix:** Inset the track (e.g. `inset-inline: 6px` on a wrapper the markers are positioned in), or clamp `left` with `calc(clamp(6px, X%, 100% - 6px))`.

### IN-04: Finished dek drops the unit

**File:** `web/src/lib/winTotals.ts:78`
**Issue:** "Vegas set the line at 10.5 wins. They finished with 13." is missing "wins". The in-progress branch also omits it ("on pace for 12.8.").
**Fix:** `` `They finished with ${w} wins.` `` (and `` `on pace for ${p.toFixed(1)} wins.` ``).

### IN-05: Team-file failure is never retried for the rest of the session

**File:** `web/src/components/TeamPage.svelte:116-133`
**Issue:** The effect depends only on `team` and `meta`. After one failed fetch, `teamFile = {failed: true}` persists while the user moves between weeks or seasons of the same team, so the expectations section stays hidden even though `loadTeam` evicted the cache entry. Unlike recent games, it offers no retry action.
**Fix:** Add a `teamRetry` counter like `gamesRetry`. Or render a StatusPanel with "Try again" in place of silently omitting the section.

### IN-06: `noLuck.test.ts` scans a hardcoded list that skips `scatterMarks.ts`

**File:** `web/src/lib/noLuck.test.ts:5-14`
**Issue:** `lib/scatterMarks.ts` is an Explore source (it draws marks and handles clicks) but isn't in the glob. Any future Explore helper file would also escape the D-15 guard.
**Fix:** Add `./scatterMarks.ts` and update the expected count to 6. Or use a pattern list (`'../components/{Explore,Epa,Record}*.svelte'`, `'./{explore,scatterMarks}.ts'`).

### IN-07: Duplicated week validation and a dead fallback in ExplorePage

**File:** `web/src/components/ExplorePage.svelte:40-50`
**Issue:** `validWeek` duplicates `App.svelte` `validTeamWeek` (lines 81-84). `seasonMeta = $derived(findSeason(meta, s)!)` asserts non-null, then line 50 tests `seasonMeta ? … : 'Week ${w}'`, which is dead under the assertion.
**Fix:** Move `validWeek(meta, season, week)` into `lib/data.ts` and use it in both places. Drop the `!` and keep the guard, or keep the `!` and drop the guard.

---

_Reviewed: 2026-11-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

## Orchestrator note

- **WR-02 is accepted as designed.** RESEARCH "Open Question Resolutions" #2 decided that malformed explore hashes (`#/explore/abc`, or a 3-digit week that fails the regex) take the existing invalid-route path, which is the board plus a notice. Only a well-formed `#/explore/{season}/{week}` with an unknown season or out-of-range week falls back silently to `#/explore`. The fixer should skip WR-02.

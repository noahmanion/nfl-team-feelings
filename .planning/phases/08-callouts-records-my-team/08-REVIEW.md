---
phase: 08-callouts-records-my-team
reviewed: 2026-11-11T23:30:00Z
depth: standard
files_reviewed: 32
files_reviewed_list:
  - pipeline/src/fgs/checks.py
  - pipeline/src/fgs/cli.py
  - pipeline/src/fgs/evidence.py
  - pipeline/src/fgs/export.py
  - pipeline/src/fgs/insights.py
  - pipeline/src/fgs/paths.py
  - pipeline/src/fgs/records.py
  - pipeline/src/fgs/season_config.py
  - pipeline/tests/test_evidence.py
  - pipeline/tests/test_insights.py
  - pipeline/tests/test_records.py
  - web/src/App.svelte
  - web/src/components/Badge.svelte
  - web/src/components/BoardRow.svelte
  - web/src/components/CalloutCard.svelte
  - web/src/components/CalloutCards.svelte
  - web/src/components/HistoryPage.svelte
  - web/src/components/MoodBoard.svelte
  - web/src/components/MoversStrip.svelte
  - web/src/components/PinButton.svelte
  - web/src/components/RecordsPage.svelte
  - web/src/components/SiteHeader.svelte
  - web/src/components/TeamPage.svelte
  - web/src/lib/callouts.ts
  - web/src/lib/copyLink.ts
  - web/src/lib/data.ts
  - web/src/lib/history.ts
  - web/src/lib/myteam.svelte.ts
  - web/src/lib/myteam.ts
  - web/src/lib/records.ts
  - web/src/lib/router.ts
  - web/src/lib/types.ts
findings:
  critical: 0
  warning: 10
  info: 7
  total: 17
status: issues_found
---

# Phase 8: Code Review Report

**Reviewed:** 2026-11-11T23:30:00Z
**Depth:** standard
**Files Reviewed:** 32
**Status:** issues_found

## Narrative Findings (AI reviewer)

## Summary

I reviewed the Phase 8 diff (`45fe02e~1..HEAD`) across `pipeline/src`, `pipeline/tests` and `web/src`. I traced these areas by hand: perception-gap ranking, cap and tiebreaks; the evidence seal and staleness guard; snapshot dating and run-length streak math; extremes tiebreak and expansion exclusion; how callouts are stored per week; the copy-link fallback; localStorage handling; pin placement; and card and strip accessibility.

The core logic holds up:
- Record ranks use win% (ties count half; 0-0 counts as .500), then point differential, then franchise id.
- The cap is per (season, week, flavor), ordered by |gap| and then score rank.
- The evidence seal filters to seasons up to 2021 before anything else runs.
- Runs measure `[start, first breaking snapshot)` in calendar days.
- Expansion seeds are dropped from both extremes and streaks.
- The pin button is a sibling of the row `<a>`, not nested inside it.
- Storage access is wrapped in try/catch throughout.

I found no blockers. The main problems:
- The same streak shows two different day counts depending on where you look.
- Evidence staleness is only partly guarded.
- The `execCommand` copy fallback can report a false "Link copied".
- Several accessibility gaps.
- The nav wraps badly on mobile, as the orchestrator observed.

## Warnings

### WR-01: Streak day counts disagree between the board card and the team page it links to

**File:** `pipeline/src/fgs/insights.py:309`, `pipeline/src/fgs/records.py:112`, `web/src/components/TeamPage.svelte:84-118`
**Issue:** Streak callouts count days up to the week's snapshot date (`d - start`). `records.json` `active` counts up to `as_of`, the export date. In the shipped data, the latest board card says "Titans fans have been miserable for **756** straight days", but the team page says "Miserable for **758** straight days". BUF shows 1,148 on the board and 1,150 on the team page. The card's "See Titans" link (`#/team/TEN/2026/9`) resolves to the latest team view. That view shows the 758 line and hides the 756 card, so one click changes the number. TeamPage hides the card on its own page, but the board does not.
**Fix:** Pick one reference date for the latest week. Either:
- compute the latest week's streak callouts with `as_of` instead of the week date (in `streak_callouts`, use `as_of` when `(season, week) == latest`), or
- have TeamPage show `streak.days` from the callout when one exists for the latest week.

The first is simpler:
```python
# callouts_by_week: pass latest=(s, w); in streak_callouts:
ref = as_of if (season, week) == latest else d
days = (ref - r["start"]).days
```

### WR-02: Evidence staleness fingerprint misses inputs that change score ranks

**File:** `pipeline/src/fgs/export.py:211-231`, `pipeline/src/fgs/insights.py:65-77`
**Issue:** The guard checks the threshold, first week, training window, factor weights and the offseason draft weight. Score ranks also depend on Elo hyperparameters (K, HFA by era, MOV, regression), feature definitions and code, and nflverse revisions to 1999–2021 data. Any of these can change which team-weeks are flagged and the n, team and peer rates, and the export would still ship the old "55% / 45% (594 cases)" line. The guard says stale numbers can never ship, but it does not cover these inputs.
**Fix:** Add a content hash of the flagged training set to the fingerprint. For example, hash the sorted `(season, week, franchise_id, flavor)` rows from `gap_flags(record_ranks(scored≤2021, team_games≤2021))`. The export can compute this cheaply, and it never imports the backtest:
```python
flags = insights.gap_flags(insights.record_ranks(scored.filter(pl.col("season") <= last), tg.filter(...)))
cases_fp = hashlib.sha256(flags.select(KEYS+["flavor"]).sort(KEYS).write_csv().encode()).hexdigest()[:12]
```
Store `cases_fingerprint` in `callout_evidence.json` and compare it in `_load_evidence`.

### WR-03: `_load_evidence` does not validate flavor payloads; n=0 crashes the export

**File:** `pipeline/src/fgs/export.py:226-231`, `pipeline/src/fgs/insights.py:46-52`, `pipeline/src/fgs/evidence.py:87-88`
**Issue:** `peer_stats` writes `{"n": 0, "team_win": None, ...}` when a flavor has no cases, which can happen after a threshold change. `_load_evidence` accepts it. Then `evidence_text` does `round(100 * None)` and raises `TypeError` deep in `callouts_by_week`, with no useful message. A hand-edited file missing a `hopeful` key fails with a bare `KeyError` in the same way.
**Fix:** In `_load_evidence`, check that each of `hopeful` and `worried` has `n > 0` and numeric `team_win` and `peer_win`. Raise `ValueError` with a clear message, or have `evidence_text` return `None` for that flavor.

### WR-04: The `execCommand` fallback can report "Link copied" when nothing was copied

**File:** `web/src/lib/copyLink.ts:35-48`
**Issue:**
- The temporary textarea is never focused. `select()` on an unfocused, off-screen element does not reliably make it the active document selection.
- Chromium returns `true` from `execCommand('copy')` whenever the command is enabled, whether or not anything was copied. So the user can see "Link copied" while the clipboard still holds older content.
- On iOS Safari, `select()` on a `readonly` textarea does not select text unless `setSelectionRange` is called.
- After the `await` on a rejected `writeText`, the user activation may already be used up, so this tier often fails silently anyway.
- When focus does move to the textarea and it is then removed, keyboard focus drops to `<body>` instead of returning to the Copy button.
**Fix:**
```ts
const prev = document.activeElement as HTMLElement | null
ta.style.top = '0'; ta.style.left = '0'
doc.body.appendChild(ta)
ta.focus(); ta.select(); ta.setSelectionRange(0, text.length)
ok = doc.execCommand('copy')
// finally: ta.remove(); prev?.focus()
```
Optionally, treat the tier as successful only if `document.getSelection()?.toString() === text` before the copy.

### WR-05: The copy status live region is `display:none` until it has text, so the first announcement can be lost

**File:** `web/src/components/CalloutCard.svelte:38-40,134-136`
**Issue:** `.status:empty { display: none }` takes the `role="status"` element out of the accessibility tree until text is inserted. Several screen readers (VoiceOver and NVDA in some browsers) only announce changes to a live region that was already in the tree. "Link copied" and "Copy the link below" may never be announced. `result` also never resets, so a second click leaves the text unchanged and nothing is re-announced.
**Fix:** Keep the region rendered and visually hide it while it is empty, for example with a `visually-hidden` class or `min-height: 0` without `display: none`. Reset `result = 'idle'` at the start of `copy()`, then set the new value after a microtask. For the `manual` case, move focus to the readonly input so keyboard users land on it.

### WR-06: PinButton combines `aria-pressed` with a label that flips between Pin and Unpin

**File:** `web/src/components/PinButton.svelte:13-14`
**Issue:** A toggle button should either keep a fixed label with `aria-pressed`, or change its label without `aria-pressed`, but not both. Right now screen readers announce "Unpin Buffalo Bills as my team, toggle button, pressed". The pressed state plus the inverted verb is contradictory and confusing.
**Fix:** Use a fixed label `aria-label="{name}: my team"` (or "Pin {name} as my team") with `aria-pressed={pinned}`. Or keep the changing label and drop `aria-pressed`.

### WR-07: CalloutCards on the team page breaks the heading hierarchy

**File:** `web/src/components/CalloutCards.svelte:19`, `web/src/components/CalloutCard.svelte:31`, `web/src/components/TeamPage.svelte:180`
**Issue:** CalloutCards always renders an `<h2>`, and each card renders an `<h3>`. On TeamPage the team name is already the `<h2>` and its sections ("Score breakdown", etc.) are `<h3>`. So "Callouts" becomes a sibling of the team name, and the card headlines sit at the same level as the page's own sections. The card `<h3>` headlines also leave out the team ("5-4, but better days are coming" appears twice, for SEA and LA, in the current data), so heading navigation lists identical, ambiguous entries. The section also has both `aria-label` and a visible `h2`, where `aria-labelledby` would be the right pattern.
**Fix:** Add a `level` prop (2 on the board, 3 on the team page) and render the card heading at `level + 1`. Use `aria-labelledby` pointing to the heading id. Include the team in the card's accessible heading, for example `<h3><span class="visually-hidden">{name}: </span>{callout.headline}</h3>`.

### WR-08: Team-season extremes include the in-progress season and rank it on a partial sample

**File:** `pipeline/src/fgs/records.py:43-75`
**Issue:** `team_season_extremes` uses every REG row up to the latest week, so 2026 team-seasons (9 weeks so far) compete for "Saddest/Happiest fanbases ever". Ties at the 0/100 clip break on REG mean, and a mean over 9 weeks is not comparable with a mean over a full season. A hot start could rank above a complete season. RECORDS_CHECK also labels the partial record "Final REG". No 2026 entry is in the top 10 today, but nothing prevents one.
**Fix:** Exclude the current season until its last REG week has been played (`max week < reg_weeks(season)` means skip). Or keep it, mark the entry `in_progress: true`, and label it "so far" on the page and in RECORDS_CHECK.

### WR-09: `as_of` is a UTC date, but snapshot dates are US-local gamedays

**File:** `pipeline/src/fgs/export.py:254`
**Issue:** `as_of = generated_at[:10]` comes from a UTC timestamp. An export run after 8 pm ET (for example, right after Monday Night Football) gets tomorrow's date, which adds 1 to every active streak and to the fallback week-0 clamp. Gamedays in nflverse are local ET dates, so the two reference dates are in different zones.
**Fix:** Derive `as_of` in `America/New_York`:
```python
from zoneinfo import ZoneInfo
as_of = datetime.fromisoformat(generated_at).astimezone(ZoneInfo("America/New_York")).date()
```

### WR-10: Top nav wraps badly at 320–375px, leaving a dangling "·" at the end of line 1 (orchestrator browser observation)

**File:** `web/src/components/SiteHeader.svelte:12-20,41-47`, `web/src/components/Sep.svelte`
**Issue:** At 375px, adding "Records" pushes "How it works" onto a second line. Each `<Sep />` is its own flex item, so the separator before "How it works" stays at the end of line 1 with nothing after it. The nav uses `flex-wrap: wrap` with `gap: var(--space-xs)` plus the Sep's own `margin-inline`, which wastes horizontal space.
**Fix:** Group each separator with the link after it, so a wrapped line starts with "· How it works" instead of ending with "·". Also tighten the spacing on small screens. Keep using `<Sep />`, because `sep.test.ts` forbids hand-rolled separators:
```svelte
<nav aria-label="Views">
  <a href="#/" ...>Board</a>
  <span class="item"><Sep /><a href="#/history" ...>Mood over time</a></span>
  <span class="item"><Sep /><a href="#/records" ...>Records</a></span>
  <span class="item"><Sep /><a href="#/methodology" ...>How it works</a></span>
</nav>
<style>
  nav { display: flex; flex-wrap: wrap; align-items: center; column-gap: 0; row-gap: 0; }
  .item { display: inline-flex; align-items: center; white-space: nowrap; }
</style>
```
Alternatively, below 480px, hide the separators (`nav :global(.sep) { display: none }`) and use `column-gap: var(--space-md)`. Verify at 320px and 375px.

## Info

### IN-01: Stale comment in App

**File:** `web/src/App.svelte:181`
**Issue:** `// 08-05 replaces null with the pinned team.` The code below it already passes `validMyTeam(...)`.
**Fix:** Delete the comment or reword it.

### IN-02: RecordsPage footnote hard-codes the excluded seasons, and `excludedText` is used only as a flag

**File:** `web/src/components/RecordsPage.svelte:62-64,148-151`
**Issue:** The footnote always says "The 1999 Browns and 2002 Texans", even though `records.excluded` drives `excludedText`. The computed string is never rendered. If `SEEDS` changes, the copy will be wrong.
**Fix:** Render `{excludedText}` in the sentence, or remove the derived value.

### IN-03: `streakStripe` assumes exactly 7 bands

**File:** `web/src/components/RecordsPage.svelte:46-47`
**Issue:** It hard-codes `--mood-0` and `--mood-6`, while `scoreStripe` and other code map through `moodToken(i, bands.length)`.
**Fix:** `var(--mood-${moodToken(kind === 'misery' ? 0 : meta.bands.length - 1, meta.bands.length)})`.

### IN-04: Unused `check_path` in `_cmd_refresh`

**File:** `pipeline/src/fgs/cli.py:462`
**Issue:** The value is assigned and never printed, unlike in `_cmd_export`. Also, `_write_records_check` runs before `marker.unlink()`, so a failure there leaves an "incomplete refresh" marker even though `write_export` already succeeded.
**Fix:** Print it, or drop the assignment. Consider writing RECORDS_CHECK after unlinking the marker, since it is not part of the web data set.

### IN-05: The "My team" highlight is a 6% tint, not the "accent outline" from CONTEXT

**File:** `web/src/components/BoardRow.svelte:94-96`, `web/src/components/RecordsPage.svelte:217-219`
**Issue:** A 6% `color-mix` tint is close to invisible on many displays. The badge carries most of the signal. CONTEXT asked for an accent outline.
**Fix:** Add `outline: 2px solid var(--accent); outline-offset: -2px` (or an accent border) to `.mine .row`.

### IN-06: RECORDS_CHECK.md is rewritten with the date on every export

**File:** `pipeline/src/fgs/cli.py:472-477`, `pipeline/src/fgs/records.py:164`
**Issue:** The `as_of` date and the active-streak day counts change daily, so every export produces a git diff even when the records are unchanged. This is noise for the hand-check sign-off.
**Fix:** Acceptable for a prototype. Optionally, put the date-dependent counts in a separate section, or skip the write when only `as_of` changed.

### IN-07: Active streak days freeze at export time with no "as of" on the team page

**File:** `web/src/components/TeamPage.svelte:174-176`
**Issue:** The records page shows "As of {date}", but the team-page line "Miserable for 758 straight days" does not. On a static site that is not re-exported daily, the count goes stale without any indication.
**Fix:** Either compute days client-side from `activeStreak.start` (UTC-safe, as `formatDate` already does), or append "as of {formatDate(records.as_of)}".

---

_Reviewed: 2026-11-11T23:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

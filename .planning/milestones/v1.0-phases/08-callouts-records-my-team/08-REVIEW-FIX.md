---
phase: 08-callouts-records-my-team
fixed_at: 2026-11-11T23:50:05Z
review_path: .planning/phases/08-callouts-records-my-team/08-REVIEW.md
iteration: 1
findings_in_scope: 17
fixed: 17
skipped: 0
status: all_fixed
---

# Phase 8: Code Review Fix Report

**Fixed at:** 2026-11-11T23:50:05Z
**Source review:** .planning/phases/08-callouts-records-my-team/08-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 17 (10 warnings, 7 info; scope "all", as the orchestrator asked)
- Fixed: 17
- Skipped: 0

Work was done directly on `main`, as instructed, with one atomic commit per finding plus one data-regeneration commit. No frozen artifact was touched: `weights.yaml` `weights:`/`fit:`/`offseason`, `HOLDOUT_RESULT.*`, `PREREGISTRATION.md` and `FREEZE_RESULT.json` are unchanged. `callout_evidence.json` was recomputed on 1999–2021 only, and its numbers did not change (hopeful n=594, 54.9% vs 44.8%; worried n=631, 45.0% vs 54.6%).

**Verification after all fixes:**
- `cd pipeline && uv run pytest -q`: 582 passed
- `uv run fgs check`: all checks passed
- `uv run fgs export`: regenerated data was committed
- `cd web && npm run test`: 145 passed
- `npm run check`: 0 errors, 0 warnings
- `npm run build`: OK
- In the shipped data, the latest board cards now match `records.json` `active`: TEN 758 = 758 and BUF 1,150 = 1,150, each card reading "as of Nov 11, 2026".
- The nav was checked in headless Chrome inside 320, 360 and 375px iframes. A wrapped line now begins with "· How it works", and no "·" is left dangling at the end of a line.

## Fixed Issues

### WR-01: Streak day counts disagree between the board card and the team page it links to

**Files modified:** `pipeline/src/fgs/insights.py`, `pipeline/src/fgs/export.py`, `pipeline/tests/test_insights.py`, `web/src/components/TeamPage.svelte`
**Commit:** 39ae751
**Applied fix:**
- `streak_callouts` now takes `latest` and `as_of`. The latest (season, week) counts days through the export date, which is the same date `records.json` `active` uses. Past weeks keep their own week date.
- The card detail names its reference date: "Score under 20 since Oct 14, 2024, as of Nov 11, 2026."
- `callouts_by_week` defaults `latest` to `asof.latest_played(games)`, and the export passes it explicitly.
- The team page streak line now reads "…, since {start} (as of {records.as_of})". This also covers IN-07.
- New test: `test_streak_callouts_latest_week_counts_through_as_of`.

### WR-02: Evidence staleness fingerprint misses inputs that change score ranks

**Files modified:** `pipeline/src/fgs/fingerprint.py` (new), `pipeline/src/fgs/export.py`, `pipeline/src/fgs/evidence.py`, `pipeline/src/fgs/cli.py`, `pipeline/tests/test_export.py`, `pipeline/tests/test_evidence.py`, `pipeline/callout_evidence.json`
**Commit:** 8827922
**Applied fix:** The new module `fgs.fingerprint` computes three hashes alongside the existing threshold, window, training-season and weights checks:
- `elo_fingerprint`: covers EloParams K, mean, reversion and seeds, plus `HFA_BY_ERA` and `MEAN_ELO`.
- `code_fingerprint`: an AST hash with comments and docstrings stripped. It covers:
  - the whole modules that build games, Elo, the sim, features, draft, score and mood, plus `season_config`, `backtest` and `evidence`;
  - only `derive_games`/`draft_winsor` from `cli.py`, and only `record_ranks`/`gap_flags` from `insights.py`.

  The source files are read and parsed, never imported, so the leakage firewall still holds. Editing copy or docs does not invalidate the evidence.
- `data_fingerprint`: a hash of the seasons up to 2021 only. It covers scored team-weeks (rank, score, W-L-T) and played team-games (points, outcome). Weekly refreshes of 2022+ never move it.

`fgs evidence` writes all of these. `_load_evidence` recomputes them from the frames the export ships and refuses a mismatch. `callout_evidence.json` was regenerated and committed.

New tests cover:
- the data hash ignoring 2022+ changes but changing when 1999–2021 data changes;
- the Elo hash tracking K, reversion and HFA;
- the code hash ignoring docs and copy but changing on a code change;
- stale-evidence rejection for each new key.

### WR-03: `_load_evidence` does not validate flavor payloads; n=0 crashes the export

**Files modified:** `pipeline/src/fgs/insights.py`, `pipeline/src/fgs/cli.py`, `pipeline/src/fgs/export.py`, `pipeline/tests/test_insights.py`
**Commit:** 23c7cc9
**Applied fix:**
- `evidence_text` returns None, so the card shows no evidence line, when any of these is true:
  - the flavor is missing or not a dict;
  - `n` is not a positive int;
  - `team_win` or `peer_win` is not a number in [0, 1];
  - `train_seasons` is malformed.
- The `fgs evidence` summary print no longer formats a None `d_margin` when n=0.
- Tests: parametrized zero-case and malformed entries, plus `gap_callouts` with all-zero evidence, which still ships callouts with `evidence: None`.

### WR-04: The `execCommand` fallback can report "Link copied" when nothing was copied

**Files modified:** `web/src/lib/copyLink.ts`, `web/src/lib/copyLink.test.ts`
**Commit:** 0b984f6
**Applied fix:**
- The temporary textarea is pinned at top/left 0, then focused, `select()`ed and `setSelectionRange(0, len)`.
- `execCommand('copy')` runs only after checking that the textarea is the active element and that the full text is selected. Otherwise the result is `manual`.
- The previously focused element (the Copy button) gets focus back in a `finally` block.
- Tests: focus restore, no copy claim when the selection fails, and no copy claim when focus never moves.

### WR-05: The copy status live region is `display:none` until it has text

**Files modified:** `web/src/components/CalloutCard.svelte`
**Commit:** 1dc1403
**Applied fix:**
- The `role="status"` element is always rendered. While empty it uses the global `visually-hidden` class rather than `display:none`, and the card is `position: relative` so the hidden status stays inside it.
- `copy()` resets the result to idle and awaits `tick()` before setting the new message, so a repeat click is announced again.
- In the manual case, focus moves to the readonly link field.

### WR-06: PinButton combines `aria-pressed` with a label that flips between Pin and Unpin

**Files modified:** `web/src/components/PinButton.svelte`
**Commit:** d089548
**Applied fix:** The button has the stable label `aria-label="My team: {name}"`, and `aria-pressed` alone carries the state. The team name is kept because every board row has its own pin button.

### WR-07: CalloutCards on the team page breaks the heading hierarchy

**Files modified:** `web/src/components/CalloutCards.svelte`, `web/src/components/CalloutCard.svelte`, `web/src/components/TeamPage.svelte`
**Commit:** 65d98e0
**Applied fix:**
- CalloutCards takes a `level` prop: 2 by default on the board, 3 on the team page. It renders the section heading at that level with `<svelte:element>` and uses `aria-labelledby` with a `$props.id()` id instead of `aria-label`.
- Each card headline renders at `level + 1`, so h3 on the board and h4 on the team page.
- Each headline starts with a visually hidden "{team name}: ", so heading navigation can tell repeated headlines apart.

### WR-08: Team-season extremes include the in-progress season

**Files modified:** `pipeline/src/fgs/records.py`, `pipeline/tests/test_records.py`
**Commit:** 1d067d5
**Applied fix:**
- New `in_progress_seasons(games)`: a season counts as in progress while any of its REG games is unplayed.
- `team_season_extremes` takes `exclude_seasons`, and `build_records` passes the in-progress seasons. A partial season therefore never competes in "Saddest/Happiest fanbases ever" until its last REG game is played.
- The RECORDS_CHECK rules text says so. The records page footnote says so too, in commit 498b02b.
- Tests: a unit test, plus a real-data assertion that no in-progress season appears.

### WR-09: `as_of` is a UTC date, but snapshot dates are US-local gamedays

**Files modified:** `pipeline/src/fgs/export.py`, `pipeline/tests/test_export.py`
**Commit:** 2a31ed4
**Applied fix:**
- New `as_of_date(generated_at)` converts the timestamp to `America/New_York` with `zoneinfo`, treating a naive timestamp as UTC.
- `build_export` uses it for the streak and records `as_of`.
- Test: an export at 03:30 UTC (after Monday Night Football) gets the previous ET date.

### WR-10: Top nav wraps badly at 320–375px

**Files modified:** `web/src/components/SiteHeader.svelte`, `web/src/lib/sep.test.ts`
**Commit:** ea5b0db
**Applied fix:**
- Each `<Sep />` is grouped with the link after it inside a `span.item` (`inline-flex`, `white-space: nowrap`), so a wrapped line begins with "· Link" and never ends with a stray dot.
- The nav `gap` is now 0, leaving the Sep's own `margin-inline` as the only horizontal spacing. Separators still come only from `Sep.svelte`.
- New sep test: exactly 3 Seps in the nav, each inside an item directly before an `<a`, none directly after a link, and `.item` is nowrap. All existing sep tests still pass.
- Checked visually at 320, 360 and 375px.

### IN-01: Stale comment in App

**Files modified:** `web/src/App.svelte`
**Commit:** a0d9c88
**Applied fix:** Replaced the stale "08-05 replaces null…" comment with one describing what the code does now.

### IN-02: RecordsPage footnote hard-codes the excluded seasons

**Files modified:** `web/src/components/RecordsPage.svelte`
**Commit:** 498b02b
**Applied fix:**
- The footnote sentence is now built from `records.excluded`, using team names, a correct list join and is/are agreement, and is rendered as `{excludedText}`.
- Added the WR-08 note: a season in progress joins the extremes lists once its regular season ends.

### IN-03: `streakStripe` assumes exactly 7 bands

**Files modified:** `web/src/components/RecordsPage.svelte`
**Commit:** fa538b4
**Applied fix:** `var(--mood-${moodToken(kind === 'misery' ? 0 : n - 1, n)})`, the same mapping `scoreStripe` uses.

### IN-04: Unused `check_path` in `_cmd_refresh`

**Files modified:** `pipeline/src/fgs/cli.py`
**Commit:** 0ff4192
**Applied fix:** Refresh now writes RECORDS_CHECK.md after `marker.unlink()`, so a failure there cannot leave an "incomplete refresh" marker behind. It also prints the hand-check path, as `fgs export` already does.

### IN-05: The "My team" highlight is a 6% tint, not the "accent outline" from CONTEXT

**Files modified:** `web/src/components/BoardRow.svelte`, `web/src/components/RecordsPage.svelte`
**Commit:** a99cefb
**Applied fix:** `.mine .row` gets `outline: 2px solid var(--accent); outline-offset: -2px`, keeping the tint. The rule is declared before `.row:focus-visible`, so the keyboard focus ring still wins.

### IN-06: RECORDS_CHECK.md is rewritten with the date on every export

**Files modified:** `pipeline/src/fgs/records.py`, `pipeline/src/fgs/cli.py`, `pipeline/tests/test_records.py`
**Commit:** 4b1960c
**Applied fix:**
- New `records_check_key(records)`: a hash of `records.json` with `as_of` and the active-streak day counts blanked. It is embedded in the file as `<!-- records-check-key: … -->`.
- `_write_records_check` skips the write when the existing file carries the same key, then returns `(path, written)`. The CLI prints either "written" or "unchanged".
- Test: a new date alone produces the same key and leaves the file byte-identical; a real records change rewrites it.

### IN-07: Active streak days freeze at export time with no "as of" on the team page

**Files modified:** `web/src/components/TeamPage.svelte`
**Commit:** 39ae751 (fixed together with WR-01)
**Applied fix:** The team-page streak line appends "(as of {formatDate(records.as_of)})".

### Data regeneration

**Files modified:** `pipeline/RECORDS_CHECK.md`, `web/public/data/callouts.json`, `web/public/data/meta.json`, `web/public/data/snapshots/*.json`
**Commit:** 90eceb6
**Applied fix:** Output of `uv run fgs export` after all fixes. The streak card details now carry "as of …", and the latest week counts through the export date. RECORDS_CHECK.md carries its key. `records.json` did not change, because no 2026 entry was in the top 10.

## Notes for the developer

- WR-02 makes the export stricter on purpose. Any change to the hashed modules, to the Elo params or HFA eras, or to the 1999–2021 data now requires `uv run fgs evidence` and a commit of `callout_evidence.json`. Doc-only edits and callout-copy edits do not.
- WR-01, WR-08 and IN-06 change logic. They have tests, but are worth a quick human look:
  - WR-01: which date each streak card counts through;
  - WR-08: what counts as an in-progress season;
  - IN-06: which fields the records key ignores.

---

_Fixed: 2026-11-11T23:50:05Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

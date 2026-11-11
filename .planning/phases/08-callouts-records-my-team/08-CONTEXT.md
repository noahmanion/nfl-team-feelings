# Phase 8: Callouts, Records & My Team - Context

**Gathered:** 2026-11-11
**Status:** Ready for planning (research REQUIRED for perception-gap baseline)
**Mode:** Autonomous — recommended answers auto-accepted (user granted full autonomy)

<domain>
## Phase Boundary

Ship the shareable "aha" layer: perception-gap callouts, biggest movers, calendar-day misery/joy streaks, historical extremes (records page), and a remembered "my team" pin that highlights across views. All computed in the pipeline (callouts.json etc.); frontend renders.

</domain>

<decisions>
## Implementation Decisions

### Perception-gap callouts (INSIGHT-02, SITE-09)
- Record-implied rank = rank by REG win% to date (ties → point differential → franchise id). Gap = record_rank − score_rank. Flag when week ≥ 4 and |gap| ≥ 8 (research may tune threshold to yield ~2–5 callouts/week on average).
- Two flavors: record better than score → "{W-L} but you should feel worried"; score better than record → "{W-L}, but better days are coming". Include a base-rate evidence line computed on training seasons 1999–2021 only: e.g. "Teams with a gap this big went on to average {x} pts/game worse than their record peers over the next 8 games ({n} cases since 1999)." Research defines the peer comparison.
- callouts.json: [{type: "worried"|"hopeful"|"mover_up"|"mover_down"|"misery"|"joy", season, week, franchise, headline, detail, evidence?}]; current-week callouts shown on board (top card strip) and the team's own callouts on its team page. Past weeks: callouts per season file rows (`callouts` key) or a season-keyed callouts file — planner decides; scrubbing the board to a past week shows that week's callouts.
- Callout card: team chip, headline (big), detail, link to team page; a "Copy link" button copies the deep link (navigator.clipboard with try/catch fallback). No share images (v2).

### Movers (INSIGHT-06, SITE-05)
- Top 3 risers and top 3 fallers by score_delta for the displayed week (week ≥ 1), shown as a compact strip above the board.

### Streaks in calendar days (INSIGHT-03)
- Each snapshot gets a date: week ≥ 1 → last gameday of that week; week 0 → draft date (or Sept 1 if unknown). A team's mood on each calendar day = its latest snapshot as of that day. Misery = consecutive days with score < 20 ("Refreshing mock drafts" or worse); joy = consecutive days with score ≥ 80. Current active streak shown on team page ("Miserable for 612 straight days"); records page lists the 10 longest ever (and flags active ones).

### Historical extremes (INSIGHT-04, SITE-06)
- Saddest/happiest fanbases ever: one entry per team-season (its min / max score and when), top 10 each; plus longest misery/joy streaks top 10. Route `#/records`, nav "Records".
- Hand-check: pipeline writes `pipeline/RECORDS_CHECK.md` listing the top-10 lists with season records and a sanity note per row (verifier/orchestrator checks them against known history, e.g. 2008 Lions 0-16, 2007 Patriots 16-0).

### My team (SITE-08)
- Pin button (☆/★ "My team") on team page header and each board row; stored in localStorage `fgs.myTeam` with try/catch (works without storage). Pinned team: highlighted row on board (accent outline + "My team" tag, kept in place — not moved to top, plus a "Jump to my team" link), default highlighted team on mood-over-time chart (unless hash specifies), highlighted entries on records page, and its callouts first in the strip. Unpin available.

### Claude's Discretion
- Card layout, strip design, threshold tuning per research, records page table design (follow 02-UI-SPEC later-phase rules for callout cards, my-team pin, movers strip).

</decisions>

<code_context>
## Existing Code Insights

- callouts.json exists as `[]` placeholder (PIPE-02); router reserves `#/records`; SiteHeader nav; BoardRow/MoodBoard/TeamPage/HistoryPage components; export snapshot rows with score_delta/rank_delta, points, blurb; history.json for chart.

</code_context>

<specifics>
## Specific Ideas

- The screenshot moments the user wants: "8-2 but you should feel worried", "Jets fans have been miserable for 600 straight days", "saddest fanbase ever".

</specifics>

<deferred>
## Deferred Ideas

- OG share images (v2), accounts/sync (out of scope).

</deferred>

<research_revisions>
## Accepted research revisions (08-RESEARCH, autonomous approval 2026-11-11)
- ALL assumptions in 08-RESEARCH's Assumptions Log are accepted as recommended, including: expansion team-seasons (CLE 1999, HOU 2002) excluded from extremes and their seeded week-0 rows from streaks; |gap| ≥ 8 with cap 3 per flavor per week, REG weeks 4..second-to-last only; peers = same W-L-T at same week (1999–2021); evidence via dev-only `fgs evidence` → committed `pipeline/callout_evidence.json` (export reads it, fails if stale); hard-coded draft-date table for week-0 dates; tiebreak for extremes (min/max score → season-avg REG score → composite); past-week callouts in season files' `callouts` key, `callouts.json` = latest week; active-streak "as of" = export date.
</research_revisions>

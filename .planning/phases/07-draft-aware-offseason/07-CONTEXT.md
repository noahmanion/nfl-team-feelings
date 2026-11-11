# Phase 7: Draft-Aware Offseason - Context

**Gathered:** 2026-11-11
**Status:** Ready for planning (research REQUIRED — flagged in ROADMAP)
**Mode:** Autonomous — recommended answers auto-accepted (user granted full autonomy)

<domain>
## Phase Boundary

Load draft picks + a draft-value chart for 1999→present and add an offseason draft adjustment to the week-0 (post-draft) snapshot that rewards draft capital ABOVE what a team's original slot would yield (capped) — never rewarding tanking. Make offseason movement visible on the chart and board. The Phase 6 frozen in-season weights are NOT changed.

</domain>

<decisions>
## Implementation Decisions

### Data (DATA-06)
- `nflreadpy.load_draft_picks()` (PFR-style codes — map GNB/KAN/LVR/SDG/etc. through an explicit PFR→franchise map, assert full coverage) cached as parquet; nflverse `draft_values.csv` for the chart (columns include stuart/otc/johnson/hill). Chart choice: the flatter of stuart/otc per research (default `stuart`, AV-based).
- Original draft order per season derived from the reverse of the prior season's final standings with playoff adjustments as recorded — research decides the cleanest source (e.g. round-1 pick numbers by team in nflverse with trades flagged, or compute from prior standings).

### Draft surplus (MODEL-16)
- surplus = Σ chart value of picks actually used by the team in that draft − Σ chart value of the picks the team would have had at its ORIGINAL slot in each of the 7 rounds (compensatory picks excluded from both sides). This measures capital gained/lost by trades, NOT draft position — the worst team holding #1 has surplus ≈ 0 (acceptance test: for every season, the team with the #1 original slot that didn't trade gets surplus 0 ± ε; tanking never helps).
- Cap: surplus winsorized at the 5th/95th percentile of the 1999–2021 distribution, then z-scored across teams for that draft.
- Applied as a separate offseason term `draft` in the week-0 snapshot only (decaying linearly to 0 by week 4 — research may choose decay). Its weight is fit on training seasons only (week-0..4 snapshots of 1999–2021, N=8 adjusted-margin target), added ON TOP of the frozen in-season composite (frozen weights untouched; `weights.yaml` gets a separate `offseason.draft` entry). Report fitted weight, Δ on the week-0 bucket, and fold-sign consistency in BACKTEST_LOG.
- If no signal (Δ ≤ 0 or fold-sign consistency < 60%), weight = 0 and the draft shows as display-only text on the team page ("Draft haul: +X over slot — doesn't move the score"). Either way surplus is exported per team-season.
- No fresh holdout exists (Phase 6 consumed it) — methodology notes the draft term's evidence is training-only walk-forward.

### Offseason visibility
- Mood-over-time chart: instead of a blank gap between seasons, draw a dashed "offseason" connector from the last snapshot of season S to week 0 of S+1 (still visually distinct = a break), so regression + draft movement is visible. Week 0 tooltip/label "Preseason (after draft)".
- Board at week 0: weekly change column shows change vs prior season's final snapshot (labelled "vs end of last season").
- Team page at week 0: blurb lead mentions draft surplus when non-trivial; factor bars include `draft` if weight ≠ 0.

### Claude's Discretion
- Decay schedule, module layout (`draft.py`), exact PFR mapping source, chart styling of dashed connector.

</decisions>

<code_context>
## Existing Code Insights

- Week-0 snapshots exist (post-regression); `explain.py` week-0 leads; history chart `toRows` inserts NaN gaps at season boundaries (change to dashed connector); export `score_delta` at week 0 currently "–".

</code_context>

<specifics>
## Specific Ideas

- Good illustration cases: teams that traded up aggressively (e.g. multiple firsts) should show positive surplus; teams that traded future firsts away negative.

</specifics>

<deferred>
## Deferred Ideas

- Free agency reaction (v2); grading drafted players' actual performance (needs post-draft outcomes — not knowable at draft time).

</deferred>

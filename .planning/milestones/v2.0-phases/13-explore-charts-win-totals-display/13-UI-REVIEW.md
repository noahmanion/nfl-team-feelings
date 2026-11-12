---
phase: 13
slug: explore-charts-win-totals-display
audited: 2026-11-12
baseline: 13-UI-SPEC.md
overall_score: 19/24
screenshots: existing 6 viewed (no new captures)
fixes_applied: [1, 2, 3, 4, 5]
---

# Phase 13 — UI Review (advisory)

Six-pillar audit against `13-UI-SPEC.md`. The six screenshots in `screenshots/` were each viewed (explore 1280 light, explore 2025/10 1280 dark, explore 375 dark, team 2015 1280 dark, team 2023 375 light, team 2026 1280 light). The auditor also read ExplorePage, EpaScatter, RecordScatter, ExploreTable, WinTotals, scatterMarks.ts, and grepped TeamPage, CalloutCards, RecordsPage, BoardRow and Delta. No new screenshots were written, and the `.planning/ui-reviews/.gitignore` gate was ensured.

## Scores

| Pillar | Score | Key finding |
|---|---|---|
| 1. Copywriting | 3/4 | Spec strings match nearly exactly (deks, notes, quadrant/zone labels, WinTotals deks/legends). The record notes say "Shaded bands are the mood labels", but below 640px no band labels are drawn, so the sentence is false on mobile. EPA notes also add an unspec'd "Regular season only." |
| 2. Visuals | 3/4 | Both scatters read well at 1280, with clear diagonals, crosshairs and quadrant labels, and the WinTotals number line is clean. Defects: the "Typical score for this record" label collides with the densest cluster of logos, and 375px charts are overplotted. |
| 3. Color | 3/4 | No hex literals and no accent on marks. The semantic split is respected (grid, muted dashes, mood bands). The dark disc treatment turns 32 bright white blobs on `#141414` into the loudest element on the page, and the logos inside shrink to 0.76. The pin ring/dim was not verified, because no screenshot had a team pinned. |
| 4. Typography | 4/4 | No font-size literals in any new file. Only 12/14/16/20 tokens and Inter/Plex Mono at the allowed weights. The number formats (signed, U+2212, tabular mono) are visible in the screenshots. |
| 5. Spacing | 3/4 | Token usage is clean. Problems are all inside Plot: the 375px x-axis ticks nearly touch, the three win-totals markers sit within about 10px of each other at 375, and the team page right column is still short beside the tall factor column. |
| 6. Experience Design | 3/4 | Loading, empty and error states, the table alternative, silent route fallback and the touch-arm tap are all implemented. There is no overplot mitigation and no label on the mood bands for touch users. |

**Overall: 19/24** (Phase 12 was 17/24.)

## Top fixes

| # | Severity / cost | Issue | Fix |
|---|---|---|---|
| 1 | WARNING (high) / cheap | The OLS label "Typical score for this record" sits at the line's right end, which is where the highest-scoring teams cluster (80–100). In light it is partly hidden behind logos at 1280. In dark the haloed text paints over a pile of white discs. It is hard to read in both modes. | In `RecordScatter.svelte`, move the label to the left/bottom end of the line (`textAnchor: 'start'`, at x0,y0 with `dy: +16`). Or anchor it at the line's midpoint on the lower-right side, away from the top-right cluster. Or draw it before the logos. One-line change. |
| 2 | WARNING (high) / cheap | The note "Shaded bands are the mood labels" is false below 640px, where no band labels are drawn. Mobile users see unlabeled coloured stripes. The tooltip is touch-only and needs a tap. | At `<640`, either drop that sentence from `RVE_NOTES`, or draw short band labels inside the plot (right-aligned mono 12, `frameAnchor: 'right'`, `dx: -4`, no gutter) at 375. Dropping the sentence is cheapest (`ExplorePage.svelte` RVE_NOTES, via `width < 640`). |
| 3 | WARNING (med) / cheap | At 375px the EPA x-axis ticks `−0.30 −0.20 −0.10 0.00 +0.10 +0.20` are nearly touching (6 ticks in about 280px). The spec's "never more than 6" is met in letter but not in legibility. | In `epaTicks` use at most 4–5 ticks below 400px (drop to every 0.2 for the x axis), or shrink the left margin from 48 to 40 on mobile. |
| 4 | WARNING (med) / cheap | 32 20px logos in a 280×320 plot overlap heavily around the league mean, so the center of the mobile EPA chart is unreadable. | Raise the mobile chart height floor from 320 to about 400 (`chartHeight` for width <400), or use size 18 below 400px. The tooltip and table still carry the data. |
| 5 | WARNING (med) / cheap | In WinTotals, when the Vegas line, the model value and the pace/final are within about 0.5 wins (2023: 10.5, 10.8, 11; 2026: 10.5, 10.3), the three markers stack: the tick runs through the ring, and the glyphs are indistinguishable at 375. | Offset the ring down by about 6px when it is within 0.7 wins of the Vegas tick (`top: 18px` on `.ring`), or put the model ring on its own row beneath the track. The legend still explains it, so this is cosmetic. |
| 6 | low / cheap | The dark-mode discs at `#f2f2f2` are the strongest visual element, so logos are small inside bright circles. | Soften `--logo-disc` in the dark chart to about `#d9d9d9`, or keep the disc smaller (`size/2 + 1`). Alternatively accept it as the Phase 12 decision. |
| 7 | low / cheap | The EPA notes include "Regular season only." and the Scrubber ends "Wk 18 · SB" on 2025. Both are accurate, but "Regular season only" was not in the spec. | Fine to keep, but update the UI-SPEC copy table. |
| 8 | low / moderate | The team page at 1280 is still lopsided (the right column ends around y=1500 while the left runs to y=1830). The 2015 page is worse, because the expectation block is the only new content. This was Phase 12 #6, partly mitigated by WinTotals. | Make the right column `position: sticky`, or move "This season" up. |

## Detailed findings

### Pillar 1: Copywriting (3/4)
- Matches the spec in the screenshots: the page dek, EPA headline/dek, the "Record vs evidence" dek (the generated line renders as "The Texans look better than their 3–5 record; the Browns look worse than theirs."), the SOURCE/NOTES footers, the quadrant/zone labels, "Show as table", and the WinTotals deks ("Vegas set the line at 8.5 wins. They finished with 8.", "They're on pace for 14.9.") and legends including the opening-line suffix.
- `ExplorePage.svelte` (RVE_NOTES): "Shaded bands are the mood labels." is not true under 640px (RecordScatter only draws band labels at ≥640 via `LABEL_MIN_WIDTH`). This is a copy and behavior mismatch visible in `explore-375-dark.png`.
- `ExplorePage.svelte` (EPA_NOTES): added "Regular season only." The spec has no such sentence. It is harmless and arguably helpful.
- No "lucky/luck" in the Explore files (the no-luck test guards it). The team-page factor "Close-game luck" predates this phase and is out of scope.
- Not verified: the tooltip strings (hover is not in the static screenshots). They are covered by unit tests.

### Pillar 2: Visuals (3/4)
- 1280 light/dark: the focal structure holds. Diagonals (`--grid`) give tier structure, the dashed crosshairs split the quadrants, and the logos carry the data. The record chart's mood bands plus right-gutter labels follow the HistoryChart language well.
- The OLS label collides with logos (`RecordScatter.svelte`, `lineLabel` pushed last at `x2,y2, dy −8`). Fix #1.
- 375 dark: the zone labels "BETTER THAN THEIR RECORD" and "WORSE THAN THEIR RECORD" sit over the y=100 gridline and over logos. They are shown at all widths per spec, but "BETTER…" overlaps the top-right cluster's neighbours at 375. The mobile EPA chart is a dense knot around the origin (fix #4).
- The WinTotals number line is clear on 1280 (2015: Vegas bar and pace dot distinct; 2026: ring and tick overlap slightly, fix #5). The ring/tick/dot encoding plus legend is readable. The tick labels `0 4 8 12 17` are correct.
- Dark discs: functional and legible, but heavy (fix #6).
- No pinned-team screenshot exists, so the ring and 0.5 dim of others were not seen. The code (`scatterMarks.ts`) follows the spec.

### Pillar 3: Color (3/4)
- No hardcoded colors in ExplorePage, EpaScatter, RecordScatter, ExploreTable or WinTotals. Everything uses tokens (`--grid`, `--text-muted`, `--mood-n`, `--logo-disc`, `--accent` only on focus, links and the my-team row).
- Accent usage stays inside the reserved list. On the Explore page the only accent is the nav underline, the Scrubber, and table links and focus.
- The pace dot uses `highlightColor`, so JAX-style low-contrast teams keep 3:1 in dark (Bills navy/red look correct in the 2015 and 2026 screenshots).
- Light mode gives the page about 95% neutral, with the logos supplying the colour, which is on-contract.
- Concern: the white disc blobs in dark mode (fix #6).

### Pillar 4: Typography (4/4)
- Grep finds no `font-size: <n>` literals and no off-scale weights in the new components. Plot text uses `CHART_FONT_PX`. Tables use mono tabular numbers, a micro uppercase header and semibold rank.
- Screenshots confirm the 20/700 headlines, 16 muted deks, 12 mono axes, and signed U+2212 ticks (`−0.20`, `+0.10`).
- Minor: the 12px mono tick text is at its minimum at 375, which is the cause of fix #3. It is not a type-scale violation.

### Pillar 5: Spacing (3/4)
- The layout spacing follows tokens (xs/sm/md/lg/xl). The Explore frame gaps (Scrubber → first chart 24, section rule + 32) match the screenshots. The only raw px values are the declared WinTotals graphic sizes and the table's minimum height.
- 375: the x tick row is cramped (fix #3). The three win-totals markers can overlap (fix #5). The team page's right column is still short (fix #8).
- The 375 layout has no horizontal scroll visible in the screenshots, and the charts are clipped inside `overflow: hidden`.

### Pillar 6: Experience Design (3/4)
- States covered in code: the snapshot error panel replaces both frames, the EPA file error is local to the EPA frame, loading placeholders keep the chart height, there are empty variants (week 0, season without pbp, no data yet), a silent route fallback, and a `<details>` table for every chart (SVGs are `role=img` with a summary aria-label, `tabindex=-1`). Table links carry accent focus.
- The mobile tap is armed (first tap shows the tip, second navigates), which avoids accidental navigations.
- Gaps: there is no overplot handling (no jitter, no label collision avoidance), mobile has no band legend, and the WinTotals section is silently omitted on `loadTeam` failure (per spec). The 375 nav wraps "How it works" onto a second line, which is Phase 12 behavior.
- Not verified (no screenshots): Explore week 0 empty state, the pinned team (ring, dim, table row tint), error panels, keyboard focus rings and reduced motion. Also not seen visually: Phase 12 leftovers #4 (Records subgrid), #7 (History logo clip), #8 (rank delta text) and #9 (callout stretch). The code for each (RecordsPage subgrid/`--score-cell`, `Delta kind="rank"`, flex/`margin-top: auto`) is present, but the pixel results were not seen.

## Files Audited
- `web/src/components/ExplorePage.svelte`, `EpaScatter.svelte`, `RecordScatter.svelte`, `ExploreTable.svelte`, `WinTotals.svelte`
- `web/src/lib/scatterMarks.ts`
- `web/src/components/TeamPage.svelte` (WinTotals wiring, grep), `Delta.svelte`, `BoardRow.svelte`, `RecordsPage.svelte`, `CalloutCards.svelte`, `CalloutCard.svelte` (grep)
- `.planning/phases/13-explore-charts-win-totals-display/screenshots/*.png` (6)

## Fixes applied (orchestrator, 054153c)

Fixes 1 to 5 were applied in one commit. I re-checked them with Playwright MCP: the 375px dark explore page and the BUF 2023 win-totals block. The gates pass: 277 tests, check clean, build OK.
- #1: the "Typical score for this record" label is now an HTML key with a dashed swatch above the chart, so no in-plot label can collide with logos.
- #2: the notes now say "Shaded bands are the board’s mood bands.", which is true at every width. The UI-SPEC copy row is updated.
- #3/#4: below 400px there are at most 5 EPA ticks (3 are shown at 375), and the chart height floor is 380.
- #5: WinTotals nudges the model ring up and the pace dot down when they sit within about 0.5 wins of another marker.
- #6, #7, #8 are left as is. #6 is the Phase 12 disc decision, #7 keeps "Regular season only." on purpose (RESEARCH resolution 1), and #8 is Phase 12 #6, still deferred.

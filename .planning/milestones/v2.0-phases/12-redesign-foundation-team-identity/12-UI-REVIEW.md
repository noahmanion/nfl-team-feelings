---
phase: 12
slug: redesign-foundation-team-identity
audited: 2026-11-11
baseline: 12-UI-SPEC.md
overall_score: 17/24
fixes_applied: [1, 2, 3]
---

# Phase 12 — UI Review (advisory)

Six-pillar audit by gsd-ui-auditor against `12-UI-SPEC.md`, using the 24 screenshots in `screenshots/` (9 viewed directly by the auditor: board 1280 light / 375 dark, team-era 1280 light, team-current 375 light, history 1280 dark / 375 light, records 1280 light, methodology 1280 light). The orchestrator wrote this file from the auditor's report, because the auditor did not write it.

## Scores

| Pillar | Score | Key finding |
|---|---|---|
| Copywriting | 3/4 | Spec strings are implemented exactly: chart headlines, deks, the SOURCE/NOTES footer, the relocation note and the disclaimer. The rank-delta glyph `#▲1` is cryptic. |
| Visuals | 2/4 | The editorial look lands, but the dark history chart lost its team color, mood labels truncated at 375px, and records rows are narrower than the page frame. |
| Color | 3/4 | No hardcoded hex in components, and the shaded cells and 60/30/10 split work. The issues are the highlight fallback and the saturated bands. |
| Typography | 3/4 | No font-size literals. Inter and Plex Mono render as specified. The Methodology "numbers" section is a dense wall of mono text. |
| Spacing | 3/4 | Rule-and-whitespace sections are consistent. The team page at 1280 leaves a tall empty right column, and records widths are ragged. |
| Experience Design | 3/4 | All states and the logo fallback are preserved. The 375px board is long before the first row, and wrapped nav lines started with "·". |

## Top fixes

| # | Severity / cost | Issue | Status |
|---|---|---|---|
| 1 | high / moderate | Dark-mode history highlight fell back to white for low-contrast teams (JAX etc.), which made the dek "in color" untrue | **Fixed** dc07433 (`highlightColor` tints the team color until it reaches 3:1) |
| 2 | high / cheap | Mood labels truncated at 375px on the board ("Planning…") | **Fixed** 9557392 (wraps below 1024px) |
| 3 | medium / cheap | Wrapped nav lines start with "·" at 375px (site nav, team week nav) | **Fixed** 533bbda (dots hidden below 640px, gap spacing) |
| 4 | medium / cheap | Records rows stop at about 840px inside the 960px frame; streak cell widths are ragged | Deferred |
| 5 | medium / cheap | Saddest/happiest lists show 10 identical 0/100 cells; lead with the season average | Deferred |
| 6 | medium / cheap | Team page at 1280 is unbalanced (tall factor column next to a short right column) | Deferred |
| 7 | low / cheap | History end-mark logo at y=100 can clip the plot top at 375px | Deferred |
| 8 | low / cheap | Rank-delta `#▲1` / `#–` is cryptic | Deferred |
| 9 | low / cheap | Callout action rows are uneven at 1280 | Deferred |
| 10 | low / cheap | Six callouts push the first board row past 1,500px at 375px | Deferred |
| 11 | low / moderate | The Methodology page is a very long column, and the "numbers" section could be a table | Deferred |

## Not verified

- Dark-mode contrast and layout on the records, methodology and team pages, which the auditor did not view directly. The Playwright sweep did confirm no horizontal scroll in light and dark at 375px.
- Reduced motion and keyboard focus rings (screenshots are static).

After the fixes, `verify_ui.py` was re-run: ALL PASS, and the screenshots were refreshed (7d62fda).

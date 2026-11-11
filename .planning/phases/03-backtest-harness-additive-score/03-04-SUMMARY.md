---
phase: 03-backtest-harness-additive-score
plan: 04
subsystem: web
tags: [svelte, observable-plot, chart, router, SITE-03]
requires: [web/public/data/history.json, meta.json, latest.json]
provides: ["#/history route", "HistoryChart", "HistoryPage", "top nav", "history.ts helpers", "loadHistory"]
affects: [web/src/App.svelte, web/src/components/SiteHeader.svelte]
tech-stack:
  added: ["@observablehq/plot 0.6.19 (exact pin)"]
  patterns: ["Plot.line z:'team' + NaN rows for season breaks", "runtime WCAG contrast pick for highlight colour"]
key-files:
  created:
    - web/src/lib/history.ts
    - web/src/lib/history.test.ts
    - web/src/components/HistoryChart.svelte
    - web/src/components/HistoryPage.svelte
  modified:
    - web/package.json
    - web/package-lock.json
    - web/src/lib/router.ts
    - web/src/lib/router.test.ts
    - web/src/lib/types.ts
    - web/src/lib/data.ts
    - web/src/components/SiteHeader.svelte
    - web/src/App.svelte
decisions:
  - "pickHighlight parses hex only (trimmed #rgb/#rrggbb); an unparsable --bg falls back to the known light/dark --bg constant chosen by prefers-color-scheme, and unparsable team colours count as failing (so the fallback chain ends at var(--text) rather than silently passing)"
  - "Band stripes use moodToken(i, n) to map meta.bands onto --mood-0..6, matching the board"
  - "Narrow-screen season ticks render as two-digit ('08) labels; highlight label flips to the left of the last point when it falls in the final 5% of x"
metrics:
  duration: ~8min
  completed: 2026-11-11
  tasks: 2
  files: 12
---

# Phase 3 Plan 04: Mood-over-time chart Summary

You can now open `#/history` and see an Observable Plot chart of every team's score since 1999. The y-axis is fixed at 0–100. One team is highlighted in its contrast-checked team colour and labelled with its abbreviation. Lines break at each season boundary, where a dashed rule is drawn, and the mood bands show as faint stripes. A visible summary line gives the team's current score and its all-time low. The page can be reached from a new top nav, or by deep link with `#/history/{ABBR}`.

## Tasks

| # | Task | Commit |
|---|------|--------|
| 1 | Install Plot, history route, pure chart helpers + tests | ce5ddb9 |
| 2 | HistoryChart, HistoryPage, SiteHeader nav, App routing | ca51b94 |

## What was built

- **Package check:** `npm view` showed the repository is `github.com/observablehq/plot` and there is no postinstall script. The package was then installed exactly pinned at `0.6.19` under `dependencies`.
- **router.ts:** adds `{kind:'history', team?}`. `#/history`, `#/history/buf` and `#/history/BUF/` all parse, with the team uppercased. `TOOLONG` and `B1` are invalid. `history` was removed from RESERVED, and `historyHash()` was added.
- **history.ts:** pure helpers `toRows`, `seasonStarts`, `tickSeasons`, `parseHex`, `relLuminance`, `contrastRatio`, `pickHighlight`, `lowPoint`, `currentPoint`, `defaultTeam`, `seasonOf` and `weekOf`. 14 new vitest cases cover them, including the unparsable-value fallbacks.
- **data.ts:** `loadHistory(meta)` caches one promise per session (cache-busted by `generated_at`) and evicts it if the fetch fails.
- **types.ts:** adds `HistoryFile` and `FactorMeta`, plus optional `Meta.factors` and `Row.contribs`. Both are backwards compatible.
- **HistoryChart.svelte:** chart width comes from `bind:clientWidth`. Height is 400px at 500px wide and up, 280px below. It draws, in order: band rects at 10% opacity (14% in dark mode), band labels at the right edge on wide screens only, dashed season rules, all-team lines (`--text-muted`, 25% opacity, 1px), the highlighted line at 2.5px, and the abbreviation label. The svg has `role="img"` and an aria-label.
- **HistoryPage.svelte:** a native select labelled "Highlight team" lists teams by name and sorts them alphabetically. It defaults to the current #1 (`latestRows[0]`). An unknown deep-linked team is replaced with `#/history`. It has loading text and an error StatusPanel with "Try again". The summary line reads "{Team} now {score} · {label}; low {min} ({season} {week label})".
- **SiteHeader / App:** nav "Board · Mood over time" with `aria-current="page"` and a 2px `--accent` underline on the active link, and a 44px minimum tap height. App renders HistoryPage on the history route once data has loaded. Loading and fatal error states are shared with the board.

## Verification

- `npm test`: 43 passed.
- `npm run check`: 0 errors, 0 warnings.
- `npm run build`: OK.
- Acceptance greps all match (`z: 'team'`, `domain: [0, 100]`, `aria-current`, `kind === 'history'`). There are no raw hex colours in `History*.svelte`.
- The real history.json has 609 keys and 32 teams, and its teams match `meta.teams` exactly.
- Browser checks at 375px and 1280px, in dark mode, and for `#/history/XYZ` are left to the orchestrator. No browser was run here.

## Deviations from Plan

**1. [Rule 2 - Correctness] Hardened pickHighlight against non-hex values** (this was an orchestrator note on the plan-checker)
- Before, a non-hex `--bg` or team colour could make the contrast check fail silently: comparisons with NaN would decide the result.
- Now `parseHex` trims and accepts `#rgb` or `#rrggbb` only. An unparsable background falls back to `FALLBACK_BG.light` or `FALLBACK_BG.dark`, picked by `prefers-color-scheme`. These constants mirror `--bg` in app.css. An unparsable team colour is treated as failing the check. All of this is tested.
- Commit: ce5ddb9

**2. Minor additions**
- `parseHex` is exported.
- `ruleY([0])` draws a baseline in `--border`.
- Axis tick strokes are restyled to `--border` with scoped CSS.
- The highlight label moves above and to the left when it sits near the right edge, so it is not clipped.

app.css was not changed: no new tokens were needed.

## Known Stubs

None.

## Notes

- Plot and d3 bring the main bundle to about 341 kB (117 kB gzip). If the size matters, HistoryPage could be loaded with a dynamic import later. That optimisation was not in this plan.

## Self-Check: PASSED

- All files listed in key-files exist; commits ce5ddb9 and ca51b94 are present in git log.

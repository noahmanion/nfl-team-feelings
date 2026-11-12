---
phase: 14-share-cards-launch-verification
plan: 02
subsystem: web/share
tags: [share, og, satori, resvg, tdd]
requires: [format.ts bandIndex/moodToken, app.css light tokens, @fontsource inter + ibm-plex-mono WOFF]
provides: [web/scripts/og-template.mjs card renderer for share.mjs (14-03)]
affects: [web/package.json, web/package-lock.json]
tech-stack:
  added: [satori 0.63.2, "@resvg/resvg-js 2.6.2"]
  patterns: [satori element trees via h() helper (no JSX), fail-loud glyph guard via loadAdditionalAsset, gc + yield every 25 renders]
key-files:
  created: [web/scripts/og-template.mjs, web/scripts/og-template.test.mjs]
  modified: [web/package.json, web/package-lock.json]
decisions:
  - "An automated identity gate (repo URL + no postinstall) replaced the human package checkpoint; both checks passed before install"
  - "Bordered or padded card boxes (score cell, mood strip, claim block, chip) use boxSizing border-box, because satori defaulted to content-box and the mood strip overflowed to x=1172"
  - "The main column's top padding is pad − stripe (52), so content starts at y=64 under the 12px stripe as specified"
metrics:
  duration: ~5min
  completed: 2026-11-12
  tasks: 2
  files: 4
---

# Phase 14 Plan 02: Card renderer (satori + resvg) and card templates Summary

`web/scripts/og-template.mjs` renders the team, callout and site share cards. Each is a 1200×630 PNG of 36–68 KB, built from satori trees with exact-pinned satori/resvg-js. Colors are pinned by test to app.css's light `:root`. Fonts are static Inter/Plex Mono 400/700 WOFF. A raw `→` or emoji fails the render with `share: missing glyph U+…`; mover details draw the arrow as an SVG.

## Tasks

| Task | Name | Commits |
|------|------|---------|
| 1 | Pinned deps; CARD tokens, fonts, renderPng + glyph guard, clampText, cardRuns | 98d2511 (chore deps), 20e394c (RED), 062d3bb (GREEN) |
| 2 | teamCard / calloutCard / siteCard with logo/chip fallback | 723ef14 (RED), 6df3d9e (GREEN) |

## Exports (contract for plan 03)

`CARD, FONTS, h, ARROW, KICKER, renderPng(tree, where), renderStats(), clampText, cardRuns, bandColors, logoBox, teamCard(vm), calloutCard(vm), siteCard({ host })`. The view-model field names match the plan's interface block exactly.

## Verification

- Identity gate: satori → `vercel/satori`, resvg-js → `yisibl/resvg-js`, and neither has a postinstall script
- `package.json` pins `"satori": "0.63.2"` and `"@resvg/resvg-js": "2.6.2"` with no caret, and the lockfile has 1 `resvg-js-linux-x64-gnu` entry
- `npx vitest run scripts/`: 33 passed. The full `npx vitest run`: 335 passed. `npm run check`: 0 errors
- Greps: emoji=0, color-mix/var(--)=0, `lineClamp: 2`=4, `loadSystemFonts: false`=1, woff2/variable=0
- Visual check (scratchpad PNGs, not committed): a WAS 2-line name with a score of 100, a BUF chip, an HOU mover with the drawn arrow, a clamped Seahawks headline and detail, and the site card. Everything sits within x 64–1136 / y 64–566, with no tofu and the score right-aligned.

## Deviations from Plan

**1. [Rule 1 - Bug] Content-box overflow in satori**
- **Found during:** Task 2 visual check
- **Issue:** The 1072-wide mood strip and the 352-wide score cell got their 12px border and 24px padding added on top of the declared width. The strip ran to x=1172, past the safe area, and the cell was 388 wide.
- **Fix:** Added `boxSizing: 'border-box'` to the score cell, mood strip, claim block and chip.
- **Files:** web/scripts/og-template.mjs. **Commit:** 6df3d9e

## TDD Gate Compliance

Each task has a `test(14-02)` RED commit before its `feat(14-02)` GREEN commit. Both RED runs failed because `og-template.mjs` or its exports didn't exist yet.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: web/scripts/og-template.mjs, web/scripts/og-template.test.mjs
- FOUND commits: 98d2511, 20e394c, 062d3bb, 723ef14, 6df3d9e

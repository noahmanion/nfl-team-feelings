---
phase: 12-redesign-foundation-team-identity
plan: 01
subsystem: web
tags: [design, typography, fonts, tokens, css]
requires: []
provides:
  - Self-hosted Inter Variable + IBM Plex Mono (exact-pinned Fontsource 5.3.0)
  - Editorial light/dark token set (rule-strong, grid, surface-hover, logo-disc, cell-tint, prose-max, score-cell, text-micro, lh-micro, weight-bold, font-mono)
  - Global .num utility and Plot grid opacity override
  - brand.test.ts guard (font import order, pins, no font CDN, no 538 string)
affects: [all later Phase 12 component plans]
tech-stack:
  added: ["@fontsource-variable/inter@5.3.0", "@fontsource/ibm-plex-mono@5.3.0", "@fontsource/inter@5.3.0 (dev)"]
  patterns: ["Side-effect font CSS imports before app.css", "CSS sources read via node:fs in tests (vitest stubs CSS)"]
key-files:
  created: [web/src/lib/brand.test.ts]
  modified: [web/package.json, web/package-lock.json, web/src/main.ts, web/src/app.css, web/src/lib/history.ts]
decisions:
  - "Brand test reads .css files from disk via node:fs because vitest returns '' for CSS ?raw imports"
metrics:
  duration: ~6min
  completed: 2026-11-11
  tasks: 2
  files: 6
requirements: [DESIGN-01, DESIGN-03, DESIGN-04]
---

# Phase 12 Plan 01: Type and Color Foundation Summary

Self-hosted Inter Variable and IBM Plex Mono via exact-pinned Fontsource 5.3.0, an editorial light/dark token set in app.css with a `.num` tabular-mono utility and solid Plot gridlines, and a brand guard test that blocks font CDNs and 538 strings.

## Tasks

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | Install fonts, import in main.ts, brand guard test | d5fe20e |
| 2 | Editorial tokens, .num, Plot grid override, FALLBACK_BG | 9dd04f4 |

## Verification

- `npm test`: 14 files, 174 tests pass (167 prior + 7 new brand tests)
- `npm run check`: 0 errors, 0 warnings
- `npm run build`: green; dist/assets contains inter-latin-wght woff2 and 10 IBM Plex Mono woff2 files
- Mood tokens and `--chip-outline` unchanged; no `overflow-x: hidden` added; history.test.ts untouched and green

## Deviations from Plan

**1. [Rule 3 - Blocking] CSS read from disk in brand.test.ts**
- **Found during:** Task 1
- **Issue:** Under vitest, `import.meta.glob('../app.css', { query: '?raw' })` returns an empty string (CSS modules are stubbed), so case 5 could never pass and the CDN/538 scans would silently skip CSS.
- **Fix:** Glob `.ts`/`.svelte` with `?raw` as planned; enumerate `.css` files by glob keys and read them with `node:fs` `readFileSync` (with `/// <reference types="node" />`). Added an assertion that app.css was actually read (length > 100).
- **Files modified:** web/src/lib/brand.test.ts
- **Commit:** d5fe20e

Also added a self-check case that the 538 regex catches a credit and does not match `15380`.

## Known Stubs

None.

## Self-Check: PASSED
- FOUND: web/src/lib/brand.test.ts, web/src/main.ts, web/src/app.css
- FOUND commits: d5fe20e, 9dd04f4

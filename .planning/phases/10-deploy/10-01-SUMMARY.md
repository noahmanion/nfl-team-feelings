---
phase: 10-deploy
plan: 01
subsystem: web
tags: [deploy, node, og-tags, footer, vite-plugin]
requires: []
provides:
  - Node 24.x pin (engines, .nvmrc, lockfile)
  - resolveSiteOrigin build-time origin resolver (reusable by Phase 14)
  - site-origin Vite plugin substituting %SITE_ORIGIN% in index.html
  - site-wide title/description/OG/Twitter/canonical tags
  - web/public/og-default.png share image
  - always-on disclaimer footer
affects: [10-02]
tech-stack:
  added: []
  patterns:
    - "Vite transformIndexHtml order 'pre' placeholder substitution for absolute URLs"
    - "Pure env-record resolver shared between vite.config.ts and vitest"
key-files:
  created:
    - web/src/lib/siteOrigin.ts
    - web/src/lib/siteOrigin.test.ts
    - web/public/og-default.png
  modified:
    - web/package.json
    - web/package-lock.json
    - web/.nvmrc
    - README.md
    - web/vite.config.ts
    - web/index.html
    - web/src/components/SiteFooter.svelte
    - web/src/App.svelte
decisions:
  - "Origin order: SITE_ORIGIN, then https:// + VERCEL_PROJECT_PRODUCTION_URL, then https://nfl-team-feelings.vercel.app; trailing slashes stripped; VERCEL_URL never used"
  - "Footer always rendered; stamp only when data is ready; 'Source: nflverse' folded into the disclaimer"
metrics:
  duration: ~2min
  completed: 2026-11-11
  tasks: 3
  files: 11
---

# Phase 10 Plan 01: Repo-side deploy prep Summary

Node pinned to 24.x, absolute site-wide Open Graph/Twitter/canonical tags generated from a tested build-time origin resolver via a `transformIndexHtml` (order 'pre') Vite plugin, a 1200x630 default share image, and a disclaimer footer that renders on every route including the fatal-error page.

## Tasks

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Pin Node 24 | 71d2a60 | web/package.json, web/package-lock.json, web/.nvmrc, README.md |
| 2 (RED) | Failing siteOrigin tests | 769a59c | web/src/lib/siteOrigin.test.ts |
| 2 (GREEN) | Resolver, plugin, share tags | 0c84060 | web/src/lib/siteOrigin.ts, web/vite.config.ts, web/index.html |
| 3 | Share image and disclaimer footer | d80b69c | web/public/og-default.png, web/src/components/SiteFooter.svelte, web/src/App.svelte |

## Verification

- `npm test` 153/153 passing (4 new siteOrigin cases), `npm run check` 0 errors/0 warnings, `npm run build` succeeds, all under Node 24.
- `dist/index.html`: no `%SITE_ORIGIN%` left; `og:url`, `og:image`, `twitter:image` and canonical use `https://nfl-team-feelings.vercel.app`; `SITE_ORIGIN=https://example.com/` build emits `href="https://example.com/"`.
- `og-default.png`: 1200 x 630 RGB PNG, 24,340 bytes; shipped to `dist/og-default.png`. Generator script stayed in the scratchpad.
- Disclaimer string is present in the built JS bundle. No `vercel.json`. Nothing under `pipeline/` changed. Nothing pushed.

## Deviations from Plan

None. The plan was executed exactly as written.

## TDD Gate Compliance

RED (`test(10-01)` 769a59c) failed as expected because the module was missing. GREEN (`feat(10-01)` 0c84060) followed. No refactor was needed.

## Known Stubs

None.

## Self-Check: PASSED

- Files exist: siteOrigin.ts, siteOrigin.test.ts, og-default.png, SiteFooter.svelte (modified)
- Commits exist: 71d2a60, 769a59c, 0c84060, d80b69c

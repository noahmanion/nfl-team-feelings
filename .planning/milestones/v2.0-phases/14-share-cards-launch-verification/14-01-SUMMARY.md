---
phase: 14-share-cards-launch-verification
plan: 01
subsystem: web/share
tags: [share, og, tdd, node-importable]
requires: [router.ts teamHash, teamNames.ts eraName/eraText, format.ts weekLabel/formatRecord]
provides: [web/src/lib/share.ts share URL contract for share.mjs (14-03) and CopyLinkButton (14-04)]
affects: [web/tsconfig.app.json]
tech-stack:
  added: []
  patterns: [Node 24 type-stripped .ts imports with explicit .ts extensions, injected origin/deep for DOM-free helpers]
key-files:
  created: [web/src/lib/share.ts, web/src/lib/share.test.ts]
  modified: [web/tsconfig.app.json]
decisions:
  - "shareTargets derives from hasSharePage over every season's week_labels keys (integer keys only), sorted, so build and app cannot disagree"
  - "Share page redirect script is guarded by a crawler UA regex (RESEARCH Pattern 5 optional hardening)"
  - "calloutShareMeta nick-prefix check uses the era nick (eraText of meta.teams nick); mover headlines like 'Texans +16' therefore stand alone as titles"
metrics:
  duration: ~6min
  completed: 2026-11-12
  tasks: 2
  files: 3
---

# Phase 14 Plan 01: share.ts URL scheme, launch gate and share page HTML Summary

`share.ts` is a pure, Node-24-importable module. It owns the `/s/` and `/og/` path scheme, the SHARE_LAUNCH gate (2026 week 9) and `shareTargets`, plus HTML escaping, the crawler-guarded share page HTML and the team and callout meta copy. It also picks the copy-link URL: the share page when one exists, otherwise the hash deep link. Tests drive all of it (25 cases).

## Tasks

| Task | Name | Commits |
|------|------|---------|
| 1 | Path builders, launch gate, targets, escapeHtml, copy-URL helpers + tsconfig flag | 1b2d624 (RED), cdbf16e (GREEN) |
| 2 | sharePageHtml + team/callout meta copy + Node import smoke | b3ac28c (RED), fe54fdd (GREEN) |

## Verification

- `npx vitest run src/`: 24 files, 302 tests passed (Node 24)
- Node smoke `await import('./src/lib/share.ts')` prints `share.ts node import ok`
- `npm run check`: 0 errors, 0 warnings
- No extensionless value imports, no imports of `callouts.ts`/`copyLink.ts`; `summary_large_image` present, no `http-equiv`, `u003c` script-safe hash encoding present
- Manual render: a `</script>` hash comes out as `"#/a</script>"` inside the single script, and as `&lt;/script&gt;` in the link href

## Deviations from Plan

**1. [Rule 1 - Bug] The test fixture's tag count was wrong**
- **Found during:** Task 2 GREEN
- **Issue:** The RED test expected at least 17 og/twitter/canonical tags. The UI-SPEC head order has exactly 16 (10 og, 5 twitter, 1 canonical).
- **Fix:** The assertion is now `toBe(16)`, which is also stricter. A typed callout fixture variable also avoids a svelte-check excess-property error.
- **Files:** web/src/lib/share.test.ts. **Commit:** fe54fdd

## TDD Gate Compliance

RED commits (`test(14-01)`) precede GREEN commits (`feat(14-01)`) for both tasks. Both RED runs failed because `./share.ts` and its exports didn't exist yet.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: web/src/lib/share.ts, web/src/lib/share.test.ts, web/tsconfig.app.json (allowImportingTsExtensions)
- FOUND commits: 1b2d624, cdbf16e, b3ac28c, fe54fdd

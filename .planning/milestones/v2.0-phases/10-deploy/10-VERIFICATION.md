---
phase: 10-deploy
verified: 2026-11-11T00:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 10: Deploy Verification Report

**Phase Goal:** Anyone can open the current site at a public Vercel URL, and it stays current on its own
**Status:** passed (initial verification)

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Public Vercel URL serves all v1 routes, built from web/, Node 24.x | VERIFIED | Default-UA curl of https://nfl-team-feelings.vercel.app/ returns 200. All /data/*.json (meta, latest, history, records, methodology, callouts, teams/KC) return 200 application/json. Hash routing means one index.html serves every route. The production JS bundle index-CVWspaCN.js is the same hash as my local `npm run build`, so prod matches HEAD web/. web/package.json engines is node 24.x. Project nodeVersion 24.x and the git link are recorded in 10-02-SUMMARY (MCP evidence, not re-checked). |
| 2 | web/ or data push redeploys; pipeline-only commit skipped | VERIFIED (recorded Vercel evidence) | Summary records dpl_9oZ1 CANCELED at a533993 (docs-only) with the ignore-step log, and dpl_EzQu READY at 4179b76 containing web fixes. The ignore command is `git diff --quiet ${VERCEL_GIT_PREVIOUS_SHA:-HEAD^} HEAD -- .` with root web/. Live prod bundle includes the post-review web fixes (hash matches local build), which corroborates the auto-redeploy. No vercel.json (settings are in project config). |
| 3 | Every page shows "data through" stamp and unofficial/not-affiliated/nflverse footer | VERIFIED | SiteFooter is rendered in App.svelte shell (line 307), outside the routes. It contains "Data through {meta.data_through}". The live bundle contains "Data through", "not affiliated with the NFL" and "nflverse". |
| 4 | Link-preview of URL shows site-wide title, description, share-card tags | VERIFIED | With `-A facebookexternalhit/1.1`, the HTML has title, description, canonical, og:type/site_name/title/description/url/image (+width/height/alt), twitter:card summary_large_image/title/description/image, all absolute on the production origin. /og-default.png returns 200 image/png, 24340 bytes. |

**Score:** 4/4

## Behavioral Spot-Checks (Node 24.20.0, web/)

| Check | Result | Status |
|-------|--------|--------|
| `npm test` | 11 files, 158 tests passed | PASS |
| `npm run check` | 0 errors, 0 warnings | PASS |
| `npm run build` | built; JS bundle hash matches production | PASS |

## Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
|-------------|-------------|--------|----------|
| DEPLOY-01 | 10-01, 10-02 | SATISFIED | Truth 1 |
| DEPLOY-02 | 10-02 | SATISFIED | Truth 2 |
| DEPLOY-03 | 10-01, 10-02 | SATISFIED | Truths 3 and 4 |

All three IDs from the PLAN frontmatter appear in REQUIREMENTS.md and are mapped to Phase 10. No orphaned requirements.

## Anti-Patterns

No TBD/FIXME/XXX in web/src or index.html. Working tree clean.

## Human Verification (non-blocking notes)

- Optionally paste the URL into opengraph.xyz or Slack to eyeball the card image. The crawler-UA curl already shows all tags and the image resolves, so this does not block.
- Vercel-side deployment states and the ignore-step log come from 10-02-SUMMARY (recorded MCP evidence); they could not be independently queried here.

## Gaps Summary

None.

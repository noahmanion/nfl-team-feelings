---
phase: 14-share-cards-launch-verification
plan: 03
subsystem: web/share
tags: [share, og, build, satori, playwright, uat]
requires: [web/src/lib/share.ts (14-01), web/scripts/og-template.mjs (14-02), siteOrigin.ts, logoSwitch.ts]
provides: [web/scripts/share.mjs buildShare + CLI, npm run build share step, verify_share.py, 14-HUMAN-UAT.md]
affects: [web/package.json, README.md, 14-VALIDATION.md]
tech-stack:
  added: []
  patterns: [post-vite-build Node 24 script importing .ts helpers, guarded CLI main via pathToFileURL, og:image self-check before exit]
key-files:
  created: [web/scripts/share.mjs, web/scripts/share.test.mjs, .planning/phases/14-share-cards-launch-verification/verify_share.py, .planning/phases/14-share-cards-launch-verification/14-HUMAN-UAT.md, .planning/phases/14-share-cards-launch-verification/samples/]
  modified: [web/package.json, README.md, .planning/phases/14-share-cards-launch-verification/14-VALIDATION.md]
decisions:
  - "Target weeks come from shareTargets(meta). A target with no snapshot rows is logged ('share: no snapshot rows for {season} w{week}') and skipped, not thrown, and summary.targets counts only rendered weeks (orchestrator W3)"
  - "The share step adds about 0.8 s to the build (vite-only 0.60 s, total 1.40–1.55 s). No D-20 fallback needed."
  - "The UAT D-25 curl uses -L so the non-trailing-slash variant follows Vercel's redirect"
metrics:
  duration: ~9min
  completed: 2026-11-12
  tasks: 3
  files: 10
---

# Phase 14 Plan 03: Share step in the build Summary

`npm run build` now runs `vite build && node --expose-gc scripts/share.mjs`. Each build renders 32 team cards, 12 callout cards and the site card (45 PNGs at 1200×630, largest 54 KB) and writes 44 static share pages under `/s/`. Every page carries absolute production og/twitter/canonical tags, and the step self-checks that each og:image file exists. In a real browser the pages redirect to the matching hash route.

## Tasks

| Task | Name | Commits |
|------|------|---------|
| 1 | buildShare() in share.mjs + integration test | f4ecc09 (RED), 586ded9 (GREEN) |
| 2 | Wire into npm run build, measure, verify dist + redirect, samples | 5b91205 |
| 3 | 14-HUMAN-UAT.md + 14-VALIDATION.md | 116f7dc |

## Measured build times (Apple Silicon, Node 24)

| Build | Wall time | Share step log |
|-------|-----------|----------------|
| `npx vite build` only | real 0.60 s (vite "built in 304ms") | — |
| `npm run build` run 1 | real 1.55 s | `rendered 45 cards in 0.71s (16ms/card avg)`, `44 pages, 1 target weeks, largest card 54 KB, rss 328 MB`, projected ≈ 10s |
| `npm run build` run 2 | real 1.40 s | `rendered 45 cards in 0.69s (15ms/card avg)`, rss 339 MB, projected ≈ 9s |
| `VITE_LOGOS=off npm run build` | exit 0, no dist/logos | `rendered 45 cards in 0.55s (12ms/card avg)`, largest 51 KB, rss 286 MB, projected ≈ 8s |
| final `npm run build` | — | `rendered 45 cards in 0.68s (15ms/card avg)`, rss 337 MB |

The share step costs about 15 ms per card and adds roughly 0.8 s per build. A full season projects to about 14 weeks × 45 cards × 15 ms ≈ 9–10 s locally. Even with Vercel's machine 3–4× slower (RESEARCH A3), that's around 40 s, well under the 60 s / 3 min D-20 thresholds, so the fallback wasn't needed. The first run didn't hit a noticeable Gatekeeper delay (Pitfall 2).

## Local dist verification

- FOUND: `dist/s/team/BUF/2026-w9/index.html`, `dist/og/team/BUF/2026-w9.png`, `dist/s/c/2026/9/CLE-worried/index.html`, `dist/og/c/2026/9/CLE-worried.png`, `dist/og-default.png`
- `property="og:image" content="https://nfl-team-feelings.vercel.app/og/team/BUF/2026-w9.png"`
- `property="og:url" content="https://nfl-team-feelings.vercel.app/s/team/BUF/2026-w9/"`
- `"#/team/BUF/2026/9"` is in the redirect script. `ls dist/s/team | wc -l` = 32
- verify_share.py against `vite preview` on port 4173 (Python 3.13 Playwright):
  ```
  PASS team share redirects - http://localhost:4173/#/team/BUF/2026/9
  PASS team heading renders - Buffalo Bills
  PASS callout share redirects - http://localhost:4173/#/team/CLE/2026/9
  PASS team card is image/png - 200 image/png
  PASS crawler gets og:image - 200
  ALL PASS
  ```
- `npm test`: 26 files, 342 tests passed. `npm run check`: 0 errors, 0 warnings. `git status --porcelain pipeline/` is empty.

## Samples (4 committed, all ≤ 56 KB)

`samples/team-WAS.png` (two-line name), `samples/team-TB-fine.png` ("It’s fine. Everything’s fine.", with U+2019), `samples/callout-HOU-mover-up.png` (drawn arrow in the mover detail) and `samples/og-default.png` (site card). I inspected each one against the UI-SPEC checklist: everything sits in the safe area, there's no tofu or emoji, the score is right-aligned, and the arrow is drawn. No template fixes were needed. I also inspected a logos-off BUF chip card in the scratchpad and didn't commit it.

## Deviations from Plan

**1. [Orchestrator note W3] Empty target weeks are skipped**
- A target week with no snapshot rows logs `share: no snapshot rows for {season} w{week}` and is skipped. Reads use `?? []` guards. The test now derives its expected targets and pages only from weeks that have rows.
- Files: web/scripts/share.mjs, web/scripts/share.test.mjs. Commit: 586ded9

**2. [Rule 1 - acceptance grep] Reworded a comment**
- The header comment named `callouts.ts`/`lib/logos`, which tripped the forbidden-import grep (count 2). I reworded it so the count is 0. There's no code change. Commit: 586ded9

**3. Callout sample choice**
- The "fine" team sample is TB. DAL has the same label.

## TDD Gate Compliance

RED `test(14-03)` f4ecc09 failed because share.mjs didn't exist yet. GREEN `feat(14-03)` 586ded9 passed 7/7.

## Known Stubs

None.

## Threat Flags

None. Pages are only produced through sharePageHtml (T-14-02 escaping), the origin comes from resolveSiteOrigin (T-14-03), and RSS and the projection are logged (T-14-04).

## Not done here (by design)

No push and no deploy. The orchestrator runs the D-25 crawler curls from `14-HUMAN-UAT.md` after Vercel is READY. The real-platform UAT is still pending.

## Self-Check: PASSED

- FOUND: web/scripts/share.mjs, web/scripts/share.test.mjs, verify_share.py, 14-HUMAN-UAT.md, samples/ (4 PNGs)
- FOUND commits: f4ecc09, 586ded9, 5b91205, 116f7dc

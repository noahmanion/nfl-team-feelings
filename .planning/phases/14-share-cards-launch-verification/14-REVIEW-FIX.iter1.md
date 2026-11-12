---
phase: 14-share-cards-launch-verification
fixed_at: 2026-11-12T00:59:30Z
review_path: .planning/phases/14-share-cards-launch-verification/14-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 14: Code Review Fix Report

**Fixed at:** 2026-11-12T00:59:30Z
**Source review:** .planning/phases/14-share-cards-launch-verification/14-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

Verification after all fixes (Node 24): `npm test` passed (26 files, 364 tests), `npm run check` reported 0 errors and 0 warnings, and `npm run build` passed (45 cards, 44 pages, 1 target week).

## Fixed Issues

### WR-01: The crawler UA regex stops redirects for real people in LinkedIn and Telegram in-app browsers, and on some Android phones

**Files modified:** `web/src/lib/share.ts`, `web/src/lib/share.test.ts`
**Commit:** c1f5e7f
**Applied fix:** `CRAWLER_RE` is now built from a list of fetcher-only tokens: facebookexternalhit, facebot, twitterbot, slackbot, linkedinbot, discordbot, telegrambot, whatsapp, applebot, googlebot, bingbot, embedly, pinterestbot, `pinterest/0.`, redditbot, skypeuripreview, vkshare, w3c_validator, iframely and opengraph. The bare `bot`, `slack`, `linkedin`, `discord` and `telegram` tokens are gone. Pinterest is matched as `pinterestbot|pinterest/0.` rather than a bare `pinterest`, because the Pinterest in-app browser adds `[Pinterest/iOS]` and a bare token would block those users. New tests pull the exact regex out of the generated HTML. They check that people in the LinkedIn in-app browser (iOS and Android), the Telegram in-app browser (Android) and the Pinterest in-app browser, on a Cubot phone, and on desktop Chrome get redirected. They also check that 10 real crawler UAs, including LinkedInBot, TelegramBot, WhatsApp and Slackbot, stay on the page.

### WR-02: The app's `hasSharePage` and the build can disagree, so copied links 404

**Files modified:** `web/src/lib/share.ts`, `web/src/lib/share.test.ts`, `web/scripts/share.mjs`, `web/scripts/share.test.mjs`
**Commit:** 8664558
**Applied fix:** The app and the build share one predicate. `hasSharePage` now also requires `week <= max_week`, so week labels emitted before the week is played never count, and the build still gets its targets from it through `shareTargets`. `share.mjs` now fails loudly instead of skipping. A missing or corrupt `snapshots/{season}.json` throws `share: cannot read ... copy links for {season} would 404`. A shareable week with no rows throws `share: no snapshot rows for {season} w{week}, but hasSharePage lists it (copy links would 404)`. `main()` already turns a thrown error into exit code 1. New tests cover the max_week rule and all three build failure paths: missing file, corrupt file and empty week. One existing sort-order test fixture had max_week 0 with labels for weeks 2 and 10. I raised its max_week to 10 so the fixture stays valid under the new rule. Status: fixed, requires human verification. This changes the gate logic, so please confirm that requiring `week <= max_week` is the intended rule.

### WR-03: Nothing enforces the "erasable TS only" contract, so a regression passes check and test but breaks the Vercel build

**Files modified:** `web/tsconfig.app.json`, `web/scripts/share.test.mjs`
**Commit:** 162f19d
**Applied fix:** Added `"erasableSyntaxOnly": true` to `tsconfig.app.json`. TS 6 supports it, and `npm run check` stays clean. Added a test that runs `import('./scripts/share.mjs')` in a separate plain `node` process, which pulls in all six `src/lib/*.ts` helpers under real type stripping. That catches extensionless imports, which the tsconfig flag cannot. To confirm both guards work, I temporarily added an `enum` to `format.ts`: svelte-check reported an erasableSyntaxOnly error and the spawned-node test failed with `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX`. I then reverted it.

### WR-04: Callout copy buttons have no unique accessible name, unlike the new header button

**Files modified:** `web/src/components/CalloutCard.svelte`, `.planning/phases/14-share-cards-launch-verification/verify_copy.py`
**Commit:** ec4f87f
**Applied fix:** CalloutCard now passes `ariaLabel="Copy link to {name}: {headline}"`. That is the form the reviewer suggested, not the plain "Copy link to {name}". A name-only label would still clash with the team page header button ("Copy link to Buffalo Bills") and with that team's other callouts. Starting with "Copy link" keeps label-in-name (WCAG 2.5.3). The phase browser check `verify_copy.py` matched the header button by substring, and that would now also match the BUF callout buttons, so it now matches with `exact=True`.

---

_Fixed: 2026-11-12T00:59:30Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

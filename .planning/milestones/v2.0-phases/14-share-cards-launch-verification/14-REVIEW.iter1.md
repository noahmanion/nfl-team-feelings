---
phase: 14-share-cards-launch-verification
reviewed: 2026-11-12T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - web/package.json
  - web/scripts/og-template.mjs
  - web/scripts/og-template.test.mjs
  - web/scripts/share.mjs
  - web/scripts/share.test.mjs
  - web/src/components/CalloutCard.svelte
  - web/src/components/CalloutCards.svelte
  - web/src/components/CopyLinkButton.svelte
  - web/src/components/TeamPage.svelte
  - web/src/lib/share.test.ts
  - web/src/lib/share.ts
  - web/tsconfig.app.json
findings:
  critical: 0
  warning: 4
  info: 6
  total: 10
status: issues_found
---

# Phase 14: Code Review Report

**Reviewed:** 2026-11-12
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

I reviewed the share-page generator (`share.ts` + `share.mjs`), the satori/resvg card renderer, and the copy-link wiring. I focused on these areas: escaping and script breakout, absolute og URLs, redirect correctness, slug consistency between the app and the build, build robustness on Vercel, copy fallback behavior, and accessibility.

The security core holds up:
- Every interpolated value goes through `escapeHtml`, which handles `&` first.
- The redirect hash is JSON-encoded and `<` becomes `<`, so data cannot close the script.
- The fallback `href` is prefixed with `/`, so it can never become a `javascript:` URL.
- The origin is normalized through `URL` and rejects anything that isn't http(s).
- Path and slug builders live in one module that both the app and the build use, and the casing matches on both sides.

I found no blockers. The problems are robustness gaps:
- The crawler UA guard also catches real people in some in-app browsers.
- The app and the build can still disagree about whether a share page exists, which produces copied links that 404.
- The "erasable TS only" contract that the Vercel build depends on isn't enforced by any check or test.
- There is a small accessibility inconsistency in the copy buttons.

I checked the committed data: every 2026 week label has snapshot rows, and the only character the fonts can't draw in callout headlines, details or labels is the mover `→`, which is already handled. So none of these issues fire against today's data.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: The crawler UA regex stops redirects for real people in LinkedIn and Telegram in-app browsers, and on some Android phones

**File:** `web/src/lib/share.ts:160,199`
**Issue:** The script skips the redirect whenever the UA matches `/bot|facebookexternalhit|facebot|twitterbot|slack|linkedin|discord|whatsapp|telegram|embedly|applebot/i`. Several of these substrings show up in UAs used by people, not just preview fetchers:
- The LinkedIn in-app browser on iOS and Android adds `LinkedInApp`, which matches `linkedin`.
- Telegram's Android in-app WebView adds `Telegram-Android`, which matches `telegram`.
- The bare `bot` matches device and model tokens such as `Cubot` (an Android OEM).

Anyone who taps a shared link in LinkedIn, one of the main targets for share cards, lands on the static fallback page instead of the app. The fallback link still works, so nothing is fully broken, but the redirect fails on exactly the platforms this phase targets.
**Fix:** Match preview-fetcher tokens only, not app names:
```ts
const CRAWLER_RE = '/facebookexternalhit|facebot|twitterbot|slackbot|linkedinbot|discordbot|whatsapp\\/|telegrambot|embedly|applebot|googlebot|bingbot|\\bbot\\b|crawler|spider/i'
```
`LinkedInBot` and `TelegramBot` are the real crawler UAs. The WhatsApp preview fetcher sends `WhatsApp/2.x`, while the WhatsApp in-app browser uses the system browser. Add a test that runs the regex against a LinkedIn in-app UA and expects the redirect to fire.

### WR-02: The app's `hasSharePage` and the build can disagree, so copied links 404

**File:** `web/scripts/share.mjs:71-82,101-108`; `web/src/lib/share.ts:36-41`
**Issue:** The 14-01 decision says "build and app cannot disagree". The build breaks that in two places:
- A target week with no snapshot rows is logged and skipped (`continue`), not treated as an error.
- `seasonFile` swallows every read or JSON parse error (`catch { f = null }`), so a missing or corrupt `snapshots/{season}.json` also turns into "no rows, skip".

Either way the build succeeds and the deploy goes out. Meanwhile the client's `hasSharePage` only checks `week_labels` and still returns true, so both copy buttons hand people `/s/team/.../` and `/s/c/.../` URLs that 404. Nothing ties `week_labels` to rows having actually been rendered. For example, if a later pipeline change emits labels for a whole season up front, every future-week copy link will 404.
**Fix:** Fail loudly so a bad deploy can't ship:
```js
const seasonFile = (season) => {
  if (!seasons.has(season)) seasons.set(season, readJson(join(dataDir, `snapshots/${season}.json`)))
  return seasons.get(season)
}
// ...
if (!rows.length) throw new Error(`share: no snapshot rows for ${season} w${week} but meta lists it (copy links would 404)`)
```
Alternatively, make `hasSharePage` also require `week <= season.max_week` and enforce the same rule in the build.

### WR-03: Nothing enforces the "erasable TS only" contract, so a regression passes check and test but breaks the Vercel build

**File:** `web/tsconfig.app.json:10`; `web/src/lib/share.ts:3-8`
**Issue:** `share.mjs` imports `share.ts`, `format.ts`, `router.ts`, `teamNames.ts`, `siteOrigin.ts` and `logoSwitch.ts` directly under Node 24 type stripping. That only works if those files, and everything they import, have no enums, namespaces or parameter properties, and every value import carries a `.ts` extension. Nothing checks this:
- `tsconfig.app.json` gained `allowImportingTsExtensions` but not `erasableSyntaxOnly`. `tsconfig.node.json` has that flag but only includes `vite.config.ts`.
- `npm test` runs the scripts through Vitest's esbuild transform, which compiles enums and resolves extensionless imports without complaint.

So if someone adds an `enum` to `format.ts` or an extensionless value import to `teamNames.ts`, `npm run check` and `npm test` stay green, but `node scripts/share.mjs` fails, and with it `npm run build` on Vercel.
**Fix:** Add `"erasableSyntaxOnly": true` to `tsconfig.app.json`, or to a small dedicated tsconfig that includes `src/lib/share.ts` and its imports. Also add a test or npm script that runs the real Node import, for example a `pretest` running `node -e "await import('./src/lib/share.ts')"`, so extensionless imports fail in CI and locally.

### WR-04: Callout copy buttons have no unique accessible name, unlike the new header button

**File:** `web/src/components/CalloutCard.svelte:44`; `web/src/components/CopyLinkButton.svelte:7,32`
**Issue:** `CopyLinkButton` gained an `ariaLabel` prop, and TeamPage passes `"Copy link to {name}"`. CalloutCard passes nothing, so the board shows up to 12 buttons all named just "Copy link". The team page then has one "Copy link to Buffalo Bills" plus several bare "Copy link" buttons for that team's callouts. In a screen reader's button list (WCAG 2.4.6 and 2.4.9), the callout buttons can't be told apart, and it's unclear which one copies the team page. The shared component makes this inconsistency easy to fix now.
**Fix:**
```svelte
<CopyLinkButton getUrl={...} {name} ariaLabel="Copy link to {name}: {headline}" />
```
Alternatively, use `aria-describedby` pointing at the card's headline id. Keep "Copy link" at the start of the label so it still satisfies WCAG 2.5.3 (label in name).

## Info

### IN-01: The Node version guard can never run

**File:** `web/scripts/share.mjs:47`
**Issue:** `process.features?.typescript` is checked inside `buildShare`, but the top-level static `import ... from '../src/lib/share.ts'` (line 11) already fails with a syntax or loader error on Node versions without type stripping. That happens before the friendly "Node 24+ required" message can run.
**Fix:** Check the version in a tiny `.mjs` entry that dynamically imports the rest, or remove the guard and rely on `engines`.

### IN-02: `SITE_ORIGIN` with a path prefix produces og URLs that don't match the deployed files

**File:** `web/src/lib/share.ts:169-170,199`; `src/lib/siteOrigin.ts:25`
**Issue:** `resolveSiteOrigin` keeps the pathname (`origin + pathname`). With `SITE_ORIGIN=https://host/app`, og:url and og:image become `https://host/app/s/...`, while the redirect goes to the root (`'/' + hash`) and the files land at `dist/s/...`. The share-mjs self-check strips the full origin, so the build still passes. This was fine for Phase 10's index.html, but it's inconsistent with root-relative share pages.
**Fix:** Use `new URL(origin).origin` for share-page URLs, or document that subpath origins aren't supported.

### IN-03: The card score and the share title round differently

**File:** `web/scripts/og-template.mjs:156` vs `web/src/lib/share.ts:120`
**Issue:** The card renders `Math.round(score)`, but the page title and alt text use `String(row.score)`. With today's integer scores they match. If the pipeline ever emits a fractional score, the preview text (e.g. "95.6") and the image ("96") would disagree.
**Fix:** Format the score once, for example with a `formatScore` helper in `share.ts`, and use it in both places.

### IN-04: A single unsupported glyph in data fails the whole site deploy

**File:** `web/scripts/og-template.mjs:95-97`
**Issue:** The missing-glyph guard throws, and that error aborts `npm run build`, so any future non-Latin character (an emoji, `≥`, `×`, `→` in a headline) blocks the entire site deploy, not just the share cards. The current data is clean: I scanned all snapshots, and the only uncovered character is `→`, in mover details. Failing loudly was a deliberate choice, but the blast radius is the whole site.
**Fix:** Consider catching per card: log the error, skip that card and its page, and have `hasSharePage` consumers tolerate the gap. Or add a pipeline-side test that callout text stays within the font coverage.

### IN-05: Mover detail lines with arrows aren't clamped

**File:** `web/scripts/og-template.mjs:201-203`
**Issue:** The arrow branch renders wrapped runs without `lineClamp` or `clampText`, while the non-arrow branch clamps at 110 characters and 2 lines. Current mover details are short, but a long one would overflow into the footer.
**Fix:** Clamp each run with `clampText`, or set a fixed `maxHeight`/`overflow: hidden` on the row.

### IN-06: Part of the integration test's expected set is derived from the code under test

**File:** `web/scripts/share.test.mjs:16-25`
**Issue:** `expected()` builds its targets from `shareTargets(meta)`, the same function the build uses, so a bug in `shareTargets` (for example in the launch comparison) would cancel out. The unit tests in `share.test.ts` cover `shareTargets` separately, so this is minor.
**Fix:** Also assert one concrete known target, for example that `{season: 2026, week: 9}` is in `exp` and `{2026, 8}` is not.

---

_Reviewed: 2026-11-12_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

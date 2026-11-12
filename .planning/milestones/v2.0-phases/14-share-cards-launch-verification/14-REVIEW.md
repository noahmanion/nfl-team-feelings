---
phase: 14-share-cards-launch-verification
reviewed: 2026-11-12T01:05:00Z
depth: standard
iteration: 2
files_reviewed: 11
files_reviewed_list:
  - web/package.json
  - web/scripts/og-template.mjs
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
  warning: 0
  info: 9
  total: 9
status: issues_found
---

# Phase 14: Code Review Report (iteration 2)

**Reviewed:** 2026-11-12
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found (info only)

## Summary

This is a re-review after fix commits c1f5e7f..ec4f87f. All four warnings from iteration 1 are resolved, and the fixes introduce no new critical or warning issues. Under Node 24.20, `src/lib/share.test.ts` and `scripts/share.test.mjs` pass (54 tests).

How each prior warning was verified:
- **WR-01 (crawler UA regex): resolved.** `CRAWLER_RE` is now a list of fetcher-only tokens. The bare `bot`, `linkedin`, `telegram`, `slack` and `discord` tokens are gone. The `\\/` escapes in `'pinterest\\/0\\.'` produce a valid `/.../i` literal inside the inline script, and the script contains no `<`, so there is no script-breakout risk. The new tests extract the regex literal the page actually ships. If that extraction fails, `src` is empty and the regex matches every UA, so the "redirects people" cases fail loudly rather than passing by accident.
- **WR-02 (app and build disagree): resolved.** `hasSharePage` now requires `week <= max_week`. I checked this against the committed `meta.json`: `max_week` includes the playoffs (22 for 2023–2025, 9 for 2026), so no playoff share pages are lost. Every week in `snapshots/2025.json` and `snapshots/2026.json`, playoff weeks included, has all 32 rows, so team copy links for eliminated teams don't point at missing pages. `share.mjs` now throws on an unreadable or corrupt snapshot file and on an empty shareable week, and `main()` turns that into exit code 1.
- **WR-03 (erasable TS contract): resolved.** `erasableSyntaxOnly` is set in `tsconfig.app.json`, which includes `src/**/*.ts`. A spawned plain-`node` import of `scripts/share.mjs` exercises real type stripping on every transitive `.ts` helper. The import does not trigger `main()`, because `process.argv[1]` is undefined under `-e`.
- **WR-04 (callout button accessible name): resolved.** The callout buttons are now labelled "Copy link to {name}: {headline}", which keeps "Copy link" at the front (label-in-name). The status text lives in a separate `role="status"` element, so the static `aria-label` does not hide the "Link copied" announcement.

The info items from iteration 1 are carried forward unchanged (IN-01..IN-06). The fixes add three new minor items (IN-07..IN-09).

## Narrative Findings (AI reviewer)

No critical or warning findings.

## Info

### IN-01: The Node version guard can never run (carried)

**File:** `web/scripts/share.mjs:47`
**Issue:** The static `.ts` imports on lines 11-26 fail before `buildShare` can reach the `process.features?.typescript` check, so the friendly "Node 24+ required" message never shows.
**Fix:** Do the version check in a tiny `.mjs` entry that dynamically imports the rest, or drop the guard and rely on `engines`.

### IN-02: `SITE_ORIGIN` with a path prefix produces og URLs that don't match the deployed files (carried)

**File:** `web/src/lib/share.ts:183-184,207`
**Issue:** og:url and og:image keep the origin's pathname, but the redirect and the output files are root-relative.
**Fix:** Use `new URL(origin).origin` for share-page URLs, or document that subpath origins aren't supported.

### IN-03: The card score and the share title round differently (carried)

**File:** `web/scripts/og-template.mjs:156` vs `web/src/lib/share.ts` (`String(row.score)`)
**Fix:** Add one shared `formatScore` helper and use it in both places.

### IN-04: A single unsupported glyph in data fails the whole site deploy (carried)

**File:** `web/scripts/og-template.mjs:95-97`
**Fix:** Catch the error per card, or add a pipeline-side test that keeps callout text within the font's glyph coverage.

### IN-05: Mover detail lines with arrows aren't clamped (carried)

**File:** `web/scripts/og-template.mjs:201-203`
**Fix:** Clamp each run with `clampText`, or give the row a fixed `maxHeight` with `overflow: hidden`.

### IN-06: Part of the integration test's expected set is derived from the code under test (carried)

**File:** `web/scripts/share.test.mjs:16-25`
**Fix:** Also assert one concrete known target, for example that 2026 w9 is in the set and 2026 w8 is not.

### IN-07: The WR-02 failure-path tests depend on running in order

**File:** `web/scripts/share.test.mjs:127-156`
**Issue:** The three `it`s share one temp `dir` and each mutates `data/snapshots/2026.json` for the next. The "missing file" case only passes if it runs before the "corrupt" case writes the file. Vitest runs these sequentially by default, but `--sequence.shuffle` or `it.only` on a later case would change the outcome.
**Fix:** Write or remove the snapshot file inside each test, for example `rmSync(snap, { force: true })` at the start of the missing-file case.

### IN-08: The spawned-node test fails with a loader error, not a clear message, on older Node versions

**File:** `web/scripts/share.test.mjs:158-168`
**Issue:** On Node versions without default type stripping (the local nvm default is Node 20, and Node 22 before 22.18), `npm test` now fails here with `ERR_UNKNOWN_FILE_EXTENSION`, and `r.stderr` doesn't point at the real cause. The failure itself is reasonable because `engines` pins 24.x, but the diagnosis is opaque.
**Fix:** Check `process.features?.typescript` first and fail with an explicit "run `nvm use 24`" message (or `it.skipIf` it with a warning).

### IN-09: JS-running previewers not on the allowlist now follow the redirect

**File:** `web/src/lib/share.ts:168-173`
**Issue:** Without the catch-all `bot` token, any preview fetcher that runs JavaScript and isn't on the list follows `location.replace('/#...')`. That fetcher would read the site-default og tags from `index.html` instead of the per-team card. The impact is low: most previewers don't run JS, and the result is a generic card, not a broken one. This was the intended trade-off for WR-01.
**Fix:** Optionally add `\bbot\b|crawler|spider` (word-boundary `bot` does not match `Cubot`), with a test case for each.

---

_Reviewed: 2026-11-12_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

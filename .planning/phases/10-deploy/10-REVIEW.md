---
phase: 10-deploy
reviewed: 2026-11-11T00:00:00Z
depth: standard
iteration: 2
files_reviewed: 9
files_reviewed_list:
  - web/index.html
  - web/vite.config.ts
  - web/src/lib/siteOrigin.ts
  - web/src/lib/siteOrigin.test.ts
  - web/src/components/SiteFooter.svelte
  - web/src/App.svelte
  - web/package.json
  - web/.nvmrc
  - README.md
findings:
  critical: 0
  warning: 0
  info: 6
  total: 6
status: issues_found
---

# Phase 10: Code Review Report (iteration 2)

**Reviewed:** 2026-11-11
**Depth:** standard
**Iteration:** 2 (re-review after the WR-01 and WR-02 fixes, commits 3919854 and aa34d86)
**Files Reviewed:** 9
**Status:** issues_found (Info only: 0 critical, 0 warning)

## Summary

I re-reviewed the diff from 61093f9 to HEAD, focusing on the two fixes.

- **WR-01 (fixed):** `.disclaimer.solo { margin-top: 0; }` now overrides `.disclaimer`'s `--space-xs`. The solo disclaimer gets no top margin, as the UI-SPEC requires, and the UA 1em margin no longer leaks in.
- **WR-02 (fixed):** `resolveSiteOrigin` now runs the value through `new URL`, rejects anything that isn't http(s), and strips any scheme from `VERCEL_PROJECT_PRODUCTION_URL`. I checked these edge cases by hand:
  - `localhost:5173` parses as a `localhost:` scheme, so it is rejected.
  - `http:example.com` normalizes to `http://example.com`.
  - Userinfo, query, and hash are dropped.
  - A default port (`:443`) is removed.
  - `"`, `<` and `>` in the path are percent-encoded.

  `npx vitest run src/lib/siteOrigin.test.ts` passes 9 of 9 tests on Node 24. The throw happens when the config loads, so a bad value fails the build loudly, which is what the fix intended.

No new Critical or Warning defects. The remaining items are minor and carried forward, plus one new Info note about the fix.

## Narrative Findings (AI reviewer)

## Info

### IN-01: `process.env` ignores `web/.env*` files (carried forward)

**File:** `web/vite.config.ts:8`
**Issue:** `resolveSiteOrigin(process.env)` only sees shell and CI variables. A `SITE_ORIGIN` set in `.env.local` is silently ignored, and the fallback origin is used instead.
**Fix:** Use `defineConfig(({ mode }) => ...)` and merge in `loadEnv(mode, process.cwd(), '')`, or document that the value must come from a shell or CI variable.

### IN-02: `.stamp { margin-bottom: 0 }` is dead CSS (carried forward)

**File:** `web/src/components/SiteFooter.svelte:27-29`
**Issue:** The global `p { margin: 0 }` reset already does this.
**Fix:** Remove the rule.

### IN-03: `engines: "24.x"` is an exact-major pin (carried forward)

**File:** `web/package.json:23-25`, `web/.nvmrc:1`
**Issue:** The pin excludes Node 22 and Node 26 LTS, which causes EBADENGINE warnings. The local nvm default is still Node 20.
**Fix:** Widen it to `">=22.12"`, or state in the README that the pin is deliberate. The README already says "Node 24, pinned by web/.nvmrc".

### IN-04: Title and description are duplicated across meta tags (carried forward)

**File:** `web/index.html:7-33`
**Issue:** The title appears four times and the description three times, so one copy can drift from the others.
**Fix:** Use `%SITE_TITLE%`/`%SITE_DESCRIPTION%` placeholders in the existing plugin, or add a keep-in-sync comment.

### IN-05: Footer shifts when data finishes loading (carried forward, reduced)

**File:** `web/src/App.svelte:307`, `web/src/components/SiteFooter.svelte:9-14`
**Issue:** The stamp line is inserted above the disclaimer once `status === 'ready'`. Since WR-01, the margin difference is only 0 vs. 4px, so the jump is now just the height of the stamp line.
**Fix:** This is acceptable for a prototype. Optionally reserve the stamp line's height while loading.

### IN-06: The origin is resolved eagerly for every Vite command, including `vitest` and `vite dev` (new)

**File:** `web/vite.config.ts:7-8`
**Issue:** `siteOrigin()` calls `resolveSiteOrigin` when the config is evaluated, and Vitest loads `vite.config.ts`. A stray invalid `SITE_ORIGIN` in the shell therefore breaks `npm test` and `npm run dev` with the build error, not just `npm run build`. This is harmless in practice, but the failure would be unexpected.
Separately, `&` and `'` in a path are not percent-encoded by `URL`. They pass through into the double-quoted attributes. That is safe there, but it means the code comment's claim that the result is "safe to paste into an HTML attribute" holds only for double-quoted attributes.
**Fix:** Optionally resolve the origin lazily inside `handler`, or in `configResolved`, so it only runs when HTML is transformed. Tighten the comment to say "double-quoted attribute".

---

_Reviewed: 2026-11-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Iteration: 2_

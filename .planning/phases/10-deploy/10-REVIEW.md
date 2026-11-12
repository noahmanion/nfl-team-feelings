---
phase: 10-deploy
reviewed: 2026-11-11T00:00:00Z
depth: standard
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
  warning: 2
  info: 5
  total: 7
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-11-11
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

I reviewed the diff from 61093f9 to HEAD: the Node 24 pin, the build-time `resolveSiteOrigin` and its `transformIndexHtml` plugin, the site-wide share tags, and the always-on disclaimer footer. The origin plumbing works for the paths that are actually used (no env set, or Vercel's `VERCEL_PROJECT_PRODUCTION_URL`). The plugin's `order: 'pre'` also runs before Vite's own `htmlEnvHook` and asset scan, so absolute `og:image` URLs aren't rewritten.

I found two real defects:
- The footer's "solo" CSS does the opposite of what the UI-SPEC asks for.
- `SITE_ORIGIN` is not validated, and a bad value can produce broken share tags or a failed build.

The rest are minor quality items.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: `margin-top: revert` gives the solo disclaimer a 1em top margin instead of none

**File:** `web/src/components/SiteFooter.svelte:33-35`
**Issue:** The UI-SPEC says that on the fatal-error page, where there is no stamp line, the disclaimer gets no extra top margin. The code uses `margin-top: revert`, but `revert` doesn't roll back to the previous author rule. It rolls the property back to the **user-agent** stylesheet. The global reset `p { margin: 0 }` in `src/app.css:94-99` is an author-origin rule, so it gets skipped. The UA default for `<p>` is `margin-block-start: 1em`, which is 14px at `--text-label`. So the solo disclaimer gets about 14px of extra space, even more than the 4px (`--space-xs`) it gets when the stamp is present.

The same thing happens on every route while data is loading, because the footer renders solo until `status === 'ready'`.
**Fix:**
```css
.disclaimer.solo {
  margin-top: 0;
}
```
A simpler option is to drop the `solo` class and put the margin only on the sibling: `.stamp + .disclaimer { margin-top: var(--space-xs); }`.

### WR-02: `SITE_ORIGIN` is not validated; a value without a scheme or with odd characters breaks share tags or the build

**File:** `web/src/lib/siteOrigin.ts:6-11`, `web/vite.config.ts:7-15`
**Issue:** `resolveSiteOrigin` only trims and strips trailing slashes, and the plugin pastes the result straight into HTML attributes. Here is what goes wrong with bad values:
- `SITE_ORIGIN=example.com` (no scheme) emits `og:url="example.com/"` and `canonical="example.com/"`, which crawlers treat as relative or invalid.
- With that same value, `og:image`/`twitter:image` become the relative path `example.com/og-default.png`. Vite's HTML asset scan treats `meta[property=og:image] content` as an asset reference, so it tries to resolve that path. You get either a build error or a silently wrong URL. The `order: 'pre'` comment in `vite.config.ts` shows the code depends on the value being absolute, but nothing enforces that.
- A value containing `"` or `<` breaks out of the attribute. It's build-time and trusted, but it's still unescaped interpolation into HTML.
- `VERCEL_PROJECT_PRODUCTION_URL` set with a scheme (`https://foo.app`) becomes `https://https://foo.app`.
**Fix:** Normalize through `URL` and fail loudly:
```ts
export function resolveSiteOrigin(env: Record<string, string | undefined>): string {
  const explicit = env.SITE_ORIGIN?.trim()
  const vercelHost = env.VERCEL_PROJECT_PRODUCTION_URL?.trim()?.replace(/^https?:\/\//, '')
  const raw = explicit ? explicit : vercelHost ? `https://${vercelHost}` : FALLBACK_ORIGIN
  let url: URL
  try {
    url = new URL(raw)
  } catch {
    throw new Error(`SITE_ORIGIN must be an absolute http(s) URL, got: ${raw}`)
  }
  if (url.protocol !== 'https:' && url.protocol !== 'http:') {
    throw new Error(`SITE_ORIGIN must be http(s), got: ${raw}`)
  }
  return (url.origin + url.pathname).replace(/\/+$/, '')
}
```
Add a test case for `SITE_ORIGIN: 'example.com'` that expects a throw.

## Info

### IN-01: `process.env` ignores `web/.env*` files, so `SITE_ORIGIN` in `.env.local` does nothing

**File:** `web/vite.config.ts:7`
**Issue:** `resolveSiteOrigin(process.env)` only sees shell or CI variables. Vite doesn't load `.env` files into `process.env` while the config is being evaluated. Someone who puts `SITE_ORIGIN=...` in `.env.local`, which is the normal Vite habit and is already gitignored via `*.local`, will quietly get the fallback origin.
**Fix:** Use the function form and `loadEnv`. For example, `defineConfig(({ mode }) => ({ plugins: [siteOrigin({ ...loadEnv(mode, process.cwd(), ''), ...process.env }), svelte()] }))`, with `siteOrigin(env)` taking the record as an argument.

### IN-02: `.stamp { margin-bottom: 0 }` is dead CSS

**File:** `web/src/components/SiteFooter.svelte:27-29`
**Issue:** The global reset already sets `p { margin: 0 }`, so this rule changes nothing. It reads as though there's a default margin to cancel, and that same misunderstanding probably led to the `revert` in WR-01.
**Fix:** Remove the rule.

### IN-03: `engines: "24.x"` is an exact-major pin that excludes the current LTS and conflicts with local Node

**File:** `web/package.json:23-25`, `web/.nvmrc:1`
**Issue:** `24.x` rejects Node 26, which became LTS in October 2026, and Node 22, which project CLAUDE.md lists as acceptable ("Use Node 22 or 24 LTS"). `npm install` under Node 22 or 26 prints EBADENGINE warnings, and Vercel will warn or refuse once 24 is deprecated. The local nvm default is still Node 20 (v20.19.0 in this shell), so a bare `npm install` without `nvm use` warns as well.
**Fix:** If the goal is only "Vercel builds on 24", the project's `nodeVersion: 24.x` setting already does that. Consider `"node": ">=22.12"` (or `"^22.12 || ^24 || ^26"`) in engines, or note in the README that the pin is deliberate.

### IN-04: Description and title strings are duplicated three to four times in `index.html`

**File:** `web/index.html:7-33`
**Issue:** The title appears four times (`<title>`, og:title, og:image:alt, twitter:title) and the description three times. A future copy edit can easily change one and leave the others stale. Since there's already a `transformIndexHtml` plugin, it could substitute `%SITE_TITLE%`/`%SITE_DESCRIPTION%` placeholders from a single constant.
**Fix:** Add placeholders, or at least a comment near the tags saying they must stay in sync.

### IN-05: The footer jumps when data finishes loading

**File:** `web/src/App.svelte:307`, `web/src/components/SiteFooter.svelte:9-14`
**Issue:** The footer now mounts during `status === 'loading'` with only the disclaimer. When data arrives, the stamp line is inserted above it and the disclaimer moves down. The visual effect is small, but it's a layout shift on every page load, and WR-01 makes it worse with a different top margin in each state.
**Fix:** This is acceptable for a prototype. Fixing WR-01 shrinks the shift. Alternatively, reserve the stamp line's height while loading.

---

_Reviewed: 2026-11-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

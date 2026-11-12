---
phase: 10-deploy
fixed_at: 2026-11-11T00:00:00Z
review_path: .planning/phases/10-deploy/10-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 10: Code Review Fix Report

**Fixed at:** 2026-11-11
**Source review:** .planning/phases/10-deploy/10-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2
- Fixed: 2
- Skipped: 0

Verification after both fixes (Node 24): `npm test` (158 tests, 11 files) passes, `npm run check` reports 0 errors and 0 warnings, and `npm run build` succeeds. `dist/index.html` still has `og:image` set to `https://nfl-team-feelings.vercel.app/og-default.png`. `SITE_ORIGIN=example.com npm run build` now fails with `SITE_ORIGIN must be an absolute http(s) URL, got: example.com`.

## Fixed Issues

### WR-01: `margin-top: revert` gives the solo disclaimer a 1em top margin instead of none

**Files modified:** `web/src/components/SiteFooter.svelte`
**Commit:** 3919854
**Applied fix:** Changed `.disclaimer.solo { margin-top: revert; }` to `margin-top: 0;`. The solo disclaimer, shown on the fatal-error page and while data loads, no longer picks up the user-agent's 1em `<p>` margin.

### WR-02: `SITE_ORIGIN` is not validated; a value without a scheme or with odd characters breaks share tags or the build

**Files modified:** `web/src/lib/siteOrigin.ts`, `web/src/lib/siteOrigin.test.ts`
**Commit:** aa34d86
**Applied fix:** `resolveSiteOrigin` is still a pure function. It now:
- strips any leading `http(s)://` from `VERCEL_PROJECT_PRODUCTION_URL` before adding `https://`;
- parses the result with `new URL`;
- throws on values that can't be parsed or that aren't http(s);
- returns `origin + pathname` with trailing slashes removed.

Running the value through `URL` also percent-encodes `"`, `<` and `>`, so the result is safe to put in an HTML attribute. `vite.config.ts` needed no change, because the throw happens when the config loads and so fails the build loudly. New tests cover:
- a Vercel URL that already has a scheme (https and http);
- an http/localhost origin and case normalization;
- schemeless values (`example.com`, `localhost:5173`, `/relative/path`), which throw;
- `ftp:` and `javascript:` schemes, which throw;
- unparseable hosts, which throw;
- attribute-breaking characters, which get encoded.

---

_Fixed: 2026-11-11_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

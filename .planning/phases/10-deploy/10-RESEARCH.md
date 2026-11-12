# Phase 10: Deploy - Research

**Researched:** 2026-11-11
**Domain:** Vercel static hosting (Git integration, ignored build step, Node pinning), Vite HTML transforms, Open Graph tags
**Confidence:** HIGH (all core mechanics verified in Vercel docs and by local experiments in a scratch copy of `web/`)

## Summary

All of the CONTEXT.md decisions hold up technically. Vercel runs the Ignored Build Step **inside the Root Directory** (`web/`) on a `--depth=10` clone. **Exit 0 skips** the build, and the deployment then shows `CANCELED`. Exit 1 or higher builds. `VERCEL_GIT_PREVIOUS_SHA` is the SHA of the *last successful deployment* for the branch. It is **empty on a branch's first deployment** and only exposed when an Ignored Build Step is configured. `VERCEL_PROJECT_PRODUCTION_URL` is available at **build time**, as a bare host with no `https://`, and is set even on preview builds. Vite's config runs in Node, so `process.env` sees it. A Vite plugin with `transformIndexHtml` and `order: 'pre'` substitutes `%SITE_ORIGIN%` cleanly. I verified this end to end in a scratch copy: `npm run check` passed with 0 errors, vitest passed, `vite build` emitted absolute `og:image`/`canonical` URLs, and there were no warnings.

**One real gotcha the plan must handle:** the locked command `git diff --quiet ${VERCEL_GIT_PREVIOUS_SHA:-HEAD^} HEAD -- .` falls back to `HEAD^` on the **first** deployment, because `PREVIOUS_SHA` is empty then. Local `main` HEAD is currently a `.planning/`-only docs commit, and GSD phases always end with docs commits. So if the ignore command is set before the first production deploy, that **first deploy will likely be CANCELED** and the site won't be live. I tested this in a depth-10 clone: with an empty `PREVIOUS_SHA` the command exits 0 at the current HEAD. Fix it with ordering: create the project **without** the ignore command, get one READY production deployment, and only then set `commandForIgnoringBuildStep` with an update-project call. A missing SHA (more than 10 commits since the last deploy) exits 128, so the build runs. That fail-open is correct.

**Primary recommendation:** Create the project with root `web`, framework `vite`, and no ignore command. Set `nodeVersion: "24.x"` with update-project. Get the first READY production deploy, then set the ignore command. Put the origin resolver in a small tested module, `web/src/lib/siteOrigin.ts`, which `vite.config.ts` imports with an explicit `.ts` extension.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Hosting `dist/` (HTML, JS, `/data/*.json`, `/og-default.png`) | CDN / Static (Vercel) | — | Fully static. No functions, no `vercel.json` (D-02) |
| Build-time absolute origin for tags | Build (Vite config, Node) | — | Crawlers don't run JS, so the tags must be in the static HTML |
| Deciding whether to build | Vercel build step (ignore command) | Git (diff) | Runs before install/build in the Root Directory |
| Freshness stamp + disclaimer | Browser / Client (Svelte `SiteFooter`) | — | Reads `meta.json` client-side. The disclaimer is static (D-13) |
| Share image | CDN / Static (`web/public/og-default.png`) | — | Generated once offline and committed |

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
**Area 1: Vercel project & build config**
- D-01 Create the project with the Vercel MCP `create_git_project` (the CLI token is invalid). Settings: repo `noahmanion/nfl-team-feelings`, projectName `nfl-team-feelings`, rootDirectory `web`, framework `vite`, build `npm run build`, output `dist`, install `npm ci` (the default; `package-lock.json` is committed), Node 24.x. Rationale: this is the decided route. Pitfall 7 says root must be `web`.
- D-02 No `vercel.json`. Hash routing needs no rewrites, and a catch-all rewrite would hide Phase 14's share pages. Vercel's defaults already cache only hashed `/assets/*` long-term, so nothing gives `/data/*` a long `max-age`. Rationale: research says "no vercel.json rewrites" and "no long max-age on /data/*". Zero config is the least that can go wrong.
- D-03 Ignored-build command, set on the project (root dir `web`): `git diff --quiet ${VERCEL_GIT_PREVIOUS_SHA:-HEAD^} HEAD -- .`. Exit 0 (no change under `web/`) skips the build; any diff or any git error (e.g. the previous SHA is missing from the shallow clone) exits non-zero and builds. Rationale: comparing against the last *deployed* SHA catches a multi-commit push where `web/` changed in an earlier commit. Falling back to `HEAD^` matches the decided command. Failing open (build) is the safe direction.
- D-04 Push the Phase 10 code to `main` before (or as) the project is connected, so the production deployment builds the committed site with the new tags. Rationale: the decided order. The first production deploy should be the real one.

**Area 2: Node pinning**
- D-05 `web/package.json` `engines.node` = `"24.x"`. `web/.nvmrc` = `24` (nvm has v24.20.0 installed locally). The Vercel project's Node version = `24.x`. Local dev on 22.12+ still works (engines isn't enforced by npm without `engine-strict`). Rationale: `>=22.12` would float to Node 26 on Vercel (Pitfall 7). All three places agree on one major.
- D-06 The README "Run it" note changes from "Node >=22.12" to "Node 24, pinned by web/.nvmrc".

**Area 3: Site-wide share tags (DEPLOY-03)**
- D-07 Static tags in `web/index.html`: `<title>Feel-Good Score: how should you feel about your NFL team?</title>`, `meta name="description"`, `og:type=website`, `og:site_name`, `og:title`, `og:description`, `og:url`, `og:image` (+ `og:image:width` 1200, `og:image:height` 630, `og:image:alt`), `twitter:card=summary_large_image`, `twitter:title`, `twitter:description`, `twitter:image`, and `link rel="canonical"`. The description stays under ~200 characters, with no emoji and no unescaped quotes (Pitfall: copy in tags).
- D-08 Absolute URLs come from one build-time origin: a tiny Vite plugin (`transformIndexHtml`) in `vite.config.ts` replaces a `%SITE_ORIGIN%`-style placeholder. Resolution order: `SITE_ORIGIN` env → `https://` + `VERCEL_PROJECT_PRODUCTION_URL` (a Vercel system env var at build time) → the hard-coded production origin (`https://nfl-team-feelings.vercel.app`, corrected after the project exists if Vercel assigns a different domain). No trailing slash. Rationale: research picked `VERCEL_PROJECT_PRODUCTION_URL` → `SITE_ORIGIN` → fallback. Phase 14 will reuse the same resolver. Preview builds still point at the production domain, which is what crawlers can reach (previews sit behind Vercel login).
- D-09 Default share image: one static `web/public/og-default.png`, 1200×630, under ~300 KB. It shows the wordmark "Feel-Good Score" plus the tagline on a plain background, using the current site colors. No logos, no NFL marks, no emoji. Generate it once with a throwaway script (e.g. Pillow via `uv run --with pillow` in the scratchpad) and commit only the PNG. Rationale: "simple static default PNG for now". Satori cards are Phase 14.
- D-10 The tags stay site-wide and static. Nothing per-route (crawlers can't see hash routes anyway). The page `<title>` doesn't change per route in this phase.

**Area 4: Freshness stamp & disclaimer footer**
- D-11 Freshness stamp: keep the existing `SiteFooter` "Data through {formatDateOnly(meta.data_through)}" (from `meta.json`, already rendered on every route via `App.svelte`). Phase 10 makes sure it is on every page and reads "Data through …". No new data field and no pipeline change. Rationale: it already exists and is accurate. Duplicating it in the header would be restyling (Phase 12).
- D-12 Disclaimer: add one line to `SiteFooter`: "Unofficial fan project — not affiliated with the NFL. Data: nflverse." ("nflverse" links to https://github.com/nflverse). Fold the existing "Source: nflverse" link into it so the source isn't stated twice. Use the existing footer styles (muted label text) and no new design tokens. Rationale: decided copy, minimal visual change.
- D-13 The disclaimer must show even when data fails to load. Render the static disclaimer line outside the `status === 'ready'` guard, and keep the data-dependent stamps (last updated, data through) inside it. Rationale: "every page" includes the fatal-error page, and the disclaimer doesn't depend on data.
- D-14 Tests: extend or add a vitest unit test only where logic exists (e.g. the origin resolver, if it's a pure function in a small module). Verify the footer and tags through `npm run build` plus a grep on `dist/index.html`, and through a fetch of the production URL. No new e2e harness. Rationale: CLAUDE.md "light process". Existing tests must keep passing (`npm test`, `npm run check`, `npm run build`).

**Area 5: Verification & records**
- D-15 Verify production by fetching the production URL (Vercel MCP `web_fetch_vercel_url` or plain HTTP). Confirm the HTML has the tags, `/data/meta.json` returns 200 JSON, and `/og-default.png` returns 200 `image/png`. Use `list_deployments` / `get_deployment` to confirm the production deployment is READY and built from the pushed commit.
- D-16 Verify the ignored-build step with a pipeline-only or planning-only commit pushed after deploy. Its deployment should show as canceled/skipped by the ignore step (`list_deployments`). If an appropriate commit doesn't occur naturally, the phase-completion docs commit (`.planning/` only) serves as the test. Rationale: success criterion 2 needs evidence. A `.planning/` commit touches nothing under `web/`.
- D-17 If the Vercel GitHub app isn't installed for the repo, or any MCP step returns requires_user_action, finish everything else and record the exact single user action (with dashboard URL) as a human_needed item. Don't block the phase.
- D-18 Record the production URL in `.planning/PROJECT.md` (Hosting constraint + a Key Decisions row) and in `README.md` (a "Live site" line at the top).

### Claude's Discretion
- The exact title and description wording (within D-07's limits) and the og image's typography and layout.
- Whether the origin resolver lives inline in `vite.config.ts` or in a small tested module.
- The footer markup details, as long as the existing styles and responsive line breaks are kept.

### Deferred Ideas (OUT OF SCOPE)
- Per-route `<title>` updates (nice for tabs and history). Phase 12 or 14.
- A "new week, reload" version-skew banner (Pitfall: open tabs across a weekly deploy). Later phase.
- A custom domain. Not requested.
- Per-team and per-callout share pages and cards. Phase 14.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEPLOY-01 | Public Vercel production URL, built from `web/`, Node pinned 24.x | Root Directory and Node settings (§Vercel facts 1, 3). Ordering of the first deploy (Pitfall 1). Discovering the domain (Pitfall 4) |
| DEPLOY-02 | Push to `main` redeploys; pipeline-only commits skipped | Ignore-step semantics verified in docs and in a depth-10 clone test (§Vercel facts 2). Verification via a `CANCELED` deployment |
| DEPLOY-03 | "Data through" stamp, site-wide title/description/share tags, disclaimer footer | Vite `order:'pre'` plugin verified (Pattern 1). Pillow OG image verified (Pattern 3). Footer contract in UI-SPEC |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Work only inside `feel-good-scorew/`. Keep it self-contained, with no shared deps and no root-level manifests.
- Light process: no CI, no e2e harness. Write unit tests only where there's pure logic.
- Free data only. Don't touch `pipeline/` (the model is frozen) or `pipeline/PREREGISTRATION*.md`.
- Stack is fixed: Vite 8 + Svelte 5 + Observable Plot. Keep TypeScript at `~6.0` (svelte-check doesn't support TS 7).
- Hosting: a static Vercel site. The Hobby plan is non-commercial, so no ads or affiliate links.
- Memory notes: nvm defaults to Node 20, so use `nvm use 22`/`24` for `web/`. Full autonomy: decide, don't ask.

## Verified Vercel Facts

### 1. Ignored Build Step (answers Q1)
- **Exit codes:** "If the command exits with code `1`, the build continues… If the command exits with code `0`, the build is immediately aborted, and the deployment state is set to `CANCELED`." The KB guide adds that exit "`1` or greater" builds. [CITED: vercel.com/docs/project-configuration/project-settings, vercel.com/kb/guide/how-do-i-use-the-ignored-build-step-field-on-vercel]
- **cwd:** "The command is executed within the Root Directory and can access the System Environment Variables that are available at build time." So `-- .` means `web/`. Vercel's own example for this case is `git diff HEAD^ HEAD --quiet -- .`. [CITED: same]
- **Clone depth:** "`git clone --depth=10`". [CITED: KB guide]
- **`VERCEL_GIT_PREVIOUS_SHA`:** "The git SHA of the last successful deployment for the project and branch. It's empty on a branch's first deployment… only exposed when an Ignored Build Step is provided." Build time only. [CITED: vercel.com/docs/environment-variables/system-environment-variables]
- **Canceled builds still count** toward the deployment quota (Hobby has a per-day cap) and use concurrent build slots. At this repo's commit rate that doesn't matter. [CITED: project-settings]
- **Soundness of `git diff --quiet ${VERCEL_GIT_PREVIOUS_SHA:-HEAD^} HEAD -- .`.** Tested in a `git clone --depth=10` of this repo, inside `web/` [VERIFIED: local experiment]:
  - With `PREVIOUS_SHA` empty or unset, `:-` falls back to `HEAD^`. At current HEAD (a docs-only commit) it **exits 0, so the deploy is skipped**. See Pitfall 1.
  - With `PREVIOUS_SHA` = a SHA not in the clone: `fatal: bad object`, **exit 128, so it builds**. That's the correct fail-open.
  - With `PREVIOUS_SHA` = the oldest commit in the clone and no `web/` change since: exit 0, skipped. Correct.
  - Because `PREVIOUS_SHA` only advances on *successful* deployments, a canceled (skipped) deploy leaves it in place. A later push still diffs against the last *built* commit. That's the right semantics for a multi-commit push.
- **REST field names:** `commandForIgnoringBuildStep` (string, max 256, nullable) is accepted by both create-project and update-project. [CITED: vercel.com/docs/rest-api/reference/endpoints/projects/create-a-new-project, …/update-an-existing-project]

### 2. `VERCEL_PROJECT_PRODUCTION_URL` (answers Q2)
- "Available at: Both build and runtime… We select the shortest production custom domain, or vercel.app domain if no custom domain is available… this is always set, even in preview deployments. This is useful to reliably generate links that point to production such as OG-image URLs. The value does not include the protocol scheme https://." [CITED: system-environment-variables]
- System env vars depend on the project setting "Automatically expose System Environment Variables", which is on by default for new projects [ASSUMED]. The hard-coded fallback in D-08 covers the case where it's off.
- `vite.config.ts` runs in Node, so `process.env.VERCEL_PROJECT_PRODUCTION_URL` is readable there. It does **not** need a `VITE_` prefix, because it's never exposed to client code. [VERIFIED: local build with the env var set produced `https://foo.vercel.app/` in `dist/index.html`]

### 3. Node version (answers Q3)
- Available: **26.x (default), 24.x, 22.x**. The project setting applies to new deployments. `package.json` `engines.node` **overrides** the project setting: `24.x`/`^24.0.0` resolves to the latest 24.x, and `>=22.0.0` resolves to the latest 26.x. [CITED: vercel.com/docs/functions/runtimes/node-js/node-js-versions]
- `nodeVersion` is **not** a create-project body field. It's an update-project field, enum `"26.x","24.x","22.x",…`. So: `create_git_project`, then update-project `{ nodeVersion: "24.x" }`. With `engines: "24.x"` in place the build is pinned either way. The project setting is belt-and-braces and also what DEPLOY-01 asks for. [CITED: REST update-project]
- The lockfile records the old engines (`package-lock.json` `packages[""].engines = {"node": ">=22.12"}`) [VERIFIED: local]. After editing `package.json`, run `npm install --package-lock-only` (under Node 24) so the lock stays in sync.

### 4. Domain (answers Q6)
- `https://nfl-team-feelings.vercel.app/` currently returns `404` with `x-vercel-error: DEPLOYMENT_NOT_FOUND` [VERIFIED: curl 2026-11-11]. That suggests the subdomain isn't serving anything, but it doesn't prove it's unclaimed. Vercel normally assigns `<project-name>.vercel.app` and adds a suffix (team slug or random) when the name is taken [ASSUMED].
- After the first READY production deploy, read the real domain from MCP `get_project` (production alias / `targets.production` aliases) or `list_deployments` (the `alias` on the production deployment). Use the **project-level `*.vercel.app` alias**, not the per-deployment `nfl-team-feelings-<hash>-<team>.vercel.app` URL. If it differs from the fallback, update `FALLBACK_ORIGIN`, PROJECT.md and README. On Vercel builds `VERCEL_PROJECT_PRODUCTION_URL` already yields the right value, so a mismatched fallback only affects local builds.

### 5. Caching (confirms D-02)
- Vercel's default for static non-hashed files is `cache-control: public, max-age=0, must-revalidate` (seen on the live 404 response headers) [VERIFIED: curl]. `/data/*.json` revalidates on every load, so no `vercel.json` is needed.

## Standard Stack

No new runtime or dev dependencies. Everything uses what's already installed. [VERIFIED: web/package.json, node_modules/vite = 8.3.8]

| Tool | Version | Purpose |
|------|---------|---------|
| Vite `transformIndexHtml` plugin hook | 8.3.8 (installed) | `%SITE_ORIGIN%` substitution |
| vitest | 5.1.0 (installed) | Resolver unit test |
| Pillow (scratchpad only, `uv run --no-project --with pillow`) | latest from PyPI | One-off OG PNG. **Never added to the repo** |
| Vercel MCP | — | create/update project, list/get deployments, fetch |

**Installation:** none for the repo. Run `npm install --package-lock-only` after the engines edit.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| pillow | PyPI | 10+ yrs | very high | github.com/python-pillow/Pillow | not run | Approved for throwaway scratchpad use only (not a repo dependency). Installed and ran OK in this session |

**Packages removed:** none. **Flagged suspicious:** none. No packages are added to `web/` or `pipeline/`.

## Architecture Patterns

### System flow

```
git push main ──> GitHub ──> Vercel Git integration (depth-10 clone)
                                  │
                                  ▼  cwd = web/
                     ignore cmd: git diff --quiet ${PREV:-HEAD^} HEAD -- .
                       exit 0 ──> deployment CANCELED (pipeline/.planning-only push)
                       exit ≥1 ──> npm ci (Node 24.x) ──> vite build
                                           │  vite.config.ts reads process.env
                                           │  SITE_ORIGIN | https://VERCEL_PROJECT_PRODUCTION_URL | fallback
                                           ▼
                             transformIndexHtml(order:'pre') replaces %SITE_ORIGIN%
                                           ▼
                             dist/ (index.html with absolute og/twitter/canonical,
                                    assets/*, data/*.json, og-default.png)
                                           ▼
                             production alias https://<project>.vercel.app
                             ├─ crawler: reads static <head> tags + /og-default.png
                             └─ browser: SPA loads /data/meta.json → footer stamp
```

### Files touched
```
web/
├── index.html                 # <head> tags with %SITE_ORIGIN% placeholders
├── vite.config.ts             # siteOrigin() plugin, imports ./src/lib/siteOrigin.ts
├── package.json, package-lock.json  # engines 24.x
├── .nvmrc                     # 24
├── public/og-default.png      # 1200x630 (new)
└── src/
    ├── App.svelte             # <SiteFooter> rendered unconditionally
    ├── components/SiteFooter.svelte  # meta optional, disclaimer line
    └── lib/siteOrigin.ts (+ siteOrigin.test.ts)
README.md, .planning/PROJECT.md      # live URL, Node note
```

### Pattern 1: Build-time origin plugin (verified working)
```ts
// web/src/lib/siteOrigin.ts — pure, tested; also type-checked by svelte-check (src/**) and tsc (via import)
export const FALLBACK_ORIGIN = 'https://nfl-team-feelings.vercel.app'
export function resolveSiteOrigin(env: Record<string, string | undefined>): string {
  const explicit = env.SITE_ORIGIN?.trim()
  const vercel = env.VERCEL_PROJECT_PRODUCTION_URL?.trim()
  const raw = explicit || (vercel ? `https://${vercel}` : '') || FALLBACK_ORIGIN
  return raw.replace(/\/+$/, '')
}
```
```ts
// web/vite.config.ts
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { defineConfig, type Plugin } from 'vite'
import { resolveSiteOrigin } from './src/lib/siteOrigin.ts' // .ts extension REQUIRED (tsconfig.node: module nodenext + allowImportingTsExtensions)

function siteOrigin(): Plugin {
  const origin = resolveSiteOrigin(process.env)
  return {
    name: 'site-origin',
    transformIndexHtml: { order: 'pre', handler: (html) => html.replaceAll('%SITE_ORIGIN%', origin) },
  }
}
export default defineConfig({ plugins: [siteOrigin(), svelte()] })
```
I verified this in a scratch copy of `web/`: `npm run check` gave 0 errors and `tsc` passed. A 3-case vitest passed. A build with `VERCEL_PROJECT_PRODUCTION_URL=foo.vercel.app` gave `https://foo.vercel.app/`, and `SITE_ORIGIN` overrides it. No build warnings. [VERIFIED: local experiment]

**Why `order: 'pre'`:** Vite's build-html plugin treats `<meta property="og:image">`, `<meta name="twitter:image">` and `<link href>` (so `canonical` too) as **asset URLs** (`ALLOWED_META_PROPERTY`/`ALLOWED_META_NAME` in Vite 8 source). Pre hooks run before that asset scan, so Vite sees an absolute `https://…` URL and skips it as external. Default order also happened to work in the test, but `pre` is the order that doesn't depend on Vite's asset-resolution leniency. [VERIFIED: node_modules/vite/dist/node/chunks/node.js]

**Why not Vite's built-in `%ENV%` replacement:** it only substitutes keys in `import.meta.env`, which means `VITE_*`-prefixed vars, and it can't do the `https://` + fallback logic. `%SITE_ORIGIN%` has no `VITE_` prefix, so Vite leaves it alone and doesn't warn. The warning only fires for prefixed keys. [VERIFIED: Vite source `htmlEnvHook`]

### Pattern 2: index.html head (copy from UI-SPEC)
```html
<title>Feel-Good Score: how should you feel about your NFL team?</title>
<meta name="description" content="Every NFL team, ranked by how good their fans should feel right now. A momentum-weighted, backtested score with a mood label on top." />
<link rel="canonical" href="%SITE_ORIGIN%/" />
<meta property="og:type" content="website" />
<meta property="og:site_name" content="Feel-Good Score" />
<meta property="og:title" content="Feel-Good Score: how should you feel about your NFL team?" />
<meta property="og:description" content="(same as description)" />
<meta property="og:url" content="%SITE_ORIGIN%/" />
<meta property="og:image" content="%SITE_ORIGIN%/og-default.png" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:image:alt" content="Feel-Good Score: how should you feel about your NFL team?" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="Feel-Good Score: how should you feel about your NFL team?" />
<meta name="twitter:description" content="(same as description)" />
<meta name="twitter:image" content="%SITE_ORIGIN%/og-default.png" />
```
OG uses `property=`; Twitter uses `name=`. [CITED: ogp.me; X card markup, ASSUMED standard]

### Pattern 3: OG image (verified)
`uv run --no-project --with pillow python -I <scratchpad>/og.py web/public/og-default.png`. Face indices in `/System/Library/Fonts/HelveticaNeue.ttc` are **0 = Regular, 1 = Bold, 10 = Medium**. A test render (bar at y 200–208, 96px Bold wordmark, 44px Regular tagline) came out at **24 KB**, 1200×630 RGB, and the tagline measured 851px wide, under the 1008px limit, so it doesn't need to wrap. Center the block vertically with `font.getbbox()` instead of hard-coding y values. Keep the script in the scratchpad, never in the repo. [VERIFIED: local experiment]

### Pattern 4: Deploy ordering (fixes Pitfall 1)
1. Do all code tasks and commit. Run `npm test && npm run check && npm run build`, then grep `dist/index.html`.
2. `git push origin main`. Local main is 2+ commits ahead of origin.
3. MCP `create_git_project` (repo, name, rootDirectory `web`, framework `vite`, build/output/install), **without** `commandForIgnoringBuildStep`.
4. Update-project: `nodeVersion: "24.x"`.
5. `list_deployments`. If no production deployment started on creation, trigger one: an MCP deploy from the `main` ref if available, else push any commit. With no ignore command set yet, even an empty commit builds.
6. Wait for READY. Read the production alias and fix the fallback/docs if it differs (that's another `web/` commit, which builds).
7. Update-project: `commandForIgnoringBuildStep: 'git diff --quiet ${VERCEL_GIT_PREVIOUS_SHA:-HEAD^} HEAD -- .'`. Send it as a literal string; don't let a shell expand `${…}` when building the payload.
8. Push a `.planning/`-only commit. `list_deployments` should show it `CANCELED` (D-16).

### Anti-Patterns to Avoid
- Setting the ignore command at project creation. The first deploy has an empty `PREVIOUS_SHA`, falls back to `HEAD^`, and if HEAD is docs-only the deploy is canceled.
- Using `VERCEL_URL` for tags. It's the per-deployment protected host, and the docs say it's incompatible with Standard Deployment Protection.
- Verifying OG on a deployment URL or preview URL. Those sit behind Vercel Authentication (SSO `deploymentType` default `preview` / standard protection), and crawlers get 401. Verify on the production alias.
- Adding `vercel.json`, a catch-all rewrite or headers (D-02).
- A `VITE_SITE_ORIGIN` client env var. Not needed, and it would leak into the bundle.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Change detection for builds | Custom script / GitHub Action | Vercel Ignored Build Step with `git diff` | Built in, runs in the Root Directory, fails open |
| Production host discovery | Hard-coded-only URL | `VERCEL_PROJECT_PRODUCTION_URL` | Vercel picks the shortest prod domain and auto-follows a future custom domain |
| HTML templating | Post-build `sed` on `dist/index.html` | Vite `transformIndexHtml` | Also works in dev and preview, typed |

## Runtime State Inventory

Not a rename/refactor phase, so this section is omitted.

## Common Pitfalls

### Pitfall 1: The first production deploy gets canceled by the ignore step
**What goes wrong:** `PREVIOUS_SHA` is empty on the first deploy, so the command falls back to `HEAD^`. HEAD is a `.planning/` docs commit, the command exits 0, and the deploy is CANCELED.
**How to avoid:** Pattern 4 ordering. Set the command only after the first READY production deploy. If it happens anyway, redeploy with "Use project's Ignore Build Step" unchecked, or push a `web/` change.
**Warning signs:** The first entry in `list_deployments` has state `CANCELED`.

### Pitfall 2: More than 10 commits since the last deploy
**What goes wrong:** `PREVIOUS_SHA` isn't in the depth-10 clone. **Behavior:** exit 128, so it builds. That's harmless: fail-open, at worst one unneeded build. No action needed. Just don't "fix" it with `|| exit 0`, which would turn it into fail-closed.

### Pitfall 3: Shell expansion of `${VERCEL_GIT_PREVIOUS_SHA}` when writing the setting
**What goes wrong:** If the command passes through a shell with double quotes before the API call, it's stored as `git diff --quiet HEAD^ HEAD -- .`, and the multi-commit-push protection is lost.
**How to avoid:** Pass it as a literal JSON string. Read it back with `get_project` and confirm `${VERCEL_GIT_PREVIOUS_SHA:-HEAD^}` is intact.

### Pitfall 4: Production domain differs from the fallback
**What goes wrong:** The name is taken, Vercel adds a suffix, and local builds or README point to the wrong host.
**How to avoid:** Read the alias from `get_project`/`list_deployments` after READY, then update `FALLBACK_ORIGIN`, README and PROJECT.md. On Vercel builds the env var already yields the right value.

### Pitfall 5: Footer test coverage gap
**What goes wrong:** `SiteFooter` gets an optional `meta`. Svelte 5 `$props()` typing has to be `{ meta?: Meta }`, and the template has to guard with `{#if meta}`. Otherwise `svelte-check` fails or the error page crashes.
**How to avoid:** `npm run check`. Manually load the site with `public/data` temporarily unreachable (or check the logic path) to confirm the disclaimer renders under the fatal panel.

### Pitfall 6: Local Node version
nvm defaults to Node 20 (memory note). `npm run build` and `npm install --package-lock-only` should run under `nvm use` (24, after the `.nvmrc` change), or npm prints EBADENGINE warnings. Vitest probes in this session ran on Node 20.19 and still worked.

### Pitfall 7: Vercel GitHub app not installed
`create_git_project` may return requires_user_action. Follow D-17: record the dashboard URL as human_needed and finish everything else. The repo is **public** [VERIFIED: `gh repo view`], so a public-repo import may still need the app for push webhooks.

## Code Examples

### SiteFooter (per UI-SPEC)
```svelte
<script lang="ts">
  import { formatDate, formatDateOnly } from '../lib/format'
  import type { Meta } from '../lib/types'
  let { meta }: { meta?: Meta } = $props()
</script>

<footer class="site-footer">
  {#if meta}
    <p>
      <span class="part">Last updated {formatDate(meta.generated_at)}</span>
      <span class="part second">Data through {formatDateOnly(meta.data_through)}</span>
    </p>
  {/if}
  <p class="disclaimer" class:solo={!meta}>
    Unofficial fan project — not affiliated with the NFL. Data: <a href="https://github.com/nflverse">nflverse</a>.
  </p>
</footer>
<!-- .disclaimer { margin-top: var(--space-xs) } .solo { margin-top: 0 }; reset default <p> margins as the existing single <p> does today -->
```
In `App.svelte`, replace the guarded block with `<SiteFooter meta={status === 'ready' && meta ? meta : undefined} />`.

### Production checks (D-15)
```bash
U=https://<alias>
curl -s $U/ | grep -E 'og:image|twitter:card|canonical|<title>'
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' $U/data/meta.json   # 200 application/json
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' $U/og-default.png   # 200 image/png
curl -s -A 'facebookexternalhit/1.1' $U/ | grep og:title                     # crawler UA sees static tags
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `engines: ">=22.12"` | `"24.x"` | `>=` floats to 26.x, the current Vercel default |
| `git diff HEAD^ HEAD` ignore | `${VERCEL_GIT_PREVIOUS_SHA:-HEAD^}` | Catches multi-commit pushes. Needs the first-deploy ordering fix |
| Node 20 | Deprecated on Vercel 2026-10-01 | Don't use it |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | "Automatically expose System Environment Variables" is on by default for new projects | Fact 2 | Low. The hard-coded fallback still yields the right URL if the domain matches |
| A2 | Vercel assigns `nfl-team-feelings.vercel.app`, or a suffixed variant if taken | Fact 4 | Low. Discovered after deploy, then the fallback and docs are updated |
| A3 | `create_git_project` may or may not trigger an initial deployment | Pattern 4 | Low. Step 5 handles both cases |
| A4 | Vercel MCP tool names/shapes (`create_git_project`, update project, `list_deployments`, `get_project`, `web_fetch_vercel_url`) match CONTEXT | Pattern 4 | Medium. The executor should inspect the tool schemas and use `vercel api` CLI fallbacks if a tool is missing (but the CLI token is invalid, so it's human_needed) |

## Open Questions

1. **Does `create_git_project` accept `commandForIgnoringBuildStep` / `nodeVersion` directly?** The REST create endpoint takes the former but not the latter. Recommendation: create the project minimal, then do separate update calls (Pattern 4).
2. **Does project creation auto-deploy?** Unknown. Check `list_deployments` right after creation.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node 24 (nvm) | build, lockfile refresh | ✓ | v24.20.0 | 22.23.3 also installed |
| uv | OG image script | ✓ | 0.10.12 | — |
| Pillow (via uv) | OG image | ✓ (downloads on demand) | latest | — |
| HelveticaNeue.ttc | OG image | ✓ | Regular idx 0, Bold idx 1 | Helvetica.ttc |
| gh + push access | D-04 push | ✓ | repo public, main default | — |
| Vercel MCP | project create/verify | deferred tools (not probed) | — | human_needed per D-17 |
| Vercel GitHub app on repo | auto-deploys | unknown | — | human_needed per D-17 |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | vitest 5.1.0 (unit tests in `web/src/lib/*.test.ts`) |
| Config file | none. Defaults via `vite.config.ts` |
| Quick run command | `cd web && npm test` |
| Full suite command | `cd web && npm test && npm run check && npm run build && grep -c '%SITE_ORIGIN%' dist/index.html` (expect `0`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEPLOY-01 | Engines/.nvmrc pinned to 24 | static | `node -p "require('./web/package.json').engines.node"` → `24.x`; `cat web/.nvmrc` → `24` | ✅ |
| DEPLOY-01 | Prod URL serves the site; project root `web`, Node 24.x | smoke (prod) | `curl -s -o /dev/null -w '%{http_code}' $U/` → 200; MCP `get_project` shows `rootDirectory: web`, `nodeVersion: 24.x` | n/a |
| DEPLOY-02 | `web/` push builds; `.planning/` push is canceled | smoke (prod) | MCP `list_deployments`: the phase code commit is READY, the docs commit is CANCELED; `get_project` shows the ignore command intact | n/a |
| DEPLOY-03 | Origin resolver order + trailing slash | unit | `cd web && npx vitest run src/lib/siteOrigin.test.ts` | ❌ Wave 0 |
| DEPLOY-03 | Tags present and absolute in built HTML | build grep | `grep -E 'og:image" content="https://.*/og-default.png' web/dist/index.html && grep -q 'twitter:card" content="summary_large_image' web/dist/index.html` | n/a |
| DEPLOY-03 | OG image 1200×630 PNG < 300 KB | static | `file web/public/og-default.png` (1200 x 630); `stat -f%z` < 307200 | ❌ (created in phase) |
| DEPLOY-03 | Footer disclaimer on every page incl. error; "Data through" stamp | check + manual/prod | `npm run check`; `grep -r 'not affiliated with the NFL' web/dist/assets/*.js`; prod visual check | n/a |
| DEPLOY-03 | Tags visible to crawler on prod | smoke (prod) | `curl -s -A facebookexternalhit/1.1 $U/ \| grep og:image`; `curl -sI $U/og-default.png` → `image/png` | n/a |

### Sampling Rate
- **Per task commit:** `npm test && npm run check`
- **Per wave merge:** full suite command above
- **Phase gate:** full suite plus the production smoke checks, before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `web/src/lib/siteOrigin.test.ts`: covers DEPLOY-03 resolver (SITE_ORIGIN wins, Vercel host gets `https://`, empty falls back, trailing slash stripped)

## Security Domain

Omitted: `security_enforcement: false` in `.planning/config.json`. Relevant notes are already covered: no secrets are involved, previews stay protected, and only the production alias is public.

## Sources

### Primary (HIGH)
- vercel.com/docs/project-configuration/project-settings: Ignored Build Step exit codes, cwd, CANCELED, quota note
- vercel.com/kb/guide/how-do-i-use-the-ignored-build-step-field-on-vercel: `--depth=10`, `-- .` example
- vercel.com/docs/environment-variables/system-environment-variables: `VERCEL_PROJECT_PRODUCTION_URL`, `VERCEL_GIT_PREVIOUS_SHA`, `VERCEL_URL`
- vercel.com/docs/functions/runtimes/node-js/node-js-versions: 26/24/22, engines override table
- vercel.com/docs/rest-api/reference/endpoints/projects/{create-a-new-project, update-an-existing-project}: `commandForIgnoringBuildStep`, `nodeVersion` enum, `ssoProtection`
- Vite 8.3.8 source (`web/node_modules/vite/dist/node/chunks/node.js`): `htmlEnvHook`, `ALLOWED_META_PROPERTY`, hook ordering
- Local experiments (scratchpad copy of `web/`, depth-10 clone, Pillow render, curl of the vercel.app host)

### Tertiary (LOW)
- Default vercel.app naming and suffix behavior (training knowledge)

## Metadata

**Confidence breakdown:**
- Vercel mechanics: HIGH (official docs plus local reproduction of the git semantics)
- Vite plugin approach: HIGH (built and type-checked in a scratch copy)
- MCP tool specifics and domain naming: MEDIUM/LOW (not probed; handled by the ordering and discovery steps)

**Research date:** 2026-11-11
**Valid until:** 2026-12-11

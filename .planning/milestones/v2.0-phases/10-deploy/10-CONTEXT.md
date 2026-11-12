# Phase 10: Deploy - Context

**Gathered:** 2026-11-11
**Status:** Ready for planning
**Mode:** Smart discuss, FULL AUTONOMY. Every grey area was auto-accepted at the recommended answer (no AskUserQuestion). Each decision below is logged with its rationale.

<domain>
## Phase Boundary

Put the existing v1 site on a public Vercel production URL, keep it current by itself, and add the minimum public-site furniture: a freshness stamp, site-wide preview tags and a disclaimer footer.

Delivers:
- Vercel project `nfl-team-feelings` (team `noah-manions-projects`, teamId `team_E1xIuSsRXZzQn824H0Sb2J0S`), Git-connected to `github.com/noahmanion/nfl-team-feelings`, root directory `web`, with an ignored-build step scoped to `web/`.
- Node pinned to 24.x everywhere (`web/package.json` engines, `web/.nvmrc`, Vercel project setting).
- Site-wide `<title>`, description, Open Graph and Twitter tags in `web/index.html`, plus one static default share image.
- A "data through" stamp and a disclaimer footer on every page.
- The production URL recorded in `.planning/PROJECT.md` and `README.md`.

Out of bounds:
- Any restyle or redesign (that is Phase 12).
- Per-team or per-callout share pages and cards (Phase 14).
- Logos (Phase 11 and 12).
- Any change under `pipeline/` (especially model code and `pipeline/PREREGISTRATION*.md`).
- A server runtime, SSR, or a router change.

</domain>

<decisions>
## Implementation Decisions

### Area 1: Vercel project & build config
- D-01 Create the project with the Vercel MCP `create_git_project` (the CLI token is invalid). Settings: repo `noahmanion/nfl-team-feelings`, projectName `nfl-team-feelings`, rootDirectory `web`, framework `vite`, build `npm run build`, output `dist`, install `npm ci` (the default; `package-lock.json` is committed), Node 24.x. Rationale: this is the decided route. Pitfall 7 says root must be `web`.
- D-02 No `vercel.json`. Hash routing needs no rewrites, and a catch-all rewrite would hide Phase 14's share pages. Vercel's defaults already cache only hashed `/assets/*` long-term, so nothing gives `/data/*` a long `max-age`. Rationale: research says "no vercel.json rewrites" and "no long max-age on /data/*". Zero config is the least that can go wrong.
- D-03 Ignored-build command, set on the project (root dir `web`): `git diff --quiet ${VERCEL_GIT_PREVIOUS_SHA:-HEAD^} HEAD -- .`. Exit 0 (no change under `web/`) skips the build; any diff or any git error (e.g. the previous SHA is missing from the shallow clone) exits non-zero and builds. Rationale: comparing against the last *deployed* SHA catches a multi-commit push where `web/` changed in an earlier commit. Falling back to `HEAD^` matches the decided command. Failing open (build) is the safe direction.
- D-04 Push the Phase 10 code to `main` before (or as) the project is connected, so the production deployment builds the committed site with the new tags. Rationale: the decided order. The first production deploy should be the real one.

### Area 2: Node pinning
- D-05 `web/package.json` `engines.node` = `"24.x"`. `web/.nvmrc` = `24` (nvm has v24.20.0 installed locally). The Vercel project's Node version = `24.x`. Local dev on 22.12+ still works (engines isn't enforced by npm without `engine-strict`). Rationale: `>=22.12` would float to Node 26 on Vercel (Pitfall 7). All three places agree on one major.
- D-06 The README "Run it" note changes from "Node >=22.12" to "Node 24, pinned by web/.nvmrc".

### Area 3: Site-wide share tags (DEPLOY-03)
- D-07 Static tags in `web/index.html`: `<title>Feel-Good Score: how should you feel about your NFL team?</title>`, `meta name="description"`, `og:type=website`, `og:site_name`, `og:title`, `og:description`, `og:url`, `og:image` (+ `og:image:width` 1200, `og:image:height` 630, `og:image:alt`), `twitter:card=summary_large_image`, `twitter:title`, `twitter:description`, `twitter:image`, and `link rel="canonical"`. The description stays under ~200 characters, with no emoji and no unescaped quotes (Pitfall: copy in tags).
- D-08 Absolute URLs come from one build-time origin: a tiny Vite plugin (`transformIndexHtml`) in `vite.config.ts` replaces a `%SITE_ORIGIN%`-style placeholder. Resolution order: `SITE_ORIGIN` env → `https://` + `VERCEL_PROJECT_PRODUCTION_URL` (a Vercel system env var at build time) → the hard-coded production origin (`https://nfl-team-feelings.vercel.app`, corrected after the project exists if Vercel assigns a different domain). No trailing slash. Rationale: research picked `VERCEL_PROJECT_PRODUCTION_URL` → `SITE_ORIGIN` → fallback. Phase 14 will reuse the same resolver. Preview builds still point at the production domain, which is what crawlers can reach (previews sit behind Vercel login).
- D-09 Default share image: one static `web/public/og-default.png`, 1200×630, under ~300 KB. It shows the wordmark "Feel-Good Score" plus the tagline on a plain background, using the current site colors. No logos, no NFL marks, no emoji. Generate it once with a throwaway script (e.g. Pillow via `uv run --with pillow` in the scratchpad) and commit only the PNG. Rationale: "simple static default PNG for now". Satori cards are Phase 14.
- D-10 The tags stay site-wide and static. Nothing per-route (crawlers can't see hash routes anyway). The page `<title>` doesn't change per route in this phase.

### Area 4: Freshness stamp & disclaimer footer
- D-11 Freshness stamp: keep the existing `SiteFooter` "Data through {formatDateOnly(meta.data_through)}" (from `meta.json`, already rendered on every route via `App.svelte`). Phase 10 makes sure it is on every page and reads "Data through …". No new data field and no pipeline change. Rationale: it already exists and is accurate. Duplicating it in the header would be restyling (Phase 12).
- D-12 Disclaimer: add one line to `SiteFooter`: "Unofficial fan project — not affiliated with the NFL. Data: nflverse." ("nflverse" links to https://github.com/nflverse). Fold the existing "Source: nflverse" link into it so the source isn't stated twice. Use the existing footer styles (muted label text) and no new design tokens. Rationale: decided copy, minimal visual change.
- D-13 The disclaimer must show even when data fails to load. Render the static disclaimer line outside the `status === 'ready'` guard, and keep the data-dependent stamps (last updated, data through) inside it. Rationale: "every page" includes the fatal-error page, and the disclaimer doesn't depend on data.
- D-14 Tests: extend or add a vitest unit test only where logic exists (e.g. the origin resolver, if it's a pure function in a small module). Verify the footer and tags through `npm run build` plus a grep on `dist/index.html`, and through a fetch of the production URL. No new e2e harness. Rationale: CLAUDE.md "light process". Existing tests must keep passing (`npm test`, `npm run check`, `npm run build`).

### Area 5: Verification & records
- D-15 Verify production by fetching the production URL (Vercel MCP `web_fetch_vercel_url` or plain HTTP). Confirm the HTML has the tags, `/data/meta.json` returns 200 JSON, and `/og-default.png` returns 200 `image/png`. Use `list_deployments` / `get_deployment` to confirm the production deployment is READY and built from the pushed commit.
- D-16 Verify the ignored-build step with a pipeline-only or planning-only commit pushed after deploy. Its deployment should show as canceled/skipped by the ignore step (`list_deployments`). If an appropriate commit doesn't occur naturally, the phase-completion docs commit (`.planning/` only) serves as the test. Rationale: success criterion 2 needs evidence. A `.planning/` commit touches nothing under `web/`.
- D-17 If the Vercel GitHub app isn't installed for the repo, or any MCP step returns requires_user_action, finish everything else and record the exact single user action (with dashboard URL) as a human_needed item. Don't block the phase.
- D-18 Record the production URL in `.planning/PROJECT.md` (Hosting constraint + a Key Decisions row) and in `README.md` (a "Live site" line at the top).

### Claude's Discretion
- The exact title and description wording (within D-07's limits) and the og image's typography and layout.
- Whether the origin resolver lives inline in `vite.config.ts` or in a small tested module.
- The footer markup details, as long as the existing styles and responsive line breaks are kept.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `web/src/components/SiteFooter.svelte` already renders "Last updated {generated_at}" and "Data through {data_through} · Source: nflverse" using `formatDate`/`formatDateOnly` from `web/src/lib/format.ts`.
- `web/public/data/meta.json` has `generated_at` and `data_through` (currently 2026-11-09, latest 2026 W9).
- `web/public/favicon.svg` exists.

### Established Patterns
- Svelte 5 runes, component-scoped `<style>` with CSS custom properties from `web/src/app.css` (`--text-muted`, `--text-label`, `--space-*`).
- Hash routing (`web/src/lib/router.ts`). All five routes render inside `App.svelte`'s `.page` wrapper, and `<SiteFooter>` is rendered once at the bottom, guarded by `status === 'ready' && meta`.
- Tests: vitest unit tests on `src/lib/*.ts` (pure functions). There are no component tests.
- `vite.config.ts` is the bare Svelte plugin config.

### Integration Points
- `web/index.html` `<head>`: the tags go here.
- `web/vite.config.ts`: the origin placeholder plugin.
- `web/package.json` `engines` and `web/.nvmrc` (currently `22`).
- Vercel project settings (MCP), the GitHub repo `main` branch.
- `README.md` (repo root = `feel-good-scorew/`) and `.planning/PROJECT.md`.

</code_context>

<specifics>
## Specific Ideas

- Footer copy, verbatim: "Unofficial fan project — not affiliated with the NFL. Data: nflverse."
- The ignored-build step must leave pipeline-only commits unbuilt, but changes to `web/public/data/` (the weekly data refresh) must build.
- The Vercel Hobby plan is non-commercial: no ads or affiliate links.

</specifics>

<deferred>
## Deferred Ideas

- Per-route `<title>` updates (nice for tabs and history). Phase 12 or 14.
- A "new week, reload" version-skew banner (Pitfall: open tabs across a weekly deploy). Later phase.
- A custom domain. Not requested.
- Per-team and per-callout share pages and cards. Phase 14.

</deferred>

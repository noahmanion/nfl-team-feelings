# Phase 14: Share Cards & Launch Verification - Research

**Researched:** 2026-11-12
**Domain:** Build-time OG image rendering (satori + resvg), static share pages on Vercel, copy-link wiring, social crawler verification
**Confidence:** HIGH for the stack, rendering, Node and TypeScript interop, and Vercel static serving (all verified live this session). MEDIUM for real-platform crawler behavior (closed by human UAT).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Rendering pipeline (SHARE-01)
- D-01: Node post-build script `web/scripts/share.mjs` (+ `web/scripts/og-template.mjs` for the satori element trees) runs after `vite build`; `package.json` build becomes `vite build && node scripts/share.mjs`. Not a Vite plugin (keeps the render step testable and separately timeable).
- D-02: `satori` pinned to an exact version (verify the current 0.x release at plan time; research said 0.63.2) and `@resvg/resvg-js` pinned exactly (2.6.2 or current), both devDependencies. No `@vercel/og`, no `sharp`, no JSX toolchain: plain `{type, props}` objects.
- D-03 (amended by UI-SPEC revision 1): Fonts are the static WOFF files already in node_modules, two weights only: `@fontsource/inter` `inter-latin-{400,700}-normal.woff` and `@fontsource/ibm-plex-mono` `ibm-plex-mono-latin-{400,700}-normal.woff`. Never WOFF2 or the variable package. Read with `fs` from `node_modules/@fontsource/...` (resolved via `createRequire`/`import.meta.resolve`).
- D-04: Logos come from `web/public/logos/{FR}.png` (local files, read as base64 data URIs). If `VITE_LOGOS=off` (existing `logosOff` switch) or a logo file is missing, the card falls back to the team-color chip (primary/secondary from meta.teams) — mirrors `TeamLogo` → `TeamChip`.
- D-05: Emoji are DROPPED from cards (no Twemoji, no network at build). The mood band color (Phase 12 `--mood-0..6` light tokens) carries the mood visually; the label text carries it verbally. A vitest test renders a card for each of the 7 band labels (incl. "It’s fine. Everything’s fine." with U+2019) and asserts non-empty PNG output and that every character of the label is covered by the loaded fonts (no tofu / missing-glyph path).
- D-06: A site-default card is rendered by the same template and overwrites `dist/og-default.png` (index.html keeps pointing at `/og-default.png`), so the site-level preview matches the card design. The committed `public/og-default.png` stays as the no-script fallback.
- D-07: Card colors/typography are copied from Phase 12 tokens into one exported constant object in `og-template.mjs` (light theme only — share previews render on unknown backgrounds); a test asserts the mood colors match `app.css` `--mood-*` values so they cannot drift.

#### Card content (SHARE-01, design follows Phase 12 system)
- D-08: Team card: team logo, era-correct team name, big score (IBM Plex Mono) out of 100, mood label in bold Inter on a band-colored bar/stripe, rank + record line (e.g. "#2 of 32 · 7-1"), date stamp "Week 9 · 2026" (week label from meta.seasons[].week_labels), site name "Feel-Good Score" + bare domain. One claim, one supporting number, logo, site name, date (research FEATURES must-have).
- D-09: Callout card: team logo + name, the callout headline as the one claim (largest text), the detail line as the supporting number, a type kicker ("Worried", "Hopeful", "Misery", "Joy", "Rising", "Falling"), the band stripe color, date stamp, site name + domain. Era text via the same `eraName`/`eraText` rules (callouts are current-season so this is mostly a no-op, but reuse the helpers if importable as erasable TS, else port the minimal logic).
- D-10: Long text is clamped: headline max 2 lines with ellipsis, detail max 2 lines; team names never truncated (font size steps down for long names like "Jacksonville Jaguars" if needed).

#### Share URL scheme & IDs (SHARE-02)
- D-11: One slug module `web/src/lib/share.ts` — erasable TypeScript only, no imports except other `.ts` files with explicit extensions — imported by both the app and `share.mjs` (Node 24 strips types natively). It exports the path builders, image path builders, hash targets, the launch constant and `hasSharePage`.
- D-12: Team share page: `/s/team/{FR}/{season}-w{week}/` (FR uppercase canonical franchise code, week unpadded), image `/og/team/{FR}/{season}-w{week}.png`. Hash target `#/team/{FR}/{season}/{week}` (existing `teamHash`).
- D-13: Callout share page: `/s/c/{season}/{week}/{FR}-{type}/` with type kebab-cased (`mover_up` → `mover-up`), image `/og/c/{season}/{week}/{FR}-{type}.png`. Stable callout ID = `{season}/{week}/{FR}-{type}` — verified unique: 0 duplicate (season, week, franchise, type) across all 28 committed snapshots. Hash target = `calloutHref(c)` (the team's season/week route).
- D-14: Images carry season+week in the filename so social caches never serve a stale card for a new week.

#### Share page HTML (SHARE-02)
- D-15: Static `index.html` per share page: `<title>`, meta description, `og:type=article`, `og:site_name`, `og:title`, `og:description`, `og:url` = the share page itself (absolute), `og:image` absolute on the production origin + `og:image:width/height/alt/type`, `twitter:card=summary_large_image` + twitter title/description/image, `link rel=canonical` = the share page. Every interpolated field HTML-escaped (`&<>"'`) via one `escapeHtml` in share.ts with a test using hostile input.
- D-16: Origin: reuse Phase 10's `resolveSiteOrigin(process.env)` (SITE_ORIGIN → VERCEL_PROJECT_PRODUCTION_URL → production fallback). Note: the existing helper's final fallback is the production origin, not localhost — keep it (local builds produce prod-pointing tags, which is what crawlers need; local preview still works because the redirect is root-relative).
- D-17: Redirect: inline `<script>location.replace('/' + HASH)</script>` (root-relative so it works on localhost/preview) — no meta refresh. Visible fallback: short branded line + "Open {Team} on Feel-Good Score →" link to the same hash route, with minimal inline CSS using Phase 12 colors/fonts (system font stack fallback; no JS bundle).
- D-18: Pages are regenerated every build into `dist/s/` and `dist/og/`; nothing generated is committed. No vercel.json rewrites (a catch-all would shadow `/s/`).

#### Durability & build budget
- D-19: `SHARE_LAUNCH = { season: 2026, week: 9 }` in share.ts. Each build generates team + callout pages/images for every (season, week) present in committed snapshots with (season, week) ≥ launch — so links shared in launch week keep resolving all season. Pre-launch weeks get no share pages (copy falls back to hash link).
- D-20: Measure render time per card and total share-step time; log both from the script. Budget: share step ≤ 60 s at launch; project the full-season count (~14 weeks × ~45 cards). If the projection exceeds ~3 min, render with a small worker/concurrency pool; if still too slow, keep pages for all weeks but images only for weeks ≥ launch that fit, and document. Record actual numbers in SUMMARY.
- D-21: Team cards for a week use that week's snapshot row (score, band, label, rank, record); callout cards use that week's callouts list (all six types, including movers).

#### Copy-link wiring (SHARE-03)
- D-22: `CalloutCard` copy button copies `location.origin + calloutSharePath(c)` when `hasSharePage(c.season, c.week)`, else the existing `deepLink(href)`.
- D-23: Team page gets a new "Copy link" button in its header (same component pattern/status/manual-fallback behavior as CalloutCard — extract a small shared `CopyLinkButton.svelte` if it reduces duplication). It copies the team share URL for the viewed (season, week) (latest when the hash has no season/week) when `hasSharePage`, else the hash deep link.
- D-24: `hasSharePage(season, week)` = (season, week) ≥ SHARE_LAUNCH and that week exists in the loaded data (the build generates pages for exactly that set). Share URLs use `location.origin` so preview/local copies work; the tags on the page always point at production.

#### Launch verification
- D-25: After push + Vercel READY, fetch one team share page and one callout share page on production with `facebookexternalhit/1.1`, `Twitterbot/1.0` and `Slackbot-LinkExpanding 1.0` UAs; assert 200, og:image/og:url/twitter:card present and absolute, and the og:image URL returns 200 image/png. Report 403s from Vercel bot protection honestly.
- D-26: Real Slack / iMessage / X pastes and the Facebook Sharing Debugger / LinkedIn Post Inspector are human UAT items in `14-HUMAN-UAT.md` with the exact URLs to paste.

### Claude's Discretion
- Exact card layout geometry, font sizes, stripe vs bar treatment (UI-SPEC decides within the Phase 12 system).
- Whether to extract `CopyLinkButton.svelte` or duplicate the small logic.
- Concurrency mechanism if D-20 needs it.

### Deferred Ideas (OUT OF SCOPE)
- Twemoji emoji on cards (would need vendored SVGs + CC-BY attribution).
- Dark-theme card variant.
- Share cards for records/explore/history pages; Web Share API and download buttons.
- Pruning of very old share weeks once per-season build time grows (revisit next season).

**UI-SPEC (approved) is also binding:** card geometry, the `CARD` token object, the 4-size type scale, `clampText(s, 68/110)`, `cardRuns` arrow splitting, the logo/chip fallback, the share page HTML template, the `CopyLinkButton.svelte` extraction with props `{ getUrl, name, ariaLabel? }`, and the copy contract. See `14-UI-SPEC.md`.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SHARE-01 | Each build generates 1200×630 share images (satori + resvg) for all 32 teams and the current season's callouts, using the redesign's fonts, colors and local logos | satori 0.63.2 + resvg-js 2.6.2 verified. A live spike rendered 424 real cards (all 2026 weeks) at about 10 ms/card with the four WOFF files and local logos. `loadAdditionalAsset` gives a missing-glyph guard. Memory leak fix and `loadSystemFonts:false` speedup (see Pitfalls 1 and 2). |
| SHARE-02 | Each share image has a static share page at a real path that includes the season and week, with absolute og tags on the production domain, and a JS redirect to the matching hash route | Vercel serves `dir/index.html` at both `/dir/` and `/dir` by default (cited). `VERCEL_PROJECT_PRODUCTION_URL` is available at build time and set even on previews (cited). Production currently returns 200 to all four crawler UAs (probed). `share.ts` can be imported by Node 24 directly (verified). |
| SHARE-03 | The copy-link buttons on team pages and callouts copy the share-page URL where one exists and fall back to the hash link otherwise | Pure `hasSharePage` and URL builders in `share.ts` are testable in vitest. `CalloutCards` already receives `meta`, so `CalloutCard` can receive it as a prop. A `.ts`-extension import needs `allowImportingTsExtensions` in `tsconfig.app.json` (verified TS5097 without it). |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Work only inside `feel-good-scorew/`. Keep everything self-contained, with no root-level manifests and no shared deps with other repo projects.
- Keep it light: favor quick prototypes, no heavy CI or test suites. Vitest unit tests on pure helpers are the established pattern.
- **Don't touch `pipeline/` model code.** This phase is `web/` only.
- Web toolchain: `cd web && source ~/.nvm/nvm.sh && nvm use 24`. The nvm default is Node 20, which **cannot** import `.ts` files. A spike run under the default Node silently produced nothing (see Pitfall 6).
- Frontend stack: Vite 8 + Svelte 5 (plain) + TypeScript ~6.0.3 (don't move to TS 7, because svelte-check peers on 5 or 6). Hash routing, and no `vercel.json` rewrites.
- Data: free and local only. No network at build time: logos and fonts come from the repo or node_modules.
- GSD workflow: edits happen through `/gsd-execute-phase`.
- User memory: v1 weights are frozen, and full autonomy means decide without asking.

## Summary

The locked stack works end to end, and it's faster than earlier research assumed. Two settings matter a lot. In the live spike, satori 0.63.2 plus @resvg/resvg-js 2.6.2 rendered 1200×630 cards with the four static WOFF files and the local 500 px logos. Satori takes about 2–4 ms per card. With default options, resvg takes about **60 ms per card, almost all of it spent scanning system fonts**. Passing `font: { loadSystemFonts: false }` drops resvg to about 8 ms, and the output doesn't change, because satori already converts all text to `<path>` (`embedFont` defaults to true). A realistic full run over every 2026 week (424 cards) took **4.2 s total (9.9 ms/card) on an Apple M5**. Cards were 32 KB on average and 58 KB at most, well under the 300 KB cap. Vercel Hobby builds on a Basic machine (2 vCPU, 8 GB) [CITED: vercel.com/docs/builds/managing-builds]. Even at 3–4× slower, the full-season projection (weeks 9–22 × ~45 cards ≈ 630 cards) is about 20–30 s, so **no concurrency pool is needed** (D-20).

The second finding is a real hazard. **resvg-js keeps about 3 MB of native memory per render** (one 1200×630 RGBA pixmap) until V8 garbage-collects the JS wrapper. The JS heap stays tiny, so V8 never collects on its own. RSS grew to 2.1 GB over 1,272 cards. Running `gc()` every ~25 cards and then yielding to the event loop (`await setImmediate()`) keeps RSS flat at about 165 MB at no measurable time cost. Run `share.mjs` with `node --expose-gc`. Under D-19, pages accumulate across seasons, so without this fix the build would eventually hit the 8 GB Basic machine limit.

For glyph coverage, satori's own `loadAdditionalAsset(languageCode, segment)` callback is the lightest guard. It fires **only** for characters that no loaded font covers. In the spike it fired for `→` and `✓` (`"symbol"`) and for `🎉` (`"emoji"`), and stayed silent for `’ · – − … #`. Throwing from it rejects the `satori()` promise, which fails the build. A scan of every 2024–2026 callout and band label found only three non-ASCII characters (`’ → −`), and `→` is the only one missing from both fonts, which matches the UI-SPEC. Node 24.20 strips types by default (`process.features.typescript === 'strip'`, with no warning). `teamNames.ts`, `router.ts`, `format.ts`, `siteOrigin.ts` and `logoSwitch.ts` import directly from a `.mjs` today. `callouts.ts` and `logos.ts` fail with ERR_MODULE_NOT_FOUND because they use extensionless *value* imports. Extensionless `import type` lines are fine because they're erased.

**Primary recommendation:** Pin `satori@0.63.2` and `@resvg/resvg-js@2.6.2` exactly. Render with `new Resvg(svg, { fitTo: { mode: 'original' }, font: { loadSystemFonts: false } })`, run the script as `node --expose-gc scripts/share.mjs` with a `gc()` + `setImmediate` yield every 25 cards, and guard glyphs by throwing from `loadAdditionalAsset`. Add `"allowImportingTsExtensions": true` to `tsconfig.app.json`, so `share.ts` can `import { teamHash } from './router.ts'` per D-11.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Card PNG rendering (satori → resvg) | Build step (Node post-build script) | — | Data changes weekly, the output is fully static, and there's no runtime |
| Share page HTML (og/twitter tags + JS redirect) | Build step → CDN/Static (`dist/s/**`) | — | Crawlers need tags in the served HTML; hash routes are invisible to them |
| Absolute origin for tags | Build step (`resolveSiteOrigin(process.env)`) | — | `VERCEL_PROJECT_PRODUCTION_URL` exists at build time |
| Serving `/s/**` and `/og/**` | CDN/Static (Vercel) | — | Default directory-index serving; no vercel.json |
| Slug/path/hash rules + `hasSharePage` | Shared pure module (`src/lib/share.ts`) | Browser + Build | One rule used by both the app and the script, so they can't drift |
| Copy-link URL selection | Browser (`CopyLinkButton.svelte` + `share.ts`) | — | Uses `location.origin` at click time |
| Redirect share page → hash route | Browser (inline script on the share page) | — | Crawlers don't run JS; humans do |
| Launch verification | External (curl with crawler UAs; human UAT) | — | Real platform behavior can only be observed |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| satori | **0.63.2** (published 2026-10-20) [VERIFIED: npm registry] | `{type, props}` tree → SVG with flexbox + font shaping | The engine behind @vercel/og. 8.16M downloads/week [VERIFIED: api.npmjs.org]. Repo github.com/vercel/satori. Engines node >=16. |
| @resvg/resvg-js | **2.6.2** [VERIFIED: npm registry] | SVG → PNG (native napi) | The standard satori companion. 7.25M downloads/week. Repo github.com/yisibl/resvg-js. Prebuilt optional deps for darwin-arm64 and linux-x64-gnu (Vercel). No postinstall script [VERIFIED: npm view]. |

### Already installed (reuse)
| Library | Version | Purpose |
|---------|---------|---------|
| @fontsource/inter | 5.3.0 (devDep) | `files/inter-latin-{400,700}-normal.woff`, resolvable through the package `exports` `./files/*` [VERIFIED: createRequire.resolve] |
| @fontsource/ibm-plex-mono | 5.3.0 (dep) | `files/ibm-plex-mono-latin-{400,700}-normal.woff` [VERIFIED] |
| vite | ^8.3.6 | `loadEnv` lets share.mjs read `VITE_LOGOS` the same way `vite.config.ts` does |
| vitest | ^5.1.0 | Verified: vitest 5.1.0 runs a `.test.mjs` that imports satori, resvg-js native and a `src/lib/*.ts` file in about 120 ms |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| @resvg/resvg-js (native) | @resvg/resvg-wasm 2.6.2 | Only if Vercel's image can't load the native binary. wasm-bindgen finalizers have the same GC-timing leak class. |
| Sync `new Resvg().render()` | `renderAsync` × 4 concurrency | Measured 5.3 vs 8.1 ms/card. Not worth the complexity at this scale. |
| `loadAdditionalAsset` glyph guard | fontkit/opentype.js cmap parse | Adds a dependency. satori already does this check internally. |

**Installation:**
```bash
cd web && source ~/.nvm/nvm.sh && nvm use 24
npm install -D --save-exact satori@0.63.2 @resvg/resvg-js@2.6.2
grep -c '"node_modules/@resvg/resvg-js-linux-x64-gnu"' package-lock.json   # must be 1 (Vercel binary recorded)
```

## Package Legitimacy Audit

slopcheck could not be installed in this environment (`pip install slopcheck` produced no binary), so per protocol both packages are tagged **[ASSUMED]** for slopcheck status. Both are long-established, very high-download packages from known orgs, and both were chosen in the project's own earlier research.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| satori | npm | multi-year (0.x line, 0.63.2 on 2026-10-20) | 8.16M/wk | github.com/vercel/satori | unavailable [ASSUMED] | Approved (pin exact). Planner may add a `checkpoint:human-verify` per protocol. |
| @resvg/resvg-js | npm | multi-year (2.6.2) | 7.25M/wk | github.com/yisibl/resvg-js | unavailable [ASSUMED] | Approved (pin exact) |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none. No postinstall scripts on either package.
**npm audit note:** satori ≥0.33 depends on `fflate` 0.7.3, which has a moderate advisory (GHSA-px8p-9vwx-vf98, ZIP64 `unzipSync` infinite loop). It isn't reachable here: there's no untrusted ZIP input, it's build-time only, and the fonts come from node_modules. **Do not run `npm audit fix --force`**, because it downgrades satori to 0.32.0 (breaking).

## Architecture Patterns

### System Architecture Diagram

```
git push (web/ changed) ──► Vercel ignored-build step (git diff -- . in web/) ──skip if no web change
                                     │ build
                                     ▼
                       npm run build = vite build ──► dist/ (index.html, assets, data/, logos/, og-default.png)
                                     │                    (dropLogos removes dist/logos if VITE_LOGOS=off)
                                     ▼
                     node --expose-gc scripts/share.mjs
   ┌──────────────────────────────────┼───────────────────────────────────────────────┐
   │ inputs: dist/data/meta.json, dist/data/snapshots/{season}.json                     │
   │         node_modules/@fontsource/*.woff (4)   public/logos/{FR}.png (base64 cache) │
   │         env: VERCEL_PROJECT_PRODUCTION_URL / SITE_ORIGIN, VITE_LOGOS (loadEnv)    │
   │                                                                                    │
   │ shareTargets(meta) [share.ts] ── (season,week) ≥ SHARE_LAUNCH ∧ week in meta ──┐   │
   │        for each (season,week):  32 team rows + that week's callouts            │   │
   │                                                                                ▼   │
   │   og-template.mjs: teamCard / calloutCard / siteCard  → {type,props} tree          │
   │        → satori(tree, {fonts, loadAdditionalAsset: throw}) ──missing glyph──► FAIL │
   │        → new Resvg(svg,{loadSystemFonts:false}).render().asPng()                   │
   │        → dist/og/team/{FR}/{s}-w{w}.png , dist/og/c/{s}/{w}/{FR}-{type}.png        │
   │   sharePageHtml(...) [share.ts, escapeHtml] → dist/s/team/{FR}/{s}-w{w}/index.html │
   │                                               dist/s/c/{s}/{w}/{FR}-{type}/index.html
   │   siteCard → overwrite dist/og-default.png                                        │
   │   every 25 cards: gc(); await setImmediate()     log: n cards, s total, ms/card, max KB
   │   self-check: every page's og:image file exists in dist ──missing──► FAIL         │
   └────────────────────────────────────────────────────────────────────────────────────┘
                                     ▼
                       Vercel CDN serves dist/ statically
   Crawler GET /s/team/BUF/2026-w9/ ─► index.html (og/twitter tags, no JS run) ─► GET /og/team/BUF/2026-w9.png
   Browser GET /s/team/BUF/2026-w9/ ─► inline script location.replace('/#/team/BUF/2026/9') ─► SPA
   App "Copy link" ─► hasSharePage(s,w,meta) ? location.origin + sharePath : deepLink(hash)
```

### Recommended Project Structure
```
web/
├── scripts/
│   ├── share.mjs              # export async function buildShare({dataDir,outDir,logoDir,env,log}); CLI main guarded
│   ├── og-template.mjs        # CARD tokens, h(), teamCard/calloutCard/siteCard, clampText, cardRuns, chip
│   ├── og-template.test.mjs   # tokens vs app.css, 7 band labels render, arrow, glyph guard, clamp
│   └── share.test.mjs         # buildShare() into a tmp dir against public/data: counts, files exist, sizes
├── src/lib/
│   ├── share.ts               # SHARE_LAUNCH, path/image builders, calloutId, hasSharePage, shareTargets,
│   │                          # escapeHtml, sharePageHtml (pure strings), team/callout copy-url helpers
│   └── share.test.ts
└── src/components/
    ├── CopyLinkButton.svelte  # extracted from CalloutCard (UI-SPEC)
    ├── CalloutCard.svelte     # + meta prop (from CalloutCards) → CopyLinkButton
    └── TeamPage.svelte        # header .share-row → CopyLinkButton
```
Keep the `.test.mjs` files under `scripts/`, outside `tsconfig.app.json`'s `include` (`src/**`). A `src/**` test that imports `og-template.mjs` would make svelte-check type-check the untyped satori trees (`allowJs` + `checkJs` are on), which risks spurious errors. Vitest's default include already matches `scripts/*.test.mjs`.

### Pattern 1: share.ts is pure and Node-importable (D-11)
**What:** Erasable TypeScript only (no enums, namespaces or parameter properties). Value imports only from `.ts` files with explicit extensions. Type imports can stay extensionless, since Node erases them.
**Verified:** `tsc` 6.0.3 rejects `import { a } from './a.ts'` under the app config with **TS5097** unless `allowImportingTsExtensions: true` is set. It passes once the flag is added (legal because `noEmit: true`). Node 24.20 then runs it directly.
```ts
// web/src/lib/share.ts
import { teamHash } from './router.ts'            // requires tsconfig.app.json allowImportingTsExtensions
import type { Callout, Meta } from './types'      // erased by Node; fine extensionless

export const SHARE_LAUNCH = { season: 2026, week: 9 } as const
const kebab = (t: string) => t.replace(/_/g, '-')
export const teamSharePath = (fr: string, s: number, w: number) => `/s/team/${fr.toUpperCase()}/${s}-w${w}/`
export const teamImagePath = (fr: string, s: number, w: number) => `/og/team/${fr.toUpperCase()}/${s}-w${w}.png`
export const calloutId = (c: Pick<Callout,'season'|'week'|'franchise'|'type'>) => `${c.season}/${c.week}/${c.franchise}-${kebab(c.type)}`
export const calloutSharePath = (c: Pick<Callout,'season'|'week'|'franchise'|'type'>) => `/s/c/${calloutId(c)}/`
export const calloutImagePath = (c: Pick<Callout,'season'|'week'|'franchise'|'type'>) => `/og/c/${calloutId(c)}.png`
export const teamShareHash = (fr: string, s: number, w: number) => teamHash(fr, s, w)
const atOrAfterLaunch = (s: number, w: number) => s > SHARE_LAUNCH.season || (s === SHARE_LAUNCH.season && w >= SHARE_LAUNCH.week)
export function hasSharePage(s: number, w: number, meta: Pick<Meta,'seasons'>): boolean {
  return atOrAfterLaunch(s, w) && !!meta.seasons.find((x) => x.season === s)?.week_labels[String(w)]
}
/** The exact (season, week) set the build renders; the app's hasSharePage agrees by construction. */
export function shareTargets(meta: Pick<Meta,'seasons'>): { season: number; week: number }[] { /* iterate week_labels keys */ }
export function escapeHtml(s: string): string {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;')
}
```
The app keeps `calloutHref(c)` from `callouts.ts` (equal to `teamHash(c.franchise, c.season, c.week)`). In `share.mjs`, use `teamHash` via share.ts or router.ts, **never** `callouts.ts` (Node can't import it, Pitfall 5). Data check: `meta.seasons[2026].week_labels` keys 0–9 exactly match `snapshots/2026.json` `weeks` keys.

**Fallback if the tsconfig change is rejected:** share.ts takes no value imports and builds `#/team/${FR}/${s}/${w}` itself. A test then asserts `teamShareHash(...) === teamHash(...)`.

### Pattern 2: Render loop (verified numbers)
```js
// Source: live spike 2026-11-12 (scratchpad/spike/full.mjs, mem4.mjs)
import satori from 'satori'
import { Resvg } from '@resvg/resvg-js'
import { setImmediate as yieldLoop } from 'node:timers/promises'

const RESVG_OPTS = { fitTo: { mode: 'original' }, font: { loadSystemFonts: false } } // 60ms → 8ms; text is already paths
const satoriOpts = (where) => ({
  width: 1200, height: 630, fonts,              // 4 WOFF buffers, read once
  loadAdditionalAsset: async (lang, segment) => {
    const cps = [...segment].map((c) => 'U+' + c.codePointAt(0).toString(16).toUpperCase().padStart(4, '0'))
    throw new Error(`share: missing glyph ${cps.join(',')} in "${segment}" (${where})`)
  },
  onStyleError: (e) => { throw new Error(`share: unsupported style in ${where}: ${e.message}`) }, // optional strictness
})
let n = 0
async function renderPng(tree, where) {
  const svg = await satori(tree, satoriOpts(where))
  const png = new Resvg(svg, RESVG_OPTS).render().asPng()
  if (++n % 25 === 0) { globalThis.gc?.(); await yieldLoop() }   // frees resvg native pixmaps (Pitfall 1)
  return png
}
```
Build script: `"build": "vite build && node --expose-gc scripts/share.mjs"`. This is a one-flag refinement of D-01. If the command must stay exactly as written, the in-script alternative is `v8.setFlagsFromString('--expose-gc'); const gc = vm.runInNewContext('gc')`, which was verified to work identically (RSS 165 MB).

`loadAdditionalAsset` fires only when **no** loaded font covers the character. A character missing from Plex Mono but present in Inter falls back to Inter silently, which isn't tofu. With the shipped files the two fonts cover the same set, so this doesn't matter in practice.

### Pattern 3: Element tree helper (no JSX)
```js
const h = (type, style, ...children) => ({ type, props: { style, children: children.length <= 1 ? children[0] : children } })
const img = (src, size) => ({ type: 'img', props: { src, width: size, height: size, style: { objectFit: 'contain' } } })
const arrow = { type: 'svg', props: { width: 36, height: 36, viewBox: '0 0 24 24',
  children: { type: 'path', props: { d: 'M4 12h14M13 6l6 6-6 6', stroke: '#6b6b6b', strokeWidth: 2.5, fill: 'none', strokeLinecap: 'round', strokeLinejoin: 'round' } } } }
// Headline clamp (verified: renders 2 lines + "…"):
h('div', { display: 'block', lineClamp: 2, fontSize: 56, fontWeight: 700, lineHeight: '62px', width: 1036 }, clampText(text, 68))
```
Verified in the spike: inline `svg`/`path` children render, `display:'block'` + `lineClamp: 2` cuts with `…` (mid-word, which is why the UI-SPEC's word-boundary `clampText` pre-pass is right), the base64 PNG data URI works, the `linear-gradient` chip renders, and curly apostrophes render correctly.

### Pattern 4: share.mjs as an importable function
`export async function buildShare({ dataDir, outDir, logoDir, env, log })`, run from the CLI only when `import.meta.url === pathToFileURL(process.argv[1]).href`. Reasons:
- vitest can run the whole step into `os.tmpdir()` against `public/data` (about 0.5 s for one week's ~45 cards, about 5 s for all 2026 weeks).
- Timing and logging (D-20) stay in one place.
- The post-write self-check runs in tests too: every emitted page's `og:image` path exists, and the PNG is 1200×630 and ≤ 300 KB.

Read the logo switch as `logosOff(loadEnv('production', webRoot, 'VITE_').VITE_LOGOS ?? process.env.VITE_LOGOS)`. `loadEnv` merges `.env*` files with process env, matching `vite.config.ts`'s `config.env`. Read logos from `public/logos/`, not `dist/logos`, because `dropLogos` deletes that directory when logos are off.

### Pattern 5: Share page HTML
- Put all og/twitter tags **at the top of `<head>`, before the `<script>`**. Slackbot fetches only part of the page with HTTP Range headers [CITED: api.slack.com/robots], and Facebook stops reading after the first 1 MB [CITED: developers.facebook.com/docs/sharing/webmasters/web-crawlers].
- The hash inside the script is `JSON.stringify(hash).replace(/</g, '\\u003c')`.
- `og:url` and canonical use the **trailing-slash** share URL, and copy-link emits the same form.

**Optional hardening (recommended, cheap):** guard the redirect, e.g. `if (!/bot|facebookexternalhit|facebot|twitterbot|slack|linkedin|discord|whatsapp|telegram|embedly|applebot/i.test(navigator.userAgent)) location.replace(...)`. Facebook, X and Slack previewers aren't believed to run JS, but a JS-executing previewer would otherwise follow the redirect to `/` and show the site card. Apple's preview fetcher sends a UA containing `facebookexternalhit … Twitterbot`, so the regex covers it. Humans are unaffected.

### Anti-Patterns to Avoid
- **Importing `callouts.ts` or `logos.ts` from share.mjs:** ERR_MODULE_NOT_FOUND (extensionless value import `./router` and `./logoSwitch`; `import.meta.env` in logos.ts).
- **Default resvg options:** a 7× slowdown from loading system fonts, and Linux build images have different system fonts anyway.
- **A `vercel.json` with rewrites or `trailingSlash`:** not needed. A catch-all would shadow `/s/` and `/og/`.
- **Raw `→` or emoji passed to satori:** the guard fails the build. `cardRuns` must split `→` first.
- **Running `npm audit fix --force`:** downgrades satori.
- **Validating locally with `vite preview` on paths without a trailing slash** (Pitfall 4).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text layout, wrapping, line clamp, font shaping | Manual line breaking / canvas text | satori `lineClamp`, flexbox, harfbuzz | Kerning, curly quotes, ellipsis, all verified |
| SVG rasterization | headless Chrome / canvas | resvg-js | Deterministic, native, ~8 ms |
| Missing-glyph detection | WOFF cmap parser, fontkit | satori `loadAdditionalAsset` throwing | Built in, zero deps, verified |
| Origin resolution | new env logic | `resolveSiteOrigin(process.env)` from `siteOrigin.ts` | Already tested, and Node-importable (verified) |
| Era names / Washington copy | port to JS | `eraName` / `eraText` from `teamNames.ts` | Node-importable as-is (verified) |
| Band → color index | new mapping | `bandIndex` / `moodToken` / `weekLabel` / `formatRecord` from `format.ts` | Node-importable as-is (verified) |
| Copy fallback chain | new clipboard code | `copyText` from `copyLink.ts`, moved into `CopyLinkButton` | WR-04/WR-05 behaviors already solved |
| Logo kill switch | new env parsing | `logosOff` from `logoSwitch.ts` + vite `loadEnv` | Same predicate as the build plugin |

**Key insight:** every piece of domain logic the cards need already exists as a pure, Node-importable `.ts` helper. Only `callouts.ts` isn't importable, and its one-line `calloutHref` equals `teamHash(fr, s, w)`.

## Common Pitfalls

### Pitfall 1: resvg-js native memory grows ~3 MB per card
**What goes wrong:** RSS reached 2.0 GB after 600 renders and 2.1 GB after 1,272. Each RenderedImage holds a 1200×630×4 pixmap until its JS wrapper is GC'd, and V8 never GCs because the JS heap is about 50 MB. Forced `gc()` without yielding did nothing. `renderAsync` showed the same growth.
**How to avoid:** `node --expose-gc`, then `gc()` followed by `await setImmediate()` every 25 cards. Verified flat at about 165 MB with no time cost (3,664 vs 3,700 ms for 600 renders).
**Warning signs:** Vercel build OOM or "SIGKILL" once multiple seasons accumulate. Log `process.memoryUsage().rss` alongside the timing line.

### Pitfall 2: resvg default system-font scan
**What goes wrong:** 60 ms/card instead of 8 ms. The first-ever run of a fresh native binary on macOS also took about 630 ms/card (a one-time Gatekeeper scan of the new `.node` file), which can mislead the D-20 timing.
**How to avoid:** `font: { loadSystemFonts: false }`. Time a second run.

### Pitfall 3: Missing glyph = silent tofu
**What goes wrong:** Without `loadAdditionalAsset`, satori emits a `.notdef` path (tofu) for `→`. The spike confirmed a path is still emitted.
**How to avoid:** Throw from `loadAdditionalAsset` and wrap each render to add the card path to the error. Data scan, all 2024–2026 callouts plus band labels: the non-ASCII characters are `’` (U+2019), `→` (U+2192) and `−` (U+2212). Only `→` is missing from both fonts. Fixed card copy adds `·`, `–` and `…`, all of which are covered (verified).

### Pitfall 4: `vite preview` masks missing share pages
**What goes wrong:** Locally, `/s/x/` (nonexistent) returns **200 with the root SPA index.html** (SPA fallback), and `/s/team/BUF/2026-w9` without the trailing slash also returns the root index locally. Only the trailing-slash form serves the nested index.html (verified with a copy of dist). On Vercel, both forms serve the nested file [CITED: vercel.com/docs/project-configuration/vercel-json#trailingslash, "both /about and /about/ will serve the same content"]. Unknown paths on production return 404 (verified: `/s/x/` → 404).
**How to avoid:** Local checks assert **files exist in dist** and fetch only trailing-slash URLs. Prove the non-slash behavior on production in D-25.

### Pitfall 5: Node can't import extensionless value imports
**What goes wrong:** `import('…/callouts.ts')` → ERR_MODULE_NOT_FOUND (its `import { teamHash } from './router'`). The same applies to `logos.ts`. Type-only extensionless imports (`teamNames.ts`, `format.ts`) work because they're erased.
**How to avoid:** share.ts value-imports only `./router.ts` (explicit extension, with the tsconfig flag). share.mjs imports only router, teamNames, format, siteOrigin, logoSwitch and share. Add a vitest or CLI smoke test, `node --input-type=module -e "await import('./src/lib/share.ts')"`, so a future edit that adds an extensionless import breaks loudly.

### Pitfall 6: Wrong Node version
**What goes wrong:** The nvm default (Node 20) has no type stripping, and the spike run under it exited silently with no output. Vercel uses 24.x (`engines`, project setting).
**How to avoid:** Always `nvm use 24` (`.nvmrc` = 24). Optionally fail fast in share.mjs: `if (!process.features?.typescript) throw new Error('share: Node 24+ required')`.

### Pitfall 7: svelte-check vs `.ts` import extensions
**What goes wrong:** TS5097 under `tsconfig.app.json`, which lacks `allowImportingTsExtensions`. `tsconfig.node.json` has it, but that config covers only `vite.config.ts`.
**How to avoid:** Add `"allowImportingTsExtensions": true` to `tsconfig.app.json` `compilerOptions`. This is legal because `noEmit: true` is set. Verified that `tsc` passes with it.

### Pitfall 8: Social caches and crawler blocking
- Facebook, X and LinkedIn cache aggressively. Slack caches about 30 min [CITED: api.slack.com/robots]. The week-versioned image filenames (D-14) handle new weeks. `og-default.png` keeps its filename (D-06), so the root preview updates only after "Scrape Again" in the Sharing Debugger. Add that to UAT.
- A Vercel Community report (2026-09-30, Hobby, custom domain) describes facebookexternalhit getting 403 from the platform even with bot protection off. The cause is unconfirmed (suspected platform DDoS mitigation of Meta IPs) [CITED: community.vercel.com/t/…/49969]. A curl with a spoofed UA can't detect this, because it comes from our IP. **Only the Facebook Sharing Debugger proves it.** Today production returns 200 to the facebookexternalhit, Twitterbot, Slackbot-LinkExpanding and LinkedInBot UAs (probed 2026-11-12). Attack Mode allows verified bots [CITED: vercel.com/docs/vercel-firewall/attack-mode].
- `og:url` must equal the share page itself, never the root or a hash URL.

### Pitfall 9: Token test parses the dark block
`app.css` has the light `:root` at lines 2–66, then a `@media (prefers-color-scheme: dark)` `:root` that redefines `--mood-*`. The D-07 drift test must parse only the first `:root { … }` block. Light values verified: mood-0..6 = `#7f1d1d #c2410c #b7791f #8a8d93 #2f9e8f #15803d #0b5d3b`, bg `#ffffff`, text `#222222`, muted `#6b6b6b`, border `#e3e3e3`, rule-strong `#222222`. These match the UI-SPEC `CARD`.

### Pitfall 10: Lockfile platform binaries
**What goes wrong:** If `package-lock.json` loses the `@resvg/resvg-js-linux-x64-gnu` optional entry, the Vercel build fails to load the binding.
**How to avoid:** A fresh install in the spike recorded all 12 platform optionals. Check with the grep under Installation, and never use `--no-optional` or `--omit=optional`.

## Code Examples

### Font loading (D-03)
```js
// Source: verified 2026-11-12 (createRequire resolves @fontsource ./files/* export)
import { createRequire } from 'node:module'
import { readFileSync } from 'node:fs'
const require = createRequire(import.meta.url)
const font = (spec, name, weight) => ({ name, weight, style: 'normal', data: readFileSync(require.resolve(spec)) })
export const FONTS = [
  font('@fontsource/inter/files/inter-latin-400-normal.woff', 'Inter', 400),
  font('@fontsource/inter/files/inter-latin-700-normal.woff', 'Inter', 700),
  font('@fontsource/ibm-plex-mono/files/ibm-plex-mono-latin-400-normal.woff', 'IBM Plex Mono', 400),
  font('@fontsource/ibm-plex-mono/files/ibm-plex-mono-latin-700-normal.woff', 'IBM Plex Mono', 700),
]
```

### PNG assertions in tests (no image lib)
```js
// PNG signature + IHDR width/height (verified in spike vitest)
expect(png.subarray(1, 4).toString('latin1')).toBe('PNG')
expect(png.readUInt32BE(16)).toBe(1200)
expect(png.readUInt32BE(20)).toBe(630)
expect(png.length).toBeLessThanOrEqual(300 * 1024)
```

### Glyph guard test
```js
await expect(renderPng(h('div', { display: 'flex' }, 'A → B'), 'test')).rejects.toThrow(/missing glyph U\+2192/)
for (const b of meta.bands) {             // 7 labels incl. U+2019
  const png = await renderPng(teamCard({ ...fixtureRow, label: b.label }), b.label) // throws on any tofu
  expect(png.readUInt32BE(16)).toBe(1200)
}
```

### Launch verification (D-25)
```bash
P=https://nfl-team-feelings.vercel.app
for path in /s/team/BUF/2026-w9/ /s/team/BUF/2026-w9 /s/c/2026/9/CLE-worried/; do
  for ua in "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)" "Twitterbot/1.0" "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)"; do
    html=$(curl -s -A "$ua" -w '\n%{http_code}' "$P$path"); code=${html##*$'\n'}
    img=$(printf '%s' "$html" | grep -o 'property="og:image" content="[^"]*"' | sed 's/.*content="//;s/"$//')
    echo "$code ${ua%% *} $path og:image=$img"
    printf '%s' "$html" | grep -q 'property="og:url" content="https://' && printf '%s' "$html" | grep -q 'name="twitter:card" content="summary_large_image"' || echo "  MISSING TAGS"
    curl -s -o /dev/null -w "  image %{http_code} %{content_type} %{size_download}B\n" "$img"
  done
done
```
Check `/s/c/2026/9/CLE-worried/` against the actual 2026 week-9 callouts at execution time (CLE worried exists today).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ts-node / tsx to run TS scripts | Node native type stripping (default on; `process.features.typescript === 'strip'` on 24.20, no warning) | Node 23.6 / 22.18 unflagged | share.mjs imports `.ts` helpers directly with zero tooling |
| @vercel/og edge function | Build-time satori + resvg | — | @vercel/og 1.0.3 still bundles satori 0.33.5 [VERIFIED: npm view] |
| satori needed TTF/OTF/WOFF only | 0.63.x accepts WOFF2 too (prior research), but WOFF stays locked (D-03) | — | Irrelevant here; WOFF verified working |
| satori threw on unsupported CSS | `onStyleError` callback; `convertColors` handles `color-mix()`/`oklch` | 0.6x [VERIFIED: satori d.ts] | UI-SPEC still bans color-mix (literal hex), which is fine |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Facebook, X, Slack and LinkedIn previewers do not execute the share page's JS redirect | Pattern 5, Pitfall 8 | The preview shows the site-default card. Mitigated by the optional UA guard and caught by human UAT (D-26). Community sources agree; no official doc found. |
| A2 | Apple Messages' preview fetcher doesn't run JS (or its UA matches the guard regex) | Pattern 5 | iMessage shows the site card. Caught by UAT. |
| A3 | Vercel Basic build machine renders 3–4× slower than an Apple M5 | Summary | The budget still holds even at 10× (630 cards × 100 ms ≈ 63 s). Low risk. |
| A4 | slopcheck status of satori and resvg-js (tool unavailable) | Package audit | Very low. Official vercel and yisibl repos, 7–8M downloads per week. |
| A5 | Meta's crawler isn't platform-blocked on this `*.vercel.app` domain | Pitfall 8 | The FB/Instagram/Messenger preview fails. It isn't fixable from the project (one community report). Record it honestly in UAT. |

## Open Questions

1. **Does Meta's real crawler get 403 on the vercel.app domain?**
   - What we know: spoofed-UA curls get 200, and one Hobby user hit platform-level 403s in Sept 2026.
   - What's unclear: whether this applies to `nfl-team-feelings.vercel.app`.
   - Recommendation: the Facebook Sharing Debugger is a required UAT line. If it reports 403, record it as a known limitation rather than a phase failure of the build-side requirements.
2. **Next season's accumulation (D-19)**
   - What we know: about 1,000 cards per season, roughly 10–40 s.
   - Recommendation: no action now (pruning is deferred). Log the card count and RSS so it's visible.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node 24 (via nvm) | share.mjs type stripping, build | ✓ | 24.20.0 (nvm default is 20, so `nvm use 24`) | — |
| npm | install | ✓ | 11.19.0 | — |
| @fontsource WOFF files | cards | ✓ | 5.3.0 (all 4 files present) | — |
| public/logos/{FR}.png | cards | ✓ | 32 × 500 px RGBA + `sm/`, manifest | chip fallback (D-04) |
| satori / resvg-js | cards | not yet installed in web/ (spike-installed fine) | 0.63.2 / 2.6.2 | resvg-wasm |
| Vercel project | deploy, D-25 | ✓ | prj_IHGS3ZnYxUGxXH59pewocdzc8ovd, Node 24.x, root `web`, ignored-build step `git diff --quiet ${VERCEL_GIT_PREVIOUS_SHA:-HEAD^} HEAD -- .` | — |
| Vercel MCP | checking deployment READY | ✓ (plugin) | — | `vercel` CLI |
| curl | D-25 | ✓ | system | — |

The ignored-build step is harmless here. Share outputs depend only on `web/` (code plus `web/public/data`), so every weekly data commit that touches `web/` triggers a build that regenerates all pages. Pipeline-only commits change no share inputs. `VERCEL_PROJECT_PRODUCTION_URL` is available at build time, has no scheme, and "is always set, even in preview deployments… useful to… generate links… such as OG-image URLs" [CITED: vercel.com/docs/environment-variables/system-environment-variables]. `resolveSiteOrigin` already handles it. Build limit: 45 min [CITED: vercel.com/docs/limits]. There's no cap on output file count.

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | vitest 5.1.0 (existing: 23 files, 277 tests, ~0.4 s) |
| Config file | none (vite.config.ts; default include also matches `scripts/*.test.mjs`) |
| Quick run command | `cd web && source ~/.nvm/nvm.sh && nvm use 24 && npx vitest run src/lib/share.test.ts scripts/` |
| Full suite command | `cd web && source ~/.nvm/nvm.sh && nvm use 24 && npm test && npm run check && npm run build` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SHARE-01 | `CARD` tokens equal the light `:root` values in app.css; tints recomputed | unit | `npx vitest run scripts/og-template.test.mjs` | ❌ Wave 0 |
| SHARE-01 | All 7 band labels (incl. U+2019) render 1200×630 PNGs with no glyph-guard throw (D-05) | unit | same | ❌ Wave 0 |
| SHARE-01 | Raw `→` / emoji makes satori reject with `missing glyph U+2192`; `cardRuns` splits the arrow and the mover detail renders | unit | same | ❌ Wave 0 |
| SHARE-01 | `clampText`: 65-char Seahawks fixture unchanged; long text cut at a word boundary ≤68 + `…` | unit | same | ❌ Wave 0 |
| SHARE-01 | Logos-off / missing logo → chip card renders (no throw) | unit | same | ❌ Wave 0 |
| SHARE-01 | `buildShare()` into a tmp dir: 32 team PNGs + N callout PNGs per target week, each 1200×630 and ≤300 KB, plus og-default.png | integration | `npx vitest run scripts/share.test.mjs` | ❌ Wave 0 |
| SHARE-02 | Path/image builders, kebab type, calloutId, trailing slash | unit | `npx vitest run src/lib/share.test.ts` | ❌ Wave 0 |
| SHARE-02 | `hasSharePage`: 2026 w8 false, w9 true, w10 false (not in meta), and agreement with `shareTargets` | unit | same | ❌ Wave 0 |
| SHARE-02 | `escapeHtml` on hostile input `<script>"'&`; `sharePageHtml` has absolute og:image/og:url/canonical on the given origin, `twitter:card`, the hash JSON-escaped (`</script>` neutralized), tags before the script | unit | same | ❌ Wave 0 |
| SHARE-02 | Every emitted page's og:image file exists in the out dir (self-check) | integration | `npx vitest run scripts/share.test.mjs` | ❌ Wave 0 |
| SHARE-02 | share.ts is importable by plain Node | smoke | `node --input-type=module -e "await import('./src/lib/share.ts')"` | ❌ Wave 0 |
| SHARE-02 | Real build emits `dist/s/team/BUF/2026-w9/index.html` and `dist/og/team/BUF/2026-w9.png`; timing log line present | smoke | `npm run build && test -f dist/s/team/BUF/2026-w9/index.html && test -f dist/og/team/BUF/2026-w9.png` | n/a |
| SHARE-03 | Copy-URL helpers: share URL when `hasSharePage`, else `deepLink(hash)`; team latest view pins `meta.latest` week | unit | `npx vitest run src/lib/share.test.ts` | ❌ Wave 0 |
| SHARE-03 | Button renders in the team header and callouts; click copies (status "Link copied") | manual / playwright | browser at `vite preview` (no component test infra; no jsdom) | manual |
| SHARE-02/04 | Production: 3 UAs × team/callout pages → 200, absolute tags, image 200 image/png; non-slash form 200 | post-deploy smoke | D-25 curl block | n/a |
| (SC 4) | Slack / iMessage / X pastes; FB Sharing Debugger; LinkedIn Post Inspector | human UAT | `14-HUMAN-UAT.md` | ❌ |

### Sampling Rate
- **Per task commit:** quick run command (under 3 s, since satori tests take about 0.1–0.5 s)
- **Per wave merge:** full suite command (test + svelte-check + build, including the share step)
- **Phase gate:** full suite green, then push, Vercel READY, the D-25 curl block, and the UAT file written before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `web/src/lib/share.test.ts` covers SHARE-02 and SHARE-03 pure logic
- [ ] `web/scripts/og-template.test.mjs` covers SHARE-01 rendering, tokens and glyphs
- [ ] `web/scripts/share.test.mjs` covers the buildShare integration in a tmp dir
- [ ] `tsconfig.app.json`: `"allowImportingTsExtensions": true` (prerequisite for the share.ts `./router.ts` import)
- [ ] Install: `npm install -D --save-exact satori@0.63.2 @resvg/resvg-js@2.6.2`

## Security Domain

`security_enforcement` is `false` in `.planning/config.json`, so the full ASVS section is omitted. The relevant controls are already locked: HTML-escape every field (D-15), JSON-encode the hash with `<` escaped inside `<script>`, keep the origin validated by `resolveSiteOrigin` (it throws on non-http(s) values), make no network calls at build, and add no runtime.

## Sources

### Primary (HIGH confidence)
- npm registry (live 2026-11-12): satori 0.63.2 (2026-10-20, deps incl. harfbuzzjs 0.10.0, fflate 0.7.3), @resvg/resvg-js 2.6.2 (12 platform optionals, no postinstall), @resvg/resvg-wasm 2.6.2, @vercel/og 1.0.3 (satori 0.33.5); api.npmjs.org weekly downloads
- satori `dist/wasm-*.d.ts`: SatoriOptions incl. `loadAdditionalAsset`, `onStyleError`, `convertColors`, `embedFont`; resvg-js `index.d.ts`: `font.loadSystemFonts`, `renderAsync`
- Live spikes (scratchpad `spike/`): render timing, memory, glyph guard, lineClamp, inline SVG, vitest compatibility, Node 24 `.ts` imports, tsc TS5097, vite preview fallback behavior, production crawler-UA probes
- https://vercel.com/docs/environment-variables/system-environment-variables (VERCEL_PROJECT_PRODUCTION_URL)
- https://vercel.com/docs/project-configuration/vercel-json#trailingslash (default serves both forms)
- https://vercel.com/docs/builds/managing-builds (Hobby = Basic 2 vCPU / 8 GB)
- https://vercel.com/docs/limits (45-min build)
- https://vercel.com/docs/vercel-firewall/attack-mode (verified bots allowed)
- https://api.slack.com/robots (UAs, Range fetch, ~30 min cache)
- https://developers.facebook.com/docs/sharing/webmasters/web-crawlers/ (UA, 1 MB limit, Sharing Debugger recrawl)

### Secondary (MEDIUM confidence)
- [resvg-js #216 / PR #318](https://github.com/yisibl/resvg-js/issues/216): memory growth tied to GC/finalizer timing (matches the measured behavior and fix)
- [Vercel Community: facebookexternalhit 403 on Hobby](https://community.vercel.com/t/facebookexternalhit-gets-403-on-my-custom-domain-even-with-a-bypass-rule-hobby/49969)
- [24ways: Microbrowsers are everywhere](https://24ways.org/2019/microbrowsers-are-everywhere/); [Apple TN2444 link previews](https://developer.apple.com/library/archive/technotes/tn2444/_index.html); community posts on the FB crawler not running JS ([outsystems](https://www.outsystems.com/forums/discussion/65767/facebook-crawlers-not-getting-the-metadata/), [indiehackers](https://www.indiehackers.com/post/our-job-pages-looked-broken-every-time-someone-shared-them-af0029287a))
- X card image requirements (2:1, min 300×157, max 4096) via [search summary of dev.twitter.com](https://dev.twitter.com/cards/types/summary-large-image); the official page returned 402 to the fetch

### Tertiary (LOW confidence)
- Exact iMessage JS behavior: not officially documented. Covered by the UA guard and UAT.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. Versions come from the registry and the render was measured.
- Architecture: HIGH. Every interop claim was executed this session (Node imports, tsc, vitest, vite preview).
- Pitfalls: HIGH for memory, speed, glyphs, imports and preview (measured). MEDIUM for crawler and platform blocking (closed by UAT).

**Research date:** 2026-11-12
**Valid until:** 2026-12-12 (satori is pre-1.0 and moves fast; the pin protects the build)

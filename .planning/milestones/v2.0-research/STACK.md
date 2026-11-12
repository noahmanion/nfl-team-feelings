# Stack Research: v2.0 Public Site (additions only)

**Domain:** Static data-journalism site (Vite 8 + Svelte 5 + Observable Plot SPA, Python/Polars pipeline → static JSON), going public on Vercel
**Researched:** 2026-11-11
**Confidence:** HIGH for the OG pipeline, Vercel, logos, and versions (all verified live). MEDIUM for font lookalikes (a taste call) and trademark posture (not legal advice).

> Scope: only what v2.0 adds. The existing pipeline (Python 3.13 / uv / Polars 2.1 / nflreadpy 0.1.5) and web app (Vite 8.3 / Svelte 5.57 / Plot 0.6.19, hash routing, `web/src/app.css` tokens) are validated. Don't re-litigate them.

## TL;DR (prescriptive)

1. **Deploy:** Use Vercel Git integration with Root Directory `web`, the Vite preset, Node 22.x (or 24.x), build `npm run build`, and output `dist`. The JSON in `web/public/data` is **already committed** (94 files, about 15 MB), so the Vercel build never runs Python. You need **no `vercel.json`**, because hash routing means no SPA rewrites. The only possible config is optional `headers`.
2. **OG cards: build-time `satori` 0.63.2 + `@resvg/resvg-js` 2.6.2, run as a Node post-build script** (`vite build && node scripts/share.mjs`). It does two things:
   - Renders `dist/og/*.png` (1200×630).
   - Writes **static share stubs under real paths** (`dist/t/KC/index.html`, `dist/c/<callout-id>/index.html`). Each stub carries `og:*` / `twitter:*` meta tags and does a JS redirect to `/#/team/KC`.

   Verified live: one card renders in about 1 s on a laptop, with an Inter font plus an ESPN logo. **Not** `@vercel/og`: an edge function only produces images. It does nothing for the real blocker, which is that crawlers can't see per-route meta tags on a hash-routed SPA. You need static stubs either way. Once you have them, static PNGs are free and simpler.
3. **EPA charts:** **No new chart library.** Plot 0.6.19 already ships the marks you need: `dot`, `image` (logos as scatter points), `linearRegressionY`, `tip`, `crosshair`, and `text`. The **data is not exported yet.** `pipeline/data/derived/team_game_epa.parquet` has `off_epa`, `def_epa`, `net_epa`, `off_sr`, play counts, and `low_confidence` per team-game, but nothing reaches `web/public/data`. Add one small `epa.json` (team-season aggregates, play-weighted) in `export.py`. No new Python dependencies.
4. **Typography (538-inspired, free):**
   - **Inter Variable** stands in for Atlas Grotesk (titles: bold for heads, thin or light for deks).
   - **IBM Plex Mono** stands in for Decima Mono (chart annotations, numbers, source lines).
   - Optionally, **Source Serif 4 Variable** stands in for Arnhem (long-form methodology prose).

   Self-host all of them through Fontsource npm packages. Don't use the Google Fonts CDN.
5. **Logos:** Use the ESPN CDN URLs that nflverse already exposes (`team_logo_espn`). Vendor them once into `web/public/logos/{TEAM}.png`, resized by ESPN's own combiner endpoint (stdlib `urllib`, so no Pillow). Keep the existing color chip as the fallback. Don't hotlink at runtime, and don't use `team_logo_wikipedia` (it returns **400** now).
6. **Data loose ends:**
   - Draft forfeits: verify against **Wikipedia per-year draft articles via the MediaWiki API**. They mark each forfeit with a parseable `{{NFLDraft-nonpick … Selection forfeited}}` template and cite it. Probe result: the **2004 R2 LV entry looks like a trade, not a forfeit.**
   - Win totals 2021–2026: **no free machine-readable source exists.** nflverse `win_totals.csv` still ends at 2020 (re-checked today). Hand-enter about 192 rows into a committed CSV, sourced from sportsoddshistory/covers (browser only, because it returns 503 to scripts) and cross-checked against sportsbettingdime.

## Recommended Stack (additions)

### Core Technologies

| Technology | Version (verified 2026-11-11) | Purpose | Why Recommended |
|------------|------------------------------|---------|-----------------|
| Vercel (Git integration, Hobby) | n/a (platform) | Static hosting from `github.com/noahmanion/nfl-team-feelings` | Zero config for a Vite `dist/`. Every push to `main` deploys, and the weekly refresh is "run `fgs`, commit JSON, push". Hobby limits are nowhere near binding: 45-min builds, no limit on output files, 100 MB CLI upload cap (Git deploys don't hit it). Hobby is for **non-commercial personal use**. A no-ads fan site fits; adding ads or sponsorship would require Pro. |
| satori | 0.63.2 (published 2026-10-20) | HTML/CSS-ish tree → SVG for OG cards | The engine behind `@vercel/og`, used directly at build time. It does flexbox layout, real font shaping (it now bundles harfbuzzjs), and `<img>` with data URIs. You write the card as plain `{type, props}` objects, so you need no React or JSX toolchain. **Live probe:** a 1200×630 card with Inter 700, IBM Plex Mono 400, and the KC logo rendered correctly in about 1.0 s on Node 20. It accepts both `.woff` and `.woff2`. |
| @resvg/resvg-js | 2.6.2 | SVG → PNG | Native (napi) prebuilt binaries for darwin-arm64 and linux-x64-gnu, which is what Vercel's build image uses, so there's no compile step. It's the standard companion to satori. |
| Fontsource packages | 5.3.x | Self-hosted webfonts imported from JS/CSS | Vite bundles them with hashed filenames and immutable caching. You avoid third-party font requests (privacy, no Google Fonts GDPR question). The same font files feed satori, so the cards match the site. |

### Fonts (538-inspired lookalikes; inspired by, not copied)

538's graphics typography is documented as **Atlas Grotesk** (Bold titles, Thin subtitle deks) plus **Decima Mono** (all-caps annotations), with **Arnhem** as the text serif. All three are commercial. I found no evidence that 538 used Druk, so don't chase a Druk lookalike.

| Role | 538 used | Free pick | Package (version) | Notes |
|------|----------|-----------|-------------------|-------|
| Headlines, chart titles, UI | Atlas Grotesk | **Inter** (variable, wght 100–900) | `@fontsource-variable/inter` 5.3.0 | A tall-x-height grotesk like Atlas. Has `font-feature-settings: "tnum"` for tabular numbers in tables. Use the thin or light weight for deks to echo 538's Bold/Thin pairing. Alternative with more character: `@fontsource-variable/schibsted-grotesk` 5.3.0. |
| Chart annotations, axis ticks, numbers, "SOURCE:" lines | Decima Mono | **IBM Plex Mono** | `@fontsource/ibm-plex-mono` 5.3.0 (static weights 400 and 600) | Use it uppercase and small (11–12 px, slight letter-spacing) for the 538 annotation feel. `@fontsource/dm-mono` 5.3.0 is a softer alternative. |
| Long-form prose (methodology page) | Arnhem | **Source Serif 4** (optional) | `@fontsource-variable/source-serif-4` 5.3.1 | Optional. The site is mostly UI and charts, so add it only if the methodology page gets the editorial treatment. |
| OG card rendering | — | Static Inter 400/700 and Plex Mono 400 | `@fontsource/inter` 5.3.0 (devDependency) | Satori's variable-font axis support isn't reliable. Load **static** weight files from `files/*-latin-700-normal.woff` for cards. The probe confirmed static weights render correctly. |

Chart styling needs no library, only Plot options plus CSS tokens:
- Light gray gridlines: `grid: true` and `stroke: "#ddd"`, and no axis domain lines.
- A bold title and a light dek above the chart, in HTML rather than Plot's `title`.
- An uppercase mono "SOURCE: nflverse · Feel-Good Score" line below the chart.
- Direct labels (`Plot.text` at series ends) instead of legends.
- A restrained palette with one highlight color.

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `@observablehq/plot` (existing) | 0.6.19 | EPA scatter (offense vs defense EPA/play), team-season trajectories | Use `Plot.image` for logo-as-dot scatter, `Plot.dot` with `Plot.tip` for the dense all-seasons view, and `Plot.linearRegressionY` for a trend line. `crosshair` is useful for the 32-point scatter. Confirmed present in the installed package (`src/marks/{image,tip,linearRegression,crosshair}.d.ts`). |
| Python stdlib `urllib`, `json`, `csv` | — | Logo vendoring step, MediaWiki API forfeit check, `epa.json` export | Everything pipeline-side for v2 fits the existing deps (polars, numpy, pyyaml). **No new Python packages.** |
| `vercel` CLI (optional) | 65.14.0 | `vercel link`, `vercel pull`, `vercel build` locally to reproduce a Vercel build | Only if you want to debug a Vercel build locally. The Git integration doesn't need it. Run it with `npx`; don't add it to package.json. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `scripts/share.mjs` (new, in `web/`) | Post-build: read `dist/data/latest.json`, `callouts.json`, and `teams/*.json`; write `dist/og/**.png` and `dist/t/<TEAM>/index.html` / `dist/c/<id>/index.html` stubs | Wire it as `"build": "vite build && node scripts/share.mjs"`. Read the site origin from `process.env.VERCEL_PROJECT_PRODUCTION_URL`. Vercel always sets it, preview builds included, without the `https://` prefix. Its docs specifically suggest it for OG-image URLs. Fall back to `http://localhost:4173` locally. |
| Social preview validators | Check cards after deploy | Use opengraph.xyz, the LinkedIn Post Inspector, and the Facebook Sharing Debugger. X has no public validator any more, so post to a private account to test. |

## Installation

```bash
cd web
# runtime fonts (bundled by Vite)
npm install @fontsource-variable/inter@5.3.0 @fontsource/ibm-plex-mono@5.3.0
# optional editorial serif
npm install @fontsource-variable/source-serif-4@5.3.1
# build-time OG generation (devDependencies: never shipped to the browser)
npm install -D satori@0.63.2 @resvg/resvg-js@2.6.2 @fontsource/inter@5.3.0
```

```css
/* web/src/main.ts */
import '@fontsource-variable/inter';
import '@fontsource/ibm-plex-mono/400.css';
import '@fontsource/ibm-plex-mono/600.css';
```

Pipeline: no `uv add` needed.

## Integration Points (where new things plug into existing code)

| Feature | Touches | Change |
|---------|---------|--------|
| Deploy | Vercel project settings | Root Directory `web`, Framework Preset Vite, Node 22.x, Build `npm run build`, Output `dist`. In the Vercel UI, enable "Include files outside root directory" **off** (not needed). Because `engines.node` is `>=22.12`, Vercel picks a compatible Node, but pin it in project settings anyway. |
| OG + stubs | `web/package.json` build script, new `web/scripts/share.mjs` | Stubs contain `og:title`, `og:description`, `og:image` (an **absolute** URL), `og:url`, `twitter:card=summary_large_image`, `<link rel=canonical>`, `<meta http-equiv="refresh" content="0;url=/#/team/KC">`, and `location.replace(...)`. The share button in the SPA copies `https://<host>/t/KC/`, **not** the hash URL. |
| OG cache-busting | `share.mjs` | Version image filenames with the data week, e.g. `/og/team/KC-2026-w10.png`. Facebook, X, Slack, and iMessage cache images for days, so a reused filename shows last week's mood. Stub URLs stay stable, and only the image URL inside them changes. |
| Logos | New `fgs logos` CLI subcommand (or a one-off script), `export.team_meta` | Download `https://a.espncdn.com/combiner/i?img=/i/teamlogos/nfl/500/{abbr}.png&h=160&w=160` (verified: 200, image/png, about 6.4 KB) into `web/public/logos/{TEAM}.png`. Commit them once (about 250 KB total). Add `"logo": "/logos/KC.png"` to `team_meta`. `share.mjs` reads the same local files, so the Vercel build makes **no network calls**. Map ESPN slugs: nflverse `LA` maps to ESPN `lar`, `WAS` to `wsh`. Take the URL from `teams.parquet` `team_logo_espn` rather than building it. |
| EPA data | `pipeline/src/fgs/export.py` (new `epa.json`), read from `data/derived/team_game_epa.parquet` | Group by `(season, franchise_id)` over the regular season with play-weighted means: `off_epa`, `def_epa`, `net_epa`, `off_sr`, `games`, `low_confidence`. About 28 × 32 rows, roughly 60 KB raw, smaller with rounding to 3 decimal places. Use columnar layout like `history.json`. Add a per-week cumulative block for the current season only if a "trajectory" chart is in scope. |
| Fonts and 538 chart styling | `web/src/app.css` tokens (`--font-sans`, new `--font-mono`, `--font-serif`), a shared Plot defaults helper | Put the font stacks behind tokens. Components already use `var(--token)` only, so the redesign is mostly token edits plus a `chartFrame` wrapper component (title, dek, chart, source line). |
| Forfeits | `pipeline/src/fgs/draft.py` `FORFEITS` (24 team-round entries; the milestone says about 18) | One-off verifier: for each draft year, call `https://en.wikipedia.org/w/api.php?action=parse&page={Y}_NFL_draft&prop=wikitext&format=json&formatversion=2` and grep `NFLDraft-nonpick` lines containing "forfeit". Verified live for 2016 and 2025 (lists NE R1, KC R3, LA R5 supplemental, ATL R5; ATL and SF R5). Send a descriptive User-Agent (Wikimedia policy). Put the citation URL in a code comment per entry. |
| Win totals 2021+ | New committed `pipeline/data/manual/win_totals_2021plus.csv` (same schema as nflverse: `season,team,line,over_odds,under_odds`, plus `source`) | Display-only. **It must never feed the frozen v1 score.** `expectation.py` already documents that 2021+ is model-sourced. Keep it outside `data/cache` so a cache wipe can't delete hand-entered data. |

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Build-time satori + resvg-js (Node post-build) | **Vercel OG / `@vercel/og` 1.0.3 edge function** | Only if cards had to be per-request dynamic (arbitrary user input in the image). They don't, because the data changes weekly. Against it: (a) it does **not** solve per-route meta tags, so you still need stubs; (b) Vercel now steers plain-Vite projects to Nitro for functions, which adds a server layer to a static site; (c) it pins **satori 0.33.5**, about 30 minor versions behind; (d) it adds a runtime and cold starts to the crawler path. |
| Build-time satori (Node) | **Python Pillow 13.0.0 in the pipeline** | If you'd rather keep all generation in Python. Against it: PNGs get committed to git every week (about 30 to 80 binary files of churn per refresh); Pillow has no layout engine, so you hand-position every text box and wrap lines manually; and the cards drift from the site's CSS. Satori runs during the Vercel build, nothing binary is committed, and it uses CSS-like flexbox. |
| Redirect stubs + keep hash routing | Migrate to history routing and emit `dist/team/KC/index.html` as copies of `index.html` with injected meta (true MPA-style prerender) | If you want shared URLs to be the canonical app URLs, with no redirect hop. That costs a router rewrite plus a `vercel.json` SPA rewrite, and it risks breaking the week-scrubber and pinned-team URL state built in v1. Defer it. Redirect stubs get 95% of the value. |
| Redirect stubs | SvelteKit + `adapter-static` prerender | Only if the app is being rewritten anyway. Overkill for adding meta tags to about 40 URLs. |
| Vendored ESPN logos (resized via the combiner) | Runtime hotlink to `a.espncdn.com` | Hotlinking works today (verified: 200 with no UA or referer checks, `access-control-allow-origin: *`). But it depends on a third-party CDN you have no agreement with, it's slower (500 px source, about 40 KB per logo × 32 on the mood board), and it breaks OG builds if ESPN blocks you. Vendor small copies. |
| ESPN logos | nflverse `team_logo_squared` (GitHub-hosted squared PNGs) | If you want uniform square tiles. Same trademark status. Served via GitHub raw redirects, which is fine for a one-time download. |
| Inter + IBM Plex Mono | Google Fonts `<link>` CDN | If you don't want npm font packages. Self-hosting is faster (same origin, no extra DNS or TLS round trip), avoids third-party requests, and the files double as satori inputs. |
| Hand-entered win totals CSV | Scrape covers.com/sportsoddshistory | Don't. It returns 503 to automated fetches and is against the site's terms. About 192 numbers is an afternoon of typing, and it's display-only. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `@vercel/og` / edge or serverless functions | Adds a runtime to a fully static site, doesn't solve meta tags, and bundles stale satori | Build-time satori + resvg-js |
| `sharp` (0.35.5) | Not needed: resvg outputs PNG directly and ESPN's combiner resizes logos. It's a heavy native dependency. | resvg-js; the ESPN combiner `h=`/`w=` params |
| React / JSX toolchain for satori | Satori takes plain `{type, props: {style, children}}` objects | A 5-line `h()` helper (used in the probe) |
| `team_logo_wikipedia` URLs | **Returns HTTP 400 today.** Wikimedia now rejects non-standard thumbnail sizes like `100px`. | `team_logo_espn` |
| `team_league_logo` (NFL shield) or team logos in the site's own branding (favicon, header, OG frame) | The NFL shield is the league's core mark, and using it implies endorsement. Logos as site branding stop being identification and start being branding. | Logos only next to the team they identify, plus a footer disclaimer |
| Variable font files in satori | Weight axes don't apply reliably | Static `@fontsource/inter` weight files |
| Proprietary 538 fonts, the 538 fox logo, or the "FiveThirtyEight" name in UI | Licensing and trade dress; the milestone says "inspired-by" | Free lookalikes above. Copy conventions (gray grids, bold title + dek, source line), not marks. |
| D3 directly / a second chart lib (ECharts, Chart.js, Vega) for EPA | Plot covers scatter, regression, tooltips, and images | Observable Plot 0.6.19 (already installed) |
| `vercel.json` SPA rewrites | Unnecessary with hash routing, and a catch-all rewrite would **shadow the share stubs and `/og/*.png`** if misconfigured | No `vercel.json`, or headers only |

## Trademark Note (logos) — MEDIUM confidence, not legal advice

NFL and team logos are registered trademarks. Common practice for non-commercial stats and fan sites (nflverse's own `nflplotR`, rbsdm, nfelo, countless blogs) is to show team logos **as nominative identification**: next to the team's data, unaltered, with no implied endorsement. Risk is low but not zero, and the realistic worst case is a takedown request. Keep it low-risk:
- Footer: "Not affiliated with or endorsed by the NFL or any team. Team names and logos are trademarks of their respective owners."
- Don't alter logos (no recoloring, no mood-tinting the logo itself), sell anything, or run ads.
- Keep the color-chip fallback, already built in v1. If a takedown ever arrives, a one-line config flag switches logos off site-wide.

## Stack Patterns by Variant

**If a crawler-visible page must be per-callout (not just per-team):**
- Give each callout a stable ID in `callouts.json` (e.g. `2026-w10-KC-worried`) and generate `dist/c/<id>/index.html` plus its PNG.
- Cap the count: current week plus records, about 20 to 40 cards, about 30 s of build. Don't render all of history.

**If OG build time ever matters (hundreds of cards):**
- Cache by content hash in `node_modules/.cache/og` (Vercel restores the build cache), or move to `@resvg/resvg-wasm`. Not needed at about 40 cards and about 1 s each.

**If Vercel's Node image ever fails to load the resvg native binary:**
- Swap to `@resvg/resvg-wasm` 2.6.2, which has the same API plus `initWasm()`.

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| satori 0.63.2 | Node >=16; fonts as ttf/otf/woff/woff2 | Verified on Node 20.19 locally. Vercel builds on 22/24. Pre-1.0, so pin the exact version. |
| @resvg/resvg-js 2.6.2 | linux-x64-gnu, darwin-arm64 prebuilt | Optional-dependency binaries. Make sure `package-lock.json` is committed with platform optionals intact. Don't run `npm install --no-optional`. |
| @fontsource* 5.3.x | Vite 8 asset pipeline | The CSS `@import` resolves font files as hashed assets. Static packages ship `.woff` and `.woff2`. Variable packages ship only `.woff2`. |
| @observablehq/plot 0.6.19 | Svelte 5 action mount (existing) | `Plot.image` renders SVG `<image href>`. Same-origin vendored logos avoid CORS taint if you ever export a chart to PNG. |
| Vercel build | Node 22.x / 24.x | Matches `engines.node >=22.12`. Locally, run `nvm use 22` before `npm run build` (local default is Node 20). |

## Sources

- npm registry (live, 2026-11-11): satori 0.63.2, @resvg/resvg-js 2.6.2, @resvg/resvg-wasm 2.6.2, @vercel/og 1.0.3 (deps: satori 0.33.5), vercel 65.14.0, sharp 0.35.5, @fontsource(-variable) inter / ibm-plex-mono / dm-mono / source-serif-4 / schibsted-grotesk 5.3.x, @observablehq/plot 0.6.19. HIGH
- PyPI JSON API (live): pillow 13.0.0, CairoSVG 2.9.1 (considered, not recommended). HIGH
- Live probe in the scratchpad: satori + resvg-js rendered a 1200×630 card with Inter 700 / Plex Mono 400 / the ESPN KC logo in about 1.05 s, and woff2 was accepted. HIGH
- Live HTTP probes: ESPN `500/kc.png` returns 200 with no UA or referer checks and `access-control-allow-origin: *`; the combiner resize returns 200 (6.4 KB); `lar`, `wsh`, `lv`, and `lac` slugs return 200; the nflverse `squared_logos` and `wordmarks` return 200; the Wikipedia thumbnail URL from `load_teams()` returns **400**. HIGH
- `pipeline/data/cache/teams.parquet` columns: `team_logo_wikipedia, team_logo_espn, team_wordmark, team_conference_logo, team_league_logo, team_logo_squared`. HIGH
- Codebase: `pipeline/src/fgs/export.py` (no EPA export), `pipeline/src/fgs/pbp.py` / `data/derived/team_game_epa.parquet` (EPA exists), `pipeline/src/fgs/draft.py` `FORFEITS`, `git ls-files web/public/data` (94 files committed). HIGH
- https://vercel.com/docs/environment-variables/system-environment-variables (`VERCEL_PROJECT_PRODUCTION_URL` is always set, has no protocol, and is recommended for OG URLs). HIGH
- https://vercel.com/docs/frameworks/frontend/vite (preset, SPA rewrite guidance, functions via Nitro). HIGH
- https://vercel.com/docs/limits (Hobby: 45-min build, no output-file cap, 100 MB CLI upload). HIGH. The Hobby non-commercial restriction is from Vercel's fair-use policy (training knowledge plus common reference, not re-fetched). MEDIUM
- https://raw.githubusercontent.com/nflverse/nfldata/master/data/win_totals.csv: still 2003–2020 (18 rows per team). HIGH
- MediaWiki API `action=parse` on `2016_NFL_draft` and `2025_NFL_draft`: `NFLDraft-nonpick … Selection forfeited` templates with refs. HIGH. `2004_NFL_draft` shows the Oakland R2 note as a trade. MEDIUM (needs a human read).
- https://www.nfl.com/news/draft-picks-that-have-been-stripped-from-nfl-teams-since-1980-0ap3000000492229: NFL's own list, but dated (about 2016). Use it as a second source for pre-2016 penalty forfeits. MEDIUM
- https://www.sportsbettingdime.com/nfl/futures/win-totals-best-odds/2021-season: all 32 teams per season, 2018–2025, but labeled "closing… as of December 22", so it's **not clearly preseason**. Cross-check only. LOW to MEDIUM
- https://www.nfeloapp.com/nfl-power-ratings/nfl-win-totals/: claims history from 2003, with no CSV. The nfelo GitHub `output_data/` has no win totals file (checked). LOW
- covers.com/sportsoddshistory/nfl-win/: returns 503 to scripts, so it's browser-only manual entry. MEDIUM
- https://harukihill.github.io/FontCritique.html (538 graphics use Atlas Grotesk Bold/Thin plus Decima Mono annotations) and https://www.typewolf.com/atlas-grotesk (538 uses Atlas Grotesk with Arnhem and Decima). MEDIUM. The free-lookalike choices are a judgment call. LOW to MEDIUM

---
*Stack research for: v2.0 Public Site additions*
*Researched: 2026-11-11*

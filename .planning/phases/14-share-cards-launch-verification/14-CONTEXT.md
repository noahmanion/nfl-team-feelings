# Phase 14: Share Cards & Launch Verification - Context

**Gathered:** 2026-11-12
**Status:** Ready for planning
**Mode:** Autonomous smart discuss (full autonomy; recommended answers accepted, no user questions)

<domain>
## Phase Boundary

Every build turns the committed data into (a) 1200×630 PNG share cards for all 32 teams and every current-season callout, and (b) static share pages at real paths (`/s/...`) whose og/twitter tags point at those cards on the production origin and which forward a browser to the matching hash route with JavaScript. The copy-link buttons on the team page and callout cards copy the share-page URL where one exists, else the hash link. Launch verification checks production with crawler user agents; real platform pastes are logged as human UAT.

Out of scope: router changes / history-mode routing, SvelteKit, Web Share API or download buttons, records-page cards, any pipeline/model change, committed generated images.

</domain>

<decisions>
## Implementation Decisions

### Rendering pipeline (SHARE-01)
- D-01: Node post-build script `web/scripts/share.mjs` (+ `web/scripts/og-template.mjs` for the satori element trees) runs after `vite build`; `package.json` build becomes `vite build && node scripts/share.mjs`. Not a Vite plugin (keeps the render step testable and separately timeable).
- D-02: `satori` pinned to an exact version (verify the current 0.x release at plan time; research said 0.63.2) and `@resvg/resvg-js` pinned exactly (2.6.2 or current), both devDependencies. No `@vercel/og`, no `sharp`, no JSX toolchain: plain `{type, props}` objects.
- D-03 (amended by UI-SPEC revision 1): Fonts are the static WOFF files already in node_modules, two weights only: `@fontsource/inter` `inter-latin-{400,700}-normal.woff` and `@fontsource/ibm-plex-mono` `ibm-plex-mono-latin-{400,700}-normal.woff`. Never WOFF2 or the variable package. Read with `fs` from `node_modules/@fontsource/...` (resolved via `createRequire`/`import.meta.resolve`).
- D-04: Logos come from `web/public/logos/{FR}.png` (local files, read as base64 data URIs). If `VITE_LOGOS=off` (existing `logosOff` switch) or a logo file is missing, the card falls back to the team-color chip (primary/secondary from meta.teams) — mirrors `TeamLogo` → `TeamChip`.
- D-05: Emoji are DROPPED from cards (no Twemoji, no network at build). The mood band color (Phase 12 `--mood-0..6` light tokens) carries the mood visually; the label text carries it verbally. A vitest test renders a card for each of the 7 band labels (incl. "It’s fine. Everything’s fine." with U+2019) and asserts non-empty PNG output and that every character of the label is covered by the loaded fonts (no tofu / missing-glyph path).
- D-06: A site-default card is rendered by the same template and overwrites `dist/og-default.png` (index.html keeps pointing at `/og-default.png`), so the site-level preview matches the card design. The committed `public/og-default.png` stays as the no-script fallback.
- D-07: Card colors/typography are copied from Phase 12 tokens into one exported constant object in `og-template.mjs` (light theme only — share previews render on unknown backgrounds); a test asserts the mood colors match `app.css` `--mood-*` values so they cannot drift.

### Card content (SHARE-01, design follows Phase 12 system)
- D-08: Team card: team logo, era-correct team name, big score (IBM Plex Mono) out of 100, mood label in bold Inter on a band-colored bar/stripe, rank + record line (e.g. "#2 of 32 · 7-1"), date stamp "Week 9 · 2026" (week label from meta.seasons[].week_labels), site name "Feel-Good Score" + bare domain. One claim, one supporting number, logo, site name, date (research FEATURES must-have).
- D-09: Callout card: team logo + name, the callout headline as the one claim (largest text), the detail line as the supporting number, a type kicker ("Worried", "Hopeful", "Misery", "Joy", "Rising", "Falling"), the band stripe color, date stamp, site name + domain. Era text via the same `eraName`/`eraText` rules (callouts are current-season so this is mostly a no-op, but reuse the helpers if importable as erasable TS, else port the minimal logic).
- D-10: Long text is clamped: headline max 2 lines with ellipsis, detail max 2 lines; team names never truncated (font size steps down for long names like "Jacksonville Jaguars" if needed).

### Share URL scheme & IDs (SHARE-02)
- D-11: One slug module `web/src/lib/share.ts` — erasable TypeScript only, no imports except other `.ts` files with explicit extensions — imported by both the app and `share.mjs` (Node 24 strips types natively). It exports the path builders, image path builders, hash targets, the launch constant and `hasSharePage`.
- D-12: Team share page: `/s/team/{FR}/{season}-w{week}/` (FR uppercase canonical franchise code, week unpadded), image `/og/team/{FR}/{season}-w{week}.png`. Hash target `#/team/{FR}/{season}/{week}` (existing `teamHash`).
- D-13: Callout share page: `/s/c/{season}/{week}/{FR}-{type}/` with type kebab-cased (`mover_up` → `mover-up`), image `/og/c/{season}/{week}/{FR}-{type}.png`. Stable callout ID = `{season}/{week}/{FR}-{type}` — verified unique: 0 duplicate (season, week, franchise, type) across all 28 committed snapshots. Hash target = `calloutHref(c)` (the team's season/week route).
- D-14: Images carry season+week in the filename so social caches never serve a stale card for a new week.

### Share page HTML (SHARE-02)
- D-15: Static `index.html` per share page: `<title>`, meta description, `og:type=article`, `og:site_name`, `og:title`, `og:description`, `og:url` = the share page itself (absolute), `og:image` absolute on the production origin + `og:image:width/height/alt/type`, `twitter:card=summary_large_image` + twitter title/description/image, `link rel=canonical` = the share page. Every interpolated field HTML-escaped (`&<>"'`) via one `escapeHtml` in share.ts with a test using hostile input.
- D-16: Origin: reuse Phase 10's `resolveSiteOrigin(process.env)` (SITE_ORIGIN → VERCEL_PROJECT_PRODUCTION_URL → production fallback). Note: the existing helper's final fallback is the production origin, not localhost — keep it (local builds produce prod-pointing tags, which is what crawlers need; local preview still works because the redirect is root-relative).
- D-17: Redirect: inline `<script>location.replace('/' + HASH)</script>` (root-relative so it works on localhost/preview) — no meta refresh. Visible fallback: short branded line + "Open {Team} on Feel-Good Score →" link to the same hash route, with minimal inline CSS using Phase 12 colors/fonts (system font stack fallback; no JS bundle).
- D-18: Pages are regenerated every build into `dist/s/` and `dist/og/`; nothing generated is committed. No vercel.json rewrites (a catch-all would shadow `/s/`).

### Durability & build budget
- D-19: `SHARE_LAUNCH = { season: 2026, week: 9 }` in share.ts. Each build generates team + callout pages/images for every (season, week) present in committed snapshots with (season, week) ≥ launch — so links shared in launch week keep resolving all season. Pre-launch weeks get no share pages (copy falls back to hash link).
- D-20: Measure render time per card and total share-step time; log both from the script. Budget: share step ≤ 60 s at launch; project the full-season count (~14 weeks × ~45 cards). If the projection exceeds ~3 min, render with a small worker/concurrency pool; if still too slow, keep pages for all weeks but images only for weeks ≥ launch that fit, and document. Record actual numbers in SUMMARY.
- D-21: Team cards for a week use that week's snapshot row (score, band, label, rank, record); callout cards use that week's callouts list (all six types, including movers).

### Copy-link wiring (SHARE-03)
- D-22: `CalloutCard` copy button copies `location.origin + calloutSharePath(c)` when `hasSharePage(c.season, c.week)`, else the existing `deepLink(href)`.
- D-23: Team page gets a new "Copy link" button in its header (same component pattern/status/manual-fallback behavior as CalloutCard — extract a small shared `CopyLinkButton.svelte` if it reduces duplication). It copies the team share URL for the viewed (season, week) (latest when the hash has no season/week) when `hasSharePage`, else the hash deep link.
- D-24: `hasSharePage(season, week)` = (season, week) ≥ SHARE_LAUNCH and that week exists in the loaded data (the build generates pages for exactly that set). Share URLs use `location.origin` so preview/local copies work; the tags on the page always point at production.

### Launch verification
- D-25: After push + Vercel READY, fetch one team share page and one callout share page on production with `facebookexternalhit/1.1`, `Twitterbot/1.0` and `Slackbot-LinkExpanding 1.0` UAs; assert 200, og:image/og:url/twitter:card present and absolute, and the og:image URL returns 200 image/png. Report 403s from Vercel bot protection honestly.
- D-26: Real Slack / iMessage / X pastes and the Facebook Sharing Debugger / LinkedIn Post Inspector are human UAT items in `14-HUMAN-UAT.md` with the exact URLs to paste.

### Claude's Discretion
- Exact card layout geometry, font sizes, stripe vs bar treatment (UI-SPEC decides within the Phase 12 system).
- Whether to extract `CopyLinkButton.svelte` or duplicate the small logic.
- Concurrency mechanism if D-20 needs it.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `web/src/lib/siteOrigin.ts` — `resolveSiteOrigin(env)` (Phase 10), already imported by `vite.config.ts` with a `.ts` extension.
- `web/src/lib/copyLink.ts` — `copyText` three-tier fallback and `deepLink(hash)`.
- `web/src/lib/callouts.ts` — `calloutHref`, `CARD_TYPES`; `web/src/lib/router.ts` — `teamHash`.
- `web/src/lib/teamNames.ts` — `eraName`/`eraText`; `web/src/lib/logoSwitch.ts` — `logosOff`; `web/src/lib/format.ts` — `bandIndex`, `moodToken`.
- `web/src/components/CalloutCard.svelte` — copy button + status live region + manual input fallback pattern.
- `web/public/logos/{FR}.png` (+ `sm/`), `web/public/og-default.png` (Phase 10 static card).
- Data: `public/data/meta.json` (`latest`, `bands` with labels/emoji, `seasons[].week_labels`, `teams` colors/names), `public/data/snapshots/{season}.json` (`weeks[w]` rows; `callouts[w]` lists).

### Established Patterns
- Pure helpers in `src/lib/*.ts` with sibling `*.test.ts` (vitest); components thin.
- `vite.config.ts` plugins handle build-time concerns (site origin, logo takedown via `closeBundle`).
- Mood colors via `--mood-{0..6}` tokens; `moodToken(bandIdx, n)`.

### Integration Points
- `web/package.json` build script; `web/src/components/CalloutCard.svelte`; `web/src/components/TeamPage.svelte` header (~line 219); `dist/s/**`, `dist/og/**`, `dist/og-default.png`.

</code_context>

<specifics>
## Specific Ideas

- Example live URLs at launch: `/s/team/BUF/2026-w9/`, `/s/c/2026/9/CLE-worried/`.
- Measure and report build time before/after.
- ≤4 card sample images/screenshots in the phase dir.

</specifics>

<deferred>
## Deferred Ideas

- Twemoji emoji on cards (would need vendored SVGs + CC-BY attribution).
- Dark-theme card variant.
- Share cards for records/explore/history pages; Web Share API and download buttons.
- Pruning of very old share weeks once per-season build time grows (revisit next season).

</deferred>

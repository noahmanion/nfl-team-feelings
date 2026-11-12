# Architecture Research: v2.0 Public Site Integration

**Domain:** Static data-journalism site (Python pipeline → static JSON → Vite/Svelte SPA) going public
**Researched:** 2026-11-11
**Confidence:** HIGH for integration points (read from the actual code). MEDIUM for OG-crawler behavior (verify with each platform's debugger).

This document covers only what v2.0 adds or changes. Everything here comes from reading `pipeline/src/fgs/*.py` and `web/src/**`, not from assumptions.

---

## Existing Architecture: The Facts That Constrain v2

| Fact (verified in code) | Where | Why it matters for v2 |
|---|---|---|
| `write_export` **owns `web/public/data/` entirely**. It writes to a temp dir and atomically swaps it in, so anything not in the `files` dict gets deleted. | `export.py: write_export` | Logos, OG images, and share stubs must **not** live under `web/public/data/`. New JSON (EPA, win totals) must be added as keys of the `build_export` `files` dict. |
| `build_export` is pure (`{relpath: obj}`) and already receives `derived["team_game_epa"]` (per team-game `off_epa, off_plays, off_sr, def_epa, def_plays, net_epa, qb_*, low_confidence`). | `cli.py: derive_games`, `pbp.py: TGE_COLUMNS` | EPA charts need **no new data loading**, only a new export file. |
| Exported JSON has **no raw EPA/play**. Snapshot rows carry only `contribs.epa_traj` / `points` (a z-scored trajectory) and `qb`. | `export.py: _row` | The EPA scatter needs a new export. |
| `meta.teams[ABBR] = {name, nick, primary, secondary}`. `teams.parquet` also has `team_logo_espn`, `team_logo_wikipedia`, `team_logo_squared`, `team_wordmark`, `team_conf`, `team_division`. | `export.py: team_meta`, cache `teams.parquet` | The logo URLs are already in the pipeline cache. Conference and division are also available for scatter faceting. |
| `fingerprint.CODE_FILES` includes **`draft.py` and `expectation.py`** (AST-hashed, so comments and docstrings are ignored). | `fingerprint.py` | Any *code* change to those files makes `callout_evidence.json` stale, and `build_export` then **raises ValueError and refuses to export** until `uv run fgs evidence` is rerun and committed. Adding comments only is free. |
| Vegas win totals flow through `expectation.vegas_expectations` → `exp_total` → the `vs_expectation` factor → the score. | `expectation.py`, `cli.py:190` | 2021+ hand-entered totals **must not** enter this path, or frozen-model scores for 2021+ change, including the consumed 2022–25 holdout. |
| `paths.PREREG_PATH = pipeline/PREREGISTRATION.md`. The holdout check requires that file to have **exactly one commit**. | `paths.py`, `holdout.py:453` | v2 pre-registration must be a **new file**. Never edit v1's. |
| `pipeline/data/` is gitignored, but `web/public/data/` is committed (94 files, about 15 MB). | `pipeline/.gitignore`, `git ls-files` | Hand-entered CSVs must live outside `pipeline/data/`. Vercel can build the web app **without Python**, since the data ships in git. |
| Routing is hash-only (`#/team/BUF/2026/9`). `deepLink()` builds `origin + pathname + hash`. `CalloutCard` "Copy link" uses `calloutHref` (season/week form). | `router.ts`, `copyLink.ts`, `callouts.ts` | Crawlers never see the fragment, so share URLs need real paths. |
| Styling: `app.css` tokens. Components have about 476 `var(--…)` references and about 41 hard-coded px values. Three `Plot.plot` call sites each inline their own `style:` object. | `app.css`, `HistoryChart`, `MethodologyChart`, `Sparkline` | A redesign is mostly a token swap plus one shared Plot theme helper. |
| `TeamChip` (color-gradient square) is used in 6 components: BoardRow, RecordsPage, MoversStrip, CalloutCard, TeamPage, RecentGames. | grep | The logo integration point is a single wrapper component that falls back to `TeamChip`. |
| Callouts have no ID. Uniqueness is (season, week, franchise, type). Current season: 104 callouts through week 9. All seasons: 5,958. | `snapshots/*.json` | Share stubs and OG images are feasible for the **current season plus 32 teams** (hundreds), not for all history (about 6k PNGs, hundreds of MB). |

---

## Target Architecture (v2)

```
                         LOCAL (weekly)                                   │  VERCEL (on git push)
┌───────────────────────────────────────────────────────────────┐        │ ┌──────────────────────────────────────┐
│ pipeline/  uv run fgs refresh                                 │        │ │ root: web/   npm run build            │
│                                                               │        │ │                                       │
│  inputs/win_totals_2021plus.csv (NEW, committed, hand-entered)│        │ │  vite build ──► dist/ (SPA + public/) │
│  inputs/draft_forfeit_sources.md (NEW, citations)             │        │ │       │                               │
│          │                                                    │        │ │       ▼                               │
│  fgs/wintotals.py (NEW, display-only, NOT in CODE_FILES)      │        │ │  scripts/share.mjs (NEW, postbuild)   │
│  fgs/draft.py FORFEITS (MODIFIED only if corrections found)   │        │ │   reads dist/data/{meta,latest,       │
│  fgs/export.py (MODIFIED):                                    │        │ │     snapshots/<cur>.json}             │
│     + epa/{season}.json        (NEW file)                     │        │ │   satori + resvg ─► dist/og/*.png     │
│     + teams/{ABBR}.json.win_totals (NEW field)                │        │ │   HTML stubs  ─► dist/s/**/index.html │
│     + meta.teams[ABBR].conf/division (NEW fields)             │        │ │       │                               │
│          │ write_export (owns web/public/data/)               │        │ │       ▼                               │
│          ▼                                                    │        │ │  static CDN: /, /data/*, /logos/*,    │
│  web/public/data/**  ─────── git commit + push ───────────────┼────────┼─►│  /og/*, /s/**                        │
│                                                               │        │ └──────────────────────────────────────┘
│  fgs logos (NEW one-shot cmd) ─► web/public/logos/{ABBR}.png  │        │
│     (committed, outside data/, so write_export never drops it)│        │
└───────────────────────────────────────────────────────────────┘        │
```

Key decision: **OG images are rendered at Vercel build time from committed JSON**, not in the Python pipeline. Deploys stay deterministic, no PNG churn lands in git (Dropbox-synced repo), and the renderer gets the same font files and logos as the site.

---

## Component Map: New vs Modified

### Pipeline (`pipeline/`)

| Component | Status | Change |
|---|---|---|
| `pipeline/PREREGISTRATION_V2.md` | **NEW** | v2 hypotheses (good-loss luck, free agency, win totals into the score), metrics, holdout definition, and decision rules. A separate file, because v1's must keep exactly one commit. |
| `fgs/paths.py` | MODIFIED (small) | Add `PREREG_V2_PATH`, `INPUTS_DIR = PIPELINE_ROOT / "inputs"`, `WEB_LOGOS_DIR = PIPELINE_ROOT.parent / "web/public/logos"`. |
| `pipeline/inputs/win_totals_2021plus.csv` | **NEW** (committed) | `season,team,line,over_odds,under_odds,source,entered_on`. Same column names as nflverse so one reader handles both. Must live outside `data/`, which is gitignored. |
| `fgs/wintotals.py` | **NEW** | `load_display_win_totals()`: concatenates the cached nflverse CSV (2003–2020) with the manual CSV (2021+), maps codes through `RAW_TO_FRANCHISE`, and validates 32 teams per season, lines in [2, 15], and no duplicate (season, team). **Must not be imported by `expectation.py`, `features.py`, or `cli.derive_games`**, and must not be added to `fingerprint.CODE_FILES`. |
| `fgs/export.py` | MODIFIED | (1) `files[f"epa/{season}.json"]` from `derived["team_game_epa"]` joined to `team_games` for `asof_week`, `week`, `opponent_id`, `game_type`. (2) `teams/{ABBR}.json` gets `win_totals: {season: [line], source: [...]}` (columnar) from `wintotals`. (3) `team_meta` adds `conf`, `division` for facets. Optional: `meta.version` → 2. |
| `fgs/draft.py` `FORFEITS` (lines ~56–81) | MODIFIED **only if** verification finds errors | Add a citation comment per entry (free, since the AST fingerprint ignores comments). If an entry changes, then `fgs evidence` → commit `callout_evidence.json` → `fgs refresh`. Scores don't move (draft weight 0, display-only), but week-0 draft text and surplus ranks do. |
| `fgs/checks.py` | MODIFIED (small) | Add a check that `wintotals` covers the latest season, a warning not a failure. Add a **guard** that the input to `vegas_expectations` has `max(season) <= 2020`. |
| `fgs/cli.py` | MODIFIED | (1) Pass display win totals into `build_export` (the `derived` dict or a kwarg). (2) New `fgs logos` one-shot subcommand: read `teams.parquet` `team_logo_espn` for the 32 canonical teams, download, and write `web/public/logos/{ABBR}.png`. Run by hand, commit the output. Not part of `refresh`, so the weekly refresh stays offline-safe. |
| `tests/` | MODIFIED | Export contract tests for `epa/{season}.json` and `win_totals`, plus the leakage guard: the manual CSV never changes `features.parquet` for 2021+. |

### Web (`web/`)

| Component | Status | Change |
|---|---|---|
| `vercel.json` | **NEW** (small) | `buildCommand`/`outputDirectory` only if the auto-detect fails. `headers`: `/og/(.*)` immutable (filenames are versioned), `/logos/(.*)` long max-age, `/data/(.*)` `max-age=0, must-revalidate` (the default, but say it explicitly). No SPA rewrites are needed with hash routing. |
| `index.html` | MODIFIED | Site-wide default `og:title`, `og:description`, `og:image=/og/site.png`, `twitter:card=summary_large_image`, `<link>` for self-hosted fonts. |
| `scripts/share.mjs` | **NEW** | Postbuild step (`"build": "vite build && node scripts/share.mjs"`). Reads `dist/data/meta.json`, `latest.json`, and `snapshots/{latest.season}.json`. Renders PNGs via **satori 0.63 + @resvg/resvg-js 2.6** (pure JS/WASM-friendly, works in Vercel's Node build image). Writes stubs and images (see Share URL Design). Absolute origin comes from `process.env.VERCEL_PROJECT_PRODUCTION_URL` (fallback `SITE_ORIGIN`, then `http://localhost:4173`). |
| `scripts/og-template.mjs` | **NEW** | Satori JSX-as-object card templates: team card and callout card. Uses the same token values as `app.css`, duplicated as a small JS constant (satori can't read CSS vars). |
| `src/lib/share.ts` (+ test) | **NEW** | Pure: `teamShareUrl(abbr)`, `calloutShareUrl(c, meta)` returns `/s/c/{season}/{week}/{franchise}-{type}/` **only when `c.season === meta.latest.season`**, else `null`. Shares the slug rule with `share.mjs`; keep one implementation in a plain `.js` module importable by both, or test them against each other. |
| `src/lib/copyLink.ts` | MODIFIED (tiny) | No logic change. Callers pass the share URL when available, else `deepLink(hash)`. |
| `CalloutCard.svelte` | MODIFIED | "Copy link" copies `calloutShareUrl(...) ?? deepLink(href)`. Needs `meta` (or `latestSeason`) as a prop. |
| `TeamPage.svelte` | MODIFIED | Add a "Share" / "Copy link" button using `teamShareUrl`. Swap `TeamChip size=24` for `TeamLogo`. Add a display-only win-total line ("Vegas preseason: 9.5 · Model: 8.7"). |
| `src/components/TeamLogo.svelte` | **NEW** | `<img src={BASE_URL + 'logos/' + abbr + '.png'} alt="" onerror → fallback>`. On error it renders `<TeamChip>`. Decorative, so `alt=""`, because the name is always adjacent. Fixed sizes from tokens (`--logo-sm`, `--logo-lg`). |
| BoardRow, RecordsPage, MoversStrip, CalloutCard, RecentGames | MODIFIED (1-line each) | `TeamChip` → `TeamLogo` (same props + `abbr`). |
| `TeamChip.svelte` | UNCHANGED | Becomes the fallback. |
| `src/app.css` | MODIFIED (main redesign surface) | New and retuned tokens: `--font-display` (condensed or slab headline), `--font-sans` (self-hosted), `--font-mono` (tabular numbers), `--bg` to a 538-ish warm light gray, `--grid`, `--axis`, `--rule-heavy` (thick black top rules for sections), `--logo-sm/lg`, a type scale adjusted within the existing 4-size/2-weight rule, or that rule explicitly relaxed. Keep the dark-mode block (restyle it, don't delete it). |
| `src/lib/plotTheme.ts` | **NEW** | `plotStyle()` and `plotDefaults` (font, grid on, `--grid` stroke, no frame, tick sizes) consumed by HistoryChart, MethodologyChart, Sparkline, and the new charts. Replaces three inline `style:` objects, so the restyle happens in one place. |
| `src/lib/types.ts` | MODIFIED | `EpaFile`, `TeamFile.win_totals`, `TeamMeta.conf/division`. |
| `src/lib/data.ts` | MODIFIED | `loadEpa(meta, season)`, using the same per-`generated_at` session-cache pattern as `loadGames`. |
| `src/lib/epa.ts` (+ test) | **NEW** | Pure: play-weighted season-to-date off/def EPA per team as of `week` (filter `asof_week <= week`, optional REG-only, optional last-N games). Mirrors the as-of semantics the scrubber already uses. |
| `src/lib/router.ts` | MODIFIED | Add `{ kind: 'explore'; season?: number; week?: number }` with `#/explore` and `#/explore/2026/9`. Use `exploreHash()`. |
| `App.svelte`, `SiteHeader.svelte` | MODIFIED | One route branch plus a nav item. |
| `src/components/ExplorePage.svelte` | **NEW** | Hosts the scatters and reuses `Scrubber` for season/week. |
| `src/components/EpaScatter.svelte` | **NEW** | Plot `dot`, x = offense EPA/play, y = defense EPA/play allowed with a **reversed y-axis** (up = better defense), logos via Plot `image` mark (`src: d => logoUrl(d.franchise)`), mood-band color ring from the snapshot row, `tip`, and highlight for the my-team pin. |
| `src/components/ScoreVsRecordScatter.svelte` | **NEW** (optional) | Score vs win% from existing snapshot rows. No new data. This is the perception-gap chart and the core-value visual. |

---

## Share URL Design (the hash-route problem)

**Problem:** `https://site/#/team/BUF` is sent to crawlers as `https://site/`, so every share shows the generic card.

**Pattern: prerendered stub pages with a JS (not meta-refresh) redirect.**

```
/s/team/BUF/index.html                       ← share URL for a team (always "latest")
/s/c/2026/9/CLE-worried/index.html           ← share URL for a callout (immutable)
/og/team/BUF-2026-9.png                      ← image versioned by data week
/og/c/2026-9-CLE-worried.png
/og/site.png                                 ← default
```

Stub contents (generated):

```html
<!doctype html><html><head>
<meta charset="utf-8">
<title>Browns: 5-4, but you should feel worried · Feel-Good Score</title>
<meta property="og:title" content="5-4, but you should feel worried">
<meta property="og:description" content="The Browns have the 16th-best record but the 25th-best score.">
<meta property="og:image" content="https://<prod-origin>/og/c/2026-9-CLE-worried.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:url" content="https://<prod-origin>/s/c/2026/9/CLE-worried/">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="https://<prod-origin>/s/c/2026/9/CLE-worried/">
<script>location.replace('/#/team/CLE/2026/9')</script>
</head><body><noscript><a href="/#/team/CLE/2026/9">Open the Browns on Feel-Good Score</a></noscript></body></html>
```

Rules:
- **JS redirect, not `<meta http-equiv="refresh">`.** Social crawlers don't run JS, so they stay on the stub and read its tags. Some crawlers may follow meta refresh, which would land them on the generic `index.html`. MEDIUM/LOW confidence on per-platform behavior, so verify with the Facebook Sharing Debugger, the LinkedIn Post Inspector, and a real Slack/iMessage/X paste after the first deploy.
- **og:url and og:image are absolute**, with the origin from `VERCEL_PROJECT_PRODUCTION_URL` (a Vercel system env var; verify it is exposed to the build) so preview deploys still point images at production. Accept that preview-deploy stubs reference prod images.
- **Version the image filename by (season, week)**, because platforms cache images by URL for days. The team stub URL stays stable while its `og:image` changes weekly.
- **Scope:** 32 team stubs plus every callout in the *current season* (about 250 per full season; 104 now). Older-season callouts fall back to copying the hash deep link. That's an explicit, documented limit, not a bug.
- Vercel serves `dist/s/team/BUF/index.html` at `/s/team/BUF/` with no config.
- The `/s/` prefix keeps stubs clear of `/data/`, `/assets/`, `/logos/`, and `/og/`.

---

## Data Flow Changes

### 1. EPA exploratory charts

```
pbp cache ─► pbp.team_game_epa (existing) ─► derived["team_game_epa"] (existing)
                                                   │ join team_games on (game_id, franchise_id)
                                                   ▼  for asof_week, week, opponent_id, game_type
                     export.py  files["epa/{season}.json"]   (NEW, columnar, ~15 KB/season)
                     { season, franchise[], opponent[], week[], asof_week[], game_type[],
                       off_epa[], off_plays[], off_sr[], def_epa[], def_plays[],
                       low_confidence: bool }  (floats rounded to 3 dp)
                                                   ▼
web: data.loadEpa(meta, season) ─► lib/epa.ts seasonToDate(file, week, {regOnly, lastN})
     ─► EpaScatter (joined with loadSeason rows for band/score/rank)
```

- Export per-game rows, not pre-aggregated, so the web can do season-to-date, last-N, or REG-only without another export. Aggregation must be **play-weighted** (`sum(epa*plays)/sum(plays)`), not a mean of game means.
- `def_epa` is EPA *allowed* (lower is better). Invert the y-axis rather than negating the data, so tooltips still show real values.
- Values are **garbage-time filtered** (wp 0.05–0.95, `pbp.WP_LO/HI`) and opponent-*unadjusted*. Label both on the chart. These numbers won't match rbsdm/nfelo exactly.
- 1999–2000 carry `low_confidence` (thin pbp), and three games have no pbp (`KNOWN_NO_PBP`). Show a note.
- No model code changes. `export.py` is not in `CODE_FILES`, so the evidence fingerprint is unaffected.

### 2. Display-only win totals

```
nflverse win_totals.csv (cache, 2003-2020) ─┐
inputs/win_totals_2021plus.csv (NEW) ───────┴─► wintotals.load_display_win_totals()  (NEW, display-only)
                                                 ▼
                                export.py → teams/{ABBR}.json.win_totals
                                                 ▼
                                TeamPage "Vegas preseason line" (next to model expectation)

expectation.vegas_expectations ◄── load_win_totals() (UNCHANGED; nflverse file only, ≤2020 guarded)
```

The two paths never touch. This is the single most important integration rule this milestone, because it keeps the frozen v1 score identical.

### 3. Logos

```
teams.parquet.team_logo_espn ─► fgs logos (one-shot) ─► web/public/logos/{ABBR}.png (committed)
                                                           ├─► TeamLogo.svelte (img, onerror → TeamChip)
                                                           ├─► EpaScatter (Plot image mark)
                                                           └─► scripts/share.mjs (satori, read from disk as data URI)
```

- **Vendor, don't hotlink.** Satori needs the bytes at build time anyway. Hotlinking ESPN's CDN from a public site risks breakage and is impolite. Use about 32 × 20–40 KB, or downscale to about 160 px in the logos command.
- **A web-side path convention (`logos/{ABBR}.png`) beats a JSON field.** It avoids touching the export contract for something static and keeps logos out of `write_export`'s directory. The only pipeline involvement is the one-shot downloader, which can read URLs from the cache it already has.
- Fallback: `<img onerror>` swaps to `TeamChip`. Also fall back when `abbr` isn't in `meta.teams`.
- Logos are current-branding only (historic Rams/Chargers/Raiders logos differ). That's fine for a fan visualization; note it in the methodology footer along with an "NFL marks are property of their owners" line.

### 4. Draft-forfeit verification

The table is `pipeline/src/fgs/draft.py: FORFEITS` (24 keyed (year, round) entries, 27 slot-owners), with `UNATTRIBUTED_SHORT` right below it. Consumer: `draft.original_slots/surplus` → week-0 `draft` block in snapshots, plus `checks.py` MODEL-16 conservation.

Workflow:
1. Verify each entry against a primary source (NFL.com/league announcement, PFR draft pages). Record the URLs in `pipeline/inputs/draft_forfeit_sources.md` or as inline comments. Comments are fingerprint-neutral.
2. If **no** entry changes, nothing else happens.
3. If any entry changes: edit `FORFEITS`, run `uv run pytest` (draft tests), run `uv run fgs evidence` (the code fingerprint changed), commit `callout_evidence.json`, then run `uv run fgs refresh`. Scores are unchanged (draft weight 0), but week-0 draft text and ranks may shift for the affected years.

### 5. v2 pre-registration

A docs-only artifact: `pipeline/PREREGISTRATION_V2.md`. It has no code dependencies and should reference the v1 frozen `weights.yaml` sha256 and the git SHA. Its integrity check can reuse `holdout.file_sha256` and the "exactly one commit" rule via a new `PREREG_V2_PATH`, but that tooling belongs to the v2 model milestone, not this one.

---

## Architectural Patterns to Follow

### Pattern 1: Add to the `files` dict, never write beside it
**What:** Every new JSON artifact is a key in `build_export`'s return value.
**Why:** `write_export` replaces `web/public/data/` atomically and deletes anything it didn't write. Anything written around it disappears on the next refresh.
**Corollary:** Non-JSON static assets (logos, fonts) go in `web/public/<other>/`, and build-generated assets (OG, stubs) go in `dist/` via the postbuild script.

### Pattern 2: Display-only data gets its own module, outside the fingerprint
**What:** `wintotals.py` is new and separate from `expectation.py`. Forfeit citations go in comments.
**Why:** `fingerprint.CODE_FILES` makes any executable change to model modules invalidate the evidence and block export, and touching the expectation path changes frozen scores.

### Pattern 3: Pure TS helper + thin component (existing convention)
**What:** `lib/epa.ts` and `lib/share.ts` hold the logic and carry vitest tests. Components only render. This mirrors the existing `callouts.ts`, `history.ts`, and `records.ts`.

### Pattern 4: Restyle through tokens + one Plot theme
**What:** Change values in `app.css`, add a few tokens, and centralize Plot options in `plotTheme.ts`.
**Why:** About 476 token references already exist, so most components restyle without edits. Touch component CSS only for structural 538-isms (heavy section rules, uppercase small-caps labels, left-aligned chart titles with a subtitle line).
```ts
// lib/plotTheme.ts
export const plotStyle = { fontFamily: 'var(--font-sans)', fontSize: '13px', color: 'var(--text-muted)', background: 'transparent' }
export const plotBase = { style: plotStyle, grid: true, marginTop: 24 } // spread into Plot.plot({...plotBase, ...})
```

### Pattern 5: Build-time share generation from committed data
**What:** `share.mjs` runs after `vite build` and reads `dist/data/*`. It is deterministic for a given commit.
**Why:** It needs no server runtime (honors the "static only" constraint), puts no binaries in git, and keeps Python off Vercel.

---

## Anti-Patterns to Avoid

| Anti-pattern | Why bad | Instead |
|---|---|---|
| Appending 2021+ lines to `pipeline/data/cache/win_totals.csv` | `vegas_expectations` would consume them, changing `expectation_source` and the score for 2021+, which silently rewrites the frozen model and the consumed holdout | A separate `inputs/` CSV and the `wintotals.py` display path, plus a guard check |
| Editing `pipeline/PREREGISTRATION.md` for v2 | Breaks the v1 holdout integrity check ("exactly one commit") | `PREREGISTRATION_V2.md` |
| Dynamic OG via `@vercel/og` Edge/Serverless functions | Adds a server runtime and function cold starts; contradicts the static constraint | Build-time satori → PNG |
| Generating OG and stubs for all 5,958 historical callouts | Hundreds of MB, slow builds | Current season plus teams; history falls back to hash links |
| Writing logos or OG into `web/public/data/` | Wiped by the next `write_export` | `web/public/logos/`, `dist/og/` |
| Meta-refresh redirects in stubs | Some crawlers may follow them to the generic page | JS `location.replace` + `<noscript>` link |
| Hotlinking ESPN logo URLs from the client | Third-party dependency, breakage, unusable by satori | Vendored PNGs |
| Restyling by rewriting every component | High churn, regressions across 149 web tests | Token values + `plotTheme.ts` + targeted structural CSS |
| Switching to SvelteKit/history routing to "fix" sharing | A large refactor of App/router for something stubs solve | Keep hash routing; stubs at `/s/**` |

---

## Suggested Build Order

| # | Phase | Depends on | Rationale |
|---|---|---|---|
| 1 | **v2 pre-registration doc** | nothing | **Time-critical.** The 2026 season is at week 10. Every week before commit is lost holdout data, and the document must define the holdout as starting *after its commit* (e.g. 2026 weeks ≥ N plus 2027), or as 2027 only. Docs only, so about an hour. |
| 2 | **Vercel deploy of the current site** | nothing (data is committed) | Gets the production origin needed for absolute `og:image` URLs. Proves Node 22 (`engines >=22.12`), root dir `web`, and the `dist` output. Ships value immediately. |
| 3 | **Pipeline data loose ends + exports**: forfeit verification, `inputs/win_totals_2021plus.csv` + `wintotals.py`, `epa/{season}.json`, `meta.teams.conf/division`, `fgs logos` | none (parallel with 2) | All pipeline touches happen in one phase, so `fgs evidence` reruns at most once and there's a single refresh/commit. Produces every artifact the web phases consume. |
| 4 | **Redesign foundation + logos**: tokens, self-hosted fonts, `plotTheme.ts`, `TeamLogo` swap in 6 components, default OG meta in `index.html` | 3 (logos) | New charts and OG cards must be built in the final visual language once, not restyled later. |
| 5 | **Explore/EPA charts**: `#/explore`, `EpaScatter`, optional `ScoreVsRecordScatter` | 3 (epa export), 4 (theme, logos) | Pure web work on stable data and style. |
| 6 | **Share/OG**: `share.mjs`, templates, stubs, `share.ts`, Copy-link changes, `vercel.json` headers, crawler verification | 2 (prod origin), 4 (fonts, logos, palette) | Last, because the cards encode the final design and need the deployed origin to test against real crawlers. |

Phases 1–3 are independent of one another and can run in parallel or in any order, but 1 should land first because it's time-sensitive.

---

## Scalability / Size Notes

| Concern | Now | v2 impact |
|---|---|---|
| Deployed data | about 15 MB (snapshots 14 MB) | +about 0.4 MB EPA files, +about 1 MB logos, +about 15–25 MB OG PNGs per full season (about 280 × 60 KB). Well within Vercel Hobby. |
| Build time | `vite build` takes seconds | satori + resvg take about 30–80 ms per card, so about 300 cards in under 30 s. |
| Weekly ops | `fgs refresh` → commit → push | Unchanged. Push triggers the Vercel build, which regenerates OG for the new week. |

---

## Open Questions / Flags for Phase Research

- **Crawler behavior** for JS-redirect stubs on X, Facebook, LinkedIn, Slack, iMessage, and Discord: test after phase 2. (MEDIUM confidence)
- Whether `VERCEL_PROJECT_PRODUCTION_URL` is set during the **build step** on Hobby (expected yes; verify) versus needing a manual `SITE_ORIGIN` env var. A custom domain changes the origin.
- **Font choice and licensing:** pick OFL fonts available as TTF/OTF/WOFF (satori does **not** accept WOFF2). Self-host for both the site and satori.
- The PROJECT.md count of "18 draft-forfeit entries" doesn't match the 24 (year, round) keys / 27 owners currently in `FORFEITS`. Confirm which entries were entered from memory before verifying.
- Whether the 2021+ win totals should also appear on week-0 board rows (the snapshot row contract) or only on the team page. The team page alone is the recommendation: smaller blast radius, and the snapshot files are already 14 MB.

## Sources

- Code read directly (HIGH): `pipeline/src/fgs/{export,cli,fingerprint,draft,expectation,efficiency,pbp,paths,holdout}.py`, `web/src/lib/{router,route.svelte,data,copyLink,callouts,types}.ts`, `web/src/app.css`, `web/src/components/{TeamChip,CalloutCard}.svelte`, `web/package.json`, `web/vite.config.ts`, `web/index.html`, `.gitignore` files, `teams.parquet` and `team_game_epa.parquet` schemas (inspected live).
- npm registry (live 2026-11-11): satori 0.63.2, @resvg/resvg-js 2.6.2, sharp 0.35.5. HIGH for versions.
- OG/crawler redirect guidance (LOW–MEDIUM, general advice that tags must be in the served HTML and image URLs absolute; nothing specific on meta refresh): [DEV: link preview fixes](https://dev.to/ctrlzed/link-preview-not-showing-fix-it-on-whatsapp-x-linkedin-1l25), [macmyths: debug OG with curl](https://macmyths.com/how-to-debug-open-graph-tags-with-curl/), [andrewbaker.ninja: thumbnail troubleshooting](https://andrewbaker.ninja/2026/03/05/the-hitchhikers-guide-to-fixing-why-a-thumbnail-image-does-not-show-for-your-article-on-whatsapp-linkedin-twitter-or-instagram/).
- Training knowledge (MEDIUM): Vercel serves `dir/index.html` at `dir/`; satori rejects WOFF2; `VERCEL_PROJECT_PRODUCTION_URL` system env var.

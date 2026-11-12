# Project Research Summary

**Project:** Feel-Good Score, milestone v2.0 "Public Site"
**Researched:** 2026-11-11
**Confidence:** HIGH for integration and tooling (verified against the code and live probes). MEDIUM for social-crawler behavior, the FiveThirtyEight-style design brief, and trademark posture.

## Executive Summary

v2.0 takes the finished site, which runs on a frozen model, and makes it public, shareable, better-looking and more explorable. It adds no model changes. The plan:

- Host the static `dist/` on Vercel.
- Render share cards at build time.
- Restyle the site through design tokens plus one shared chart theme.
- Add two opinionated charts built on data the pipeline already computes.

The new stack is small: satori and @resvg/resvg-js for the cards, Fontsource for fonts, and logos stored in the repo. There are no new Python dependencies and no second chart library.

There are two structural constraints:

1. **Crawlers can't see hash routes.** Per-team and per-callout previews need static share pages at real paths. Each page carries its own `og:*` tags and sends the visitor on to the hash route with JavaScript. The router doesn't change and no server runtime is needed.
2. **The model is frozen.**
   - Editing `expectation.py`, `draft.py` or `mood.py` changes the `fingerprint.CODE_FILES` hash.
   - Any 2021+ Vegas line that reaches `vegas_expectations` would quietly change the results of the holdout seasons that were already used up.

   The defense is structural. Display-only data lives in its own module. The redesign stays inside `web/`. A golden composite-hash test pins every score from 2025 and earlier.

Risks, highest cost first:

1. **The v2 holdout erodes.** Every 2026 week played before the v2 pre-registration is committed is lost to the holdout. Write it first, define the holdout as games kicking off after the v2 freeze commit, and make 2027 the primary evaluation.
2. **Frozen scores drift.** Causes include the win totals leaking in, forfeit edits, or re-pulling play-by-play data.
3. **Share links decay.** Social caches hold images for days, and old share pages can 404. Put the season and week in every path and image name.
4. **The planned logo links are broken.** nflverse's Wikipedia logo URLs already return HTTP 400, so store the logos in the repo. Relocated and renamed franchises need era-correct names.

## Orchestrator Decisions (resolved)

| Topic | Decision |
|---|---|
| Share cards | Rendered at build time with satori and @resvg/resvg-js in a Node script after `vite build`. Not `@vercel/og`, not Pillow. |
| Share pages | Static pages at real paths that redirect to the hash route with JavaScript, not a meta refresh. Regenerated every build, not committed. Season and week in paths and image filenames. |
| Logos | Downloaded once into `web/public/logos` from ESPN. Current logo everywhere, era-correct names, color-chip fallback. |
| Fonts | Inter and IBM Plex Mono, plus Source Serif 4 if needed, self-hosted via Fontsource. Satori can't read WOFF2 or variable fonts, so it gets static TTF/WOFF files. |
| Node | Pinned to 24.x. The `>=22.12` range would resolve to Node 26 on Vercel. |
| v2 pre-registration | New `pipeline/PREREGISTRATION_V2.md`. The holdout is games kicking off after the v2 freeze commit, with 2027 primary. The v1 file is never edited, because the v1 holdout guard requires it to stay at exactly one commit. |
| Frozen-score guard | A golden test hashes the composite score and label for every snapshot from 2025 and earlier. |
| 2021+ win totals | Stored in `pipeline/inputs/` and read by a display-only module. Shown on the team page only and never fed into the score. |
| Forfeits | Verify all 24 `FORFEITS` entries; PROJECT.md's count of 18 is stale. Supplemental-draft forfeits get their own label. |

## Key Findings

### Stack (additions only)

- **Vercel Git integration (Hobby plan):**
  - Root directory `web`, Vite preset, output `dist`, no `vercel.json` rewrites.
  - The data is already committed, so the build never runs Python.
  - The Hobby plan is non-commercial only: no ads or affiliate links.
- **satori 0.63.2 and @resvg/resvg-js 2.6.2** (devDependencies):
  - Produces a 1200×630 card in about 1 second.
  - Uses plain `{type, props}` objects, so no JSX toolchain is needed.
  - Pin satori to an exact version, since it is pre-1.0.
- **Fontsource 5.3.x:** Inter and IBM Plex Mono stand in for Atlas Grotesk and Decima Mono, the fonts FiveThirtyEight actually used.
- **Observable Plot 0.6.19**, already installed, has every mark needed: `image`, `dot`, `linearRegressionY`, `tip` and `crosshair`.
- **Logos:** ESPN PNGs at about 160 px, downloaded once with the standard library's `urllib`. Map `LA` to `lar` and `WAS` to `wsh`.
- **Absolute `og:image` origin:** use `VERCEL_PROJECT_PRODUCTION_URL`, falling back to `SITE_ORIGIN`, then `http://localhost:4173`.
- **Avoid:**
  - `@vercel/og` and `sharp`
  - a second chart library
  - `team_logo_wikipedia` (its links return HTTP 400)
  - logos or the NFL shield as site branding
  - FiveThirtyEight's fonts or marks
  - a catch-all rewrite, which would hide the share pages

### Features

- **Must have:**
  - Deploy, a "data through" freshness stamp and site-level preview tags.
  - Share URLs for each team and each callout, with a card showing one claim, one supporting number, the logo, the site name and a date.
  - Logos stored in the repo, with the color-chip fallback.
  - Mobile layout, accessible chart encodings, source footers and a "not affiliated with the NFL" disclaimer.
  - The 2021+ win totals (display-only) and the draft-forfeit audit.
- **Should have:**
  - The FiveThirtyEight-inspired redesign.
  - An offense-vs-defense EPA scatter with logos and tier diagonals.
  - A "record vs evidence" scatter. Don't label teams "lucky" or "unlucky": v1 found the luck factor carries a weight of about zero.
  - The v2 pre-registration.
- **Defer:**
  - An expectations dumbbell chart.
  - Web Share and download buttons.
  - Share cards for the records page.
  - SvelteKit or history-mode routing.
  - Small-multiple charts.
  - Era-accurate logo art.
  - The v2 model itself, to be evaluated around February 2028.

### Architecture

- `write_export` owns `web/public/data/` and deletes anything it didn't write. New JSON has to be added as keys in the `build_export` `files` dict.
- Static assets go in `web/public/logos/`. Build-generated assets go in `dist/og` and `dist/s`, written by a post-build script.
- New and changed parts:
  - **Pre-registration:** `PREREGISTRATION_V2.md` plus new constants in `paths.py`.
  - **Win totals:** `pipeline/inputs/win_totals_2021plus.csv` read by a new `wintotals.py`, with a validator: 32 teams per season, totals summing to about 272, canonical team codes. A guard ensures `vegas_expectations` never reads anything after 2020.
  - **Export additions:**
    - `epa/{season}.json`, one row per game in a column layout, aggregated weighted by plays in `lib/epa.ts`.
    - Win totals on the team files.
    - Conference and division in `meta`.
  - **Logo download:** `fgs logos`, a one-shot command kept out of `refresh`.
  - **Share pages:** `web/scripts/share.mjs`, `og-template.mjs` and `lib/share.ts`, all using one shared rule for building URL slugs.
  - **Web:**
    - `TeamLogo`, which falls back to `TeamChip`.
    - `plotTheme.ts` for the shared chart theme.
    - `ExplorePage` at `#/explore`, with `EpaScatter` and `ScoreVsRecordScatter`.
    - `app.css` restyled through its existing tokens.
- The EPA numbers drop garbage-time plays and aren't adjusted for opponent strength, so say that on the chart. Reuse the filters in `efficiency.py`. Show defense with the axis inverted rather than negating the data.

### Critical Pitfalls

1. **A contaminated v2 holdout.**
   - Count holdout games by kickoff after the v2 freeze commit, which must come after the pre-registration commit.
   - Development uses data from 2025 and earlier; 2022–2025 becomes training data.
   - Fix the verdict wording and the expected statistical power in advance, and list what would void the holdout.
2. **Frozen-score drift.**
   - Keep the golden test and the separate display-only module.
   - Add citations to forfeits as comments only, which the fingerprint ignores.
   - Keep the redesign web-only and don't re-pull play-by-play.
   - If a forfeit really is wrong, rerun `fgs evidence` deliberately.
3. **Hash routes, stale previews and dead links.**
   - Static share pages that redirect with JavaScript only.
   - `og:url` points at the share page itself, and `og:image` is an absolute URL.
   - Season and week in every path and filename, and a date stamp on every card.
   - Test on the production domain, because preview deployments sit behind Vercel's login protection.
4. **Logos.**
   - Store them in the repo, keep the chip fallback, add the footer disclaimer and a switch to turn logos off.
   - Use era names: Oakland, San Diego, St. Louis, and "Washington" before 2020.
   - Never show HOU before 2002.
5. **Card rendering.**
   - Satori needs TTF or WOFF fonts.
   - Emoji need Twemoji or have to be removed; test glyphs across all 7 mood bands and with curly apostrophes.
   - HTML-escape every field written into a share page.
6. **Hand-entered data.**
   - Win totals: run them through the validator and record whether each line is the preseason or closing number, with a source URL per row.
   - Forfeits: two independent citations each.

## Implications for Roadmap

1. **v2 Pre-registration** comes first: losing holdout data can't be undone, and the work is docs only. The free-agency input gets a weight of 0 if it can't be built from `load_contracts` without leaking future data.
2. **Deploy:**
   - Vercel project with root `web`, Node 24.x and `.nvmrc`.
   - An ignored-build step scoped to `web/`.
   - No long cache lifetime on `/data/*`.
   - The freshness stamp, site preview tags and the disclaimer.
3. **Pipeline data:**
   - The golden test lands first.
   - Forfeits, win totals with the validator and guard, the EPA export, conference and division fields, and `fgs logos`.
   - All of it goes in one phase so `fgs evidence` reruns at most once.
4. **Redesign foundation and team identity:**
   - Tokens, fonts and `plotTheme`.
   - `TeamLogo` across the 6 places that show a team chip, plus era names.
   - The restyled pages.
   - Keep the playful mood labels, and don't touch `mood.py`.
5. **Explore charts:** the `#/explore` page with the EPA scatter and the record-vs-evidence scatter, plus the team page's win totals, labeled "Vegas preseason (display only)" vs "model preseason (used in score)".
6. **Share cards and share pages**, which depend on the final design, the production origin and the local logos. Launch verification goes here: the Facebook Sharing Debugger, LinkedIn Post Inspector, opengraph.xyz, and real pastes into Slack, iMessage and X.

Phases 1–3 are independent of one another. Phase 4 comes before phases 5 and 6, and phase 2 comes before the share testing in phase 6.

### Research Flags

- **Phase 6:** whether crawlers follow the share pages' JavaScript redirect, the emoji strategy, and whether `VERCEL_PROJECT_PRODUCTION_URL` is available during the build. Pin the exact share-path scheme and give each callout a stable ID, built from its season, week, franchise and type.
- **Phase 3:**
  - The 2004 Raiders round-2 forfeit may actually be a trade.
  - DEN 2001 R3 and BAL 2008 R5 may be missing from the table.
  - The 2021+ win totals have to be entered by hand, because covers.com only loads in a browser.
- **Phase 1:** whether the free-agency input is feasible at all, given that the contracts data has no signing dates.

## Confidence Assessment

| Area | Confidence | Notes |
|---|---|---|
| Stack | HIGH | Live registry versions checked, and a satori + resvg card rendered end to end. |
| Features | MEDIUM | What data exists is HIGH; the FiveThirtyEight style is reconstructed from secondary sources. |
| Architecture | HIGH | Read from the code. |
| Pitfalls | HIGH / MEDIUM | Repo-specific pitfalls are HIGH; a few external ones are LOW. |

---
*Research completed: 2026-11-11. Ready for roadmap: yes.*

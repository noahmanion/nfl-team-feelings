# Pitfalls Research

**Domain:** v2.0 "Public Site". Adding a public deploy, share cards, logos, a redesign, exploratory EPA charts, data loose ends, and a v2 pre-registration to an existing frozen-model NFL static site (Python → static JSON → Vite/Svelte/Plot hash-routed SPA).
**Researched:** 2026-11-11
**Confidence:** HIGH for repo-specific findings (verified against the code and by live HTTP probes). MEDIUM for Vercel and social-crawler behavior (official docs plus multiple sources). LOW where noted.

Phase names below are by topic, since roadmap numbering doesn't exist yet: **Deploy**, **Team Identity (logos/names)**, **Redesign**, **Share Cards (OG)**, **EPA Charts**, **Data Loose Ends**, **v2 Pre-registration**.

---

## Critical Pitfalls

### Pitfall 1: The nflverse Wikipedia logo URLs are already broken (HTTP 400)

**What goes wrong:**
`load_teams()` (cached at `pipeline/data/cache/teams.parquet`) gives `team_logo_wikipedia` URLs like `.../179px-Arizona_Cardinals_logo.svg.png` and `.../100px-...`. **Probed live on 2026-11-11, both returned HTTP 400.** Since early 2026, Wikimedia has rejected hotlinked thumbnails at non-standard widths. The only allowed widths are 20/40/60/120/250/330/500/960/1280/1920/3840. The rate limit was re-enabled on 2026-02-11 (Phabricator T402792). If you build on these URLs you get 32 broken images, and the failure may come and go.

**Why it happens:**
The PROJECT.md target feature says "nflverse `load_teams` logo URLs". You naturally grab the first logo column. The URLs look legitimate and probably worked when nflverse generated them.

**How to avoid:**
- Don't hotlink logos at runtime at all. Download once in the pipeline (`fgs logos` or part of export), resize to 2 sizes (e.g. 64 px and 256 px; PNG or WebP), and write them to `web/public/logos/{FRANCHISE}.png`. That's about 32 × 2 small files.
- Source priority for that one-time download: `team_logo_espn` (`a.espncdn.com/i/teamlogos/nfl/500/*.png`, probed 200 with `access-control-allow-origin: *`), then `team_logo_squared` from `raw.githubusercontent.com/nflverse/nflverse-pbp` (probed 200, CORS `*`). Note that the `github.com/.../raw/...` form 302-redirects and has an empty ACAO, so use the `raw.githubusercontent.com` form.
- Keep the existing team-color chip as the fallback (`onerror` swaps to chip plus abbreviation). The "graceful fallback" requirement is then cheap.

**Warning signs:** Broken-image icons in dev. HTTP 400/429 from `upload.wikimedia.org` in the network tab. Logos that work at one size and fail at another.

**Phase to address:** Team Identity.

---

### Pitfall 2: Hash routes can't carry per-page Open Graph tags

**What goes wrong:**
The router is pure hash (`#/team/KC/2026/10`). The fragment is never sent to the server, and social scrapers (Facebook, X, Slack, iMessage, Discord) don't run JS. Every shared link, whatever the hash, unfurls with whatever is in the static `index.html`. Today that's `<title>Feel-Good Score</title>` and no OG tags at all. Changing `<meta>` from Svelte at runtime does nothing for crawlers.

**Why it happens:**
OG tags "work" in the browser devtools after client-side updates, so the bug only shows up in a real unfurl.

**How to avoid:**
- Generate **real path-based share stubs** as static files: `web/public/s/team/KC/2026/10/index.html` (and `/s/callout/<id>/index.html`). Each one holds its own `og:title`, `og:description`, `og:image`, `og:url` (pointing at **itself**), and `twitter:card=summary_large_image`, plus a **JS-only** redirect: `location.replace('/#/team/KC/2026/10')` and a visible fallback link.
- **Don't use `<meta http-equiv="refresh">`** for the redirect. Some scrapers (Facebook in particular, MEDIUM-LOW confidence) follow meta refresh and would land on the root page's tags.
- **Don't set `og:url` to the hash URL or the root.** Facebook consolidates on `og:url`, strips the fragment, and shows the home card.
- The "Copy link" / share button must copy the `/s/...` URL, not `location.href`. `copyLink.ts` exists today; that's where the change goes.
- Leave hash routing for the app itself. Moving to history routing plus SvelteKit prerendering is a bigger change than the stub approach needs.

**Warning signs:** Every link previews identically. Debuggers (Facebook Sharing Debugger, opengraph.xyz) show the root title for team URLs.

**Phase to address:** Share Cards (OG).

---

### Pitfall 3: Social caches serve stale weekly cards, and old share links 404 after the next deploy

**What goes wrong:**
(a) Scrapers cache per URL. Facebook keeps a card for roughly 7–30 days and X for roughly 1–7 days. Neither is officially documented (LOW-MEDIUM). If a "latest" URL like `/s/team/KC/` or a fixed image path like `/og/KC.png` is reused while its content changes weekly, it shows last week's score with no way to know.
(b) Vercel deployments are atomic, full replacements. If the weekly refresh only regenerates *this week's* share stubs and cards, every previously shared link 404s on the next deploy.

**Why it happens:**
The weekly-refresh mental model ("overwrite with latest") is right for the app's JSON. It's wrong for shared artifacts, which are permanent public URLs.

**How to avoid:**
- Make share URLs **snapshot-addressed and immutable**: `/s/team/{T}/{season}/{week}/` with the image at `/og/{season}/{week}/{T}.png`. A share then represents a moment, so caching it is *correct*.
- Every card prints its "as of 2026 · Week 10" stamp so a stale preview is still honest.
- Stubs and cards are **cumulative**. Either commit them, or regenerate them deterministically for every (season, week) since launch on each export. Never delete old ones. Add a check that every stub URL from the previous deploy still exists. A simple manifest diff is enough.
- Don't pre-generate cards for all of history. 32 teams × ~600 historical weeks ≈ 19k PNGs at 50–100 KB is about 1–2 GB, which bloats the repo and the build. Generate from the launch week forward, plus the callouts.

**Warning signs:** The preview score disagrees with the live page. Card count grows linearly with no pruning plan, or old `/s/` links return 404.

**Phase to address:** Share Cards (OG).

---

### Pitfall 4: Display-only 2021+ win totals silently change the frozen score

**What goes wrong:**
`expectation.py` reads `win_totals.csv` through `load_win_totals()`, and `vegas_expectations()` normalizes *whatever rows are present*. If the hand-entered 2021+ lines get appended to that cached CSV, or loaded through the same function, `vs_exp` for 2021–2026 switches from model-sourced to Vegas-sourced. That changes the shipped composite for the 2022–25 holdout years and makes `HOLDOUT_RESULT.*` irreproducible. That breaks the "weights frozen forever" contract without touching `weights.yaml`.

There are two more traps:
- `pipeline/.gitignore` ignores `data/`. A hand-entered file placed in `pipeline/data/...` **won't be committed** and is lost or unreproducible.
- `expectation.py` is listed in `fingerprint.CODE_FILES`. *Any* edit to that module, even a display-only helper, changes `code_fingerprint`, and the export then refuses to ship the callout-evidence line.

**Why it happens:**
"Win totals" already has a loader and a code path, so reusing it feels natural.

**How to avoid:**
- Put the manual data in a new committed path, e.g. `pipeline/manual/win_totals_2021plus.csv`, with columns `season, team, line, over_odds, under_odds, source, source_url, retrieved_on, line_type`. Load it from a **new** module (e.g. `display_extras.py`) that is not in `CODE_FILES` and that `features`, `score`, or `expectation` never import.
- Export it into a separate JSON field or file (`vegas_display`) that the score never reads.
- Add a **golden test**: hash the composite (and percentile) for every snapshot with season ≤ 2025 and assert it matches the value recorded at v1.0. Run it in every v2.0 phase that touches the pipeline. This one test covers Pitfalls 4, 9, 11, and 12.
- Extend the existing `test_leakage` firewall so `fgs.features`, `score`, and `expectation` can't import the display module.

**Warning signs:** Holdout or Spearman numbers shift on re-run. The evidence line disappears from the site after an "unrelated" change. `git status` stays clean after hand-entering data, meaning the file was ignored.

**Phase to address:** Data Loose Ends. The golden test should go in the *first* pipeline-touching phase.

---

### Pitfall 5: The 2026 season is not "fresh". The v2 holdout is contaminated before it starts.

**What goes wrong:**
As of 2026-11-11, about 10 weeks of 2026 have been played, scored by v1, published, and looked at. The v2 model (good-loss luck, free agency, win totals in the score) isn't built this milestone, so it gets designed and fitted *later*, while more 2026 games are watched. Any 2026 snapshot whose N=8 target window includes games played before the v2 model is frozen is not out-of-sample. Ideas like "good-loss luck" may themselves be inspired by 2026 games already seen (garden of forking paths). Pre-registering "holdout = 2026–2027" today and evaluating all of 2026 later would be a quiet version of the leak that v1's pre-registration was built to prevent.

**Why it happens:**
"Holdout = seasons after training" is how v1 was framed, and v1's holdout (2022–25) really was untouched. The calendar is different this time.

**How to avoid:**
- Define the holdout by **time relative to the v2 freeze commit**, not by season label. A snapshot is eligible only if **every game in its target window** kicks off after the commit time of the v2 frozen weights, *and* that commit descends from the pre-registration commit.
- State the consequence honestly up front. Unless v2 freezes before roughly week 12 of 2026, which conflicts with "no model changes this milestone", **the primary holdout is the full 2027 season, and late 2026 is at most a secondary or diagnostic slice.** Pre-register that.
- Pre-register a **development data ceiling**: all v2 feature design, fitting, alpha selection, and sanity checking uses seasons ≤ 2025. Add a guard like v1's: the `fgs` v2 commands refuse to compute any metric on season ≥ 2026 until the holdout command runs.
- Pre-register the **comparators**: v2 vs plain Elo, *and* v2 vs the frozen v1 composite, on the same rows with paired bootstrap. Also state explicitly that 2022–25 is now **training data** for v2, so it's no longer a holdout. Any "v2 beats v1 on 2022–25" is in-sample.
- Pre-register **power**. v1 measured +0.004 Spearman over 4 seasons with a CI that included 0. One season (2027) can only detect much larger effects. Fix the verdict wording now (yes / slight / no, as in v1 §8), and expect "slight" or "no".
- Pre-register **what voids the holdout**: any change to v2 feature definitions, fit procedure, or target after the freeze commit. Also say how nflverse retroactive data revisions are handled; recommend pinning the evaluation data snapshot by hash.
- Pre-register **rule-change handling** for 2027. An 18-game schedule or other format changes have been floated (LOW confidence on timing). Say now how `season_config` and the target treat them.
- Hand-entering the **2026 preseason** win total is legitimate, since it's pre-season information. Entering a *current* or in-season adjusted 2026 futures line by mistake is not (see Pitfall 8).

**Warning signs:** The pre-registration says "2026–2027" with no time-of-freeze clause. Any notebook or plot of v2 features on 2026 data. The v2 weights commit isn't a descendant of the pre-registration commit.

**Phase to address:** v2 Pre-registration. It's documentation-only this milestone, but it must include the guards spec.

---

### Pitfall 6: Anachronistic logos and names for relocated and renamed franchises

**What goes wrong:**
`franchises.RAW_TO_FRANCHISE` collapses `OAK→LV`, `SD→LAC`, `STL→LA` at ingest, so the exported data has no era identity. nflverse's own `OAK`, `SD`, and `STL` rows (verified in the cache) point to the **current** LV, LAC, and LAR logo URLs. Showing the "2005 Raiders" with a Las Vegas logo, or "St. Louis" history under an LA Rams logo, looks wrong to exactly the fans the site is for. Relocation is also only part of the problem. Washington changed name *and* logo (Redskins to Football Team in 2020–21 to Commanders in 2022+). Many franchises redesigned logos in-era: Rams and Chargers 2020, Jaguars 2013, Bucs 2014, Bills 2011, Lions 2009/2017, Falcons 2003, Seahawks 2002, Cardinals 2005, and others. Also, HOU didn't exist in 1999–2001, and 1999–2001 had 31 teams.

**Why it happens:**
"Historical logos" sounds like 3 extra images. It's really a per-season asset table for most of the league.

**How to avoid:**
- Decide explicitly, and recommend: **one current franchise logo everywhere, plus an era-correct display name and abbreviation**, e.g. "San Diego Chargers (now LAC)", derived from a small `season → name` table: OAK ≤2019, SD ≤2016, STL ≤2015, Washington eras. Write this decision on the methodology page. Don't chase era-accurate logo art.
- For Washington's pre-2020 seasons, display "Washington" rather than the former name. That's the standard practice of most outlets now, and it avoids putting a slur on a public site.
- Never render HOU for seasons before 2002. The data already can't produce it, but the logo grid and legends should respect it too.

**Warning signs:** A Las Vegas logo next to "2002 AFC champion". The records page shows a "LV" abbreviation for 1999–2019 rows.

**Phase to address:** Team Identity.

---

## Moderate Pitfalls

### Pitfall 7: Vercel project config for a subdirectory app

**What goes wrong / how to avoid:**
- **Root Directory must be `web`.** The git toplevel is `feel-good-scorew/`, which is the GitHub repo. With the root left at `/`, Vercel finds no `package.json` and fails, or detects the wrong framework. Framework preset "Vite", build `npm run build`, output `dist`. Commit `package-lock.json` (it exists) so `npm ci` is reproducible.
- **Node version floats.** `engines: ">=22.12"` resolves to the **latest** Vercel major, which is 26.x today per Vercel's own mapping table (`>=22.0.0` → latest 26.x). Pin `"engines": {"node": "24.x"}` (or `22.x`) so a future Node major can't break the build without notice. Locally, nvm defaults to Node 20, which Vercel deprecated on 2026-10-01 and Vite 8 only barely supports. Add `web/.nvmrc` with `24`.
- **Don't run the Python pipeline on Vercel.** The data is committed in `web/public/data`. The build is `vite build` only, plus any Node-based card generation if you choose build-time cards.
- **Ignored Build Step.** Every push to the repo, including pipeline-only commits, triggers a web build. Set an ignored-build command such as `git diff --quiet HEAD^ HEAD -- .` (scoped to `web/`). Hobby has per-day deployment limits.
- **Preview deployments are behind Vercel Authentication by default** (Deployment Protection, MEDIUM confidence). Scrapers can't fetch OG tags or images from preview URLs, so OG testing on previews "fails" for the wrong reason. Test OG on the production domain, or temporarily allow a protection bypass.
- **Absolute `og:image` URLs need the production origin at generation time.** `VERCEL_URL` is the per-deployment (protected) host. Use a hard-coded `SITE_URL`, or `VERCEL_PROJECT_PRODUCTION_URL` in the Node build script. Vite only exposes `VITE_*` vars to client code.
- **Hobby is non-commercial.** No ads or affiliate sportsbook links. That matters here because of the Vegas lines.

**Phase to address:** Deploy.

---

### Pitfall 8: Hand-entered 2021+ win totals: wrong line, wrong scale, typos

**What goes wrong:** You enter in-season or current futures lines instead of preseason closing lines, or mix opening and closing lines across years. 2021+ seasons have 17 games, so lines are around 8.5 rather than 8.0, and naive comparisons to the 2003–2020 file mislead. Team codes can drift (LV/LAC/LA vs OAK/SD/STL, WAS name changes). A single typo goes unnoticed because nothing consumes the data predictively. Sportsoddshistory now redirects to covers.com and returns 503 to automated fetches, so entry is manual by design.

**How to avoid:** Record `line_type` (preseason close) and `source_url` per row. Add a validator: exactly 32 rows per season, lines in [3.5, 13.5] with a .5 step, franchise codes in `CANONICAL`, and **the season sum ≈ 32 × 17/2 = 272 (±~8)**, since books' totals roughly conserve wins. Cross-check 2–3 teams per season against a second source (nfelo win-totals page, LOW-MEDIUM). Display the line next to the *model* preseason expectation with explicit labels, because for 2021+ the score uses the model number, not Vegas. Otherwise users assume the score reacts to the Vegas line shown.

**Phase to address:** Data Loose Ends.

---

### Pitfall 9: "Verifying" draft forfeits by memory again, and tripping the fingerprint guard

**What goes wrong:** The 18 `draft.FORFEITS` entries were entered from memory. Re-checking them from memory (including Claude's) repeats the mistake. Candidates that *may* be missing, from LOW-confidence recall that needs checking, not trusting: Denver's 2001 3rd-round pick (salary-cap violations) and Baltimore's 2008 5th (2007 supplemental pick, Jared Gaither). Also, `draft.py` is in `fingerprint.CODE_FILES`, so editing `FORFEITS` changes `code_fingerprint`, and the export then drops the callout-evidence line until `fgs evidence` is re-run. That's correct behavior, but it's surprising mid-phase.

**How to avoid:** For each (year, round), require **two independent citations**: PFR's draft page for that year showing the round short or the slot gap, plus a contemporaneous news source for the penalty. Store the citation in a comment or a sidecar file. Use the pick data itself as the third check: the round's count against teams plus comp picks. Comp picks only exist in rounds 3–7 and are appended at the end, so a round count alone can mislead there. Note that the draft data uses PFR codes (`SDG`, `NOR`, `GNB`, `KAN`), which are mapped elsewhere. Since the draft reaction is display-only, confirm the composite golden test (Pitfall 4) still passes, then re-run `fgs evidence` deliberately and commit the new fingerprints.

**Phase to address:** Data Loose Ends.

---

### Pitfall 10: OG image rendering: emoji, fonts, and remote images

**What goes wrong:** Mood labels contain emoji (🕶️ 🔄 📋 🔥 😏 🎽 🎉) and curly apostrophes ("It’s fine."). Satori, behind `@vercel/og`, supports **TTF/OTF/WOFF only, not WOFF2**, and needs an explicit emoji loader (e.g. Twemoji graphemes). Pillow has no practical color-emoji support. resvg doesn't use system color-emoji fonts reliably. So cards render tofu boxes or blanks. Remote logo fetches during generation inherit Pitfall 1's breakage. Facebook and X don't accept SVG `og:image`.

**How to avoid:** Generate PNG cards at 1200×630 and keep them under about 300 KB, which suits WhatsApp; X's limit is 5 MB. Embed fonts as TTF or WOFF files that ship with the repo. Use self-hosted logos from `web/public/logos/`. Either render emoji through Twemoji assets or leave the emoji off the card. Add a check that renders every mood band's label once and fails on missing glyphs.

**Phase to address:** Share Cards (OG).

---

### Pitfall 11: A redesign that edits pipeline-owned copy or tokens trips the freeze guards

**What goes wrong:** Mood labels and emoji live in `pipeline/src/fgs/mood.py`, and `mood.py` is in `CODE_FILES`. Changing copy as part of the "editorial redesign" changes the code fingerprint and silently drops the evidence line. If the redesign reworks band thresholds (`min: 0/5/20/...`), the *product* changes, not just the style.

**How to avoid:** The redesign stays in `web/` (CSS tokens in `app.css`, components). Any mood copy change is a deliberate pipeline task with `fgs evidence` re-run. Thresholds don't change in v2.0.

**Phase to address:** Redesign.

---

### Pitfall 12: The EPA scatter re-pulls pbp and shifts frozen history, or overclaims

**What goes wrong:**
- Adding columns to the slim pbp snapshot for new charts forces a re-download. nflverse periodically revises historical EPA (EP model updates), so `epa_traj` and `qb_trend` for 1999–2025 shift and the "frozen" scores move.
- Defensive EPA axes get the wrong sign (lower is better, so invert or label "EPA allowed").
- The chart's garbage-time and play filters differ from `efficiency.py`, so the scatter disagrees with the factor bars on the same page.
- Early-season points (2–3 games) get plotted with the same visual weight as 17-game samples.
- An exploratory scatter implies EPA drives the score more than the backtested weights say. That contradicts the "honest" core value.

**How to avoid:** Aggregate chart data in the pipeline from the **existing** slim pbp with the **same filter functions** as `efficiency.py`. Never refetch history for chart features; if you must, gate it behind the golden test. Invert or label defensive axes. Show games-played (size or opacity) and an early-season caveat. Label the chart "exploratory, not an input weight" and link to methodology.

**Phase to address:** EPA Charts.

---

### Pitfall 13: Imitating FiveThirtyEight too closely

**What goes wrong:** You copy 538's name, fox mark, signature chart-header styling, or its typefaces. 538 used commercial fonts (Atlas Grotesk and Decima Mono, from training knowledge, MEDIUM). Self-hosting those without a license is a font-license violation, and the full "538 look" plus "538 Elo" language reads as trade-dress borrowing from a brand ABC/Disney still owns after the 2025 shutdown.

**How to avoid:** Borrow *principles*: a grey grid, direct labeling, restrained color, annotation-first charts, and a monospace for numbers. Use OFL fonts (e.g. IBM Plex Sans/Mono, Source Serif 4, or Inter), self-hosted via `@fontsource` (which ships WOFF too, for card generation). Don't use the 538 name in branding or titles. Credit "Elo methodology after FiveThirtyEight" in methodology only.

**Phase to address:** Redesign.

---

### Pitfall 14: Trademark and redistribution of NFL logos

**What goes wrong:** NFL and club logos are trademarks of NFL Properties. Committing them to a **public** GitHub repo and stamping them on share cards is redistribution as well as display. The risk for a non-commercial fan site is low but not zero (LOW confidence, not legal advice). nflverse itself redistributes logos on GitHub, which is the practical precedent.

**How to avoid:** Use logos only nominatively (identifying teams), unmodified, never in the site's own brand mark or favicon. Add a footer line: "Not affiliated with the NFL or any team. Logos are trademarks of their owners." Keep a one-switch fallback (`LOGOS=off` → color chips) so a takedown is a config flip, not a redesign.

**Phase to address:** Team Identity.

---

## Minor Pitfalls

- **Logo legibility on dark backgrounds.** The site has no dark mode today, but the redesign might add one, or cards may use dark backgrounds. Raiders (black/silver), Saints, Bears, Patriots, and Titans navy logos vanish on dark. Put logos on a light disc or chip, or skip dark mode in v2.0. Some team primary colors (multiple navies) are near-identical in highlight-one-of-32 charts; use team color plus the logo or label, never color alone.
- **Plot `image` mark performance and CORS.** 32–600 logo images per chart is fine. One per game for thousands of points is not, so use dots and highlight with logos only on the selection. Same-origin self-hosted logos avoid needing `crossOrigin`. If you ever export a chart to canvas or PNG, cross-origin images without `crossOrigin: "anonymous"` taint the canvas.
- **Cache headers.** Vercel caches static files on its CDN until the next deploy, and invalidation is automatic per deployment. Don't add a `vercel.json` rule giving `/data/*` a long browser `max-age`, or users see last week's scores after a refresh. Only Vite's hashed `/assets/*` should be long-lived (Vercel handles that).
- **Version skew in open tabs.** A tab loaded before a weekly deploy lazily fetches new per-team JSON against the old in-memory `latest.json`/`meta.json`. Put a `data_version` in every file (`meta.generated_at` exists or is easy to add). If it mismatches on fetch, show a "new week, reload" banner.
- **Repo bloat.** Committing re-exported JSON weekly is fine at about 15 MB, *if* export is byte-deterministic (stable key order, fixed rounding). Otherwise all 94 files churn every week. OG PNGs grow linearly too (Pitfall 3). Budget for it or keep cards out of git and generate them at build time.
- **Emoji and copy in `<title>`/`og:description`.** Keep descriptions under about 200 characters, with no raw unescaped quotes, and HTML-escape team and callout text in generated stubs.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hotlink logo URLs from `load_teams` | Zero pipeline work | Broken today (Wikimedia 400), fragile (ESPN path changes), CORS/canvas issues, no fallback | Never for production; OK in a throwaway spike |
| One `/og/KC.png` overwritten weekly | Simple | Stale social previews for weeks; can't be fixed by the site | Never; version by season/week |
| Append 2021+ totals to cached `win_totals.csv` | Reuses loader | Silently changes frozen 2021+ scores and holdout reproducibility | Never |
| Era-accurate logo table for all teams | Historical authenticity | Dozens of assets, license ambiguity, constant upkeep | Only if the user explicitly asks; default to current logo + era name |
| Pre-generate cards for all historical weeks | Every link shareable | About 19k PNGs, 1–2 GB, slow builds | Never; from launch week forward + callouts |
| `engines: ">=22.12"` | No edits | Floats to newest Node major on Vercel | Pin `24.x` |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Vercel | Root Directory left at repo root | Root `web`, preset Vite, output `dist`, ignored-build step scoped to `web/` |
| Vercel previews | Testing OG unfurls on protected preview URLs | Test on the production domain; use the Sharing Debugger / opengraph.xyz |
| Facebook/X/Slack scrapers | Expecting JS-set meta or hash URLs to work | Static per-path stubs with absolute `og:image` and a JS-only redirect |
| Wikimedia | Non-standard thumbnail widths (nflverse's 100px/179px) | Don't hotlink; download once (standard widths if Wikimedia is ever needed) |
| ESPN CDN | Assuming abbreviations match franchise IDs (`wsh`, `lar`) | Use nflverse's URL column as given; download once |
| github.com raw links | `github.com/.../raw/...` → 302 with no CORS | Use `raw.githubusercontent.com` |
| Satori/@vercel/og | WOFF2 fonts, emoji, remote images | TTF/WOFF, Twemoji loader, local logo files |
| covers.com/sportsoddshistory | Scraping (503 to bots) | Manual entry with source URL per row + validator |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Plot image mark per data point | Janky hover, slow first paint | Dots + logos only for highlighted or selected | ~1–2k images |
| Shipping per-play EPA to the browser | Multi-MB downloads | Aggregate to team-week in the pipeline | Any per-play export |
| Unbounded OG card generation | Long builds, repo growth | Snapshot-addressed, launch-forward, cumulative | ~thousands of cards |
| Loading all 28 snapshot files (14 MB) for a cross-season chart | Slow mobile load | Purpose-built small JSON per chart | Already true at 14 MB |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Unescaped team or callout text interpolated into generated HTML stubs | Broken markup or injection in share pages | HTML-escape every interpolated field; tests on a quote-containing string |
| Exposing a Vercel token or bypass secret in client code or a committed `vercel.json` | Account misuse | Keep tokens out of the repo; protection bypass only via dashboard |
| Sportsbook affiliate links next to Vegas lines | Hobby ToS violation; gambling-ad rules | None; display lines as data with a source only |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing the Vegas win total for 2021+ next to a score that doesn't use it | Users think the score reacts to Vegas | Label "Vegas preseason (display only)" vs "model preseason (used in score)" |
| Current LV logo on 2005 Oakland rows | Credibility loss with fans | Current logo + "Oakland Raiders" era name |
| Stale share preview with no date | "This site is wrong" | Week stamp printed on every card |
| Exploratory EPA chart without caveats | Implies causal or predictive claims | "Exploratory" label + sample-size encoding + methodology link |
| The redesign drops the playful mood label for gravitas | Loses product personality | Serious charts, playful label stays (the core concept) |

## "Looks Done But Isn't" Checklist

- [ ] **Deploy:** Production builds with the pinned Node major. A pipeline-only commit doesn't trigger a web build. `/data/latest.json` returns fresh content after a redeploy (`x-vercel-cache` check).
- [ ] **OG:** Facebook Sharing Debugger and one X/Slack unfurl show the *team-specific* card on the production URL, not on a preview.
- [ ] **OG:** The previous deploy's `/s/...` URLs all return 200 after a new deploy (manifest diff).
- [ ] **OG:** All 7 mood emoji and "It’s" render on cards (no tofu).
- [ ] **Logos:** All 32 load with network access to ESPN, Wikimedia, and GitHub *blocked*, meaning they're self-hosted. Fallback chip appears when a logo file is deleted.
- [ ] **Logos:** 1999–2019 Raiders rows read "Oakland", 1999–2016 Chargers "San Diego", 1999–2015 Rams "St. Louis". No HOU before 2002.
- [ ] **Win totals:** The validator passes (32/season, sum ≈ 272, codes canonical). The **golden composite hash for ≤2025 is unchanged**. The file is tracked by git.
- [ ] **Forfeits:** Each entry has two citations. The golden hash is unchanged. `fgs evidence` was re-run and the evidence line is back on the site.
- [ ] **EPA charts:** Uses `efficiency.py` filters. Defensive axis direction labeled. No pbp re-pull, or the golden hash still passes.
- [ ] **Redesign:** No 538 name, marks, or commercial fonts. Font licenses (OFL) committed with the fonts. Contrast passes for text and logos.
- [ ] **Pre-registration:** The holdout eligibility rule is defined by game kickoff after the v2 freeze commit. Dev ceiling ≤2025. Comparators v1 + Elo. Power/verdict wording fixed. Void conditions listed. Committed before any v2 code.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Frozen score drifted (win totals / pbp / forfeits) | MEDIUM | `git bisect` with the golden test; revert the data path; re-run export; confirm the holdout re-run reproduces `HOLDOUT_RESULT.json` (read-only check, no `--force`) |
| Stale or wrong share cards in the wild | LOW–MEDIUM | New snapshot URLs fix new shares; for an existing URL, use Facebook "Scrape Again"; X has no tool, so wait out the cache |
| Old share links 404 | LOW | Restore stubs from git history or regenerate; add the manifest check |
| v2 holdout contaminated (looked at 2026 with v2 features) | HIGH (can't be undone) | Declare the affected slice void in writing, move the primary holdout to 2027, record it in the pre-registration addendum before freezing |
| Logo takedown request | LOW | Flip to the color-chip fallback, remove `public/logos`, redeploy |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Golden ≤2025 composite hash test (guards 4, 9, 11, 12) | First pipeline-touching phase (recommend Data Loose Ends go early, or Deploy) | Test exists and passes in CI-less `uv run pytest` |
| 7 Vercel config / Node / previews | Deploy | Production deploy green; Node pinned; ignored build works |
| 1 Broken Wikimedia URLs, 14 trademark, 6 era names | Team Identity | Offline logo check; era-name spot checks; footer disclaimer |
| 13 538 imitation, 11 pipeline-owned copy | Redesign | No 538 assets/fonts; `mood.py` untouched or `fgs evidence` re-run |
| 2 Hash OG, 3 cache/404, 10 rendering | Share Cards (after Deploy, since it needs the prod origin; after Team Identity, since it needs local logos) | Debugger unfurls; manifest diff; emoji render test |
| 12 EPA re-pull/overclaim | EPA Charts | Golden test; same filter functions; caveat copy |
| 4 Win totals leak, 8 entry errors, 9 forfeits | Data Loose Ends | Validator + golden test + citations |
| 5 Contaminated holdout | v2 Pre-registration | Time-of-freeze eligibility clause, dev ceiling guard spec, committed before any v2 code |

**Ordering implication:** Deploy → Team Identity → Redesign → Share Cards → EPA Charts. Data Loose Ends can run in parallel but should land the golden test first. The v2 Pre-registration should be written **early in the milestone, not last**. Every week that passes is more 2026 seen and less holdout. The clean option is to commit it at the start of v2.0, with the explicit time-of-freeze rule.

## Sources

- Repo inspection (HIGH): `pipeline/src/fgs/{expectation,fingerprint,draft,franchises,mood}.py`, `web/src/lib/router.ts`, `web/package.json`, `web/index.html`, `pipeline/.gitignore`, `pipeline/data/cache/teams.parquet` (OAK/SD/STL rows point to current LV/LAC/LAR logos), `draft_picks.parquet` round counts.
- Live HTTP probes 2026-11-11 (HIGH): nflverse Wikipedia logo URLs → **400**; `a.espncdn.com/i/teamlogos/nfl/500/*.png` → 200, ACAO `*`; `raw.githubusercontent.com/nflverse/nflverse-pbp/.../squared_logos` → 200, ACAO `*`; `github.com/.../raw/...` → 302, empty ACAO.
- Wikimedia thumbnail size limits (MEDIUM-HIGH): https://www.mediawiki.org/wiki/Common_thumbnail_sizes, https://phabricator.wikimedia.org/T402792
- Vercel CDN caching (HIGH): https://vercel.com/docs/caching/cdn-cache
- Vercel Node versions and engines mapping (HIGH): https://vercel.com/docs/functions/runtimes/node-js/node-js-versions; Node 20 deprecation: https://vercel.com/changelog/node-js-20-is-being-deprecated
- Vercel limits (HIGH): https://vercel.com/docs/limits
- Satori font formats, no WOFF2 (HIGH): https://github.com/vercel/satori
- Hash routes and OG crawlers (MEDIUM): https://luo.app/blog/per-route-html-without-ssr, https://nikolina-dev-blog.vercel.app/blog/dynamic-og-tags
- Social cache durations (LOW-MEDIUM, undocumented officially): https://nuxtseo.com/tools/social-share-debugger, https://israynotarray.com/en/misc/2026/05/14/force-refresh-social-og-cache-with-v-1-query-string/
- Observable Plot image mark options (`crossOrigin`, `preserveAspectRatio`): installed `@observablehq/plot` 0.6.19 typings (HIGH).
- `pipeline/PREREGISTRATION.md` (v1 contract, guards, power evidence: +0.004 Spearman, CI includes 0) (HIGH).
- Training knowledge, flagged LOW: possible missing forfeits (DEN 2001 R3, BAL 2008 R5), 538 typefaces, Facebook following meta refresh, 18-game schedule timing, NFL logo trademark posture.

---
*Pitfalls research for: v2.0 Public Site (feel-good-score)*
*Researched: 2026-11-11*

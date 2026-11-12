# Feature Research

**Domain:** Public NFL data-journalism site: team "feel-good" ratings, shareable callouts, exploratory efficiency charts (milestone v2.0 "Public Site")
**Researched:** 2026-11-11
**Confidence:** MEDIUM overall. Data availability and the hash-routing/OG constraint are HIGH, checked against the repo and live nflreadpy. The FiveThirtyEight style description is MEDIUM: there is no official style guide, so it is reconstructed from community themes and memory of the published graphics. Competitor feature lists are MEDIUM/LOW.

Scope: only the NEW v2.0 features. Everything in PROJECT.md "Validated" already exists and is treated as a dependency, not re-researched.

---

## Facts from the codebase that shape these features (verified 2026-11-11)

| Fact | Where | Consequence |
|------|-------|-------------|
| The site uses **hash routing** (`#/team/KC`, `#/board/2026/9`) | `web/src/lib/router.ts` | **Link-preview crawlers never see the fragment and don't run JS.** Every shared `#/...` URL unfurls with the same root `index.html` tags. Per-team or per-callout OG cards need **real paths** (static stub pages). This is the biggest single constraint on feature 2. HIGH |
| Per-game `off_epa`, `def_epa`, `off_plays`, `def_plays`, `off_sr` are already computed (garbage-time filtered), with a `low_confidence` flag for early seasons | `pipeline/src/fgs/pbp.py` | The EPA scatter needs **no new data source**, only a new export. Aggregate play-weighted (Σepa·plays / Σplays), not as a mean of per-game means. HIGH |
| `nfl.load_teams()` has 36 rows (it includes OAK, SD, STL, and both LA and LAR) with `team_logo_espn` (500px PNG on ESPN CDN), `team_logo_squared`, `team_wordmark` (nflverse GitHub), `team_logo_wikipedia`, and `team_color`..`team_color4` | live call | Logos are free and keyed by abbr. Map them through the existing franchise IDs (LV/LAC/LA) and choose current vs era logos deliberately. HIGH |
| Team JSON already carries `primary` / `secondary` colors | `web/public/data/teams/*.json` | Team-color highlighting in a 538-style redesign is already supported by the data. |
| Callouts are structured: `headline`, `detail`, `evidence` (base rate with n), `stat`, `band`, `franchise` | `web/public/data/callouts.json` | Share cards can be **generated straight from callout JSON**. The headline, evidence sentence, and sample size are already written. HIGH |
| Latest rows carry `expectation_source: "model"` for 2026 | `latest.json` | Displayed 2021+ Vegas win totals sit **next to** a model-derived expectation the score actually uses. They must be labeled so nobody thinks Vegas feeds the 2021+ score. |
| `draft.FORFEITS` is a hand table; the DP never invents forfeits | `pipeline/src/fgs/draft.py` | Verifying the 18 entries is a data-audit task with a citation per row, not a feature build. |
| `nfl.load_contracts()` exists (OverTheCap via nflverse, 53.7k rows, `year_signed`, `apy`, `apy_cap_pct`, `team`, nested `contract_history`) | live call | A free-agency input for v2 is **plausible from free data**. It has no signing date, though, and `team` is the current team. The pre-registration must define the FA feature against `contract_history`, and must say what happens if that proves unusable. MEDIUM |

---

## Feature Landscape

### Table Stakes (users expect these; missing = feels broken or amateur once public)

| # | Feature | Why Expected | Complexity | Depends on (existing) | Notes |
|---|---------|--------------|------------|-----------------------|-------|
| T1 | **Public URL on Vercel, static, with HTTPS and a stable domain** | It's the premise of the milestone. | LOW | Vite build, `web/dist` | Root dir `feel-good-scorew/web`. Hash routing needs no rewrites; real-path share stubs (T4) are plain static files, so they need none either. The data is 15 MB of JSON, fine for static hosting, but check that first load fetches only `latest.json` and `meta.json`. |
| T2 | **"Data as of" freshness stamp + weekly refresh story** | A public data site with no visible date looks abandoned or wrong. 538's NFL page led with "Updated [date], after Week N". | LOW | `meta.json`, refresh command | Show "Through Week 9, 2026 · updated Nov 10" in the header and on every share card. |
| T3 | **Site-level OG/Twitter tags on `index.html`** (title, description, a default 1200×630 image, `twitter:card=summary_large_image`, absolute URLs) | Any link to the site posted anywhere should unfurl with a picture. | LOW | none | 1200×630 is the cross-platform default; X accepts it. Image URLs must be absolute. |
| T4 | **Per-team and per-callout share URLs that unfurl correctly** | This is the point of "shareable callouts". If a fan pastes `/#/team/CLE` they get the generic card, which wastes the feature. | MEDIUM | callouts.json, team JSON, router | Pattern: emit static stubs at real paths, e.g. `/s/cle/index.html` and `/s/2026-w9-cle-worried/index.html`. Each carries its own `og:image` and `og:title`, plus a JS/meta-refresh redirect to `/#/team/CLE`. "Share" / "Copy link" in the UI copies the stub URL, not the hash URL (`copyLink.ts` exists and gets updated). **Put the week in the image filename**: Facebook/Slack cache previews for days to weeks, so `cle.png` would show stale moods. |
| T5 | **Share card images (PNG, 1200×630) generated at build/refresh time** | Platforms need a raster image. Fans share pictures, not links. | MEDIUM | callouts, latest rows, logos (T7) | Pre-render about 32 team cards plus the current week's callouts (about 5–10) each refresh. Don't render historical weeks; that's thousands of images for no benefit. The rendering approach (Satori+resvg in Node, Pillow in Python, or Playwright screenshots of a card route) is a STACK decision. All three are static. |
| T6 | **Card content: one claim, one number, one visual, brand + date** | See "What makes a good sports share card" below. | LOW–MEDIUM | callouts | The callout headline *is* the claim ("5-4, but you should feel worried"). |
| T7 | **Team logos with fallback** (board rows, team header, scatter marks, share cards) | Every serious NFL analytics site (rbsdm, nfelo, PFF tiers, 538's table) identifies teams by logo. Text-only boards look like a spreadsheet. | LOW–MEDIUM | franchise map, team colors | **Vendor the logos** into `web/public/logos/` (32 small PNGs or SVGs from `team_logo_squared`/ESPN) rather than hotlinking: no third-party outage, no CORS problems when drawing into a canvas or rendering share cards, and the cards need local files anyway. Fallback: a colored circle with the abbreviation in `team_color`. Fixed square size with `alt` text. Use current logos for the franchise everywhere; era logos (OAK/SD/STL) are a nice-to-have on historical views only. |
| T8 | **Responsive / mobile layout** | Shared links are mostly opened on phones. A 32-row board and a scatter must work at 375px. | MEDIUM | all pages | Scatter on mobile: logos at about 20px, tap for tooltip, maybe hide the tier-line labels. Board: collapse secondary columns. |
| T9 | **Accessible charts and color** | Public site. Team-color-only encoding fails for color-blind users and for teams with similar colors. | LOW–MEDIUM | Plot charts | Pair color with labels or logos. Direct-label highlighted lines. Use `tabular-nums`. Check contrast of gray text. |
| T10 | **Source/notes footer on every chart and on the site** | Data-journalism convention, and nflverse attribution is expected (nflverse data is CC-BY-4.0 / MIT-style; credit nflverse, and the Vegas source for win totals). | LOW | SiteFooter.svelte | "Source: nflverse play-by-play, schedules; preseason win totals via [source]. Notes: …" |
| T11 | **2021+ Vegas preseason win totals shown, clearly labeled display-only** | The "expectations" story ("Vegas said 6.5, they're on pace for 11") is the most intuitive expectation for fans, and 2003–2020 already have it. | LOW (data entry ~192 values) | team page, vs_exp display | Store as `pipeline/data/win_totals_2021plus.csv` with columns `season, team, line, over_odds, under_odds, source, retrieved`. Use the **preseason** line (late August), not the opening line, and record which one. Show it next to the model expectation, labeled "Vegas (not used in score)". |
| T12 | **Verified draft-forfeit table with citations** | Credibility once public. A wrong "forfeited pick" is an easy gotcha. | LOW | `draft.FORFEITS`, draft display | Add `source` (URL) per entry and a check that the forfeit count per (season, round) matches the actual pick count. **Gotcha:** supplemental-draft selections (e.g. Browns 2013 → 2nd in 2013 supp. for Josh Gordon) forfeit the *next* year's pick. Those are real missing slots but not penalties. Decide whether they belong in FORFEITS and label them distinctly. LOW confidence on specific cases; verify each against Pro Football Reference / Wikipedia. |

#### What makes a good sports-data share card (T5/T6 detail)

Synthesized from OG best-practice guides and how The Athletic, 538, and nfelo/rbsdm tweets look when shared. MEDIUM confidence.

1. **Readable as a thumbnail.** Previews often render at about 500px wide, or smaller in chat apps. One headline at ≥48px equivalent, at most about 12 words. No body paragraphs, no axis ticks.
2. **One claim + one proof number.** The claim is the callout headline. The proof is the base rate ("Teams like this won 45% of their next 8 — 631 cases"). The number is what makes it a *data* card and not a meme.
3. **Team identity at a glance.** Logo plus team-color accent bar. Mood label and emoji as the playful layer.
4. **A tiny visual, optional but strong.** A sparkline of the score over the last 16 games, or "record rank vs score rank" as two dots on a 1–32 line. That's the perception gap made visual.
5. **Brand + date + URL in the footer.** "Feel-Good Score · Through Week 9, 2026 · [domain]". Stale-looking cards get dismissed, and an undated card is misleading after the next week.
6. **Safe margins.** Keep text out of the outer ~60px, since X and LinkedIn crop or round corners. Make sure the image is still legible in dark mode.
7. **Honest framing.** Base rate with sample size and years. Never a bare "will win" or a probability without context.

### Differentiators (where this product competes; aligned with "how should you feel")

| # | Feature | Value Proposition | Complexity | Depends on | Notes |
|---|---------|-------------------|------------|------------|-------|
| D1 | **Offense vs defense EPA/play scatter with logos and tier diagonals** | This is the community-standard exploratory chart (rbsdm's tiers, nfelo "EPA Tiers", PFF tiers). Fans recognize it instantly, and it grounds "how you should feel" in efficiency, not record. | MEDIUM | pbp per-game EPA (exists), logos (T7), my-team pin | X = offensive EPA/play; Y = defensive EPA/play **allowed, inverted** so up means better; logos as marks. Add diagonal iso-lines for net EPA (nfelo uses a weighted slope, about 1.6; plain slope 1 is simpler and fine) and league-median crosshairs. Quadrant labels in plain words: "Good at everything", "All offense", "All defense", "Rough". Filters: season, and window **season-to-date vs last 8 games** (ties to the momentum framing). Pinned team highlighted, others at reduced opacity. Tooltip shows EPA/play, rank, success rate, record. |
| D2 | **"Record vs evidence" scatter (perception-gap chart)** | The signature chart for this product. X = record rank (or win%), Y = feel-good score (or rank). Teams far off the diagonal are exactly the callouts. It shows *why* the callouts exist in a single picture. | LOW–MEDIUM | latest rows, callouts | Label the off-diagonal zones "Better than their record" and "Worse than their record". **Frame it as "record vs evidence", not "lucky/unlucky".** v1 found the luck factor ≈0/negative, so "luckiest teams" would claim something the model doesn't support. Annotate the callout teams. |
| D3 | **Expectations chart: preseason Vegas line vs current projected wins** | Uses T11 data. "Picked to go 4-13, now projected 9-8" is the 6-4-team-feels-great story from the Key Decisions table. | LOW–MEDIUM | T11, sim (projected wins) | A dumbbell or arrow chart per team: preseason line → current projected wins (from the existing Monte Carlo). Sort by difference. Display-only. |
| D4 | **538-inspired editorial redesign** | Makes the serious charts feel credible and the playful mood label land as a deliberate contrast. That's the brand. | MEDIUM–HIGH (touches every component) | all existing pages | See the "FiveThirtyEight-inspired style, concretely" section below. |
| D5 | **Standings-style forecast table with logos and shaded probability cells** | This was 538 NFL predictions' core interactive (Elo, change, record, make playoffs %, win division %, win SB %), and fans scan it in seconds. The board is close to this already. | MEDIUM | MoodBoard, sim outputs | Restyle the board as a clean table: logo + name, score, mood, 1-week change, record, playoff %. Shade probability cells with one sequential hue. Sortable columns are optional. |
| D6 | **Callout card in-page "Share" button with a preview** | Lowers friction. The user sees the image they'll post. | LOW | T4, T5 | Use the Web Share API on mobile and copy-link on desktop, plus a "Download image" link to the PNG. |
| D7 | **v2 model pre-registration published on the methodology page** | Almost no hobby sports models pre-register. Publishing "here's what we'll test, judged after Feb 2028" is unusual and credible, and it extends v1's honesty story. | LOW (doc) | PREREGISTRATION.md (v1), methodology page | See "What a good v2 pre-registration contains". |
| D8 | **"Feel-good vs efficiency" small multiples or slope view** (stretch) | Shows teams whose EPA trend and record diverge. | MEDIUM | D1 data | Only after D1 and D2. Probably defer. |

#### FiveThirtyEight-inspired style, concretely (D4 spec input)

There's no official 538 style guide. This is reconstructed from the published NFL predictions interactive, the editorial charts, and community recreations (ggplot `theme_538`, matplotlib `fivethirtyeight` style, `fivethirtyplot`). MEDIUM confidence.

**Page / article frame**
- **Headline + dek.** A bold sans headline, short and declarative ("Which NFL fans should feel better than they do"), with a 1–2 sentence gray dek under it saying what the page shows and the as-of date. Every chart gets its own mini headline (bold, about 18px) and one-line dek (regular, gray) **inside** the chart block, not as a separate H2 far above.
- **Byline/updated line:** "Updated Nov. 10, 2026, after Week 9". Use AP-style dates and spell out the week.
- **Single readable column** (about 640–720px) for prose. Charts and tables can break wider (about 960–1100px).
- **Generous whitespace, few boxes.** Separate sections with thin rules and spacing, not cards with shadows.

**Charts**
- Light gray chart background (the classic 538 graphic used about `#F0F0F0`, white in later years) **or** white with very light gray gridlines. Pick one and use it everywhere.
- **Gridlines:** thin, light gray, usually only on the value axis. No axis lines, no tick marks, no chart border.
- **Axis labels** small and gray, often placed inside the plot at the end of the axis (e.g. the top tick reads "+0.2 EPA/play") instead of a rotated y-axis title.
- **Direct labeling instead of legends.** Label the highlighted line at its end.
- **Highlight one, gray the rest.** In a 32-team chart, every team is light gray and the selected or pinned team gets its team color with a thicker stroke and a label. This works directly with Observable Plot (`stroke` by condition, `Plot.text` at the last point).
- **Annotations** with a thin leader line and short gray text ("Week 6: lost QB"). Sparingly.
- **Footer on every chart:** "SOURCE: NFLVERSE" in small caps or small uppercase, plus "NOTES: …" where needed. The real 538 put its own logo bottom-right. **Put our own wordmark there, never theirs.**
- **Numbers in tabular or monospaced figures.** 538 used a mono face (Decima Mono) for numbers in tables. Use `font-variant-numeric: tabular-nums` or a free mono.

**Tables (the NFL predictions table)**
- Rows: small logo (about 20–24px) + team name, then numeric columns right-aligned.
- **Probability columns as shaded cells**, a sequential single-hue scale, with the value printed in the cell and "<1%" / ">99%" instead of 0 or 100.
- A thin rule between rows, no zebra striping, a sticky header, and an uppercase small gray header row.
- Change columns with ▲/▼ and green/red (or blue/orange for color-blind safety).

**Typography and color**
- 538 used Atlas Grotesk plus Decima Mono, both **commercial**. Use free look-alikes instead, e.g. a neo-grotesk sans (Inter / Public Sans / IBM Plex Sans) and a mono (IBM Plex Mono / JetBrains Mono), self-hosted.
- A restrained palette: near-black text, gray `#666`-ish secondary text, one accent color for the brand, and team colors only for highlights. The playful mood labels and emoji are the deliberate contrast to the sober charts.

**Do not copy:** the name "FiveThirtyEight" or "538", the fox/logo, their exact color tokens as a brand, the commercial fonts, or page layouts pixel for pixel. Use "inspired-by" conventions only. These are generic data-journalism conventions shared by NYT, The Upshot, and the Economist, so adopting them is safe.

#### What exploratory charts NFL analytics sites offer (D1–D3 context)

| Site | Exploratory charts | Relevant to "how should you feel"? |
|------|-------------------|-----------------------------------|
| rbsdm.com (Ben Baldwin / nflverse) | Team tiers (off EPA vs def EPA, logos, diagonal tiers), QB EPA+CPOE composite scatter, team stats tables with filters (week range, garbage time toggle, pass/rush) | **Yes:** the tiers scatter (→ D1). The week-range filter maps to "last N games". QB charts are out of scope. |
| nfelo (nfeloapp.com) | EPA tiers (x off, y def, weighted diagonal slope about 1.6), power ratings table, win totals history, QB rankings | Tiers yes. Win totals history inspires D3. |
| FiveThirtyEight NFL predictions (archived; site shut down 2025) | Standings table with Elo, playoff/division/SB % shaded cells, game-by-game win probabilities, QB-adjusted Elo, "how our predictions work" methodology | Yes: table conventions (D5) and the methodology page tone. |
| The Athletic / PFF | Weekly tier scatters in articles, playoff-odds charts, power rankings with movement arrows | Tiers scatter plus movement arrows (we already have movers). |

LOW–MEDIUM confidence on exact current controls. rbsdm's page couldn't be fetched directly, so its features are described from training knowledge plus secondary references.

### Anti-Features (seem good, cause problems)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Switching to history-mode routing / SvelteKit SSR just for share cards | "Real URLs fix OG." | It rewrites the router and every link, and needs SPA rewrites. All that for about 40 shareable URLs per week. | Static share stubs at `/s/...` that redirect to hash routes (T4). Revisit SvelteKit only if per-page SEO ever matters. |
| Runtime OG generation (`@vercel/og` edge function) | It's the documented Vercel way. | Adds a serverless runtime to a deliberately static site, costs cold starts, and can't render arbitrary historical states any better. The data only changes weekly. | Build-time PNGs, regenerated by the weekly refresh. |
| Share cards for every historical week and team | "Completeness." | Thousands of images, slow builds, a bloated deploy, and nobody shares week 7 of 2004. | Latest week only: 32 team cards + current callouts + a few records-page cards ("saddest fanbase ever"). |
| "Luckiest / unluckiest teams" headline chart | Popular framing on Twitter. | v1's backtest gave the luck factor ≈0 or negative weight, so labeling teams "unlucky, will bounce back" overstates what the model shows. | D2 "record vs evidence" framing with base rates from callouts. |
| User-adjustable scatter axes / build-your-own chart | Feels "exploratory". | Becomes a generic stats explorer (rbsdm does this better) and dilutes the single-score message. | 2–3 opinionated charts (D1–D3) with a couple of filters. |
| Hotlinking ESPN logo URLs at runtime | Zero effort. | A third-party dependency on every page view, possible hotlink blocking, and canvas/OG rendering breaks on cross-origin images. | Vendor the PNGs/SVGs into `web/public/logos/`. |
| Feeding 2021+ Vegas win totals into the live score | "We have the data now." | It would change the frozen v1 model and the methodology claims. | Display-only now. The v2 pre-registration decides whether they enter the v2 score. |
| Copying 538 branding (name, fox, fonts, exact palette) | "Make it look like 538." | Trademark and font licensing problems, and it reads as a knockoff. | Generic data-journalism conventions with our own wordmark. |
| Comments, accounts, email signups, analytics-heavy tracking | "It's public now." | Moderation, privacy, and process the repo explicitly avoids. | At most Vercel Web Analytics (cookieless) if wanted. Optional. |
| Changing the v1 model during this milestone | "While we're here…" | It invalidates the consumed-holdout story and the v2 fresh holdout. | Pre-register v2 only. No model code changes. |

---

## What a good v2 pre-registration contains (D7)

Built from the v1 `pipeline/PREREGISTRATION.md`, which is already strong, and the two-stage predictive-model pre-registration template from Hofman, Chatzimparmpas, Sharma, Watts & Hullman, arXiv 2311.18807 (stage 1 before training, stage 2 before testing). MEDIUM–HIGH confidence on structure. The sports-specific items are reasoned from this project's situation.

**Keep from v1** (sections that worked): status and order of commits, exact model spec, target definition, primary metric + comparator + pass rule, bootstrap plan with seeds, fixed verdict wording for each outcome, secondary metrics marked non-gating, pre-stated diagnostics, known risks, "if it fails" policy, code guards with commit-ancestry checks.

**Add for v2:**

1. **Hypotheses, one per new input, plus the composite.** For example: H1 "good-loss luck (postgame expected-margin or win-prob residual) adds rank signal beyond v1"; H2 "free-agency net value adds offseason/early-season signal"; H3 "Vegas preseason totals in `vs_exp` beat the model-derived expectation". Name **one** primary hypothesis (the v2 composite beats the frozen v1 composite) and treat the per-input ablations as secondary.
2. **Comparators, ordered:** frozen v1 composite (primary comparator, not Elo), plain Elo, Vegas spread (the ceiling for next-game Brier).
3. **Exact feature definitions before any v2 code runs on the holdout.** Formula, data source, columns, as-of rule. For FA: `load_contracts` has no signing date and `team` is the current team, so the definition must say how team-at-signing comes from `contract_history`, and that the input is **dropped (weight 0, documented) if it can't be built leak-free**. Decide that now, not after seeing results.
4. **Data provenance and timing:** win totals must be **preseason** lines with a source and retrieval date. For 2027, record the line before Week 1, with a commit timestamp as proof. Hash the data files.
5. **Holdout definition that confronts 2026 being half-observed.** Today is 2026 Week 10, and v1 is already showing 2026 data, so the author has seen weeks 1–9. Options to pre-commit:
   - (a) holdout = all of 2026 + 2027, with a rule that no v2 development code reads `season >= 2026` rows, and an explicit admission that the ideas were formed while watching 2026; or
   - (b) holdout = 2026 games after the freeze commit + all of 2027 (cleaner, smaller).

   The recommendation is to state the choice and its contamination risk explicitly. Either way, training is 1999–2025 (the consumed 2022–25 holdout becomes legal training data, and that should be said).
6. **Power / expected precision stated up front.** v1 had 4 holdout seasons and a CI including 0. Two seasons will be about √2 noisier. Pre-commit to the "within noise" wording being the likely outcome, and say what *would* be convincing.
7. **Evaluation date and trigger:** run once, after the 2027 season's Super Bowl (about Feb 2028), via a guarded `fgs holdout-v2` command.
8. **Model-selection budget:** how many v2 variants may be tried on training data (with forward-chaining or LOSO CV), and that only the single frozen v2 goes to the holdout.
9. **Deviations log:** an appended section for any unavoidable change (e.g. nflverse schema change), each dated with a reason, made before the evaluation.
10. **What ships during the holdout:** the site keeps showing v1 (frozen). v2 runs shadow-only, so the public score doesn't change mid-test.
11. **Out of scope for this milestone:** the document is written and committed. No v2 feature code beyond what's needed to write precise definitions.

---

## Feature Dependencies

```
Vendored logos (T7)
    ├──required by──> Share card images (T5)
    ├──required by──> EPA scatter marks (D1)
    └──enhances────> Board/table rows (D5), team header

Redesign tokens: fonts, colors, chart theme (D4, partial)
    ├──should precede──> Share card visual design (T5/T6), so cards match the site
    └──should precede──> New charts (D1–D3), built once in the final style

Static share stubs at real paths (T4)
    └──requires──> Share card PNGs (T5) ──requires──> callouts.json + latest rows (exist)
    └──requires──> Known production domain (T1), since og:image must be absolute

Vercel deploy (T1) ──required by──> verifying unfurls (needs a public URL for the FB/X/Slack debuggers)

EPA scatter (D1) ──requires──> new pipeline export of season/last-8 off/def EPA per team-week (data exists in pbp.py)
Record-vs-evidence (D2) ──requires──> latest rows only (exists)
Expectations chart (D3) ──requires──> 2021+ win totals (T11) + sim projected wins (exists)

Draft-forfeit verification (T12): independent (pipeline-only)
v2 pre-registration (D7): independent of the site, but must be committed before any v2 code touches 2026+ data,
    and preferably before the 2027 preseason lines are recorded

Win totals into the live score ──conflicts──> frozen v1 model (display-only resolves it)
History-mode routing ──conflicts──> existing hash router (stubs avoid it)
```

### Dependency Notes
- **T5 requires T7:** card renderers (Satori, Pillow, Playwright) need local image files. Remote ESPN images in a build step are fragile.
- **T4 requires T1:** `og:image` must be an absolute URL on the final domain, and unfurls can only be tested against a public URL.
- **D4 tokens before D1–D3 and T5:** otherwise every new chart and the card template get styled twice.
- **D3 requires T11:** without 2021+ lines the expectations chart is empty for the six most recent seasons.

---

## MVP Definition (for this milestone)

### Launch With (v2.0 must-haves)
- [ ] T1 Vercel deploy + T2 freshness stamp + T3 site OG tags: the site is public and unfurls.
- [ ] T7 vendored logos with fallback: required by cards and scatter.
- [ ] D4 redesign (tokens + chart theme + table restyle): the stated milestone goal.
- [ ] T4 + T5 + T6 share stubs and cards for team pages and current callouts: the stated milestone goal. Without real paths it doesn't work.
- [ ] D1 EPA tiers scatter + D2 record-vs-evidence scatter: the "exploratory charts" goal, both cheap given the existing data.
- [ ] T11 2021+ win totals (display-only) + T12 forfeit verification: the loose ends.
- [ ] D7 v2 pre-registration committed: independent and time-sensitive (2027 preseason lines).
- [ ] T8 mobile + T9 accessibility + T10 source footers: they come with the redesign.

### Add After Validation
- [ ] D3 expectations dumbbell chart, once T11 data is in.
- [ ] D6 Web Share / download-image button.
- [ ] Records-page share cards ("saddest fanbase ever").

### Future Consideration
- [ ] SvelteKit + prerendered real routes (if SEO or per-page meta beyond share stubs is ever wanted).
- [ ] D8 small multiples; era-accurate historical logos.
- [ ] v2 model itself (after holdout evaluation, about Feb 2028).

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| T1–T3 deploy, freshness, site OG | HIGH | LOW | P1 |
| T7 logos | HIGH | LOW | P1 |
| D4 redesign | HIGH | MEDIUM–HIGH | P1 |
| T4–T6 share stubs + cards | HIGH | MEDIUM | P1 |
| D2 record-vs-evidence scatter | HIGH (on-brand) | LOW | P1 |
| D1 EPA tiers scatter | MEDIUM–HIGH | MEDIUM | P1 |
| T11 win totals display | MEDIUM | LOW (manual entry) | P1 |
| T12 forfeit verification | LOW (credibility) | LOW | P1 (loose end) |
| D7 v2 pre-registration | MEDIUM (credibility) | LOW | P1 |
| D5 shaded-probability table | MEDIUM | MEDIUM (part of D4) | P2 |
| D3 expectations chart | MEDIUM | LOW–MEDIUM | P2 |
| D6 share button UX | MEDIUM | LOW | P2 |
| D8 small multiples | LOW | MEDIUM | P3 |

## Competitor Feature Analysis

| Feature | 538 NFL predictions (archived) | rbsdm / nfelo | Our Approach |
|---------|-------------------------------|---------------|--------------|
| Team ranking table | Logo + Elo + change + shaded playoff/SB % cells | nfelo power-ratings table | Mood board restyled as a 538-like table; mood label as the playful column |
| Off/def efficiency | Not a focus (Elo-based) | EPA tiers scatter with logos and diagonals | D1 with season / last-8 toggle and pinned-team highlight |
| Expectations | Preseason Elo-based projections | nfelo win-totals history | D3: Vegas preseason line → current projected wins (display-only) |
| Shareability | Article-level OG images | Charts shared as screenshots on X | Auto-generated per-team and per-callout cards with base-rate evidence |
| Methodology transparency | Long "how our predictions work" article | Blog write-ups | Existing methodology page + published v1 holdout result + v2 pre-registration |

## Sources

- Repo inspection (2026-11-11): `web/src/lib/router.ts`, `web/public/data/{latest,callouts}.json`, `teams/*.json`, `pipeline/src/fgs/{pbp,efficiency,draft}.py`, `pipeline/PREREGISTRATION.md`. HIGH
- Live nflreadpy 0.1.5 calls: `load_teams()` logo/color columns; `load_contracts()` shape/columns; loader list. HIGH
- [nfelo EPA tiers](https://nfeloapp.com/nfl-power-ratings/nfl-epa-tiers): axes (x off EPA, y def EPA inverted), diagonal slope about 1.6. MEDIUM
- [nfelo EPA tiers by team](https://nfeloapp.com/nfl-power-ratings/nfl-epa-tiers-by-team); PFF weekly team-tier reviews (e.g. [week 12, 2023](https://www.pff.com/news/nfl-statistical-review-week-12-team-tiers-dropback-outcomes-2023)). MEDIUM
- rbsdm.com features: training knowledge + secondary reference ([whitecounty.com article](https://whitecounty.com/?p=1200726)). LOW–MEDIUM
- OG sizing: [frontendchecklist og-image-size](https://frontendchecklist.io/rules/seo/og-image-size), [krumzi OG sizes](https://www.krumzi.com/blog/the-optimal-open-graph-image-sizes-to-maximize-link-clicks-on-social-media), [linkpreview complete guide](https://linkpreview-ev5.pages.dev/blog/complete-guide-to-open-graph-tags). MEDIUM
- Fragments/crawlers/caching: [Wikimedia Phabricator T431181](https://phabricator.wikimedia.org/T431181), [Facebook sharing for SPAs (Speaker Deck)](https://speakerdeck.com/sienatime/facebook-sharing-for-single-page-apps?slide=15), [link.boo preview caching](https://link.boo/guides/facebook-link-preview-not-updating), [Dynamic OG tags for SPA on Vercel](https://nikolina-dev-blog.vercel.app/blog/dynamic-og-tags). MEDIUM (consistent across sources; RFC 3986 §3.5 is authoritative on fragments)
- Build-time OG rendering: [Satori + Astro at build time](https://dev.to/morellodev/generating-og-images-at-build-time-with-satori-and-astro-4b4b), [x-satori](https://github.com/zhengqbbb/x-satori). MEDIUM
- 538 style reconstruction: [fivethirtyplot README](https://rdrr.io/github/kiernann/fivethirtyplot/f/README.md), [style_538.R](https://rdrr.io/github/kiernann/fivethirtyplot/src/R/style_538.R), [Trafford Data Lab style post](https://medium.com/@traffordDataLab/developing-a-data-visualisation-style-cd24f88fa59), [matplotlib fivethirtyeight style](https://matplotlib.org/3.2.2/_sources/gallery/style_sheets/fivethirtyeight.rst.txt). MEDIUM (no official guide exists)
- Pre-registration for predictive modeling: [Hofman et al., arXiv 2311.18807](https://arxiv.org/pdf/2311.18807v1.pdf), [Gelman blog discussion](https://statmodeling.stat.columbia.edu/2023/12/06/exploring-pre-registration-for-predictive-modeling/), [OSF Prereg form](https://ftp.fau.de/cran/web/packages/preregr/vignettes/form_OSFprereg_v1.html). MEDIUM–HIGH

---
*Feature research for: NFL feel-good score public site (v2.0)*
*Researched: 2026-11-11*

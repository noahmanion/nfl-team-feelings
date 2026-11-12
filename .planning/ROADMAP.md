# Roadmap: Feel-Good Score

## Milestones

- ✅ **v1.0 Feel-Good Score v1** — Phases 1–8 (shipped 2026-11-11)
- 🚧 **v2.0 Public Site** — Phases 9–14 (in progress)

## Phases

<details>
<summary>✅ v1.0 Feel-Good Score v1 (Phases 1–8) — SHIPPED 2026-11-11</summary>

- [x] Phase 1: Data Foundation & Elo Core (3/3 plans) — completed 2026-11-11
- [x] Phase 2: Elo Mood Board (4/4 plans) — completed 2026-11-11
- [x] Phase 3: Backtest Harness & Additive Score (4/4 plans) — completed 2026-11-11
- [x] Phase 4: Game-Result Factors & Team Deep-Dive (4/4 plans) — completed 2026-11-11
- [x] Phase 5: Efficiency, QB Trend & Season Simulator (5/5 plans) — completed 2026-11-11
- [x] Phase 6: Weight Freeze & Methodology (5/5 plans) — completed 2026-11-11
- [x] Phase 7: Draft-Aware Offseason (4/4 plans) — completed 2026-11-11
- [x] Phase 8: Callouts, Records & My Team (5/5 plans) — completed 2026-11-11

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

### 🚧 v2.0 Public Site (Phases 9–14)

**Milestone goal:** Take the site public. Deploy it, restyle it as FiveThirtyEight-inspired data journalism with team logos, make callouts shareable, add exploratory EPA charts, and close the v1 data loose ends. The frozen v1 model stays untouched, and the v2 model is pre-registered against a fresh 2026–27 holdout.

- [x] **Phase 9: v2 Pre-registration** - Commit the v2 model plan and holdout before any v2 model code or more 2026 weeks are spent (docs only, time-critical) (completed 2026-11-12)
- [x] **Phase 10: Deploy** - The existing site is live on a Vercel production URL with auto-redeploys, a freshness stamp, site-level share tags and a disclaimer (completed 2026-11-12)
- [ ] **Phase 11: Pipeline Data & Guards** - Golden frozen-score test first, then forfeit audit, display-only 2021+ win totals, EPA export and local logos in one pass
- [ ] **Phase 12: Redesign Foundation & Team Identity** - Editorial type system, shared chart theme, restyled pages and logos everywhere, with all v1 behavior intact
- [ ] **Phase 13: Explore Charts & Win Totals Display** - A new Explore page with the EPA and record-vs-evidence scatters, and Vegas win totals on the team page
- [ ] **Phase 14: Share Cards & Launch Verification** - Build-time share images and static share pages, copy-link wired to them, verified on real platforms

## Phase Details

### Phase 9: v2 Pre-registration

**Goal**: The v2 model is pre-registered in writing before any v2 model code exists, so the 2026–27 holdout stays clean
**Depends on**: Nothing (first phase of v2.0; can run in parallel with Phases 10 and 11, but should land first)
**Requirements**: INTEG-02, INTEG-03
**Success Criteria** (what must be TRUE):

  1. `pipeline/PREREGISTRATION_V2.md` exists and is committed, while v1's `PREREGISTRATION.md` is byte-identical and still at exactly one commit (the v1 holdout guard passes)
  2. The document defines MODEL-V2-01 (good-loss luck), MODEL-V2-02 (free agency) and MODEL-V2-03 (Vegas win totals into the score) precisely enough that someone else could build them, along with the development-data ceiling (≤2025), the holdout (games kicking off after the v2 freeze commit, 2027 primary), the comparators (frozen v1 composite and Elo), the metrics, the per-input drop rules and the verdict wording
  3. For each candidate input, the document states whether it can be built from free data without leakage (e.g. whether `load_contracts` has signing dates) and pre-commits to dropping any that can't
  4. The git history shows no v2 model code before the pre-registration commit

**Plans**: 1 plan

Plans:

- [x] 09-01-PLAN.md — Write, self-check and single-commit pipeline/PREREGISTRATION_V2.md, then read-only integrity checks 1–8

### Phase 10: Deploy

**Goal**: Anyone can open the current site at a public Vercel URL, and it stays current on its own
**Depends on**: Nothing (independent of Phases 9 and 11)
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03
**Success Criteria** (what must be TRUE):

  1. A visitor can open the Vercel production URL and use every v1 route (board, team, history, records, methodology), built from `web/` in github.com/noahmanion/nfl-team-feelings with Node pinned to 24.x
  2. Pushing a `web/` or data change to `main` redeploys automatically, and a pipeline-only commit is skipped by the ignored-build step
  3. Every page shows a "data through" freshness stamp and a footer saying it's an unofficial fan project, not affiliated with the NFL, with data from nflverse
  4. Pasting the site URL into a link-preview tool shows the site-wide title, description and share-card tags

**Plans**: 2 plans

Plans:
**Wave 1**

- [x] 10-01-PLAN.md — Repo changes: Node 24 pin, site-origin resolver + Vite plugin, share tags, og-default.png, always-on disclaimer footer

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 10-02-PLAN.md — Orchestrator deploy: push, create Vercel project (root web, Node 24.x), READY prod deploy, ignore step, prod verification, record URL

### Phase 11: Pipeline Data & Guards

**Goal**: The pipeline exports everything v2's new views need (verified forfeits, display-only win totals, EPA, local logos) while frozen v1 scores are provably unchanged
**Depends on**: Nothing (independent of Phases 9 and 10); INTEG-01 lands before any other change in this phase
**Requirements**: INTEG-01, DATA-01, DATA-02, EXPL-01, LOGO-01
**Success Criteria** (what must be TRUE):

  1. A golden test pins a hash of every exported composite score and mood label for seasons ≤2025, it was committed before the phase's other changes, and it still passes at the end of the phase (or the one deliberate `fgs evidence` rerun is documented)
  2. All 24 draft-forfeit entries carry a cited public source and are each confirmed, corrected or removed, and supplemental-draft forfeits are labeled separately from penalties
  3. The 2021–2026 Vegas preseason win totals live in a sourced file under `pipeline/inputs/`, pass the validator (32 teams per season, canonical codes, sane totals), and are read only by a display-only module; a guard shows `vegas_expectations` never reads past 2020
  4. The exported data includes per-team-season offense and defense EPA/play, success rate and play counts, and the web can compute play-weighted season-to-date values for any week
  5. Running the logo command once puts all 32 team logos in `web/public/logos/` (committed), and the site makes no runtime requests to external logo hosts

**Plans**: 5 plans

Plans:
**Wave 1**

- [x] 11-01-PLAN.md — Golden frozen-score test (first commit), forfeit audit + FORFEIT_KIND, one fgs evidence rerun

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 11-02-PLAN.md — Write-once 2021-2025 win totals file, 2026 display file, wintotals.py validator, <=2020 guards, team-file vegas_win_totals

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 11-03-PLAN.md — EPA per team-game export, conf/division + epa_seasons in meta, web loadEpa + seasonToDate

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 11-04-PLAN.md — fgs logos command, 32 committed ESPN logos + manifest, no-hotlink tests

**Wave 5** *(blocked on Wave 4 completion)*

- [ ] 11-05-PLAN.md — Regenerate site data once, golden re-check, full pipeline + web gates

### Phase 12: Redesign Foundation & Team Identity

**Goal**: The whole site reads as clean, editorial data journalism with team logos, and nothing from v1 broke
**Depends on**: Phase 11 (local logos)
**Requirements**: DESIGN-01, DESIGN-02, DESIGN-03, DESIGN-04, LOGO-02, LOGO-03
**Success Criteria** (what must be TRUE):

  1. Text renders in self-hosted Inter and numbers and annotations in IBM Plex Mono with tabular figures, with no FiveThirtyEight name, logo or proprietary fonts anywhere
  2. Every chart shares one theme: bold headline, gray dek, light value-axis gridlines only, direct labels instead of legends, the highlighted team in its color with others in gray, and a SOURCE/NOTES footer
  3. The board, team, history, records and methodology pages use the editorial layout (rule-separated tables, small logos, shaded score cells) in both light and dark mode
  4. Logos appear on board rows, the team page header, records rows and chart marks, fall back to the color chip when a logo fails to load, and relocated franchises show the current logo with the era-correct name (e.g. "San Diego Chargers" in 2010)
  5. Routes, the week scrubber, my-team pin, callouts, copy-link and the 375px mobile layout all still work, and the existing web tests pass

**Plans**: TBD
**UI hint**: yes

### Phase 13: Explore Charts & Win Totals Display

**Goal**: Users can explore team efficiency and see the perception gap at a glance, and compare each team's Vegas expectation to its actual pace
**Depends on**: Phase 11 (EPA export, win totals), Phase 12 (chart theme, logos)
**Requirements**: EXPL-02, EXPL-03, DATA-03
**Success Criteria** (what must be TRUE):

  1. A user can open `#/explore`, pick a season and week, and see an offense-vs-defense EPA/play scatter with team logos as marks
  2. The Explore page shows a "record vs evidence" scatter (win% vs feel-good score) where the perception gap is visible, with no "lucky/unlucky" framing, and clicking any mark opens that team's page
  3. The team page shows the team's preseason Vegas win total next to its actual pace, labeled "not used in score" for seasons where the model expectation drives the score

**Plans**: TBD
**UI hint**: yes

### Phase 14: Share Cards & Launch Verification

**Goal**: A link to any team or current-season callout unfurls as a rich, on-brand preview on real social platforms
**Depends on**: Phase 10 (production origin), Phase 12 (final design, fonts, logos)
**Requirements**: SHARE-01, SHARE-02, SHARE-03
**Success Criteria** (what must be TRUE):

  1. Each build produces 1200×630 share images for all 32 teams and the current season's callouts, rendered in the redesign's fonts, colors and local logos, with every mood-band label and apostrophe rendering correctly
  2. Each share image has a static share page at a real path that includes the season and week, with absolute `og:image` on the production domain, and opening it in a browser lands on the matching hash route
  3. The copy-link buttons on team pages and callouts copy the share-page URL where one exists and fall back to the hash link otherwise
  4. Pasting a team share URL and a callout share URL into Slack, iMessage and X (and the Facebook/LinkedIn debuggers) shows the correct card image and title

**Plans**: TBD
**UI hint**: yes

## Progress

**Execution order:** 9 → 10 → 11 → 12 → 13 → 14 (Phases 9, 10 and 11 are mutually independent; 9 should land first)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Data Foundation & Elo Core | v1.0 | 3/3 | Complete | 2026-11-11 |
| 2. Elo Mood Board | v1.0 | 4/4 | Complete | 2026-11-11 |
| 3. Backtest Harness & Additive Score | v1.0 | 4/4 | Complete | 2026-11-11 |
| 4. Game-Result Factors & Team Deep-Dive | v1.0 | 4/4 | Complete | 2026-11-11 |
| 5. Efficiency, QB Trend & Season Simulator | v1.0 | 5/5 | Complete | 2026-11-11 |
| 6. Weight Freeze & Methodology | v1.0 | 5/5 | Complete | 2026-11-11 |
| 7. Draft-Aware Offseason | v1.0 | 4/4 | Complete | 2026-11-11 |
| 8. Callouts, Records & My Team | v1.0 | 5/5 | Complete | 2026-11-11 |
| 9. v2 Pre-registration | v2.0 | 1/1 | Complete    | 2026-11-12 |
| 10. Deploy | v2.0 | 2/2 | Complete    | 2026-11-12 |
| 11. Pipeline Data & Guards | v2.0 | 4/5 | In Progress|  |
| 12. Redesign Foundation & Team Identity | v2.0 | 0/TBD | Not started | - |
| 13. Explore Charts & Win Totals Display | v2.0 | 0/TBD | Not started | - |
| 14. Share Cards & Launch Verification | v2.0 | 0/TBD | Not started | - |

# Requirements: Feel-Good Score

**Defined:** 2026-11-11
**Milestone:** v2.0 Public Site
**Core Value:** A single, honest, momentum-weighted "feel-good score" per team that is backtested to predict future performance — so "you should feel better than you do" is actually true.

## v2.0 Requirements

### Model Integrity (frozen v1 + v2 pre-registration)

- [x] **INTEG-01**: A golden test pins a hash of every exported composite score and mood label for seasons ≤2025, so any v2.0 change that alters a frozen v1 score fails the test suite
- [x] **INTEG-02**: A new `pipeline/PREREGISTRATION_V2.md` (v1's `PREREGISTRATION.md` untouched) commits, before any v2 model code exists, to: the exact definitions of the candidate inputs (MODEL-V2-01 good-loss luck, MODEL-V2-02 free agency, MODEL-V2-03 Vegas win totals into the score), the development-data ceiling (≤2025), the holdout (games kicking off after the v2 freeze commit, with 2027 primary), the comparators (frozen v1 composite and Elo), the metrics, the per-input drop rules, and the verdict wording decided in advance
- [x] **INTEG-03**: The pre-registration states whether each candidate input can be built without leakage from free data (e.g. whether free-agency data has signing dates), and pre-commits to dropping any that can't

### Deploy

- [x] **DEPLOY-01**: The site is publicly reachable at a Vercel production URL, built from `web/` in the GitHub repo, with Node pinned to 24.x
- [x] **DEPLOY-02**: Pushing to `main` redeploys automatically, and pipeline-only commits don't trigger a web build
- [x] **DEPLOY-03**: The site shows a "data through" freshness stamp, carries site-wide title, description and share-card tags, and has a footer saying it's an unofficial fan project, not affiliated with the NFL, with data from nflverse

### Data Loose Ends

- [x] **DATA-01**: Every entry in the draft-forfeit table (all 24, not only the 18 entered from memory) is checked against a cited public source. Each entry is confirmed, corrected or removed, and supplemental-draft forfeits are labeled separately from penalties
- [x] **DATA-02**: The 2021–2026 Vegas preseason win totals live in a committed, sourced file under `pipeline/inputs/` and are read by a display-only module. They never reach `vs_exp` or the score, and INTEG-01 still passes
- [ ] **DATA-03**: The team page shows a team's preseason Vegas win total next to its actual pace, labeled "not used in score" for seasons where the model expectation drives the score

### Team Identity

- [x] **LOGO-01**: All 32 team logos are downloaded once by a pipeline command into `web/public/logos/` and committed, so there's no hotlinking at runtime
- [x] **LOGO-02**: Logos appear on board rows, the team page header, records rows and chart marks, falling back to the existing color chip if a logo fails to load
- [x] **LOGO-03**: Relocated franchises show the current logo with the era-correct team name for that season (e.g. "San Diego Chargers" in 2010)

### Editorial Redesign (FiveThirtyEight-inspired)

- [x] **DESIGN-01**: The site uses a data-journalism type system: self-hosted Inter for text and IBM Plex Mono for numbers and annotations, with tabular figures
- [ ] **DESIGN-02**: Every chart follows one shared chart theme: a bold headline and gray dek, light value-axis gridlines only, direct labels instead of legends, the highlighted team in its color with the others in gray, and a SOURCE/NOTES footer
- [x] **DESIGN-03**: The board, team, history, records and methodology pages are restyled into a clean editorial layout (rule-separated tables with small logos, shaded score cells) in light and dark mode, without the FiveThirtyEight name, logo or proprietary fonts
- [x] **DESIGN-04**: The redesign keeps all v1 behavior: routes, scrubber, my-team pin, callouts, copy-link and mobile layout at 375px all still work, and the existing web tests pass

### Explore Charts

- [x] **EXPL-01**: The pipeline exports per-team-season EPA (offense and defense EPA/play, success rate, play counts), and the web computes play-weighted season-to-date values for any week
- [ ] **EXPL-02**: A new Explore page shows an offense-vs-defense EPA/play scatter with team logos as marks, for the selected season and week
- [ ] **EXPL-03**: The Explore page shows a "record vs evidence" scatter (win% vs feel-good score) that makes the perception gap visible, and each mark links to its team page

### Share Cards

- [ ] **SHARE-01**: Each build generates 1200×630 share images (satori + resvg) for all 32 teams and the current season's callouts, using the redesign's fonts, colors and local logos
- [ ] **SHARE-02**: Each share image has a static share page at a real path that includes the season and week. The page carries absolute share-card tags (og:image on the production domain) and redirects to the matching hash route with JavaScript
- [ ] **SHARE-03**: The copy-link buttons on team pages and callouts copy the share-page URL where one exists and fall back to the hash link otherwise

## Future Requirements (deferred)

- **MODEL-V2-01/02/03 implementation**: build and freeze the v2 model per PREREGISTRATION_V2.md, then evaluate on post-freeze games and 2027 (a future milestone)
- Share cards for historical (pre-current-season) callouts
- Era-specific historical logos

## Out of Scope

- Changing the frozen v1 weights or score in any way. The holdout was consumed; INTEG-01 enforces this.
- Moving to a history-mode router or server-side rendering, or using Vercel OG edge functions. Static share pages solve sharing.
- Copying FiveThirtyEight branding, logos or proprietary fonts. Inspired-by only.
- Hotlinking logos at runtime. The Wikipedia thumbnail links are broken and ESPN links can change.
- A "luckiest/unluckiest" framing on charts. v1 found the luck factor carries ≈0 or negative weight.
- Fan sentiment inputs, live updates, weight sliders and paid data (unchanged from v1).

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INTEG-01 | Phase 11 | Complete |
| INTEG-02 | Phase 9 | Complete |
| INTEG-03 | Phase 9 | Complete |
| DEPLOY-01 | Phase 10 | Complete |
| DEPLOY-02 | Phase 10 | Complete |
| DEPLOY-03 | Phase 10 | Complete |
| DATA-01 | Phase 11 | Complete |
| DATA-02 | Phase 11 | Complete |
| DATA-03 | Phase 13 | Pending |
| LOGO-01 | Phase 11 | Complete |
| LOGO-02 | Phase 12 | Complete |
| LOGO-03 | Phase 12 | Complete |
| DESIGN-01 | Phase 12 | Complete |
| DESIGN-02 | Phase 12 | Pending |
| DESIGN-03 | Phase 12 | Complete |
| DESIGN-04 | Phase 12 | Complete |
| EXPL-01 | Phase 11 | Complete |
| EXPL-02 | Phase 13 | Pending |
| EXPL-03 | Phase 13 | Pending |
| SHARE-01 | Phase 14 | Pending |
| SHARE-02 | Phase 14 | Pending |
| SHARE-03 | Phase 14 | Pending |

**Coverage:** 22/22 v2.0 requirements mapped, no orphans, no duplicates.

---
*Defined: 2026-11-11 for milestone v2.0 Public Site*

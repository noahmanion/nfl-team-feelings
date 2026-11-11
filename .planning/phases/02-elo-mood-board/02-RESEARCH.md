# Phase 2: Elo Mood Board - Research

**Researched:** 2026-11-11
**Domain:** Python/Polars JSON export (percentile scores, mood-band hysteresis) and a Vite 8 + Svelte 5 static site with hash routing
**Confidence:** HIGH. Every number below came from running code against the real `elo_snapshots.parquet`, live `nflreadpy.load_teams()`, and a fresh `create-vite` scaffold on Node 22.

## Summary

Phase 1 left a clean contract: `pipeline/data/derived/elo_snapshots.parquet` (19,422 rows; columns `season, week, franchise_id, elo, wins, losses, ties, win_pct`) plus `games.parquet` with `asof_week`, `played` and `game_type`. Phase 2 adds two pure Python modules (`mood.py` for percentile, bands and hysteresis; `export.py` for building and writing the JSON contract), two CLI subcommands (`export`, `refresh`), a small teams-metadata cache, and a new `web/` Vite + Svelte 5 app that reads only `web/public/data/`.

All the hard questions were tested empirically. The percentile computation (NumPy `searchsorted` mid-rank against the 15,978 REG + week-0 rows) together with hysteresis and the full JSON export runs in about 0.5 s. All 28 season files total about 3.2 MB raw (122 KB max per season, 7 KB gzipped), the 32 team files about 0.9 MB, and `history.json` 61 KB. Committing the JSON is fine. With the literal ±2 hysteresis reading, label changes drop by about 26% and quick A→B→A reversions by about 43% versus no buffer. The buffer is modest because the median weekly score move is already 4 points (90th percentile 10).

Three contract gaps must be closed in the plan. (1) Board rows need team name and colors, but the CONTEXT row shape has neither, so add a `teams` map to `meta.json`. (2) The frontend needs `reg_weeks` per season to label postseason weeks. The data confirms WC = `reg_weeks + 1` in every season from 1999 to 2025 (17 through 2020, 18 from 2021), and 2020's 14-team playoff did not shift the week numbers. (3) `nflreadpy.load_teams()` returns 36 rows, including both `LA` and `LAR` plus legacy `OAK`, `SD` and `STL`, so filter it to the 32 canonical codes.

**Primary recommendation:** Build `mood.py` (pure functions with unit tests) and `export.py` as `build_export(derived, teams, generated_at) -> dict[relpath, obj]` plus a separate writer, so tests can run on in-memory frames. Wire up `fgs refresh` as download → derive → checks (abort before writing anything) → write parquet → export. Scaffold `web/` with `npm create vite@latest web -- --template svelte-ts --no-interactive`, delete the demo assets, and add `vitest` only for pure TS modules (`router.ts`, `format.ts`).

## User Constraints (from CONTEXT.md)

<user_constraints>

### Locked Decisions

#### Score & mood labels
- The displayed "Feel-Good Score" is an integer 0–100: the percentile of the team's current underlying rating among ALL historical team-week snapshots 1999→present (regular-season and week-0 rows). In Phase 2 the underlying rating = Elo; later phases swap in the composite without changing the display contract.
- Never show decimals in the UI (out-of-scope: false precision). Elo itself may appear only as a secondary detail.
- Seven mood bands by score: ≥95 "Planning the parade" · 80–94 "Buying the jersey" · 60–79 "Cautiously smug" · 40–59 "It's fine. Everything's fine." · 20–39 "Checking the draft order" · 5–19 "Refreshing mock drafts" · <5 "Witness protection". Bands, labels and emoji live in pipeline config and are emitted in `meta.json` (frontend never hardcodes them).
- Hysteresis: a team's label only changes when its score moves past the band boundary by ≥2 points; otherwise it keeps its previous week's label. Computed in the pipeline chronologically per team-season; week 0 starts fresh (no carry from prior season).
- Weekly change = score delta vs the team's previous snapshot week (week 0 for week 1; for week 0 show "—"), plus rank change.

#### JSON contract (PIPE-02 — the only pipeline↔site interface)
- Pipeline writes into `web/public/data/` via a new `fgs export` step:
  - `meta.json` — generated_at (ISO), data_through (last played gameday), latest {season, week}, partial_week flag, seasons available with max week each, mood bands, score_kind ("elo" for now), version.
  - `latest.json` — the current board snapshot (same shape as one week inside a season file).
  - `snapshots/{season}.json` — every week of that season: `{season, weeks: {"0": [rows], "1": [...]}}`, row = franchise, rank, score, elo (int), label, emoji, wins, losses, ties, score_delta, rank_delta.
  - `teams/{ABBR}.json` — franchise name, colors, and columnar history arrays (season, week, score, elo, label) — reserved for Phase 4 deep-dive but populated now.
  - `history.json` — compact columnar all-team score grid (for Phase 3 chart).
  - `callouts.json` — `[]` placeholder this phase.
- Team display metadata (full name, nickname, primary/secondary colors) comes from `nflreadpy.load_teams()` mapped to canonical franchise_id; color chips, NOT logos.
- Generated JSON under `web/public/data/` is gitignored? — NO: keep it committed so the site runs without Python; regenerated by refresh. (Small: ~28 season files.)

#### Refresh command (PIPE-01)
- `uv run fgs refresh` (from `pipeline/`) = re-download schedules → build → check (abort on failure) → export. Works on a partially completed week: latest week = latest week with ≥1 played game, `partial_week=true` if that week has unplayed games; site shows "Week N (in progress)".
- Site shows a "Last updated" stamp from `meta.generated_at` and "data through {date}".

#### Frontend stack & layout
- `web/` = Vite 8 + Svelte 5 + TypeScript ~6.0 (svelte-ts template), Node 22 pinned via `web/.nvmrc`. No router lib: tiny hash router (`#/` latest board, `#/board/{season}/{week}`). Observable Plot not needed until Phase 3.
- Start locally: `cd web && npm install && npm run dev` (documented; `npm run dev` is the one command once installed).
- Board layout: single ranked list (cards/rows) — rank, team color chip + abbreviation + name, record W-L(-T), big score number, mood label + emoji, delta arrow (▲/▼/–) with value. Phone-first: rows stack cleanly at 375px with no horizontal scroll; desktop gets a wider table-like row.
- Scrubber: season `<select>` + week range slider (0..max week of season incl. playoffs, labelled "Preseason", "Wk N", "Wild Card"/"Divisional"/"Conf"/"Super Bowl"), plus "Latest" button. Changing either updates the hash.
- Visual tone: clean data-viz base (neutral background, one accent), playful copy only in labels/emoji/headline. Light + dark via prefers-color-scheme.

#### README (PIPE-03)
- Root README: what the idea is, how to run (pipeline refresh + site dev), where it stands. Keep brief.

### Claude's Discretion
- Component breakdown, CSS approach (plain CSS/scoped Svelte styles, no Tailwind needed), exact color tokens, percentile computation details, file naming inside `web/src`.

### Deferred Ideas (OUT OF SCOPE)
- Team click-through deep-dive (Phase 4), mood-over-time chart (Phase 3), callouts content (Phase 8), my-team pin (Phase 8).

### Specifics (from CONTEXT)
- Headline copy idea: "How should you feel about your team?" with the board below.
- Postseason weeks: nflverse weeks 19–22 (WC/DIV/CON/SB) for seasons ≥2021, 18–21 earlier — label from game_type, not raw week number.

</user_constraints>

**UI contract:** `02-UI-SPEC.md` is binding for every visual and interaction detail: tokens, the 375px and ≥1024px grids, states, copy, accessibility, and the component inventory. This research doesn't restate it. The planner should treat its "Planner dependency" note on `reg_weeks` as resolved by Finding 2 below.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PIPE-01 | One command refreshes data and regenerates all JSON after each week's games (full replay), tested on a partial week | `fgs refresh` flow (Pattern 3). The partial-week fixture technique was verified: null the MNF result in a copy of raw gives `latest=(2026,9), partial=True`; setting a week-10 TNF result gives `latest=(2026,10)`, 1 of 14 played, 32 rows in week 10, and only NYG/WAS Elo changed |
| PIPE-02 | JSON contract (meta, latest, snapshots, teams, history, callouts) is the only pipeline↔site interface | Contract shapes plus the measured sizes (Code Examples, Finding 4). Gaps to close: `meta.teams`, `meta.seasons[].reg_weeks` |
| PIPE-03 | Site runs locally with one command; README documents idea/run/status | `npm run dev` after `npm install` was verified on the svelte-ts template (Vite 8.3.8). Update the root README |
| SITE-01 | Board of all teams ranked with record, mood label, weekly change | Rank by Elo with an ordinal tiebreak (scores tie often). Row fields are listed in the contract, and team names and colors come from `meta.teams` |
| SITE-04 | Scrub any season/week since 1999 | `meta.seasons[]` with `max_week` and `reg_weeks`. Per-season files are lazy-loaded (≤122 KB). Hash router verified with vitest |
| SITE-10 | Mobile + last-updated stamp + hash deep links | `meta.generated_at` and `data_through`. Hash router pattern. Phone width is checked manually (UI-SPEC layouts) |
| INSIGHT-01 | Playful mood labels from historical percentile bands with hysteresis | `mood.py` algorithm and measured flip rates (Finding 3). Bands config is emitted in `meta.bands` |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

From `/Users/noahmanion/Dropbox/code/idea-graveyard/CLAUDE.md` (repo) and `feel-good-scorew/CLAUDE.md`:
- Stay self-contained inside `feel-good-scorew/`. Don't share deps with other repo projects and don't add root-level package manifests (at the idea-graveyard root). `web/package.json` inside the project is fine.
- Keep it light: quick prototypes, no heavy process, no CI or deployment setup unless asked. Tests stay light. The pipeline already uses pytest, and frontend tests should cover only pure TS logic.
- Each project has a brief README (what it is, how to run, where it stands). Update the existing `feel-good-scorew/README.md`.
- Stack (project CLAUDE.md): Python 3.13 + uv + nflreadpy (pinned 0.1.5) + Polars in `pipeline/`. Vite 8 + Svelte 5 in `web/`. **TypeScript must stay ~6.0**, because svelte-check 4.7.8 only supports TS 5/6. Use Node 22/24 LTS.
- Hosting is local first, with Vercel static later. Hash routing means no `vercel.json` is needed.
- GSD workflow: edits go through GSD commands (the executor handles this).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Percentile score, mood band, hysteresis, deltas, ranks | Pipeline (Python, `mood.py`) | — | ARCHITECTURE Anti-Pattern 4: the frontend never computes the model. Hysteresis needs the full chronological history |
| JSON contract emission | Pipeline (`export.py`) | — | PIPE-02: the single interface |
| Team display metadata (names, colors) | Pipeline (ingest + `meta.teams`) | — | Canonical franchise mapping lives only in Python |
| Week labels (Preseason / Week N / Wild Card…) | Browser (`format.ts`) | Pipeline supplies `reg_weeks` | A presentation string, derived from data-driven `reg_weeks`, never a hardcoded 2021 cutover |
| Routing, scrubbing, fetch + session cache | Browser (Svelte SPA) | CDN/static serves `public/data` | Static hosting with hash routes |
| Static assets and data files | CDN/Static (`vite dev` locally, Vercel later) | — | No server runtime |

## Standard Stack

### Core (pipeline additions: none)
Phase 2 needs **no new Python dependencies**. NumPy (`searchsorted`), Polars and stdlib `json` cover everything. `nflreadpy.load_teams()` is already available in the pinned 0.1.5. [VERIFIED: ran in pipeline venv]

### Core (web)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| vite | 8.3.8 (template pins ^8.3.6) | Dev server and static build | Official template [VERIFIED: npm view + scaffold] |
| svelte | 5.57.3 | UI with runes | [VERIFIED: npm view + scaffold] |
| @sveltejs/vite-plugin-svelte | 7.3.1 | Vite integration | [VERIFIED] |
| typescript | ~6.0.3 (template) | Types. **Do not bump to 7** | [VERIFIED: scaffold package.json] |
| svelte-check | 4.7.8 (template ^4.7.7) | `npm run check` | Ran: 0 errors on the prototype [VERIFIED] |
| @tsconfig/svelte | 5.0.8 | tsconfig base | [VERIFIED] |
| @types/node | ^24.19.2 | Types for vite.config | [VERIFIED] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| vitest | 5.1.0 (peer `vite ^6.4 \|\| ^7 \|\| ^8`; engines node `^22.12 \|\| ^24 \|\| >=26`) | Unit tests for `router.ts` / `format.ts` | Only for pure TS. `npx vitest run` took 1.2 s wall time with **no config file** (default node env) [VERIFIED: installed and ran] |

**Not needed in Phase 2:** Observable Plot (Phase 3), jsdom/happy-dom, @testing-library/svelte, Playwright. Component tests would be heavy process, which CLAUDE.md asks to avoid.

**Installation:**
```bash
# from feel-good-scorew/
source ~/.nvm/nvm.sh && nvm use 22
npm create vite@latest web -- --template svelte-ts --no-interactive   # create-vite 9.3.4 verified
cd web && echo 22 > .nvmrc && npm install && npm install -D vitest@^5.1.0
# then delete demo files: src/lib/Counter.svelte, src/assets/*, public/icons.svg, README.md (web/ — the project README is the root one)
```
Template contents verified on 2026-11-11: `.gitignore` (ignores `node_modules`, `dist`, not `public/`), `.vscode/extensions.json`, `index.html` (`<title>web</title>`, `lang="en"` already set), `public/favicon.svg`, `public/icons.svg`, `src/{App.svelte, app.css, main.ts, lib/Counter.svelte, assets/{hero.png,svelte.svg,vite.svg}}`, `svelte.config.js` (empty `export default {}`), `tsconfig.json`/`tsconfig.app.json`/`tsconfig.node.json`, `vite.config.ts` (`plugins: [svelte()]`). Scripts: `dev`, `build`, `preview`, `check`. Add `"test": "vitest run"`. `npm install` took 7 s (49 packages); vitest added 16 more in 1 s.

## Package Legitimacy Audit

slopcheck could not be installed in this environment (`pip install slopcheck` failed silently, so the command is unavailable). Every package below comes from the **official `create-vite` svelte-ts template** or from vitest (the Vite team's own test runner). All were installed and run successfully in the scratch dir. Per protocol they're tagged ASSUMED for slopcheck, but the provenance risk is very low.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| vite | npm | 6+ yrs | very high | github.com/vitejs/vite | unavailable [ASSUMED] | Approved (official template) |
| svelte | npm | 9+ yrs | very high | github.com/sveltejs/svelte | unavailable [ASSUMED] | Approved (official template) |
| @sveltejs/vite-plugin-svelte | npm | 5+ yrs | high | github.com/sveltejs/vite-plugin-svelte | unavailable [ASSUMED] | Approved (official template) |
| svelte-check, @tsconfig/svelte, typescript, @types/node | npm | multi-year | very high | sveltejs / microsoft / DefinitelyTyped | unavailable [ASSUMED] | Approved (official template) |
| vitest | npm | 5 yrs | very high | github.com/vitest-dev/vitest | unavailable [ASSUMED] | Approved. `npm view vitest scripts.postinstall` is empty |

**Packages removed:** none. **Packages flagged [SUS]:** none. Because slopcheck was unavailable, the planner may add one `checkpoint:human-verify` for `npm install -D vitest`. The template packages arrive via the official scaffolder.

## Key Findings (empirical)

### Finding 1: `load_teams()` quirks
Live call, nflreadpy 0.1.5: **36 rows**, 16 columns: `team_abbr, team_name, team_id, team_nick, team_conf, team_division, team_color, team_color2, team_color3, team_color4, team_logo_wikipedia, team_logo_espn, team_wordmark, team_conference_logo, team_league_logo, team_logo_squared`. [VERIFIED]
- Extra rows beyond canonical: `LAR` (duplicate of `LA`, same team_id 2510), plus `OAK`, `SD`, `STL` (legacy). All 32 `CANONICAL` codes are present. **Filter `team_abbr.is_in(CANONICAL)` and assert exactly 32 rows.**
- `team_name` is the full name ("Los Angeles Rams", "Washington Commanders"). `team_nick` is the nickname. Current names only, so historical Raiders seasons display as "Las Vegas Raiders", which matches ARCHITECTURE Anti-Pattern 5.
- `team_color` and `team_color2` are valid `#RRGGBB` for all 32, in **mixed case** (`#ffc20e` vs `#FFB612`). Uppercase them. `team_color3`/`team_color4` are null for NYJ and TEN, so don't use them. LV and PIT have primary `#000000` (the UI-SPEC chip outline handles that).
- Cache it like schedules: `data/cache/teams.parquet`, via `load_teams(refresh=False)` in `ingest.py` with `update_config(cache_mode="off")`. Tests must never hit the network: skip when the cache file is missing (same pattern as `real_cache`).

### Finding 2: Postseason week numbering
From `games.parquet` (all played seasons): [VERIFIED]
- 1999–2020: `REG 1-17, WC 18, DIV 19, CON 20, SB 21`. **This includes 2020** (14-team playoff, same week numbers).
- 2021–2025: `REG 1-18, WC 19, DIV 20, CON 21, SB 22`.
- 2026: REG 1-18 scheduled, snapshots through week 9.
- `asof_week == week` for every game 1999–2026, and snapshot max week per season is 21 / 22 / 9.
- So `postseason index = week - reg_weeks` (1=WC, 2=DIV, 3=CON, 4=SB), and `season_config.reg_weeks(season)` matches the data exactly. **Recommendation:** emit `reg_weeks` per season in `meta.seasons[]`, computed from data (`max week where game_type=="REG"`). Add an export-time assertion that it equals `season_config.reg_weeks(s)` and that the postseason weeks' game_types are WC/DIV/CON/SB in order, which honors "label from game_type". The frontend builds labels from `reg_weeks` and never hardcodes 2021.

### Finding 3: Percentile and hysteresis on real data
Script: scratchpad `mood_exp.py`, run on the real `elo_snapshots.parquet`. [VERIFIED]
- **Reference set:** rows with `week <= reg_weeks(season)` (week 0 plus REG) = **15,978** of 19,422 rows. Playoff-week rows are scored against it but not included in it.
- **Percentile:** mid-rank `100 * (count_less + 0.5*count_equal) / N` with `np.searchsorted`, then `np.rint` gives integers **0..100** (128 rows at 100, 120 at 0). Floor gives 0..100 with only 2 rows at 100. Recommend `rint` and clip to [0, 100].
- **Band shares by construction** (reference rows): 4.5 / 15 / 20 / 20 / 20 / 15 / 5.5 %. For 2026 week 9 the band counts are [2, 6, 7, 2, 5, 9, 1]. Only 2 teams are "It's fine", because midseason Elo spreads wider than week 0. Top is BUF 98 (Elo 1697), bottom TEN 2 (1309). That is plausible.
- **Drift:** because the reference includes the current season, every refresh re-scores history slightly. Measured: adding one week's 32 rows changes **1.3%** of all historical scores by exactly **1 point** (max 1). Excluding 2026 entirely changes 5.7% by ≤1. That's acceptable under the locked "1999→present" rule, but it means a refresh touches many season files in git and makes historical scores non-frozen (see Pitfall 4).
- **Weekly score moves:** median |Δ| = 4, p90 = 10, max = 25 points.
- **Hysteresis, measured over all 1999–2026 team-season chains (week 0 fresh):**

| Variant | Rule (t = lower threshold of the band being entered/left) | Label changes | per team-week | A→B→A reversions ≤3 wks | Rows where label ≠ raw band |
|---|---|---|---|---|---|
| none | — | 4,535 | 0.245 | 2,186 | 0 |
| **±2 literal (recommended)** | up: `s ≥ t+2`; down: `s ≤ t−2` | 3,372 (−26%) | 0.182 | 1,239 (−43%) | 1,546 (8.0%) |
| ±2 strict | up: `s ≥ t+2`; down: `s ≤ t−3` | 3,060 (−33%) | 0.165 | 1,031 (−53%) | 2,051 (10.6%) |
| ±3 strict | up `t+3`, down `t−4` | 2,559 (−44%) | 0.138 | 698 (−68%) | 2,976 (15.3%) |

Recommend the **literal ±2** reading: entering band k from below requires `score ≥ T[k] + 2`, and leaving band k downward requires `score ≤ T[k] − 2`, so the dead zone around each threshold is `T−1..T+1`. Multi-band jumps go to the furthest band whose boundary is cleared by the buffer. About 8% of rows show a label one band away from their raw score band, so the UI-SPEC rule "stripe color from label, not score" is load-bearing. Put the buffer (2) in the bands config so it can be tuned.

### Finding 4: JSON sizes (prototype export, compact separators, `ensure_ascii=False`)
[VERIFIED: scratchpad `size_exp.py`]

| File(s) | Count | Total raw | Max raw | Total gzip | Max gzip |
|---|---|---|---|---|---|
| `snapshots/{season}.json` | 28 | 3.2 MB | 122 KB | 191 KB | 7 KB |
| `teams/{ABBR}.json` | 32 | 0.9 MB | 28 KB | 61 KB | ~1 KB |
| `history.json` (`keys` + per-team score arrays) | 1 | 61 KB | — | 17 KB | — |
| one week (≈ `latest.json`) | 1 | 5.3 KB | — | — | — |

The total is about 4.2 MB committed, which is fine. Repeating label strings in every row is the bulk of the size, and gzip removes it. Optionally add an integer `band` field per row (index into `meta.bands`), which would also simplify the stripe lookup. Don't bother shrinking further.

### Finding 5: Partial-week testing
Live cache: 2026 week 9 is fully played (15/15, data through 2026-11-09), and week 10 starts 2026-11-12. **So `partial_week` is false on real data today.** The partial path must be tested synthetically: mutate a copy of raw schedules and call `derive()` in memory (verified):
- Nulling `result/home_score/away_score` for the last week-9 game gives latest (2026, 9) with partial=True, and the grid still ends at week 9.
- Setting a TNF week-10 result (`2026_10_WAS_NYG`) gives latest (2026, 10) with 1/14 played and 32 rows in week 10. Only NYG and WAS Elo differ from week 9, so the other 30 teams get `score_delta = 0`, which renders "–". That matches the UI-SPEC partial-week state.

### Finding 6: Frontend toolchain behavior
[VERIFIED in scratch scaffold]
- Under Node 22.23.3: `npx vitest run` passed 4 router tests in 77 ms (1.2 s wall). `npm run check` reported 0 errors across 119 files. `npm run build` produced 26 KB JS (10.5 KB gz) in 233 ms.
- Exporting a runes store from `route.svelte.ts` as `$state({ current })` and mutating `.current` on `hashchange` works and type-checks. You can't export a reassigned `$state` primitive, so wrap it in an object.
- Node environment: nvm default is **20.19.0**, available versions are 22.23.3 and 24.20.0, and a login zsh resolves `node` to **v26.7.0**. vitest 5's `engines` says `^22.12 || ^24 || >=26`. It happened to run on 20.19 here, but don't rely on that. Ship `web/.nvmrc` = `22` and optionally `"engines": {"node": ">=22.12"}`. The README should say `nvm use` (or any Node ≥22.12).
- Fetch data with `` `${import.meta.env.BASE_URL}data/meta.json` `` so a future non-root deploy works.

## Architecture Patterns

### System Architecture Diagram

```
                       uv run fgs refresh
                              │
   nflverse ──nflreadpy──▶ ingest.load_schedules(refresh=True) ─┐
   nflverse ──nflreadpy──▶ ingest.load_teams(refresh=True) ─────┤  data/cache/*.parquet
                                                                ▼
                     pre-derive checks (columns, codes) ── fail ──▶ exit 1 (nothing written)
                                                                ▼
                     derive(raw): games(+Elo, asof_week) → team_games → snapshots grid
                                                                ▼
                     run_checks(...) ─────────────── fail ──▶ exit 1 (old JSON untouched)
                                                                ▼
                     write data/derived/*.parquet
                                                                ▼
             mood.py: reference set (wk0+REG) → percentile score (int 0..100)
                      → rank (by Elo, ordinal) → deltas (vs prev week, same season)
                      → band + hysteresis (chronological per team-season, wk0 fresh)
                                                                ▼
             export.build_export(...) → {relpath: obj} ──▶ write_export(web/public/data)
                meta.json · latest.json · snapshots/{season}.json · teams/{ABBR}.json
                history.json · callouts.json([])
                                                                ▼
  Browser ── boot: fetch meta.json + latest.json (parallel)
          ── hashchange → parse route ─┬─ "#/" → latest
                                       └─ "#/board/s/w" → validate vs meta.seasons
                                             → fetch snapshots/{s}.json (session cache,
                                               ignore stale responses) → weeks[w]
          ── render: Scrubber · BoardHeading · MoodBoard(rows, meta.teams, meta.bands) · Footer
```

### Recommended Project Structure
```
feel-good-scorew/
├── README.md                       # update: run pipeline refresh + site dev, status
├── pipeline/src/fgs/
│   ├── ingest.py                   # + load_teams(refresh) → data/cache/teams.parquet
│   ├── mood.py                     # NEW: BANDS config, percentile(), band_of(), hysteresis(), score_frame()
│   ├── export.py                   # NEW: build_export() pure, write_export() I/O, EXPORT_DIR
│   ├── paths.py                    # + WEB_DATA_DIR = PIPELINE_ROOT.parent / "web" / "public" / "data"
│   └── cli.py                      # + export, refresh subcommands
├── pipeline/tests/
│   ├── test_mood.py                # NEW: synthetic percentile/hysteresis/delta tests
│   └── test_export.py              # NEW: contract on real cache (skip if missing) + partial-week synthetic
└── web/
    ├── .nvmrc                      # 22
    ├── index.html                  # title "Feel-Good Score"
    ├── public/data/                # GENERATED, committed
    └── src/
        ├── main.ts · App.svelte · app.css
        ├── lib/{router.ts, router.test.ts, format.ts, format.test.ts, data.ts, types.ts, route.svelte.ts}
        └── components/{SiteHeader, Scrubber, BoardHeading, MoodBoard, BoardRow, TeamChip,
                        MoodLabel, Delta, Badge, StatusPanel, SiteFooter}.svelte
```

### Pattern 1: Pure mood functions (pipeline)
**What:** keep percentile, band and hysteresis as pure functions over arrays/lists, then join them back with Polars.
```python
# mood.py — verified algorithm (scratchpad mood_exp.py)
import numpy as np
BANDS = [  # low → high; emitted verbatim as meta.bands
    {"min": 0,  "label": "Witness protection",              "emoji": "🕶️"},
    {"min": 5,  "label": "Refreshing mock drafts",          "emoji": "🔄"},
    {"min": 20, "label": "Checking the draft order",        "emoji": "📋"},
    {"min": 40, "label": "It’s fine. Everything’s fine.",   "emoji": "🔥"},
    {"min": 60, "label": "Cautiously smug",                 "emoji": "😏"},
    {"min": 80, "label": "Buying the jersey",               "emoji": "🎽"},
    {"min": 95, "label": "Planning the parade",             "emoji": "🎉"},
]  # emoji are placeholders [ASSUMED]; UI-SPEC mock shows 🎽 and 🕶
HYSTERESIS = 2
T = [b["min"] for b in BANDS]

def percentile_scores(elo: np.ndarray, ref: np.ndarray) -> np.ndarray:
    ref = np.sort(ref)
    lo, hi = np.searchsorted(ref, elo, "left"), np.searchsorted(ref, elo, "right")
    return np.clip(np.rint(100.0 * (lo + 0.5 * (hi - lo)) / ref.size), 0, 100).astype(int)

def band_of(s: int) -> int:
    return int(np.searchsorted(T, s, "right") - 1)

def hysteresis(scores: list[int], buf: int = HYSTERESIS) -> list[int]:
    """Band index per week for ONE team-season (week 0 first). Week 0 = raw band."""
    out, prev = [], None
    for s in scores:
        b = band_of(s)
        if prev is None:
            prev = b
        elif b > prev:
            prev = max([k for k in range(prev + 1, b + 1) if s >= T[k] + buf], default=prev)
        elif b < prev:
            new = prev
            for k in range(prev, b, -1):          # leaving band k downward across T[k]
                if s <= T[k] - buf: new = k - 1
                else: break
            prev = new
        out.append(prev)
    return out
```

### Pattern 2: Scored frame and contract rows
- `rank`: sort by `elo` desc, then `franchise_id` asc, and use `rank("ordinal")` within (season, week). Don't rank by integer score, because DEN and JAX are both 93 in 2026 week 9.
- `score_delta = score − score.shift(1).over(franchise_id, season)`, so it's null at week 0. `rank_delta = rank.shift(1) − rank`, where **positive means moved up**, per UI-SPEC.
- Hysteresis: sort by (franchise_id, season, week), `group_by([franchise_id, season], maintain_order=True)`, apply `hysteresis` to the score list, explode. A Python loop over about 19k rows took under 0.5 s end to end.
- `elo` is emitted as `int(round(elo))`. No floats anywhere in board rows.

### Pattern 3: `fgs refresh` = checked pipeline, write-last
```python
def _cmd_refresh(args) -> int:
    raw = load_schedules(refresh=True)
    teams = load_teams(refresh=True)
    # reuse the _cmd_check body as a function: returns (ok, derived)
    ok, derived, params = _checked_derive(raw)   # columns+codes pre-derive, then run_checks
    if not ok:
        print("checks failed; JSON not regenerated", file=sys.stderr); return 1
    _write_derived(derived)                       # parquet (what build_all does today)
    files = export.build_export(derived, teams, generated_at=_now_iso())
    export.write_export(files, WEB_DATA_DIR)      # clears snapshots/ and teams/ first
    print(f"exported {len(files)} files; latest {meta['latest']} partial={meta['partial_week']}")
    return 0
```
- `fgs export` = read `data/derived/*.parquet` and `data/cache/teams.parquet`, then build and write. It doesn't touch the network. Use it for iterating on the export without re-downloading.
- Note: today's `build_all` writes parquet **before** checks run. Refresh must check first, so failures leave both the parquet and the JSON from the previous good run.
- Refactor `_cmd_check`'s body into a reusable helper rather than duplicating it.

### Pattern 4: Tiny hash router plus a runes route store (web)
```ts
// lib/router.ts — verified with vitest 5.1.0
export type Route = { kind: 'latest' } | { kind: 'board'; season: number; week: number } | { kind: 'invalid' }
export function parseHash(hash: string): Route {
  const h = hash.replace(/^#/, '')
  if (h === '' || h === '/') return { kind: 'latest' }
  const m = /^\/board\/(\d{4})\/(\d{1,2})\/?$/.exec(h)
  return m ? { kind: 'board', season: +m[1], week: +m[2] } : { kind: 'invalid' }
}
export const boardHash = (s: number, w: number) => `#/board/${s}/${w}`

// lib/route.svelte.ts — verified with svelte-check (0 errors)
import { parseHash, type Route } from './router'
export const route = $state<{ current: Route }>({ current: parseHash(location.hash) })
window.addEventListener('hashchange', () => { route.current = parseHash(location.hash) })
```
- Season select: `location.hash = boardHash(...)`, which pushes a history entry. Slider `input`: `history.replaceState(null, '', boardHash(...))` **plus** set `route.current` directly, because `replaceState` does **not** fire `hashchange`. [CITED: HTML spec behavior: hashchange fires on fragment navigation, not on history.replaceState] This is a classic trap; see Pitfall 6.
- Validation against `meta.seasons` happens in App, not in `parseHash`, which keeps `parseHash` pure and testable.

### Pattern 5: Data layer
- `data.ts`: `loadMeta()` with `fetch(url, { cache: 'no-store' })`. Other files get `?v=${meta.generated_at}` appended, so a refresh is never masked by the browser cache. Season files are cached in a `Map<number, Promise<SeasonFile>>`.
- Stale-response guard: keep a `requestedSeason` token and ignore resolved fetches whose season ≠ the latest request (UI-SPEC).

### Anti-Patterns to Avoid
- **Computing labels or percentiles in the browser:** this violates the locked decision and Anti-Pattern 4.
- **Hardcoding the 2021 cutover or the band thresholds in TS:** read `meta.seasons[].reg_weeks` and `meta.bands`.
- **Ranking by the integer score:** produces ties and unstable order. Rank by Elo.
- **Writing JSON incrementally while building:** build every object first, then write. Clear `snapshots/` and `teams/` so stale files can't linger.
- **Fetching all 32 `teams/*.json` files to render the board:** put the team names and colors in `meta.teams`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Percentile against a 16k reference | Python loops / custom sort | `np.searchsorted` (left/right mid-rank) | Exact tie handling, vectorized, 1 line |
| Team names/colors | A hand-typed table of 32 teams | `nflreadpy.load_teams()` filtered to `CANONICAL` | Already the source of truth. Colors verified valid |
| Postseason week labels | `if season >= 2021` in TS | `reg_weeks` from data in `meta.seasons` | Era rules belong in the pipeline |
| Routing | A router library | 15-line `parseHash` + `hashchange` | Two routes. Locked decision |
| Date formatting | Manual string building | `Intl.DateTimeFormat('en-US', …)` | UI-SPEC rule. Handles the local timezone |
| JSON writing | `polars.write_json` per file | stdlib `json.dumps(obj, separators=(",",":"), ensure_ascii=False)` written as UTF-8 | Control over shape. Compact. Readable emoji/’ in diffs |

## Common Pitfalls

### Pitfall 1: `load_teams()` has 36 rows, including `LAR` and `LA`
**What goes wrong:** a join on `team_abbr` creates duplicate Rams rows, or legacy OAK/SD/STL rows leak into the output. **Avoid:** `filter(team_abbr ∈ CANONICAL)`, assert `height == 32`, and assert unique franchise_id. **Warning sign:** `meta.teams` has 33+ keys.

### Pitfall 2: Percentile reference includes playoff weeks
**What goes wrong:** eliminated teams' frozen ratings get counted 1–4 extra times, which skews the distribution. **Avoid:** reference = rows with `week <= reg_weeks(season)` only (15,978 rows). Score playoff rows against it.

### Pitfall 3: Hysteresis chain crosses seasons or skips week 0
**What goes wrong:** the label carries over from last year's Super Bowl week. **Avoid:** group by (franchise_id, season). Week 0 = raw band. Unit-test that a week-0 score of 61 after a prior-season 58 "fine" label gives "smug".

### Pitfall 4: Historical scores drift by ±1 every refresh
**What goes wrong:** git diffs touch many old season files each week, and a historical "score 95" can become 94. Measured: about 1.3% of rows move by 1 point per added week. **Avoid / accept:** this follows from the locked "1999→present" reference. Document it in the README status line. Don't write tests that pin exact historical scores. Pin structure and monotonicity instead. (Freezing the reference to completed seasons would contradict the locked decision, so it's not recommended.)

### Pitfall 5: Partial week can't be reproduced on today's data
**What goes wrong:** the "tested on a partial week" requirement (PIPE-01) gets verified against a fully played week 9. **Avoid:** a synthetic test that mutates raw results (Finding 5) and runs derive + build_export in memory. Assert `meta.partial_week`, `meta.latest`, and that teams that didn't play have `score_delta == 0`.

### Pitfall 6: `history.replaceState` doesn't fire `hashchange`
**What goes wrong:** dragging the slider updates the URL but not the board, or the code switches to `location.hash =` and floods history. **Avoid:** on slider input, update `route.current` directly and call `replaceState`. Season changes use `location.hash`, and the `hashchange` listener handles them.

### Pitfall 7: Apostrophes and emoji in JSON
**What goes wrong:** the label renders with a straight `'` while UI-SPEC wants `’`, or emoji become `\ud83d…` escapes in committed files. Escapes still parse, but the diffs are unreadable. **Avoid:** store `’` (U+2019) in the pipeline BANDS config. Write with `ensure_ascii=False` and `encoding="utf-8"`. Emoji with a variation selector (🕶️ = U+1F576 U+FE0F) are fine.

### Pitfall 8: Node version mismatch
**What goes wrong:** nvm defaults to Node 20 on this machine, and vitest 5 declares Node ≥22.12. **Avoid:** `web/.nvmrc` = 22, and the README says `nvm use`. Verified both: it works on 22, and on 20 it happened to pass, but that isn't supported.

### Pitfall 9: Offseason "latest"
**What goes wrong:** after a new season's schedule is published (before kickoff), snapshots hold week-0-only rows for the new season (WR-03), while "latest played week" is still the previous Super Bowl. **Avoid:** include such seasons in `meta.seasons` with `max_week: 0`, and keep `meta.latest` = the last played week, per CONTEXT. Make sure the season select still lists the new season. (This isn't reachable on today's data. A cheap synthetic test is optional.)

### Pitfall 10: `generated_at` breaks idempotence checks
`meta.generated_at` changes every run. Any "export twice gives identical output" test must ignore that key, or inject `generated_at` as a parameter (the recommended `build_export(..., generated_at=...)` signature does this).

## Code Examples

### Contract shapes (recommended; additive to CONTEXT)
```jsonc
// meta.json
{
  "version": 1, "score_kind": "elo",
  "generated_at": "2026-11-11T18:40:00+00:00",
  "data_through": "2026-11-09",
  "latest": {"season": 2026, "week": 9}, "partial_week": false,
  "seasons": [{"season": 1999, "max_week": 21, "reg_weeks": 17, "n_teams": 31}, …,
              {"season": 2026, "max_week": 9, "reg_weeks": 18, "n_teams": 32}],
  "bands": [{"min": 0, "max": 4, "label": "Witness protection", "emoji": "🕶️"}, …],
  "hysteresis": 2,
  "teams": {"BUF": {"name": "Buffalo Bills", "nick": "Bills", "primary": "#00338D", "secondary": "#C60C30"}, …}
}
// latest.json — self-describing wrapper around one week's rows
{"season": 2026, "week": 9, "rows": [ {row}, … ]}
// snapshots/2026.json
{"season": 2026, "weeks": {"0": [ {row} ], …, "9": [ … ]}}
// row
{"franchise": "BUF", "rank": 1, "score": 98, "elo": 1697, "label": "Planning the parade", "emoji": "🎉",
 "wins": 7, "losses": 1, "ties": 0, "score_delta": 3, "rank_delta": 0}
// teams/BUF.json
{"franchise": "BUF", "name": "Buffalo Bills", "nick": "Bills", "primary": "#00338D", "secondary": "#C60C30",
 "history": {"season": [...], "week": [...], "score": [...], "elo": [...], "label": [...]}}
// history.json — null where a team didn't exist (HOU before 2002)
{"keys": ["1999-0", "1999-1", …], "teams": {"BUF": [50, 52, …], "HOU": [null, …]}}
// callouts.json
[]
```
For `reg_weeks`: compute from data and assert it equals `season_config.reg_weeks`. For a season with no REG games played yet, fall back to `season_config.reg_weeks`. `data_through`: reuse `cli._data_through(games, *latest)`.

### Week labels (frontend)
```ts
// lib/format.ts
const POST = ['Wild Card', 'Divisional', 'Conference Championships', 'Super Bowl']
const POST_TICK = ['WC', 'Div', 'Conf', 'SB']
export function weekLabel(week: number, regWeeks: number): string {
  if (week === 0) return 'Preseason'
  if (week <= regWeeks) return `Week ${week}`
  return POST[week - regWeeks - 1] ?? `Week ${week}`
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Svelte 4 stores (`writable`) | Svelte 5 runes (`$state`, `$derived`, `$effect`) in `.svelte` / `.svelte.ts` | Svelte 5 | The template uses runes. Shared reactive state goes in `.svelte.ts` modules as exported objects |
| `new App({ target })` | `mount(App, { target })` | Svelte 5 | The template's `main.ts` already does this |
| create-vite svelte-ts with `vitePreprocess` in svelte.config | `svelte.config.js` is an empty `export default {}` | create-vite 9.x (verified) | TS in `<script lang="ts">` works without explicit preprocess config (checked: build + svelte-check pass) |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Emoji per band (🕶️ 🔄 📋 🔥 😏 🎽 🎉) | Pattern 1 | Cosmetic. They live in pipeline config, so changing them is a one-line edit |
| A2 | `rint` (not floor) for the integer percentile | Finding 3 | Low. Shifts about 0.5 point at band edges |
| A3 | Literal ±2 rule (`≥T+2` up, `≤T−2` down) is the intended reading of "past the boundary by ≥2" | Finding 3 | Low. The strict variant is a one-character change. Both are measured |
| A4 | `meta.teams` and `meta.seasons[].reg_weeks`/`n_teams` are acceptable additive extensions of the locked contract | Code Examples | Low. Additive. The board can't show names or colors without them |
| A5 | `latest.json` wraps rows as `{season, week, rows}` instead of a bare array | Code Examples | Low. CONTEXT says "same shape as one week". The wrapper is self-describing. Planner decides |
| A6 | slopcheck unavailable, so packages tagged ASSUMED | Audit | Very low: official template |

## Open Questions (RESOLVED: band field = yes; latest.json wrapper = yes; emoji placeholders OK)

1. **Should rows carry an integer `band`?**
   - Known: UI-SPEC maps stripe color by label → band index, and that works.
   - Recommendation: add `band` (int) to rows. It costs about 9 bytes per row and removes the string matching. Optional.
2. **Should `fgs refresh` re-download teams every run?**
   - Recommendation: yes. It's tiny and makes rebrands self-healing. `fgs export` uses the cache.
3. **Should we commit `web/public/data/` with every refresh even though about 1% of historical scores drift?**
   - Locked: committed. Accept the diffs (Pitfall 4).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | pipeline | ✓ | 0.10.12 | — |
| Python 3.13 venv (pipeline) | pipeline | ✓ | 3.13 + polars 2.1.0, nflreadpy 0.1.5 | — |
| Network to nflverse (GitHub releases) | `fgs refresh` | ✓ (load_teams succeeded live) | — | `fgs export` from cache |
| Node 22 (nvm) | web | ✓ | 22.23.3 (nvm default is 20.19.0; login shell node 26.7.0) | Node 24.20.0 also installed |
| npm | web | ✓ | 10.9.9 | pnpm |
| create-vite | scaffold | ✓ via npm | 9.3.4 | — |
| slopcheck | package audit | ✗ | — | Treat as ASSUMED. Official template |

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (pipeline) | pytest 9.2 (existing; 74 tests pass in 0.52 s) |
| Framework (web) | vitest 5.1.0 (Wave 0 install), plus `svelte-check` and `vite build` as compile gates |
| Config file | `pipeline/pyproject.toml` `[tool.pytest.ini_options]` (exists). vitest needs **no config** (default `**/*.test.ts`, node env) |
| Quick run command | `cd pipeline && uv run pytest -q tests/test_mood.py tests/test_export.py` / `cd web && npx vitest run` |
| Full suite command | `cd pipeline && uv run pytest -q && cd ../web && npm run test && npm run check && npm run build` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INSIGHT-01 | percentile 0..100, ties mid-rank, reference = wk0+REG only | unit (synthetic) | `uv run pytest -q tests/test_mood.py -k percentile` | ❌ Wave 0 |
| INSIGHT-01 | hysteresis: holds within ±1 of a boundary, switches at ±2, multi-band jumps, week 0 fresh, no cross-season carry | unit | `uv run pytest -q tests/test_mood.py -k hysteresis` | ❌ Wave 0 |
| INSIGHT-01 | on real data, label changes < raw-band changes (sanity: ≈3.4k vs 4.5k) | integration (real cache, skip if missing) | `uv run pytest -q tests/test_mood.py -k real` | ❌ Wave 0 |
| PIPE-02 | contract: 28 season files, 32 team files, meta keys, row keys, ints only, ranks 1..n, n_teams per season, meta.teams has 32 entries with `#RRGGBB` | integration (real cache, tmp out dir) | `uv run pytest -q tests/test_export.py -k contract` | ❌ Wave 0 |
| PIPE-02 | latest.json == snapshots[latest.season].weeks[latest.week] rows | integration | `uv run pytest -q tests/test_export.py -k latest` | ❌ Wave 0 |
| PIPE-01 | partial week: null the last wk-9 result gives partial_week true. A TNF wk-10 result gives latest wk10 and 30 teams with score_delta 0 | integration (synthetic mutation of cached raw) | `uv run pytest -q tests/test_export.py -k partial` | ❌ Wave 0 |
| PIPE-01 | `fgs refresh` aborts without writing when checks fail (monkeypatch load_schedules to inject a bad code; out dir untouched) | integration | `uv run pytest -q tests/test_cli.py -k refresh` | ❌ Wave 0 |
| SITE-04/10 | parseHash/boardHash round-trip, invalid → 'invalid' | unit | `cd web && npx vitest run src/lib/router.test.ts` | ❌ Wave 0 |
| SITE-04 | weekLabel for 2020 (reg 17: 18→Wild Card, 21→Super Bowl) and 2021 (reg 18: 22→Super Bowl), week 0 → Preseason; formatRecord with ties; formatDelta sign/arrows | unit | `cd web && npx vitest run src/lib/format.test.ts` | ❌ Wave 0 |
| SITE-01/10, PIPE-03 | board renders 32 rows, no horizontal scroll at 375px, dark mode, stamp visible, deep link reload works | manual (browser devtools at 375/1024px) | `cd web && npm run dev` then visit `#/`, `#/board/2007/21`, `#/board/1999/0`, `#/board/1800/3` | manual-only: visual/layout |
| PIPE-03 | site builds and type-checks | smoke | `cd web && npm run check && npm run build` | ✅ after scaffold |

### Sampling Rate
- **Per task commit:** the quick command for the side touched (pytest subset or `npx vitest run`).
- **Per wave merge:** full suite command.
- **Phase gate:** full suite green, `uv run fgs refresh` succeeds end to end, and the manual 375px/desktop check is done before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `pipeline/tests/test_mood.py`: percentile and hysteresis unit tests plus a real-data sanity check
- [ ] `pipeline/tests/test_export.py`: contract, latest-equals-season-week, partial-week synthetic (reuse `real_cache`; build the teams fixture from `data/cache/teams.parquet` or skip if missing)
- [ ] `pipeline/tests/test_cli.py`: add a refresh-abort test (monkeypatch `fgs.cli.load_schedules`, `load_teams` and `WEB_DATA_DIR`)
- [ ] `web/`: scaffold, then `npm install -D vitest@^5.1.0` and add `"test": "vitest run"`
- [ ] `web/src/lib/router.test.ts`, `web/src/lib/format.test.ts`

## Security Domain

`security_enforcement: false` in `.planning/config.json`, so this section is omitted. (For the record: there's no auth, no user input beyond the hash, and the hash is parsed with a strict regex. Svelte escapes text by default, so data strings render as text. Don't use `{@html}`.)

## Sources

### Primary (HIGH confidence)
- Live runs in this session: `pipeline/data/derived/{games,elo_snapshots}.parquet` analysis (week numbering, percentile, hysteresis, sizes); `nflreadpy.load_teams()` (nflreadpy 0.1.5); `derive()` partial-week mutations; `pytest -q` (74 passed).
- `npm create vite@9.3.4 … --template svelte-ts` scaffold under Node 22.23.3, with `npm install`, `vitest@5.1.0` run, `svelte-check`, and `vite build`.
- npm registry (`npm view`): vite 8.3.8, svelte 5.57.3, @sveltejs/vite-plugin-svelte 7.3.1, svelte-check 4.7.8, vitest 5.1.0 (peers, engines), create-vite 9.3.4.
- Existing code: `pipeline/src/fgs/{cli,snapshots,games,season_config,franchises,ingest,paths}.py`; Phase 1 SUMMARYs and REVIEW-FIX (asof_week, WR-03 week-0 rows, test patterns).

### Secondary (MEDIUM confidence)
- HTML Living Standard behavior: `history.replaceState`/`pushState` don't fire `hashchange` (well-established; not re-fetched this session).

### Tertiary (LOW confidence)
- none

Scratch scripts: `/private/tmp/claude-501/-Users-noahmanion-Dropbox-code-idea-graveyard-feel-good-scorew/e9aca8f6-0367-4770-bd90-f3eef6a0daef/scratchpad/mood_exp.py`, `/private/tmp/claude-501/-Users-noahmanion-Dropbox-code-idea-graveyard-feel-good-scorew/e9aca8f6-0367-4770-bd90-f3eef6a0daef/scratchpad/size_exp.py`, scaffold at `/private/tmp/claude-501/-Users-noahmanion-Dropbox-code-idea-graveyard-feel-good-scorew/e9aca8f6-0367-4770-bd90-f3eef6a0daef/scratchpad/web/`.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. Scaffolded, installed, tested and built in this session.
- Architecture: HIGH. Extends the Phase 1 patterns (pure derive, CLI subcommands, real-cache-skip tests).
- Mood algorithm and sizes: HIGH. Measured on real data.
- Pitfalls: HIGH for the data ones (measured) and MEDIUM for the browser history API (well known, not re-verified).

**Research date:** 2026-11-11
**Valid until:** about 2026-12-11 (frontend versions move fast; the data findings are stable until the 2026 postseason confirms week 19–22 numbering)

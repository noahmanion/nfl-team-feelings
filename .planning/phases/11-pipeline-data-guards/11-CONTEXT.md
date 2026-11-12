# Phase 11: Pipeline Data & Guards - Context

**Gathered:** 2026-11-11
**Status:** Ready for planning
**Mode:** Smart discuss, FULL AUTONOMY. Every grey area was auto-accepted at the recommended answer (no AskUserQuestion). Data sourcing for forfeits and win totals was done during discuss (research agents + independent re-parse), so the plan works from fetched evidence in `sources/`, not from memory.

<domain>
## Phase Boundary

The pipeline exports everything v2's new views need while frozen v1 scores are provably unchanged:
- INTEG-01: a golden test that pins every exported composite score + mood label for seasons <=2025. It lands in the FIRST execution commit and passes at the end.
- DATA-01: every draft-forfeit entry checked against cited, fetched sources; confirmed, corrected or removed; supplemental-draft forfeits labeled separately from penalties.
- DATA-02: 2021-2026 Vegas preseason win totals in committed, sourced files under `pipeline/inputs/`, read only by a display-only module, validated, with a guard that `vegas_expectations` never reads past 2020.
- EXPL-01: per-team-game EPA export (`epa/{season}.json`) + conf/division in meta; web loader + `lib/epa.ts` play-weighted season-to-date aggregation with tests.
- LOGO-01: `fgs logos` one-shot command downloads 32 ESPN logos into `web/public/logos/` (committed); no runtime hotlinking.

Out of bounds: any UI that shows the new data (Phases 12-13), any v2 model code, editing `pipeline/PREREGISTRATION.md` or `PREREGISTRATION_V2.md` (or Part A of the DEVIATIONS file), any change to weights.yaml, refitting anything.

</domain>

<decisions>
## Implementation Decisions

### Area 1: Golden frozen-score test (INTEG-01)
- D-01 Pin = sha256 over the sorted rows `(season, week, franchise, score, label)` for every snapshot row with season <= 2025, plus one hash per season so a failure names the season. Stored in a committed file `pipeline/tests/golden/v1_scores_le2025.json` (`{"overall": ..., "per_season": {...}, "rows": N, "generated_from": "<commit>"}`).
- D-02 Two checks in `pipeline/tests/test_golden_scores.py`:
  (a) Export check, always runs: recompute the hash from the committed `web/public/data/snapshots/{1999..2025}.json` (`weeks[w][i].franchise/score/label`). Fails if any committed export drifts.
  (b) Derive check, uses the real cache (skips cleanly via the existing `real_cache` fixture pattern when the cache is missing): `derive(load_schedules(), **derive_inputs())` -> `mood.score_frame` -> same hash. This catches code changes before an export is written.
- D-03 The pin is generated from the CURRENT HEAD data (before any other phase change) with a tiny helper (`python -m` script or a `--regen` env flag documented in the test docstring, refusing to run unless `FGS_GOLDEN_REGEN=1`). Commit 1 of execution = test + pin file only.
- D-04 Draft is display-only (weights.yaml `offseason.draft.weight: 0.00`, `display_only: true`), so forfeit edits cannot change score/label; the golden test passing after the forfeit change + evidence rerun is the proof. Record the before/after hash in the SUMMARY.

### Area 2: Draft-forfeit audit (DATA-01)
Evidence: `sources/forfeit_audit.json` (every citation is a URL fetched this session, with a quote; Wikipedia per-year draft articles via API + a second independent source for all but 2000 NE).
- D-05 Of the 27 team-round lines (24 keys): 26 confirmed, 1 corrected: `(2017, 4)` NE -> NO (the Deflategate R4 pick NE lost was the one it held from New Orleans via the Brandin Cooks trade; NE's own R4 had been traded and was used; table is keyed by ORIGINAL slot owner). 2004 R2 LV is confirmed but re-labeled supplemental (OAK's pick was traded to HOU, which spent it in the 2003 supplemental draft on Tony Hollings).
- D-06 Missing forfeits found by the audit are ADDED when the nflverse pick data shows the corresponding slot gap (run the draft tests/checks; the alignment DP must not warn for them): 2000 R4 NE (supp), 2001 R3 PIT (penalty), 2002 R3 DEN + SF (penalty), 2003 R6 HOU (supp), 2005 R3 DEN (penalty), 2008 R5 BAL (supp), 2011 R7 DAL (supp), 2012 R6 DET (penalty), 2017 R5 SEA (penalty), 2021 R7 MIN (penalty; replaces the `UNATTRIBUTED_SHORT` (2021,7) entry), 2022 R6 NO (penalty), 2023 R5 HOU (penalty). Entries before FIRST_DRAFT (2000) don't matter for surplus but stay for completeness only if harmless. Any candidate the pick data contradicts is NOT added and is logged in SUMMARY. Do NOT add DEN 2001 R3 (not forfeited) or 2021 LV R6 / NO R7 (rescinded).
- D-07 Label: keep `FORFEITS: dict[(year, round), list[str]]` (callers/tests rely on it) and add `FORFEIT_KIND: dict[tuple[int, int, str], str]` with values `"penalty"` / `"supplemental"`, covering every FORFEITS team exactly (a test asserts the key sets match). Each line keeps a short reason comment plus citation URLs in comments (comment text is ignored by the fingerprint).
- D-08 This is a real correction, so: one deliberate `uv run fgs evidence` rerun AFTER all draft.py edits, commit `callout_evidence.json`, then confirm the golden test still passes and `fgs export` succeeds. Commit the audit JSON with the phase (already in `sources/`).

### Area 3: Display-only win totals (DATA-02)
Evidence: `sources/win_totals_2021_2025.sourced.csv` (160 rows) and `sources/win_totals_2026.sourced.csv` (32 rows); `raw_*.json` and the Covers text hold the page notes.
- D-09 Files (Phase 9 carry-forward honored):
  - `pipeline/inputs/win_totals_2021plus.csv` = 2021-2025 ONLY, written once, in exactly one commit, never edited afterwards (A3.4 pin). Source: Sports Odds History season pages (Wayback snapshots, since covers.com 503s to automation), one page per season. Lines: 2021 BetMGM as of 2021-09-09; 2022 Westgate as of 2022-09-08; 2023 Westgate "Closing odds prior to each teams' first game"; 2024 as of 2024-09-05; 2025 BetMGM as of 2025-09-04. Sums 277.0 / 272.5 / 273.0 / 270.5 / 276.0. Every row matched the raw HTML (line + both odds) by an independent re-parse.
  - `pipeline/inputs/win_totals_display_2026plus.csv` = 2026 (future seasons appended here). 2026 = DraftKings opening lines from the Covers article of 2026-02-19 (`line_type=preseason_open`; no single page with all 32 pre-Week-1 closing lines was reachable). Sum 273.0. A3.6 already says 2026 lines are never a v2 input.
- D-10 Columns exactly: `season,team,line,over_odds,under_odds,source,entered_on,line_type` (A3.2 columns + `line_type`). `line_type` in {`preseason_close`, `preseason_open`}. 2021/22/24/25 are "as of <Week 1 kickoff date>" lines, recorded as `preseason_close`.
- D-11 Module `pipeline/src/fgs/wintotals.py` (NOT added to fingerprint CODE_FILES; it never feeds the score): `load_display_win_totals(inputs_dir=paths.INPUTS_DIR)` reads both files, `validate(df, file_seasons)` raises on: wrong columns; season outside the file's range; != 32 rows or != 32 distinct canonical teams per season (via `RAW_TO_FRANCHISE` + `CANONICAL`); duplicate (season, team); line not a positive multiple of 0.5; season sum outside `reg_games(season) * 16 ± 8` (272 ± 8 for 17-game seasons); source not an absolute `https://` URL; odds not empty-or-int; unknown `line_type`. Add `INPUTS_DIR` to `paths.py`.
- D-12 Guards (tests, plus one runtime assert where it costs nothing): (a) the frame `cli._cached_vegas` returns has max season <= 2020 against the real cache; (b) `vegas_expectations` / `expectations` code paths never reference `inputs/` or `wintotals` (AST/grep test on expectation.py, cli.py derive path, features.py, score.py); (c) `wintotals` is imported only by export (and its tests/cli); (d) `win_totals_2021plus.csv` has exactly one commit in git history when git is available (skip otherwise); (e) end-to-end: derive with vs without the display files gives identical scores (the golden test covers it).
- D-13 Export: team files gain `vegas_win_totals` columnar `{season, line, over_odds, under_odds, line_type, source, used_in_score}`. 2003-2020 rows come from the cached nflverse `win_totals.csv` raw `line` (used_in_score = true, line_type `nflverse`, source = the nflverse URL); 2021+ rows from wintotals.py (used_in_score = false). Display only; no score field reads it.

### Area 4: EPA export (EXPL-01)
- D-14 `epa/{season}.json` for every season with pbp, added as keys in `build_export`'s `files` dict (write_export deletes anything else). Columnar per played team-game: `game_id, week (asof_week), game_type, franchise, opponent, off_epa, off_plays, off_sr, def_epa, def_plays, def_sr`, floats rounded to 4 dp. `def_sr` = the opponent's `off_sr` in the same game (same scrimmage filter). Source = `derived["team_game_epa"]` joined to team_games; reuse the existing `pbp.scrimmage` filters (pass/rush plays, garbage time WP 0.05-0.95 dropped) unchanged. File-level `note` field: "Garbage time (WP outside 5-95%) excluded; not opponent-adjusted." If pbp is absent the export still works (no epa files, meta flag `epa_seasons: []`).
- D-15 `meta.teams[abbr]` gains `conf` and `division` (current alignment from nflverse teams; documented as current, not era-correct). `meta.epa_seasons` lists seasons with an EPA file.
- D-16 Web: `types.ts` EpaFile type; `data.ts` `loadEpa(meta, season)` cached like `loadGames` (keyed by generated_at + season, evicted on failure); `lib/epa.ts` `seasonToDate(file, week)` returns per-franchise `{off_epa, def_epa, off_sr, def_sr, off_plays, def_plays, games}` as play-weighted means (sum(x*plays)/sum(plays)) over rows with `week <= week` (postseason included when the week is past the regular season), with `epa.test.ts` covering weighting, the week cutoff, missing teams and zero plays. No UI.

### Area 5: Logos (LOGO-01)
- D-17 `fgs logos [--force]` subcommand, NOT called by `refresh`. Module `pipeline/src/fgs/logos.py`: URL `https://a.espncdn.com/i/teamlogos/nfl/500/{code}.png` with code = franchise lowercased, mapped `LA->lar`, `WAS->wsh`. Never `team_logo_wikipedia`. Writes `web/public/logos/{FRANCHISE}.png` atomically (tmp + replace), validates the PNG signature and size > 1 KB, skips existing files unless `--force`, and writes `web/public/logos/manifest.json` (franchise -> source URL, sha256, bytes, fetched date). Run once; commit the 32 PNGs + manifest.
- D-18 Tests: mocked downloads (no network) for mapping, validation and skip/force; a web-side test (or pipeline test) asserts `web/src` contains no `espncdn`/`wikipedia` logo URLs; a test that all 32 committed logo files exist when the directory is present.

### Area 6: Execution order & verification
- D-19 Order: (1) golden test + pin commit; (2) forfeits + kind labels + evidence rerun; (3) win totals files (2021plus file in its own single commit) + wintotals.py + guards; (4) EPA export + meta + web loader/lib; (5) logos command + downloaded logos; (6) `uv run fgs export`, commit regenerated `web/public/data`; full `uv run pytest`, and in web/ (`source ~/.nvm/nvm.sh && nvm use 24`) `npm test`, `npm run check`, `npm run build`.
- D-20 Regenerate site data with `uv run fgs export` (cache only, no network). No pbp re-pull (Pitfall: frozen-score drift).

### Claude's Discretion
- Exact helper/function names, rounding precision beyond the stated 4 dp, test file split, how the golden regen helper is invoked.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `export.build_export` / `write_export` (`files` dict is the whole contract; write_export owns `web/public/data/`).
- `pbp.team_game_epa` already yields `off_epa, off_plays, off_sr, def_epa, def_plays` per (game_id, franchise_id); `derived["team_game_epa"]` carries it into the export.
- `expectation.load_win_totals` / `vegas_expectations` (nflverse 2003-2020; must stay untouched in behavior); `cli._cached_vegas`.
- `franchises.RAW_TO_FRANCHISE`, `CANONICAL`; `season_config.reg_games`.
- teams cache has `team_conf`, `team_division`, `team_logo_espn`.
- tests/conftest: `real_cache`, `derive_inputs()`, session sim cache fixture.
- web/src/lib/data.ts cache pattern (`loadGames`).

### Established Patterns
- Fingerprint (`fingerprint.CODE_FILES` incl. draft.py, expectation.py) hashes AST, so comments are free but code edits force `fgs evidence`.
- Light process: pytest + vitest, no CI.
- Atomic writes (tmp + os.replace).

### Integration Points
- `cli.main` subparsers (add `logos`); `paths.py` (INPUTS_DIR, LOGOS_DIR).
- `export.team_meta` (conf/division), team files (vegas_win_totals), new `epa/` files.

</code_context>

<specifics>
## Specific Ideas

- Never fabricate data. All numbers come from `sources/` evidence; the 2026 line type is honestly `preseason_open`.
- Forfeit citations as comments; the audit JSON is the full evidence record.

</specifics>

<deferred>
## Deferred Ideas

- 2026 pre-Week-1 closing lines (only the February DraftKings opener was reachable; covers.com 503s to automation). Could replace/augment later in the display-only 2026plus file.
- Era-correct conference/division alignment (meta carries current alignment only).
- Win-totals and EPA UI (Phase 13).

</deferred>

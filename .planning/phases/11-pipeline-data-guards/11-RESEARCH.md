# Phase 11: Pipeline Data & Guards - Research

**Researched:** 2026-11-11
**Domain:** Integrating code into the existing `fgs` pipeline (Python 3.13 / Polars) and the Svelte web loader. No new libraries.
**Confidence:** HIGH. Every claim below was checked by reading the code or by running read-only probes against `pipeline/data/cache` at HEAD `97e1f33`.

## Summary

All five requirements fit the existing seams. No new dependencies are needed: `urllib`, `hashlib`, `subprocess` and `ast` from the stdlib, plus Polars, cover everything. The main risks are ordering and fingerprint risks, not technical ones.

**Golden test:** feasible and cheap. Two hashes were computed over sorted `(season, week, franchise, score, label)` rows for seasons ≤2025: one from the committed `web/public/data/snapshots/{1999..2025}.json` and one from a fresh `derive(load_schedules(), **cli.cached_inputs(), sim_cache_dir=tmp)` → `mood.score_frame`. Both cover **19,102 rows** and are **identical** (hash prefix `3ac3c2b58d0bfecf` in the probe's line format). A cold derive takes about 10 s (the simulator). With a warm sim cache it takes under 1 s.

**Forfeits:** the D-06 rule "the alignment DP must not warn" is **vacuous for every candidate**. All 13 additions are in rounds 3-7, where compensatory picks pad the pick count, so the DP never warns whether or not the forfeit is real. A positional test does discriminate: delete the candidate's slot from the derived original order and count the change in exact owner matches. The three "should NOT be added" controls show zero or negative gain, so the test works. Results:

| Status | Candidates |
|--------|------------|
| Supported, add | 2017 R4 NE→NO, 2003 R6 HOU, 2008 R5 BAL, 2011 R7 DAL, 2012 R6 DET, 2017 R5 SEA, 2021 R7 MIN, 2023 R5 HOU |
| Weakly supported, add | 2022 R6 NO |
| Not shown, do not add | 2000 R4 NE, 2002 R3 SF, 2005 R3 DEN |
| Leans against, do not add | 2001 R3 PIT, 2002 R3 DEN |

Adding the five unsupported candidates would turn real regular picks into "comp" picks and charge uninvolved teams up to 7.1 points (for example, 2002 DAL −7.1 and 2001 DAL −5.7).

**Primary recommendation:**
1. Commit the golden test first. Hash the committed export and re-derive.
2. Apply the 9 supported forfeit changes, add `FORFEIT_KIND`, update 2 draft tests, then run `fgs evidence` exactly once. The evidence numbers don't change; only `code_fingerprint` does.
3. Keep all win-totals code out of `fingerprint.CODE_FILES` and out of `cli.derive_games`. Wire the display data through a new `build_export(..., win_totals=...)` keyword that both `_cmd_export` and `_cmd_refresh` pass.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Area 1: Golden frozen-score test (INTEG-01)
- D-01 Pin = sha256 over the sorted rows `(season, week, franchise, score, label)` for every snapshot row with season <= 2025, plus one hash per season so a failure names the season. Stored in a committed file `pipeline/tests/golden/v1_scores_le2025.json` (`{"overall": ..., "per_season": {...}, "rows": N, "generated_from": "<commit>"}`).
- D-02 Two checks in `pipeline/tests/test_golden_scores.py`:
  (a) Export check, always runs: recompute the hash from the committed `web/public/data/snapshots/{1999..2025}.json` (`weeks[w][i].franchise/score/label`). Fails if any committed export drifts.
  (b) Derive check, uses the real cache (skips cleanly via the existing `real_cache` fixture pattern when the cache is missing): `derive(load_schedules(), **derive_inputs())` -> `mood.score_frame` -> same hash. This catches code changes before an export is written.
- D-03 The pin is generated from the CURRENT HEAD data (before any other phase change) with a tiny helper (`python -m` script or a `--regen` env flag documented in the test docstring, refusing to run unless `FGS_GOLDEN_REGEN=1`). Commit 1 of execution = test + pin file only.
- D-04 Draft is display-only (weights.yaml `offseason.draft.weight: 0.00`, `display_only: true`), so forfeit edits cannot change score/label; the golden test passing after the forfeit change + evidence rerun is the proof. Record the before/after hash in the SUMMARY.

#### Area 2: Draft-forfeit audit (DATA-01)
Evidence: `sources/forfeit_audit.json` (every citation is a URL fetched this session, with a quote; Wikipedia per-year draft articles via API + a second independent source for all but 2000 NE).
- D-05 Of the 27 team-round lines (24 keys): 26 confirmed, 1 corrected: `(2017, 4)` NE -> NO (the Deflategate R4 pick NE lost was the one it held from New Orleans via the Brandin Cooks trade; NE's own R4 had been traded and was used; table is keyed by ORIGINAL slot owner). 2004 R2 LV is confirmed but re-labeled supplemental (OAK's pick was traded to HOU, which spent it in the 2003 supplemental draft on Tony Hollings).
- D-06 Missing forfeits found by the audit are ADDED when the nflverse pick data shows the corresponding slot gap (run the draft tests/checks; the alignment DP must not warn for them): 2000 R4 NE (supp), 2001 R3 PIT (penalty), 2002 R3 DEN + SF (penalty), 2003 R6 HOU (supp), 2005 R3 DEN (penalty), 2008 R5 BAL (supp), 2011 R7 DAL (supp), 2012 R6 DET (penalty), 2017 R5 SEA (penalty), 2021 R7 MIN (penalty; replaces the `UNATTRIBUTED_SHORT` (2021,7) entry), 2022 R6 NO (penalty), 2023 R5 HOU (penalty). Entries before FIRST_DRAFT (2000) don't matter for surplus but stay for completeness only if harmless. Any candidate the pick data contradicts is NOT added and is logged in SUMMARY. Do NOT add DEN 2001 R3 (not forfeited) or 2021 LV R6 / NO R7 (rescinded).
- D-07 Label: keep `FORFEITS: dict[(year, round), list[str]]` (callers/tests rely on it) and add `FORFEIT_KIND: dict[tuple[int, int, str], str]` with values `"penalty"` / `"supplemental"`, covering every FORFEITS team exactly (a test asserts the key sets match). Each line keeps a short reason comment plus citation URLs in comments (comment text is ignored by the fingerprint).
- D-08 This is a real correction, so: one deliberate `uv run fgs evidence` rerun AFTER all draft.py edits, commit `callout_evidence.json`, then confirm the golden test still passes and `fgs export` succeeds. Commit the audit JSON with the phase (already in `sources/`).

#### Area 3: Display-only win totals (DATA-02)
Evidence: `sources/win_totals_2021_2025.sourced.csv` (160 rows) and `sources/win_totals_2026.sourced.csv` (32 rows); `raw_*.json` and the Covers text hold the page notes.
- D-09 Files (Phase 9 carry-forward honored):
  - `pipeline/inputs/win_totals_2021plus.csv` = 2021-2025 ONLY, written once, in exactly one commit, never edited afterwards (A3.4 pin). Source: Sports Odds History season pages (Wayback snapshots, since covers.com 503s to automation), one page per season. Lines: 2021 BetMGM as of 2021-09-09; 2022 Westgate as of 2022-09-08; 2023 Westgate "Closing odds prior to each teams' first game"; 2024 as of 2024-09-05; 2025 BetMGM as of 2025-09-04. Sums 277.0 / 272.5 / 273.0 / 270.5 / 276.0. Every row matched the raw HTML (line + both odds) by an independent re-parse.
  - `pipeline/inputs/win_totals_display_2026plus.csv` = 2026 (future seasons appended here). 2026 = DraftKings opening lines from the Covers article of 2026-02-19 (`line_type=preseason_open`; no single page with all 32 pre-Week-1 closing lines was reachable). Sum 273.0. A3.6 already says 2026 lines are never a v2 input.
- D-10 Columns exactly: `season,team,line,over_odds,under_odds,source,entered_on,line_type` (A3.2 columns + `line_type`). `line_type` in {`preseason_close`, `preseason_open`}. 2021/22/24/25 are "as of <Week 1 kickoff date>" lines, recorded as `preseason_close`.
- D-11 Module `pipeline/src/fgs/wintotals.py` (NOT added to fingerprint CODE_FILES; it never feeds the score): `load_display_win_totals(inputs_dir=paths.INPUTS_DIR)` reads both files, `validate(df, file_seasons)` raises on: wrong columns; season outside the file's range; != 32 rows or != 32 distinct canonical teams per season (via `RAW_TO_FRANCHISE` + `CANONICAL`); duplicate (season, team); line not a positive multiple of 0.5; season sum outside `reg_games(season) * 16 ± 8` (272 ± 8 for 17-game seasons); source not an absolute `https://` URL; odds not empty-or-int; unknown `line_type`. Add `INPUTS_DIR` to `paths.py`.
- D-12 Guards (tests, plus one runtime assert where it costs nothing): (a) the frame `cli._cached_vegas` returns has max season <= 2020 against the real cache; (b) `vegas_expectations` / `expectations` code paths never reference `inputs/` or `wintotals` (AST/grep test on expectation.py, cli.py derive path, features.py, score.py); (c) `wintotals` is imported only by export (and its tests/cli); (d) `win_totals_2021plus.csv` has exactly one commit in git history when git is available (skip otherwise); (e) end-to-end: derive with vs without the display files gives identical scores (the golden test covers it).
- D-13 Export: team files gain `vegas_win_totals` columnar `{season, line, over_odds, under_odds, line_type, source, used_in_score}`. 2003-2020 rows come from the cached nflverse `win_totals.csv` raw `line` (used_in_score = true, line_type `nflverse`, source = the nflverse URL); 2021+ rows from wintotals.py (used_in_score = false). Display only; no score field reads it.

#### Area 4: EPA export (EXPL-01)
- D-14 `epa/{season}.json` for every season with pbp, added as keys in `build_export`'s `files` dict (write_export deletes anything else). Columnar per played team-game: `game_id, week (asof_week), game_type, franchise, opponent, off_epa, off_plays, off_sr, def_epa, def_plays, def_sr`, floats rounded to 4 dp. `def_sr` = the opponent's `off_sr` in the same game (same scrimmage filter). Source = `derived["team_game_epa"]` joined to team_games; reuse the existing `pbp.scrimmage` filters (pass/rush plays, garbage time WP 0.05-0.95 dropped) unchanged. File-level `note` field: "Garbage time (WP outside 5-95%) excluded; not opponent-adjusted." If pbp is absent the export still works (no epa files, meta flag `epa_seasons: []`).
- D-15 `meta.teams[abbr]` gains `conf` and `division` (current alignment from nflverse teams; documented as current, not era-correct). `meta.epa_seasons` lists seasons with an EPA file.
- D-16 Web: `types.ts` EpaFile type; `data.ts` `loadEpa(meta, season)` cached like `loadGames` (keyed by generated_at + season, evicted on failure); `lib/epa.ts` `seasonToDate(file, week)` returns per-franchise `{off_epa, def_epa, off_sr, def_sr, off_plays, def_plays, games}` as play-weighted means (sum(x*plays)/sum(plays)) over rows with `week <= week` (postseason included when the week is past the regular season), with `epa.test.ts` covering weighting, the week cutoff, missing teams and zero plays. No UI.

#### Area 5: Logos (LOGO-01)
- D-17 `fgs logos [--force]` subcommand, NOT called by `refresh`. Module `pipeline/src/fgs/logos.py`: URL `https://a.espncdn.com/i/teamlogos/nfl/500/{code}.png` with code = franchise lowercased, mapped `LA->lar`, `WAS->wsh`. Never `team_logo_wikipedia`. Writes `web/public/logos/{FRANCHISE}.png` atomically (tmp + replace), validates the PNG signature and size > 1 KB, skips existing files unless `--force`, and writes `web/public/logos/manifest.json` (franchise -> source URL, sha256, bytes, fetched date). Run once; commit the 32 PNGs + manifest.
- D-18 Tests: mocked downloads (no network) for mapping, validation and skip/force; a web-side test (or pipeline test) asserts `web/src` contains no `espncdn`/`wikipedia` logo URLs; a test that all 32 committed logo files exist when the directory is present.

#### Area 6: Execution order & verification
- D-19 Order: (1) golden test + pin commit; (2) forfeits + kind labels + evidence rerun; (3) win totals files (2021plus file in its own single commit) + wintotals.py + guards; (4) EPA export + meta + web loader/lib; (5) logos command + downloaded logos; (6) `uv run fgs export`, commit regenerated `web/public/data`; full `uv run pytest`, and in web/ (`source ~/.nvm/nvm.sh && nvm use 24`) `npm test`, `npm run check`, `npm run build`.
- D-20 Regenerate site data with `uv run fgs export` (cache only, no network). No pbp re-pull (Pitfall: frozen-score drift).

### Claude's Discretion
- Exact helper/function names, rounding precision beyond the stated 4 dp, test file split, how the golden regen helper is invoked.

### Deferred Ideas (OUT OF SCOPE)
- 2026 pre-Week-1 closing lines (only the February DraftKings opener was reachable; covers.com 503s to automation). Could replace/augment later in the display-only 2026plus file.
- Era-correct conference/division alignment (meta carries current alignment only).
- Win-totals and EPA UI (Phase 13).

Out of bounds: any UI that shows the new data (Phases 12-13), any v2 model code, editing `pipeline/PREREGISTRATION.md` or `PREREGISTRATION_V2.md` (or Part A of the DEVIATIONS file), any change to weights.yaml, refitting anything.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INTEG-01 | A golden hash of every exported score and label for seasons ≤2025 | The export and a fresh derive agree on all 19,102 rows. The hash format, runtimes and fixture reuse are covered below. |
| DATA-01 | Every forfeit entry is checked against a cited source and labeled supplemental vs penalty | Per-candidate pick-data verdicts, surplus deltas, the 2 tests that must change, and the fingerprint/evidence rerun |
| DATA-02 | 2021-2026 win totals in sourced `pipeline/inputs/` files, display-only, with a guard | The sourced CSVs already pass every D-11 rule (checked). `_cached_vegas` max season is 2020. Export wiring path and guard-test designs are below. |
| EXPL-01 | Per-team EPA export plus a web play-weighted season-to-date helper | `team_game_epa` schema checked. `def_sr` join checked (0 nulls; `def_epa`/`def_plays` equal the opponent's offense exactly). Each season's file is about 40 KB. |
| LOGO-01 | 32 logos downloaded once into `web/public/logos/` | All 32 ESPN URLs return 200 `image/png`, 7.5-131 KB each, about 1.7 MB total. Wrong codes **also return 200**, so the mapping test matters. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Work only inside `feel-good-scorew/`. Don't share dependencies. Keep process light: no CI. pytest + vitest only.
- Stack: Python 3.13 + uv + Polars in `pipeline/`; Vite 8 + Svelte 5 + TypeScript ~6.0 in `web/`. Don't bump to TS 7.
- Free data only (nflverse primary). ESPN CDN logos are fetched once and committed, so there's no hotlinking.
- Go through the GSD workflow (`/gsd-execute-phase`) for edits.
- Memory: web needs Node 22/24 (`source ~/.nvm/nvm.sh && nvm use 24`; the nvm default is 20). The user wants full autonomy and short status answers.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Golden score pin | Pipeline tests | Committed export JSON | It hashes artifacts, so no runtime code is involved |
| Forfeit table + kinds | Pipeline (`draft.py`) | `callout_evidence.json` (fingerprint) | Display-only surplus; the AST fingerprint covers `draft.py` |
| Win totals (2021+) | Pipeline (`wintotals.py`, `inputs/`) | Export team files | Display-only. It must never touch derive or features |
| EPA per team-game | Pipeline export (`export.py`) | Web `lib/epa.ts` (aggregation) | The pipeline ships per-game data and the browser aggregates per week |
| conf/division | Pipeline export (`team_meta`) | Web `types.ts` | Read from the nflverse teams cache |
| Logos | Pipeline one-shot CLI (`logos.py`) | Static `web/public/logos/` | Fetched at build/dev time only; served as static assets |

## Standard Stack

No new packages. Everything uses what's already locked in `pipeline/uv.lock` and `web/package-lock.json`.

| Need | Use | Verified |
|------|-----|----------|
| Hashing | `hashlib.sha256` | stdlib |
| HTTP download (logos) | `urllib.request.urlopen` (same as `draft.load_draft_values` / `expectation.load_win_totals`) | ESPN accepts the `Python-urllib/3.13` UA (200, checked with curl -A) |
| CSV read/validate | `polars.read_csv(path, infer_schema_length=0)` (all strings, then cast) | Used in the probe |
| Git commit count | `subprocess.run(["git", ...])` (same pattern as `holdout.git_state` / `tests/test_holdout.py::_git`) | Git root = `feel-good-scorew/` (own `.git`, not shallow) |
| Static source scan (web) | `import.meta.glob('../**/*.{ts,svelte}', {query:'?raw', import:'default', eager:true})` (pattern from `src/lib/sep.test.ts`) | vitest 5.1, uses `vite.config.ts` (no separate vitest config) |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed in this phase, so slopcheck was not needed. **Packages removed:** none. **Flagged:** none.

## Architecture Patterns

### Data flow (after the phase)

```
nflverse cache (schedules, pbp/*.parquet, win_totals.csv 2003-2020, draft_picks, teams)
   │
   ├─► cli.cached_inputs() ──► derive_games() ──► features/score ──► mood.score_frame ──► snapshots (score, label)
   │      (pbp_games, vegas≤2020, draft)            ▲ never sees inputs/ (guard D-12b)          │
   │                                                │                                           ▼
   │                             draft.FORFEITS ──► draft.surplus_table (display only, weight 0) ─► week-0 draft block
   │
   ├─► win_totals.csv (raw lines 2003-2020) ─┐
pipeline/inputs/*.csv ─► wintotals.load+validate ─┴─► cli builds `win_totals` frame ─► build_export(win_totals=…) ─► teams/{F}.json.vegas_win_totals
   │
   ├─► derived["team_game_epa"] ⋈ team_games ⋈ opponent off_sr ─► epa/{season}.json ─► web loadEpa ─► lib/epa.seasonToDate(week)
   └─► teams.parquet team_conf/team_division ─► meta.teams[abbr].conf/division

fgs logos (manual, once) ─► ESPN CDN ─► web/public/logos/{F}.png + manifest.json ─► Vite copies to dist/logos

Golden test: committed snapshots/{1999..2025}.json ─┐
             fresh derive → score_frame (≤2025) ────┴─► sha256 == tests/golden/v1_scores_le2025.json
```

### New/changed files

```
pipeline/
├── inputs/win_totals_2021plus.csv            # NEW, single commit, copy of sources/win_totals_2021_2025.sourced.csv
├── inputs/win_totals_display_2026plus.csv    # NEW, copy of sources/win_totals_2026.sourced.csv
├── src/fgs/paths.py                          # + INPUTS_DIR, LOGOS_DIR (paths.py is NOT in fingerprint)
├── src/fgs/draft.py                          # FORFEITS edits, FORFEIT_KIND, UNATTRIBUTED_SHORT -> set()  (fingerprinted!)
├── src/fgs/wintotals.py                      # NEW (not fingerprinted)
├── src/fgs/logos.py                          # NEW
├── src/fgs/export.py                         # team_meta conf/division, epa files, meta.epa_seasons, vegas_win_totals
├── src/fgs/cli.py                            # `logos` subparser; win_totals frame passed to build_export in _cmd_export AND _cmd_refresh
└── tests/
    ├── golden/v1_scores_le2025.json          # NEW pin
    ├── test_golden_scores.py                 # NEW
    ├── test_wintotals.py                     # NEW (validator + guards a-d)
    ├── test_logos.py                         # NEW (mocked)
    ├── test_draft.py                         # 2 assertions updated + FORFEIT_KIND tests
    └── test_export.py                        # META_KEYS + epa/conf/vegas_win_totals contract
web/
├── public/logos/{32}.png + manifest.json     # NEW (committed; ~1.7 MB)
└── src/lib/{types.ts, data.ts, epa.ts, epa.test.ts, nohotlink.test.ts}
```

### Pattern 1: Golden hash (verified format)

```python
# Source: probe run against HEAD 97e1f33 (export rows == derive rows == 19,102)
import hashlib, json
from pathlib import Path

def canon(rows):  # rows: iterable of (season:int, week:int, franchise:str, score:int, label:str)
    return "\n".join(f"{s},{w},{f},{sc},{lb}" for s, w, f, sc, lb in sorted(rows)).encode("utf-8")

def export_rows(web_data: Path, last=2025):
    for p in sorted((web_data / "snapshots").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d["season"] > last:
            continue
        for w, lst in d["weeks"].items():
            for r in lst:
                yield d["season"], int(w), r["franchise"], int(r["score"]), r["label"]

def derive_rows(scored, last=2025):  # scored = mood.score_frame(derived["features"])
    s = scored.filter(pl.col("season") <= last).select("season", "week", "franchise_id", "score", "label")
    return ((int(a), int(b), c, int(d), e) for a, b, c, d, e in s.iter_rows())
```

- The `(season, week, franchise)` triple is unique, so sorting the tuples is deterministic. Labels include `It’s fine. Everything’s fine.` with a curly apostrophe, so always encode UTF-8.
- Per-season hashes: group the sorted rows by season and hash each group in the same format. Rows per season: 682 for 1999-2001 (31 teams × 22 weeks).
- Regen: guard on `os.environ.get("FGS_GOLDEN_REGEN") == "1"`. Write the pin from the **export** rows and also assert that derive matches before writing. Get `generated_from` from `git rev-parse --short HEAD`.
- Derive check: reuse `conftest.derive_inputs()` (the session sim cache via the autouse `sim_cache_dir` fixture) and `real_cache`. If the golden test runs first in the session it pays the cold sim (about 10 s). Otherwise the cost is about 0.2 s.

### Pattern 2: Forfeit additions (pick-data verdicts)

**Method.** The DP warning can't discriminate in rounds 3-7: comp picks make `len(act) >= len(o)`, so the warning never fires. Use this test instead:
1. Take the derived original order with the existing forfeits removed.
2. Count exact owner matches under `draft.align`.
3. Delete the candidate's slot and count again.
4. Rank the candidate's deletion against deleting every other slot in the round.

Scripts are in the session scratchpad. They can be recreated from the table below.

| Candidate | Matches without → with deletion | Rank of candidate among 31-32 deletions | Verdict | Surplus effect of adding (vs current) |
|-----------|-------------------|---------------------|---------|---------------|
| 2017 R4 **NO** (replacing NE) | NE-deleted 3 → NO-deleted 7 | 1 | **Supported (correct D-05)** | 10 teams ±0.1 |
| 2003 R6 HOU (supp) | 5 → 9 | 2 | **Supported** | TB −0.7, others ±0.1 |
| 2008 R5 BAL (supp) | 1 → 10 | 1 (tie) | **Supported** | LAC −2.0 (pick 166 becomes trailing comp), others ±0.1 |
| 2011 R7 DAL (supp) | 5 → 14 | 1 | **Supported** | ±0.1 only |
| 2012 R6 DET (penalty) | 12 → 17 | 1 | **Supported** | NYJ −0.8 |
| 2017 R5 SEA (penalty) | 14 → 16 | 1 (tie) | **Supported** | CIN −1.7 |
| 2021 R7 MIN (penalty; replaces UNATTRIBUTED_SHORT) | Round is short (31 picks/32 slots). The best forced deletion is MIN's slot (12). The NO slot would give 6 | 1 | **Supported**. No warning with `UNATTRIBUTED_SHORT = set()` | **No surplus change** (late-R7 stuart value is 0.0) |
| 2023 R5 HOU (penalty) | 1 → 14 | 1 (tie) | **Supported** | HOU −2.0 |
| 2022 R6 NO (penalty) | 6 → 7 | 3 | **Weakly supported (not contradicted)**. Add | LA −0.6 |
| 2000 R4 NE (supp) | 13 → 12 | 4 | **Not shown**. No deletion anywhere in this round gains | CHI −3.9 if added |
| 2002 R3 SF (penalty) | 11 → 11 | 11 | **Not shown** | BUF −5.5 (with DEN) if added |
| 2005 R3 DEN (penalty) | 11 → 11 | 2 (best possible +1) | **Not shown** | TEN −5.5 if added |
| 2001 R3 PIT (penalty) | 12 → 10 | 24 of 31 | **Leans against** | DAL −5.7 if added |
| 2002 R3 DEN (penalty) | 11 → 9 | 29 of 32 | **Leans against** | DAL −7.1 (with SF) if added |
| Control: 2001 R3 DEN (not forfeited) | 12 → 12 | — | No gain, as expected | — |
| Control: 2021 R6 LV (rescinded) | 15 → 15 | — | No gain, as expected | — |
| Control: 2021 R7 NO (rescinded) | 12 → 6 | 28 | Strongly against, as expected | — |

**Recommendation (D-06 rule "added when the pick data shows the gap"):**
- Add the 8 supported changes plus 2022 R6 NO.
- Do **not** add 2000 R4 NE, 2001 R3 PIT, 2002 R3 DEN/SF or 2005 R3 DEN. Log them in the SUMMARY as "sourced, but the nflverse pick data does not show the slot gap: the 2000-2005 derived order is too noisy (best deletion gain in those rounds is 0 to +2), and adding them would reclassify a real regular pick as compensatory and charge an uninvolved team 3.9-7.1 points".
- Optionally keep them as a **comment block** in draft.py with citations. Comments are fingerprint-free.

**Combined effect of the recommended set** (checked):
- No warnings.
- Winsor bounds stay exactly `(-17.29, 16.19)`, the frozen weights.yaml value.
- Slot Spearman −0.063.
- Every draft sums to ≤ 0.
- Known-trade assertions are unchanged (2020 MIA 39.8, 2018 CLE 37.9, 2012 LV −38.5, 2022 LA −29.6, 2020 CIN 0.0).
- `check_draft_sum`/`check_draft_coverage` stay clean.
- 62 team-draft rows change, max |Δ| 2.0, in drafts 2003/2008/2011/2012/2017/2022/2023.

**Tests that assert specific FORFEITS contents** (in `tests/test_draft.py`). With the patched table, all other real-data draft tests pass:
- `test_forfeit_2017_r4_ne_and_regular_picks_kept`: `gone == ["NE"]` → `["NO"]`. Its other asserts still hold: 31 regular picks, `{"BUF","MIA"}` among the owners, and pick 138 regular. Rename the test to `..._no_...`.
- `test_forfeit_2008_r5_is_sf_not_kc_lv`: `gone == ["SF"]` → `["SF", "BAL"]` and `len(regular) == 31` → `30`. KC/LV are still in the owners; SF and BAL are not.
- The other draft tests stay green (checked): `test_no_unknown_short_rounds_real`, `test_winsor_real`, the acceptance tests and `test_forfeit_2016_r5_atl_la`. `test_surplus_unknown_short_round_warns_and_charges_nobody` passes explicit `unattributed=`, so it's unaffected.
- New: `set(FORFEIT_KIND) == {(y, r, t) for (y, r), ts in FORFEITS.items() for t in ts}` and every value is in `{"penalty", "supplemental"}`.

**Display-only proof:**
- `weights.yaml` has `offseason.draft.weight: 0.00, display_only: true`.
- `score.apply_offseason` returns before touching `composite` when `offseason_live(cfg)` is False.
- `mood.reference_values` uses `composite_inseason`.
- So score and label can't move, and the golden test proves it.

The week-0 `draft` block (surplus/z/rank/text) changes in the snapshot files for 2003, 2008, 2011, 2012, 2017, 2022 and 2023. That's expected and is not part of the golden hash.

**Fingerprint:**
- `fingerprint.CODE_FILES` includes `draft.py`, so any non-comment edit (FORFEITS, FORFEIT_KIND, UNATTRIBUTED_SHORT) changes `code_fingerprint` (currently `6e1958f91b8a`, matching the committed `callout_evidence.json`).
- `build_export` → `_load_evidence` then raises "callout_evidence.json is stale". Every real-data export test (`test_export.py` real_files, `test_cli` export/refresh) fails until `uv run fgs evidence` runs.
- `evidence.py`/`insights.py` don't use draft data, so the hopeful/worried numbers stay identical and only `code_fingerprint` and `generated_at` change.
- **Run `fgs evidence` immediately after the draft.py edits, in the same plan, before the full pytest.**

### Pattern 3: Display win totals without touching expectations

Where the Vegas data flows today:
- `cli.cached_inputs()` → `_cached_vegas(cache_dir)` → `vegas_expectations(pl.read_csv(cache/win_totals.csv))`. That gives columns `season, franchise_id, vegas_line, vegas_norm`, 2003-2020, with OAK/SD/STL mapped.
- That frame → `derive(..., vegas=)` → `derive_games` → `features.build_features(vegas=)` → `features._sim_columns` → `expectation.expectations(sim, vegas)` → `exp_total`/`vs_exp`.
- It's also used by `checks.check_vegas_coverage` (`VEGAS_SEASONS = (2003, 2020)`) and `backtest._sealed_sim`.

Fingerprint map:
- **Fingerprinted** (changing them forces `fgs evidence`): `expectation.py`, `features.py`, `score.py`, `cli.derive_games`, `cli.draft_winsor`.
- **Not fingerprinted:** `paths.py`, `export.py`, `cli._cached_vegas`, `cli.cached_inputs`, `cli._cmd_export`, `cli._cmd_refresh`, `pbp.py`, `wintotals.py`, `logos.py`.

**Put the D-12 runtime assert in `cli._cached_vegas`** (for example, `assert int(v["season"].max()) <= 2020`, or better a `ValueError`, which survives `-O`, as `export._export_weights` does). Do not put it in `expectation.py`: that would change the fingerprint again after the evidence rerun.

**Export wiring (recommended):**
- Add `build_export(derived, teams_df, generated_at, *, evidence=None, win_totals: pl.DataFrame | None = None)`. Keep `build_export` pure.
- The CLI builds `win_totals` with a helper, for example `wintotals.display_frame(nflverse_raw_df, display_df)`, which returns rows `franchise_id, season, line, over_odds, under_odds, line_type, source, used_in_score`.
- 2003-2020 come from the **raw cached CSV** `pl.read_csv(cache/"win_totals.csv")`. Map `team` via `RAW_TO_FRANCHISE`. Use `line_type="nflverse"`, `source=expectation.WIN_TOTALS_URL` (import the constant, don't duplicate it) and `used_in_score=True`. The cached CSV has `season,team,line,over_odds,under_odds` (all Int64/Float64 with 0 nulls, 576 rows). Don't use `derived["vegas"]`: it has no odds.
- 2021+ come from `load_display_win_totals()` with `used_in_score=False`.
- **Both** `_cmd_export` and `_cmd_refresh` call `build_export`. Pass `win_totals=` in both, with one shared helper such as `cli._display_win_totals(cache_dir)`. If either path is missed, a refresh silently drops the field.
- When `win_totals` is None (tests, missing cache), emit an empty columnar dict so the team-file shape stays stable.
- For D-12(c): with this wiring, `export.py` doesn't need to import `wintotals` at all. The allowed importers are `cli.py`, `export.py` and `tests/test_wintotals.py`.

**Guard tests (D-12):**
- (a) Real cache: `v = cli._cached_vegas(CACHE_DIR)`; assert `v is not None and v["season"].max() <= 2020`. Currently 2003-2020. Skip if `win_totals.csv` isn't cached.
- (b) Source scan:
  - Whole-file text of `expectation.py`, `features.py` and `score.py`, with comments stripped like `test_leakage`.
  - For `cli.py`, extract the function sources `derive_games`, `derive`, `cached_inputs` and `_cached_vegas` with `ast.get_source_segment`.
  - Assert none contains `wintotals`, `inputs` or `INPUTS_DIR`. Careful: the word "inputs" appears in the `cached_inputs` function name itself. Match `INPUTS_DIR`, `"inputs/"`, `wintotals` and `win_totals_2021plus`/`display_2026plus`, not the bare word.
- (c) Use the regex `^\s*(from|import)\s+[\w., ]*wintotals` over every `src/fgs/*.py`. The only allowed hits are `cli.py`, `export.py` and `wintotals.py` (`test_leakage.test_backtest_not_imported_upstream` pattern).
- (d) Git, from `paths.PIPELINE_ROOT.parent` (the git root):
  - Skip when `git` is missing, the directory isn't a work tree, or `git rev-parse --is-shallow-repository` is true.
  - Count `git log --format=%H -- pipeline/inputs/win_totals_2021plus.csv`.
  - Assert `n == 1` and `git status --porcelain -- <file>` is empty.
  - Practical note: before the file's commit exists, n == 0. Have the test **skip** on 0 ("not committed yet") so the executor can run tests before committing. Otherwise the plan must commit the CSV alone *before* running pytest. With either choice, the CSV must be in its own commit (D-19).
- (e) Covered by the golden derive check, since derive never receives the display files. Optionally add an explicit test that calls `derive` twice and compares `score_frame`. That's redundant with golden; skip it to keep process light.

**Validator facts:**
- Both sourced CSVs already pass every D-11 rule (checked):
  - 2021-2025 sums are 277.0/272.5/273.0/270.5/276.0 and 2026 is 273.0, all inside 272±8.
  - 32 canonical teams per season, no duplicates, all lines multiples of 0.5 (min 4.0, max 12.5).
  - All sources are `https://`, all odds are non-empty ints, `entered_on` is `2026-11-11`, and the line types are `preseason_close` and `preseason_open`.
- **Do not** apply the sum rule to nflverse 2003-2020. 2003 sums to 265.5, which falls outside 16×16±8 = [248, 264].
- Read with `infer_schema_length=0` (all strings), then validate and cast. Otherwise Polars may parse `100` odds as i64 and empty odds as null inconsistently.

### Pattern 4: EPA export (verified schema)

`derived["team_game_epa"]` (= `pbp.team_game_epa`) schema: `game_id str, season i32, franchise_id str, off_epa f64, off_plays i64, off_sr f64, def_epa f64, def_plays i64, net_epa, team_db, team_db_epa_sum, qb_id, qb_name, dropbacks, qb_epa, qb_sr, low_confidence`. It has **no week, game_type or opponent**, so join `derived["team_games"]` (columns `game_id, season, week, asof_week, game_type, is_reg, ..., franchise_id, opponent_id, played, ...`).

```python
# Source: probe against the real cache (14,818 joined rows, 0 null def_sr)
tge = derived["team_game_epa"]
opp = tge.select("game_id", pl.col("franchise_id").alias("opponent_id"), pl.col("off_sr").alias("def_sr"))
epa = (
    derived["team_games"].filter(pl.col("played"))
    .select("game_id", "season", "asof_week", "game_type", "franchise_id", "opponent_id")
    .join(tge.select("game_id", "franchise_id", "off_epa", "off_plays", "off_sr", "def_epa", "def_plays"),
          on=["game_id", "franchise_id"], how="inner")   # drops KNOWN_NO_PBP + lagging games
    .join(opp, on=["game_id", "opponent_id"], how="left")
    .sort("season", "asof_week", "game_id", "franchise_id")
)
# per season: {"season", "note", "game_id": [...], "week": asof_week list, "game_type", "franchise", "opponent",
#   "off_epa": [round(x, 4) + 0.0 ...], "off_plays", "off_sr", "def_epa", "def_plays", "def_sr"}
```

- Checked: `def_plays == opponent off_plays` and `def_epa == opponent off_epa` for every row. Defining `def_sr` as the opponent's `off_sr` is therefore consistent with the existing `def_*` columns (same scrimmage filter). `asof_week == week` for every played game.
- KNOWN_NO_PBP: 3 games / 6 team-games (`1999_01_BAL_STL`, `2000_03_SD_KC`, `2000_06_BUF_MIA`) drop out through the inner join. That's correct: the web counts `games` from rows present. Lagging current-season games also drop out until a refresh picks up the pbp.
- Size: about 36-40 KB per full season (516-570 rows; 2026 to week 9 is 19 KB). The export adds about 1.1 MB total across 28 files. Fine.
- Use `+ 0.0` after `round` to avoid `-0.0` (the existing convention; see `test_contribs_have_no_negative_zero`). `json.dumps(allow_nan=False)` in `write_export` fails loudly on NaN. `off_sr`/`def_sr` have no nulls today, but map None → None defensively.
- Guard: `if derived.get("team_game_epa") is None` → no epa files and `meta.epa_seasons = []`. Only add seasons present in **both** the EPA frame and the scored seasons.
- meta: add `"epa_seasons": sorted(int)`. **`tests/test_export.py::META_KEYS` must gain `epa_seasons`** (`test_contract_meta` asserts exact key-set equality).
- conf/division: `team_meta` currently builds `{name, nick, primary, secondary}`. Add `"conf": r["team_conf"], "division": r["team_division"]`. These are present in `teams.parquet`, e.g. LA → NFC / NFC West. This also flows into `teams/{F}.json` through `**teams[fid]`.
  - **`test_team_meta_filters_and_uppercases` asserts the exact dict** and `_fake_teams()` lacks the columns. Update both. Make `team_meta` tolerate missing columns (`r.get`) or extend `_fake_teams`. Extending the fake is cleaner and keeps the contract strict.

### Pattern 5: Web loader + aggregation

- `web/src/lib/data.ts`: copy the `loadGames` pattern exactly: a `Map<string, Promise<EpaFile>>` keyed `${meta.generated_at}|${season}`, URL `epa/${season}.json?v=${encodeURIComponent(meta.generated_at)}`, evicted on rejection.
- `types.ts`:
  - `export interface EpaFile { season: number; note: string; game_id: string[]; week: number[]; game_type: string[]; franchise: string[]; opponent: string[]; off_epa: number[]; off_plays: number[]; off_sr: number[]; def_epa: number[]; def_plays: number[]; def_sr: number[] }`.
  - `Meta.epa_seasons?: number[]` (optional, matching how `factors?`/`offseason?` were added).
  - `TeamMeta.conf?: string; division?: string`.
- `lib/epa.ts`:

```ts
export interface EpaAgg { off_epa: number | null; def_epa: number | null; off_sr: number | null; def_sr: number | null;
  off_plays: number; def_plays: number; games: number }
export function seasonToDate(f: EpaFile, week: number): Record<string, EpaAgg> {
  const acc: Record<string, { oe: number; de: number; os: number; ds: number; op: number; dp: number; g: number }> = {}
  for (let i = 0; i < f.franchise.length; i++) {
    if (f.week[i] > week) continue
    const a = (acc[f.franchise[i]] ??= { oe: 0, de: 0, os: 0, ds: 0, op: 0, dp: 0, g: 0 })
    const op = f.off_plays[i], dp = f.def_plays[i]
    a.oe += f.off_epa[i] * op; a.os += f.off_sr[i] * op; a.op += op
    a.de += f.def_epa[i] * dp; a.ds += f.def_sr[i] * dp; a.dp += dp; a.g += 1
  }
  // zero plays -> null means (never divide by 0)
  ...
}
```

- Test file `web/src/lib/epa.test.ts`: vitest picks up `src/**/*.test.ts` by default (11 files today). No config change is needed.
- `def_sr` is weighted by `def_plays`. That equals the opponent's offensive plays, so the weighting is consistent.

### Pattern 6: Logos

- Checked by HEAD request: `https://a.espncdn.com/i/teamlogos/nfl/500/{code}.png` returns `200 image/png` for all 32 codes `ari atl bal buf car chi cin cle dal den det gb hou ind jax kc lar lac lv mia min ne no nyg nyj phi pit sea sf tb ten wsh`. Sizes run 7,574 B (nyg) to 130,614 B (nyj), about 1.7 MB total. Every file is over 1 KB.
- **Pitfall:** `.../500/la.png` and `.../500/was.png` **also return 200** with different images (29,273 B and 28,658 B). The PNG signature and size checks can't catch a wrong code. Add a test that compares the hard-coded mapping with the cached `teams.parquet` `team_logo_espn` column, whose URLs end in exactly the codes above. Skip it if the cache is missing; it needs no network.
- Module shape:
  - `logos.py` has `logo_url(franchise) -> str`, `CODE_OVERRIDES = {"LA": "lar", "WAS": "wsh"}`, `validate_png(data: bytes) -> None` (signature `b"\x89PNG\r\n\x1a\n"` and `len > 1024`), and `fetch_logos(out_dir=paths.LOGOS_DIR, force=False, fetch=_http_get, today=None) -> dict`.
  - Writes are atomic: `path.with_name(name + ".tmp")` then `os.replace`, the same as `draft.load_draft_values`.
  - Write `manifest.json` last, sorted keys, `indent=1`.
  - **Inject `fetch`** (a callable `url -> bytes`) so tests need no `urllib` monkeypatching. The existing alternative is `monkeypatch.setattr("urllib.request.urlopen", fake)` (`tests/test_expectation.py::test_load_win_totals_reads_cache`). That only works if the module calls `urllib.request.urlopen` through the module attribute (as `draft.py`/`expectation.py` do), not via `from urllib.request import urlopen`.
- CLI: `p = sub.add_parser("logos", help=...); p.add_argument("--force", action="store_true"); p.set_defaults(func=_cmd_logos)`. This matches the existing pattern in `cli.main`. Update the cli module docstring's command list. Don't wire it into `refresh`.
- `paths.LOGOS_DIR = PIPELINE_ROOT.parent / "web" / "public" / "logos"`. This is a sibling of `WEB_DATA_DIR`. `write_export` only owns `web/public/data/`, so logos are never deleted by an export. Checked: neither `web/public/logos/` nor `web/public/data/epa/` is gitignored.
- No-hotlink test (web side, vitest): glob `../**/*.{ts,svelte}` and `../../index.html` as raw text and assert there's no `espncdn` and no `wikipedia` (scope it to logo URLs, e.g. `/(espncdn|wikipedia)\.(com|org)\/.*\.(png|svg)/i`). `web/src` currently has no matches.

### Anti-Patterns to Avoid
- **Editing `expectation.py`/`features.py`/`cli.derive_games` for win totals.** It changes the fingerprint and risks leaking into `vs_exp`. Keep all display wiring in `_cmd_export`/`_cmd_refresh`/`build_export`.
- **Adding forfeits because the DP doesn't warn.** In rounds 3-7 it never warns. Use the positional evidence above.
- **Running `fgs refresh` or `build --refresh`** during the phase. It re-pulls 2026 pbp and schedules (D-20). `fgs export` is cache-only.
- **Editing `win_totals_2021plus.csv` after its commit.** That breaks the A3.4 pin. Copy the sourced CSV byte-for-byte; don't reformat it.
- **Regenerating the golden pin after code changes.** The pin comes only from commit 1 (HEAD data). The regen flag exists for future deliberate use.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Session sim cache in tests | A new cache dir per test | `conftest.derive_inputs()` / autouse `sim_cache_dir` | A cold sim costs about 10 s and is shared across the session |
| Franchise code mapping | New maps | `franchises.RAW_TO_FRANCHISE`, `CANONICAL` | OAK/SD/STL are already handled |
| Season game counts | Hard-coded 16/17 | `season_config.reg_games(season)` | Changes in 2021 |
| Import-firewall test | A new framework | Regex + comment strip from `test_leakage.py` | Already proven |
| Git checks | GitPython | `subprocess` + the `holdout.git_state` style | No new dependency |
| Atomic file writes | Ad hoc | tmp + `os.replace` (draft.py/expectation.py) | Established pattern |

## Runtime State Inventory

This phase isn't a rename. Only one piece of runtime state is relevant:

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `pipeline/callout_evidence.json` stores `code_fingerprint` 6e1958f91b8a, which the draft.py edits invalidate | One `uv run fgs evidence` after the draft edits, then commit |
| Live service config | None. Vercel builds from git; logos/data are static | None |
| OS-registered state | None | None |
| Secrets/env vars | `FGS_GOLDEN_REGEN` (new, test-only) | Document in the test docstring |
| Build artifacts | `data/derived/sim` (real sim cache, gitignored). `fgs export` reads and writes it; harmless | None |

## Common Pitfalls

### Pitfall 1: Stale evidence breaks every real-data export test mid-phase
**What goes wrong:** after the `draft.py` edits, `build_export` raises "callout_evidence.json is stale (code_fingerprint ...)".
**How to avoid:** make `uv run fgs evidence` the last step of the forfeit task. Commit `callout_evidence.json` with it. Make no further edits to fingerprinted files (CODE_FILES or `cli.derive_games`/`draft_winsor`) after that.
**Warning signs:** `test_export.py` real_files errors and `test_cli` export failures.

### Pitfall 2: Refresh path missing the new export inputs
**What goes wrong:** `_cmd_export` passes `win_totals=` but `_cmd_refresh` doesn't, so the next weekly refresh ships team files without `vegas_win_totals`.
**How to avoid:** one helper, called from both. Add an assertion in `test_cli` refresh tests, which already monkeypatch heavily. At minimum, unit-test the helper.

### Pitfall 3: Contract tests with exact key sets
- `META_KEYS` (`test_export.py:28`) needs `epa_seasons`.
- `test_team_meta_filters_and_uppercases` needs `conf`/`division` in the expected dict and in `_fake_teams()`.
- `test_contract_history_and_teams` asserts `set(h) == {season, week, score, elo, label}` on `history` only. Adding `vegas_win_totals` at the team-file top level is safe.
- `test_contract_files` could gain `epa/` assertions.

### Pitfall 4: Wrong ESPN code silently succeeds
See Pattern 6. `la.png`/`was.png` return valid but different PNGs.

### Pitfall 5: Git-count test before the commit
n == 0 before the CSV is committed. Have the test skip at 0, or commit first. Never assert `>= 1` when a later edit would add a second commit; the assertion must be `== 1`.

### Pitfall 6: Golden derive and 2026
`score_frame` includes the live 2026 season. Filter `season <= 2025` **after** `score_frame`. The reference is fixed at 1999-2021, so 2026 games never move ≤2025 scores (checked: hash equal with 2026 data present).

### Pitfall 7: `uv run pytest` writes nothing to tracked files
Checked: a full suite run left `git status` clean. The `fgs` commands do write: `fgs export` writes `web/public/data` and `RECORDS_CHECK.md`, and `fgs evidence` writes `callout_evidence.json`. Run them only in D-19 steps 2 and 6.

## Code Examples

### Win-totals validator skeleton

```python
# pipeline/src/fgs/wintotals.py (not fingerprinted; display only)
COLUMNS = ["season", "team", "line", "over_odds", "under_odds", "source", "entered_on", "line_type"]
LINE_TYPES = {"preseason_close", "preseason_open"}
FILES = {"win_totals_2021plus.csv": (2021, 2025), "win_totals_display_2026plus.csv": (2026, None)}

def validate(df: pl.DataFrame, file_seasons: tuple[int, int | None]) -> pl.DataFrame:
    if df.columns != COLUMNS: raise ValueError(...)
    # cast season/line; odds: "" or r"^[+-]?\d+$"; team -> RAW_TO_FRANCHISE -> must be in CANONICAL
    # per season: height == 32 and n_unique(team) == 32; no dup (season, team)
    # (line * 2) integral and line > 0;  abs(sum(line) - reg_games(s) * 16) <= 8
    # source.startswith("https://") and urlparse(...).netloc; line_type in LINE_TYPES
```

### Git single-commit guard

```python
def test_win_totals_2021plus_single_commit():
    root = paths.PIPELINE_ROOT.parent
    rel = "pipeline/inputs/win_totals_2021plus.csv"
    try:
        ok = subprocess.run(["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True)
    except OSError:
        pytest.skip("git not available")
    if ok.stdout.strip() != "true":
        pytest.skip("not a git work tree")
    if subprocess.run(["git", "-C", str(root), "rev-parse", "--is-shallow-repository"],
                      capture_output=True, text=True).stdout.strip() == "true":
        pytest.skip("shallow clone")
    n = len(subprocess.run(["git", "-C", str(root), "log", "--format=%H", "--", rel],
                           capture_output=True, text=True).stdout.split())
    if n == 0:
        pytest.skip("win_totals_2021plus.csv not committed yet")
    assert n == 1, f"{rel} has {n} commits; it is write-once (PREREGISTRATION_V2_DEVIATIONS A3.4)"
    dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--", rel],
                           capture_output=True, text=True).stdout.strip()
    assert not dirty, f"{rel} has uncommitted changes: {dirty}"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `UNATTRIBUTED_SHORT = {(2021, 7)}` | `(2021, 7): ["MIN"]` in FORFEITS; `UNATTRIBUTED_SHORT = set()` (keep the name; `surplus_table` defaults to it) | This phase | No surplus change (pick value 0 at the end of R7) |
| 2017 R4 keyed NE | Keyed NO (original slot owner) | This phase | 10 teams ±0.1 |
| Logos hotlinked (planned) | Committed `web/public/logos` | This phase | No runtime external requests |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Positional match gain is a valid detector of a forfeited slot in the derived original order. Supported by the 3 controls behaving as expected, but the 2000-2005 orders are noisy. | Pattern 2 | Real forfeits in 2000-2005 stay unrecorded. Display-only, so there's no score impact. They're logged in the SUMMARY. |
| A2 | The trailing pick that becomes "comp" when a forfeit is added (e.g. 2008 R5 pick 166 LAC) really is a compensatory pick. Not verifiable from nflverse, which has no comp flag. | Pattern 2 | LAC 2008 surplus off by 2.0 (display only) |
| A3 | ESPN CDN keeps serving these URLs at execution time. Checked today only. | Pattern 6 | `fgs logos` fails loudly (PNG validation); re-run later |

## Open Questions

1. **Should the 5 unsupported audit candidates be recorded anywhere besides the SUMMARY?**
   - Recommendation: add a comment block `# Sourced but not applied (pick data shows no slot gap): ...` with citations in `draft.py`. It's fingerprint-free and keeps DATA-01's audit trail in the code.
2. **Does `fgs export` need `--refresh`-free teams data for conf/division?** No. `load_teams()` reads `data/cache/teams.parquet` (present, with `team_conf`/`team_division`).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv + Python | Pipeline | ✓ | Python 3.13 (uv-managed `.venv`) | — |
| nflverse cache | Golden derive, export, draft probes | ✓ | `pipeline/data/cache` (18 MB; pbp 1999-2026, win_totals 2003-2020, draft_picks, teams) | Real-data tests skip |
| Node 24 via nvm | Web test/check/build | ✓ | v24.20.0 (`source ~/.nvm/nvm.sh && nvm use 24`; default is 20) | — |
| git | Commit-count guard | ✓ | Repo root `feel-good-scorew/`, not shallow | Test skips |
| Network to a.espncdn.com | `fgs logos` (once) | ✓ | 32/32 HTTP 200 | Re-run later; tests are mocked |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥9.2 (pipeline, `[tool.pytest.ini_options] testpaths=["tests"]`, no markers); vitest 5.1 (web, no separate config) |
| Config file | `pipeline/pyproject.toml`; `web/vite.config.ts` |
| Quick run command | `cd pipeline && uv run pytest tests/test_golden_scores.py tests/test_draft.py tests/test_wintotals.py tests/test_logos.py -q` (a few seconds plus about 10 s of cold sim for the golden derive) |
| Full suite command | `cd pipeline && uv run pytest -q` (**584 tests, about 2 min 26 s** today; slowest are freeze/refresh/backtest at 11-19 s each) and `cd web && source ~/.nvm/nvm.sh && nvm use 24 && npm test && npm run check && npm run build` (**about 0.8 s / 1.5 s / 0.6 s**; 158 vitest tests) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTEG-01 | Committed export ≤2025 matches the pin | unit (file hash) | `uv run pytest tests/test_golden_scores.py -k export -q` | ❌ Wave 0 |
| INTEG-01 | A fresh derive matches the pin | integration (real cache, skips without it) | `uv run pytest tests/test_golden_scores.py -k derive -q` | ❌ Wave 0 |
| DATA-01 | FORFEITS/FORFEIT_KIND key sets match; kinds valid; 2017 R4 is NO; (2021, 7) is MIN; `UNATTRIBUTED_SHORT` is empty | unit | `uv run pytest tests/test_draft.py -q` | ✅ (extend) |
| DATA-01 | No unknown short rounds; acceptance and winsor tests still pass | integration | `uv run pytest tests/test_draft.py -k "real or acceptance or forfeit" -q` | ✅ (2 asserts updated) |
| DATA-01 | Evidence fresh after rerun | integration | `uv run pytest tests/test_export.py -k stale_evidence -q` and `uv run fgs export` exit 0 | ✅ |
| DATA-02 | Validator accepts both committed files and rejects each bad case | unit | `uv run pytest tests/test_wintotals.py -q` | ❌ Wave 0 |
| DATA-02 | `_cached_vegas` max season ≤2020; no `wintotals`/inputs refs in expectation paths; import firewall; single git commit | unit/integration | `uv run pytest tests/test_wintotals.py -k guard -q` | ❌ Wave 0 |
| DATA-02 | Team files carry `vegas_win_totals` (2003-2020 used_in_score true; 2021+ false) | integration | `uv run pytest tests/test_export.py -k vegas -q` | ❌ (add) |
| EXPL-01 | `epa/{season}.json` per pbp season, columns, 4 dp, def_sr equals the opponent's off_sr, `meta.epa_seasons`, conf/division | integration | `uv run pytest tests/test_export.py -k "epa or meta" -q` | ❌ (add) |
| EXPL-01 | No pbp → no epa files, `epa_seasons == []` | unit (synthetic) | `uv run pytest tests/test_export.py -k no_pbp -q` | ❌ (add) |
| EXPL-01 | `seasonToDate` weighting, week cutoff, missing team, zero plays | unit | `cd web && npx vitest run src/lib/epa.test.ts` | ❌ Wave 0 |
| LOGO-01 | URL mapping (LA→lar, WAS→wsh) and its agreement with the teams cache; PNG validation; skip/force; manifest | unit (mocked fetch) | `uv run pytest tests/test_logos.py -q` | ❌ Wave 0 |
| LOGO-01 | 32 committed PNGs + manifest exist | unit (skips if dir absent) | `uv run pytest tests/test_logos.py -k committed -q` | ❌ Wave 0 |
| LOGO-01 | No external logo URLs in `web/src` | unit | `cd web && npx vitest run src/lib/nohotlink.test.ts` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the quick run command for the touched area, plus `tests/test_golden_scores.py`.
- **Per wave merge:** full `uv run pytest -q`.
- **Phase gate (D-19 step 6):**
  1. `uv run fgs export`
  2. full pytest
  3. web `npm test && npm run check && npm run build` (Node 24)
  4. Record the golden hash before and after in the SUMMARY.

### Wave 0 Gaps
- [ ] `pipeline/tests/test_golden_scores.py` + `pipeline/tests/golden/v1_scores_le2025.json` (commit 1, before anything else)
- [ ] `pipeline/tests/test_wintotals.py`
- [ ] `pipeline/tests/test_logos.py`
- [ ] `web/src/lib/epa.test.ts`, `web/src/lib/nohotlink.test.ts`
- No framework installs needed.

## Security Domain

`security_enforcement` is `false` in `.planning/config.json`, so this section is omitted. One note: logo downloads go only to a fixed HTTPS host, with signature and size validation and atomic writes. There's no user input.

## Sources

### Primary (HIGH confidence)
- Codebase at HEAD 97e1f33: `pipeline/src/fgs/{draft,cli,export,expectation,fingerprint,pbp,mood,score,paths,franchises,season_config,holdout}.py`, `pipeline/tests/{conftest,test_draft,test_export,test_leakage,test_expectation,test_holdout,test_e2e}.py`, `pipeline/weights.yaml`, `pipeline/callout_evidence.json`, `web/src/lib/{data,types,sep.test}.ts`, `web/package.json`, `pipeline/PREREGISTRATION_V2_DEVIATIONS.md` A3.
- Read-only probes, scripts in the session scratchpad:
  - golden export-vs-derive equality and timing
  - per-candidate forfeit surplus/warning diffs, plus the deletion-ranking test with 3 controls
  - combined acceptance tests under the patched FORFEITS
  - EPA join/def_sr/size
  - sourced CSV validation
  - full pytest and web test/check/build timings
- `curl -sI` HEAD checks of all 32 ESPN logo URLs, the Python UA, and the wrong-code (la/was) behavior.
- `.planning/phases/11-pipeline-data-guards/sources/forfeit_audit.json` (citations already fetched during discuss).

### Secondary / Tertiary
- None. No web searches were needed: the sourcing was already done.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. No new dependencies; existing patterns read directly.
- Architecture: HIGH. Every integration seam was located and the fingerprint coverage checked.
- Forfeit verdicts: MEDIUM-HIGH. The method is validated by controls, but the 2000-2005 derived orders are noisy (A1, A2).
- Pitfalls: HIGH. Each one was reproduced or read from the code.

**Research date:** 2026-11-11
**Valid until:** 2026-12-11. The ESPN CDN check is valid for days.

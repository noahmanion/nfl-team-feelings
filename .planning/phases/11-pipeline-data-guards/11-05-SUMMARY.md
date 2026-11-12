---
phase: 11-pipeline-data-guards
plan: 05
subsystem: pipeline+web
tags: [export, golden-test, phase-gate, INTEG-01, DATA-01, DATA-02, EXPL-01, LOGO-01]
requires: ["11-01", "11-02", "11-03", "11-04"]
provides:
  - "Committed web/public/data with epa/{season}.json, meta.epa_seasons, meta.teams conf/division, team vegas_win_totals"
  - "Phase 11 end-to-end gate evidence (pytest + vitest + svelte-check + vite build)"
affects: [web/public/data]
tech-stack:
  added: []
  patterns: ["regenerate once from cache with fgs export, then prove golden pin before == after"]
key-files:
  created:
    - web/public/data/epa/1999.json .. 2026.json (28 files)
  modified:
    - web/public/data/meta.json
    - web/public/data/teams/*.json (32)
    - web/public/data/snapshots/{2003,2008,2011,2012,2017,2022,2023}.json
decisions:
  - "Site data regenerated once from the cache with `fgs export` (no refresh/evidence/network); golden hash unchanged"
metrics:
  duration: "~6 min"
  completed: 2026-11-12
  tasks: 2
  files: 68
---

# Phase 11 Plan 05: Regenerate Site Data + Phase Gate Summary

The site data was regenerated once from cache with `uv run fgs export`, with no network. It now ships the EPA files, conf/division and the display-only Vegas win totals. The golden v1 pin still matches byte for byte, and every pipeline and web gate passes.

## Golden pin (INTEG-01)

| | Overall sha256 | Rows |
|---|---|---|
| Before (pin, 11-01) | `3ac3c2b58d0bfecf2ba7641160cac7a78110265d1c209e27764c2febf0539472` | 19,102 |
| After (regenerated export, via `export_rows`/`pin_of`) | `3ac3c2b58d0bfecf2ba7641160cac7a78110265d1c209e27764c2febf0539472` | 19,102 |

The two are equal. `tests/test_golden_scores.py` has 2 tests (export and derive), and both pass against the new export. The pin file was not touched and still has a single commit.

## Export output

- `fgs export` wrote **122 files** to `web/public/data` (16M total). The latest is 2026 week 9. `RECORDS_CHECK.md` is unchanged, so it was not committed.
- **EPA:** 28 files, `epa/1999.json` .. `epa/2026.json`, **1.1M** total. There is exactly one file per `meta.epa_seasons` entry.
- `meta.teams.LA` = conf `NFC`, division `NFC West`.
- `teams/KC.json` `vegas_win_totals` has 24 rows (2003-2026). `used_in_score` is true for exactly the seasons <= 2020.
- The diff is 40 modified files plus the new `epa/`: meta.json, all 32 team files, and 7 snapshots. The snapshots are exactly 2003, 2008, 2011, 2012, 2017, 2022 and 2023, one line each (the week-0 draft blocks moved by the 11-01 forfeit audit). Scores and labels are unchanged, as the golden check proves.

## Carried-forward integrity facts

- code_fingerprint: `6e1958f91b8a` -> `07c33dd92639` (from 11-01). `callout_evidence.json` still reads `07c33dd92639`.
- `pipeline/inputs/win_totals_2021plus.csv` sha256 is `338450a3c70cc47b6ec4379dc6d72b0fe343a8a2737b2666e1535a8fc9995449`. Its only commit is still `a3135cb` (`git log` count = 1).
- Five forfeits are sourced but not applied, because the derived pick order has no slot gap for them. Applying one would reclassify a real regular pick and charge an uninvolved team:
  - 2000 R4 NE (supplemental, J'Juan Cherry)
  - 2001 R3 PIT (penalty, Wolford cap violation)
  - 2002 R3 DEN (penalty, deferred compensation)
  - 2002 R3 SF (penalty, cap violations)
  - 2005 R3 DEN (penalty, 1996-98 cap circumvention)

## Gate results

| Gate | Result |
|---|---|
| `uv run pytest -q` (pipeline) | **631 passed** in 147s, 0 skipped/failed |
| `npm test` (vitest, Node 24) | **166 passed**, 13 files (includes `src/lib/epa.test.ts`, `src/lib/nohotlink.test.ts`) |
| `npm run check` (svelte-check) | 229 files, 0 errors, 0 warnings |
| `npm run build` | built OK. `dist/logos/` has 32 PNGs (incl. KC.png) and `dist/data/epa/` has 28 files |
| `git status --porcelain -- . ":!.planning"` after gates | empty |

## Requirement -> evidence

| Req | Evidence |
|---|---|
| INTEG-01 | `tests/test_golden_scores.py` export and derive checks pass. The before and after overall hashes are equal (above). |
| DATA-01 | The audited FORFEITS table (11-01), with 30 keys / 35 team-lines carrying citations and FORFEIT_KIND. The `test_draft.py` table tests pass, and the 7 changed snapshot draft blocks are committed. |
| DATA-02 | `test_wintotals.py` guards (a-d, incl. the single-commit check) pass. KC `vegas_win_totals` has 24 rows, with `used_in_score` true only for seasons <= 2020. |
| EXPL-01 | 28 `epa/{season}.json` files match `meta.epa_seasons`, and meta has conf/division. Vitest `epa.test.ts` passes. |
| LOGO-01 | `test_logos` committed check passes, along with vitest `nohotlink.test.ts`. The build output contains 32 logos. |

## Commits

- 1b0f6b5 data(11-05): regenerate site data with EPA, win totals and conf/division (golden unchanged)

Task 2 was verification only and changed no files, so it has no commit.

## Deviations from Plan

None. The plan was executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: web/public/data/meta.json, web/public/data/teams/KC.json, web/public/data/epa/2025.json
- FOUND commit: 1b0f6b5

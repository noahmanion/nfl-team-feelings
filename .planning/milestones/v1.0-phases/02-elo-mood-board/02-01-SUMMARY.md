---
phase: 02-elo-mood-board
plan: 01
subsystem: pipeline-export + web
tags: [mood, percentile, hysteresis, json-contract, vite, svelte5]
requires:
  - fgs.cli.derive (Phase 1)
  - fgs.season_config.reg_weeks / n_teams
  - fgs.franchises.CANONICAL
provides:
  - fgs.mood (BANDS, HYSTERESIS, percentile_scores, band_of, hysteresis, score_frame)
  - fgs.export (team_meta, build_export, write_export)
  - fgs.asof (latest_played, data_through, week_progress)
  - fgs.ingest.load_teams, fgs.paths.WEB_DATA_DIR
  - "`uv run fgs export` -> web/public/data (meta, latest, snapshots/*, teams/*, history, callouts)"
  - web/ app (Vite 8 + Svelte 5 + TS 6) rendering the latest board
affects:
  - 02-02 (scrubber/hash routing builds on App.svelte, data.ts, format.ts)
  - 02-03 (fgs refresh reuses build_export/write_export)
  - 02-04 (states/polish on these components)
tech-stack:
  added: [vite 8, svelte 5, typescript ~6.0, svelte-check, vitest 5.1]
  patterns:
    - pure build_export dict keyed by relative path, then a single write step
    - stripe colour resolved from the label via meta.bands, never from the score
key-files:
  created:
    - pipeline/src/fgs/mood.py
    - pipeline/src/fgs/export.py
    - pipeline/src/fgs/asof.py
    - pipeline/tests/test_mood.py
    - pipeline/tests/test_export.py
    - web/public/data/** (generated, committed)
    - web/src/lib/{types,data,format,format.test}.ts
    - web/src/components/{SiteHeader,BoardHeading,Badge,MoodBoard,BoardRow,TeamChip,MoodLabel,Delta,SiteFooter}.svelte
  modified:
    - pipeline/src/fgs/cli.py
    - pipeline/src/fgs/ingest.py
    - pipeline/src/fgs/paths.py
    - web/src/App.svelte, web/src/app.css, web/index.html, web/package.json
decisions:
  - "Rank by Elo with ordinal ties broken by franchise id, never by the integer score"
  - "Percentile reference = week 0 + REG rows only; playoff rows are scored against it but not included"
  - "Hysteresis uses the literal +/-2 reading (enter at T+2, leave at T-2), chained per team-season with week 0 fresh"
  - "web/ has no vitest config; the default node env covers the pure TS tests"
metrics:
  duration: 5min
  completed: 2026-11-11
  tasks: 3
  files: 100
---

# Phase 2 Plan 01: Elo Mood Board Thin Slice Summary

`fgs export` now turns Elo snapshots into integer 0–100 percentile scores, applies the 7 mood bands with ±2 hysteresis, and writes the full D-06 JSON contract to `web/public/data/`. A Vite 8 + Svelte 5 app reads that contract and renders the latest week's ranked board: 32 teams, each with color chip, record, score, emoji and label, and weekly change.

## What was built

**Task 1, pipeline (TDD).**
- `mood.py` follows RESEARCH Pattern 1 exactly: mid-rank percentile via `searchsorted`, `band_of`, and `hysteresis`.
- `score_frame` adds score, rank, score_delta, rank_delta, band, label and emoji.
- `export.py` builds every file as a dict first, then writes it all in one step. The write clears `snapshots/` and `teams/`, uses `ensure_ascii=False` and compact separators.
- `week_labels` are built from `game_type`, with assertions that `reg_weeks` matches `season_config` and that postseason weeks run WC→DIV→CON→SB in order.
- `asof.py` holds the as-of helpers. `cli.py` keeps the old `_latest_played` and `_data_through` names as aliases, so existing callers still work.
- The new `export` subcommand reads the global `WEB_DATA_DIR` at call time, so tests can monkeypatch it.
- On real data: 64 files, about 4.1 MB. Latest is 2026 week 9 (not partial). BUF is first with score 98 (🎉 Planning the parade) and TEN is last with 2 (🕶️ Witness protection).

**Task 2, web scaffold (TDD).**
- Scaffolded with create-vite's svelte-ts template, then removed the demo files. Added `.nvmrc` 22, `engines >=22.12` and the `test` script.
- `app.css` holds every UI-SPEC token, light and dark, including `--mood-0..6` and `--chip-outline`.
- Added `types.ts` (the contract mirror), `data.ts` (no-store fetchers) and `format.ts`, which has 14 vitest cases.
- `formatDateOnly` parses Y-M-D parts, so the date doesn't shift by time zone. Tests pass under America/Chicago, America/Los_Angeles and Asia/Tokyo.

**Task 3, board.**
- `App` fetches meta and latest in parallel, with a visually hidden loading message and a fatal-error panel that has a Try again button.
- `BoardRow` uses the mobile grid `28px 1fr auto` and the desktop 6-column grid. On desktop it adds "Elo N" and the `#▲N` rank delta.
- Each row has one visually hidden sentence for screen readers; the visual cells are `aria-hidden`.
- `MoodBoard` adds a desktop column header (`aria-hidden`). `SiteFooter` shows last updated, data through, and the nflverse link.

## Verification

- `cd pipeline && uv run pytest -q`: 113 passed (74 prior plus 39 new). `uv run fgs elo` and `uv run fgs check` still exit 0.
- `meta.json` has 7 bands, 32 teams, and `score_kind` "elo". `latest.json` has no `\u` escapes, and `mood.py` uses the U+2019 apostrophe.
- `cd web && npm run test`: 14 passed. `npm run check`: 0 errors, 0 warnings. `npm run build`: succeeds, 22.9 KB JS.
- Grep gates: no band label strings under `web/src` (excluding tests) and no `{@html`.
- Dev server smoke test: `/data/latest.json` is served from `public/`.
- The visual check at 375px and 1024px, light and dark, is left to the orchestrator.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Added a "Try again" button to the fatal-error panel**
- **Found during:** Task 3
- **Issue:** The plan asked only for "a simple message", but UI-SPEC's fatal-error copy includes a Try again action, and leaving it out costs a full reload.
- **Fix:** The button re-runs `boot()`. It's 44px tall and uses the secondary style.
- **Files modified:** web/src/App.svelte
- **Commit:** bb7fe22

Otherwise the plan was executed as written. The extra tests cover a multi-band drop in hysteresis, the stale-file cleanup in `write_export`, and `fgs export` through the CLI with a monkeypatched output directory.

## TDD Gate Compliance

- Task 1: RED `5ba36fb` (test), then GREEN `be700c9` (feat).
- Task 2: RED `427d34e` (test), then GREEN `5f039cd` (feat).
- No refactor commits were needed.

## Known Stubs

- `web/public/data/callouts.json` is `[]` on purpose: the D-06 contract has callouts arriving in a later phase.
- The fatal-error copy references `uv run fgs refresh`, which plan 02-03 adds. The copy is the UI-SPEC text as written.

## Notes for later plans

- Historical scores drift by ±1 on each refresh (RESEARCH Pitfall 4). Tests pin structure, not exact historical scores.
- `teams.parquet` was downloaded once into `pipeline/data/cache/`, which is gitignored. The export tests skip when it's missing.

## Self-Check: PASSED

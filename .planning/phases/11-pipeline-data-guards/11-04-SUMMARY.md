---
phase: 11-pipeline-data-guards
plan: 04
subsystem: pipeline-cli + web-assets
tags: [logos, LOGO-01, no-hotlink]
requires: ["11-03"]
provides: ["fgs logos", "paths.LOGOS_DIR", "web/public/logos/{FRANCHISE}.png", "web/public/logos/manifest.json"]
affects: ["phase 12 logo display"]
tech-stack:
  added: []
  patterns: ["injected fetch callable for network-free tests", "tmp + os.replace atomic writes", "static raw-glob scan for forbidden URLs"]
key-files:
  created: [pipeline/src/fgs/logos.py, pipeline/tests/test_logos.py, web/src/lib/nohotlink.test.ts, web/public/logos/manifest.json, web/public/logos/*.png]
  modified: [pipeline/src/fgs/paths.py, pipeline/src/fgs/cli.py]
decisions:
  - "The mapping test compares the ESPN code (URL filename), not the path after /500/: teams.parquet has /500-dark/car.png for CAR"
  - "Skipped (existing) logos keep their earlier manifest fetched date"
requirements: [LOGO-01]
metrics:
  duration: ~15min
  completed: 2026-11-11
---

# Phase 11 Plan 04: One-shot ESPN logos, committed, no hotlinking Summary

`fgs logos [--force]` downloads the 32 ESPN 500px PNGs (LA->lar, WAS->wsh, other codes are the franchise id lowercased) into `web/public/logos/{FRANCHISE}.png`. Each download is checked for a PNG signature and a size over 1 KB, then written atomically. The command also writes a sorted `manifest.json` (url, sha256, bytes, fetched). It ran once against the network, and its output (32 files, 1.70 MB, 7,574 B NYG to 130,614 B NYJ) is committed. A web test proves the sources never reference an external logo host.

## Tasks

| # | Name | Commit |
|---|------|--------|
| 1 (RED) | test_logos.py + nohotlink.test.ts | b1aa504 |
| 1 (GREEN) | logos.py, paths.LOGOS_DIR, `logos` subcommand | 3073389 |
| 2 | One live `fgs logos` run; 32 PNGs + manifest committed | e59883b |

## Verification

- `uv run pytest -q`: 631 passed, golden included. `test_logos.py` passed 7 of 7 with no skips: `test_committed_logos` and the mapping-vs-cache test both ran.
- web `npm test`: 166 passed, including nohotlink (3 tests).
- `fgs logos --help` shows `--force`. `_cmd_refresh` source has no reference to logos (asserted in the tests).
- Visual spot-check: LA (Rams "LA" horn), WAS (Commanders "W") and LV (Raiders shield) are all correct.
- Nothing fingerprinted was touched: `derive_games`/`draft_winsor` and the CODE_FILES are unchanged. `win_totals_2021plus.csv`, PREREGISTRATION*.md and weights.yaml were not touched either. `refresh`/`evidence` were not run.

## Deviations from Plan

1. **[Rule 1 - Bug] Mapping test comparison.** The plan compared the segment after `/500/`, but the cached `team_logo_espn` for CAR is `/500-dark/car.png`, which made the comparison raise IndexError. The test now compares the filename (the ESPN code). The download URL stays `/500/` per D-17. Commit 3073389.
2. **Commit granularity.** The plan asked for one combined Task 1+2 commit. The orchestrator asked for per-task atomic commits plus the TDD RED/GREEN gate, so this plan has three commits.

## TDD Gate Compliance

RED `test(11-04)` b1aa504 came before GREEN `feat(11-04)` 3073389. The nohotlink web test already passed at RED, as expected, because it guards a property that already held.

## Self-Check: PASSED

- FOUND: pipeline/src/fgs/logos.py, pipeline/tests/test_logos.py, web/src/lib/nohotlink.test.ts, web/public/logos/manifest.json, 32 PNGs
- FOUND commits: b1aa504, 3073389, e59883b

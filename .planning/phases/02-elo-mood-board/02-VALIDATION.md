---
phase: 2
slug: elo-mood-board
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-11-11
---

# Phase 2 — Validation Strategy

> Derived from 02-RESEARCH.md § Validation Architecture.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.2 (pipeline, existing) + vitest 5.1 (web, Wave 0) + `svelte-check`/`vite build` compile gates |
| **Config file** | `pipeline/pyproject.toml` (exists); vitest needs none |
| **Quick run command** | `cd pipeline && uv run pytest -q tests/test_mood.py tests/test_export.py` / `cd web && npx vitest run` |
| **Full suite command** | `cd pipeline && uv run pytest -q && cd ../web && npm run test && npm run check && npm run build` |
| **Estimated runtime** | ~20 seconds |

## Sampling Rate

- **After every task commit:** quick command for the side touched
- **After every plan wave:** full suite
- **Before verify:** full suite green + `uv run fgs refresh` end-to-end + manual 375px/desktop check
- **Max feedback latency:** 30 seconds

## Per-Task Verification Map

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| INSIGHT-01 | percentile 0..100, reference = wk0+REG | unit | `uv run pytest -q tests/test_mood.py -k percentile` | ❌ W0 | ⬜ |
| INSIGHT-01 | hysteresis ±2, fresh at week 0 | unit | `uv run pytest -q tests/test_mood.py -k hysteresis` | ❌ W0 | ⬜ |
| INSIGHT-01 | real data: label changes < raw-band changes | integration | `uv run pytest -q tests/test_mood.py -k real` | ❌ W0 | ⬜ |
| PIPE-02 | contract: files, keys, ints, ranks, teams meta | integration | `uv run pytest -q tests/test_export.py -k contract` | ❌ W0 | ⬜ |
| PIPE-02 | latest.json == season file week | integration | `uv run pytest -q tests/test_export.py -k latest` | ❌ W0 | ⬜ |
| PIPE-01 | partial week detection | integration | `uv run pytest -q tests/test_export.py -k partial` | ❌ W0 | ⬜ |
| PIPE-01 | refresh aborts on failed checks without writing | integration | `uv run pytest -q tests/test_cli.py -k refresh` | ❌ W0 | ⬜ |
| SITE-04/10 | hash router round-trip | unit | `cd web && npx vitest run src/lib/router.test.ts` | ❌ W0 | ⬜ |
| SITE-04 | week labels per era, record/delta formatting | unit | `cd web && npx vitest run src/lib/format.test.ts` | ❌ W0 | ⬜ |
| PIPE-03 | site type-checks and builds | smoke | `cd web && npm run check && npm run build` | ❌ W0 | ⬜ |

## Wave 0 Requirements

- [ ] `pipeline/tests/test_mood.py`, `pipeline/tests/test_export.py`, refresh test in `test_cli.py`
- [ ] `web/` scaffold + vitest + `"test": "vitest run"`, `web/.nvmrc` = 22
- [ ] `web/src/lib/router.test.ts`, `web/src/lib/format.test.ts`

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Board renders, no horizontal scroll at 375px, dark mode, stamp, deep links | SITE-01/10 | Visual/layout | `npm run dev`; visit `#/`, `#/board/2007/21`, `#/board/1999/0`, `#/board/1800/3` at 375px & 1024px (orchestrator will check via browser automation) |

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags (vitest run, not watch)
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true`

**Approval:** approved 2026-11-11 (autonomous)

---
phase: 3
slug: backtest-harness-additive-score
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-11-11
---

# Phase 3 — Validation Strategy

> Derived from 03-RESEARCH.md § Validation Architecture (reproduced below). UI: follows 02-UI-SPEC.md "Design System for Later Phases" (no separate UI-SPEC this phase — autonomous decision).

## Sampling Rate
- After every task commit: quick run command (<2s)
- After every wave: full pipeline suite + `npm test && npm run check`
- Phase gate: full suite green, `uv run fgs backtest` prints table with Elo Brier ≈ 0.22, `uv run fgs export` regenerates committed JSON; orchestrator browser-checks `#/history` at 375px and 1280px.
- Max feedback latency: 30s


### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.2.0 (pipeline), vitest 5.1 + svelte-check (web) |
| Config file | `pipeline/pyproject.toml [tool.pytest.ini_options]`, `web/package.json` scripts |
| Quick run command | `cd pipeline && uv run pytest -q tests/test_features.py tests/test_score.py tests/test_leakage.py` |
| Full suite command | `cd pipeline && uv run pytest -q && cd ../web && nvm use && npm test && npm run check && npm run build` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BACK-01 | Target = opponent+HFA-adjusted next-N mean; <2 remaining excluded; README documents it | unit (synthetic) + grep | `uv run pytest tests/test_backtest.py -k target -x` ; `grep -n "adjusted margin" README.md` | ❌ Wave 0 |
| BACK-02 | `fgs backtest` prints all 5 baselines; Elo Brier in [0.215, 0.23]; spread Brier < Elo Brier; backtest.json has candidate×N×bucket + per-season; default seasons 2003–2021 | integration (real_cache) | `uv run pytest tests/test_backtest.py -k "baselines or holdout" -x` | ❌ Wave 0 |
| BACK-02 | Holdout sealed: no 2022+ rows in metrics without `--include-holdout` | unit | `uv run pytest tests/test_backtest.py -k holdout -x` | ❌ Wave 0 |
| BACK-03 | Fake future games / truncation leave elo, factors, contribs, composite, score, band, rank unchanged | integration (real + synthetic) | `uv run pytest tests/test_leakage.py -x` | ❌ Wave 0 |
| MODEL-14 | Σ contrib_f == composite (≤1e-9); z=0 on zero variance; no NaN anywhere | unit | `uv run pytest tests/test_score.py -x` | ❌ Wave 0 |
| MODEL-03 | season_record: REG only, ties 0.5, week-0/bye → 0.5 | unit (synthetic conftest) | `uv run pytest tests/test_features.py -k season_record -x` | ❌ Wave 0 |
| MODEL-04 | last16 spans season boundary, includes playoffs, <16 games uses available, none → 0.5 | unit (synthetic) | `uv run pytest tests/test_features.py -k last16 -x` | ❌ Wave 0 |
| MODEL-14 | Export: meta.score_kind=="composite", meta.factors weights match weights.yaml, rows.contribs keys == factor keys | contract (real) | `uv run pytest tests/test_export.py -x` (update line 74 assertion) | ✅ (needs update) |
| SITE-03 | `toRows` inserts NaN at each season boundary; x-gap; null→NaN; router parses `#/history` and `#/history/BUF`; contrast fallback | unit (vitest) | `cd web && npm test` | ❌ Wave 0 (`lib/history.test.ts`, router.test.ts additions) |
| SITE-03 | Chart renders at 375 px with no horizontal scroll; fixed 0–100 y | manual (visual) | `npm run dev` → `#/history`, `#/history/DET` | manual-only |

### Sampling Rate
- **Per task commit:** the quick run command (under 2 s).
- **Per wave merge:** full pipeline suite plus `npm test && npm run check`.
- **Phase gate:** full suite green, `uv run fgs backtest` prints the table with Elo Brier ≈ 0.22, `uv run fgs export` regenerates committed JSON, then `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `pipeline/tests/test_features.py`, `test_score.py`, `test_backtest.py`, `test_leakage.py`
- [ ] Update `tests/test_export.py:74` (score_kind) and `tests/test_mood.py:118` (reference now frozen/composite)
- [ ] `web/src/lib/history.test.ts`. Extend `router.test.ts` for `#/history[/ABBR]` (currently in RESERVED)
- [ ] `uv add pyyaml`. `npm install @observablehq/plot@0.6.19`


## Validation Sign-Off
- [x] All tasks have automated verify or Wave 0 dependencies
- [x] No watch-mode flags
- [x] `nyquist_compliant: true`

**Approval:** approved 2026-11-11 (autonomous)

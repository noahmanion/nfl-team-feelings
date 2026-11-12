---
phase: 4
slug: game-result-factors-team-deep-dive
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-11-11
---

# Phase 4 — Validation Strategy

> Derived from 04-RESEARCH.md § Validation Architecture. UI follows 02-UI-SPEC "Design System for Later Phases" (team page, factor breakdown). Orchestrator browser-checks `#/team/{ABBR}` at 375px/1280px, light/dark.


### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.2 (pipeline); vitest 5.1 + svelte-check (web) |
| Config file | `pipeline/pyproject.toml [tool.pytest.ini_options]`; `web/package.json` scripts |
| Quick run command | `cd pipeline && uv run pytest -q tests/test_features.py tests/test_explain.py tests/test_leakage.py` |
| Full suite command | `cd pipeline && uv run pytest -q && cd ../web && source ~/.nvm/nvm.sh && nvm use && npm test && npm run check && npm run build` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODEL-06 | mov = mean capped margin over last 8 played (REG+PO), crosses seasons, cap ±24, none → 0 | unit (synthetic, hand-computed) | `uv run pytest tests/test_features.py -k mov -x` | ❌ Wave 0 |
| MODEL-07 | sow = mean(result − p_avg) with opponent pre-game Elo, HFA sign, neutral = 0, tie = 0.5 | unit (hand-computed p_avg) | `uv run pytest tests/test_features.py -k sow -x` | ❌ Wave 0 |
| MODEL-09 | streak sign/length, tie → 0, carries across seasons, cap ±8 | unit | `uv run pytest tests/test_features.py -k streak -x` | ❌ Wave 0 |
| MODEL-10 | luck = one-score W − L over last 16, \|m\| ≤ 8 inclusive, ties excluded | unit | `uv run pytest tests/test_features.py -k luck -x` | ❌ Wave 0 |
| MODEL-06/07/09/10 | Report has ridge:+mov … +luck rows; N=8 Spearman of +luck in [0.519, 0.525]; holdout still sealed | integration (real_cache) | `uv run pytest tests/test_backtest.py -k "ridge_composites or holdout" -x` | ✅ (extend) |
| MODEL-06/07/09/10 | BACKTEST_LOG has 4 new rows; weights.yaml has 7 keys that load | grep + unit | `grep -cE "^\| .* \| (mov\|sow\|streak\|luck) \|" BACKTEST_LOG.md` ; `uv run pytest tests/test_backtest.py -k weights_yaml -x` | ✅ (extend) |
| MODEL-06/07/09/10 | New factor values unchanged by fake future / truncation | integration | `uv run pytest tests/test_leakage.py -x` | ✅ (extend columns) |
| SITE-02 | Σ points == score − baseline for every exported row; baseline == meta.baseline; points keys == factor keys; ints | contract (real) | `uv run pytest tests/test_export.py -k points -x` | ❌ Wave 0 |
| SITE-02 | largest_remainder exact and deterministic; near-zero c finite; all-zero contribs → zeros | unit | `uv run pytest tests/test_explain.py -x` | ❌ Wave 0 |
| SITE-02 | games/{season}.json exists per season, columns equal length, scores null iff unplayed | contract | `uv run pytest tests/test_export.py -k games -x` | ❌ Wave 0 |
| SITE-02 | router parses `#/team/BUF`, `#/team/buf/2024/5`; teamHash; reserved no longer includes team | unit (vitest) | `cd web && npm test` | ✅ router.test.ts (extend) |
| SITE-02 | recentGames: as-of filter, prior-season fill, W/L/T, margin sign, max 6; barRows sorting/top-4/scale | unit (vitest) | `cd web && npm test` | ❌ Wave 0 (`lib/team.test.ts`) |
| SITE-02 | Page renders at 375 px, bars sum label "= score", no horizontal scroll, row links work | manual (visual) | `npm run dev` → `#/team/BUF`, `#/team/DEN/2026/9`, `#/team/CLE/1999/0` | manual-only |
| INSIGHT-05 | Every row has a non-empty blurb ending in "."; plural subject; "but" iff top-2 signs differ; week-0 lead; no "0 straight" | unit + contract | `uv run pytest tests/test_explain.py -k blurb -x` ; `uv run pytest tests/test_export.py -k blurb -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the quick run command (a few seconds).
- **Per factor step:** `uv run fgs backtest` (~1.3 s), then compare against the Prototype Results table (±0.002).
- **Per wave merge:** full pipeline suite plus `npm test && npm run check`.
- **Phase gate:** full suite green, `uv run fgs export` regenerates committed JSON with 7 factors, then a browser check of the team page at 375 px and 1280 px in light and dark, before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `pipeline/tests/test_explain.py`: attribution, largest remainder, phrasebook
- [ ] `tests/test_features.py`: synthetic cases for the 4 factors. The conftest `_ROWS` league has a tie (NE–NYJ), a neutral game, a playoff game and a season boundary, enough to hand-compute mov/sow/streak/luck.
- [ ] Extend `tests/test_leakage.py` columns and `tests/test_export.py` ROW_KEYS/META_KEYS (+points, blurb, baseline)
- [ ] `web/src/lib/team.test.ts`. Update the router.test.ts reserved-team case.
- [ ] No framework installs needed.


**Approval:** approved 2026-11-11 (autonomous)

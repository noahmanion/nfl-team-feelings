---
phase: 6
slug: weight-freeze-methodology
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-11-11
---

# Phase 6 — Validation Strategy

> Derived from 06-RESEARCH.md § Validation Architecture. UI per 02-UI-SPEC later-phase rules (prose page + chart). Orchestrator browser-checks #/methodology at 375/1280px.


### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥9.2 (pipeline), vitest 5 (web) |
| Config file | `pipeline/pyproject.toml [tool.pytest.ini_options]`, `web/package.json` scripts |
| Quick run command | `cd pipeline && uv run pytest tests/test_bootstrap.py tests/test_freeze.py tests/test_holdout.py tests/test_methodology.py -x -q` |
| Full suite command | `cd pipeline && uv run pytest -q` and `cd web && npm test && npm run check && npm run build` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BACK-04 | `fgs freeze` writes frozen yaml (tmp path). `load_weights` returns the 11 rounded weights, and the `fit` block has sign + k/19 with 0 ≤ k ≤ 19 | integration (real cache, tmp WEIGHTS_PATH) | `uv run pytest tests/test_freeze.py -x` | ❌ Wave 0 |
| BACK-04 | Freeze output is unchanged when ≥2022 results are swapped (sealing) | integration | same | ❌ Wave 0 |
| BACK-04 | Guards: `--propose-weights` refused when frozen; `freeze` refused without `--unfreeze`; `freeze --unfreeze` refused when HOLDOUT_RESULT.md exists; `--include-holdout` refused before the result exists | unit (monkeypatched paths) | same | ❌ Wave 0 |
| BACK-04 | Export/refresh never fit: `backtest.ridge_fit` monkeypatched to raise, export still succeeds | unit | `uv run pytest tests/test_export.py -k never_refits -x` | ✅ extend |
| MODEL-15 | Negative and ≈0 weights are kept; `-0.00` is normalized; no clipping | unit | `uv run pytest tests/test_freeze.py -k sign -x` | ❌ Wave 0 |
| BACK-05 | Bootstrap: identical predictors → diff CI exactly [0, 0]; deterministic for a seed; season-block distinct resamples = C(2k−1, k); stratified draw keeps per-season cluster counts; strong vs pure-noise predictor → diff lower bound > 0 | unit (synthetic) | `uv run pytest tests/test_bootstrap.py -x` | ❌ Wave 0 |
| BACK-05 | `evaluate_frozen` on stand-in 2018–2021 (fit ≤2017): schema complete, composite Spearman == `bt.spearman(Σ round(w)·z)`, Brier maps fit only on ≤ fit_last; raises for seasons > 2021 without `allow_holdout` | integration (training only) | `uv run pytest tests/test_holdout.py -x` | ❌ Wave 0 |
| BACK-05 | `fgs holdout` refuses when the result exists, weights aren't frozen, or prereg is missing/dirty (all with tmp paths; **never on the real holdout**) | unit | same | ❌ Wave 0 |
| BACK-06 | `verdict()` maps (diff, CI) → yes/slight/no exactly as pre-registered | unit | `uv run pytest tests/test_holdout.py -k verdict -x` | ❌ Wave 0 |
| BACK-06 | The real one-time result: HOLDOUT_RESULT.md exists, its commit postdates the PREREGISTRATION.md commit, and the verdict is recorded | manual/grep (verifier) | `git log --format='%H %ci' -- pipeline/PREREGISTRATION.md pipeline/HOLDOUT_RESULT.md` | n/a |
| SITE-07 | `methodology.json` in export files; factor weights == weights.yaml == meta.factors; `holdout: null` path works; notes' numbers match the evidence | unit | `uv run pytest tests/test_methodology.py tests/test_export.py -x` | ❌ Wave 0 / ✅ extend |
| SITE-07 | Router parses `#/methodology`; `records` still reserved; verdict/effect formatting helpers | unit (vitest) | `cd web && npx vitest run src/lib/router.test.ts src/lib/methodology.test.ts` | ✅ update / ❌ Wave 0 |
| SITE-07 | Page renders at 375px and 1280px, no horizontal scroll, chart whiskers visible, nav "How it works" active | manual (Playwright screenshot, as in prior phases) | `npm run build && npm run preview` + screenshot | manual |

### Sampling Rate
- **Per task commit:** quick run command above (the synthetic/stand-in tests are fast; real-cache freeze tests take about a minute).
- **Per wave merge:** full pipeline suite + `npm test && npm run check`.
- **Phase gate:** full suite green before the one-time `fgs holdout` task. The holdout task itself is not re-run by tests.

### Wave 0 Gaps
- [ ] `pipeline/tests/test_bootstrap.py`: synthetic bootstrap properties
- [ ] `pipeline/tests/test_freeze.py`: freeze output, sealing, guards, sign/rounding
- [ ] `pipeline/tests/test_holdout.py`: stand-in evaluator, guards, verdict
- [ ] `pipeline/tests/test_methodology.py`: schema + number consistency
- [ ] `web/src/lib/methodology.test.ts`: formatting helpers
- [ ] Update `web/src/lib/router.test.ts` (methodology no longer reserved) and `tests/test_backtest.py::test_weights_yaml_loads` (frozen file keys)


**Approval:** approved 2026-11-11 (autonomous)

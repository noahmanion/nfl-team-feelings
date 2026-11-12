---
phase: 8
slug: callouts-records-my-team
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-11-11
---

# Phase 8 — Validation Strategy

> Derived from 08-RESEARCH.md § Validation Architecture. UI per 02-UI-SPEC later-phase rules. Orchestrator browser-checks affected views at 375/1280px.


### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥9.2 (pipeline), vitest ^5.1 node env (web) |
| Config file | `pipeline/pyproject.toml [tool.pytest.ini_options]`; web uses `vite.config.ts` defaults |
| Quick run command | `cd pipeline && uv run pytest -q tests/test_insights.py tests/test_records.py tests/test_evidence.py` ; `cd web && npx vitest run src/lib/callouts.test.ts src/lib/myteam.test.ts` |
| Full suite command | `cd pipeline && uv run pytest -q` (~28 s) ; `cd web && npx vitest run && npm run check` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INSIGHT-02 | record_rank tiebreak (win% → PD → id); 0-0 = .500; gap sign → flavor; week window 4..rw−1; cap 3/flavor | unit (synthetic frame) | `uv run pytest -q tests/test_insights.py -k gap` | ❌ Wave 0 |
| INSIGHT-02 | Evidence ignores seasons > 2021 (fake 60-0 future results give identical JSON); export raises on stale threshold/fingerprint | unit | `uv run pytest -q tests/test_evidence.py` | ❌ Wave 0 |
| INSIGHT-02 | Firewall: insights.py/records.py don't import backtest | unit | `uv run pytest -q tests/test_leakage.py -k backtest_not_imported` (extend list) | ✅ extend |
| INSIGHT-03 | Snapshot dates: draft table covers every season; dates strictly increase per team; fallback clamped to as_of | unit + real-data check | `uv run pytest -q tests/test_insights.py -k date` | ❌ Wave 0 |
| INSIGHT-03 | Streak scan: active vs ended, cross-season runs, seeded week-0 dropped, days = end−start | unit | `uv run pytest -q tests/test_insights.py -k streak` | ❌ Wave 0 |
| INSIGHT-04 | Extremes: one per team-season, SEEDS excluded, tiebreak deterministic, 10 each | unit | `uv run pytest -q tests/test_records.py` | ❌ Wave 0 |
| INSIGHT-04 | RECORDS_CHECK.md written with 4 lists + notable non-entries | manual (verifier reads vs known history) | `uv run fgs export && cat RECORDS_CHECK.md` | — |
| INSIGHT-06 | Movers top/bottom 3, delta ≠ 0, tiebreak, week ≥ 1 only | unit | `uv run pytest -q tests/test_insights.py -k movers` | ❌ Wave 0 |
| SITE-05/09 | Export: `callouts.json` = latest list with locked keys; each season file has `callouts`; types in allowed set | unit | `uv run pytest -q tests/test_export.py` (update `== []` assertion) | ✅ update |
| SITE-06 | `#/records` parses (remove from RESERVED); records.json shape | unit | `npx vitest run src/lib/router.test.ts` | ✅ extend |
| SITE-08 | myTeam: invalid/garbage stored value → null; storage throwing → in-memory works; orderCallouts puts my team first | unit (injected fake storage) | `npx vitest run src/lib/myteam.test.ts src/lib/callouts.test.ts` | ❌ Wave 0 |
| SITE-08/09 | Pin toggles aria-pressed, row not reordered, Copy link status message, clipboard fallback | manual (browser, http://localhost via vite dev, plus a LAN-IP non-secure origin to exercise the fallback) | — | — |

### Sampling Rate
- **Per task commit:** the quick run command for the touched side.
- **Per wave merge:** full pytest + vitest + `npm run check`.
- **Phase gate:** full suites green, RECORDS_CHECK.md reviewed, `fgs evidence` output committed and matching the export fingerprint.

### Wave 0 Gaps
- [ ] `pipeline/tests/test_insights.py`: gap, dates, streaks, movers (synthetic frames from `conftest.make_games` where possible)
- [ ] `pipeline/tests/test_records.py`: extremes and exclusions
- [ ] `pipeline/tests/test_evidence.py`: holdout seal and staleness guard
- [ ] `web/src/lib/myteam.test.ts`, `web/src/lib/callouts.test.ts`
- [ ] Update `tests/test_export.py:72` (`callouts.json == []`) and the `test_leakage.py` firewall list


**Approval:** approved 2026-11-11 (autonomous)

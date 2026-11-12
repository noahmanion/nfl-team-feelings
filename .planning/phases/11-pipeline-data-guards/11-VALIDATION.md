---
phase: 11
slug: pipeline-data-guards
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-11-11
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from 11-RESEARCH.md "Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=9.2 (pipeline); vitest 5.1 (web) |
| **Config file** | `pipeline/pyproject.toml`; `web/vite.config.ts` |
| **Quick run command** | `cd pipeline && uv run pytest tests/test_golden_scores.py tests/test_draft.py tests/test_wintotals.py tests/test_logos.py -q` |
| **Full suite command** | `cd pipeline && uv run pytest -q` + `cd web && source ~/.nvm/nvm.sh && nvm use 24 && npm test && npm run check && npm run build` |
| **Estimated runtime** | quick ~20 s; full ~150 s pipeline + ~3 s web |

---

## Sampling Rate

- **After every task commit:** quick command for the touched area + `tests/test_golden_scores.py`
- **After every plan wave:** full `uv run pytest -q`
- **Before verify:** `uv run fgs export`, full pytest, web test/check/build all green; golden hash before/after recorded
- **Max feedback latency:** ~150 seconds

---

## Per-Requirement Verification Map

| Requirement | Behavior | Test Type | Automated Command | File Exists |
|-------------|----------|-----------|-------------------|-------------|
| INTEG-01 | Committed export <=2025 matches pin | unit | `uv run pytest tests/test_golden_scores.py -k export -q` | ❌ W0 |
| INTEG-01 | Fresh derive matches pin | integration (skips w/o cache) | `uv run pytest tests/test_golden_scores.py -k derive -q` | ❌ W0 |
| DATA-01 | FORFEITS/FORFEIT_KIND consistent; 2017 R4 NO; 2021 R7 MIN; UNATTRIBUTED_SHORT empty | unit | `uv run pytest tests/test_draft.py -q` | ✅ extend |
| DATA-01 | Evidence fresh after one rerun | integration | `uv run pytest tests/test_export.py -q` + `uv run fgs export` | ✅ |
| DATA-02 | Validator accepts committed files, rejects bad cases | unit | `uv run pytest tests/test_wintotals.py -q` | ❌ W0 |
| DATA-02 | vegas <=2020 guard, import firewall, single-commit file | unit/integration | `uv run pytest tests/test_wintotals.py -k guard -q` | ❌ W0 |
| DATA-02 | Team files carry vegas_win_totals with used_in_score | integration | `uv run pytest tests/test_export.py -k vegas -q` | ❌ add |
| EXPL-01 | epa/{season}.json, def_sr, meta.epa_seasons, conf/division | integration | `uv run pytest tests/test_export.py -k "epa or meta" -q` | ❌ add |
| EXPL-01 | seasonToDate play-weighted aggregation | unit | `cd web && npx vitest run src/lib/epa.test.ts` | ❌ W0 |
| LOGO-01 | URL mapping, PNG validation, skip/force, manifest | unit (mocked) | `uv run pytest tests/test_logos.py -q` | ❌ W0 |
| LOGO-01 | 32 committed logos; no external logo URLs in web/src | unit | `uv run pytest tests/test_logos.py -k committed -q`; `npx vitest run src/lib/nohotlink.test.ts` | ❌ W0 |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pipeline/tests/test_golden_scores.py` + `pipeline/tests/golden/v1_scores_le2025.json` (first execution commit)
- [ ] `pipeline/tests/test_wintotals.py`
- [ ] `pipeline/tests/test_logos.py`
- [ ] `web/src/lib/epa.test.ts`, `web/src/lib/nohotlink.test.ts`

No framework installs needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Logos look right (correct team art) | LOGO-01 | visual | open a few of `web/public/logos/*.png` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 150s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

---
phase: 7
slug: draft-aware-offseason
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-11-11
---

# Phase 7 — Validation Strategy

> Derived from 07-RESEARCH.md § Validation Architecture. UI per 02-UI-SPEC later-phase rules. Orchestrator browser-checks affected views at 375/1280px.


### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥9.2 (pipeline), vitest 5.x (web) |
| Config file | `pipeline/pyproject.toml` `[tool.pytest.ini_options] testpaths=["tests"]`; `web/` vitest default |
| Quick run command | `cd pipeline && uv run pytest -q tests/test_draft.py` ; `cd web && npx vitest run src/lib/history.test.ts` |
| Full suite command | `cd pipeline && uv run pytest -q` ; `cd web && npm test && npm run check` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-06 | Every PFR code since 1999 maps; unknown code raises | unit | `uv run pytest -q tests/test_draft.py -k pfr` | ❌ Wave 0 |
| DATA-06 | Draft cache covers 2000..current; 31/32 franchises per draft; max pick ≤ 262; chart has picks 1..262 | integration (cached data, skip if no cache) | `uv run pytest -q tests/test_draft.py -k coverage` | ❌ Wave 0 |
| MODEL-16 | Synthetic 4-team draft: untraded team → surplus 0 exactly; a trade-up moves value between exactly two teams; a forfeit lowers only the owner; comp tail excluded | unit | `uv run pytest -q tests/test_draft.py -k surplus` | ❌ Wave 0 |
| MODEL-16 | Real data: every draft 2000–2026, a slot-1 team whose aligned picks are all its own and that has no extra regular picks → surplus == 0; per-season Σ surplus ≤ 1e-9; Spearman(surplus, slot) over 2000–2021 in [−0.15, 0.15] | integration | `uv run pytest -q tests/test_draft.py -k acceptance` | ❌ Wave 0 |
| MODEL-16 | Tie rotation + expansion-first + R1–R2 forfeit table used in `original_order` | unit | `-k order` | ❌ Wave 0 |
| MODEL-16 | Gate: (Δ>0, consistency vs final sign ≥ .6, w>0) else 0; never reads seasons > 2021 | unit (synthetic) + leakage | `uv run pytest -q tests/test_backtest.py -k draft` | ❌ Wave 0 |
| MODEL-16 | w = 0 → no `contrib_draft`, factor keys unchanged, scores identical to pre-phase; w ≠ 0 (fake 1.0) → contrib only weeks 0–3 with decay; percentile reference unchanged | unit | `uv run pytest -q tests/test_score.py -k draft` | ❌ Wave 0 |
| MODEL-16 | Week-0 score_delta = score(S,0) − score(S−1,last); null for first season/expansion | unit | `uv run pytest -q tests/test_mood.py` (update line 166) | ✅ (edit) |
| MODEL-16 | Export: week-0 rows carry `draft` {surplus, z, equiv_pick, rank} or null; `week_labels["0"]=="Preseason (after draft)"`; meta.offseason present | unit | `uv run pytest -q tests/test_export.py` (update 92, 118) | ✅ (edit) |
| MODEL-16 | Leakage: appending a future season doesn't change past week-0 deltas/surplus/z (frozen winsor) | unit | `uv run pytest -q tests/test_leakage.py` | ✅ (extend) |
| Visibility | `connectors()`: one segment per team per boundary, from the last non-null of S to week 0 of S+1; skips nulls; highlight filter | unit (vitest) | `npx vitest run src/lib/history.test.ts` | ✅ (extend) |
| Visibility | BoardRow week-0 text "… vs end of last season" | manual/visual + svelte-check | `npm run check` | — |
| MODEL-16 | BACKTEST_LOG row with fitted weight, wk0 Δ, fold-sign consistency (k/19) | manual (command output pasted) | `uv run fgs backtest --draft` | — |

### Sampling Rate
- **Per task commit:** the quick command for the touched side.
- **Per wave merge:** the full pipeline pytest plus web `npm test`.
- **Phase gate:** full suites green, `uv run fgs backtest --draft` output recorded in BACKTEST_LOG and weights.yaml, and `uv run fgs export` builds.

### Wave 0 Gaps
- [ ] `pipeline/tests/test_draft.py`: synthetic builders for team_games standings and draft rounds; real-cache acceptance (skip when cache missing)
- [ ] Fixture: tiny `draft_values` (picks 1..N) for unit tests
- [ ] Extend `web/src/lib/history.test.ts` with `connectors()` cases


**Approval:** approved 2026-11-11 (autonomous)

## Plan-checker notes for executors (2026-11-11)
- 07-01: derivable draft years = years present in picks (skip e.g. 2027 with no picks); add test.
- 07-03 T1: scope the allow_holdout grep to the draft_* function sources (inspect.getsource), not the whole file.
- 07-03 T3: diff weights.yaml against a recorded pre-edit SHA/BEFORE snapshot, not HEAD~1.

---
phase: 1
slug: data-foundation-elo-core
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-11-11
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from 01-RESEARCH.md § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.2.0 (dev dependency in `pipeline/pyproject.toml`) |
| **Config file** | `pipeline/pyproject.toml` `[tool.pytest.ini_options] testpaths=["tests"]` — Wave 0 installs |
| **Quick run command** | `cd pipeline && uv run pytest -q tests/test_elo.py tests/test_franchises.py` |
| **Full suite command** | `cd pipeline && uv run fgs build && uv run fgs check && uv run pytest -q` |
| **Estimated runtime** | quick ~2s; full ~30s (first run downloads ~0.5MB schedules) |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| DATA-01 | Ingest writes cache; re-run reads cache with no network | unit | `uv run pytest tests/test_ingest.py -x` | ❌ W0 | ⬜ pending |
| DATA-01 | Cached frame covers 1999..current with required columns | integration | `uv run pytest tests/test_checks.py -k columns` | ❌ W0 | ⬜ pending |
| DATA-02 | OAK/SD/STL normalize; unknown code fails; 32 canonical | unit | `uv run pytest tests/test_franchises.py` | ❌ W0 | ⬜ pending |
| DATA-02 | LV/LAC/LA/WAS continuous 1999–2026 | integration | `uv run pytest tests/test_checks.py -k continuity` | ❌ W0 | ⬜ pending |
| DATA-03 | season_config: 31/32 teams, 16/17 games, 12/14 playoff teams, divisions | integration | `uv run pytest tests/test_checks.py -k "config or divisions"` | ❌ W0 | ⬜ pending |
| DATA-04 | Tie=0.5, neutral=no HFA, null-result skipped | unit | `uv run pytest tests/test_elo.py -k "tie or neutral or unplayed"` | ❌ W0 | ⬜ pending |
| DATA-04 | BUF/CIN 2022 = 16 accepted; others 16/17 | integration | `uv run pytest tests/test_checks.py -k games_per_team` | ❌ W0 | ⬜ pending |
| DATA-07 | `fgs check` exit 0 on real data, 1 on injected bad code | integration | `uv run pytest tests/test_checks.py -k check_cli` | ❌ W0 | ⬜ pending |
| MODEL-01 | MOV mult exact, zero-sum, regression, expansion seeds | unit | `uv run pytest tests/test_elo.py` | ❌ W0 | ⬜ pending |
| MODEL-01 | 2026 top-5 winning records, bottom-5 losing; mean ≈ 1505 | integration | `uv run pytest tests/test_checks.py -k elo_sanity` | ❌ W0 | ⬜ pending |
| MODEL-02 | Grid complete, no null elo, bye carries forward, week 0 post-regression | unit+integration | `uv run pytest tests/test_snapshots.py` | ❌ W0 | ⬜ pending |
| MODEL-02 | `fgs elo --season 2026 --week 0 --top 32` prints 32 rows | smoke | `uv run fgs elo --season 2026 --week 0 --top 32` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pipeline/pyproject.toml` — uv project, pytest config, `fgs` script entry
- [ ] `pipeline/tests/conftest.py` — `synthetic_games()` fixture + `real_games` fixture (skips if cache missing)
- [ ] `pipeline/tests/test_elo.py`, `test_franchises.py`, `test_snapshots.py`, `test_checks.py`, `test_ingest.py`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Current 2026 ranking "looks plausible" | MODEL-01 | Judgment call | `uv run fgs elo --season 2026 --week 9` and eyeball top/bottom 5 vs records |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-11-11 (autonomous)

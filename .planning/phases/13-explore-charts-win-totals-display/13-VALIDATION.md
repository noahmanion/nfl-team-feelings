---
phase: 13
slug: explore-charts-win-totals-display
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-11-11
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Source: 13-RESEARCH.md § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (web, incl. SSR via `svelte/server`); pytest via uv (pipeline) |
| **Config file** | `web/vite.config.ts`; `pipeline/pyproject.toml` |
| **Quick run command** | `source ~/.nvm/nvm.sh && nvm use 24 >/dev/null && cd web && npx vitest run src/lib/<file>.test.ts` |
| **Full suite command** | `source ~/.nvm/nvm.sh && nvm use 24 >/dev/null && cd web && npm test && npm run check && npm run build` (+ `cd pipeline && uv run pytest -q` when the pipeline is touched) |
| **Estimated runtime** | ~30s web; ~150s pipeline |

---

## Sampling Rate

- **After every task commit:** Run the quick vitest file(s) touched; for the pipeline task, `uv run pytest tests/test_export.py -q -k expectation` plus `tests/test_golden_scores.py`
- **After every plan wave:** Run the full web suite (and the full pipeline suite if that wave touched the pipeline)
- **Before `/gsd:verify-work`:** Both full suites green, golden pin unchanged, Playwright sweep done
- **Max feedback latency:** 150 seconds

---

## Per-Task Verification Map

Plans fill in task IDs. Requirement-level map:

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| EXPL-02 | explore route parse, `exploreHash` | unit | `npx vitest run src/lib/router.test.ts` | ✅ extend | ⬜ pending |
| EXPL-02 | regOnly, join, league means, ranks, domains, diagonals, signed format, height, empty states | unit | `npx vitest run src/lib/explore.test.ts` | ❌ W0 | ⬜ pending |
| EXPL-02/03 | `tapAction` touch arming | unit | `npx vitest run src/lib/explore.test.ts` | ❌ W0 | ⬜ pending |
| EXPL-03 | win% (ties), OLS `fitLine`, residuals, dek, gap format | unit | `npx vitest run src/lib/explore.test.ts` | ❌ W0 | ⬜ pending |
| EXPL-03 | no "luck" wording on Explore | static grep test | `npx vitest run src/lib/noLuck.test.ts` | ❌ W0 | ⬜ pending |
| DATA-03 | team-file `expectation` block (sources by era, 1 dp, reg_games incl. 2022 BUF/CIN = 16) | pytest | `cd pipeline && uv run pytest tests/test_export.py -q -k expectation` | ✅ extend | ⬜ pending |
| DATA-03 | golden pin unchanged | regression | `cd pipeline && uv run pytest tests/test_golden_scores.py -q` | ✅ | ⬜ pending |
| DATA-03 | pace, finished, ticks, label selection (used / display-only / opener / model-only) | unit | `npx vitest run src/lib/winTotals.test.ts` | ❌ W0 | ⬜ pending |
| DATA-03 | ChartFrame `source` prop | SSR unit | `npx vitest run src/lib/chartFrame.test.ts` | ✅ extend | ⬜ pending |
| D-24 | readable rank delta | unit | `npx vitest run src/lib/format.test.ts` | ✅ extend | ⬜ pending |
| visual | charts render, click to navigate, 375 no h-scroll, dark legible, D-22/23/25 | Playwright | `verify_ui.py` / Playwright MCP | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `web/src/lib/explore.test.ts`: EXPL-02/03 pure logic and tapAction
- [ ] `web/src/lib/winTotals.test.ts`: DATA-03 pace and labels
- [ ] `web/src/lib/noLuck.test.ts`: D-15 wording guard
- [ ] `pipeline/tests/test_export.py`: `test_expectation_*`
- [ ] Phase verify harness (adapted from `12-*/verify_ui.py`) or a Playwright MCP sweep

Tests are written alongside each lib module (same task), not as separate stubs.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual look of scatters (logo legibility, label collisions) in light/dark at 1280/375 | EXPL-02/03 | aesthetic judgment | Playwright screenshots, ≤6 saved to `screenshots/` |
| Tap-to-tip then tap-to-navigate on a real phone | EXPL-02/03 | real touch hardware | Open `#/explore` on a phone, tap a logo twice |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 150s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

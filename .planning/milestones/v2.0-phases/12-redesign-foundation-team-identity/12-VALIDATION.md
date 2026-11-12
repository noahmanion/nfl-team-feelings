---
phase: 12
slug: redesign-foundation-team-identity
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-11-11
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from 12-RESEARCH.md "Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest 5.1 (node env, Svelte SSR via `svelte/server`); Python Playwright for visual/e2e |
| **Config file** | none (vitest reads `web/vite.config.ts`) |
| **Quick run command** | `source ~/.nvm/nvm.sh && nvm use 24 >/dev/null && cd web && npx vitest run src/lib/<file>.test.ts` |
| **Full suite command** | `source ~/.nvm/nvm.sh && nvm use 24 && cd web && npm test && npm run check && npm run build` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** the touched module's quick run, plus `npm run check` when a `.svelte` file changed
- **After every plan wave:** full suite command
- **Before `/gsd:verify-work`:** full suite green + Playwright screenshots/behavior checks
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

Per-plan automated commands (all green at 12-07):

| Plan | Automated command | Status |
|------|-------------------|--------|
| 12-01 | `npx vitest run src/lib/brand.test.ts src/lib/plotTheme.test.ts && npm run check` | ✅ green |
| 12-02 | `npx vitest run src/lib/logos.test.ts src/lib/teamNames.test.ts src/lib/teamLogo.test.ts` | ✅ green |
| 12-03 | `npx vitest run src/lib/chartFrame.test.ts src/lib/plotTheme.test.ts` | ✅ green |
| 12-04 | `npm test && npm run check && npm run build` (charts in ChartFrame + plotTheme) | ✅ green |
| 12-05 | `npm test && npm run check && npm run build` (board + chrome) | ✅ green |
| 12-06 | `npm test && npm run check && npm run build` (team, records, methodology) | ✅ green |
| 12-07 | `npm test && npm run check && npm run build`; `VITE_LOGOS=off npm run build` + `verify_ui.py --logos-off`; `npm run build` + `verify_ui.py` | ✅ green |

Requirement → test map:

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| DESIGN-01 | Fontsource imports, `--font-mono`, no font CDN, no 538 marks in web/src | unit (raw scan) | `npx vitest run src/lib/brand.test.ts` | ✅ | ✅ green |
| DESIGN-01 | Build bundles Inter woff2 | build smoke | `npm run build && ls dist/assets/*.woff2` | n/a | ✅ green |
| DESIGN-02 | plotTheme contract + all Plot charts use it, no Plot `title` | unit | `npx vitest run src/lib/plotTheme.test.ts` | ✅ | ✅ green |
| DESIGN-02 | ChartFrame headline/dek/SOURCE/NOTES | unit (SSR) | `npx vitest run src/lib/chartFrame.test.ts` | ✅ | ✅ green |
| DESIGN-03 | Editorial look, 5 pages, light+dark, 1280+375 | manual-visual (Playwright) | `verify_ui.py` -> 24 PNGs in `screenshots/` | ✅ | ✅ green |
| DESIGN-04 | Existing 167 tests still pass | regression | `npm test` (212/212, 19 files) | ✅ | ✅ green |
| DESIGN-04 | 375px no h-scroll; pin, scrubber, copy-link | e2e (Playwright) | `python3 verify_ui.py` | ✅ | ✅ green |
| LOGO-02 | `logoSrc`/`logosEnabled`, 32 sm derivatives | unit | `npx vitest run src/lib/logos.test.ts` | ✅ | ✅ green |
| LOGO-02 | TeamLogo branches (img / chip) | unit (SSR) | `npx vitest run src/lib/teamLogo.test.ts` | ✅ | ✅ green |
| LOGO-02 | Real image-error → chip | e2e | `verify_ui.py` (route 404 KC.png) | ✅ | ✅ green |
| LOGO-03 | Era boundaries, WAS eras, HOU guard, eraText | unit | `npx vitest run src/lib/teamNames.test.ts` | ✅ | ✅ green |
| LOGO-03 | "San Diego Chargers" on LAC 2010 team page | e2e | `verify_ui.py` (text assertion) | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `web/src/lib/plotTheme.test.ts`
- [x] `web/src/lib/logos.test.ts`
- [x] `web/src/lib/teamNames.test.ts`
- [x] `web/src/lib/teamLogo.test.ts`
- [x] `web/src/lib/chartFrame.test.ts`
- [x] `web/src/lib/brand.test.ts` (fonts, no CDN, no 538)
- [x] Playwright check (MCP or Python) for screenshots, 375px overflow, behaviors, logo 404

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Editorial look & dark-mode logo legibility | DESIGN-03 | Aesthetic judgment | Done in 12-07 (week-nav dot fix 00d2a74). Review screenshots at 1280/375 × light/dark for board, team, history, records, methodology |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-11-11 (12-07 sweep: verify_ui.py ALL PASS in both modes)

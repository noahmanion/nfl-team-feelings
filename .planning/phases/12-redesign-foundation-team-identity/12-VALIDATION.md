---
phase: 12
slug: redesign-foundation-team-identity
status: draft
nyquist_compliant: false
wave_0_complete: false
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

Filled in by the planner per PLAN task `<automated>` blocks. Requirement → test map:

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| DESIGN-01 | Fontsource imports, `--font-mono`, no font CDN, no 538 marks in web/src | unit (raw scan) | `npx vitest run src/lib/brand.test.ts` | ❌ W0 | ⬜ pending |
| DESIGN-01 | Build bundles Inter woff2 | build smoke | `npm run build && ls dist/assets/*.woff2` | n/a | ⬜ pending |
| DESIGN-02 | plotTheme contract + all Plot charts use it, no Plot `title` | unit | `npx vitest run src/lib/plotTheme.test.ts` | ❌ W0 | ⬜ pending |
| DESIGN-02 | ChartFrame headline/dek/SOURCE/NOTES | unit (SSR) | `npx vitest run src/lib/chartFrame.test.ts` | ❌ W0 | ⬜ pending |
| DESIGN-03 | Editorial look, 5 pages, light+dark, 1280+375 | manual-visual (Playwright) | screenshots in `screenshots/` | ❌ W0 | ⬜ pending |
| DESIGN-04 | Existing 167 tests still pass | regression | `npm test` | ✅ | ⬜ pending |
| DESIGN-04 | 375px no h-scroll; pin, scrubber, copy-link | e2e (Playwright) | Playwright script | ❌ W0 | ⬜ pending |
| LOGO-02 | `logoSrc`/`logosEnabled`, 32 sm derivatives | unit | `npx vitest run src/lib/logos.test.ts` | ❌ W0 | ⬜ pending |
| LOGO-02 | TeamLogo branches (img / chip) | unit (SSR) | `npx vitest run src/lib/teamLogo.test.ts` | ❌ W0 | ⬜ pending |
| LOGO-02 | Real image-error → chip | e2e | Playwright route 404 for one logo | ❌ W0 | ⬜ pending |
| LOGO-03 | Era boundaries, WAS eras, HOU guard, eraText | unit | `npx vitest run src/lib/teamNames.test.ts` | ❌ W0 | ⬜ pending |
| LOGO-03 | "San Diego Chargers" on LAC 2010 team page | e2e | Playwright text assertion | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `web/src/lib/plotTheme.test.ts`
- [ ] `web/src/lib/logos.test.ts`
- [ ] `web/src/lib/teamNames.test.ts`
- [ ] `web/src/lib/teamLogo.test.ts`
- [ ] `web/src/lib/chartFrame.test.ts`
- [ ] `web/src/lib/brand.test.ts` (fonts, no CDN, no 538)
- [ ] Playwright check (MCP or Python) for screenshots, 375px overflow, behaviors, logo 404

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Editorial look & dark-mode logo legibility | DESIGN-03 | Aesthetic judgment | Review screenshots at 1280/375 × light/dark for board, team, history, records, methodology |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

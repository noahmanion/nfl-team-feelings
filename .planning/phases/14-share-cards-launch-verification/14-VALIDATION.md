---
phase: 14
slug: share-cards-launch-verification
status: in-progress
nyquist_compliant: false
wave_0_complete: true
created: 2026-11-12
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Source: 14-RESEARCH.md "Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest 5.1.0 (existing suite: 23 files, 277 tests) |
| **Config file** | none (vite.config.ts; default include also matches `scripts/*.test.mjs`) |
| **Quick run command** | `cd web && source ~/.nvm/nvm.sh && nvm use 24 && npx vitest run src/lib/share.test.ts scripts/` |
| **Full suite command** | `cd web && source ~/.nvm/nvm.sh && nvm use 24 && npm test && npm run check && npm run build` |
| **Estimated runtime** | ~3 s quick; ~30 s full (build incl. share step) |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite green; after push, Vercel READY + D-25 crawler curl block
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

Task IDs filled by 14-03. Statuses reflect runs on 2026-11-12 (Node 24): quick run 65 tests green, full suite 342 tests green, `npm run check` 0 errors, build + verify_share.py ALL PASS.

| Task | Req | Behavior | Test Type | Automated Command | File Exists | Status |
|------|-----|----------|-----------|-------------------|-------------|--------|
| 14-02-T1 | SHARE-01 | `CARD` tokens equal light `:root` values in app.css | unit | `npx vitest run scripts/og-template.test.mjs` | ✅ | ✅ green |
| 14-02-T1 | SHARE-01 | All 7 band labels (incl. U+2019) render 1200×630 PNGs; glyph guard does not throw | unit | same | ✅ | ✅ green |
| 14-02-T1 | SHARE-01 | Raw `→`/emoji rejected by glyph guard; `cardRuns` arrow split renders mover detail | unit | same | ✅ | ✅ green |
| 14-02-T1 | SHARE-01 | `clampText` word-boundary clamp + `…` | unit | same | ✅ | ✅ green |
| 14-02-T2 | SHARE-01 | Logos-off / missing logo → chip card renders | unit | same | ✅ | ✅ green |
| 14-03-T1 | SHARE-01 | `buildShare()` in tmp dir: 32 team + N callout PNGs per target week, 1200×630, ≤300 KB, og-default.png | integration | `npx vitest run scripts/share.test.mjs` | ✅ | ✅ green |
| 14-01-T1 | SHARE-02 | Path/image builders, kebab type, calloutId, trailing slash | unit | `npx vitest run src/lib/share.test.ts` | ✅ | ✅ green |
| 14-01-T1 | SHARE-02 | `hasSharePage` launch gating (w8 false, w9 true, absent week false) | unit | same | ✅ | ✅ green |
| 14-01-T2 | SHARE-02 | `escapeHtml` hostile input; page HTML absolute og:image/og:url/canonical, twitter:card, safe hash in script | unit | same | ✅ | ✅ green |
| 14-03-T1 | SHARE-02 | Every emitted page's og:image file exists | integration | `npx vitest run scripts/share.test.mjs` | ✅ | ✅ green |
| 14-01-T2 | SHARE-02 | share.ts importable from plain Node 24 | smoke | `node --input-type=module -e "await import('./src/lib/share.ts')"` | ✅ | ✅ green |
| 14-03-T2 | SHARE-02 | Real build emits `dist/s/team/BUF/2026-w9/index.html` + `dist/og/team/BUF/2026-w9.png`; timing log | smoke | `npm run build && test -f dist/s/team/BUF/2026-w9/index.html && test -f dist/og/team/BUF/2026-w9.png` | n/a | ✅ green |
| 14-03-T2 | SHARE-02 | Share page redirects a browser to the hash route; crawler UA gets og:image; card served as image/png (vite preview) | e2e | `python3 ../.planning/phases/14-share-cards-launch-verification/verify_share.py` | ✅ | ✅ green |
| 14-01-T1 | SHARE-03 | Copy URL = share URL when `hasSharePage`, else `deepLink(hash)`; latest team view pins `meta.latest` week | unit | `npx vitest run src/lib/share.test.ts` | ✅ | ✅ green |
| 14-04-T1/T2 | SHARE-03 | Copy-link buttons (team header + callouts) use teamCopyUrl/calloutCopyUrl | build + browser | 14-04 plan verify (copycheck build, port 4174) | — | ⬜ pending (14-04) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `web/src/lib/share.test.ts` — SHARE-02/03 pure logic
- [x] `web/scripts/og-template.test.mjs` — SHARE-01 rendering, tokens, glyphs
- [x] `web/scripts/share.test.mjs` — buildShare integration in tmp dir
- [x] `tsconfig.app.json` `"allowImportingTsExtensions": true`
- [x] `npm install -D --save-exact satori@0.63.2 @resvg/resvg-js@2.6.2`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Copy-link button in team header + callouts copies share URL ("Link copied") | SHARE-03 | No component test infra (no jsdom) | Playwright/browser at `vite preview`: click, read clipboard/manual field |
| Production crawler fetch (facebookexternalhit, Twitterbot, Slackbot) → 200, absolute tags, image 200 | SHARE-02 | Needs deployed production | D-25 curl block after Vercel READY (in `14-HUMAN-UAT.md`) — ⬜ pending (orchestrator) |
| Slack / iMessage / X pastes; FB Sharing Debugger; LinkedIn Post Inspector | SC 4 | Real platforms, human accounts | `14-HUMAN-UAT.md` URLs — ⬜ pending (human UAT) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

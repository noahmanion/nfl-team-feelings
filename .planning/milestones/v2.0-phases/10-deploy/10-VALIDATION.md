---
phase: 10
slug: deploy
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-11-11
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest 5.1.0 (`web/src/lib/*.test.ts`) |
| **Config file** | none. Defaults come via `web/vite.config.ts` |
| **Quick run command** | `cd web && npm test && npm run check` |
| **Full suite command** | `cd web && npm test && npm run check && npm run build && ! grep -q '%SITE_ORIGIN%' dist/index.html` |
| **Estimated runtime** | ~30 seconds |

Run under Node 24 (`source ~/.nvm/nvm.sh && nvm use 24`). nvm's default is Node 20, which is too old for Vite 8.

---

## Sampling Rate

- **After every task commit:** run the quick command
- **After every plan wave:** run the full suite command
- **Before `/gsd:verify-work`:** the full suite and the production smoke checks must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

The task IDs are filled in by the planner. Required coverage per requirement:

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| DEPLOY-01 | engines and .nvmrc are pinned to 24 | static | `node -p "require('./web/package.json').engines.node"` prints `24.x`; `cat web/.nvmrc` prints `24` | ✅ | ⬜ pending |
| DEPLOY-01 | the production URL serves the site from root `web` on Node 24.x | smoke (prod) | `curl -s -o /dev/null -w '%{http_code}' $PROD/` returns 200; MCP `get_project` shows rootDirectory=web, nodeVersion=24.x | n/a | ⬜ pending |
| DEPLOY-02 | a `web/` push builds; a `.planning/`-only push is CANCELED | smoke (prod) | MCP `list_deployments` states for the two commits; `get_project` shows `commandForIgnoringBuildStep` | n/a | ⬜ pending |
| DEPLOY-03 | origin resolver order and trailing-slash strip | unit | `cd web && npx vitest run src/lib/siteOrigin.test.ts` | ❌ W0 | ⬜ pending |
| DEPLOY-03 | the built HTML has absolute og/twitter tags | build grep | `grep -E 'og:image" content="https://[^"]+/og-default.png' web/dist/index.html` | n/a | ⬜ pending |
| DEPLOY-03 | the og image is a 1200×630 PNG under 300 KB | static | `file web/public/og-default.png`; `stat -f%z` < 307200 | ❌ (created in phase) | ⬜ pending |
| DEPLOY-03 | footer disclaimer and "Data through" stamp | build grep + prod | `grep -l 'not affiliated with the NFL' web/dist/assets/*.js` | n/a | ⬜ pending |
| DEPLOY-03 | crawlers see the tags on prod | smoke (prod) | `curl -s -A facebookexternalhit/1.1 $PROD/ \| grep og:image`; `curl -sI $PROD/og-default.png` shows image/png | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `web/src/lib/siteOrigin.test.ts` covers the resolver: SITE_ORIGIN wins, the Vercel host gets `https://`, an empty value falls back, and a trailing slash is stripped

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Link-preview tool shows the card | DEPLOY-03 | Third-party unfurlers (opengraph.xyz, Slack) | Paste the production URL into opengraph.xyz and check the title, description and image |
| Every v1 route works on prod | DEPLOY-01 | Client-side hash routes | Open `#/`, `#/team/KC`, `#/history`, `#/records`, `#/methodology` on prod (or fetch the HTML and JSON) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

---
phase: 10-deploy
plan: 02
subsystem: infra
tags: [deploy, vercel, ignored-build-step, node]
requires: [10-01]
provides:
  - Vercel project nfl-team-feelings (prj_IHGS3ZnYxUGxXH59pewocdzc8ovd), Git-linked to noahmanion/nfl-team-feelings, production branch main
  - Production URL https://nfl-team-feelings.vercel.app/
  - Ignored-build step scoped to web/
affects: [14]
tech-stack:
  added: [Vercel Git integration (Hobby)]
  patterns:
    - "Create the project without the ignore command, get one READY prod deploy, then set the ignore command (avoids a first-deploy cancel)"
key-files:
  created: []
  modified:
    - README.md
    - .planning/PROJECT.md
decisions:
  - "Deployment protection changed from all_except_custom_domains (the team default, which would have put the *.vercel.app production alias behind Vercel login) to prod_deployment_urls_and_all_previews (Standard): the production domain is public; per-deployment and preview URLs stay protected"
  - "create_git_project called with deploy:false; framework/build/output/nodeVersion set via update_project; first prod deploy triggered via create_deployment at the pushed SHA"
  - "FALLBACK_ORIGIN unchanged: nfl-team-feelings.vercel.app is the project's verified production domain"
metrics:
  duration: ~5min
  completed: 2026-11-11
  tasks: 3
---

# Phase 10 Plan 02: Deploy to Vercel Summary

The site is live at **https://nfl-team-feelings.vercel.app/**. It builds from `web/` on Node 24.x, push-to-main redeploys automatically, and commits that don't touch `web/` are skipped by the ignored-build step.

## Task 1: push and create the project
- Pushed `main` f0becb7..1602905 (the last 10-01 web commit is d80b69c).
- `create_git_project` (team_E1xIuSsRXZzQn824H0Sb2J0S, repo noahmanion/nfl-team-feelings, projectName nfl-team-feelings, rootDirectory web, deploy:false) created project `prj_IHGS3ZnYxUGxXH59pewocdzc8ovd`, linked to GitHub with production branch main. The Vercel GitHub app was already installed, so no user action was needed.
- `update_project` set framework `vite`, buildCommand `npm run build`, outputDirectory `dist`, nodeVersion `24.x` and rootDirectory `web`. The project read back framework vite and nodeVersion 24.x.
- [Rule 2: missing critical setting] The team default protection `all_except_custom_domains` would have protected the `*.vercel.app` production alias. I switched it to `prod_deployment_urls_and_all_previews` (Standard Protection).

## Task 2: READY production deploy and the domain
- Triggered `create_deployment` with target production and gitSource github noahmanion/nfl-team-feelings, ref main, sha 1602905. It produced **dpl_3KixvoWnHMr2x6wwg6gHtuXaoycE, state READY**, built from commit 1602905.
- The build log shows the clone at 1602905, `npm install` with 108 packages, then `vite build` (index.html 2.03 kB, JS 397.56 kB). There was no Node-version warning, so the project setting (24.x) and engines (24.x) agree.
- Domain: `list_project_domains` lists `nfl-team-feelings.vercel.app` (verified). The deployment aliases are `nfl-team-feelings.vercel.app`, `nfl-team-feelings-noah-manions-projects.vercel.app` and `nfl-team-feelings-git-main-…`. PROD is `https://nfl-team-feelings.vercel.app`, which already equals `FALLBACK_ORIGIN`, so the fallback commit wasn't needed.

## Task 3: ignore step, production checks, URL record, skip proof
- `update_project` set `commandForIgnoringBuildStep` to the literal `git diff --quiet ${VERCEL_GIT_PREVIOUS_SHA:-HEAD^} HEAD -- .`. The MCP project summary doesn't echo this field, but the build log of the next deployment printed the command character for character (below).
- Local depth-10 clone simulation, run from web/: a web change against 61093f9 exits **1** (build), and no change exits **0** (skip).
- Production checks (curl, default and `facebookexternalhit/1.1` user agents):
  - `/` returns 200.
  - The title is "Feel-Good Score: how should you feel about your NFL team?".
  - The page has canonical, og:url, og:image, twitter:card and twitter:image, all absolute on https://nfl-team-feelings.vercel.app.
  - `/data/{meta,latest,history,records,methodology,callouts}.json` and `/data/teams/KC.json` each return `200 application/json`.
  - `/data/meta.json` has `cache-control: public, max-age=0, must-revalidate`, so no long max-age.
  - `/og-default.png` returns `200 image/png` at 24,340 bytes.
  - The main JS bundle contains "not affiliated with the NFL" and "Data through".
- Commit a533993 `docs(10-02): record production URL` touches only README.md and .planning/PROJECT.md. The push auto-created production deployment **dpl_9oZ1dkFZD4R7abBJ6BQzfuiLVQWN**. Its build log shows `Running "git diff --quiet ${VERCEL_GIT_PREVIOUS_SHA:-HEAD^} HEAD -- ."`, then "The deployment was canceled because the Ignored Build Step command returned exit code 0." That makes it **CANCELED**, and production keeps serving dpl_3Kixvo.

## DEPLOY-02 live evidence
- An auto-redeploy on push was observed: the a533993 push created a deployment without any manual trigger.
- A non-web commit was skipped (CANCELED, above).
- **A `web/` change builds after the ignore command is set:** the push of 5a41881..4179b76 included the code-review fixes 3919854 (SiteFooter) and aa34d86 (siteOrigin). The HEAD commit 4179b76 itself is docs-only. That push produced production deployment **dpl_EzQueyJyy9ovpuBEkuPytZqbsgAg, state READY**. So diffing against `VERCEL_GIT_PREVIOUS_SHA` (the last deployed SHA, 1602905) catches web changes in earlier commits of a multi-commit push, as D-03 intended.

## Deviations from Plan
- **[Rule 2] Deployment protection.** Changed to Standard so the production domain is public (see decisions).
- **Ignore-command read-back.** I verified it through the build log instead of `get_project`, because the MCP summary omits the field.

## Self-Check: PASSED
- Production URL returns 200, and the share tags are visible to crawlers.
- The README "Live site" line and the PROJECT.md Hosting bullet plus Key Decisions row are present.
- No changes under `pipeline/`, and no `vercel.json`.

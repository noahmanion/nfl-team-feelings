---
phase: 14-share-cards-launch-verification
verified: 2026-11-12T01:10:00Z
status: human_needed
score: 3/3 automated must-haves verified (SC4 pending human UAT)
overrides_applied: 0
human_verification:
  - test: "Slack, iMessage, X paste of team and callout share URLs on the deployed site"
    expected: "Large 1200x630 card and matching og:title"
    why_human: "Needs deployed production domain and real platform scrapers"
  - test: "Facebook Sharing Debugger and LinkedIn Post Inspector"
    expected: "200, absolute og:image, no missing-tag warnings (FB 403 is a known Vercel limitation)"
    why_human: "External services, deployed site"
  - test: "Browser click on share URL lands on matching hash route"
    expected: "BUF -> /#/team/BUF/2026/9; CLE callout -> /#/team/CLE/2026/9"
    why_human: "Needs deployed site (redirect script verified statically only)"
  - test: "Pre-launch (week 8) callout copy-link keeps hash link"
    expected: "Hash link copied"
    why_human: "Live UI interaction"
---

# Phase 14: Share Cards and Launch Verification Report

**Phase Goal:** A link to any team or current-season callout unfurls as a rich, on-brand preview on real social platforms.
**Status:** human_needed (automated checks all pass; SC4 is the expected human/deploy step, see 14-HUMAN-UAT.md)
**Re-verification:** No, initial

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Build produces 1200x630 images for all 32 teams and current-season callouts, redesign fonts/colors/local logos, labels and apostrophes right | VERIFIED | `npm run build` printed "rendered 45 cards". dist/og has 32 team PNGs + 12 callout PNGs, plus og-default.png. `file` reports 1200 x 630 PNG. I viewed BUF and CLE cards: Inter/Plex Mono, local logos, "Buying the jersey", "WORRIED", headline correct. Apostrophe in the share pages is present as an HTML entity or curly quote. |
| 2 | Each image has a static share page at a real path with season+week, absolute og:image on production domain, lands on matching hash route | VERIFIED (static) | 44 pages in dist/s (32 `/s/team/XX/2026-w9/`, 12 `/s/c/2026/9/...`). Pages carry og:image and twitter:image as `https://nfl-team-feelings.vercel.app/og/...png`, with width/height/alt, canonical and og:url. The inline script redirects non-crawlers to `/#/team/BUF/2026/9` and `/#/team/CLE/2026/9`. Actual browser landing is for UAT. |
| 3 | Copy-link buttons on team pages and callouts copy share URL where one exists, else hash link | VERIFIED | TeamPage.svelte uses `teamCopyUrl`, CalloutCard.svelte uses `calloutCopyUrl` (src/lib/share). Both fall back to `deepLink`. copyLink and share tests pass. |
| 4 | Real Slack/iMessage/X pastes and FB/LinkedIn debuggers show correct card | HUMAN NEEDED | Requires production deploy and humans. 14-HUMAN-UAT.md has status pending, with all test results blank. |

**Score:** 3/3 automatable truths verified; truth 4 deferred to human UAT by design.

## Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Unit tests | `npm test` | 26 files, 364 tests passed | PASS |
| Type check | `npm run check` | 0 errors, 0 warnings | PASS |
| Build | `npm run build` | 45 cards, 44 pages, largest card 54 KB | PASS |

## Requirements Coverage

| Requirement | Source Plans | Status | Evidence |
|-------------|--------------|--------|----------|
| SHARE-01 | 14-02, 14-03 | SATISFIED | 45 cards at 1200x630, visually checked |
| SHARE-02 | 14-01, 14-03 | SATISFIED (static; live crawler check pending) | 44 share pages with absolute og tags and JS redirect |
| SHARE-03 | 14-01, 14-04 | SATISFIED | Copy buttons wired to share URL with hash fallback |

All three IDs appear in PLAN frontmatter and in REQUIREMENTS.md, and no orphaned Phase 14 requirements were found.

## Anti-Patterns

No TBD, FIXME or XXX debt markers in web/scripts or web/src, apart from the "XXX" fake-franchise test fixtures. The four code-review warnings (WR-01 to WR-04) were fixed, and 14-REVIEW-FIX reports a clean state.

## Gaps Summary

No code gaps. Remaining items are the deployed-site checks (SC4): the orchestrator's production deploy and crawler-UA curl checks, then the platform pastes and debugger runs in 14-HUMAN-UAT.md. Note that the share-card images were verified locally only, and Facebook's cached og-default.png needs a "Scrape Again".

_Verified: 2026-11-12T01:10:00Z_
_Verifier: Claude (gsd-verifier)_

## Automated pre-check result (2026-11-12, production deploy dpl_6CcU2DchecQ2gPGuczhjRBQ1NZVf @ d706dcb, READY)

All 16 checks passed: 2 pages (`/s/team/BUF/2026-w9/`, `/s/c/2026/9/CLE-worried/`) x 4 UAs (`facebookexternalhit/1.1`, `Twitterbot/1.0`, `Slackbot-LinkExpanding 1.0`, `LinkedInBot/1.0`) returned 200 with `twitter:card=summary_large_image`, absolute `og:url` (= the share page) and absolute `og:image` on `https://nfl-team-feelings.vercel.app`; each og:image returned `200 image/png`. Non-slash form (`-L`) 200; plain curl 200 (no Vercel bot challenge observed); `/og-default.png` 200 (50 KB, new satori card). Redirect script targets `#/team/BUF/2026/9`. Caveat: curl with a crawler UA cannot detect UA+IP-based blocking of the real Meta crawler, so test 4 (FB Sharing Debugger) remains required.

Vercel build log: vite 722 ms; share step 45 cards in 1.71 s (38 ms/card), rss 273 MB; build completed in 5 s; projected full season ~24 s.

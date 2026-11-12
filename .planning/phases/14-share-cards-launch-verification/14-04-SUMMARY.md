---
phase: 14-share-cards-launch-verification
plan: 04
subsystem: web/share
tags: [share, copy-link, svelte, playwright, a11y]
requires: [web/src/lib/share.ts teamCopyUrl/calloutCopyUrl (14-01), web/src/lib/copyLink.ts]
provides: [web/src/components/CopyLinkButton.svelte, team header Copy link button, share-aware callout copy, verify_copy.py]
affects: [web/src/components/CalloutCard.svelte, web/src/components/CalloutCards.svelte, web/src/components/TeamPage.svelte, 14-VALIDATION.md]
tech-stack:
  added: []
  patterns: [shared copy button computing its URL at click time via a getUrl closure]
key-files:
  created: [web/src/components/CopyLinkButton.svelte, .planning/phases/14-share-cards-launch-verification/verify_copy.py]
  modified: [web/src/components/CalloutCard.svelte, web/src/components/CalloutCards.svelte, web/src/components/TeamPage.svelte, .planning/phases/14-share-cards-launch-verification/14-VALIDATION.md]
decisions:
  - "CopyLinkButton takes getUrl() and calls it at click time, so the copied URL always matches the week on screen. The share-vs-hash choice stays in share.ts."
  - "The visually hidden status is now positioned inside .copy-link (position:relative), not the card"
metrics:
  duration: ~8min
  completed: 2026-11-12
  tasks: 2
  files: 6
---

# Phase 14 Plan 04: Copy links point at share pages Summary

Both copy-link placements now go through one shared `CopyLinkButton.svelte`: the callout cards and a new "Copy link to {name}" button in the team page header. From the launch week (2026 w9) on, they copy `/s/team/{FR}/{s}-w{w}/` or `/s/c/{s}/{w}/{FR}-{type}/` share URLs. Before that week they copy the hash deep link exactly as before. The WR-05 behavior (status, re-announce, manual fallback) carries over unchanged.

## Tasks

| Task | Name | Commit |
|------|------|--------|
| 1 | Extract CopyLinkButton; wire CalloutCard (+meta) and TeamPage header | 320b457 |
| 2 | verify_copy.py browser check | fbf0150 |

## Browser verification (verify_copy.py, isolated build on port 4174, Chromium)

```
PASS 1a header button 'Copy link to Buffalo Bills' exists - count=1
PASS 1b latest team copy -> share URL - 'http://localhost:4174/s/team/BUF/2026-w9/' / 'Link copied'
PASS 2 pre-launch team copy -> hash link - 'http://localhost:4174/#/team/BUF/2026/8'
PASS 3 latest callout copy -> share URL - 'http://localhost:4174/s/c/2026/9/CLE-worried/'
PASS 5 repeat click still ends 'Link copied' - 'Link copied'
PASS 4 pre-launch callout copy -> hash link - 'http://localhost:4174/#/team/CLE/2026/8'
PASS 6 375px team page has no horizontal scroll - scrollWidth=375
ALL PASS
```

I started the preview server in the background, ran the script, then stopped the server; port 4174 was confirmed free afterwards. Because this passed, 14-VALIDATION.md now has `nyquist_compliant: true` (`wave_0_complete` was already true), both SHARE-03 14-04 rows are green, and sign-off is approved.

## Full suite (Node 24, after both tasks)

- `npm test`: 26 files, 342 tests passed
- `npm run check`: 0 errors, 0 warnings
- `npm run build`: vite build OK; share step rendered 45 cards and wrote 44 pages

## Deviations from Plan

None. The plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: web/src/components/CopyLinkButton.svelte
- FOUND: .planning/phases/14-share-cards-launch-verification/verify_copy.py
- FOUND: commits 320b457, fbf0150

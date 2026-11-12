---
phase: 14
reviewed: 2026-11-12
baseline: 14-UI-SPEC.md
overall_score: 20
max_score: 24
fixes_applied: [1, 2, 3]
---

# Phase 14 — UI Review

**Overall: 20/24** (audited against 14-UI-SPEC.md from the 4 committed sample cards, built `dist/s/**` HTML and Svelte sources; auditor returned inline, orchestrator recorded it).

| Pillar | Score | Key finding |
|---|---|---|
| Copywriting | 3/4 | Callout share description ran the mover detail into the week stamp (no separator) |
| Visuals | 3/4 | Callout card top-heavy (~150px void on short claims); site card widows |
| Color | 4/4 | Light tokens only, no accent/emoji on cards, stripe/tint as specified |
| Typography | 3/4 | 4 sizes / 2 weights as contracted; site-card headline + dek widows |
| Spacing | 4/4 | 64px safe area holds; 4px scale respected |
| Experience Design | 3/4 | "Link copied" status is subtle and never clears (spec-mandated pattern from Phase 8/12) |

## Top fixes

1. **Callout description run-on** (WARNING, ~10 min). FIXED: `calloutShareMeta` appends a period when the detail lacks terminal punctuation; test added.
2. **Callout card top-heavy** (WARNING, ~20 min). FIXED: callout body grows and the claim block centers in the free space (`og-template.mjs`); sample re-rendered.
3. **Site-card widows** (WARNING, ~15 min). FIXED: explicit balanced line breaks for headline ("How should you feel / about your NFL team?") and dek; sample re-rendered.
4. **Copy feedback subtle / never clears** (WARNING, ~20 min). DEFERRED: the status pattern is the shared Phase 8/12 contract (WR-05); changing it is a cross-page UX change, not a Phase 14 fix.
5. **Mover alt text repetitive / unitless** ("Minnesota Vikings: Vikings −17. …") (WARNING, ~15 min). DEFERRED: low impact; candidate for a later copy pass.

## Minor notes

- Neutral band (mood-3 gray) stripe reads close to "unstyled" — palette-inherent.
- Crawler-UA regex is a maintenance list (unknown JS-running previewers follow the redirect and show the site card).
- Team-page button 1px `--border` outline < 3:1 non-text contrast — carried from Phase 12.

## Verification after fixes

`npm test` 365 passed, `npm run check` 0 errors, `npm run build` OK (45 cards in 0.69 s, 44 pages, largest 54 KB).

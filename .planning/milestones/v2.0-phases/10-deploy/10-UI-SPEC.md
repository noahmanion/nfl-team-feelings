---
phase: 10
slug: deploy
status: approved
reviewed_at: 2026-11-11
shadcn_initialized: false
preset: none
created: 2026-11-11
---

# Phase 10 — UI Design Contract

> Minimal contract. The only visible change in this phase is in the footer. Everything else is `<head>` tags and one static share image. **No restyle; the redesign is Phase 12.** Every value below comes from the existing tokens in `web/src/app.css` (02-UI-SPEC). Add no new tokens.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none (Svelte 5 + Vite, hand-rolled tokens; the shadcn gate doesn't apply because the stack isn't React) |
| Preset | not applicable |
| Component library | none |
| Icon library | none (this phase adds no icons) |
| Font | `--font-sans` (system-ui stack) on the site; the OG image uses macOS `/System/Library/Fonts/HelveticaNeue.ttc` (a throwaway Pillow script) |

---

## Spacing Scale

Existing tokens, unchanged: xs 4 / sm 8 / md 16 / lg 24 / xl 32 / 2xl 48 / 3xl 64.

Footer usage in this phase:
- `.site-footer` keeps `margin-top: var(--space-xl)`.
- The disclaimer line sits under the stamp line with `margin-top: var(--space-xs)`. On the fatal-error page there is no stamp line, so the disclaimer gets no extra top margin.

OG image (raster px, all multiples of 8): 96px left/right padding; 24px gap between the wordmark and the tagline; an 8px-tall accent bar, 96px wide, placed 32px above the wordmark.

Exceptions: none.

---

## Typography

Existing tokens, unchanged:

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 16px | 400 | 1.5 |
| Label | 14px | 400 | 1.4 |
| Heading | 20px | 600 | 1.25 |
| Display | 28px | 600 | 1.1 |

- The whole footer, disclaimer included, uses Label: `--text-label`, `--lh-label`, `--weight-regular`, color `--text-muted`. It inherits these from the existing `.site-footer` rule.
- OG image (fixed raster, outside the CSS scale): the wordmark "Feel-Good Score" at 96px Bold (Helvetica Neue's semibold equivalent), and the tagline at 44px Regular. Two weights only.

---

## Color

Existing tokens, unchanged (light / dark):

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `--bg` #f6f6f3 / #121316 | Page background |
| Secondary (30%) | `--surface` #ffffff / #1b1d21 | Cards (no change this phase) |
| Accent (10%) | `--accent` #3446d4 / #8f9cff | See reserved list |
| Destructive | `--danger` #b42318 / #ff8a7a | Not used this phase |

Accent reserved for (in this phase): the "nflverse" text link in the disclaimer (the global `a` rule plus `:focus-visible` outline), and the 96×8 bar on the OG image. Nothing else.

OG image palette uses the light theme only: background `#f6f6f3`, wordmark `#1b1b1f` (`--text`), tagline `#5b5d63` (`--text-muted`), bar `#3446d4` (`--accent`). No logos, no NFL marks, no team colors, no emoji, no gradients.

---

## Component Contract: `SiteFooter.svelte`

- `meta` becomes optional: `{ meta?: Meta }`.
- In `App.svelte`, render `<SiteFooter meta={status === 'ready' ? meta : undefined} />` **unconditionally**, so the footer appears on every route, the fatal-error page included.
- Markup has two `<p>` elements:
  1. **Stamp line** (only when `meta` is present). Keep the existing `.part` spans and their responsive behavior: stacked below 1024px; inline at 1024px and up, joined with the existing `.second::before ' · '`.
     - Part 1: `Last updated {formatDate(meta.generated_at)}`
     - Part 2: `Data through {formatDateOnly(meta.data_through)}` (the "· Source: nflverse" suffix is **removed**)
  2. **Disclaimer line** (always): `Unofficial fan project — not affiliated with the NFL. Data: <a href="https://github.com/nflverse">nflverse</a>.`
     - Use a real em dash (U+2014) with a space on each side. The final period sits outside the link.
     - Same tab, no `target="_blank"` (matches the existing link).
- Responsive: the disclaimer is one wrapping line at every width. Add no new breakpoints; it just has to wrap cleanly at 320px.
- No other visible change on any page. Header, board, and all other pages stay untouched.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Disclaimer (footer, every page) | Unofficial fan project — not affiliated with the NFL. Data: nflverse. |
| Freshness stamp (footer, when data loaded) | Data through {Mon D, YYYY} (existing `formatDateOnly`) |
| `<title>` | Feel-Good Score: how should you feel about your NFL team? |
| `meta description` / `og:description` / `twitter:description` | Every NFL team, ranked by how good their fans should feel right now. A momentum-weighted, backtested score with a mood label on top. |
| `og:title` / `twitter:title` | Feel-Good Score: how should you feel about your NFL team? |
| `og:site_name` | Feel-Good Score |
| `og:image:alt` | Feel-Good Score: how should you feel about your NFL team? |
| OG image text | "Feel-Good Score" (wordmark), with "How should you feel about your NFL team?" below it (tagline) |
| Primary CTA | none new (assumption: the phase adds no actions) |
| Empty state | none new |
| Error state | unchanged (the existing fatal StatusPanel); the disclaimer now also renders under it |
| Destructive actions | none |

Tag-copy rules: description stays under 200 characters (the one above is 132), with no emoji and no double quotes. The em dash appears only in the footer, not in the tags.

---

## Share Image Contract (`web/public/og-default.png`)

- 1200×630 PNG, under 300 KB, RGB, no transparency.
- Layout: left-aligned and vertically centered as a block (bar, wordmark, tagline), with 96px side padding. The tagline wraps inside 1008px if it needs to (it shouldn't at 44px).
- Generate it once with a throwaway Pillow script in the scratchpad and commit only the PNG.
- Tags: `og:image` and `twitter:image` take the absolute `%SITE_ORIGIN%/og-default.png`; `og:image:width` is 1200 and `og:image:height` is 630; `twitter:card` is `summary_large_image`.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| none | none | not applicable (no shadcn, no third-party registries) |

---

## Assumptions (full autonomy, no questions asked)

- Exact meta description wording, OG typography and layout, and accent-bar use: Claude's discretion per CONTEXT.
- Footer render strategy (optional `meta` prop, footer always mounted) implements D-13.
- Light-theme-only OG image: crawlers don't honor color schemes.

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-11-11 (gsd-ui-checker, 6/6 PASS)

---
phase: 12
slug: redesign-foundation-team-identity
status: approved
reviewed_at: 2026-11-11
shadcn_initialized: false
preset: none
created: 2026-11-11
---

# Phase 12 — UI Design Contract

> Restyle the v1 site into editorial data journalism (inspired by generic NYT Upshot / Economist / FiveThirtyEight conventions, **never** their name, logo, marks, fonts or exact brand colors), add team logos and era-correct names, and keep every v1 behavior. All decisions in `12-CONTEXT.md` (D-01..D-25) are locked. This contract fills in final values for the areas left to Claude's discretion. It extends the v1 baseline (`02-UI-SPEC.md`) and Phase 10 (`10-UI-SPEC.md`). Anything this file does not mention stays as v1 shipped it.

Scope: `web/` only. Never touch `pipeline/`, `mood.py`, or band thresholds/labels/emoji.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none. Svelte 5 + Vite with hand-rolled CSS tokens in `web/src/app.css`. The shadcn gate doesn't apply because this isn't a React project. |
| Preset | not applicable |
| Component library | none |
| Icon library | none. Use the text glyphs ▲ ▼ – → ← · and the mood emoji already in use. Team logos are content, not icons. |
| Font (text/UI) | **Inter Variable** via `@fontsource-variable/inter` **5.3.0** (exact pin), imported in `web/src/main.ts` |
| Font (numbers/annotations) | **IBM Plex Mono** 400 and 600 via `@fontsource/ibm-plex-mono` **5.3.0** (exact pin): `import '@fontsource/ibm-plex-mono/400.css'` and `'/600.css'` |
| Card fonts (Phase 14, devDependency only) | `@fontsource/inter` **5.3.0**. Nothing from it is imported at runtime. |
| Charts | Observable Plot 0.6.19 (existing) plus the new `web/src/lib/plotTheme.ts` |

Font rules:
- Import fonts in `main.ts` **before** `./app.css`. Don't add a `<link>` to any font CDN, and don't copy font files into `public/`.
- Add `font-synthesis: none` to `body`. That way a missing weight falls back to the nearest real face and never gets faux-bolded.
- HistoryChart measures its gutter text on a canvas. Re-run that measurement (bump a `$state` counter) after `document.fonts.ready` resolves, or the label columns will be sized against the fallback font.

---

## Spacing Scale

The existing tokens are unchanged:

| Token | Value | Usage in this phase |
|-------|-------|---------------------|
| `--space-xs` | 4px | Logo-to-text gap, headline-to-dek gap, gap between the two lines of a chart footer |
| `--space-sm` | 8px | Table cell vertical padding (desktop), chart-to-footer gap, column gaps on mobile |
| `--space-md` | 16px | Table cell horizontal padding, dek-to-chart gap, padding under section rules, column gaps on desktop |
| `--space-lg` | 24px | Gap between page blocks (callouts, movers, board) |
| `--space-xl` | 32px | Gap between sections on a page (each one topped by a rule) and between consecutive ChartFrames; footer top margin |
| `--space-2xl` | 48px | Header top margin at ≥1024px (unchanged) |
| `--space-3xl` | 64px | Bottom page padding at ≥1024px (unchanged) |

Existing size tokens stay: `--tap-min: 44px`, `--stripe-width: 4px`, `--content-max: 960px`, `--radius-sm: 4px`, `--radius-md: 8px`.

New size tokens:

| Token | Value | Usage |
|-------|-------|-------|
| `--prose-max` | 680px | Max width of methodology prose paragraphs, lists and deks |
| `--score-cell` | 56px | Width of the shaded score cell in board and records rows |

Exceptions (all multiples of 4 unless noted):
- Tap targets stay at least 44px (`--tap-min`).
- Logo sizes are 16, 20, 24, 32 and 48px (the `TeamLogo` `size` prop).
- Focus outline is 2px; rules are 1px.
- **Inside Plot only:** the existing pixel offsets (`TEAM_DX` 6, `GAP` 10, margins 6, 28 and 32) can stay. They live in SVG coordinate space and aren't layout spacing.
- Letter-spacing on mono micro text is 0.04em.
- **Radius:** editorial blocks (board rows, callout blocks, movers rows, records rows) are **square** (radius 0). `--radius-md` stays only on buttons and inputs (Copy link, Jump to my team, Latest, select, manual-copy input).

---

## Typography

### Families

| Token | Value |
|-------|-------|
| `--font-sans` | `'Inter Variable', system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif` |
| `--font-mono` | `'IBM Plex Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace` |

### Sizes (the 4-size scale is kept; one micro size added per D-03)

| Role | Token | Size | Line height | Family | Used for |
|------|-------|------|-------------|--------|----------|
| Display | `--text-display` | 28px | 1.1 | Inter 700 | Site h1, team page name, team page score (mono 600) |
| Heading | `--text-heading` | 20px | 1.25 | Inter 700 | Page h2 (board week heading, Mood over time, Records, How it works), section h2/h3, ChartFrame headline, callout headline; board/records **score number** (mono 600) |
| Body | `--text-body` | 16px | 1.5 | Inter 400 | Prose, deks, team names in rows, nav links, mood labels |
| Label | `--text-label` | 14px | 1.4 | Inter 400 / mono | Secondary text and meta lines; mono for record, rank, deltas, Elo, factor values, chart direct labels |
| Micro | `--text-micro` | 12px | 1.4 (`--lh-micro`) | mono 400, UPPERCASE, `letter-spacing: 0.04em` | Table column headers, ChartFrame SOURCE/NOTES footer, chart tick labels, band labels in the chart gutter, badges, sparkline min/max |

There are exactly 4 sizes for reading text. Micro is the locked D-03 annotation size and is only ever used in mono. No other `font-size` literals are allowed. The existing literals map like this:
- `HistoryChart` legend `12px` → `--text-micro`
- `Sparkline` `fontSize: 11` → 12
- `PinButton` `20px` (glyph) → `--text-heading`
- `StatusPanel` `0.9em` → `--text-label`

### Weights (2 per family)

| Token | Value | Family | Use |
|-------|-------|--------|-----|
| `--weight-regular` | 400 | both | All running text, deks, mono annotations, ticks |
| `--weight-bold` (new) | 700 | Inter | Headlines (h1/h2/h3, ChartFrame headline, callout headline), wordmark, abbreviations, nav current item, buttons |
| `--weight-semibold` | 600 | **mono only** | Score numbers, ranks, deltas, chart direct labels |

Migration rule: wherever a component sets `font-weight: var(--weight-semibold)` on **Inter** text, change it to `var(--weight-bold)` (about 37 occurrences across the 18 components). Where the element switches to mono (scores, ranks, deltas, `.num`), keep `--weight-semibold`. After the change, Inter renders only at 400/700 and Plex Mono only at 400/600.

### Numbers (D-03)

Every score, record, rank, delta, Elo, percentage, factor point value, date-free stat, game score and day count uses:
```css
font-family: var(--font-mono);
font-variant-numeric: tabular-nums;
```
Add a utility class `.num` in `app.css` with exactly these two declarations, and reuse the existing `.num` in MethodologyPage. Mood labels, team names, prose and dates written in words stay in Inter.

---

## Color

### Core tokens (final values; measured WCAG 2.x contrast)

| Role | Token | Light | Dark | Contrast (light / dark) |
|------|-------|-------|------|------------------------|
| Dominant (60%), page | `--bg` | `#ffffff` | `#141414` | — |
| Secondary (30%), controls/sticky bar | `--surface` | `#ffffff` | `#1c1c1c` | — |
| Row hover | `--surface-hover` (new) | `#f5f5f5` | `#222222` | — |
| Text | `--text` | `#222222` | `#ededed` | 15.91:1 on bg / 15.74:1 on bg (14.56:1 on surface) |
| Muted text | `--text-muted` | `#6b6b6b` | `#a3a3a3` | **5.33:1** on bg / **7.30:1** on bg, **6.76:1** on surface |
| Hairline rule | `--border` | `#e3e3e3` | `#333333` | decorative (1.28 / 1.46) |
| Strong rule | `--rule-strong` (new) | `#222222` | `#ededed` | Under table header rows and above page sections |
| Chart gridline | `--grid` (new) | `#e6e6e6` | `#2e2e2e` | decorative (1.25 / 1.36) |
| Accent | `--accent` | `#1f5fbf` | `#8db4ff` | **6.09:1** on bg / **8.86:1** on bg, **8.20:1** on surface |
| On-accent | `--on-accent` | `#ffffff` | `#141414` | 6.09:1 / 8.86:1 |
| Up | `--up` | `#1e7a4c` | `#5fbf8a` | 5.33:1 / 8.16:1 |
| Down | `--down` | `#b3362c` | `#f2877b` | 6.03:1 / 7.48:1 |
| Destructive | `--danger` | `#b3362c` | `#f2877b` | same as `--down`. No destructive actions in this phase; the error-panel title icon only. |
| Logo disc | `--logo-disc` (new) | `transparent` | `#f2f2f2` | disc vs dark bg 16.46:1 |
| Chip outline | `--chip-outline` | unchanged | unchanged | — |

Contrast on tinted states, measured:

| State | Light | Dark |
|-------|-------|------|
| Muted on `--surface-hover` | 4.89:1 | 6.31:1 |
| Accent on `--surface-hover` | 5.59:1 | — |
| Up on `--surface-hover` | 4.88:1 | — |
| Muted on my-team tint (6% accent over bg; light `#f2f5fb`) | 4.88:1 | 6.39:1 (8% accent) |

Every text pair passes AA (4.5:1) at 12–14px.

### The 60/30/10 split in an editorial layout

- **60%: `--bg`.** Rows, callout blocks, chart areas and sections all sit directly on the page. There are no card fills.
- **30%: structure.** This comes from rules (`--border`, `--rule-strong`), the gridlines, the `--surface` sticky scrubber bar and controls, and the low-alpha mood-band score cells. In light mode `--surface` equals `--bg`. That is intentional: separation comes from rules, not fills.
- **10%: accent.** See the reserved list.

### Accent reserved for (and only for)

1. The `:focus-visible` outline on every focusable element
2. Text links (`a`), including the footer "nflverse" link, "See {team} →", "Mood over time →" and week-nav links
3. The current nav item's 2px underline in the SiteHeader
4. The week slider's filled track and thumb, and the "Latest" button fill (unchanged from v1)
5. The "In progress" and "Still going" badges (border and text)
6. The my-team row: 2px outline plus a 6% (light) / 8% (dark) tint
7. The "composite" dot in MethodologyChart
8. The Copy link button text

Accent is **never** used for score numbers, team names, mood labels, headlines, chart series other than the composite dot, gridlines or rules. Team colors are the only highlight colors in team charts.

### Mood band tokens (unchanged values, new usage)

`--mood-0..6` keep their v1 values in both modes (they are the data encoding; D-04). All of them clear 3:1 as graphics on the new `--bg`:
- Light, on `#fff`: 10.02, 5.18, 3.64, 3.33, 3.28, 5.02, 7.95
- Dark, on `#141414`: 6.66, 8.14, 12.03, 5.90, 12.45, 10.57, 14.36

**Shaded score cell** (board rows, records rows, team page score). The background is:
```css
color-mix(in srgb, var(--band) var(--cell-tint), var(--bg))
```
- `--cell-tint` is 16% (light) or 20% (dark).
- The cell's left edge is solid: `box-shadow: inset var(--stripe-width) 0 0 var(--band)`.
- The number inside is `--text` mono 600. **Muted text is never placed inside a shaded cell.**
- Measured `--text` contrast across all 7 bands is 11.89–13.57:1 (light) and 9.21–11.77:1 (dark).

**Stripe decision (Claude's discretion, D-21):** the v1 4px left row stripe becomes the shaded cell's 4px left edge. Rows lose their own left stripe. The stripe still follows the exported band label (resolved through `bandIndex`), never the raw score.

### Chart colors

| Element | Value |
|---------|-------|
| Gridlines (value axis only) | `var(--grid)`, 1px, `strokeOpacity: 1` |
| Tick labels | `var(--text-muted)`, mono 12 |
| Background series (31 teams) | `BACKGROUND_STROKE = 'var(--text-muted)'`. Keep v1's width-scaled opacity and width (0.16/0.12/0.08; 0.75/0.6/0.5). |
| Highlighted team | Team primary, else secondary, else `--text`, chosen by the existing `pickHighlight` (≥3:1 vs `--bg`), at `HIGHLIGHT_WIDTH = 2.5` |
| Season dividers | `var(--border)`, dashed `2,3` |
| Mood band rects | `var(--mood-n)` at `fillOpacity` 0.10 (light) / 0.14 (dark), unchanged |
| Reference rules (Elo-alone, "average team") | `var(--text-muted)` dashed `4,3`. This changes from `--border`, which disappears on white. |

Required code follow-up: update `FALLBACK_BG` in `web/src/lib/history.ts` to `{ light: '#ffffff', dark: '#141414' }` so it matches the new `--bg`. Adjust any test that pins the old values to the new ones (don't weaken it).

---

## Shared Chart Theme Contract: `web/src/lib/plotTheme.ts` (D-07)

This module is pure TypeScript with no Svelte imports. It exports:

```ts
export const CHART_FONT_PX = 12          // ticks, band labels
export const LABEL_FONT_PX = 14          // direct labels at series ends
export const HIGHLIGHT_WIDTH = 2.5
export const BACKGROUND_STROKE = 'var(--text-muted)'
export const GRID_STROKE = 'var(--grid)'
export const LOGO_MARK_PX = 20           // HistoryChart end-of-line logo (24 at width >= 900)

export const themeStyle = {
  fontFamily: 'var(--font-mono)',
  fontSize: `${CHART_FONT_PX}px`,
  color: 'var(--text-muted)',
  background: 'transparent',
  overflow: 'visible',
}

/** Team highlight stroke: the color pickHighlight already chose; '' or invalid -> 'var(--text)'. */
export function teamStroke(color: string | null | undefined): string

/** Value-axis options: grid on, no domain line, no ticks, mono labels. */
export function valueAxis(extra?: object): object   // { grid: true, tickSize: 0, line: false, label: null, ...extra }
/** Category/time axis: no grid, no ticks, no line. */
export function baseAxis(extra?: object): object    // { grid: false, tickSize: 0, line: false, label: null, ...extra }

/** Merge the theme into Plot options. Caller options win; style is shallow-merged. */
export function withTheme<T extends object>(options: T): T
```

Rules every Plot chart follows:
- Pass options through `withTheme`, and never set `title`/`subtitle`/`caption` on the Plot (the headline, dek and caption are HTML in ChartFrame).
- **Gridlines go on the value axis only:** y on HistoryChart and Sparkline (the sparkline draws no grid), x on MethodologyChart. Use `stroke: GRID_STROKE`.
- **No axis domain lines, no tick marks** (`tickSize: 0`), no frame, no rotated axis titles. The unit goes in the dek.
- Prefer direct labels over legends (D-09). The one documented exception: the HistoryChart mood-band legend under 640px.
- Remove the now-redundant `.chart :global(g[aria-label$='-axis tick'])` CSS overrides, since there are no ticks left to color.
- Charts keep their `role="img"` and `aria-label` summaries exactly as in v1.
- Unit tests (vitest, `plotTheme.test.ts`):
  - `withTheme` merges without clobbering caller `style` keys.
  - `teamStroke` falls back to `var(--text)` for empty or invalid input.
  - `valueAxis()` has `tickSize: 0` and `grid: true`.

Sparkline exception (D-08): it uses `themeStyle` and `teamStroke` but renders without a ChartFrame. Its min/max labels are mono 12 muted.

---

## Component Contract: `ChartFrame.svelte` (D-08)

Props: `{ headline: string; dek?: string; notes?: string; level?: 2 | 3 = 3; id: string; children: Snippet }`

Anatomy, top to bottom:

```
<figure class="chart-frame" aria-labelledby="{id}">
  <svelte:element this="h{level}" id="{id}" class="cf-headline">{headline}</svelte:element>   Inter 700, 20px/1.25, --text
  {#if dek}<p class="cf-dek">{dek}</p>{/if}                                                   Inter 400, 16px/1.5, --text-muted, max-width --prose-max
  <div class="cf-body">{@render children()}</div>                                             the chart, full container width
  <figcaption class="cf-foot">                                                                mono 400, 12px/1.4, --text-muted, letter-spacing .04em
    <span class="cf-source">SOURCE: NFLVERSE · FEEL-GOOD SCORE</span>
    {#if notes}<span class="cf-notes">NOTES: {notes}</span>{/if}
  </figcaption>
</figure>
```

Spacing:
- Headline to dek: 4px (`--space-xs`).
- Dek to body: 16px (`--space-md`).
- Body to footer: 8px (`--space-sm`).
- Source line to notes line: 4px. The two lines are stacked as blocks at every width.
- `margin: 0`. Consecutive frames are separated by 32px (`--space-xl`).
- No border, background, radius or shadow.

Text rules:
- `SOURCE:` and `NOTES:` prefixes and the source value are uppercase. The notes text is **sentence case**, because long uppercase sentences are hard to read.
- Both footer lines wrap (`overflow-wrap: anywhere`) and never cause horizontal scroll.
- The headline is HTML, never a Plot `title`.

Applied to:

| Chart | Where the frame goes | Heading level |
|-------|----------------------|---------------|
| HistoryChart | `HistoryPage` wraps `<HistoryChart>` together with its mobile band legend | h3 |
| MethodologyChart | Replaces the component's own `<figure>`/`<figcaption>` | h3 |
| FactorBars | `TeamPage`'s "Score breakdown" section. The frame headline **replaces** the existing `<h3 id="why-heading">` (keep `id="why-heading"` so the section's `aria-labelledby` still resolves). | h3 |

Sparkline gets no frame (documented exception).

---

## Component Contract: `TeamLogo.svelte` (D-11..D-15)

Props: `{ franchise: string; primary?: string | null; secondary?: string | null; size?: 16 | 20 | 24 | 32 | 48 = 24; alt?: string = '' }`

Pure helpers live in `web/src/lib/logos.ts` and are unit-tested:
- `logosEnabled(env = import.meta.env.VITE_LOGOS): boolean` returns false only when the value is `'off'`, case-insensitive.
- `logoSrc(franchise): string | null` returns `/logos/sm/${F}.png` when `F` is one of the 32 known franchise codes (`^[A-Z]{2,3}$` and present in the list), else `null`.

Render:
1. If `!logosEnabled()`, or `logoSrc` is null, or the image's `error` event has fired: render `<TeamChip {primary} {secondary} {size} />`. Extend TeamChip's `size` union to `16 | 20 | 24 | 32 | 48`. Its box is `size`×`size` with the existing gradient and outline. Keep `24` behaving as before.
2. Otherwise:
   ```html
   <span class="logo" style:--logo-size="{size}px">
     <img src={src} width={size} height={size} alt={alt} loading="lazy" decoding="async" onerror={() => failed = true}
          aria-hidden={alt === '' ? 'true' : undefined}>
   </span>
   ```
   - The `.logo` box is a fixed `size`×`size` with `flex: none` and `display: inline-grid; place-items: center`, so there is no layout shift while the image loads.
   - **Light mode:** no disc. The image fills the box (`width/height: 100%; object-fit: contain`).
   - **Dark mode:** `background: var(--logo-disc); border-radius: 50%`. The image is inset 12% per side (`width/height: 76%`), so a 24px disc holds an image about 18px across.
3. `alt` defaults to `''` because every placement has a visible or screen-reader team name next to it. Never set alt to the team name when the name is also printed next to the logo.

Don't alter the logo: no recolor, no filter, no mood tint, no crop beyond `object-fit: contain`. Logos are never site branding (favicon, OG default, header wordmark).

### Sizes per surface

| Surface | Mobile (<1024px) | Desktop (≥1024px) | Replaces |
|---------|------------------|-------------------|----------|
| Board row | 24 | 24 | `TeamChip` 16 |
| Team page header | 32 | 48 | `TeamChip` 24 |
| Records rows (all 4 lists) | 24 | 24 | `TeamChip` 16 |
| Callout block "who" line | 20 | 20 | `TeamChip` 16 |
| Movers strip items | 20 | 20 | `TeamChip` 16 |
| Recent games opponent | 20 | 20 | `TeamChip` 16 |
| HistoryChart end-of-line mark | 20 (Plot `image`) | 24 at chart width ≥900 | new |
| History page team `<select>` | text only (D-15) | text only | — |

The team page header switches 32→48 with a CSS media query that sets `--logo-size`. If that's simpler, render one `TeamLogo` with `size={48}` and override its box to 32px under 1024px. Either way the `src` stays the 96px derivative.

### Small derivatives (D-12)

`web/scripts/logos-sm.sh` loops over the 32 `web/public/logos/{F}.png` files and runs `sips -Z 96 "$in" --out "web/public/logos/sm/$F.png"`. Commit the 32 outputs. The 500px originals and `manifest.json` stay untouched, and so does `pipeline/`. `nohotlink.test.ts` must keep passing, because every logo path is same-origin.

### HistoryChart logo mark (D-10)

- Exactly one `Plot.image` at the highlighted team's last non-NaN point: `width = height = LOGO_MARK_PX` (24 when width ≥ 900), `src: logoSrc(team)`, centered on the point.
- In dark mode, draw a `Plot.dot` with `r = LOGO_MARK_PX/2`, `fill: 'var(--logo-disc)'` and `stroke: 'none'` underneath it, with the image at 76% size.
- The direct label (`team` abbreviation, mono 600 14px, `var(--text)`) moves right to `dx = LOGO_MARK_PX/2 + 4`. Add `LOGO_MARK_PX + 4` to the gutter calculation (`teamCol`).
- If logos are disabled or `logoSrc` is null: no image and no disc, and the label keeps v1's `dx`. An SVG `<image>` that fails to load renders nothing; the label still identifies the team.
- Never one logo per data point.

---

## Era Names Contract: `web/src/lib/teamNames.ts` (D-16..D-19)

Pure functions. The current logo is used in every era.

| Franchise | Seasons | `eraName` | `eraAbbr` |
|-----------|---------|-----------|-----------|
| LV | ≤ 2019 | Oakland Raiders | OAK |
| LV | ≥ 2020 | `meta.teams.LV.name` | LV |
| LAC | ≤ 2016 | San Diego Chargers | SD |
| LAC | ≥ 2017 | `meta` name | LAC |
| LA | ≤ 2015 | St. Louis Rams | STL |
| LA | ≥ 2016 | `meta` name | LA |
| WAS | ≤ 2019 | **Washington** (never the former name, anywhere, including code comments and tests) | WAS |
| WAS | 2020–2021 | Washington Football Team | WAS |
| WAS | ≥ 2022 | `meta` name | WAS |
| any other | all | `meta.teams[F].name` (falls back to `F`) | `F` |

API:
- `eraName(franchise, season, meta)`
- `eraAbbr(franchise, season)`
- `isActiveFranchise(franchise, season)`: false for HOU before 2002, true otherwise. Any per-season team list skips inactive franchises.

Unit tests:
- Seasons 2015/2016 (STL→LA), 2016/2017 (SD→LAC), 2019/2020 (OAK→LV), WAS 2019/2020/2021/2022, HOU 2001/2002.
- An unknown franchise falls back to its code.

Which season to use, per surface (D-18):

| Surface | Season used for name/abbr |
|---------|---------------------------|
| Board rows, BoardRow screen-reader text | Board's viewed season |
| Team page header, `Loading {name}…`, error/empty copy | Viewed season |
| Callout blocks and movers strip | Viewed season |
| Records: saddest/happiest rows | Row's season |
| Records: streak rows | Streak start season. **Active** streaks use the current name. |
| Recent games opponent | That game's season |
| History page selector, HistoryChart label, aria-label, ChartFrame headline | Current name (franchise-level) |
| Pin button label, "My team" strings | Current name |

---

## Layout Contract (per page)

Global frame (App):
- **<1024px:** keep v1 (max-width 640px, centered, side padding 16px).
- **≥1024px:** keep `--content-max` 960px. Tables and charts use the full width. Prose (methodology paragraphs, deks, notes) caps at `--prose-max` 680px.
- Breakpoints stay as v1: the layout breakpoint is 1024px, and HistoryChart's band label/legend switch is at 640px.
- Sections are separated by a 1px rule plus whitespace: `border-top: 1px solid var(--border)`, `padding-top: --space-md`, `margin-top: --space-xl`. No boxed cards, no shadows anywhere (D-22).

### Header (`SiteHeader`)
- Wordmark "Feel-Good Score": Inter 700, 16px, `--text`. Text only, never a logo.
- h1 "How should you feel about your team?": display 28/700.
- Subhead: body 16, muted (it serves as the site dek).
- Nav: unchanged markup and copy. Links are Inter 400 16px in `--text`, 44px tap height, with a 2px accent underline on the current page.
- The header ends with `border-bottom: 1px solid var(--rule-strong)` and `padding-bottom: --space-sm` below the nav.

### Board (`BoardHeading`, `CalloutCards`, `MoversStrip`, `MoodBoard`, `BoardRow`)
- **BoardHeading:**
  - h2 `{season} · {Week label}` at heading 20/700.
  - The count line `32 teams` is the page dek, in label 14 muted. The number `32` stays plain text in Inter; it's a count in a sentence.
  - The note line is body muted.
- **Callout blocks** (D-22):
  - No border box, radius or background.
  - `border-top: 2px solid var(--stripe-color)` (the band color), `padding-top: --space-md`.
  - Who line: `TeamLogo` 20 + era name (label 14 muted).
  - Headline heading 20/700. Detail is body muted; evidence is label muted.
  - Actions unchanged ("See {name}", "Copy link").
  - Grid gap 24px. Columns as in v1.
- **Movers strip:**
  - Items become unboxed rows: `border-bottom: 1px solid var(--border)`, min-height 44px, hover `--surface-hover`.
  - Each row is `TeamLogo` 20 + era abbreviation (Inter 700) + delta (mono 600 14).
  - Column titles "Risers"/"Fallers" are mono micro uppercase muted.
- **Column header row (≥1024px only, as in v1):**
  - Mono micro uppercase muted. Text stays "# / Team / Record / Score / Mood / Change"; uppercase comes from CSS.
  - `border-bottom: 1px solid var(--rule-strong)`, `padding-bottom: --space-sm`.
  - Numeric headers (Record, Score, Change) are right-aligned.
- **Rows** (`ol` gap 0):
  - Each row: `border-bottom: 1px solid var(--border)`, no left/right/top border, radius 0, transparent background. No zebra striping. Hover: `--surface-hover`.
  - Desktop grid: `32px | minmax(0,1fr) | 80px | var(--score-cell) | minmax(0,280px) | 72px`, column gap 16px, padding `8px 16px`, plus the existing pin-slot inline-end reservation. Min row height 48px.
  - Rank: mono 600 14, muted.
  - Team: `TeamLogo` 24 + era abbreviation (Inter 700 16) + era name (Inter 400 16, ellipsis) + "My team" badge.
  - Record: mono 400 14, muted, right-aligned.
  - Score: shaded cell (see Color), full row height, number mono 600 20 right-aligned with 8px inner padding. The `Elo ####` line moves **out** of the shaded cell and becomes a muted mono 14 line under the record at ≥1024px, because muted text can't sit on the tint.
  - Mood: `MoodLabel`, unchanged.
  - Change: `Delta` mono 600 14, right-aligned. The rank delta shows under it at ≥1024px as in v1.
- **Mobile (<1024px):** keep v1's two-line grid. Columns are `28px | minmax(0,1fr) | var(--score-cell)`, gap 8px, padding `8px 16px` with the pin slot reserved on the right.
  - Line 1: rank, logo 24, abbreviation, name (ellipsis), shaded score cell spanning both lines.
  - Line 2: record (mono 14 muted) and mood label.
  - The Delta moves to line 2, right-aligned before the score cell.
- **My-team row:** 2px accent outline (inset −2px) plus the accent tint, unchanged. The shaded score cell keeps its band tint.
- **Skeleton rows:** 64px tall with a bottom rule only, and a `--border` bar at 60% width. No box.
- **Scrubber:** behavior unchanged. Its bar loses the radius and gets `border-bottom: 1px solid var(--border)`. The week output and tick labels are mono; "Latest" stays accent-filled.

### Team page (`TeamPage`, `FactorBars`, `RecentGames`, `Sparkline`)
- **Header grid** (unchanged structure):
  - `TeamLogo` (32 mobile / 48 desktop), then h2 era name at display 28/700, then the pin button.
  - Sub-lines are label 14 muted. Record and rank numbers inside them are wrapped in `.num` spans.
  - The score is a shaded cell (band color, 4px band edge) at min 72×56px. The number is mono 600 28, followed by the `Delta`.
  - The mood label uses heading size, unchanged.
- The week nav, streak, blurb and draft note keep their copy; draft and streak lines are muted.
- Sections ("Score breakdown", "Recent games") become rule-topped sections, not boxed blocks.
- **FactorBars** inside ChartFrame:
  - Factor label is body 16. The value is mono 600 14 in `--up`/`--down`/muted.
  - Bars are square (radius 0) at 8px tall. The center baseline is 1px `--text-muted`.
  - The "Average team {baseline}" line and the "= {score}" total are mono.
  - The total rule is `--rule-strong`.
- **RecentGames:**
  - Opponent `TeamLogo` 20 + era abbreviation for that game's season.
  - W/L/T, score `pf–pa` and margin in mono. Rows are separated by `--border` rules.
- **Sparkline:** heading "This season" is h3 at heading size; the chart is themed with no frame.

### History page (`HistoryPage`, `HistoryChart`)
- Page h2 "Mood over time" at heading 20/700, plus the new dek (see Copywriting).
- The picker label and select are unchanged. The select gets radius-md and a `--border` outline.
- The summary paragraph stays (body; numbers in `.num`) along with its "See {name} →" link.
- ChartFrame wraps the chart. Heights stay at 400 (≥500px) and 280 (<500px).
- Band labels sit in the right gutter at ≥640px (mono 12 muted). Under 640px the compact legend shows instead (mono 12 muted; swatches square, not rounded) — the documented legend exception.
- Background lines are gray; the highlighted team uses its color plus the logo mark plus the direct label.

### Records page (`RecordsPage`)
- h2 "Records" at heading 20/700. The intro paragraph is the dek (body muted). "As of {date}" is mono micro uppercase muted.
- Each list section is rule-topped, with an h3 at heading 20/700.
- Rows use the board row style: bottom rules, no box or radius, hover `--surface-hover`.
  - Rank: mono 600 14 muted.
  - `TeamLogo` 24 + `{season} {eraName}` (extremes) or `{eraName} {seasons span}` (streaks).
  - The meta line is label 14 muted, with record and numbers in `.num`.
  - The big value sits in a shaded cell (`--score-cell` wide, mono 600 20) tinted by the existing `scoreStripe` (extremes) or `streakStripe` (streaks) color. Day counts stay `formatDays` text, set in mono.
- "Still going" (accent) and "My team" (neutral) badges are mono micro uppercase.
- The footnote is label muted, with max width `--prose-max`.

### Methodology page (`MethodologyPage`, `MethodologyChart`)
- Add a page head before the first section: h2 "How it works" at heading 20/700, with a dek (see Copywriting). The existing section h2s stay h2 elements at heading size with rule tops.
- Paragraphs and lists: max-width `--prose-max` (680px), body 16/1.5. Inter only (Source Serif 4 is deferred).
- Figures and inline numbers (`.num`) are mono.
- The band list keeps its 8px band swatches (square), emoji, label and range (range in mono).
- Factor rows and "The numbers" rows use bottom rules, not boxes. The `Weight`, `Added`, `Rank corr.` and `Brier` values are mono.
- Both MethodologyCharts are wrapped in ChartFrame; their old figcaption text moves into the dek and notes.
- New muted paragraph at the end of "What the score is": the D-18 relocation note (see Copywriting).
- No new 538/FiveThirtyEight mentions. Existing factual Elo credit text, if any, stays as it is.

### Footer (`SiteFooter`)
- `border-top: 1px solid var(--border)`, `padding-top: --space-md`, `margin-top: --space-xl`.
- The stamp line keeps v1 copy and responsive behavior. Its dates are Inter label muted.
- The disclaimer line gets the new trademark copy (below). It's label 14 muted, wraps cleanly at 320px, and keeps the existing nflverse link (accent).

---

## 375px Rules (DESIGN-04)

- No horizontal scroll on any route at 320–375px, in either color scheme. Fix overflow with `min-width: 0` plus ellipsis, never `overflow-x: hidden` on html/body.
- Board row: logo 24, name ellipsizes before the abbreviation or score cell is squeezed. The pin button keeps its 44px slot.
- Team header: logo 32. The name wraps (no ellipsis on the h2). The score cell drops below the name block as in v1.
- ChartFrame: headline and dek wrap. The SOURCE/NOTES lines wrap (`overflow-wrap: anywhere`).
- HistoryChart: height 280, `’YY` ticks, logo mark 20, band legend under the chart.
- MethodologyChart keeps v1's narrow margins (120px left, 40px rows).
- Records meta lines wrap under the name. The shaded value cell keeps `--score-cell` width.
- Movers strip: two columns of 20px logo + abbreviation + delta. Truncate the abbreviation before the delta.
- All tap targets stay at least 44px.

---

## Interaction & State Contract

All v1 behavior is preserved (D-24): hash routes, scrubber (input and keyboard), my-team pin and "Jump to my team", callouts with copy-link (including the manual-copy fallback and live region), freshness stamp, disclaimer, `prefers-reduced-motion`.

| State | Contract |
|-------|----------|
| Logo loading | A fixed-size empty box (dark: disc already visible). No spinner, no layout shift. |
| Logo error | Swaps to `TeamChip` at the same size, once. No retry loop. |
| `VITE_LOGOS=off` | Every surface renders `TeamChip`, and HistoryChart draws no image mark. Checked in a unit test of `logosEnabled`. |
| Fonts loading | System fallback stack (Fontsource `font-display: swap`). HistoryChart re-measures after `document.fonts.ready`. |
| Hover on rows | `--surface-hover` background. 120ms color transition (existing), off under reduced motion. |
| Focus | 2px accent outline, offset 2px. On rows it's inset −2px, as v1 does for the pinned row. |
| Dark mode | `prefers-color-scheme` only (D-05). No toggle. Plot charts read CSS variables, so they follow the scheme; Sparkline/HistoryChart keep their existing `matchMedia` listeners. |
| Empty/error/loading panels | Unchanged copy. `StatusPanel` restyled: no shadow, 1px `--border`, radius-md kept (it's a control-like panel). |

Visual verification (D-25):
- Use Playwright at 1280px and 375px, with `emulateMedia({ colorScheme: 'light' | 'dark' })`.
- Capture board, team (`#/team/LAC/2010/…` to show "San Diego Chargers", plus a current team), history, records and methodology.
- Save to `.planning/phases/12-redesign-foundation-team-identity/screenshots/{page}-{width}-{scheme}.png`, which is 20 images.
- Run `nvm use 22` (or 24) first.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary CTA | No new actions. Existing CTAs keep their v1 copy: "Copy link", "See {era name}", "Jump to my team", "Latest", "Try again", "Go to latest". |
| Empty state heading | Unchanged: "No moods to report" (board), "No {era name} data for {season}" (team) |
| Empty state body | Unchanged: "We don’t have any teams for this week. Jump to the latest week to see the current board." |
| Error state | Unchanged v1 StatusPanel copy (problem + "Try again"/"Go to latest"), e.g. "Couldn’t load the mood history" / "The history file didn’t load. Try again in a moment." |
| Destructive confirmation | none (this phase has no destructive actions) |

### New copy (exact strings; use the curly apostrophe ’, as the codebase does)

| Location | Copy |
|----------|------|
| ChartFrame source line (every frame) | `SOURCE: NFLVERSE · FEEL-GOOD SCORE` |
| **HistoryChart** headline | `How {current name} fans should have felt since {first season}` |
| HistoryChart dek | `Weekly feel-good score, 0 to 100. {current name} in color, every other team in gray.` |
| HistoryChart notes | `Dashed segments mark offseason changes. Shaded bands are the mood labels.` |
| History page dek (under h2 "Mood over time") | `Every team’s feel-good score, every week since {first season}. Pick a team to put it in color.` |
| **MethodologyChart** (`spearman_n8`) headline | `Which method ranks teams best` |
| … dek | `Rank correlation with each team’s next 8 games, by test period. Higher is better.` |
| **MethodologyChart** (`brier`) headline | `Which method calls single games best` |
| … dek | `Next-game Brier score, by test period. Lower is better.` |
| MethodologyChart notes (both) | `Dots are the value; the dashed line marks Elo alone. {intervalNote}` (existing `intervalNote` text) |
| **FactorBars** headline (score present) | `Where the {score} comes from` |
| FactorBars headline (no breakdown) | `Score breakdown` (dek omitted; the existing "Factor breakdown unavailable for this week." stays) |
| FactorBars dek | `Points each factor adds to or takes from an average team ({baseline}). Together they sum to the score.` |
| FactorBars notes | none |
| Methodology page h2 | `How it works` |
| Methodology page dek | `What goes into the score, how it was tested, and where it falls short.` |
| Methodology relocation note (D-18) | `Relocated teams show their name from that season with the current logo.` |
| Footer disclaimer (replaces the Phase 10 line) | `Unofficial fan project — not affiliated with or endorsed by the NFL or any team. Team names and logos are trademarks of their respective owners. Data: <a href="https://github.com/nflverse">nflverse</a>.` |
| Board column headers | Unchanged text `#`, `Team`, `Record`, `Score`, `Mood`, `Change` (rendered uppercase via CSS) |
| TeamLogo alt | `''` (decorative; the adjacent name is the label) |

Copy rules:
- The em dash in the footer is U+2014 with spaces, and the final period sits outside the link (Phase 10 rule).
- The words "FiveThirtyEight", "538" and "fox" never appear in shipped UI copy or shipped code comments (D-06).
- Mood labels and emoji are untouched (D-23).
- No "lucky"/"unlucky" framing anywhere.
- Era names never use Washington's former name.

---

## Component Inventory (this phase)

| File | Status | Notes |
|------|--------|-------|
| `src/app.css` | modify | New/changed tokens above; `.num`; `font-synthesis: none`; `--text-micro`, `--lh-micro`, `--weight-bold`, `--rule-strong`, `--grid`, `--surface-hover`, `--logo-disc`, `--cell-tint`, `--prose-max`, `--score-cell` |
| `src/main.ts` | modify | Fontsource imports (Inter Variable; Plex Mono 400/600) before `app.css` |
| `src/lib/plotTheme.ts` (+test) | new | Theme contract |
| `src/lib/teamNames.ts` (+test) | new | Era names, `isActiveFranchise` |
| `src/lib/logos.ts` (+test) | new | `logosEnabled`, `logoSrc` |
| `src/components/ChartFrame.svelte` | new | Headline/dek/body/footer |
| `src/components/TeamLogo.svelte` | new | Logo, disc, chip fallback |
| `src/components/TeamChip.svelte` | modify | `size` union 16/20/24/32/48 |
| `scripts/logos-sm.sh` + `public/logos/sm/*.png` (32) | new | 96px derivatives |
| BoardRow, MoodBoard, BoardHeading, CalloutCard(s), MoversStrip, TeamPage, FactorBars, RecentGames, Sparkline, HistoryPage, HistoryChart, MethodologyChart, MethodologyPage, RecordsPage, SiteHeader, SiteFooter, Scrubber, Badge, Delta, StatusPanel, PinButton | modify (style + small markup) | Props and APIs unchanged (D-20). Routing untouched. |
| `src/lib/history.ts` | modify | `FALLBACK_BG` to new bg values |
| `package.json` | modify | `@fontsource-variable/inter` 5.3.0 and `@fontsource/ibm-plex-mono` 5.3.0 (dependencies, exact); `@fontsource/inter` 5.3.0 (devDependency, exact) |

Gates: `npm test`, `npm run check` and `npm run build` pass under Node 22/24. Existing tests aren't weakened.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| none (no shadcn, no third-party registries) | none | not applicable |

npm additions are first-party Fontsource packages (OFL fonts), pinned exactly. No runtime third-party network requests are added. Fonts and logos are same-origin.

---

## Pre-population Sources

| Source | Decisions used |
|--------|----------------|
| 12-CONTEXT.md | D-01..D-25: fonts, palette base values, plotTheme exports, ChartFrame anatomy, TeamLogo props/sizes/disc/off-switch, era table, name-context matrix, board table look, page frame, guardrails, verification |
| research/FEATURES.md (style section) | Headline + dek, value-axis grid only, direct labels, highlight-one-gray-rest, SOURCE/NOTES footer, shaded cells, rule-separated tables |
| research/STACK.md (Fonts) | Package names/versions (5.3.0 verified on npm 2026-11-11), Plex Mono 400/600, static Inter for cards |
| research/PITFALLS.md (6, 11, 13, 14, minor) | Era names, Washington rule, HOU guard, no 538 marks, nominative logos, off-switch, light disc in dark mode |
| 02-UI-SPEC / 10-UI-SPEC / `app.css` | Spacing scale, 4-size type scale, mood band tokens, accent discipline, breakpoints, footer structure |
| Claude's discretion (autonomous) | Final hex for up/down/accent/surface-hover, stripe folded into the score cell, cell tint 16%/20%, weight migration (Inter 400/700, mono 400/600), logo sizes per surface, chart copy, Inter-only (no Source Serif 4) |

Measured contrast: computed with the WCAG 2.x relative-luminance formula on 2026-11-11 (script in the session scratchpad). All text pairs are ≥4.5:1, and all mood graphics are ≥3:1 on `--bg`.

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending

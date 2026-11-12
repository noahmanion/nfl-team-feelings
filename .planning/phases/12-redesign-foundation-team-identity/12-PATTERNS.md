# Phase 12: Redesign Foundation & Team Identity - Pattern Map

**Mapped:** 2026-11-11
**Files analyzed:** 18 new + about 24 modified (21 components plus app.css, main.ts, history.ts, package.json, README)
**Analogs found:** 17 / 18 new files (only `web/scripts/logos-sm.sh` has no in-repo analog; use the RESEARCH.md snippet)

All paths below are relative to `web/`. Line numbers come from the current HEAD (b45189b).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/lib/plotTheme.ts` | utility (pure TS) | transform | `src/lib/format.ts` (pure exports) + Plot option literals in `HistoryChart.svelte:135-152` | role-match |
| `src/lib/plotTheme.test.ts` | test (unit + raw-source scan) | transform | `src/lib/format.test.ts` + `src/lib/nohotlink.test.ts` (glob `?raw`) | exact |
| `src/lib/logos.ts` | utility (pure TS) | transform | `src/lib/format.ts` (`bandIndex` defensive guard style) | role-match |
| `src/lib/logos.test.ts` | test (unit + glob) | file-I/O (glob) | `src/lib/nohotlink.test.ts` (import.meta.glob) | exact |
| `src/lib/teamNames.ts` | utility (pure TS) | transform | `src/lib/format.ts`; `RecordsPage.svelte:39` `teamName()` | role-match |
| `src/lib/teamNames.test.ts` | test | transform | `src/lib/format.test.ts` | exact |
| `src/lib/teamLogo.test.ts` | test (SSR render) | request-response | `src/lib/sep.test.ts` (`svelte/compiler` with `generate: 'server'`) | role-match |
| `src/lib/chartFrame.test.ts` | test (SSR render) | request-response | `src/lib/sep.test.ts` | role-match |
| `src/lib/fonts.test.ts` (brand guard) | test (raw-source scan) | file-I/O | `src/lib/nohotlink.test.ts` | exact |
| `src/components/TeamLogo.svelte` | component | event-driven (img error) | `src/components/TeamChip.svelte` | exact |
| `src/components/ChartFrame.svelte` | component (wrapper w/ snippet) | request-response | `CalloutCard.svelte:50` (`svelte:element h{level}`) + `Badge.svelte` (children Snippet) + `MethodologyChart.svelte:95-123` (figure/figcaption) | role-match |
| `scripts/logos-sm.sh` | build script | batch / file-I/O | none | no analog |
| `public/logos/sm/*.png` (32) | static asset | — | `public/logos/*.png` | exact |
| `src/components/TeamChip.svelte` (mod) | component | — | self | — |
| `src/components/HistoryChart.svelte` (mod) | component (Plot) | transform | self | — |
| `src/components/MethodologyChart.svelte` (mod) | component (Plot) | transform | self | — |
| `src/components/Sparkline.svelte` (mod) | component (Plot) | transform | self | — |
| `src/app.css`, `src/main.ts`, `src/lib/history.ts` (mod) | config / tokens | — | self | — |
| BoardRow, CalloutCard, MoversStrip, RecentGames, TeamPage, RecordsPage, FactorBars, HistoryPage, MethodologyPage, SiteHeader, SiteFooter, Scrubber, MoodBoard, BoardHeading, Badge, Delta, StatusPanel, PinButton (mod) | component | request-response | self (restyle via `<style>` + TeamChip→TeamLogo swap) | — |

## Pattern Assignments

### `src/components/TeamLogo.svelte` (component, event-driven)

**Analog:** `src/components/TeamChip.svelte` (whole file, 39 lines). Copy its props typing, `$derived` validation, and scoped style conventions.

**Props + derived pattern** (TeamChip lines 1-10):
```svelte
<script lang="ts">
  let {
    primary,
    secondary,
    size = 16,
  }: { primary?: string | null; secondary?: string | null; size?: 16 | 24 } = $props()

  const HEX = /^#[0-9A-Fa-f]{6}$/
  const ok = $derived(!!primary && !!secondary && HEX.test(primary) && HEX.test(secondary))
</script>
```

**Box style pattern** (TeamChip lines 22-30): `display: inline-block; flex: none; width/height: var(--chip-size)`. TeamLogo's `.logo` uses the same `flex: none`, with `inline-grid; place-items: center`, and sizes from `--logo-size`.

**Render and error pattern:** RESEARCH.md Pattern 5. The failure state is keyed to `src` (`failedSrc !== src`), not a boolean. Fallback is `<TeamChip {primary} {secondary} {size} />`.

**Dark disc:** put it in a scoped `@media (prefers-color-scheme: dark)` block inside the component's `<style>`. The media-query structure follows `app.css:58-80`.

---

### `src/components/TeamChip.svelte` (modify)

- Line 6: widen `size?: 16 | 24` to `16 | 20 | 24 | 32 | 48`.
- Lines 15 and 32-35: the `.large` class covers 24 only. Replace it with `style:--chip-size="{size}px"` on the span. The base `.chip` already reads `var(--chip-size)` (lines 25-26), so 24 still renders at 24px. Keep the `box-shadow` at line 29 (chip outline).

---

### `src/components/ChartFrame.svelte` (component, wrapper)

**Dynamic heading level analog** (`CalloutCard.svelte:50-52`):
```svelte
<svelte:element this={`h${level}`} class="headline"
  ><span class="visually-hidden">{name}: </span>{callout.headline}</svelte:element
>
```
**Snippet children analog** (`Badge.svelte:2-7`):
```svelte
import type { Snippet } from 'svelte'
let { variant = 'default', children }: { variant?: ...; children: Snippet } = $props()
<span class="badge" ...>{@render children()}</span>
```
**Figure/figcaption + style analog** (`MethodologyChart.svelte:95-123`): `.figure { margin: 0; display: flex; flex-direction: column; gap: var(--space-xs) }` and `figcaption { color: var(--text-muted); font-size: var(--text-label); line-height: var(--lh-label) }`. ChartFrame's footer uses `--font-mono`, `--text-micro`, uppercase, and `letter-spacing: .04em`.

**Guard:** the `SOURCE: NFLVERSE · FEEL-GOOD SCORE` text must be a single text node. `sep.test.ts:22-28` fails on `<span>·</span>`.

---

### `src/lib/plotTheme.ts`, `src/lib/logos.ts`, `src/lib/teamNames.ts` (pure utilities)

**Analog:** `src/lib/format.ts`. Use named exports, JSDoc one-liners, and defensive type guards. Types come from `./types`:
```ts
import type { Band, Row, SeasonMeta } from './types'

/** The row's band index (hysteresis-adjusted, from the export) if it is a valid index into bands, else -1. */
export function bandIndex(band: unknown, bands: Band[]): number {
  return typeof band === 'number' && Number.isInteger(band) && band >= 0 && band < bands.length ? band : -1
}
```
(format.ts lines 1, 75-78)

- `teamNames.ts` takes `meta: Pick<Meta, 'teams'>`. `Meta`/`TeamMeta` are at `lib/types.ts:5,8-10`. It replaces the inline `const teamName = (abbr: string) => meta.teams[abbr]?.name ?? abbr` at `RecordsPage.svelte:39`, so the code-fallback semantic stays the same.
- `plotTheme.ts`: start from the current inline style literal `HistoryChart.svelte:140` / `MethodologyChart.svelte:47`, `{ fontSize: '14px', color: 'var(--text-muted)', background: 'transparent', fontFamily: 'inherit' }`. `themeStyle` replaces it with the mono font, 12px, and `overflow: 'visible'`. Full signatures are in the UI-SPEC "Shared Chart Theme Contract".
- `logos.ts` and `teamNames.ts` code: use RESEARCH.md "Code Examples" verbatim.

---

### `src/lib/*.test.ts` (new tests)

**Unit test analog** (`format.test.ts:1-18`): `import { describe, expect, it } from 'vitest'`, a named import from `./module`, small fixture builders (`const season = (s, reg) => ({...})`), and one `describe` per function.

**Raw-source scan analog** (`nohotlink.test.ts:5-13, 25-30`). Use it for `fonts.test.ts` (no font CDN, no 538, main.ts import order) and the `plotTheme.test.ts` chart-source scan:
```ts
const sources = import.meta.glob(['../**/*.{ts,svelte}', '!./nohotlink.test.ts'], {
  query: '?raw', import: 'default', eager: true,
}) as Record<string, string>
const html = import.meta.glob('../../index.html', { query: '?raw', import: 'default', eager: true }) as Record<string, string>
...
const offenders = Object.entries({ ...sources, ...html }).filter(([, src]) => RE.test(src)).map(([path]) => path)
expect(offenders).toEqual([])
```
Build forbidden strings from parts, as at line 16 (`'espn' + 'cdn'`), so the test file never matches itself. Exclude the test file from the glob.

**Component render analog** (`sep.test.ts:1, 7-17`): this file uses `compile(src, { generate: 'server' })`. For TeamLogo and ChartFrame, use `render` from `svelte/server` (verified in RESEARCH.md). The glob-of-components idiom is `import.meta.glob('../components/*.svelte', { query: '?raw', import: 'default', eager: true })`.

**Logo derivative test:** use `import.meta.glob('/public/logos/sm/*.png')` keys. Do not import `node:fs`, because `svelte-check` fails without node types (RESEARCH.md).

---

### `src/components/HistoryChart.svelte` (modify, Plot)

Existing pattern to keep: the `$effect` builds `marks[]`, calls `Plot.plot({...})`, sets `role`/`aria-label`, then `container.replaceChildren(plot)`, and the cleanup returns `() => plot.remove()` (lines 49-158).

| Lines | Change |
|-------|--------|
| 1-5 | add `import { withTheme, valueAxis, baseAxis, BACKGROUND_STROKE, HIGHLIGHT_WIDTH, teamStroke, LOGO_MARK_PX, LABEL_FONT_PX, CHART_FONT_PX } from '../lib/plotTheme'` and `import { logoSrc, logosEnabled } from '../lib/logos'` |
| 38-47 | constants map to `CHART_FONT_PX`/`LABEL_FONT_PX`. `textWidth` reads the container font, so set `.chart { font-family: var(--font-mono) }` and add the `fontsTick` re-measure (RESEARCH Pattern 6) |
| 66 | `teamCol` adds `LOGO_MARK_PX + 4` when a logo is drawn |
| 100 | delete `Plot.ruleY([0], …)` |
| 105, 110, 117 | `BACKGROUND_STROKE`, `HIGHLIGHT_WIDTH`, `teamStroke(color)` |
| 122-132 | label `dx` becomes `LOGO_MARK_PX/2 + 4` when a logo is drawn. Push the `Plot.dot` disc (dark) and the `Plot.image` before the text (RESEARCH Pattern 4). The `dark` prop already exists at line 16 |
| 135-152 | wrap the options in `withTheme({...})`, with `x: baseAxis({...})` and `y: valueAxis({...})` |
| 183-209 | legend `font-size: 12px` becomes `var(--text-micro)` plus mono. `.swatch` `border-radius: 2px` becomes 0. Delete the tick override (206-209). Add the grid CSS rule (D-28 / Pattern 1b) |

### `src/components/MethodologyChart.svelte` (modify, Plot)
- Line 47: `style` becomes `withTheme`. Line 48: `x: valueAxis({...})`.
- Line 52: `Plot.gridX({ stroke: 'var(--border)', strokeOpacity: 1, … })` already uses the explicit-grid pattern. Change the stroke to `GRID_STROKE`. Reuse this line as the gridline reference for the others.
- Line 66: `fontWeight: 600` on the period label is Inter text in the SVG mono context. Keep it at 600 (mono) per the UI-SPEC weights.
- Line 69: ref rule `stroke: 'var(--border)'` becomes `'var(--text-muted)'`, dashed `4,3`.
- Lines 95-98: replace `<figure>/<figcaption>` with `<ChartFrame>`. Keep `axisLabel` (25-27) in the aria-label (line 89). Delete the tick CSS at 116-118.

### `src/components/Sparkline.svelte` (modify, Plot)
- Line 55: `style: { background: 'transparent' }` becomes `style: themeStyle` (or `withTheme`).
- Line 59: baseline `stroke: 'var(--border)'` becomes `'var(--text-muted)'`.
- Line 70: `fontSize: 11` becomes `CHART_FONT_PX`. `fontVariant: 'tabular-nums'` is already there (71).
- Lines 29-35: the color is derived via `pickHighlight`. Wrap the result in `teamStroke()`.

---

### TeamChip → TeamLogo call sites (modify)

**Current form** (`BoardRow.svelte:63`): `<TeamChip primary={team?.primary} secondary={team?.secondary} />`
**New form:** `<TeamLogo franchise={row.franchise} primary={team?.primary} secondary={team?.secondary} size={24} />`

| Site | Franchise expr | Size | Era-name source |
|------|----------------|------|-----------------|
| `BoardRow.svelte:6,63` (name `:37`, abbr `:64`) | `row.franchise` | 24 | `season` prop (line 23). PinButton `:81` keeps the current `team?.name` |
| `CalloutCard.svelte:3,45` (name `:16`) | `callout.franchise` | 20 | `callout.season` |
| `MoversStrip.svelte:3,30` (sr name `:28`) | `c.franchise` | 20 | `c.season` |
| `RecentGames.svelte:2,33` | opponent code | 20 | `g.season` |
| `TeamPage.svelte:11,172` (name `:24`) | `team` | 48 (32 under 1024px) | `season`. PinButton `:174` keeps the current name |
| `RecordsPage.svelte:5,109,110` | `e.franchise` | 24 | `e.season` |
| `RecordsPage.svelte:134,135` | `s.franchise` | 24 | `s.active ? latest : s.start_season` |
| `RecordsPage.svelte:69` | `x.franchise` | — | `x.season` |

**Existing name derivation to replace** (BoardRow:37): `const name = $derived(team?.name ?? row.franchise)` becomes `$derived(eraName(row.franchise, season, meta))`. Where a component holds only `team: TeamMeta` and not `meta`, build a `{ teams: { [F]: team } }` shim, or add a franchise-name fallback in `eraName`. Don't change component props (D-20).

**Blurb/headline copy (D-26):** apply `eraText()` at `TeamPage.svelte:198` (`row.blurb`), `CalloutCard.svelte:51-52` (`callout.headline`, `callout.detail`) and `MoversStrip.svelte:28`.

---

### `TeamPage.svelte` FactorBars section (modify)
The current markup is at lines 204-207:
```svelte
<section class="block" aria-labelledby="why-heading">
  <h3 id="why-heading">Score breakdown</h3>
  <FactorBars ... />
</section>
```
Replace the `<h3>` with `<ChartFrame id="why-heading" level={3} headline=… dek=…>`. ChartFrame must put `id` on the heading so `aria-labelledby` resolves. **Don't add or remove any `<Sep />`** (sep.test.ts:44 pins 5).

### `MethodologyPage.svelte` (modify)
`.num` is already defined locally (lines 253-255, `font-variant-numeric: tabular-nums`). Once app.css owns `.num` (font-mono + tabular-nums), delete the local rule or leave it identical.

### `HistoryPage.svelte` (modify)
- The dark-mode listener at lines 65-72 (matchMedia pattern) already feeds `HistoryChart`'s `dark` prop. Reuse it and don't add a second listener.
- Wrap `<HistoryChart>` and the legend in `<ChartFrame level={3}>`. `teamName={teamMeta.name}` (line 140) stays the current name.

---

### `src/app.css` (modify, tokens)
- Lines 22-33: the token block. Replace `--font-sans` and add `--font-mono`, `--text-micro`, `--lh-micro`, `--weight-bold`, `--prose-max`, `--score-cell`, `--cell-tint`.
- Lines 35-46 (light) and 58-70 (dark): swap in the color values per UI-SPEC. Add `--rule-strong`, `--grid`, `--surface-hover`, `--logo-disc`. **Leave `--mood-*` (48-55, 72-78) untouched.**
- Line 107: in the `body` block, add `font-synthesis: none`.
- After `.visually-hidden` (145-155): add a global `.num { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }` and the Plot grid override rule.
- Keep the comment at 133-134 (no `overflow-x: hidden`).

### `src/main.ts` (modify)
The current file is 9 lines. Insert the three Fontsource imports above `import { mount } from 'svelte'` / `'./app.css'` (exact block in RESEARCH "Code Examples").

### `src/lib/history.ts` (modify)
Line 121: `export const FALLBACK_BG = { light: '#f6f6f3', dark: '#121316' } as const` becomes `{ light: '#ffffff', dark: '#141414' }`. Keep the `history.test.ts:88-99` assertions passing.

### `package.json` (modify)
Line 27 is `"@observablehq/plot": "0.6.19"`, an exact-pin style. Add the Fontsource deps the same way (no caret).

### README (modify)
`web/README.md` does not exist. The project README is `feel-good-scorew/README.md`. Add the OFL font credit line (D-27) and the `VITE_LOGOS=off` takedown note there.

## Shared Patterns

### Plot render lifecycle
**Source:** `HistoryChart.svelte:29-30, 49-50, 154-158, 161`
**Apply to:** all three Plot charts (unchanged structure)
```svelte
let width = $state(0)
let container: HTMLDivElement
$effect(() => {
  if (width <= 0) return
  const plot = Plot.plot({...})
  plot.setAttribute('role', 'img')
  plot.setAttribute('aria-label', `...`)
  container.replaceChildren(plot)
  return () => plot.remove()
})
<div class="chart" bind:clientWidth={width} bind:this={container}></div>
```

### Color-scheme tracking
**Source:** `Sparkline.svelte:20-27` (identical in `HistoryPage.svelte:66-72`)
**Apply to:** any component needing JS-side dark state. TeamLogo should use CSS media queries instead.
```ts
let dark = $state(false)
$effect(() => {
  const mq = window.matchMedia('(prefers-color-scheme: dark)')
  dark = mq.matches
  const onChange = () => (dark = mq.matches)
  mq.addEventListener('change', onChange)
  return () => mq.removeEventListener('change', onChange)
})
```

### Band color → token
**Source:** `BoardRow.svelte:35-36` with `format.ts:76-83`
**Apply to:** shaded score cells (BoardRow, TeamPage, RecordsPage)
```ts
const bandIdx = $derived(bandIndex(row.band, bands))
const stripe = $derived(bandIdx < 0 ? 'var(--border)' : `var(--mood-${moodToken(bandIdx, bands.length)})`)
```
The cell uses `style:--band={stripe}` and `background: color-mix(in srgb, var(--band) var(--cell-tint), var(--bg)); box-shadow: inset var(--stripe-width) 0 0 var(--band)`. Delete the row-level `border-left` (BoardRow:117, CalloutCard border-left).

### Defensive number display
**Source:** `BoardRow.svelte:39-40`. Never render NaN/null:
```ts
const ok = (n: unknown): n is number => typeof n === 'number' && Number.isFinite(n)
const num = (n: unknown): string => (ok(n) ? String(n) : '–')
```

### My-team highlight
**Source:** `BoardRow.svelte:96-100`. Keep it, with `--surface` changed to `--bg` in the mix:
```css
.mine .row { background: color-mix(in srgb, var(--accent) 6%, var(--surface)); outline: 2px solid var(--accent); outline-offset: -2px; }
```

### Overflow
**Source:** `app.css:133-134` and `CalloutCard .name` (`min-width: 0; overflow: hidden; text-overflow: ellipsis`). Every new flex/grid child that holds a name gets `min-width: 0` plus an ellipsis.

### Editorial box removal (radius/border sites)
`BoardRow.svelte:115-118` (`background: var(--surface); border; border-left stripe; border-radius: var(--radius-md)`) and `CalloutCard.svelte:~83-87` (same set). Both become a bottom rule (rows) or a 2px band top rule (callouts), with no radius. Other sites (RESEARCH inventory): `MoversStrip:93`, `RecordsPage:216`, `MethodologyPage:285`, `MoodBoard:124,131`.

### Markup-pinning guards (must stay green)
- `sep.test.ts:30-38`: SiteHeader nav keeps exactly 3 × `<span class="item"><Sep /><a `, and `.item { white-space: nowrap }`.
- `sep.test.ts:40-48`: TeamPage has 5 `<Sep />`, 2 of them inside `<nav class="week-nav">` with `boardHash(season, week)`.
- `nohotlink.test.ts`: no external logo host strings in any `src/**/*.{ts,svelte}`.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `web/scripts/logos-sm.sh` | build script | batch file-I/O | There are no shell scripts in the project outside `.venv`, and `web/scripts/` doesn't exist yet. Use the RESEARCH.md `logos-sm.sh` snippet. Note that `NYJ.png` is 4096px; `sips -Z 96` handles that. |
| Playwright screenshot/behavior script (D-25) | verification script | e2e | There's no existing Playwright script in `web/`. Keep it in the phase dir or the scratchpad, using the RESEARCH Validation section. |

## Metadata

**Analog search scope:** `web/src/components/*.svelte`, `web/src/lib/*.ts`, `web/src/app.css`, `web/src/main.ts`, `web/vite.config.ts`, `web/package.json`, `web/public/`
**Files scanned:** 25 components, 28 lib files; read in full: TeamChip, HistoryChart, MethodologyChart, Sparkline, sep.test, nohotlink.test, app.css, format.ts; partial: BoardRow, TeamPage, CalloutCard, FactorBars, HistoryPage, MethodologyPage, history.ts, format.test.ts
**Pattern extraction date:** 2026-11-11

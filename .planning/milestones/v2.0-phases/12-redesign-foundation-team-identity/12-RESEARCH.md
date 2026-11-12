# Phase 12: Redesign Foundation & Team Identity - Research

**Researched:** 2026-11-11
**Domain:** Svelte 5 + Vite 8 static SPA restyle (CSS tokens, Observable Plot 0.6.19 theme, self-hosted fonts, team logos, era-correct names)
**Confidence:** HIGH. Almost every claim was checked against the live codebase, the installed `node_modules`, the npm registry, or a scratch probe run in this session.

## Summary

This phase is a `web/`-only restyle with three new pure modules (`plotTheme.ts`, `logos.ts`, `teamNames.ts`), two new components (`ChartFrame.svelte`, `TeamLogo.svelte`), 32 committed 96px logo derivatives, and three exactly pinned Fontsource packages. The design contract (`12-UI-SPEC.md`) is already approved and very prescriptive. The planner's real job is to sequence the work safely across 21 existing components, and to know where the code fights the contract.

The codebase research turned up five things the UI-SPEC does not say:

1. **Plot's grid opacity trap.** A scale-level `grid: true` or `grid: 'var(--grid)'` renders at `strokeOpacity 0.1`. That default is hard-coded in `gridDefaults`, so the gridlines come out nearly invisible.
2. **HistoryChart measures the wrong font.** It measures label widths with the container's font. That font becomes Inter while the labels render in Plex Mono.
3. **Test guards on markup.** `sep.test.ts` pins `<Sep />` counts and the nav markup in `TeamPage`/`SiteHeader`.
4. **Logo sizes are not uniform.** `NYJ.png` is 4096×4096, not 500×500.
5. **Pipeline copy says "Commanders" for 2005 and 2010.** Generated blurbs and headlines use the current Washington nickname for those seasons. The UI layer can't fix that without touching pipeline copy.

The scratch probes confirmed four tools the plan depends on:
- **SSR rendering.** vitest (node env, no jsdom) can SSR-render Svelte components with `svelte/server` `render()`.
- **Env stubbing.** `vi.stubEnv('VITE_LOGOS','off')` changes `import.meta.env` at runtime.
- **Public-asset globs.** `import.meta.glob('/public/logos/*.png')` lists public assets inside tests.
- **Image resizing.** `sips -Z 96` keeps PNG alpha and produces about 5–7 KB files.

**Primary recommendation:** Build the pure modules and the test-backed primitives first: tokens and fonts, `plotTheme`, `logos`, `teamNames`, `TeamLogo`, `ChartFrame`, and the logo derivatives. Then restyle page by page, running `npm test && npm run check && npm run build` after each page. Finish with the Playwright screenshot sweep (20 images). Draw gridlines with explicit `Plot.gridY`/`gridX` marks carrying `strokeOpacity: 1`, not the scale `grid` option.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Area 1: Type system & palette (DESIGN-01, DESIGN-03)
- D-01 Fonts via Fontsource npm packages, imported once in `web/src/main.ts`: `@fontsource-variable/inter` (text/UI, all weights) and `@fontsource/ibm-plex-mono` weights 400 and 600 (numbers, annotations, chart ticks, SOURCE lines). No Google Fonts CDN, no `<link>` to third parties. Pin exact versions.
- D-02 Keep static files for Phase 14 satori: add `@fontsource/inter` (static) as a **devDependency**; its `files/inter-latin-{400,700}-normal.woff` plus `@fontsource/ibm-plex-mono/files/ibm-plex-mono-latin-400-normal.woff` are the card fonts. No fonts copied into `public/` (Vite bundles the webfonts with hashed names).
- D-03 Tokens: add `--font-sans: 'Inter Variable', <system stack>` and `--font-mono: 'IBM Plex Mono', ui-monospace, <stack>`; `--weight-bold: 700`; `--text-micro: 12px` (mono uppercase annotations/table headers, letter-spacing 0.04em). Keep the existing 4-size scale names so components don't churn. Numbers (scores, records, ranks, deltas, Elo, percentages) render in `--font-mono` with `font-variant-numeric: tabular-nums`.
- D-04 Palette (restrained, editorial): light = white page `--bg: #ffffff`, `--surface: #ffffff`, near-black `--text: #222222`, gray `--text-muted: #6b6b6b` (must keep ≥4.5:1 on white), rules `--border: #e3e3e3` plus a stronger `--rule-strong: #222222` for table header/section rules, chart gridlines `--grid: #e6e6e6`. Dark = `--bg: #141414`, `--surface: #1c1c1c`, `--text: #ededed`, `--text-muted: #a3a3a3`, `--border: #333333`, `--rule-strong: #ededed`, `--grid: #2e2e2e`. One brand accent for links/focus: a deep blue (`#1f5fbf` light / `#8db4ff` dark) — not FiveThirtyEight's orange/red brand tokens. Up/down keep green/red semantics but desaturated; mood band tokens unchanged in hue (they are the data encoding).
- D-05 Dark mode stays `prefers-color-scheme` driven (existing mechanism), no manual toggle in this phase.
- D-06 No FiveThirtyEight/538 name, logo, fox mark or fonts anywhere in the UI or code comments shipped to users. Methodology may keep any existing factual credit for the Elo method; no new 538 mentions.

#### Area 2: Shared chart theme (DESIGN-02)
- D-07 New `web/src/lib/plotTheme.ts` exports the shared Plot defaults (`style` with mono font, transparent background, muted color; `grid` only on the value axis using `--grid`; no axis domain lines and no tick marks (`tickSize: 0`); small mono tick labels; highlight helpers `HIGHLIGHT_WIDTH`, `BACKGROUND_STROKE` gray, `teamStroke(color)`), plus a `withTheme(options)` helper that merges them. Every Plot chart (HistoryChart, MethodologyChart, Sparkline) uses it.
- D-08 New `ChartFrame.svelte` wraps every full chart: bold headline (Inter 700, ~18–20px), one-line gray dek, the chart slot, and a footer line in mono uppercase micro text: `SOURCE: NFLVERSE · FEEL-GOOD SCORE` plus optional `NOTES: …`. Headline/dek are HTML, not Plot `title`. Applied to HistoryChart, MethodologyChart and the FactorBars breakdown (HTML chart). Sparkline is an inline micro-chart inside board rows: it uses the theme colors but no frame (documented exception).
- D-09 Highlight-one-gray-the-rest: highlighted team in its team color (thicker stroke + direct label at series end, with logo mark where a mark identifies a team); all other teams in neutral gray. Direct labels instead of legends wherever space allows; on narrow (<640px) widths an existing compact legend may remain for mood bands (labels can't fit), documented.
- D-10 Chart marks with logos (LOGO-02 "chart marks"): HistoryChart puts a small team logo (Plot `image` mark, 20–24px) at the highlighted line's last point next to the direct label. MethodologyChart has no teams. Never one logo per data point.

#### Area 3: Logos & team identity (LOGO-02, LOGO-03)
- D-11 `TeamLogo.svelte` (props: `franchise`, `primary`, `secondary`, `size` 16|20|24|32|48, `alt`), renders `<img src="/logos/sm/{F}.png" loading="lazy" decoding="async" width height alt>`; on `error` it swaps to the existing `TeamChip`. Logos are nominative identifiers only (never site branding/favicon).
- D-12 Small logo derivatives: the committed 500×500 PNGs (~50 KB each, ~1.6 MB per board) stay untouched for Phase 14 cards. Add `web/public/logos/sm/{F}.png` at 96×96 (2× for ≤48px display) produced once with macOS `sips -Z 96` via a tiny committed script `web/scripts/logos-sm.sh`; commit the 32 outputs. `pipeline/` logo code is not modified.
- D-13 Global off-switch: `VITE_LOGOS=off` (build-time env) makes `TeamLogo` render the chip only — a takedown is a config flip. Default on.
- D-14 Dark-mode legibility: logos sit on a light disc in dark mode (`--logo-disc: #f2f2f2` circle with ~12% padding); in light mode no disc (transparent). Applied inside TeamLogo so every usage is consistent.
- D-15 Placement: board rows (replaces chip), team page header (32–48px), records rows, callout cards, movers strip, recent-games opponent, HistoryChart end mark. The history page team selector stays text.
- D-16 Era names: new pure module `web/src/lib/teamNames.ts` with `eraName(franchise, season, meta)` and `eraAbbr(franchise, season)`: LV ≤2019 → "Oakland Raiders"/OAK; LAC ≤2016 → "San Diego Chargers"/SD; LA ≤2015 → "St. Louis Rams"/STL; WAS ≤2019 → "Washington" (never the former name), 2020–2021 → "Washington Football Team", 2022+ → current meta name. Otherwise the meta name. Current logo always.
- D-17 `isActiveFranchise(franchise, season)`: HOU returns false before 2002; any UI listing teams for a season must not render HOU before 2002 (data already can't produce it; guard + unit test).
- D-18 Name context per surface: board/team page/callouts/movers → the viewed season; records season rows → that season; streaks → the streak's start season (active streaks → current name); recent games → that season; history page selector and the chart → current name (franchise-level). A one-line note on the methodology page: "Relocated teams show their name from that season with the current logo."
- D-19 Unit tests (vitest) for `teamNames.ts` boundary seasons (2015/2016 STL→LA, 2016/2017 SD→LAC, 2019/2020 OAK→LV, WAS 2019/2020/2021/2022, HOU 2001/2002) and for TeamLogo fallback logic where testable as pure functions (e.g. `logoSrc`, `logosEnabled`).

#### Area 4: Editorial layout & behavior preservation (DESIGN-03, DESIGN-04)
- D-20 Restyle mostly through `app.css` tokens and component `<style>` blocks; no markup restructuring unless needed for the table look. Keep component props/APIs and routing untouched.
- D-21 Board = standings-style table: thin `--border` rule between rows, no zebra, no cards/shadows, strong rule under an uppercase mono micro header row; small 24px logo + name; right-aligned mono numbers; the score cell shaded with the row's mood-band color at low alpha (`color-mix`) with the number printed in it. Keep the existing band stripe or fold it into the shaded cell (planner's choice), keep my-team highlight, rank, record, mood label, delta.
- D-22 Page frame: bold headline + gray dek per page; single readable column ~680px for prose (methodology), tables/charts up to the existing `--content-max: 960px`. Sections separated by rules and whitespace, not boxed cards. Callout cards become rule-topped editorial blocks (no shadows).
- D-23 Mood labels/emoji untouched (playful contrast stays); `pipeline/src/fgs/mood.py` not touched.
- D-24 Behavior guardrails: routes, scrubber, my-team pin, callouts, copy-link, freshness stamp + disclaimer footer (Phase 10), 375px mobile layout without horizontal scroll. `npm test`, `npm run check`, `npm run build` must pass; existing tests are not weakened.
- D-25 Visual verification with Playwright at 1280px and 375px, light and dark (`emulateMedia colorScheme`), on board, team, history, records, methodology; screenshots saved in this phase dir under `screenshots/`.

### Claude's Discretion
- Exact pixel sizes, spacing, gridline values and the precise accent hue, within the constraints above.
- Whether the board's band stripe stays or merges into the shaded score cell.
- Whether to add Source Serif 4 for methodology prose (default: no — Inter only keeps it light).

(The approved `12-UI-SPEC.md` has already resolved these: the stripe folds into the shaded cell's 4px left edge, the type is Inter only, and the final hex values are set. The planner treats the UI-SPEC as locked too.)

### Deferred Ideas (OUT OF SCOPE)
- Era-specific historical logo art (deferred at v2.0 start).
- Manual light/dark toggle.
- Sortable board columns.
- Source Serif 4 for long-form prose.
- Explore page, EPA scatter, win totals (Phase 13); share cards (Phase 14).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DESIGN-01 | Self-hosted Inter (text) + IBM Plex Mono (numbers/annotations), tabular figures | Fontsource 5.3.0 packages verified (exports, family names `'Inter Variable'`/`'IBM Plex Mono'`, `font-display: swap`, latin woff2 sizes). Import paths are under Code Examples. Pitfall 2 covers the canvas re-measure. |
| DESIGN-02 | One shared chart theme: headline/dek, value-axis grid only, direct labels, highlight in color with the rest gray, SOURCE/NOTES footer | Plot 0.6.19 internals verified: the `gridDefaults` opacity of 0.1, `tickSize`, `line` default false, `style` applied via `Object.assign(svg.style)`, image mark `src` constant-path rule. Every existing Plot option site is mapped below. |
| DESIGN-03 | Editorial layout on 5 pages, light and dark, no 538 marks | Component inventory with file:line, the 38 `--weight-semibold` sites, the 4 font-size literals, the box/radius sites. `grep` shows no 538 references in `web/src` or `index.html`; the only "538" is pipeline data text (see Open Questions). |
| DESIGN-04 | All v1 behavior intact, 375px works, existing tests pass | Baseline 13 files / 167 tests pass, `svelte-check` 0 errors, build OK. Markup-pinning tests (`sep.test.ts`, `nohotlink.test.ts`, `history.test.ts`) are documented under Pitfalls. |
| LOGO-02 | Logos on board rows, team header, records rows, chart marks; chip fallback on error | `TeamChip` usages enumerated (7 sites). `sips` derivative procedure verified. The error-swap state pitfall is documented. Testing strategy: pure functions plus SSR render, with Playwright `route` 404 for the real error path. |
| LOGO-03 | Era-correct names (e.g. "San Diego Chargers" in 2010) | Every name/abbr render site enumerated with its season source (`row`/`season` props, `callout.season`, `RecentGame.season`, `ExtremeEntry.season`, `StreakEntry.start_season`). meta names verified. The pipeline "Commanders" copy gap is flagged. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Work only inside `feel-good-scorew/`, and in this phase only `web/` (plus the phase dir under `.planning/`). No root-level manifests and no shared deps.
- Keep process light: no new CI and no heavy test suites. The vitest unit tests named in D-19 and the UI-SPEC are the whole test budget.
- **Never touch** `pipeline/` model code (`mood.py`, `expectation.py`, `draft.py`, …), `pipeline/PREREGISTRATION*.md`, or `pipeline/inputs/`. Logo derivatives are generated by a `web/scripts/` script, not by `pipeline/src/fgs/logos.py`.
- Stack per project CLAUDE.md: Vite 8 + Svelte 5 (plain, hash routing) + Observable Plot 0.6.19. TypeScript stays `~6.0.3`, because svelte-check doesn't support TS 7.
- Node: nvm defaults to 20 on this machine. Run `source ~/.nvm/nvm.sh && nvm use 24` before any npm command (`engines.node` is `24.x`, `.nvmrc` is `24`).
- GSD workflow: edits happen through `/gsd-execute-phase`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Fonts (Inter Variable, Plex Mono) | CDN / Static (Vite-hashed `dist/assets/*.woff2`) | Browser (`@font-face`, unicode-range) | Bundled by Vite from npm, same-origin, no third-party requests |
| Logo derivatives 96px | CDN / Static (`web/public/logos/sm/`) | Build-time dev script (`sips`) | Generated once and committed. Served as plain static files |
| Logo render and fallback | Browser (`TeamLogo.svelte`) | — | The `<img>` error event and the disc styling run client-side |
| Logo kill-switch `VITE_LOGOS` | Build (Vite env replacement) | Browser (`logosEnabled()`) | Statically inlined at build, so a takedown means a rebuild with the env set |
| Era names/abbr | Browser (pure `teamNames.ts`) | — | Pipeline data carries only franchise codes. The display mapping is UI-only (pipeline frozen) |
| Chart theme | Browser (`plotTheme.ts` + Plot SVG) | — | Plot renders client-side in `$effect` |
| Data (scores, history) | Static JSON (`public/data`) | — | Unchanged in this phase |

## Standard Stack

### Core (already installed, verified in `web/package.json` / `node_modules`)
| Library | Version | Purpose |
|---------|---------|---------|
| svelte | 5.57.3 | Components (runes) |
| vite | 8.3.8 | Build/dev |
| @observablehq/plot | 0.6.19 (exact) | Charts |
| vitest | 5.1.0 | Tests (node environment, no jsdom) |
| typescript | ~6.0.3 | Types |

### New (this phase), all [VERIFIED: npm registry + tarball inspection + fontsource.org docs]
| Package | Version | Dep type | Purpose | Import |
|---------|---------|----------|---------|--------|
| `@fontsource-variable/inter` | 5.3.0 | dependencies (exact) | UI text, weights 100–900 variable. Family name `'Inter Variable'` | `import '@fontsource-variable/inter'` (index.css is byte-identical to `wght.css`: 7 `@font-face` subsets, `font-display: swap`) |
| `@fontsource/ibm-plex-mono` | 5.3.0 | dependencies (exact) | Numbers/annotations. Family name `'IBM Plex Mono'` | `import '@fontsource/ibm-plex-mono/400.css'` and `import '@fontsource/ibm-plex-mono/600.css'` |
| `@fontsource/inter` | 5.3.0 | devDependencies (exact) | Phase 14 card fonts only, never imported at runtime | Files exist: `files/inter-latin-400-normal.woff`, `files/inter-latin-700-normal.woff`. Plex: `files/ibm-plex-mono-latin-400-normal.woff` |

**Installation (exact pins):**
```bash
source ~/.nvm/nvm.sh && nvm use 24 && cd web
npm install --save-exact @fontsource-variable/inter@5.3.0 @fontsource/ibm-plex-mono@5.3.0
npm install --save-exact --save-dev @fontsource/inter@5.3.0
```

**Payload per page view (latin only, via unicode-range):** Inter latin woff2 48,256 B, Plex Mono latin 400 14,708 B, Plex Mono latin 600 15,620 B, about 79 KB total [VERIFIED: tarball]. Vite will emit every subset file into `dist/assets` (cyrillic, greek, vietnamese, latin-ext, plus Plex `.woff` fallbacks), but browsers only fetch the subsets a page's glyphs need. That's acceptable, and nothing needs subset pruning.

**Glyph coverage note:** Fontsource's latin range includes U+2000–206F (’ — · –), U+2191/2193 and U+2212. It does **not** include → ← (U+2192/2190) or ▲ ▼ (U+25B2/25BC). Those glyphs fall back to the system stack (`system-ui` / `ui-monospace`). That's harmless, but expect the arrows and triangles to render in the system face [VERIFIED: index.css unicode-range].

### Alternatives Considered
None. The fonts and stack are locked (D-01/D-02).

## Package Legitimacy Audit

| Package | Registry | Age | Downloads (wk ending 2026-11-10) | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| @fontsource-variable/inter | npm | created 2023-05-21 | 11.0M | github.com/fontsource/font-files | unavailable | Approved (official Fontsource docs confirm the `@fontsource-variable/*` naming and `'<Family> Variable'` family. No postinstall script. OFL-1.1) |
| @fontsource/ibm-plex-mono | npm | created 2020-12-23 | 4.6M | github.com/fontsource/font-files | unavailable | Approved (no postinstall, OFL-1.1) |
| @fontsource/inter | npm | created 2020-12-23 | 7.1M | github.com/fontsource/font-files | unavailable | Approved (no postinstall, OFL-1.1) |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none
*slopcheck could not be installed in this environment. The three packages are first-party Fontsource packages confirmed against fontsource.org docs and the registry (multi-million weekly downloads, 3–6 years old, no install scripts), and the planner may treat them as approved. If the planner's policy requires the strict gate anyway, put a single `checkpoint:human-verify` before the `npm install`.*

## Architecture Patterns

### System Architecture Diagram

```
 public/data/*.json ──fetch──▶ App.svelte (hash router) ──▶ Page components
                                                        │
          ┌────────────────────────────┬───────────────┼────────────────────────┐
          ▼                            ▼               ▼                        ▼
   BoardRow / Records rows      TeamPage header   HistoryPage            MethodologyPage
   Callout / Movers / Recent        │                 │                        │
          │                         │                 ▼                        ▼
          ├─ teamNames.eraName(F, season, meta) ◀─────┤ (current name)   ChartFrame(headline,dek,notes)
          ├─ teamNames.eraAbbr(F, season)             ▼                        │
          └─ TeamLogo(F) ──logosEnabled()?──no──▶ TeamChip             ChartFrame ──▶ MethodologyChart
                  │ yes                                │                       └─ withTheme(Plot opts)
                  ▼                                    ▼
           logoSrc(F) ─null─▶ TeamChip         HistoryChart: withTheme + gridY mark
                  │                              + Plot.image(logoSrc(team)) at last point
                  ▼                              (skipped when !logosEnabled() or src null)
           <img /logos/sm/F.png> ─onerror─▶ TeamChip (same size, once)
```

### Recommended Project Structure (new files only)
```
web/
├── scripts/logos-sm.sh            # one-off sips loop, committed
├── public/logos/sm/{F}.png        # 32 × 96px derivatives, committed
└── src/
    ├── lib/plotTheme.ts (+ .test.ts)
    ├── lib/logos.ts (+ .test.ts)       # FRANCHISES, logosEnabled, logoSrc
    ├── lib/teamNames.ts (+ .test.ts)   # eraName, eraAbbr, isActiveFranchise
    └── components/ChartFrame.svelte, TeamLogo.svelte
```

### Pattern 1: Gridlines as explicit marks (not the scale `grid` option)
**What:** Plot's scale/axis `grid` option builds a grid mark through `gridDefaults({opacity = 0.1, …})`. A string passes only `stroke` (`gridOptions` → `{stroke: isColor(grid) ? grid : undefined}`), so the result is `var(--grid)` at 10% opacity, which is effectively invisible against `#ffffff` [VERIFIED: node_modules/@observablehq/plot/dist/plot.js:6598-6611, 8873-8890]. `isColor` accepts `var(...)` and `color-mix(...)` [VERIFIED: dist/plot.js:894-902].
**Do this:** keep the axis gridless and add `Plot.gridY({ stroke: GRID_STROKE, strokeOpacity: 1, ticks })` (HistoryChart) or `Plot.gridX(...)` (MethodologyChart already does this at `MethodologyChart.svelte:52` with `--border`). Pass the same `ticks` array the axis uses.
**Reconciling with the UI-SPEC test bullet "`valueAxis()` has `tickSize: 0` and `grid: true`":** do one of the following.
- (a) `valueAxis()` returns `grid: true`, and `withTheme` converts any scale with `grid === true` into an explicit `gridX`/`gridY` mark with `strokeOpacity: 1`, setting the scale's grid to `false` so no second faint grid appears.
- (b) `valueAxis()` returns `grid: true`, plus a CSS rule in each chart container: `.chart :global(g[aria-label='y-grid']) { stroke: var(--grid); stroke-opacity: 1 }`. The grid group's aria-label is `` `${k}-grid` `` [VERIFIED: dist/plot.js:6573/6590]. CSS beats presentation attributes, the same technique the v1 tick-color overrides use.

**Recommend (b)** for minimum code: one CSS rule per chart (or one global rule in `app.css` scoped to `svg[class^='plot-'] g[aria-label$='-grid']`). It keeps `valueAxis()` literally as specified and the unit test intact.

### Pattern 2: `withTheme` merge
```ts
// web/src/lib/plotTheme.ts (sketch; contract in 12-UI-SPEC)
export function withTheme<T extends { style?: unknown }>(options: T): T {
  const style = typeof options.style === 'object' && options.style ? options.style : {}
  return { ...options, style: { ...themeStyle, ...style } } as T
}
```
Plot applies an object `style` via `Object.assign(svg.style, style)` [VERIFIED: dist/plot.js:4078-4086], so `fontFamily: 'var(--font-mono)'` works as an inline CSS var and overrides Plot's `font-family="system-ui, sans-serif"` attribute. Text marks inherit it. `Plot.text` also accepts `fontFamily`, `fontWeight`, `fontVariant` and `monospace` per mark.

### Pattern 3: Axis option shapes in 0.6.19
- `tickSize: 0` removes tick marks. The label offset then equals `tickPadding` (default 3) [CITED: node_modules/@observablehq/plot/src/scales.d.ts:557-583].
- `line` defaults to false. There's no domain line unless one is asked for [VERIFIED: scales.d.ts:632-635]. v1 charts already have none. The `Plot.ruleY([0], {stroke:'var(--border)'})` at `HistoryChart.svelte:100` is a hand-drawn baseline. Drop it, because the 0 gridline replaces it.
- `fontVariant` on quantitative axes defaults to `tabular-nums`.
- Facet axes (`fy` in MethodologyChart) default `tickSize: 0` already.

### Pattern 4: HistoryChart logo mark (Plot.image)
```ts
// Source: node_modules/@observablehq/plot/dist/plot.js Image mark (13038-13131)
const src = logosEnabled() ? logoSrc(team) : null
if (src && last.length) {
  if (dark) marks.push(Plot.dot(last, { x: 'x', y: 'y', r: LOGO / 2, fill: 'var(--logo-disc)', stroke: 'none' }))
  marks.push(Plot.image(last, { x: 'x', y: 'y', src, width: dark ? LOGO * 0.76 : LOGO }))
}
```
- A **constant** `src` must start with `/` or `./` (`isPath`) or a URL scheme. Any other string is treated as a **field name** [VERIFIED: dist/plot.js:13038-13054]. `/logos/sm/KC.png` qualifies, and `${import.meta.env.BASE_URL}logos/sm/KC.png` qualifies too while `base` is `/`.
- If only `width` is given, `height` defaults to `width`, and the image is centered on (x, y) [VERIFIED: dist/plot.js:13059-13131].
- Don't pass `r` to the image unless the circular `clip-path` is wanted.
- Same-origin, so no `crossOrigin` is needed.
- A failed `<image>` renders nothing, and the label still identifies the team. That's acceptable per the UI-SPEC.

### Pattern 5: TeamLogo error state keyed to `src`
Components get **reused with new props**. The TeamPage header persists across `#/team/A` → `#/team/B` navigation, and keyed lists reorder. A plain `let failed = $state(false)` stays `true` after a failed team and wrongly shows the chip for the next team. Key the failure to the src:
```svelte
<script lang="ts">
  import TeamChip from './TeamChip.svelte'
  import { logoSrc, logosEnabled } from '../lib/logos'
  let { franchise, primary = null, secondary = null, size = 24, alt = '' }:
    { franchise: string; primary?: string | null; secondary?: string | null; size?: 16|20|24|32|48; alt?: string } = $props()
  const src = $derived(logosEnabled() ? logoSrc(franchise) : null)
  let failedSrc = $state<string | null>(null)
  const showImg = $derived(src !== null && failedSrc !== src)
</script>
{#if showImg}
  <span class="logo" style:--logo-size="{size}px">
    <img {src} width={size} height={size} {alt} loading="lazy" decoding="async"
         aria-hidden={alt === '' ? 'true' : undefined} onerror={() => (failedSrc = src)} />
  </span>
{:else}
  <TeamChip {primary} {secondary} {size} />
{/if}
```
In a client-side `mount` (not hydration), Svelte attaches `onerror` synchronously when it creates the element, before the network fetch, so an early error event isn't lost [ASSUMED: Svelte 5 attribute/event ordering; low risk, and verified by the Playwright 404 check in Validation].

### Pattern 6: Re-measure after fonts load (HistoryChart)
`textWidth()` at `HistoryChart.svelte:42-47` reads `getComputedStyle(container).fontFamily`. Today that's the body font. After the theme, the SVG text is **Plex Mono** (from `themeStyle.fontFamily`) while the container `<div>` still inherits **Inter**. The gutter would be measured with the wrong font.
- Fix: give `.chart` `font-family: var(--font-mono)` (so computed style matches the SVG), **and** bump a `$state` counter on `document.fonts.ready`:
```ts
let fontsTick = $state(0)
$effect(() => { document.fonts?.ready.then(() => fontsTick++) })
// inside the plot $effect: void fontsTick
```
- The team label column also grows by `LOGO_MARK_PX + 4` when a logo is drawn (UI-SPEC).

### Anti-Patterns to Avoid
- **Scale-level `grid: 'var(--grid)'` and expecting it visible.** It renders at 0.1 opacity (Pattern 1).
- **Plot `title`/`subtitle`/`caption`.** Headline, dek and footer are HTML in ChartFrame.
- **One logo per data point.** Use one `Plot.image` for the highlighted team only.
- **`overflow-x: hidden` on html/body** to hide a 375px overflow. Fix with `min-width: 0` plus ellipsis (an existing project rule, `app.css:133-134`).
- **Hard-coding team names for eras inside components.** Every name goes through `eraName`/`eraAbbr`.
- **Changing component props/APIs** (D-20). `MethodologyChart` derives its headline/dek from the existing `metric` prop, and `HistoryPage` composes the ChartFrame around `HistoryChart`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Webfont hosting | Copying woff2 into `public/`, writing `@font-face` | Fontsource imports | Hashed assets, unicode-range subsets, `font-display: swap` included |
| Image resize | Node `sharp`/canvas script | macOS `sips -Z 96` (sips-316 on this machine) | Zero deps, alpha preserved [VERIFIED: scratch probe: KC/LAC/WAS 96×96, hasAlpha yes, 5.4–7.1 KB] |
| Contrast pick for highlight | New contrast code | Existing `pickHighlight`/`contrastRatio` in `lib/history.ts` | Already tested |
| Mood band index → token | New mapping | `bandIndex` + `moodToken` in `lib/format.ts` | Already used by stripes |
| Env stubbing in tests | Module mocking | Param-injected `logosEnabled(env = import.meta.env.VITE_LOGOS)` (plus `vi.stubEnv` if wanted) | Pure, deterministic |

## Runtime State Inventory

Not a rename or migration of stored identifiers. Era names are display-only. Stated explicitly:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None. JSON keeps franchise codes (`LV`, `LAC`, `LA`, `WAS`), and display mapping happens client-side | none |
| Live service config | Vercel project env: a `VITE_LOGOS` var does not exist yet (default on) | none now. Document that a takedown means setting `VITE_LOGOS=off` in Vercel env and redeploying |
| OS-registered state | None | none |
| Secrets/env vars | `VITE_LOGOS` is new and build-time only. Vite exposes `VITE_*` from `process.env` and `.env*` [ASSUMED: standard Vite env behavior; verify with `VITE_LOGOS=off npm run build && grep -c '/logos/sm/' dist/assets/*.js`] | add a short note to `web/README` |
| Build artifacts | `web/dist` is gitignored. localStorage `my-team` key unchanged | none |

## Codebase Inventory (file:line, for task scoping)

### TeamChip → TeamLogo replacement sites (7)
| File:line | Current | New size | Name/abbr season source |
|-----------|---------|----------|-------------------------|
| `BoardRow.svelte:6,63` | `<TeamChip primary secondary />` (16) | 24 | `season` prop (already passed, line 15). abbr at `:64` is `row.franchise` → `eraAbbr(row.franchise, season)`. name `:37` → `eraName`. `srText` `:53-55` uses `name`. **PinButton `:81` keeps the current name** (UI-SPEC) |
| `CalloutCard.svelte:3,45` | chip 16 | 20 | `callout.season` (`Callout.season` exists, `types.ts:41`). `name` `:16` feeds headline sr text, "See {name}" and manual-copy aria-label |
| `MoversStrip.svelte:3,30` | chip 16 | 20 | `c.season`. sr name `:28`, abbr `:31` |
| `RecentGames.svelte:2,33` | chip 16 | 20 | `g.season` (`RecentGame.season`, `team.ts:5`). sr name `:28`, abbr `:34` |
| `TeamPage.svelte:11,172` | chip size 24 | 32 / 48 (media query) | `season` prop. `name` `:24` is used in loading/error/empty copy (`:155,160,162-165`) and the h2 `:173`. **PinButton `:174` keeps the current name** |
| `RecordsPage.svelte:5,109` (extremes) | chip 16 | 24 | `e.season` → `teamName()` `:39` needs a season param |
| `RecordsPage.svelte:134` (streaks) | chip 16 | 24 | `s.active ? current : s.start_season` |
| `RecordsPage.svelte:69` (excluded footnote) | `teamName(x.franchise)` | — | `x.season` (e.g. "the 2002 Houston Texans") |

Current-name sites that stay current: `HistoryPage.svelte:61` (selector options), `:105,108` (summary), `:133` ("See {name} →"), `:140` (`teamName` prop → chart aria-label `HistoryChart.svelte:155`).

`TeamChip.svelte`: `size` union `16 | 24` (`:6`), with `.large` using `--space-lg` (`:32-35`). Extend to `16|20|24|32|48` with `style:width/height={size}px` (or a `--chip-size` override). 24 must stay 24px.

### Plot option sites to migrate to `withTheme`
| File:line | What changes |
|-----------|--------------|
| `HistoryChart.svelte:140` | `style` → `withTheme`. Font becomes mono, 14→12 (CHART_FONT_PX) |
| `HistoryChart.svelte:142-151` | x: `baseAxis()`. y: `valueAxis()` + gridY at `[0,20,40,60,80,100]` |
| `HistoryChart.svelte:96,100` | season dividers stay `--border` dashed. Remove `ruleY([0])` |
| `HistoryChart.svelte:105,110,117` | `BACKGROUND_STROKE`, `HIGHLIGHT_WIDTH`, `teamStroke(color)` |
| `HistoryChart.svelte:122-132` | label: mono 600 14 (`LABEL_FONT_PX`), `dx` = `LOGO/2 + 4` when the logo is shown |
| `HistoryChart.svelte:191,202,206-209` | legend `12px` → `--text-micro`, square swatches, delete the tick CSS override |
| `MethodologyChart.svelte:47,48,52,53,69,76` | style → theme. x → `valueAxis` (grid already via `gridX`; switch its stroke to `GRID_STROKE` + `strokeOpacity: 1`). Ref rule `:69` `--border` → `--text-muted` dashed `4,3`. Composite dot stays `--accent` |
| `MethodologyChart.svelte:95-98,116-123` | `<figure>/<figcaption>` → `ChartFrame` (headline/dek by `metric`, notes = existing sentence + `intervalNote`). `axisLabel` `:25-27` remains in `aria-label` |
| `Sparkline.svelte:55,59,70` | `style` → `themeStyle`. Baseline rule `--border` → `--text-muted` dashed. `fontSize: 11` → 12, mono |

### Typography migration counts [VERIFIED: grep]
- `--weight-semibold`: 38 occurrences (37 in 18 components + 1 token def). Inter text → `--weight-bold`. Mono numbers keep semibold.
- Font-size literals: `HistoryChart.svelte:191` (12px), `PinButton.svelte:35` (20px), `Sparkline.svelte:70` (11), `StatusPanel.svelte:101` (0.9em, with its own mono stack at `:100` → `var(--font-mono)`).
- `box-shadow`: only `TeamChip.svelte:29` (chip outline, keep it).
- Radius on editorial blocks to set to 0: `BoardRow:118`, `CalloutCard:86`, `MoversStrip:93`, `RecordsPage:216`, `MethodologyPage:285`, `MoodBoard:124,131` (skeleton). Keep radius on `Scrubber`/`HistoryPage` select/buttons/`StatusPanel`.

### Existing tests that pin markup, colors or text (must stay green, not weakened)
| Test | Pins | Risk in this phase |
|------|------|-------------------|
| `lib/sep.test.ts:41-47` | `TeamPage.svelte` contains **exactly 5** `<Sep />`. The week-nav `<nav class="week-nav">` has exactly 2 and contains `boardHash(season, week)` | Wrapping record/rank in `.num` spans is fine. Adding or removing any `<Sep />` in TeamPage fails |
| `lib/sep.test.ts:30-38` | SiteHeader nav: 3 × `<span class="item"><Sep /><a `, and `.item { white-space: nowrap }` | Restyling the nav must keep that exact markup |
| `lib/sep.test.ts:22-28` | No hand-rolled `class="sep"` or `<span>·</span>` in any component | ChartFrame's `SOURCE: NFLVERSE · FEEL-GOOD SCORE` is a single text node, so it's safe. Don't wrap `·` in its own span |
| `lib/nohotlink.test.ts` | No `espn…cdn`/`wiki…pedia` `.png/.svg` URL in any `src/**/*.{ts,svelte}` or `index.html` | Don't paste `manifest.json` source URLs into `logos.ts` or `logos-sm.sh` comments (the .sh isn't scanned, but keep it clean) |
| `lib/history.test.ts:88-99` | `pickHighlight` with literal bgs `#f6f6f3`/`#121316`, plus the fallback path with `'var(--bg)'`/`''` | Changing `FALLBACK_BG` (`history.ts:121`) to `#ffffff`/`#141414` keeps every assertion true (#002244 vs #fff passes; #002244 vs #141414 fails → secondary #FFFFFF). Optionally update the comment literals |

Baseline (2026-11-11, Node 24.20.0): **13 test files / 167 tests pass**, `svelte-check` **0 errors / 0 warnings** (229 files), `vite build` OK (CSS 30.4 KB, JS 397.6 KB) [VERIFIED: ran].

### Logo assets
- `web/public/logos/*.png`: 31 files at 500×500, plus **`NYJ.png` at 4096×4096 (130 KB)** [VERIFIED: sips]. `sips -Z 96` scales any size down, so the script handles it, but don't write it to assume 500px.
- `manifest.json` (Phase 11) lists source URLs and sha256. Leave it untouched.
- `meta.json` has 32 teams: HOU "Houston Texans", LV "Las Vegas Raiders", LAC "Los Angeles Chargers", LA "Los Angeles Rams", WAS "Washington Commanders". `seasons[0..2].n_teams = 31` (1999–2001) [VERIFIED].

## Common Pitfalls

### Pitfall 1: Invisible gridlines
**What goes wrong:** You set `y: { grid: 'var(--grid)' }` and see almost nothing.
**Why it happens:** Plot's `gridDefaults` opacity is 0.1.
**How to avoid:** Use Pattern 1. Use an explicit grid mark with `strokeOpacity: 1`, or a CSS override on `g[aria-label$='-grid']`.
**Warning signs:** The screenshots show no horizontal rules on HistoryChart.

### Pitfall 2: Gutter sized against the wrong font
**What goes wrong:** The team label or band labels get clipped or collide in the right gutter.
**Why it happens:** `textWidth` measures the container's (Inter or fallback) font, while the SVG renders Plex Mono, and fonts load after the first paint.
**How to avoid:** Use Pattern 6: set the container font to mono and re-render on `document.fonts.ready`.

### Pitfall 3: Sticky logo failure across navigation
**What goes wrong:** One 404 leaves the chip in place on later teams.
**How to avoid:** Key the failure to the `src` (Pattern 5).

### Pitfall 4: Breaking `sep.test.ts` with a header refactor
**What goes wrong:** The tests fail after a markup tidy-up in TeamPage or SiteHeader.
**How to avoid:** Keep `<Sep />` counts and SiteHeader nav markup byte-compatible. Run `npm test` after each component.

### Pitfall 5: Era names leak into "current" contexts, or vice versa
**What goes wrong:** You get the PinButton saying "Pin San Diego Chargers", the HistoryChart labelled "OAK", or "LV" on 2005 records rows.
**How to avoid:** Follow the D-18 table. Each site gets its season from the table above. Use the current name for PinButton, the History page, and active streaks.

### Pitfall 6: Pipeline-generated copy still says "Commanders" for old seasons
**What goes wrong:** On a 2005 Washington team page, the header reads "Washington" while the blurb says "The Commanders are a below-average team…" and the callout headline reads "Commanders +11" [VERIFIED: `public/data/snapshots/2005.json` has 25 such strings, `2010.json` has 14]. Raiders, Chargers and Rams nicknames are era-neutral, so only Washington is affected.
**Why it happens:** `pipeline/src/fgs/export.py`/`insights.py` build copy from the current `nick`. The pipeline is frozen and out of scope.
**How to avoid:** See Open Question 1. Recommended: either a tiny web-side `eraCopy(text, franchise, season)` that rewrites `\bThe Commanders\b`→"Washington" and `\bCommanders\b`→"Washington" (≤2019) or "Football Team" (2020–21), unit-tested; or accept it and document it as a known gap. Don't edit pipeline code.

### Pitfall 7: "538" appears in shipped data text
**What goes wrong:** A naive `grep -r 538 web/` verification flags `public/data/methodology.json`. Its `notes[brier_maps]` text says "fixed 538-style update constants", and `snapshots/*.json` contain the integer 538.
**How to avoid:** That note is the existing factual Elo credit, which D-06 explicitly permits. It's pipeline-owned, so don't edit it. Scope the D-06 grep to `web/src`, `web/index.html` and `web/public/*.svg` (all clean today [VERIFIED: grep]).

### Pitfall 8: `VITE_LOGOS` is build-time, not runtime
**What goes wrong:** Someone expects a runtime toggle.
**Why it happens:** Vite statically replaces `import.meta.env.VITE_LOGOS` at build. A takedown needs the env var set **and** a redeploy.
**Also:** with `logosEnabled(env = import.meta.env.VITE_LOGOS)`, tests pass the value explicitly. `vi.stubEnv` also works [VERIFIED: scratch probe printed `env off`]. Type: `ImportMetaEnv` extends `Record<string, any>` in `vite/types/importMeta.d.ts`, so no `.d.ts` augmentation is needed for `svelte-check`.

### Pitfall 9: Dark mode disc only via media query
**What goes wrong:** `--logo-disc` is `transparent` in light and `#f2f2f2` in dark, set in `app.css`.
**How to avoid:** Put the disc styling on `.logo` in TeamLogo's `<style>` under `@media (prefers-color-scheme: dark)`, or just always set `background: var(--logo-disc); border-radius: 50%` and switch the image inset by media query. For HistoryChart, the `dark` prop already exists (`HistoryChart.svelte:16,26`, fed by HistoryPage's `matchMedia` listener at `HistoryPage.svelte:65-72`).

### Pitfall 10: Muted text on shaded cells
**What goes wrong:** Muted text lands on a tinted cell. The UI-SPEC forbids it, and the current BoardRow puts `elo` inside `.score-cell` (`BoardRow.svelte:72-75`).
**How to avoid:** Move the Elo line out of the cell into the record column at ≥1024px (UI-SPEC Board section).

## Code Examples

### main.ts font imports (before app.css)
```ts
// web/src/main.ts
import '@fontsource-variable/inter'
import '@fontsource/ibm-plex-mono/400.css'
import '@fontsource/ibm-plex-mono/600.css'
import { mount } from 'svelte'
import './app.css'
import App from './App.svelte'
```
Package `exports` map `"."` → `index.css` and `"./*"` → `./*.css` [VERIFIED: npm view exports], so both `…/400.css` and `…/400` resolve. Use the explicit `.css`.

### logos-sm.sh
```bash
#!/usr/bin/env bash
# Builds 96px logo derivatives for UI use (2x for <=48px). Originals stay untouched.
set -euo pipefail
cd "$(dirname "$0")/../public/logos"
mkdir -p sm
for f in *.png; do
  sips -Z 96 "$f" --out "sm/$f" >/dev/null
done
ls sm/*.png | wc -l   # expect 32
```
`sips -Z` fits the longest side, which keeps the square aspect. Run it from any cwd.

### logos.ts
```ts
export const FRANCHISES = ['ARI','ATL','BAL','BUF','CAR','CHI','CIN','CLE','DAL','DEN','DET','GB','HOU','IND','JAX','KC',
  'LA','LAC','LV','MIA','MIN','NE','NO','NYG','NYJ','PHI','PIT','SEA','SF','TB','TEN','WAS'] as const
const KNOWN = new Set<string>(FRANCHISES)
export const logosEnabled = (env: unknown = import.meta.env.VITE_LOGOS): boolean =>
  !(typeof env === 'string' && env.trim().toLowerCase() === 'off')
export const logoSrc = (f: string | null | undefined): string | null =>
  typeof f === 'string' && /^[A-Z]{2,3}$/.test(f) && KNOWN.has(f) ? `${import.meta.env.BASE_URL}logos/sm/${f}.png` : null
```
(The list matches the 32 files in `public/logos` and the 32 keys of `meta.teams` [VERIFIED].)

### Test: every derivative exists and matches meta (no fs import needed)
```ts
// web/src/lib/logos.test.ts
const sm = Object.keys(import.meta.glob('/public/logos/sm/*.png'))   // lazy glob: paths only
const meta = Object.values(import.meta.glob('/public/data/meta.json', { eager: true, import: 'default' }))[0] as Meta
expect(sm.map((p) => p.split('/').pop()!.replace('.png', '')).sort()).toEqual([...FRANCHISES].sort())
expect(Object.keys(meta.teams).sort()).toEqual([...FRANCHISES].sort())
```
[VERIFIED: scratch probe, `import.meta.glob('/public/logos/*.png')` returned 32 keys and meta.json loaded with 32 teams.] This avoids `node:fs`, which isn't in `tsconfig.app.json` `types` and would fail `svelte-check`.

### Test: TeamLogo render branches via SSR (no jsdom)
```ts
import { render } from 'svelte/server'
import TeamLogo from '../components/TeamLogo.svelte'
it('renders img for a known franchise', () => {
  const { body } = render(TeamLogo, { props: { franchise: 'KC', primary: '#E31837', secondary: '#FFB81C', size: 24 } })
  expect(body).toContain('src="/logos/sm/KC.png"')
})
it('renders the chip for unknown franchise', () => {
  const { body } = render(TeamLogo, { props: { franchise: 'XXX', size: 24 } })
  expect(body).toContain('class="chip')
})
it('renders the chip when logos are off', () => {
  vi.stubEnv('VITE_LOGOS', 'off')
  // ...render KC, expect 'chip' and no '<img'
  vi.unstubAllEnvs()
})
```
[VERIFIED: scratch probe SSR-rendered `TeamChip.svelte` under this project's vite config; output `<span class="chip svelte-… large" aria-hidden="true" style="--team-primary: …">`.] The `onerror` swap can't fire in SSR, so it gets covered in Playwright (see Validation).

### teamNames.ts
```ts
import type { Meta } from './types'
export function eraName(f: string, season: number, meta: Pick<Meta, 'teams'>): string {
  if (f === 'LV' && season <= 2019) return 'Oakland Raiders'
  if (f === 'LAC' && season <= 2016) return 'San Diego Chargers'
  if (f === 'LA' && season <= 2015) return 'St. Louis Rams'
  if (f === 'WAS' && season <= 2019) return 'Washington'
  if (f === 'WAS' && season <= 2021) return 'Washington Football Team'
  return meta.teams[f]?.name ?? f
}
export function eraAbbr(f: string, season: number): string {
  if (f === 'LV' && season <= 2019) return 'OAK'
  if (f === 'LAC' && season <= 2016) return 'SD'
  if (f === 'LA' && season <= 2015) return 'STL'
  return f
}
export const isActiveFranchise = (f: string, season: number): boolean => !(f === 'HOU' && season < 2002)
```
These follow the D-16 boundaries exactly. Never write Washington's former name, including in tests and comments.

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Google Fonts `<link>` | Fontsource npm (self-hosted, hashed) | No third-party requests. Matches D-01 |
| `@fontsource/inter` static weights for UI | `@fontsource-variable/inter` (family `'Inter Variable'`) | One file per subset covers 400/700 |
| Plot scale `grid: true` | Explicit `gridX/gridY` marks or CSS override when a specific color/opacity is needed | Grid opacity is fixed at 0.1 otherwise |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Svelte 5 attaches `onerror` before the image fetch in client `mount`, so early errors aren't missed | Pattern 5 | Logo 404 shows a blank box instead of the chip. Caught by the Playwright 404 check |
| A2 | Vite exposes `VITE_LOGOS` from `process.env` at build (`VITE_LOGOS=off npm run build`) | Runtime State, Pitfall 8 | The kill switch silently doesn't work. Verify with a one-off build + grep in the plan |
| A3 | The Vercel build picks `VITE_LOGOS` up from project env vars | Runtime State | Same as A2. Only matters at takedown time |

## Open Questions

1. **Era-incorrect "Commanders" in pipeline-generated blurbs and callout headlines (2005, 2010, … ≤2021).**
   - What we know: the strings are in `snapshots/*.json`, `callouts.json` and `blurb`/`headline` fields. Pipeline edits are out of scope. LOGO-03 is about displayed names, and the success criterion example is the Chargers (unaffected).
   - Recommendation: add a small pure `eraCopy(text, franchise, season)` in `teamNames.ts`. For `WAS` and season ≤2021, replace `The Commanders`/`Commanders` with "Washington" (≤2019) or "the Football Team"/"Football Team" (2020–21). Apply it to `row.blurb` (TeamPage `:198`) and callout `headline`/`detail` (CalloutCard, MoversStrip sr text). Cover it with 3–4 unit tests. If the planner wants zero scope creep, document it as a known gap instead. Don't touch the pipeline either way.
2. **OFL license notice.** The fonts ship from `node_modules` (each package includes `LICENSE`). Bundled webfonts on a static site are normal OFL use. Optionally add one line to `web/README.md` ("Fonts: Inter, IBM Plex Mono — SIL OFL 1.1 via Fontsource"). It's low cost, and it satisfies the PITFALLS checklist item "Font licenses (OFL) committed".
3. **Grid approach (Pattern 1, (a) vs (b)).** Recommended (b), the CSS override, because it keeps the UI-SPEC `valueAxis()` contract literal. The planner should pick one and use it in all three charts.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node (nvm) | npm test/check/build | ✓ | 24.20.0 (also 22.23.3; default is 20.19.0, so `nvm use 24` is required) | — |
| npm registry | Fontsource install | ✓ | — | — |
| `sips` (macOS) | logo derivatives | ✓ | sips-316 | — (outputs are committed, so CI never needs it) |
| Playwright (Python) + Chromium | D-25 screenshots, logo-404 check | ✓ | `/Library/Frameworks/Python.framework/Versions/3.13/bin/playwright`, chromium-1248 cached | Playwright MCP (writes only inside the project, `.playwright-mcp/`) |
| slopcheck | package audit | ✗ | — | Manual registry checks (done above) |

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | vitest 5.1.0 (node environment, no jsdom). Svelte SSR via `svelte/server` works under the existing `vite.config.ts` |
| Config file | none (vitest reads `web/vite.config.ts`) |
| Quick run command | `source ~/.nvm/nvm.sh && nvm use 24 >/dev/null && cd web && npx vitest run src/lib/<file>.test.ts` |
| Full suite command | `source ~/.nvm/nvm.sh && nvm use 24 && cd web && npm test && npm run check && npm run build` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DESIGN-01 | Fonts imported, tokens set, no external font links | unit (raw-source scan) | `npx vitest run src/lib/fonts.test.ts`. Glob `../main.ts?raw` contains the 3 imports before `./app.css`. `index.html` + sources contain no `fonts.googleapis`/`fonts.gstatic`. `app.css?raw` defines `--font-mono` with `'IBM Plex Mono'` | ❌ Wave 0 |
| DESIGN-01 | Build bundles woff2 | build smoke | `npm run build && ls dist/assets/*.woff2 \| grep -c inter-latin-wght` | n/a (command) |
| DESIGN-02 | Theme contract | unit | `npx vitest run src/lib/plotTheme.test.ts` (withTheme merge, teamStroke fallback, valueAxis tickSize 0 / grid true) | ❌ Wave 0 |
| DESIGN-02 | All 3 Plot charts use the theme, no Plot `title` | unit (raw-source scan) | extend `plotTheme.test.ts`: glob `../components/{HistoryChart,MethodologyChart,Sparkline}.svelte?raw` includes `withTheme(` or `themeStyle`, and none contains `title:` / `caption:` | ❌ Wave 0 |
| DESIGN-02 | ChartFrame renders headline/dek/SOURCE/NOTES | unit (SSR) | `npx vitest run src/lib/chartFrame.test.ts` (`render(ChartFrame, {props, children})`. Snippet children can be built with `createRawSnippet` from `svelte`) [ASSUMED: createRawSnippet SSR; else test via a wrapper fixture] | ❌ Wave 0 |
| DESIGN-03 | Editorial look, light and dark, 5 pages | manual-visual (Playwright) | Python Playwright script, 1280 & 375 × light/dark × 5 pages → 20 PNGs in `screenshots/` | ❌ Wave 0 (script in phase dir or scratchpad) |
| DESIGN-03 | No 538 marks in shipped code | unit (raw-source scan) | glob `../**/*.{ts,svelte}` + `index.html`: no `/fivethirtyeight\|\b538\b/i` (exclude the test file) | ❌ Wave 0 |
| DESIGN-04 | Existing tests unchanged and passing | regression | `npm test` (≥167 tests, 13 files + new) | ✅ |
| DESIGN-04 | 375px no horizontal scroll, routes/scrubber/pin/copy-link work | e2e (Playwright) | in the same script: `document.documentElement.scrollWidth <= innerWidth` per route at 375. Click pin → reload → "My team" badge present. Scrubber keyboard step changes the hash. Copy link → status text | ❌ Wave 0 |
| LOGO-02 | `logoSrc`/`logosEnabled`, 32 derivatives exist | unit | `npx vitest run src/lib/logos.test.ts` | ❌ Wave 0 |
| LOGO-02 | TeamLogo branches (img / chip on unknown / chip when off) | unit (SSR) | `npx vitest run src/lib/teamLogo.test.ts` | ❌ Wave 0 |
| LOGO-02 | Real error fallback | e2e | Playwright `page.route('**/logos/sm/KC.png', r => r.fulfill(status=404))` → KC row shows `.chip` | ❌ Wave 0 |
| LOGO-02 | Kill switch at build | build smoke | `VITE_LOGOS=off npm run build && ! grep -q 'logos/sm' dist/assets/*.js` (or assert `logosEnabled` is constant-folded) [ASSUMED behavior; adjust the assertion to what the build emits] | n/a |
| LOGO-03 | Era boundaries, HOU guard, fallback to code | unit | `npx vitest run src/lib/teamNames.test.ts` | ❌ Wave 0 |
| LOGO-03 | "San Diego Chargers" visible on `#/team/LAC/2010/…` | e2e | Playwright text assertion + screenshot | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the touched module's `npx vitest run src/lib/<x>.test.ts`, plus `npm run check` when a `.svelte` file changed.
- **Per wave merge:** `npm test && npm run check && npm run build`.
- **Phase gate:** full suite green + the 20 screenshots + Playwright behavior checks before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `web/src/lib/plotTheme.test.ts`: theme contract + chart source scan
- [ ] `web/src/lib/logos.test.ts`: `logosEnabled`, `logoSrc`, 32 derivatives ↔ meta
- [ ] `web/src/lib/teamNames.test.ts`: D-19 boundaries (+ `eraCopy` if adopted)
- [ ] `web/src/lib/teamLogo.test.ts`: SSR branches
- [ ] `web/src/lib/fonts.test.ts` (or fold into an existing "brand guard" test): font imports, no CDN, no 538
- [ ] Playwright script (Python, already installed) for screenshots + 375px overflow + behavior + logo-404. Run against `npm run preview` (port 4173) or `npm run dev`. Use `?r=1` to force a fresh data load (project memory note).
- Framework install: none needed.

## Security Domain

`security_enforcement` is `false` in `.planning/config.json`, so this section is omitted. (For the record: there's no auth or user input in this phase. Assets stay same-origin, there are no new third-party requests, and the logo `alt` is empty/decorative.)

## Sources

### Primary (HIGH confidence)
- Codebase: `web/src/**` (all components and libs read or grepped with line numbers), `web/package.json`, `web/vite.config.ts`, `tsconfig.app.json`, `public/logos/*`, `public/data/meta.json`, `methodology.json`, `snapshots/2005.json`, `snapshots/2010.json`
- `web/node_modules/@observablehq/plot` 0.6.19: `dist/plot.js` (gridDefaults, gridOptions, isColor, inferAxes, Image mark, applyInlineStyles), `src/scales.d.ts`, `src/marks/image.d.ts`
- npm registry: `npm view` for the three Fontsource packages (version 5.3.0, exports, license, no postinstall, created dates). `npm pack` tarball inspection (CSS family names, unicode ranges, file names and sizes)
- fontsource.org/docs/getting-started/variable: `@fontsource-variable/*` naming and the `'<Family> Variable'` family name
- Scratch probes (this session): `sips -Z 96` output; vitest SSR render of `TeamChip.svelte`; `vi.stubEnv`; `import.meta.glob('/public/...')`; baseline `npm test`/`check`/`build`

### Secondary (MEDIUM confidence)
- `.planning/research/PITFALLS.md` (Pitfalls 6, 11, 13, 14, minor), `.planning/research/STACK.md` (in project CLAUDE.md)

### Tertiary (LOW confidence)
- None used for any recommendation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. Registry, tarballs and official docs all agree.
- Architecture/patterns: HIGH. Plot behavior was read from the installed source, and the test techniques were probed live.
- Pitfalls: HIGH. Each one was found in this codebase or its data. The Svelte `onerror` timing (A1) and Vite env (A2) are ASSUMED and get checked in Validation.

**Research date:** 2026-11-11
**Valid until:** 2026-12-11 (stable stack; re-check if Plot or Fontsource versions move)

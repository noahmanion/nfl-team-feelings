# Phase 12: Redesign Foundation & Team Identity - Context

**Gathered:** 2026-11-11
**Status:** Ready for planning
**Mode:** Smart discuss, full autonomy (recommended answers auto-accepted; no user prompts)

<domain>
## Phase Boundary

Restyle the existing v1 site (`web/` only) into clean, editorial, data-journalism design: self-hosted Inter and IBM Plex Mono, one shared Observable Plot chart theme, editorial tables with small logos and shaded score cells, in light and dark mode. Add team logos everywhere a team is identified (LOGO-02) and era-correct team names for relocated or renamed franchises (LOGO-03). Every v1 behavior stays intact (DESIGN-04).

Requirements: DESIGN-01, DESIGN-02, DESIGN-03, DESIGN-04, LOGO-02, LOGO-03.

Out of scope: the Explore page and scatters (Phase 13), win totals display (Phase 13), share cards and share pages (Phase 14), any pipeline model code (`mood.py`, `expectation.py`, `draft.py`, etc.), `pipeline/PREREGISTRATION*.md`, `pipeline/inputs/`.
</domain>

<decisions>
## Implementation Decisions

### Area 1: Type system & palette (DESIGN-01, DESIGN-03)
- D-01 Fonts via Fontsource npm packages, imported once in `web/src/main.ts`: `@fontsource-variable/inter` (text/UI, all weights) and `@fontsource/ibm-plex-mono` weights 400 and 600 (numbers, annotations, chart ticks, SOURCE lines). No Google Fonts CDN, no `<link>` to third parties. Pin exact versions.
- D-02 Keep static files for Phase 14 satori: add `@fontsource/inter` (static) as a **devDependency**; its `files/inter-latin-{400,700}-normal.woff` plus `@fontsource/ibm-plex-mono/files/ibm-plex-mono-latin-400-normal.woff` are the card fonts. No fonts copied into `public/` (Vite bundles the webfonts with hashed names).
- D-03 Tokens: add `--font-sans: 'Inter Variable', <system stack>` and `--font-mono: 'IBM Plex Mono', ui-monospace, <stack>`; `--weight-bold: 700`; `--text-micro: 12px` (mono uppercase annotations/table headers, letter-spacing 0.04em). Keep the existing 4-size scale names so components don't churn. Numbers (scores, records, ranks, deltas, Elo, percentages) render in `--font-mono` with `font-variant-numeric: tabular-nums`.
- D-04 Palette (restrained, editorial): light = white page `--bg: #ffffff`, `--surface: #ffffff`, near-black `--text: #222222`, gray `--text-muted: #6b6b6b` (must keep ≥4.5:1 on white), rules `--border: #e3e3e3` plus a stronger `--rule-strong: #222222` for table header/section rules, chart gridlines `--grid: #e6e6e6`. Dark = `--bg: #141414`, `--surface: #1c1c1c`, `--text: #ededed`, `--text-muted: #a3a3a3`, `--border: #333333`, `--rule-strong: #ededed`, `--grid: #2e2e2e`. One brand accent for links/focus: a deep blue (`#1f5fbf` light / `#8db4ff` dark) — not FiveThirtyEight's orange/red brand tokens. Up/down keep green/red semantics but desaturated; mood band tokens unchanged in hue (they are the data encoding).
- D-05 Dark mode stays `prefers-color-scheme` driven (existing mechanism), no manual toggle in this phase.
- D-06 No FiveThirtyEight/538 name, logo, fox mark or fonts anywhere in the UI or code comments shipped to users. Methodology may keep any existing factual credit for the Elo method; no new 538 mentions.

### Area 2: Shared chart theme (DESIGN-02)
- D-07 New `web/src/lib/plotTheme.ts` exports the shared Plot defaults (`style` with mono font, transparent background, muted color; `grid` only on the value axis using `--grid`; no axis domain lines and no tick marks (`tickSize: 0`); small mono tick labels; highlight helpers `HIGHLIGHT_WIDTH`, `BACKGROUND_STROKE` gray, `teamStroke(color)`), plus a `withTheme(options)` helper that merges them. Every Plot chart (HistoryChart, MethodologyChart, Sparkline) uses it.
- D-08 New `ChartFrame.svelte` wraps every full chart: bold headline (Inter 700, ~18–20px), one-line gray dek, the chart slot, and a footer line in mono uppercase micro text: `SOURCE: NFLVERSE · FEEL-GOOD SCORE` plus optional `NOTES: …`. Headline/dek are HTML, not Plot `title`. Applied to HistoryChart, MethodologyChart and the FactorBars breakdown (HTML chart). Sparkline is an inline micro-chart inside board rows: it uses the theme colors but no frame (documented exception).
- D-09 Highlight-one-gray-the-rest: highlighted team in its team color (thicker stroke + direct label at series end, with logo mark where a mark identifies a team); all other teams in neutral gray. Direct labels instead of legends wherever space allows; on narrow (<640px) widths an existing compact legend may remain for mood bands (labels can't fit), documented.
- D-10 Chart marks with logos (LOGO-02 "chart marks"): HistoryChart puts a small team logo (Plot `image` mark, 20–24px) at the highlighted line's last point next to the direct label. MethodologyChart has no teams. Never one logo per data point.

### Area 3: Logos & team identity (LOGO-02, LOGO-03)
- D-11 `TeamLogo.svelte` (props: `franchise`, `primary`, `secondary`, `size` 16|20|24|32|48, `alt`), renders `<img src="/logos/sm/{F}.png" loading="lazy" decoding="async" width height alt>`; on `error` it swaps to the existing `TeamChip`. Logos are nominative identifiers only (never site branding/favicon).
- D-12 Small logo derivatives: the committed 500×500 PNGs (~50 KB each, ~1.6 MB per board) stay untouched for Phase 14 cards. Add `web/public/logos/sm/{F}.png` at 96×96 (2× for ≤48px display) produced once with macOS `sips -Z 96` via a tiny committed script `web/scripts/logos-sm.sh`; commit the 32 outputs. `pipeline/` logo code is not modified.
- D-13 Global off-switch: `VITE_LOGOS=off` (build-time env) makes `TeamLogo` render the chip only — a takedown is a config flip. Default on.
- D-14 Dark-mode legibility: logos sit on a light disc in dark mode (`--logo-disc: #f2f2f2` circle with ~12% padding); in light mode no disc (transparent). Applied inside TeamLogo so every usage is consistent.
- D-15 Placement: board rows (replaces chip), team page header (32–48px), records rows, callout cards, movers strip, recent-games opponent, HistoryChart end mark. The history page team selector stays text.
- D-16 Era names: new pure module `web/src/lib/teamNames.ts` with `eraName(franchise, season, meta)` and `eraAbbr(franchise, season)`: LV ≤2019 → "Oakland Raiders"/OAK; LAC ≤2016 → "San Diego Chargers"/SD; LA ≤2015 → "St. Louis Rams"/STL; WAS ≤2019 → "Washington" (never the former name), 2020–2021 → "Washington Football Team", 2022+ → current meta name. Otherwise the meta name. Current logo always.
- D-17 `isActiveFranchise(franchise, season)`: HOU returns false before 2002; any UI listing teams for a season must not render HOU before 2002 (data already can't produce it; guard + unit test).
- D-18 Name context per surface: board/team page/callouts/movers → the viewed season; records season rows → that season; streaks → the streak's start season (active streaks → current name); recent games → that season; history page selector and the chart → current name (franchise-level). A one-line note on the methodology page: "Relocated teams show their name from that season with the current logo."
- D-19 Unit tests (vitest) for `teamNames.ts` boundary seasons (2015/2016 STL→LA, 2016/2017 SD→LAC, 2019/2020 OAK→LV, WAS 2019/2020/2021/2022, HOU 2001/2002) and for TeamLogo fallback logic where testable as pure functions (e.g. `logoSrc`, `logosEnabled`).

### Area 4: Editorial layout & behavior preservation (DESIGN-03, DESIGN-04)
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
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `web/src/app.css`: token system (spacing, 4 type sizes, light/dark colors, `--mood-0..6`) already used by all components via `var(--token)`; dark mode via `prefers-color-scheme`.
- `TeamChip.svelte` (16/24px gradient chip from team primary/secondary) — the fallback for TeamLogo.
- `meta.teams[F]` has `name`, `nick`, `primary`, `secondary`, `conf`, `division` (current, not era-correct).
- `web/public/logos/{F}.png` 500×500 ×32 + `manifest.json` (Phase 11, LOGO-01); `nohotlink.test.ts` forbids external logo hosts.
- Plot charts: `HistoryChart.svelte` (32 gray lines + highlighted team, band rects, direct end label), `MethodologyChart.svelte`, `Sparkline.svelte`; `FactorBars.svelte` is an HTML bar chart.
- `lib/format.ts` (`moodToken`, `bandIndex`, `formatRecord`), `lib/router.ts` (`teamHash`).

### Established Patterns
- Svelte 5 runes, plain Vite SPA, hash routing; Plot charts rendered in `$effect` with `bind:clientWidth` and `container.replaceChildren(plot)`.
- Components use only tokens; layout overflow solved with `min-width: 0` + ellipsis, never `overflow-x: hidden` on body.
- Pure logic lives in `lib/*.ts` with vitest tests next to it.

### Integration Points
- Team chip usages: BoardRow, CalloutCard, RecentGames, TeamPage header, RecordsPage (2 lists), MoversStrip.
- Season-context names: BoardRow (`team?.name`), TeamPage `name`, RecordsPage `teamName()`, CalloutCard, HistoryPage summary.
- `main.ts` for font imports; `SiteFooter.svelte` for disclaimer (could add "Logos are trademarks of their owners.").
</code_context>

<specifics>
## Specific Ideas

- FiveThirtyEight-INSPIRED data journalism (generic conventions shared by NYT Upshot / Economist): bold head + gray dek, light value gridlines only, no axis lines, direct labels, highlight one team in color, SOURCE/NOTES footer, mono tabular numbers, shaded cells, rule-separated tables.
- Era-name example from the roadmap: "San Diego Chargers" in 2010.
- Footer may gain "Logos are trademarks of their owners." next to the existing disclaimer.
</specifics>

<deferred>
## Deferred Ideas

- Era-specific historical logo art (deferred at v2.0 start).
- Manual light/dark toggle.
- Sortable board columns.
- Source Serif 4 for long-form prose.
- Explore page, EPA scatter, win totals (Phase 13); share cards (Phase 14).
</deferred>

## Post-research resolutions (autonomous, 2026-11-11)
- D-26 Washington copy: add a web-side `eraText(text, franchise, season)` helper in `lib/teamNames.ts`, scoped to WAS only, that rewrites "Commanders" in pipeline-generated blurbs/headlines to "Washington" (≤2019) or "Washington Football Team"/"Football Team" (2020–2021). Other relocated teams' copy uses nicknames that are era-neutral. Pipeline untouched.
- D-27 README (web or project) gains one line crediting Inter and IBM Plex Mono (SIL OFL 1.1).
- D-28 Gridlines: Plot `grid: true` on the value axis plus one CSS rule giving Plot's grid group full opacity in `--grid` color (Plot 0.6.19 hard-codes 10% opacity).

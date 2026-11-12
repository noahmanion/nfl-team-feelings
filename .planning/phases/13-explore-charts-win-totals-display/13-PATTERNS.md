# Phase 13: Explore Charts & Win Totals Display - Pattern Map

**Mapped:** 2026-11-11
**Files analyzed:** 24 (10 new, 14 modified)
**Analogs found:** 23 / 24 (only `ExploreTable.svelte` has no table analog; it borrows row/my-team styles)

All web paths are relative to `web/src/`. Line numbers are from the current tree (HEAD `2b0032a`).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `lib/router.ts` (+`router.test.ts`) | route | request-response (pure parse) | itself: `TEAM` regex + `teamHash` (router.ts 15, 28-34, 47-50) | exact |
| `App.svelte` | provider/route switch | event-driven (hash) | itself: team-route validation (App 80-83, 109-119) + history branch (231-234) | exact |
| `components/SiteHeader.svelte` | component | static | itself: `.item` + `Sep` nav (SiteHeader 17-19) | exact |
| `components/ExplorePage.svelte` | component (page) | request-response (session-cached fetch) | `HistoryPage.svelte` (load effect, dark matchMedia, ChartFrame) + `App.svelte` Scrubber handlers (197-209) | exact |
| `components/EpaScatter.svelte` | component (chart) | transform → render | `HistoryChart.svelte` | exact |
| `components/RecordScatter.svelte` | component (chart) | transform → render | `HistoryChart.svelte` (band rects, band-label gutter, textWidth) | exact |
| `components/ExploreTable.svelte` | component | static render | `RecordsPage.svelte` rows + `.mine` (243-249), `CalloutCards.svelte` `<details>/<summary>` (32-39, 65-75) | partial |
| `lib/explore.ts` (+`explore.test.ts`) | utility (pure) | transform | `lib/epa.ts` + `lib/epa.test.ts` (columnar `file()` builder) | exact |
| `lib/noLuck.test.ts` | test (static grep) | batch | `lib/nohotlink.test.ts` | exact |
| `lib/winTotals.ts` (+`winTotals.test.ts`) | utility (pure) | transform | `lib/format.ts` (`formatRecord`, `plural`) | role-match |
| `components/WinTotals.svelte` | component | static render | `ChartFrame` usage in `TeamPage.svelte` 223-234; legend/swatch CSS in `HistoryChart.svelte` 241-266 | role-match |
| `lib/data.ts` (`loadTeam`, `TeamFile`) | service (loader) | request-response, cached | itself: `loadGames` (data.ts 75-88) | exact |
| `lib/types.ts` | model | — | `EpaFile`/`GamesFile` columnar interfaces (types.ts last lines) | exact |
| `components/ChartFrame.svelte` (+`chartFrame.test.ts`) | component | static | itself (line 21 hard-coded source) | exact |
| `components/TeamPage.svelte` | component (page) | request-response | itself: `loadRecords` effect (95-111), `.columns` grid (222-257, 380-417) | exact |
| `components/RecordsPage.svelte` | component | static (CSS only) | itself (`.records` 171-179, `.rows` 219-226, `.row` 228-239, `.big` 297-318) | exact |
| `components/HistoryChart.svelte` | component | CSS/Plot option only | itself (Plot.plot call 192-210) | exact |
| `lib/format.ts` (+`format.test.ts`) | utility | transform | `formatDelta` (format.ts 30-35), `plural` (38) | exact |
| `components/Delta.svelte` | component | static | itself (line 8) | exact |
| `components/CalloutCards.svelte` / `CalloutCard.svelte` | component | CSS only | `.grid` (CalloutCards 57-61), `.card` / `.actions` (CalloutCard 81-129) | exact |
| `components/BoardRow.svelte` / `MoodBoard.svelte` | component | CSS only | grid template with `72px` last column (BoardRow 245, MoodBoard 140) | exact |
| `pipeline/src/fgs/export.py` | utility (export) | batch / file-I/O | `_vegas_win_totals` (export.py 410-430) + teams loop (392-400) | exact |
| `pipeline/tests/test_export.py` | test | batch | `test_vegas_win_totals_empty_without_frame` / `_real` (671-708) | exact |
| `.planning/phases/13-.../verify_ui.py` | test (e2e) | batch | `.planning/phases/12-redesign-foundation-team-identity/verify_ui.py` | exact |

## Pattern Assignments

### `lib/router.ts` (route, pure parse)

**Analog:** the TEAM route in the same file. Union member to add (lines 3-11):
```ts
  | { kind: 'team'; team: string; season?: number; week?: number }
```
Regex and parse (lines 15, 28-34). Copy the optional season/week tail:
```ts
const TEAM = /^\/team\/([A-Za-z]{2,3})(?:\/(\d{4})(?:\/(\d{1,2}))?)?\/?$/
...
  const tm = TEAM.exec(h)
  if (tm) {
    const team = tm[1].toUpperCase()
    if (!tm[2]) return { kind: 'team', team }
    return tm[3] ? { kind: 'team', team, season: Number(tm[2]), week: Number(tm[3]) } : { kind: 'team', team, season: Number(tm[2]) }
  }
```
Hash builder (lines 47-50). `exploreHash` is the same shape without `team`:
```ts
export const teamHash = (team: string, season?: number, week?: number): string =>
  season === undefined || week === undefined
    ? `#/team/${team.toUpperCase()}`
    : `#/team/${team.toUpperCase()}/${season}/${week}`
```
Put the EXPLORE check before `METHODOLOGY` (line 35). **Tests:** extend `router.test.ts`, which already uses `expect(parseHash(...)).toEqual({...})` blocks (lines 4-30), and import `exploreHash` in its import line (line 2).

---

### `App.svelte` (route switch)

**Validation:** reuse `validTeamWeek` (lines 80-83) and copy the team branch of the redirect `$effect` (lines 109-119):
```ts
    } else if (r.kind === 'team') {
      ...
      notice = null
      if (r.season !== undefined && (r.week === undefined || !validTeamWeek(meta, r.season, r.week))) {
        replace(teamHash(r.team))
      }
```
For explore, set `notice = null`, then `replace('#/explore')` under the same condition. Add `'explore'` to the line 107 group, or make it its own branch.

**Render branch:** copy lines 231-234 (history: page plus loading fallback):
```svelte
    {:else if route.current.kind === 'history' && status === 'ready' && meta && latestFile}
      <HistoryPage {meta} latestRows={latestFile.rows} team={route.current.team} />
    {:else if route.current.kind === 'history'}
      <p class="loading" role="status">Loading…</p>
```
**Header `current`:** extend the nested ternary at lines 214-222 with `route.current.kind === 'explore' ? 'explore'`.

---

### `components/SiteHeader.svelte`

The prop union is on line 6 (`'board' | 'history' | 'team' | 'records' | 'methodology'`); add `'explore'`. Insert this between the history item (17-19) and the records item (20-22):
```svelte
    <span class="item"
      ><Sep /><a href={historyHash()} aria-current={current === 'history' ? 'page' : undefined}>Mood over time</a></span
    >
```
Import `exploreHash` with the other hashes on line 3. No CSS changes.

---

### `components/ExplorePage.svelte` (page, cached fetch)

**Analog:** `HistoryPage.svelte`, plus the Scrubber wiring from `App.svelte`.

Imports (HistoryPage 1-23). Copy the shape: components, then `../lib/data`, `../lib/format`, `myteam`/`myteam.svelte`, `route.svelte` (`go`, `replace`), `router`, types.

Props (HistoryPage 25): `let { meta, latestRows, team }: { meta: Meta; latestRows: Row[]; team?: string } = $props()`. Explore takes `{ meta, latestRows, season?, week? }`.

**Load with `live` guard and retry** (HistoryPage 27-47; TeamPage 43-64 for `loadSeason`):
```ts
  let failed = $state(false)
  let retry = $state(0)
  $effect(() => {
    void retry
    failed = false
    let live = true
    loadHistory(meta).then(
      (h) => { if (live) history = h },
      (err) => { console.error(err); if (live) failed = true },
    )
    return () => { live = false }
  })
```
Use this twice: once for `loadSeason(meta, s)` (skipped when latest), once for `loadEpa(meta, s)` with a separate `epaFailed`/`epaRetry` (the EPA error stays inside its own frame, per UI-SPEC).

**Dark scheme tracking** (HistoryPage 67-75), copied verbatim:
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
**Pin:** `validMyTeam(myTeam.abbr, meta.teams)` (HistoryPage 56). Read it in a `$derived` so pin changes re-render.

**Scrubber handlers** (App 197-209). Swap `boardHash` for `exploreHash`, and write `#/explore` when the result is latest:
```ts
  function onSeasonChange(season: number) {
    const s = findSeason(meta, season)
    if (!s) return
    go(boardHash(season, carryWeek(target.week, findSeason(meta, target.season), s)))
  }
  function onWeekInput(week: number) { replace(boardHash(target.season, week)) }
  const toLatest = () => go('#/')
```
Scrubber props (App 254-264): `{meta} season week isLatest {partial} disabled onSeasonChange onWeekInput onLatest`. Scrubber itself is unchanged.

**HOU filter** (App 178): `currentRows.filter((r) => isActiveFranchise(r.franchise, season))`.

**Error panel** (HistoryPage 129-135, App 273-282):
```svelte
    <StatusPanel variant="error" title="…" body="…"
      actions={[{ label: 'Try again', onClick: () => retry++ }, { label: 'Go to latest', onClick: toLatest }]} />
```
**ChartFrame wrapping** (HistoryPage 138-156): `<ChartFrame id=… level={3} headline=… dek=… notes=…><Chart … {dark} /></ChartFrame>`.

---

### `components/EpaScatter.svelte` and `components/RecordScatter.svelte` (Plot charts)

**Analog:** `HistoryChart.svelte` (whole file). Copy these pieces:

Imports (1-17):
```ts
  import * as Plot from '@observablehq/plot'
  import { moodToken } from '../lib/format'
  import { logoSrc, logosEnabled } from '../lib/logos'
  import { BACKGROUND_STROKE, CHART_FONT_PX, HIGHLIGHT_WIDTH, LABEL_FONT_PX, LOGO_MARK_PX, baseAxis, teamStroke, valueAxis, withTheme } from '../lib/plotTheme'
```
Width binding and container (41-42, 218):
```svelte
  let width = $state(0)
  let container: HTMLDivElement
...
<div class="chart" bind:clientWidth={width} bind:this={container}></div>
```
Font re-measure tick (53-63). RecordScatter needs it for the band-label gutter. Canvas `textWidth` (86-92), copy verbatim into RecordScatter.

**Render effect skeleton** (94-96, 192-215):
```ts
  $effect(() => {
    if (width <= 0) return
    void fontsTick
    ...
    const plot = Plot.plot(withTheme({ width, height: …, marginLeft: 32, marginRight: …, x: baseAxis({...}), y: valueAxis({...}), marks }))
    plot.setAttribute('role', 'img')
    plot.setAttribute('aria-label', `…`)
    container.replaceChildren(plot)
    return () => plot.remove()
  })
```
Add `plot.setAttribute('tabindex', '-1')`, then attach the `pointerdown`/`input`/`click` listeners (RESEARCH Pattern 3, `tapAction` from `lib/explore.ts`) before `replaceChildren`. Read `value` via `(plot as unknown as { value: T | null }).value`.

**Band rects** (RecordScatter; 100-106, 121-128):
```ts
    const bandRects = bands.map((b, i) => ({
      label: b.label,
      fill: `var(--mood-${moodToken(i, bands.length)})`,
      y1: b.min, y2: Math.min(100, b.max + 1), mid: (b.min + Math.min(100, b.max + 1)) / 2,
    }))
    Plot.rect(bandRects, { x1: 0, x2: xMax, y1: 'y1', y2: 'y2', fill: 'fill', fillOpacity: dark ? 0.14 : 0.1 })
```
Band labels in the right gutter (130-143): `Plot.text(bandRects, { x: xMax, y: 'mid', text: 'label', textAnchor: 'start', dx: …, fontSize: CHART_FONT_PX, fill: 'var(--text-muted)', clip: false })`; `bandCol` (line 118).

**Logo plus dark disc** (173-177). Use `src` as a function channel, never a bare string:
```ts
      if (dark) marks.push(Plot.dot(last, { x: 'x', y: 'y', r: logoPx / 2, fill: 'var(--logo-disc)', stroke: 'none' }))
      marks.push(Plot.image(last, { x: 'x', y: 'y', src: () => src, width: dark ? logoPx * 0.76 : logoPx }))
```
For scatters, use `src: (d) => d.src`, disc `r: size/2 + 2`, and separate mark groups (others with `opacity`, then the ring dot, then the pinned group).

**Link mark** (162-171) is the template for tier diagonals: `Plot.link(data, { x1: 'x1', y1: 'y1', x2: 'x2', y2: 'y2', stroke: …, strokeWidth: 1 })`. Add `clip: true` and `stroke: 'var(--grid)'`.

**Dashed reference rule** (145-150): `Plot.ruleX(…, { stroke: 'var(--border)', strokeDasharray: '2,3' })`. For crosshairs and OLS, use `var(--text-muted)` with `'4,3'`.

**Axes** (198-207): `baseAxis({ domain, ticks, tickFormat })`, `valueAxis({ domain: [0, 100], ticks: [0,20,40,60,80,100], tickFormat })`. Explicit `domain` is mandatory (RESEARCH anti-pattern).

**Color** for the ring: compute it in the parent or the chart like HistoryPage 77-82:
```ts
    const bg = getComputedStyle(document.documentElement).getPropertyValue('--bg')
    return highlightColor(teamMeta.primary, teamMeta.secondary, bg, dark)
```
Logo-off fallback: `logosEnabled()` / `logoSrc(F)` null → `Plot.dot` with `fill: teamStroke(primary)` (plotTheme `teamStroke`).

**Chart CSS** (231-240), copied verbatim:
```css
  .chart { font-family: var(--font-mono); inline-size: 100%; min-width: 0; overflow: hidden; }
  .chart :global(svg) { display: block; max-inline-size: 100%; }
```

---

### `components/ExploreTable.svelte` (`<details>` table)

No `<table>` exists in the codebase. Copy:
- `<details>`/`<summary>` markup and CSS from `CalloutCards.svelte` 32-39 and 65-75. Change the summary color from `var(--accent)` to `var(--text)` (UI-SPEC):
```css
  summary { display: flex; align-items: center; min-block-size: var(--tap-min); color: var(--accent); cursor: pointer; }
  summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
```
- Team cell: `TeamLogo` plus link, from RecordsPage 109-113 (`<TeamLogo franchise={…} primary={tm?.primary} secondary={tm?.secondary} size={24} />`; use size 20).
- My-team row tint from BoardRow 123-133 (apply to `tr.mine`):
```css
  .mine .row { background: color-mix(in srgb, var(--accent) 6%, var(--bg)); outline: 2px solid var(--accent); outline-offset: -2px; }
  @media (prefers-color-scheme: dark) { .mine .row { background: color-mix(in srgb, var(--accent) 8%, var(--bg)); } }
```
- `class="visually-hidden"` already exists globally (BoardRow 64, TeamPage 181). Use it for `<caption>`.

---

### `lib/explore.ts` (+`explore.test.ts`)

**Analog:** `lib/epa.ts`, a pure, typed, doc-commented module that imports only `./types`:
```ts
import type { EpaFile } from './types'
/** Season-to-date efficiency for one franchise. Means are play-weighted; null when no plays. */
export interface EpaAgg { off_epa: number | null; … games: number }
export function seasonToDate(f: EpaFile, week: number): Record<string, EpaAgg> {
```
Null-rate handling convention (epa.ts 17-38): skip null rates, never treat them as 0. Apply the same rule in `leagueMeans`. Use the RESEARCH Code Examples (`regOnly`, `fitLine`, `paddedDomain`, `diagonals`, `signed`, `height`, `tapAction`) as written.

**Test builder** (epa.test.ts 1-23). Reuse the tuple-to-columnar `file()` helper for `regOnly`/join tests:
```ts
type R = [number, string, string, number, number, number, number, number, number]
function file(rows: R[]): EpaFile {
  return { season: 2025, note: 'test', game_id: rows.map((r, i) => `g${i}`), week: rows.map((r) => r[0]),
    game_type: rows.map((r) => (r[0] > 18 ? 'WC' : 'REG')), franchise: rows.map((r) => r[1]), … }
}
```
Era names and dek text: `eraName(F, season, meta)`, `eraText(text, F, season)`, `isActiveFranchise` (teamNames.ts 7-40). Don't touch `formatRecord` (format.ts 26-28; it uses a hyphen and is test-pinned). Add an en-dash `recordText`.

---

### `lib/noLuck.test.ts`

**Analog:** `lib/nohotlink.test.ts` (whole file, 35 lines):
```ts
const sources = import.meta.glob(['../**/*.{ts,svelte}', '!./nohotlink.test.ts'], { query: '?raw', import: 'default', eager: true }) as Record<string, string>
// Built from parts so this file never matches itself.
const hosts = ['espn' + 'cdn', 'wiki' + 'pedia'].join('|')
...
  it('scans the app sources and index.html', () => { expect(Object.keys(sources).length).toBeGreaterThan(10) })
  it('has no external logo URL anywhere', () => {
    const offenders = Object.entries({ ...sources, ...html }).filter(([, src]) => EXTERNAL_LOGO.test(src)).map(([path]) => path)
    expect(offenders).toEqual([])
  })
  it('the pattern would catch a hotlink', () => { … })
```
Narrow the glob to `../components/{ExplorePage,EpaScatter,RecordScatter,ExploreTable}.svelte` + `./explore.ts`, assert at least 5 files found, and build the regex as `new RegExp(['lu','ck'].join(''), 'i')`. Never include `types.ts` (`contribs.luck`).

---

### `lib/winTotals.ts` (+`winTotals.test.ts`)

**Analog:** `lib/format.ts`, pure string helpers with a `plural` helper (line 38):
```ts
const isNum = (n: unknown): n is number => typeof n === 'number' && Number.isFinite(n)
const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`
```
`changeText` (format.ts 46-55) is the model for multi-branch copy selection (week-0 vs in-season vs finished). Use the `pace`, `finished`, `lineTicks` bodies from RESEARCH Code Examples. Tests follow the `format.test.ts` describe/it style.

---

### `components/WinTotals.svelte`

- Wrapper: `ChartFrame` with `id="expect-heading" level={3} headline="Preseason expectations" dek=… notes=… source=…`, the same as TeamPage 224-233.
- Legend list CSS: start from HistoryChart `.legend`/`.swatch` (241-266: `list-style: none; margin: 0; padding: 0`, flex items, `flex: none` swatch). Switch to the UI-SPEC grid `16px | minmax(0,1fr) | auto` with row rules.
- Number formatting: `.num` mono tabular (TeamPage 198 `<span class="num">`).
- Pace dot color: `highlightColor(primary, secondary, bg, dark)` as in HistoryPage 77-82 (needs the dark matchMedia effect from HistoryPage 67-75).
- Plain HTML only, no Plot.

---

### `lib/data.ts` (`loadTeam`) and `lib/types.ts` (`TeamFile`)

**Analog:** `loadGames` (data.ts 75-88). Copy it verbatim and swap the path to `teams/${F}.json`:
```ts
const gamesCache = new Map<string, Promise<GamesFile>>()
export function loadGames(meta: Meta, season: number): Promise<GamesFile> {
  const key = `${meta.generated_at}|${season}`
  const cached = gamesCache.get(key)
  if (cached) return cached
  const p = getJson<GamesFile>(`games/${season}.json?v=${encodeURIComponent(meta.generated_at)}`)
  gamesCache.set(key, p)
  p.catch(() => { if (gamesCache.get(key) === p) gamesCache.delete(key) })
  return p
}
```
Add `TeamFile` to the import on line 1. In `types.ts`, follow the columnar style of `GamesFile`/`EpaFile` (one-line doc comment that names the producer). The fields mirror export.py 392-400: `franchise`, `...TeamMeta`, `history{season,week,score,elo,label}`, `vegas_win_totals{season,line,over_odds,under_odds,line_type,source,used_in_score}`, `expectation{season,exp_total,source,reg_games}`.

---

### `components/ChartFrame.svelte` (+`chartFrame.test.ts`)

Props line 13. Add `source?: string`:
```ts
  }: { headline: string; dek?: string; notes?: string; level?: 2 | 3; id: string; children: Snippet } = $props()
```
Line 21 becomes `{source ?? 'SOURCE: NFLVERSE · FEEL-GOOD SCORE'}` (or a default in destructuring). **Test:** copy the SSR case at chartFrame.test.ts 25-31:
```ts
    const { body } = render(ChartFrame, { props: { id: 'cf2', headline: 'H', children } })
    expect(body).toContain('SOURCE: NFLVERSE · FEEL-GOOD SCORE')
```
Add a case with `source: 'SOURCE: NFLVERSE (2003–2020) · COVERS / DRAFTKINGS (2021+)'`.

---

### `components/TeamPage.svelte` (insert WinTotals)

**Fetch:** copy the `loadRecords` effect (95-111). It is failure-tolerant and keyed by team, which matches "omit section on failure":
```ts
  let streak = $state<{ team: string; active: ActiveStreak | null; asOf: string | null } | null>(null)
  $effect(() => {
    const t = team
    let live = true
    loadRecords(meta).then(
      (r) => { if (live) streak = { team: t, … } },
      (err) => { console.error(err); if (live) streak = { team: t, active: null, asOf: null } },
    )
    return () => { live = false }
  })
```
Use `loadTeam(meta, team)` → `teamFile = { team: t, file }` or `{ team: t, file: null }`.

**Placement (D-21):** today `.columns` (222-257) holds two sibling `section.block`s (Why, games). Wrap the WinTotals section and the existing games section in `<div class="right">` so the 1024px grid (411-417) keeps two columns. `.block` (386-394) supplies the rule, padding and margin. In `.right`, the first `.block` keeps its top rule.

**Record source:** `row.wins/losses/ties` with the `ok()` guard (134-137).

---

### Phase 12 leftovers

**`RecordsPage.svelte` (D-22):** remove `max-width: 680px` (line 172). `.rows` (219-226) becomes `display: grid; grid-template-columns: 28px minmax(0, 1fr) max-content`. `li` and `.row` (228-239, currently `grid-template-columns: 28px minmax(0, 1fr) auto`) become `grid-column: 1 / -1; grid-template-columns: subgrid`. `.big` (297-318) already has `min-inline-size: var(--score-cell)`. `.dek` (190-193) and `.footnote` (326-330) already cap at `--prose-max`.

**`HistoryChart.svelte` (D-23):** in the `Plot.plot(withTheme({...}))` call (192-197), add `marginTop: drawLogo ? 24 : undefined` (`drawLogo` is defined on line 115).

**`lib/format.ts` + `Delta.svelte` (D-24):** copy `formatDelta`'s shape (30-35) into `formatRankDelta` returning `{ text, dir, aria }`. Reuse `plural` (38) for `spot`/`spots`. Delta line 8 currently reads:
```svelte
<span class="delta {d.dir}">{kind === 'rank' ? '#' : ''}{d.text}</span>
```
→ for `kind === 'rank'`, use `formatRankDelta`, drop `#`, and add `aria-label={aria}`. **Pitfall 7:** widen the last grid column `72px` → `88px` in both `BoardRow.svelte` line 245 and `MoodBoard.svelte` line 140 (identical templates).

**`CalloutCards.svelte` / `CalloutCard.svelte` (D-25):** `.grid` (CalloutCards 57-61) gets `align-items: stretch`. Cards render directly as grid children (lines 27-29, no `li`), so `.card` (CalloutCard 81-91) is already `display: flex; flex-direction: column` and `.actions` (123-129) already has `margin-top: auto`. The likely gap is the card's root element not stretching to the row height. Ensure the CalloutCard root is the grid item with `block-size: 100%` / no `align-self`. Verify at 1280.

---

### `pipeline/src/fgs/export.py` (D-17)

**Analog:** `_vegas_win_totals` (lines 410-430), a constant `*_KEYS` tuple plus a columnar helper with stable empty shape:
```python
VEGAS_WIN_TOTAL_KEYS = ("season", "line", "over_odds", "under_odds", "line_type", "source", "used_in_score")

def _vegas_win_totals(win_totals: pl.DataFrame | None, fid: str) -> dict[str, list]:
    """Columnar … Empty lists (same keys) when no frame is given, so the team-file shape is stable."""
    if win_totals is None:
        return {k: [] for k in VEGAS_WIN_TOTAL_KEYS}
    part = win_totals.filter(pl.col("franchise_id") == fid).sort("season")
```
**Insertion point:** the team-file dict at lines 392-400. Add `"expectation": _expectation(scored, fid),` after `"vegas_win_totals": …`. `scored` is in scope (line 312). `season_config` is already imported (line 17). `EXPECTED_GAME_EXCEPTIONS` and `reg_games` are in `season_config.py` lines 59 and 66; read them, don't edit them (the file is fingerprinted). Use the `_expectation` body from RESEARCH as written. Place the helper and `EXPECTATION_KEYS` right after `_vegas_win_totals`.

### `pipeline/tests/test_export.py`

**Analog:** the Phase 11 block (lines 667-708). Add a `# --- Phase 13: display-only expectation (DATA-03, D-17) ---` block after it.
- Synthetic (copy 671-677): `files, _ = _draft_export(monkeypatch, {**LIVE_CFG, "weight": 0.0, "display_only": True})`, then assert every `teams/*` has `expectation` with `EXPECTATION_KEYS` and `exp_total` all None.
- Real (copy 680-690 structure): loop `for fid in sorted(CANONICAL)`, check equal column lengths, `season == sorted(season)`, vegas iff 2003–2020, `reg_games` 16/17 with BUF/CIN 2022 = 16, and `json.dumps(v, allow_nan=False)`. The `real_files` fixture (76-83) returns `(derived, files)`.

### `.planning/phases/13-.../verify_ui.py`

Copy `.planning/phases/12-redesign-foundation-team-identity/verify_ui.py`: the `check()` (lines 27-30), `go()` with the `?r=1` reload (39-43), and `new_context(browser, width, scheme, **kw)` (46-50) helpers. For the touch-arming test, pass `has_touch=True` via `**kw`. `META` path resolution at line 17 (`HERE.parents[2] / "web" / …`) works unchanged.

## Shared Patterns

### Async load with stale guard
**Source:** `HistoryPage.svelte` 31-47, `TeamPage.svelte` 47-64 and 95-111
**Apply to:** ExplorePage (season + EPA), TeamPage (`loadTeam`)
`let live = true` in the effect; the `then`/`reject` handlers check `live`; the cleanup sets `live = false`; `void retry` for "Try again".

### Session cache keyed by `generated_at`, evicted on failure
**Source:** `lib/data.ts` 75-103
**Apply to:** `loadTeam`

### Dark-scheme reactivity and team highlight color
**Source:** `HistoryPage.svelte` 67-82; `lib/history.ts` `highlightColor` (line 143)
**Apply to:** ExplorePage → both scatters (pass `dark`), WinTotals pace dot

### Plot render lifecycle
**Source:** `HistoryChart.svelte` 41-42, 94-96, 192-215, 218, 231-240
**Apply to:** EpaScatter, RecordScatter
`bind:clientWidth` → `$effect` reads every reactive dep → `Plot.plot(withTheme(...))` → set role/aria → `container.replaceChildren(plot)` → `return () => plot.remove()`.

### Theme helpers
**Source:** `lib/plotTheme.ts` (`withTheme`, `valueAxis`, `baseAxis`, `teamStroke`, `CHART_FONT_PX`=12, `LABEL_FONT_PX`=14)
**Apply to:** both scatters. Never hand-set grid opacity (app.css fixes Plot's hard-coded 0.1).

### Pinned team
**Source:** `HistoryPage.svelte` 56 (`validMyTeam(myTeam.abbr, meta.teams)`), `RecordsPage.svelte` 65
**Apply to:** ExplorePage (charts + table row tint)

### Era identity and HOU filter
**Source:** `lib/teamNames.ts` 7-40, `App.svelte` 178
**Apply to:** explore.ts (dek, tooltips), ExploreTable, ExplorePage rows

### Rule-topped sections
**Source:** `TeamPage.svelte` `.block` 386-394, `RecordsPage.svelte` `section` 206-213
**Apply to:** ExplorePage second section, WinTotals section

### Static source-grep tests
**Source:** `lib/nohotlink.test.ts`, `lib/brand.test.ts` 15-30 (`import.meta.glob(..., {query:'?raw', import:'default', eager:true})`, regex built from parts)
**Apply to:** `noLuck.test.ts`

### SSR component tests
**Source:** `lib/chartFrame.test.ts` 1-7 (`render` from `svelte/server`, `createRawSnippet` children)
**Apply to:** ChartFrame `source` prop test; optional WinTotals/ExploreTable smoke tests

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `components/ExploreTable.svelte` (the `<table>` itself) | component | static | No `<table>` anywhere in `web/src`. Use the UI-SPEC "Table View Contract" for thead/td styles; the `<details>`, team cell and `.mine` styles come from the analogs above. |
| Plot `pointer`/`tip`/`plot.value` click wiring | — | event-driven | No existing chart uses `tip`, `pointer` or `input`. Use RESEARCH Pattern 3 and the "Plot 0.6.19 facts" table. |

## Metadata

**Analog search scope:** `web/src/{App.svelte,components/,lib/}`, `pipeline/src/fgs/export.py`, `pipeline/src/fgs/season_config.py`, `pipeline/tests/test_export.py`, `.planning/phases/12-redesign-foundation-team-identity/verify_ui.py`
**Files scanned:** ~30
**Pattern extraction date:** 2026-11-11

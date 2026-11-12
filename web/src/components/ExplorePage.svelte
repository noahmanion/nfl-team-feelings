<script lang="ts">
  import ChartFrame from './ChartFrame.svelte'
  import EpaScatter from './EpaScatter.svelte'
  import ExploreTable, { type ExploreColumn, type ExploreRow } from './ExploreTable.svelte'
  import RecordScatter from './RecordScatter.svelte'
  import Scrubber from './Scrubber.svelte'
  import StatusPanel from './StatusPanel.svelte'
  import { findSeason, isLatest, loadEpa, loadSeason } from '../lib/data'
  import { seasonToDate } from '../lib/epa'
  import {
    chartHeight,
    emptyCopy,
    epaEmpty,
    epaPoints,
    fitLine,
    gapText,
    leagueMeans,
    pct,
    recordDek,
    recordPoints,
    recordText,
    regOnly,
    signed,
    withGaps,
    type EpaPoint,
    type RecordPoint,
  } from '../lib/explore'
  import { carryWeek, weekLabel } from '../lib/format'
  import { validMyTeam } from '../lib/myteam'
  import { myTeam } from '../lib/myteam.svelte'
  import { go, replace } from '../lib/route.svelte'
  import { exploreHash, teamHash } from '../lib/router'
  import { isActiveFranchise } from '../lib/teamNames'
  import type { EpaFile, Meta, Row, SeasonFile } from '../lib/types'

  // Explore page (EXPL-02, EXPL-03): one Scrubber drives both scatters (D-03).
  let { meta, latestRows, season, week }: { meta: Meta; latestRows: Row[]; season?: number; week?: number } = $props()

  // ---- target week: the explicit season/week when valid, else the latest week ----
  function validWeek(sv: number | undefined, wv: number | undefined): boolean {
    if (sv === undefined || wv === undefined) return false
    const sm = findSeason(meta, sv)
    return !!sm && wv >= 0 && wv <= sm.max_week
  }
  const explicit = $derived(validWeek(season, week))
  const s = $derived(explicit ? season! : meta.latest.season)
  const w = $derived(explicit ? week! : meta.latest.week)
  const latest = $derived(isLatest(meta, s, w))
  const seasonMeta = $derived(findSeason(meta, s)!)
  const wl = $derived(seasonMeta ? weekLabel(w, seasonMeta) : `Week ${w}`)
  const partial = $derived(!!meta.partial_week)

  // ---- snapshot rows: latest.json for the latest week, else the season file ----
  let seasonFile = $state<SeasonFile | null>(null)
  let snapFailed = $state(false)
  let retry = $state(0)

  $effect(() => {
    void retry
    if (latest) return
    const want = s
    snapFailed = false
    let live = true
    loadSeason(meta, want).then(
      (f) => {
        if (live) seasonFile = f
      },
      (err) => {
        console.error(err)
        if (live) snapFailed = true
      },
    )
    return () => {
      live = false
    }
  })

  const rows = $derived.by((): Row[] | undefined => {
    const src = latest ? latestRows : seasonFile?.season === s ? (seasonFile.weeks[String(w)] ?? []) : undefined
    return src?.filter((r) => isActiveFranchise(r.franchise, s))
  })
  const gamesPlayed = $derived(rows ? rows.reduce((n, r) => n + r.wins + r.losses + r.ties, 0) : 0)

  // ---- EPA file: only for seasons with play-by-play; its failure only hits the EPA frame ----
  const hasEpa = $derived(!!meta.epa_seasons?.includes(s))
  const firstEpaSeason = $derived(meta.epa_seasons?.length ? Math.min(...meta.epa_seasons) : s)
  let epaFile = $state<EpaFile | null>(null)
  let epaFailed = $state(false)
  let epaRetry = $state(0)

  $effect(() => {
    void epaRetry
    if (!hasEpa) return
    const want = s
    epaFailed = false
    let live = true
    loadEpa(meta, want).then(
      (f) => {
        if (live) epaFile = f
      },
      (err) => {
        console.error(err)
        if (live) epaFailed = true
      },
    )
    return () => {
      live = false
    }
  })

  const epaFileNow = $derived(epaFile?.season === s ? epaFile : null)
  const agg = $derived(epaFileNow ? seasonToDate(regOnly(epaFileNow), w) : null)
  const epaPts = $derived(rows && agg ? epaPoints(rows, agg, s, meta) : [])
  // League means over the plotted teams only.
  const means = $derived.by(() => {
    const m = agg ? leagueMeans(epaPts.map((p) => agg[p.franchise])) : { off: null, def: null }
    return { off: m.off ?? 0, def: m.def ?? 0 }
  })
  // Empty checks that don't need the EPA file come first (week 0, no pbp for the season).
  const epaKind = $derived(
    epaEmpty({ season: s, week: w, gamesPlayed, epaSeasons: meta.epa_seasons, nPoints: epaFileNow ? epaPts.length : 1 }),
  )

  // ---- record vs evidence ----
  const recBase = $derived(rows ? recordPoints(rows, s, meta) : [])
  const line = $derived(fitLine(recBase))
  const recPts = $derived(withGaps(recBase, line))

  // ---- pin, theme, size ----
  const pinned = $derived(validMyTeam(myTeam.abbr, meta.teams))
  let dark = $state(false)
  $effect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    dark = mq.matches
    const onChange = () => (dark = mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  })
  let width = $state(0)
  const placeholderHeight = $derived(chartHeight(width || 343))

  // ---- copy ----
  const EPA_HEADLINE = 'How efficiently every team plays'
  const RVE_HEADLINE = 'Record vs evidence'
  const epaDek = $derived(
    `Offense against defense in expected points added per play, ${s} through ${wl}. Efficiency is one input to the feel-good score, not the score itself.` +
      (w >= 1 && w <= 3 ? ' Early-season efficiency is noisy: a single game can move a team a long way.' : ''),
  )
  const EPA_NOTES =
    'EPA per play, season to date, garbage time filtered. Not adjusted for opponents. Defense axis is flipped: higher = fewer points allowed. Regular season only.'
  const RVE_NOTES =
    'Win % counts ties as half a win. The dashed line is the typical score for each record this week. Shaded bands are the board’s mood bands.'
  const rveDek = $derived(recordDek(recPts, line, s, wl, meta))
  const epaAria = $derived(
    `Scatter of offensive against defensive EPA per play for ${epaPts.length} teams, ${s} through ${wl}. Full values in the table below.`,
  )
  const rveAria = $derived(
    `Scatter of win percentage against feel-good score for ${recPts.length} teams, ${s} through ${wl}. Full values in the table below.`,
  )

  // ---- tables (D-16a): links go where the marks go ----
  const href = (f: string) => (latest ? teamHash(f) : teamHash(f, s, w))
  const EPA_COLUMNS: ExploreColumn[] = [
    { key: 'off', label: 'Off EPA', numeric: true },
    { key: 'def', label: 'Def EPA', numeric: true },
    { key: 'net', label: 'Net', numeric: true },
    { key: 'record', label: 'Record', numeric: true, wideOnly: true },
  ]
  const RVE_COLUMNS: ExploreColumn[] = [
    { key: 'record', label: 'Record', numeric: true },
    { key: 'winpct', label: 'Win %', numeric: true, wideOnly: true },
    { key: 'score', label: 'Score', numeric: true },
    { key: 'gap', label: 'Gap', numeric: true },
  ]
  const base = (p: EpaPoint | RecordPoint) => ({
    franchise: p.franchise,
    abbr: p.abbr,
    name: p.name,
    href: href(p.franchise),
    mine: p.franchise === pinned,
  })
  const epaRows = $derived(
    [...epaPts]
      .sort((a, b) => b.net - a.net)
      .map(
        (p): ExploreRow => ({
          ...base(p),
          cells: {
            off: { text: signed(p.off, 3) },
            def: { text: signed(p.def, 3) },
            net: { text: signed(p.net, 3) },
            record: { text: recordText(p.wins, p.losses, p.ties) },
          },
        }),
      ),
  )
  const rveRows = $derived(
    [...recPts]
      .sort((a, b) => b.y - a.y)
      .map(
        (p): ExploreRow => ({
          ...base(p),
          cells: {
            record: { text: recordText(p.wins, p.losses, p.ties) },
            winpct: { text: pct(p.x, 1) },
            score: { text: String(p.y) },
            gap:
              p.gap == null
                ? { text: '–', tone: 'muted' }
                : { text: gapText(p.gap), tone: Math.abs(p.gap) < 0.5 ? 'muted' : p.gap > 0 ? 'up' : 'down' },
          },
        }),
      ),
  )

  // ---- scrubber: the latest week always writes #/explore ----
  const hashFor = (sv: number, wv: number) => (isLatest(meta, sv, wv) ? '#/explore' : exploreHash(sv, wv))
  function onSeasonChange(next: number) {
    const to = findSeason(meta, next)
    if (!to) return
    go(hashFor(next, carryWeek(w, findSeason(meta, s), to)))
  }
  const onWeekInput = (next: number) => replace(hashFor(s, next))
  const toLatest = () => go('#/explore')
</script>

<article class="explore" aria-labelledby="explore-heading" bind:clientWidth={width}>
  <header class="page-head">
    <h2 id="explore-heading">Explore</h2>
    <p class="dek">
      Two ways to check the board: how efficiently teams play, and how their record compares with the evidence.
    </p>
  </header>

  <div class="scrub">
    <Scrubber
      {meta}
      season={s}
      week={w}
      isLatest={latest}
      {partial}
      {onSeasonChange}
      {onWeekInput}
      onLatest={toLatest}
    />
  </div>

  {#snippet loading()}
    <div class="chart-loading" style:min-height="{placeholderHeight}px" role="status">Loading {s} {wl}…</div>
  {/snippet}

  {#if snapFailed && !latest}
    <div class="error">
      <StatusPanel
        variant="error"
        title="Couldn’t load this week"
        body={`The data for ${s} ${wl} didn’t load. Try again, or jump to the latest week.`}
        actions={[
          { label: 'Try again', onClick: () => retry++ },
          { label: 'Go to latest', onClick: toLatest },
        ]}
      />
    </div>
  {:else}
    <section class="block first" aria-labelledby="epa-heading">
      {#if !rows}
        <ChartFrame id="epa-heading" level={3} headline={EPA_HEADLINE} footer={false}>{@render loading()}</ChartFrame>
      {:else if epaKind}
        <ChartFrame id="epa-heading" level={3} headline={EPA_HEADLINE} notes={EPA_NOTES}>
          <p class="chart-empty">{emptyCopy(epaKind, s, wl, firstEpaSeason)}</p>
        </ChartFrame>
      {:else if epaFailed}
        <ChartFrame id="epa-heading" level={3} headline={EPA_HEADLINE} notes={EPA_NOTES}>
          <StatusPanel
            variant="error"
            title="Couldn’t load efficiency data"
            body={`The play-by-play numbers for ${s} didn’t load.`}
            actions={[{ label: 'Try again', onClick: () => epaRetry++ }]}
          />
        </ChartFrame>
      {:else if !epaFileNow}
        <ChartFrame id="epa-heading" level={3} headline={EPA_HEADLINE} footer={false}>{@render loading()}</ChartFrame>
      {:else}
        <ChartFrame id="epa-heading" level={3} headline={EPA_HEADLINE} dek={epaDek} notes={EPA_NOTES}>
          <EpaScatter
            points={epaPts}
            {means}
            season={s}
            week={w}
            {latest}
            {pinned}
            {dark}
            {meta}
            ariaLabel={epaAria}
          />
        </ChartFrame>
        <ExploreTable caption={EPA_HEADLINE} columns={EPA_COLUMNS} rows={epaRows} {meta} />
      {/if}
    </section>

    <section class="block" aria-labelledby="rve-heading">
      {#if !rows}
        <ChartFrame id="rve-heading" level={3} headline={RVE_HEADLINE} footer={false}>{@render loading()}</ChartFrame>
      {:else if recPts.length === 0}
        <ChartFrame id="rve-heading" level={3} headline={RVE_HEADLINE} notes={RVE_NOTES}>
          <p class="chart-empty">{emptyCopy('no-games', s, wl, firstEpaSeason)}</p>
        </ChartFrame>
      {:else}
        <ChartFrame id="rve-heading" level={3} headline={RVE_HEADLINE} dek={rveDek} notes={RVE_NOTES}>
          <RecordScatter
            points={recPts}
            {line}
            bands={meta.bands}
            season={s}
            week={w}
            {latest}
            {pinned}
            {dark}
            {meta}
            ariaLabel={rveAria}
          />
        </ChartFrame>
        <ExploreTable caption={RVE_HEADLINE} columns={RVE_COLUMNS} rows={rveRows} {meta} />
      {/if}
    </section>
  {/if}
</article>

<style>
  .explore {
    min-width: 0;
  }
  h2 {
    font-size: var(--text-heading);
    line-height: var(--lh-heading);
    font-weight: var(--weight-bold);
  }
  .dek {
    margin-top: var(--space-xs);
    max-width: var(--prose-max);
    color: var(--text-muted);
  }
  .scrub {
    margin-top: var(--space-md);
  }
  .error {
    margin-top: var(--space-lg);
  }
  .block {
    min-width: 0;
    margin-top: var(--space-xl);
    padding-top: var(--space-md);
    border-top: 1px solid var(--border);
  }
  .block.first {
    margin-top: var(--space-lg);
    padding-top: 0;
    border-top: none;
  }
  .chart-loading,
  .chart-empty {
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0;
    padding: var(--space-md);
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    color: var(--text-muted);
    text-align: center;
  }
  .chart-empty {
    min-height: 160px;
  }
</style>

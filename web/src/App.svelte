<script lang="ts">
  import { onMount } from 'svelte'
  import BoardHeading from './components/BoardHeading.svelte'
  import MoodBoard from './components/MoodBoard.svelte'
  import Scrubber from './components/Scrubber.svelte'
  import SiteFooter from './components/SiteFooter.svelte'
  import SiteHeader from './components/SiteHeader.svelte'
  import StatusPanel from './components/StatusPanel.svelte'
  import { findSeason, isLatest as isLatestWeek, loadLatest, loadMeta, loadSeason } from './lib/data'
  import { carryWeek } from './lib/format'
  import { go, replace, route } from './lib/route.svelte'
  import { boardHash, type Route } from './lib/router'
  import type { Meta, Row, SeasonFile, WeekFile } from './lib/types'

  let meta = $state<Meta | null>(null)
  let latestFile = $state<WeekFile | null>(null)
  let status = $state<'loading' | 'ready' | 'error'>('loading')

  // Initial load: meta + latest in parallel. "Try again" on the fatal panel re-runs this.
  async function boot() {
    status = 'loading'
    try {
      const [m, latest] = await Promise.all([loadMeta(), loadLatest()])
      meta = m
      latestFile = latest
      status = 'ready'
    } catch (err) {
      console.error(err)
      meta = null
      latestFile = null
      status = 'error'
    }
  }

  onMount(boot)

  // ---- route -> view (route.current is the single source of truth, D-11) ----

  type Target = { season: number; week: number; latest: boolean }

  function validBoard(m: Meta, r: Route): r is Extract<Route, { kind: 'board' }> {
    if (r.kind !== 'board') return false
    const s = findSeason(m, r.season)
    return !!s && r.week >= 0 && r.week <= s.max_week
  }

  const target = $derived.by((): Target | null => {
    if (!meta) return null
    const r = route.current
    if (validBoard(meta, r) && !isLatestWeek(meta, r.season, r.week)) {
      return { season: r.season, week: r.week, latest: false }
    }
    // latest, a board route equal to meta.latest, or anything we redirect to #/
    return { season: meta.latest.season, week: meta.latest.week, latest: true }
  })

  let notice = $state(false)

  // Bad or reserved links fall back to #/; bad ones also get a dismissible notice.
  $effect(() => {
    if (!meta) return
    const r = route.current
    if (r.kind === 'reserved') {
      replace('#/')
    } else if (r.kind === 'invalid' || (r.kind === 'board' && !validBoard(meta, r))) {
      replace('#/')
      notice = true
    } else if (r.kind === 'board' && !isLatestWeek(meta, r.season, r.week)) {
      notice = false
    }
  })

  // ---- season files: session-cached, stale responses ignored ----

  let seasonFile = $state<SeasonFile | null>(null)
  let seasonError = $state<number | null>(null)
  let retry = $state(0)
  let requestedSeason: number | null = null

  $effect(() => {
    void retry
    // Record the wanted season before any early return, so an older in-flight fetch
    // (e.g. A -> B -> back to A) can't land after the user has moved on.
    requestedSeason = !meta || !target || target.latest ? null : target.season
    if (!meta || requestedSeason === null) return
    const s = requestedSeason
    if (seasonFile?.season === s) return
    seasonError = null
    loadSeason(meta, s).then(
      (file) => {
        if (requestedSeason === s) seasonFile = file
      },
      (err) => {
        console.error(err)
        if (requestedSeason === s) seasonError = s
      },
    )
  })

  const currentRows = $derived.by((): Row[] | undefined => {
    if (!target) return undefined
    if (target.latest) return latestFile?.rows
    if (seasonFile?.season === target.season) return seasonFile.weeks[String(target.week)] ?? []
    return undefined
  })

  // Keep the previous board visible (dimmed) while a season file loads.
  let shown = $state<{ rows: Row[]; week: number } | null>(null)
  $effect(() => {
    if (currentRows && target) shown = { rows: currentRows, week: target.week }
  })

  const seasonFailed = $derived(!!target && !target.latest && seasonError === target.season)
  const pending = $derived(!!target && !target.latest && currentRows === undefined && !seasonFailed)
  const seasonMeta = $derived(meta && target ? findSeason(meta, target.season) : undefined)
  const partial = $derived(!!meta?.partial_week)

  // ---- scrubber handlers ----

  function onSeasonChange(season: number) {
    if (!meta || !target) return
    const s = findSeason(meta, season)
    if (!s) return
    go(boardHash(season, carryWeek(target.week, findSeason(meta, target.season), s)))
  }

  function onWeekInput(week: number) {
    if (!target) return
    replace(boardHash(target.season, week))
  }

  const toLatest = () => go('#/')
</script>

<div class="page">
  <SiteHeader />

  <main>
    {#if status === 'error'}
      <StatusPanel variant="error" fatal title="Couldn’t load the mood board" actions={[{ label: 'Try again', onClick: boot }]}>
        The data files are missing or unreadable. If you’re running this locally, run <code>uv run fgs refresh</code>
        in <code>pipeline/</code>, then try again.
      </StatusPanel>
    {:else}
      <Scrubber
        {meta}
        season={target?.season ?? 0}
        week={target?.week ?? 0}
        isLatest={!!target?.latest}
        {partial}
        disabled={status !== 'ready'}
        {onSeasonChange}
        {onWeekInput}
        onLatest={toLatest}
      />
      {#if status === 'ready' && meta && target && seasonMeta}
        {#if notice}
          <StatusPanel
            variant="notice"
            body="We don’t have a board for that week, so here’s the latest one."
            onDismiss={() => (notice = false)}
          />
        {/if}
        {#if seasonFailed}
          <StatusPanel
            variant="error"
            title="Couldn’t load the {target.season} season"
            body="That season’s data didn’t load. Try again, or jump back to the latest week."
            actions={[
              { label: 'Try again', onClick: () => retry++ },
              { label: 'Go to latest', onClick: toLatest },
            ]}
          />
        {:else if shown}
          <BoardHeading
            season={seasonMeta}
            week={target.week}
            count={shown.rows.length}
            {partial}
            isLatest={target.latest}
            scoreKind={meta.score_kind}
          />
          <MoodBoard rows={shown.rows} {meta} week={shown.week} busy={pending} />
        {:else}
          <MoodBoard loading />
        {/if}
      {:else}
        <MoodBoard loading />
      {/if}
    {/if}
  </main>

  {#if status === 'ready' && meta}
    <SiteFooter {meta} />
  {/if}
</div>

<style>
  .page {
    max-width: 640px;
    margin: 0 auto;
    padding: var(--space-lg) var(--space-md) var(--space-xl);
  }
  main {
    margin-top: var(--space-lg);
  }
  @media (min-width: 1024px) {
    .page {
      max-width: calc(var(--content-max) + 2 * var(--space-lg));
      padding: var(--space-2xl) var(--space-lg) var(--space-3xl);
    }
  }
</style>

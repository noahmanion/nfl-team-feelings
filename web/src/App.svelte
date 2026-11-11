<script lang="ts">
  import { onMount } from 'svelte'
  import BoardHeading from './components/BoardHeading.svelte'
  import MoodBoard from './components/MoodBoard.svelte'
  import Scrubber from './components/Scrubber.svelte'
  import SiteFooter from './components/SiteFooter.svelte'
  import SiteHeader from './components/SiteHeader.svelte'
  import StatusPanel from './components/StatusPanel.svelte'
  import { findSeason, isLatest as isLatestWeek, loadLatest, loadMeta, loadSeason } from './lib/data'
  import { go, replace, route } from './lib/route.svelte'
  import { boardHash, type Route } from './lib/router'
  import type { Meta, Row, SeasonFile, WeekFile } from './lib/types'

  let meta = $state<Meta | null>(null)
  let latestFile = $state<WeekFile | null>(null)
  let failed = $state(false)

  async function boot() {
    failed = false
    try {
      const [m, latest] = await Promise.all([loadMeta(), loadLatest()])
      meta = m
      latestFile = latest
    } catch (err) {
      console.error(err)
      failed = true
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
    if (!meta || !target || target.latest) return
    const s = target.season
    if (seasonFile?.season === s) return
    requestedSeason = s
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
    go(boardHash(season, Math.min(target.week, s.max_week)))
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
    {#if failed}
      <section class="panel" role="alert">
        <h2>Couldn’t load the mood board</h2>
        <p>
          The data files are missing or unreadable. If you’re running this locally, run <code>uv run fgs refresh</code>
          in <code>pipeline/</code>, then try again.
        </p>
        <button type="button" onclick={boot}>Try again</button>
      </section>
    {:else}
      <Scrubber
        {meta}
        season={target?.season ?? 0}
        week={target?.week ?? 0}
        isLatest={!!target?.latest}
        {partial}
        disabled={!meta}
        {onSeasonChange}
        {onWeekInput}
        onLatest={toLatest}
      />
      {#if meta && target && seasonMeta}
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
          {#if !pending && currentRows && currentRows.length === 0}
            <StatusPanel
              variant="empty"
              title="No moods to report"
              body="We don’t have any teams for this week. Jump to the latest week to see the current board."
              actions={[{ label: 'Go to latest', onClick: toLatest }]}
            />
          {:else}
            <div class="board-wrap" class:pending aria-busy={pending}>
              <MoodBoard rows={shown.rows} teams={meta.teams} bands={meta.bands} week={shown.week} />
            </div>
          {/if}
        {/if}
      {:else}
        <p class="visually-hidden">Loading the mood board…</p>
      {/if}
    {/if}
  </main>

  {#if meta && !failed}
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
  .board-wrap.pending {
    opacity: 0.6;
  }
  .panel {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-sm);
    padding: var(--space-lg);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
  }
  .panel h2 {
    font-size: var(--text-heading);
    line-height: var(--lh-heading);
    font-weight: var(--weight-semibold);
  }
  .panel button {
    min-height: var(--tap-min);
    padding: 0 var(--space-md);
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition:
      background-color 120ms ease,
      color 120ms ease;
  }
  @media (min-width: 1024px) {
    .page {
      max-width: calc(var(--content-max) + 2 * var(--space-lg));
      padding: var(--space-2xl) var(--space-lg) var(--space-3xl);
    }
  }
</style>

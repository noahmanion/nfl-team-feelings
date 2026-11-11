<script lang="ts">
  import { onMount } from 'svelte'
  import BoardHeading from './components/BoardHeading.svelte'
  import MoodBoard from './components/MoodBoard.svelte'
  import SiteFooter from './components/SiteFooter.svelte'
  import SiteHeader from './components/SiteHeader.svelte'
  import { loadLatest, loadMeta } from './lib/data'
  import type { Meta, WeekFile } from './lib/types'

  let meta = $state<Meta | null>(null)
  let view = $state<WeekFile | null>(null)
  let failed = $state(false)

  async function boot() {
    failed = false
    try {
      const [m, latest] = await Promise.all([loadMeta(), loadLatest()])
      meta = m
      view = latest
    } catch (err) {
      console.error(err)
      failed = true
    }
  }

  onMount(boot)

  const seasonMeta = $derived(meta && view ? meta.seasons.find((s) => s.season === view!.season) : undefined)
  const isLatest = $derived(!!meta && !!view && meta.latest.season === view.season && meta.latest.week === view.week)
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
    {:else if meta && view && seasonMeta}
      <BoardHeading
        season={seasonMeta}
        week={view.week}
        count={view.rows.length}
        partial={meta.partial_week}
        {isLatest}
        scoreKind={meta.score_kind}
      />
      <MoodBoard rows={view.rows} teams={meta.teams} bands={meta.bands} week={view.week} />
    {:else}
      <p class="visually-hidden">Loading the mood board…</p>
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

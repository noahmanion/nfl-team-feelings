<script lang="ts">
  import Badge from './Badge.svelte'
  import { weekLabel } from '../lib/format'
  import type { SeasonMeta } from '../lib/types'

  let {
    season,
    week,
    count,
    partial,
    isLatest,
    scoreKind,
    firstSeason = false,
  }: {
    season: SeasonMeta
    week: number
    count: number
    partial: boolean
    isLatest: boolean
    scoreKind: string
    /** The first season in the data: there is no "last season" to compare week 0 against. */
    firstSeason?: boolean
  } = $props()

  const label = $derived(weekLabel(week, season))
  const inProgress = $derived(partial && isLatest)
</script>

<div class="board-heading">
  <div class="title">
    <h2 id="board-heading">{season.season} · {label}</h2>
    {#if inProgress}<Badge variant="accent">In progress</Badge>{/if}
  </div>
  <p class="count">{count} teams{scoreKind === 'elo' ? ' · Elo-based score' : ''}</p>
  {#if inProgress}
    <p class="note">Some {label} games haven’t been played yet. Teams that haven’t played keep last week’s score.</p>
  {:else if week === 0}
    {#if firstSeason}
      <p class="note">Before kickoff: the first season in the data, so everyone starts even.</p>
    {:else}
      <p class="note">Before kickoff: last season’s mood, pulled back toward the middle. Change is vs the end of last season.</p>
    {/if}
  {/if}
</div>

<style>
  .board-heading {
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--space-xs);
    margin-bottom: var(--space-md);
  }
  .title {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--space-sm);
  }
  h2 {
    font-size: var(--text-heading);
    line-height: var(--lh-heading);
    font-weight: var(--weight-semibold);
  }
  .count,
  .note {
    color: var(--text-muted);
    font-size: var(--text-label);
    line-height: var(--lh-label);
  }
  .note {
    font-size: var(--text-body);
    line-height: var(--lh-body);
  }
  @media (min-width: 1024px) {
    .board-heading {
      grid-template-columns: 1fr auto;
      align-items: center;
    }
    .note {
      grid-column: 1 / -1;
    }
  }
</style>

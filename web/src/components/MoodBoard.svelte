<script lang="ts">
  import BoardRow from './BoardRow.svelte'
  import StatusPanel from './StatusPanel.svelte'
  import { go } from '../lib/route.svelte'
  import type { Meta, Row } from '../lib/types'

  let {
    rows = [],
    meta = null,
    week = 0,
    loading = false,
    busy = false,
  }: {
    rows?: Row[]
    meta?: Meta | null
    week?: number
    /** Initial boot: static skeleton, no data yet. */
    loading?: boolean
    /** Season switch: keep the current rows visible but dimmed. */
    busy?: boolean
  } = $props()

  const SKELETON_ROWS = 8
</script>

{#snippet columns()}
  <div class="columns" aria-hidden="true">
    <span>#</span><span>Team</span><span>Record</span><span class="num">Score</span><span>Mood</span><span class="num"
      >Change</span
    >
  </div>
{/snippet}

{#if loading || !meta}
  <div class="board">
    {@render columns()}
    <p class="visually-hidden">Loading the mood board…</p>
    <ol class="skeleton" aria-busy="true">
      {#each Array.from({ length: SKELETON_ROWS }, (_, i) => i) as i (i)}
        <li class="skeleton-row" aria-hidden="true"><span class="bar"></span></li>
      {/each}
    </ol>
  </div>
{:else if !busy && rows.length === 0}
  <StatusPanel
    variant="empty"
    title="No moods to report"
    body="We don’t have any teams for this week. Jump to the latest week to see the current board."
    actions={[{ label: 'Go to latest', onClick: () => go('#/') }]}
  />
{:else}
  <div class="board" class:busy>
    {@render columns()}
    <ol aria-labelledby="board-heading" aria-busy={busy}>
      {#each rows as row (row.franchise)}
        <BoardRow {row} team={meta.teams[row.franchise]} bands={meta.bands} {week} />
      {/each}
    </ol>
  </div>
{/if}

<style>
  ol {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
  }
  .busy {
    opacity: 0.6;
  }
  .skeleton-row {
    display: flex;
    align-items: center;
    block-size: 64px;
    padding: 0 var(--space-md);
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: var(--stripe-width) solid var(--border);
    border-radius: var(--radius-md);
  }
  .bar {
    display: block;
    inline-size: 60%;
    block-size: 16px;
    background: var(--border);
    border-radius: var(--radius-sm);
  }
  .columns {
    display: none;
  }
  @media (min-width: 1024px) {
    .columns {
      display: grid;
      grid-template-columns: 48px minmax(0, 1fr) 80px 72px minmax(0, 280px) 72px;
      column-gap: var(--space-md);
      /* align with row content: 1px border + stripe on the left, 1px border on the right */
      padding: 0 calc(var(--space-md) + 1px) var(--space-sm) calc(var(--space-md) + var(--stripe-width));
      font-size: var(--text-label);
      line-height: var(--lh-label);
      font-weight: var(--weight-semibold);
      color: var(--text-muted);
    }
    .num {
      text-align: right;
    }
  }
</style>

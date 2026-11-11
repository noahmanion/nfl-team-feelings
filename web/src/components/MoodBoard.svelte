<script lang="ts">
  import BoardRow from './BoardRow.svelte'
  import type { Band, Row, TeamMeta } from '../lib/types'

  let { rows, teams, bands, week }: { rows: Row[]; teams: Record<string, TeamMeta>; bands: Band[]; week: number } =
    $props()
</script>

<div class="board">
  <div class="columns" aria-hidden="true">
    <span>#</span><span>Team</span><span>Record</span><span class="num">Score</span><span>Mood</span><span class="num"
      >Change</span
    >
  </div>
  <ol aria-labelledby="board-heading">
    {#each rows as row (row.franchise)}
      <BoardRow {row} team={teams[row.franchise]} {bands} {week} />
    {/each}
  </ol>
</div>

<style>
  ol {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
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

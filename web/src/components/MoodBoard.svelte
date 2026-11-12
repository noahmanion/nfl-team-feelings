<script lang="ts">
  import BoardRow from './BoardRow.svelte'
  import StatusPanel from './StatusPanel.svelte'
  import { go } from '../lib/route.svelte'
  import { validMyTeam } from '../lib/myteam'
  import { myTeam } from '../lib/myteam.svelte'
  import { isActiveFranchise } from '../lib/teamNames'
  import type { Meta, Row } from '../lib/types'

  let {
    rows = [],
    meta = null,
    season = 0,
    week = 0,
    latest = true,
    loading = false,
    busy = false,
  }: {
    rows?: Row[]
    meta?: Meta | null
    season?: number
    week?: number
    /** Latest board: rows link to #/team/ABBR; historical boards link to that week's page. */
    latest?: boolean
    /** Initial boot: static skeleton, no data yet. */
    loading?: boolean
    /** Season switch: keep the current rows visible but dimmed. */
    busy?: boolean
  } = $props()

  const SKELETON_ROWS = 8

  const pinned = $derived(validMyTeam(myTeam.abbr, meta?.teams))
  // D-17: franchises that did not exist yet in the viewed season (HOU before 2002) are not shown.
  const visibleRows = $derived(rows.filter((r) => isActiveFranchise(r.franchise, season)))
  const pinnedOnBoard = $derived(pinned !== null && visibleRows.some((r) => r.franchise === pinned))

  // No row fragment link: the app uses hash routing, so scroll and focus by hand.
  function jumpToMine(): void {
    if (!pinned) return
    const li = document.getElementById('row-' + pinned)
    li?.scrollIntoView({ block: 'center' })
    li?.querySelector<HTMLAnchorElement>('a.row')?.focus({ preventScroll: true })
  }
</script>

{#snippet columns()}
  <div class="columns" aria-hidden="true">
    <span>#</span><span>Team</span><span class="right">Record</span><span class="right">Score</span><span>Mood</span><span
      class="right">Change</span
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
{:else if !busy && visibleRows.length === 0}
  <StatusPanel
    variant="empty"
    title="No moods to report"
    body="We don’t have any teams for this week. Jump to the latest week to see the current board."
    actions={[{ label: 'Go to latest', onClick: () => go('#/') }]}
  />
{:else}
  <div class="board" class:busy>
    {#if pinnedOnBoard}
      <div class="jump"><button type="button" onclick={jumpToMine}>Jump to my team</button></div>
    {/if}
    {@render columns()}
    <ol aria-labelledby="board-heading" aria-busy={busy}>
      {#each visibleRows as row (row.franchise)}
        <BoardRow {row} team={meta.teams[row.franchise]} bands={meta.bands} {season} {week} {latest} {pinned} />
      {/each}
    </ol>
  </div>
{/if}

<style>
  ol {
    display: flex;
    flex-direction: column;
    gap: 0;
  }
  .busy {
    opacity: 0.6;
  }
  .jump {
    display: flex;
    justify-content: flex-end;
    margin-block-end: var(--space-sm);
  }
  .jump button {
    min-block-size: var(--tap-min);
    padding: 0 var(--space-md);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    color: var(--text);
    font: inherit;
    font-size: var(--text-label);
    font-weight: var(--weight-bold);
    cursor: pointer;
  }
  .jump button:hover {
    background: var(--surface-hover);
  }
  .jump button:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  .skeleton-row {
    display: flex;
    align-items: center;
    block-size: 64px;
    padding: 0 var(--space-md);
    border-bottom: 1px solid var(--border);
    border-radius: 0;
  }
  .bar {
    display: block;
    inline-size: 60%;
    block-size: 16px;
    background: var(--border);
    border-radius: 0;
  }
  .columns {
    display: none;
  }
  @media (min-width: 1024px) {
    .columns {
      display: grid;
      grid-template-columns: 32px minmax(0, 1fr) 80px var(--score-cell) minmax(0, 280px) 72px;
      column-gap: var(--space-md);
      /* align with BoardRow content; the right side reserves the pin button slot */
      padding: 0 calc(var(--tap-min) + var(--space-sm)) var(--space-sm) var(--space-md);
      border-bottom: 1px solid var(--rule-strong);
      font-family: var(--font-mono);
      font-size: var(--text-micro);
      line-height: var(--lh-micro);
      font-weight: var(--weight-regular);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--text-muted);
    }
    .right {
      text-align: right;
    }
  }
</style>

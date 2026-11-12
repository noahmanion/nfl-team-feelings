<script lang="ts">
  import TeamLogo from './TeamLogo.svelte'
  import { findSeason } from '../lib/data'
  import { weekLabel } from '../lib/format'
  import { signed, type RecentGame } from '../lib/team'
  import { eraAbbr, eraName } from '../lib/teamNames'
  import type { Meta } from '../lib/types'

  let { games, meta, currentSeason }: { games: RecentGame[]; meta: Meta; currentSeason: number } = $props()

  function when(g: RecentGame): string {
    const sm = findSeason(meta, g.season)
    const label = sm ? weekLabel(g.week, sm) : `Week ${g.week}`
    return g.season === currentSeason ? label : `${g.season} · ${label}`
  }

  const word = { W: 'Won', L: 'Lost', T: 'Tied' } as const
</script>

{#if games.length === 0}
  <p class="empty">No games yet.</p>
{:else}
  <ol class="games">
    {#each games as g (`${g.season}-${g.week}-${g.opp}`)}
      {@const opp = meta.teams[g.opp]}
      <li class="game">
        <span class="visually-hidden"
          >{when(g)}: {word[g.result]} {g.pf} to {g.pa} {g.home || g.neutral ? 'against' : 'at'}
          {eraName(g.opp, g.season, meta)}{g.neutral ? ', neutral site' : ''}.</span
        >
        <span class="when" aria-hidden="true">{when(g)}</span>
        <span class="matchup" aria-hidden="true">
          <span class="at">{g.home || g.neutral ? 'vs' : '@'}</span>
          <TeamLogo franchise={g.opp} primary={opp?.primary} secondary={opp?.secondary} size={20} />
          <span class="opp">{eraAbbr(g.opp, g.season)}</span>
          {#if g.neutral}<span class="neutral">(neutral)</span>{/if}
        </span>
        <span class="outcome" aria-hidden="true">
          <span class="result {g.result}">{g.result}</span>
          <span class="score">{g.pf}–{g.pa}</span>
          <span class="margin">{signed(g.margin)}</span>
        </span>
      </li>
    {/each}
  </ol>
{/if}

<style>
  .empty {
    color: var(--text-muted);
  }
  .games {
    display: flex;
    flex-direction: column;
  }
  .game {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-rows: auto auto;
    column-gap: var(--space-sm);
    align-items: center;
    padding: var(--space-sm) 0;
    border-bottom: 1px solid var(--border);
  }
  .game:last-child {
    border-bottom: none;
  }
  .when {
    grid-column: 1;
    grid-row: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text-muted);
    font-size: var(--text-label);
    line-height: var(--lh-label);
  }
  .matchup {
    grid-column: 1;
    grid-row: 2;
    display: flex;
    align-items: center;
    gap: var(--space-xs);
    min-width: 0;
  }
  .at {
    color: var(--text-muted);
  }
  .opp {
    font-weight: var(--weight-bold);
  }
  .neutral {
    color: var(--text-muted);
    font-size: var(--text-label);
  }
  .outcome {
    grid-column: 2;
    grid-row: 1 / span 2;
    display: flex;
    align-items: baseline;
    gap: var(--space-sm);
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  .result {
    font-weight: var(--weight-semibold);
  }
  .W {
    color: var(--up);
  }
  .L {
    color: var(--down);
  }
  .T {
    color: var(--text-muted);
  }
  .margin {
    min-inline-size: 3ch;
    text-align: right;
    color: var(--text-muted);
    font-size: var(--text-label);
  }
</style>

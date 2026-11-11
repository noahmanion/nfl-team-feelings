<script lang="ts">
  import { barRows, signed, type BarRow } from '../lib/team'
  import type { FactorMeta } from '../lib/types'

  let {
    points,
    factors,
    baseline,
    score,
  }: { points: Record<string, number> | undefined; factors: FactorMeta[]; baseline: number; score: number } = $props()

  // Factor-agnostic: whatever meta.factors lists is drawn, in |points| order.
  const bars = $derived(points ? barRows(points, factors, baseline) : null)
  const width = (p: number, scale: number): string => `${(Math.abs(p) / scale) * 50}%`
</script>

{#snippet bar(r: BarRow, scale: number)}
  <li class="factor">
    <span class="visually-hidden">{r.label}: {signed(r.points)} points</span>
    <span class="label" aria-hidden="true">{r.label}</span>
    <span class="value" class:up={r.points > 0} class:down={r.points < 0} aria-hidden="true">{signed(r.points)}</span>
    <span class="track" aria-hidden="true">
      <span
        class="bar"
        class:pos={r.points > 0}
        class:neg={r.points < 0}
        style:width={width(r.points, scale)}
      ></span>
    </span>
    {#if r.description}<span class="desc">{r.description}</span>{/if}
  </li>
{/snippet}

<div class="factors">
  {#if bars}
    <p class="baseline">Average team {baseline}</p>
    <ol>
      {#each bars.shown as r (r.key)}
        {@render bar(r, bars.scale)}
      {/each}
    </ol>
    {#if bars.rest.length}
      <details>
        <summary>All factors</summary>
        <ol>
          {#each bars.rest as r (r.key)}
            {@render bar(r, bars.scale)}
          {/each}
        </ol>
      </details>
    {/if}
    <p class="total">= {score}</p>
  {:else}
    <p class="missing">Factor breakdown unavailable for this week.</p>
  {/if}
</div>

<style>
  .factors {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
    min-width: 0;
  }
  .baseline,
  .missing {
    color: var(--text-muted);
    font-size: var(--text-label);
    line-height: var(--lh-label);
  }
  ol {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
  }
  details ol {
    margin-top: var(--space-md);
  }
  .factor {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    column-gap: var(--space-sm);
    row-gap: var(--space-xs);
    align-items: baseline;
    min-width: 0;
  }
  .label {
    min-width: 0;
    font-size: var(--text-body);
    line-height: var(--lh-body);
  }
  .value {
    font-size: var(--text-label);
    line-height: var(--lh-label);
    font-weight: var(--weight-semibold);
    font-variant-numeric: tabular-nums;
    color: var(--text-muted);
  }
  .value.up {
    color: var(--up);
  }
  .value.down {
    color: var(--down);
  }
  .track {
    grid-column: 1 / -1;
    position: relative;
    display: block;
    min-width: 0;
    block-size: var(--space-sm);
  }
  /* 1px center line = the "average team" baseline */
  .track::before {
    content: '';
    position: absolute;
    inset-block: calc(-1 * var(--space-xs));
    left: 50%;
    width: 1px;
    background: var(--border);
  }
  .bar {
    position: absolute;
    inset-block: 0;
    border-radius: var(--radius-sm);
  }
  .bar.pos {
    left: 50%;
    background: var(--up);
  }
  .bar.neg {
    right: 50%;
    background: var(--down);
  }
  .desc {
    grid-column: 1 / -1;
    color: var(--text-muted);
    font-size: var(--text-label);
    line-height: var(--lh-label);
  }
  details summary {
    display: inline-flex;
    align-items: center;
    min-block-size: var(--tap-min);
    color: var(--accent);
    cursor: pointer;
  }
  .total {
    padding-top: var(--space-sm);
    border-top: 1px solid var(--border);
    font-weight: var(--weight-semibold);
    font-variant-numeric: tabular-nums;
  }
</style>

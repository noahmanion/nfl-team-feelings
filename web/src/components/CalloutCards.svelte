<script lang="ts">
  import CalloutCard from './CalloutCard.svelte'
  import type { Callout, Meta } from '../lib/types'

  let {
    callouts,
    meta,
    heading = 'Worth talking about',
  }: { callouts: Callout[]; meta: Meta; heading?: string } = $props()

  const MAX = 6
  const first = $derived(callouts.slice(0, MAX))
  const rest = $derived(callouts.slice(MAX))
  const key = (c: Callout) => `${c.type}|${c.franchise}|${c.season}|${c.week}`
</script>

{#if callouts.length > 0}
  <section class="callouts" aria-label={heading}>
    <h2>{heading}</h2>
    <div class="grid">
      {#each first as c (key(c))}
        <CalloutCard callout={c} team={meta.teams[c.franchise]} bands={meta.bands} />
      {/each}
    </div>
    {#if rest.length > 0}
      <details>
        <summary>Show all {callouts.length}</summary>
        <div class="grid more">
          {#each rest as c (key(c))}
            <CalloutCard callout={c} team={meta.teams[c.franchise]} bands={meta.bands} />
          {/each}
        </div>
      </details>
    {/if}
  </section>
{/if}

<style>
  .callouts {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
    margin-bottom: var(--space-lg);
    min-width: 0;
  }
  h2 {
    font-size: var(--text-heading);
    line-height: var(--lh-heading);
    font-weight: var(--weight-semibold);
  }
  .grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-md);
  }
  .more {
    margin-top: var(--space-md);
  }
  summary {
    display: flex;
    align-items: center;
    min-block-size: var(--tap-min);
    color: var(--accent);
    cursor: pointer;
  }
  summary:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  @media (min-width: 1024px) {
    .grid {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
  }
</style>

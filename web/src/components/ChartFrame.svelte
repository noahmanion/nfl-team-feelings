<script lang="ts">
  import type { Snippet } from 'svelte'

  // Chart wrapper (D-08): HTML headline, optional dek, the chart, and a mono SOURCE/NOTES footer.
  // Headlines are never Plot titles; the figure is labelled by its heading.
  let {
    headline,
    dek,
    notes,
    level = 3,
    id,
    source,
    children,
  }: { headline: string; dek?: string; notes?: string; level?: 2 | 3; id: string; source?: string; children: Snippet } =
    $props()
</script>

<figure class="chart-frame" aria-labelledby={id}>
  <svelte:element this={`h${level}`} {id} class="cf-headline">{headline}</svelte:element>
  {#if dek}<p class="cf-dek">{dek}</p>{/if}
  <div class="cf-body">{@render children()}</div>
  <figcaption class="cf-foot">
    <span class="cf-source">{source ?? 'SOURCE: NFLVERSE · FEEL-GOOD SCORE'}</span>
    {#if notes}<span class="cf-notes">NOTES: {notes}</span>{/if}
  </figcaption>
</figure>

<style>
  .chart-frame {
    margin: 0;
    border: none;
    background: none;
  }
  :global(.chart-frame + .chart-frame) {
    margin-top: var(--space-xl);
  }
  .cf-headline {
    margin: 0;
    font-size: var(--text-heading);
    line-height: var(--lh-heading);
    font-weight: var(--weight-bold);
    color: var(--text);
  }
  .cf-dek {
    margin: var(--space-xs) 0 0;
    font-size: var(--text-body);
    line-height: var(--lh-body);
    color: var(--text-muted);
    max-width: var(--prose-max);
  }
  .cf-body {
    margin-top: var(--space-md);
    min-width: 0;
  }
  .cf-foot {
    margin-top: var(--space-sm);
    font-family: var(--font-mono);
    font-size: var(--text-micro);
    line-height: var(--lh-micro);
    color: var(--text-muted);
    letter-spacing: 0.04em;
  }
  .cf-source,
  .cf-notes {
    display: block;
    overflow-wrap: anywhere;
  }
  .cf-source {
    text-transform: uppercase;
  }
  /* notes stay sentence case: long uppercase sentences are hard to read */
  .cf-notes {
    margin-top: var(--space-xs);
  }
</style>

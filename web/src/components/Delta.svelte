<script lang="ts">
  import { formatDelta, formatRankDelta } from '../lib/format'

  let { value, kind = 'score' }: { value: number | null; kind?: 'score' | 'rank' } = $props()
  const d = $derived(formatDelta(value))
  const r = $derived(formatRankDelta(value))
</script>

{#if kind === 'rank'}
  <span class="delta {r.dir}" aria-label={r.aria}>{r.text}</span>
{:else}
  <span class="delta {d.dir}">{d.text}</span>
{/if}

<style>
  .delta {
    font-family: var(--font-mono);
    font-size: var(--text-label);
    line-height: var(--lh-label);
    font-weight: var(--weight-semibold);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  .up {
    color: var(--up);
  }
  .down {
    color: var(--down);
  }
  .none {
    color: var(--text-muted);
  }
</style>

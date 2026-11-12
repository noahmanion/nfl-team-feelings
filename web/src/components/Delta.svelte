<script lang="ts">
  import { formatDelta } from '../lib/format'

  let { value, kind = 'score' }: { value: number | null; kind?: 'score' | 'rank' } = $props()
  const d = $derived(formatDelta(value))
</script>

<span class="delta {d.dir}">{kind === 'rank' ? '#' : ''}{d.text}</span>

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

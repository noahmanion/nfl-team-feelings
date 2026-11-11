<script lang="ts">
  import type { Snippet } from 'svelte'

  let { variant = 'default', children }: { variant?: 'default' | 'accent'; children: Snippet } = $props()
</script>

<span class="badge" class:accent={variant === 'accent'}>{@render children()}</span>

<style>
  .badge {
    display: inline-block;
    padding: 0 var(--space-sm);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    font-size: var(--text-label);
    line-height: var(--lh-label);
    font-weight: var(--weight-semibold);
    color: var(--text-muted);
    white-space: nowrap;
  }
  .accent {
    border-color: var(--accent);
    color: var(--accent);
  }
</style>

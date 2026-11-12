<script lang="ts">
  import type { Snippet } from 'svelte'

  let { variant = 'default', children }: { variant?: 'default' | 'accent' | 'neutral'; children: Snippet } = $props()
</script>

<span class="badge" class:accent={variant === 'accent'} class:neutral={variant === 'neutral'}>{@render children()}</span>

<style>
  .badge {
    display: inline-block;
    padding: 0 var(--space-sm);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    font-family: var(--font-mono);
    font-size: var(--text-micro);
    line-height: var(--lh-micro);
    font-weight: var(--weight-regular);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-muted);
    white-space: nowrap;
  }
  .accent {
    border-color: var(--accent);
    color: var(--accent);
  }
  .neutral {
    border-color: var(--border);
    color: var(--text);
  }
</style>

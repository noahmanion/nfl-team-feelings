<script lang="ts">
  import type { Snippet } from 'svelte'

  export interface StatusAction {
    label: string
    onClick: () => void
  }

  let {
    variant,
    title,
    body,
    actions = [],
    onDismiss,
    fatal = false,
    children,
  }: {
    variant: 'notice' | 'error' | 'empty'
    title?: string
    /** Plain-text body. Use `children` instead when the body needs markup (e.g. a <code> command). */
    body?: string
    actions?: StatusAction[]
    onDismiss?: () => void
    fatal?: boolean
    children?: Snippet
  } = $props()
</script>

{#snippet content()}
  {#if title}<h2>{title}</h2>{/if}
  <p>{#if children}{@render children()}{:else}{body}{/if}</p>
  {#if actions.length}
    <div class="actions">
      {#each actions as action (action.label)}
        <button type="button" onclick={action.onClick}>{action.label}</button>
      {/each}
    </div>
  {/if}
{/snippet}

{#if variant === 'notice'}
  <div class="notice" role="status">
    <p>{body}</p>
    {#if onDismiss}
      <button type="button" class="dismiss" aria-label="Dismiss" onclick={onDismiss}>×</button>
    {/if}
  </div>
{:else if fatal}
  <section class="panel" role="alert">{@render content()}</section>
{:else}
  <section class="panel" role="status">{@render content()}</section>
{/if}

<style>
  .notice {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    margin-bottom: var(--space-sm);
    color: var(--text-muted);
    font-size: var(--text-body);
    line-height: var(--lh-body);
  }
  .notice p {
    flex: 1;
  }
  .dismiss {
    flex: none;
    inline-size: var(--tap-min);
    block-size: var(--tap-min);
    background: transparent;
    color: var(--text-muted);
    border: none;
    border-radius: var(--radius-md);
    font-size: var(--text-heading);
    line-height: 1;
    cursor: pointer;
    transition:
      background-color 120ms ease,
      color 120ms ease;
  }
  .dismiss:hover {
    color: var(--text);
  }
  .panel {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-sm);
    padding: var(--space-lg);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
  }
  .panel p {
    font-size: var(--text-body);
    line-height: var(--lh-body);
  }
  .panel :global(code) {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.9em;
    overflow-wrap: anywhere;
  }
  h2 {
    font-size: var(--text-heading);
    line-height: var(--lh-heading);
    font-weight: var(--weight-semibold);
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-sm);
  }
  .actions button {
    min-height: var(--tap-min);
    padding: 0 var(--space-md);
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition:
      background-color 120ms ease,
      color 120ms ease;
  }
  .actions button:hover {
    background: var(--bg);
  }
  .actions button:focus-visible,
  .dismiss:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
</style>

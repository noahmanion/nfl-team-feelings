<script lang="ts">
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
  }: {
    variant: 'notice' | 'error' | 'empty'
    title?: string
    body: string
    actions?: StatusAction[]
    onDismiss?: () => void
    fatal?: boolean
  } = $props()
</script>

{#if variant === 'notice'}
  <div class="notice" role="status">
    <p>{body}</p>
    {#if onDismiss}
      <button type="button" class="dismiss" aria-label="Dismiss" onclick={onDismiss}>×</button>
    {/if}
  </div>
{:else}
  <section class="panel" role={fatal ? 'alert' : 'status'}>
    {#if title}<h2>{title}</h2>{/if}
    <p>{body}</p>
    {#if actions.length}
      <div class="actions">
        {#each actions as action (action.label)}
          <button type="button" onclick={action.onClick}>{action.label}</button>
        {/each}
      </div>
    {/if}
  </section>
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
</style>

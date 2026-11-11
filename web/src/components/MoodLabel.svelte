<script lang="ts">
  let { emoji, label, size = 'body' }: { emoji: string; label: string; size?: 'body' | 'heading' } = $props()
</script>

<span class="mood" class:heading={size === 'heading'} title={label}
  ><span class="emoji" aria-hidden="true">{emoji}</span><span class="text">{label}</span></span
>

<style>
  .mood {
    display: flex;
    align-items: baseline;
    gap: var(--space-xs);
    min-width: 0;
  }
  .heading {
    font-size: var(--text-heading);
    line-height: var(--lh-heading);
    font-weight: var(--weight-semibold);
  }
  .emoji {
    flex: none;
  }
  .text {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>

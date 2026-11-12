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
    font-weight: var(--weight-bold);
  }
  /* Explicit em-based gap: emoji advance widths vary (variation selectors), and the flex gap
     alone left the glyph touching the label. Scales with the heading size. */
  .emoji {
    flex: none;
    margin-inline-end: 0.35em;
  }
  .text {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>

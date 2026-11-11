<script lang="ts">
  let { emoji, label }: { emoji: string; label: string } = $props()
</script>

<span class="mood" title={label}><span class="emoji" aria-hidden="true">{emoji}</span><span class="text">{label}</span></span>

<style>
  .mood {
    display: flex;
    align-items: baseline;
    gap: var(--space-xs);
    min-width: 0;
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

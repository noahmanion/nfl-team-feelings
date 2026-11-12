<script lang="ts">
  let {
    primary,
    secondary,
    size = 16,
  }: { primary?: string | null; secondary?: string | null; size?: 16 | 20 | 24 | 32 | 48 } = $props()

  const HEX = /^#[0-9A-Fa-f]{6}$/
  const ok = $derived(!!primary && !!secondary && HEX.test(primary) && HEX.test(secondary))
</script>

<span
  class="chip"
  class:fallback={!ok}
  style:--chip-size="{size}px"
  style:--team-primary={ok ? primary : null}
  style:--team-secondary={ok ? secondary : null}
  aria-hidden="true"
></span>

<style>
  .chip {
    display: inline-block;
    flex: none;
    width: var(--chip-size);
    height: var(--chip-size);
    border-radius: var(--radius-sm);
    background: linear-gradient(135deg, var(--team-primary) 0 50%, var(--team-secondary) 50% 100%);
    box-shadow: inset 0 0 0 1px var(--chip-outline);
  }
  .fallback {
    background: var(--text-muted);
  }
</style>

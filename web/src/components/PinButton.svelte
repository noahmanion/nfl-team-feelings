<script lang="ts">
  import { myTeam, toggleMyTeam } from '../lib/myteam.svelte'

  let { abbr, name }: { abbr: string; name: string } = $props()

  const pinned = $derived(myTeam.abbr === abbr)
  // WR-06: a toggle keeps one fixed label; aria-pressed alone carries the on/off state
  // ("My team: Buffalo Bills, toggle button, pressed").
</script>

<button
  type="button"
  class="pin"
  class:pinned
  aria-pressed={pinned}
  aria-label="My team: {name}"
  onclick={() => toggleMyTeam(abbr)}
>
  <span aria-hidden="true">{pinned ? '★' : '☆'}</span>
</button>

<style>
  .pin {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: none;
    inline-size: var(--tap-min);
    block-size: var(--tap-min);
    padding: 0;
    background: transparent;
    border: 0;
    border-radius: var(--radius-sm);
    color: var(--text-muted);
    font-size: var(--text-heading);
    line-height: 1;
    cursor: pointer;
  }
  .pin:hover {
    color: var(--text);
  }
  .pinned {
    color: var(--accent);
  }
  .pin:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
</style>

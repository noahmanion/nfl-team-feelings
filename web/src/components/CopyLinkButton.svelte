<script lang="ts">
  import { tick } from 'svelte'
  import { copyText } from '../lib/copyLink'

  // Shared Copy link button (14-04): callout cards and the team page header. The URL is computed at
  // click time, so it always matches the week being viewed (share page or hash deep link).
  let { getUrl, name, ariaLabel }: { getUrl: () => string; name: string; ariaLabel?: string } = $props()

  let result = $state<'idle' | 'copied' | 'manual'>('idle')
  let url = $state('')
  let manualInput = $state<HTMLInputElement | null>(null)
  const status = $derived(result === 'copied' ? 'Link copied' : result === 'manual' ? 'Copy the link below' : '')

  // "Link copied" clears after ~2s; a new click restarts the timer. The manual
  // fallback field stays until the next click, since the user still has to copy from it.
  const RESET_MS = 2000
  let resetTimer: ReturnType<typeof setTimeout> | undefined
  $effect(() => () => clearTimeout(resetTimer))

  // WR-05: clear the live region first and let it render empty, so a repeated click re-announces
  // the same message; in the manual case move focus to the link field for keyboard users.
  async function copy() {
    clearTimeout(resetTimer)
    result = 'idle'
    await tick()
    url = getUrl()
    const r = await copyText(url)
    result = r
    if (r === 'copied') {
      resetTimer = setTimeout(() => {
        if (result === 'copied') result = 'idle'
      }, RESET_MS)
    }
    if (r === 'manual') {
      await tick()
      manualInput?.focus()
    }
  }

  const selectAll = (e: Event) => (e.currentTarget as HTMLInputElement).select()
</script>

<div class="copy-link">
  <button type="button" class="copy" aria-label={ariaLabel} onclick={copy}>Copy link</button>
  <!-- always in the accessibility tree (WR-05); only visually hidden while empty -->
  <p class="status" class:visually-hidden={!status} role="status">{status}</p>
  {#if result === 'manual'}
    <input
      bind:this={manualInput}
      class="manual"
      type="text"
      readonly
      value={url}
      aria-label="Link to {name}"
      onfocus={selectAll}
      onclick={selectAll}
    />
  {/if}
</div>

<style>
  .copy-link {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    column-gap: var(--space-md);
    row-gap: var(--space-xs);
    flex: 1 1 auto;
    min-width: 0;
    position: relative; /* contains the visually hidden status */
  }
  .copy {
    min-block-size: var(--tap-min);
    padding: 0 var(--space-md);
    font: inherit;
    font-size: var(--text-label);
    font-weight: var(--weight-bold);
    color: var(--accent);
    background: transparent;
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    cursor: pointer;
  }
  .copy:focus-visible,
  .manual:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  .status {
    font-size: var(--text-label);
    line-height: var(--lh-label);
    color: var(--text-muted);
  }
  .manual {
    flex-basis: 100%;
    width: 100%;
    min-block-size: var(--tap-min);
    padding: 0 var(--space-sm);
    font: inherit;
    font-size: var(--text-label);
    color: var(--text);
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
  }
</style>

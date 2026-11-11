<script lang="ts">
  import { tick } from 'svelte'
  import TeamChip from './TeamChip.svelte'
  import { calloutHref } from '../lib/callouts'
  import { copyText, deepLink } from '../lib/copyLink'
  import { bandIndex, moodToken } from '../lib/format'
  import type { Band, Callout, TeamMeta } from '../lib/types'

  let { callout, team, bands }: { callout: Callout; team: TeamMeta | undefined; bands: Band[] } = $props()

  const name = $derived(team?.name ?? callout.franchise)
  const href = $derived(calloutHref(callout))
  const bandIdx = $derived(bandIndex(callout.band, bands))
  const stripe = $derived(bandIdx < 0 ? 'var(--border)' : `var(--mood-${moodToken(bandIdx, bands.length)})`)

  let result = $state<'idle' | 'copied' | 'manual'>('idle')
  let url = $state('')
  let manualInput = $state<HTMLInputElement | null>(null)
  const status = $derived(result === 'copied' ? 'Link copied' : result === 'manual' ? 'Copy the link below' : '')

  // WR-05: clear the live region first and let it render empty, so a repeated click re-announces
  // the same message; in the manual case move focus to the link field for keyboard users.
  async function copy() {
    result = 'idle'
    await tick()
    url = deepLink(href)
    const r = await copyText(url)
    result = r
    if (r === 'manual') {
      await tick()
      manualInput?.focus()
    }
  }

  const selectAll = (e: Event) => (e.currentTarget as HTMLInputElement).select()
</script>

<article class="card" style:--stripe-color={stripe}>
  <p class="who">
    <TeamChip primary={team?.primary} secondary={team?.secondary} />
    <span class="name">{name}</span>
  </p>
  <h3 class="headline">{callout.headline}</h3>
  <p class="detail">{callout.detail}</p>
  {#if callout.evidence}<p class="evidence">{callout.evidence}</p>{/if}
  <div class="actions">
    <a class="see" {href}>See {name}</a>
    <button type="button" class="copy" onclick={copy}>Copy link</button>
  </div>
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
</article>

<style>
  .card {
    position: relative; /* contains the visually hidden status */
    display: flex;
    flex-direction: column;
    gap: var(--space-xs);
    min-width: 0;
    padding: var(--space-md);
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: var(--stripe-width) solid var(--stripe-color);
    border-radius: var(--radius-md);
  }
  .who {
    display: flex;
    align-items: center;
    gap: var(--space-xs);
    min-width: 0;
    font-size: var(--text-label);
    line-height: var(--lh-label);
    color: var(--text-muted);
  }
  .name {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .headline {
    font-size: var(--text-heading);
    line-height: var(--lh-heading);
    font-weight: var(--weight-semibold);
    overflow-wrap: anywhere;
  }
  .detail {
    font-size: var(--text-body);
    line-height: var(--lh-body);
    color: var(--text-muted);
  }
  .evidence {
    font-size: var(--text-label);
    line-height: var(--lh-label);
    color: var(--text-muted);
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-md);
    margin-top: auto;
    padding-top: var(--space-xs);
  }
  .see {
    display: inline-flex;
    align-items: center;
    min-block-size: var(--tap-min);
    color: var(--accent);
  }
  .copy {
    min-block-size: var(--tap-min);
    padding: 0 var(--space-md);
    font: inherit;
    font-size: var(--text-label);
    font-weight: var(--weight-semibold);
    color: var(--accent);
    background: transparent;
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    cursor: pointer;
  }
  .copy:focus-visible,
  .see:focus-visible,
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

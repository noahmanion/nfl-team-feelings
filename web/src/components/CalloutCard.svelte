<script lang="ts">
  import CopyLinkButton from './CopyLinkButton.svelte'
  import TeamLogo from './TeamLogo.svelte'
  import { calloutHref } from '../lib/callouts'
  import { deepLink } from '../lib/copyLink'
  import { bandIndex, moodToken } from '../lib/format'
  import { eraName, eraText } from '../lib/teamNames'
  import { calloutCopyUrl } from '../lib/share'
  import type { Band, Callout, Meta, TeamMeta } from '../lib/types'

  let {
    callout,
    team,
    bands,
    meta,
    level = 3,
  }: { callout: Callout; team: TeamMeta | undefined; bands: Band[]; meta: Meta; level?: number } = $props()

  // Era-correct name and copy for the callout's season (D-16, D-26).
  const name = $derived(eraName(callout.franchise, callout.season, { teams: team ? { [callout.franchise]: team } : {} }))
  const headline = $derived(eraText(callout.headline, callout.franchise, callout.season))
  const detail = $derived(eraText(callout.detail, callout.franchise, callout.season))
  const evidence = $derived(callout.evidence ? eraText(callout.evidence, callout.franchise, callout.season) : null)
  const href = $derived(calloutHref(callout))
  const bandIdx = $derived(bandIndex(callout.band, bands))
  const stripe = $derived(bandIdx < 0 ? 'var(--border)' : `var(--mood-${moodToken(bandIdx, bands.length)})`)
</script>

<article class="card" style:--stripe-color={stripe}>
  <p class="who">
    <TeamLogo franchise={callout.franchise} primary={team?.primary} secondary={team?.secondary} size={20} />
    <span class="name">{name}</span>
  </p>
  <!-- the team is part of the accessible heading: headlines like "5-4, but better days are coming"
       repeat across teams (WR-07) -->
  <svelte:element this={`h${level}`} class="headline"
    ><span class="visually-hidden">{name}: </span>{headline}</svelte:element
  >
  <p class="detail">{detail}</p>
  {#if evidence}<p class="evidence">{evidence}</p>{/if}
  <div class="actions">
    <a class="see" {href}>See {name}</a>
    <!-- D-22: share page URL from the launch week on, hash deep link before it -->
    <CopyLinkButton getUrl={() => calloutCopyUrl(callout, meta, location.origin, deepLink)} {name} />
  </div>
</article>

<style>
  .card {
    position: relative; /* contains the visually hidden status */
    display: flex;
    flex-direction: column;
    gap: var(--space-xs);
    min-width: 0;
    block-size: 100%;
    /* editorial block (D-22): rule-topped in the band color, no box */
    padding-top: var(--space-md);
    border-top: 2px solid var(--stripe-color);
    border-radius: 0;
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
    font-weight: var(--weight-bold);
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
  .see:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
</style>

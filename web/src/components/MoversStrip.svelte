<script lang="ts">
  import Delta from './Delta.svelte'
  import TeamLogo from './TeamLogo.svelte'
  import { calloutHref } from '../lib/callouts'
  import { eraAbbr, eraName, eraText } from '../lib/teamNames'
  import type { Callout, Meta } from '../lib/types'

  let { up, down, meta }: { up: Callout[]; down: Callout[]; meta: Meta } = $props()

  const cols = $derived([
    { id: 'risers', title: 'Risers', items: up },
    { id: 'fallers', title: 'Fallers', items: down },
  ])
</script>

{#if up.length > 0 || down.length > 0}
  <section class="movers" aria-labelledby="movers-heading">
    <h2 id="movers-heading">Biggest movers</h2>
    <div class="cols">
      {#each cols as col (col.id)}
        <div class="col">
          <h3 id="movers-{col.id}">{col.title}</h3>
          {#if col.items.length > 0}
            <ul aria-labelledby="movers-{col.id}">
              {#each col.items as c (c.franchise)}
                {@const team = meta.teams[c.franchise]}
                {@const srName = eraName(c.franchise, c.season, meta)}
                {@const srHeadline = eraText(c.headline, c.franchise, c.season)}
                {@const srDetail = eraText(c.detail, c.franchise, c.season)}
                <li>
                  <a class="item" href={calloutHref(c)}>
                    <span class="visually-hidden">{srName}, {srHeadline}, {srDetail}</span>
                    <span class="line" aria-hidden="true">
                      <TeamLogo franchise={c.franchise} primary={team?.primary} secondary={team?.secondary} size={20} />
                      <span class="abbr">{eraAbbr(c.franchise, c.season)}</span>
                      <Delta value={c.stat} kind="score" />
                    </span>
                  </a>
                </li>
              {/each}
            </ul>
          {:else}
            <p class="none">None this week</p>
          {/if}
        </div>
      {/each}
    </div>
  </section>
{/if}

<style>
  .movers {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
    margin-bottom: var(--space-lg);
    min-width: 0;
  }
  h2 {
    font-size: var(--text-heading);
    line-height: var(--lh-heading);
    font-weight: var(--weight-bold);
  }
  .cols {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--space-md);
  }
  .col {
    display: flex;
    flex-direction: column;
    gap: var(--space-xs);
    min-width: 0;
  }
  h3 {
    font-family: var(--font-mono);
    font-size: var(--text-micro);
    line-height: var(--lh-micro);
    font-weight: var(--weight-regular);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-muted);
  }
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0;
  }
  .item {
    display: flex;
    align-items: center;
    min-block-size: var(--tap-min);
    min-width: 0;
    padding: 0 var(--space-sm);
    background: transparent;
    border-bottom: 1px solid var(--border);
    border-radius: 0;
    color: inherit;
    text-decoration: none;
    transition: background-color 120ms ease;
  }
  .item:hover {
    background: var(--surface-hover);
  }
  .item:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: -2px;
  }
  .line {
    display: flex;
    align-items: center;
    gap: var(--space-xs);
    min-width: 0;
    overflow: hidden;
    white-space: nowrap;
  }
  .abbr {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    font-weight: var(--weight-bold);
    letter-spacing: 0.02em;
  }
  .none {
    font-size: var(--text-label);
    line-height: var(--lh-label);
    color: var(--text-muted);
  }
</style>

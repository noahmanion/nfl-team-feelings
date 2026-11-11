<script lang="ts">
  import Delta from './Delta.svelte'
  import TeamChip from './TeamChip.svelte'
  import { calloutHref } from '../lib/callouts'
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
                <li>
                  <a class="item" href={calloutHref(c)}>
                    <span class="visually-hidden">{team?.name ?? c.franchise}, {c.headline}, {c.detail}</span>
                    <span class="line" aria-hidden="true">
                      <TeamChip primary={team?.primary} secondary={team?.secondary} />
                      <span class="abbr">{c.franchise}</span>
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
    font-weight: var(--weight-semibold);
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
    font-size: var(--text-label);
    line-height: var(--lh-label);
    font-weight: var(--weight-semibold);
    color: var(--text-muted);
  }
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-xs);
  }
  .item {
    display: flex;
    align-items: center;
    min-block-size: var(--tap-min);
    min-width: 0;
    padding: 0 var(--space-sm);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    color: inherit;
    text-decoration: none;
  }
  .item:hover {
    background: var(--bg);
  }
  .item:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
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
    font-weight: var(--weight-semibold);
    letter-spacing: 0.02em;
  }
  .none {
    font-size: var(--text-label);
    line-height: var(--lh-label);
    color: var(--text-muted);
  }
</style>

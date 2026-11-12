<script lang="ts" module>
  export interface ExploreColumn {
    key: string
    label: string
    numeric?: boolean
    /** Hidden below 640px. */
    wideOnly?: boolean
  }
  export interface ExploreCell {
    text: string
    tone?: 'up' | 'down' | 'muted'
  }
  export interface ExploreRow {
    franchise: string
    abbr: string
    name: string
    href: string
    mine: boolean
    cells: Record<string, ExploreCell>
  }
</script>

<script lang="ts">
  import TeamLogo from './TeamLogo.svelte'
  import type { Meta } from '../lib/types'

  // Accessible table view of an Explore chart (D-16a): collapsed by default, team links go to the
  // same team pages as the chart marks.
  let { caption, columns, rows, meta }: { caption: string; columns: ExploreColumn[]; rows: ExploreRow[]; meta: Meta } =
    $props()
</script>

<details class="as-table">
  <summary>Show as table</summary>
  <div class="scroll">
    <table>
      <caption class="visually-hidden">{caption}</caption>
      <thead>
        <tr>
          <th scope="col" class="num">#</th>
          <th scope="col">Team</th>
          {#each columns as c (c.key)}
            <th scope="col" class:num={c.numeric} class:wide={c.wideOnly}>{c.label}</th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each rows as r, i (r.franchise)}
          {@const tm = meta.teams[r.franchise]}
          <tr class:mine={r.mine}>
            <td class="rank num">{i + 1}</td>
            <td class="team">
              <span class="team-inner">
                <TeamLogo franchise={r.franchise} primary={tm?.primary} secondary={tm?.secondary} size={20} />
                <a href={r.href}>{r.abbr}</a>
                <span class="name">{r.name}</span>
              </span>
            </td>
            {#each columns as c (c.key)}
              {@const cell = r.cells[c.key]}
              <td
                class:num={c.numeric}
                class:wide={c.wideOnly}
                class:up={cell?.tone === 'up'}
                class:down={cell?.tone === 'down'}
                class:muted={cell?.tone === 'muted'}>{cell?.text ?? ''}</td
              >
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</details>

<style>
  .as-table {
    margin-top: var(--space-sm);
    min-width: 0;
  }
  summary {
    display: flex;
    align-items: center;
    min-block-size: var(--tap-min);
    font-size: var(--text-label);
    color: var(--text);
    cursor: pointer;
  }
  summary:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  .scroll {
    overflow-x: auto;
    min-width: 0;
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  th {
    padding: 0 var(--space-md) var(--space-sm);
    border-bottom: 1px solid var(--rule-strong);
    font-family: var(--font-mono);
    font-size: var(--text-micro);
    line-height: var(--lh-micro);
    font-weight: var(--weight-regular);
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--text-muted);
    text-align: left;
    white-space: nowrap;
  }
  td {
    padding: var(--space-sm) var(--space-md);
    border-bottom: 1px solid var(--border);
    font-size: var(--text-label);
    line-height: var(--lh-label);
    vertical-align: middle;
  }
  .num {
    text-align: right;
  }
  td.num {
    font-family: var(--font-mono);
    font-weight: var(--weight-regular);
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }
  td.rank {
    font-weight: var(--weight-semibold);
    color: var(--text-muted);
  }
  .team {
    max-width: 0;
    width: 100%;
  }
  .team-inner {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    min-width: 0;
  }
  .team a {
    flex: none;
    font-weight: var(--weight-bold);
    color: var(--accent);
  }
  .team a:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  .name {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text-muted);
  }
  .up {
    color: var(--up);
  }
  .down {
    color: var(--down);
  }
  .muted {
    color: var(--text-muted);
  }
  /* My team: the Phase 12 tint plus a 2px accent outline (BoardRow). */
  tr.mine {
    background: color-mix(in srgb, var(--accent) 6%, var(--bg));
    outline: 2px solid var(--accent);
    outline-offset: -2px;
  }
  @media (prefers-color-scheme: dark) {
    tr.mine {
      background: color-mix(in srgb, var(--accent) 8%, var(--bg));
    }
  }
  @media (max-width: 639px) {
    th,
    td {
      padding-inline: var(--space-sm);
    }
    .wide,
    .name {
      display: none;
    }
  }
</style>

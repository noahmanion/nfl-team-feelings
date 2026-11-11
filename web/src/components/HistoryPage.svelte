<script lang="ts">
  import HistoryChart from './HistoryChart.svelte'
  import StatusPanel from './StatusPanel.svelte'
  import { findSeason, loadHistory } from '../lib/data'
  import { weekLabel } from '../lib/format'
  import {
    currentPoint,
    defaultTeam,
    lowPoint,
    pickHighlight,
    seasonOf,
    seasonStarts,
    toRows,
    weekOf,
    type Point,
  } from '../lib/history'
  import { go, replace } from '../lib/route.svelte'
  import { historyHash, teamHash } from '../lib/router'
  import type { HistoryFile, Meta, Row } from '../lib/types'

  let { meta, latestRows, team }: { meta: Meta; latestRows: Row[]; team?: string } = $props()

  let history = $state<HistoryFile | null>(null)
  let failed = $state(false)
  let retry = $state(0)

  $effect(() => {
    void retry
    failed = false
    let live = true
    loadHistory(meta).then(
      (h) => {
        if (live) history = h
      },
      (err) => {
        console.error(err)
        if (live) failed = true
      },
    )
    return () => {
      live = false
    }
  })

  // Deep-linked team must exist in meta.teams; anything else falls back to #/history.
  const valid = $derived(!!team && Object.hasOwn(meta.teams, team))
  $effect(() => {
    if (team && !valid) replace(historyHash())
  })
  const selected = $derived((valid ? team : defaultTeam(latestRows)) ?? Object.keys(meta.teams)[0])
  const teamMeta = $derived(meta.teams[selected])

  const options = $derived(
    Object.entries(meta.teams)
      .map(([abbr, t]) => ({ abbr, name: t.name }))
      .sort((a, b) => a.name.localeCompare(b.name)),
  )

  // Track the colour scheme so band opacity and highlight contrast follow it.
  let dark = $state(false)
  $effect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    dark = mq.matches
    const onChange = () => (dark = mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  })

  const color = $derived.by(() => {
    void dark
    if (!teamMeta) return 'var(--text)'
    const bg = getComputedStyle(document.documentElement).getPropertyValue('--bg')
    const pick = pickHighlight(teamMeta.primary, teamMeta.secondary, bg, dark)
    return pick === 'primary' ? teamMeta.primary.trim() : pick === 'secondary' ? teamMeta.secondary.trim() : 'var(--text)'
  })

  const chart = $derived.by(() => {
    if (!history) return null
    const { rows, xs, xMax } = toRows(history)
    return { rows, xMax, starts: seasonStarts(history, xs) }
  })

  function when(p: Point): string {
    const s = seasonOf(p.key)
    const sm = findSeason(meta, s)
    return `${s} ${sm ? weekLabel(weekOf(p.key), sm) : `Week ${weekOf(p.key)}`}`
  }

  function bandLabel(score: number): string {
    return meta.bands.find((b) => score >= b.min && score <= b.max)?.label ?? ''
  }

  const summary = $derived.by(() => {
    if (!history || !teamMeta) return ''
    const now = currentPoint(history, selected)
    const low = lowPoint(history, selected)
    if (!now) return `${teamMeta.name}: no scores yet.`
    const label = latestRows.find((r) => r.franchise === selected)?.label ?? bandLabel(now.score)
    const lowText = low ? `; low ${Math.round(low.score)} (${when(low)})` : ''
    return `${teamMeta.name} now ${Math.round(now.score)}${label ? ` · ${label}` : ''}${lowText}`
  })
</script>

<section class="history" aria-labelledby="history-heading">
  <div class="top">
    <h2 id="history-heading">Mood over time</h2>
    <div class="picker">
      <label for="team-select">Highlight team</label>
      <select id="team-select" value={selected} onchange={(e) => go(historyHash(e.currentTarget.value))}>
        {#each options as o (o.abbr)}
          <option value={o.abbr}>{o.name}</option>
        {/each}
      </select>
    </div>
  </div>

  {#if failed}
    <StatusPanel
      variant="error"
      title="Couldn’t load the mood history"
      body="The history file didn’t load. Try again in a moment."
      actions={[{ label: 'Try again', onClick: () => retry++ }]}
    />
  {:else if chart && teamMeta}
    <p class="summary">{summary} <a href={teamHash(selected)}>See {teamMeta.name} →</a></p>
    <HistoryChart
      rows={chart.rows}
      xMax={chart.xMax}
      starts={chart.starts}
      team={selected}
      teamName={teamMeta.name}
      {color}
      bands={meta.bands}
      {dark}
    />
  {:else}
    <p class="loading" role="status">Loading mood history…</p>
  {/if}
</section>

<style>
  .history {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
    min-width: 0;
  }
  .top {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    justify-content: space-between;
    gap: var(--space-md);
  }
  h2 {
    font-size: var(--text-heading);
    line-height: var(--lh-heading);
    font-weight: var(--weight-semibold);
  }
  .picker {
    display: flex;
    flex-direction: column;
    gap: var(--space-xs);
    min-width: 0;
    flex: 0 1 auto;
  }
  label {
    color: var(--text-muted);
    font-size: var(--text-label);
    line-height: var(--lh-label);
  }
  select {
    min-width: 0;
    max-inline-size: 100%;
    block-size: var(--tap-min);
    padding: 0 var(--space-sm);
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    font: inherit;
  }
  select:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  .summary {
    font-size: var(--text-body);
    line-height: var(--lh-body);
  }
  .loading {
    color: var(--text-muted);
  }
</style>

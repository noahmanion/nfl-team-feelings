<script lang="ts">
  import * as Plot from '@observablehq/plot'
  import { moodToken } from '../lib/format'
  import { tickSeasons, type ChartRow, type SeasonStart } from '../lib/history'
  import type { Band } from '../lib/types'

  let {
    rows,
    xMax,
    starts,
    team,
    teamName,
    color,
    bands,
    dark = false,
  }: {
    rows: ChartRow[]
    xMax: number
    starts: SeasonStart[]
    team: string
    teamName: string
    color: string
    bands: Band[]
    dark?: boolean
  } = $props()

  let width = $state(0)
  let container: HTMLDivElement

  const highlightRows = $derived(rows.filter((r) => r.team === team))

  // Band labels live in a right gutter outside the plot area (never over the lines).
  // Below this width they are dropped and a compact legend under the chart takes over.
  const LABEL_MIN_WIDTH = 640
  const showBandLabels = $derived(width >= LABEL_MIN_WIDTH)
  const BAND_FONT_PX = 12
  const TEAM_FONT_PX = 14

  // Rendered text width in px; canvas measure with the container's font, else a rough estimate.
  function textWidth(texts: string[], px: number, weight = 400): number {
    const font = container ? getComputedStyle(container).fontFamily : 'sans-serif'
    const ctx = document.createElement('canvas').getContext('2d')
    if (ctx) ctx.font = `${weight} ${px}px ${font}`
    return Math.max(0, ...texts.map((t) => (ctx ? ctx.measureText(t).width : t.length * px * 0.6)))
  }

  $effect(() => {
    if (width <= 0) return
    const wide = width >= 500
    const ticks = tickSeasons(starts, width)
    const seasonAt = new Map(starts.map((d) => [d.x, d.season]))
    const bandRects = bands.map((b, i) => ({
      label: b.label,
      fill: `var(--mood-${moodToken(i, bands.length)})`,
      y1: b.min,
      y2: Math.min(100, b.max + 1),
      mid: (b.min + Math.min(100, b.max + 1)) / 2,
    }))
    const last = highlightRows.filter((r) => !Number.isNaN(r.y)).slice(-1)
    // Gutter = [team end-label column][band label column]. The team label always sits in its
    // own column just past the line end, so it can never run into a band label.
    const TEAM_DX = 6
    const GAP = 10
    const teamCol = Math.ceil(TEAM_DX + textWidth([team, 'WWW'], TEAM_FONT_PX, 600))
    const bandCol = showBandLabels ? Math.ceil(GAP + textWidth(bands.map((b) => b.label), BAND_FONT_PX) + 4) : 0

    const marks: Plot.Markish[] = [
      Plot.rect(bandRects, {
        x1: 0,
        x2: xMax,
        y1: 'y1',
        y2: 'y2',
        fill: 'fill',
        fillOpacity: dark ? 0.14 : 0.1,
      }),
    ]
    if (showBandLabels) {
      marks.push(
        Plot.text(bandRects, {
          x: xMax,
          y: 'mid',
          text: 'label',
          textAnchor: 'start',
          dx: teamCol + GAP,
          fontSize: BAND_FONT_PX,
          fill: 'var(--text-muted)',
          clip: false,
        }),
      )
    }
    marks.push(
      Plot.ruleX(starts.slice(1), {
        x: (d: SeasonStart) => d.x - 0.5,
        stroke: 'var(--border)',
        strokeDasharray: '2,3',
        strokeWidth: 1,
      }),
      Plot.ruleY([0], { stroke: 'var(--border)' }),
      Plot.line(rows, {
        x: 'x',
        y: 'y',
        z: 'team',
        stroke: 'var(--text-muted)',
        strokeOpacity: 0.25,
        strokeWidth: 1,
      }),
      Plot.line(highlightRows, { x: 'x', y: 'y', stroke: color, strokeWidth: 2.5 }),
      Plot.text(last, {
        x: 'x',
        y: 'y',
        text: () => team,
        dx: TEAM_DX,
        textAnchor: 'start',
        fill: 'var(--text)',
        fontSize: TEAM_FONT_PX,
        fontWeight: 600,
        clip: false,
      }),
    )

    const plot = Plot.plot({
      width,
      height: wide ? 400 : 280,
      marginLeft: 32,
      marginRight: teamCol + bandCol,
      style: { fontSize: '14px', color: 'var(--text-muted)', background: 'transparent', fontFamily: 'inherit' },
      x: {
        domain: [0, xMax],
        ticks: ticks.map((d) => d.x),
        tickFormat: (v: number) => {
          const s = seasonAt.get(v)
          if (s === undefined) return ''
          return wide ? String(s) : `’${String(s).slice(-2)}`
        },
        label: null,
      },
      y: { domain: [0, 100], ticks: [0, 20, 40, 60, 80, 100], tickFormat: (v: number) => String(Math.round(v)), label: null },
      marks,
    })
    plot.setAttribute('role', 'img')
    plot.setAttribute('aria-label', `Mood score over time for all teams since ${starts[0]?.season ?? 1999}, ${teamName} highlighted`)
    container.replaceChildren(plot)
    return () => plot.remove()
  })
</script>

<div class="chart" bind:clientWidth={width} bind:this={container}></div>
{#if width > 0 && !showBandLabels}
  <ul class="legend" aria-label="Mood bands">
    {#each bands as b, i (b.min)}
      <li>
        <span class="swatch" style:background={`var(--mood-${moodToken(i, bands.length)})`}></span>
        {b.min}–{b.max} {b.label}
      </li>
    {/each}
  </ul>
{/if}

<style>
  .chart {
    inline-size: 100%;
    min-width: 0;
    overflow: hidden;
  }
  .chart :global(svg) {
    display: block;
    max-inline-size: 100%;
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-xs) var(--space-sm);
    margin: 0;
    padding: 0;
    list-style: none;
    color: var(--text-muted);
    font-size: 12px;
    line-height: 1.4;
  }
  .legend li {
    display: inline-flex;
    align-items: center;
    gap: var(--space-xs);
  }
  .swatch {
    inline-size: 10px;
    block-size: 10px;
    border-radius: 2px;
    opacity: 0.6;
    flex: none;
  }
  /* axis tick lines in --border (presentation attributes lose to CSS) */
  .chart :global(g[aria-label$='-axis tick']) {
    stroke: var(--border);
  }
</style>

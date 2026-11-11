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
    const nearEnd = last.length > 0 && last[0].x > xMax * 0.95

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
    if (wide) {
      marks.push(
        Plot.text(bandRects, {
          x: xMax,
          y: 'mid',
          text: 'label',
          textAnchor: 'end',
          dx: -4,
          fill: 'var(--text-muted)',
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
        dx: nearEnd ? -6 : 6,
        dy: nearEnd ? -10 : 0,
        textAnchor: nearEnd ? 'end' : 'start',
        fill: 'var(--text)',
        fontWeight: 600,
      }),
    )

    const plot = Plot.plot({
      width,
      height: wide ? 400 : 280,
      marginLeft: 32,
      marginRight: wide ? 8 : 4,
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
  /* axis tick lines in --border (presentation attributes lose to CSS) */
  .chart :global(g[aria-label$='-axis tick']) {
    stroke: var(--border);
  }
</style>

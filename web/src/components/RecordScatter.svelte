<script lang="ts">
  import * as Plot from '@observablehq/plot'
  import { chartHeight, recordTip, type Line, type RecordPoint } from '../lib/explore'
  import { moodToken } from '../lib/format'
  import { highlightColor } from '../lib/history'
  import { CHART_FONT_PX, baseAxis, valueAxis, withTheme } from '../lib/plotTheme'
  import { go } from '../lib/route.svelte'
  import { teamHash } from '../lib/router'
  import { attachClick, logoMarks } from '../lib/scatterMarks'
  import type { Band, Meta } from '../lib/types'

  let {
    points,
    line,
    bands,
    season,
    week,
    latest,
    pinned,
    dark = false,
    meta,
    ariaLabel,
  }: {
    points: RecordPoint[]
    line: Line | null
    bands: Band[]
    season: number
    week: number
    latest: boolean
    pinned: string | null
    dark?: boolean
    meta: Meta
    ariaLabel: string
  } = $props()

  let width = $state(0)
  let container: HTMLDivElement

  // Band labels sit in a right gutter at >= 640 (as on HistoryChart); below that the tip carries the mood.
  const LABEL_MIN_WIDTH = 640
  const GUTTER_DX = 10

  // The gutter is measured with canvas text metrics, so re-measure once the web fonts have loaded.
  let fontsTick = $state(0)
  $effect(() => {
    let live = true
    document.fonts?.ready.then(() => {
      if (live) fontsTick++
    })
    return () => {
      live = false
    }
  })

  // Rendered text width in px; canvas measure with the container's font, else a rough estimate.
  function textWidth(texts: string[], px: number, weight = 400): number {
    const font = container ? getComputedStyle(container).fontFamily : 'sans-serif'
    const ctx = document.createElement('canvas').getContext('2d')
    if (ctx) ctx.font = `${weight} ${px}px ${font}`
    return Math.max(0, ...texts.map((t) => (ctx ? ctx.measureText(t).width : t.length * px * 0.6)))
  }

  const pct0 = (v: number) => `${Math.round(v * 100)}%`

  $effect(() => {
    if (width <= 0 || points.length === 0) return
    void fontsTick
    const size = width >= 640 ? 28 : 20
    const pinSize = size + 8
    const inset = pinSize / 2 + 4
    const pin = pinned ? points.find((p) => p.franchise === pinned) : undefined
    const others = pin ? points.filter((p) => p.franchise !== pin.franchise) : points
    const colorOf = (F: string) => meta.teams[F]?.primary ?? ''
    const showBandLabels = width >= LABEL_MIN_WIDTH

    const bandRects = bands.map((b, i) => {
      const y2 = Math.min(100, b.max + 1)
      return { label: b.label, fill: `var(--mood-${moodToken(i, bands.length)})`, y1: b.min, y2, mid: (b.min + y2) / 2 }
    })
    const marginRight = showBandLabels
      ? Math.ceil(16 + textWidth(bands.map((b) => b.label), CHART_FONT_PX) + GUTTER_DX)
      : 16

    const marks: Plot.Markish[] = [
      // No x channel: each band spans the full frame width (x [0, 1] plus the logo inset).
      Plot.rect(bandRects, { y1: 'y1', y2: 'y2', fill: 'fill', fillOpacity: dark ? 0.14 : 0.1 }),
    ]
    if (showBandLabels) {
      marks.push(
        Plot.text(bandRects, {
          frameAnchor: 'right',
          y: 'mid',
          text: 'label',
          textAnchor: 'start',
          dx: GUTTER_DX,
          fontSize: CHART_FONT_PX,
          fill: 'var(--text-muted)',
          clip: false,
        }),
      )
    }
    if (line) {
      const xs = points.map((p) => p.x)
      const x0 = Math.min(...xs)
      const x1 = Math.max(...xs)
      const at = (x: number) => line.a + line.b * x
      const seg = [{ x1: x0, y1: at(x0), x2: x1, y2: at(x1) }]
      marks.push(
        Plot.link(seg, {
          x1: 'x1',
          y1: 'y1',
          x2: 'x2',
          y2: 'y2',
          stroke: 'var(--text-muted)',
          strokeWidth: 1.5,
          strokeDasharray: '4,3',
        }),
      )
      // The line is keyed in HTML above the chart (UI review #1): an in-plot label collided with top logos.
      marks.push(
        Plot.text(['BETTER THAN THEIR RECORD'], {
          text: (d: string) => d,
          frameAnchor: 'top-left',
          textAnchor: 'start',
          dx: 8,
          dy: 8,
          fontSize: CHART_FONT_PX,
          fill: 'var(--text-muted)',
        }),
        Plot.text(['WORSE THAN THEIR RECORD'], {
          text: (d: string) => d,
          frameAnchor: 'bottom-right',
          textAnchor: 'end',
          dx: -8,
          dy: -8,
          fontSize: CHART_FONT_PX,
          fill: 'var(--text-muted)',
        }),
      )
    }
    marks.push(...logoMarks(others, { x: 'x', y: 'y', size, opacity: pin ? 0.5 : 1, dark, colorOf }))
    if (pin) {
      const t = meta.teams[pin.franchise]
      const bg = getComputedStyle(document.documentElement).getPropertyValue('--bg')
      const ring = highlightColor(t?.primary ?? '', t?.secondary ?? '', bg, dark)
      marks.push(
        ...logoMarks([pin], { x: 'x', y: 'y', size: pinSize, opacity: 1, dark, ringColor: ring, colorOf, pinnedText: true }),
      )
    }
    marks.push(
      Plot.tip(
        points,
        Plot.pointer({
          x: 'x',
          y: 'y',
          title: recordTip,
          maxRadius: size / 2 + 6,
          fill: 'var(--bg)',
          stroke: 'var(--border)',
          fontSize: CHART_FONT_PX,
        }),
      ),
    )

    const plot = Plot.plot(
      withTheme({
        width,
        height: chartHeight(width),
        marginTop: 28,
        marginRight,
        marginBottom: 36,
        marginLeft: 48,
        x: baseAxis({
          domain: [0, 1],
          inset,
          ticks: [0, 0.25, 0.5, 0.75, 1],
          tickFormat: pct0,
          label: 'Win % →',
          labelAnchor: 'right',
          labelArrow: 'none',
        }),
        y: valueAxis({
          domain: [0, 100],
          inset,
          ticks: [0, 20, 40, 60, 80, 100],
          tickFormat: (v: number) => String(Math.round(v)),
          label: '↑ Feel-good score',
          labelAnchor: 'top',
          labelArrow: 'none',
        }),
        marks,
      }),
    )
    plot.setAttribute('role', 'img')
    plot.setAttribute('aria-label', ariaLabel)
    plot.setAttribute('tabindex', '-1')
    attachClick<RecordPoint>(plot, (d) => (latest ? teamHash(d.franchise) : teamHash(d.franchise, season, week)), go)
    container.replaceChildren(plot)
    return () => plot.remove()
  })
</script>

{#if line}
  <p class="key"><svg width="24" height="8" aria-hidden="true"><line x1="0" y1="4" x2="24" y2="4" /></svg>Typical score for this record</p>
{/if}
<div class="chart" bind:clientWidth={width} bind:this={container}></div>

<style>
  .key {
    display: flex;
    align-items: center;
    gap: var(--space-xs);
    margin: 0 0 var(--space-xs);
    font-family: var(--font-mono);
    font-size: var(--text-micro);
    color: var(--text-muted);
  }
  .key line {
    stroke: var(--text-muted);
    stroke-width: 1.5;
    stroke-dasharray: 4 3;
  }
  .chart {
    font-family: var(--font-mono);
    inline-size: 100%;
    min-width: 0;
    overflow: hidden;
  }
  .chart :global(svg) {
    display: block;
    max-inline-size: 100%;
  }
</style>

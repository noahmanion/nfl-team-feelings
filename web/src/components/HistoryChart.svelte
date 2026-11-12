<script lang="ts">
  import * as Plot from '@observablehq/plot'
  import { moodToken } from '../lib/format'
  import { logoSrc, logosEnabled } from '../lib/logos'
  import {
    BACKGROUND_STROKE,
    CHART_FONT_PX,
    HIGHLIGHT_WIDTH,
    LABEL_FONT_PX,
    LOGO_MARK_PX,
    baseAxis,
    teamStroke,
    valueAxis,
    withTheme,
  } from '../lib/plotTheme'
  import { tickSeasons, type ChartRow, type Connector, type SeasonStart } from '../lib/history'
  import type { Band } from '../lib/types'

  let {
    rows,
    xMax,
    starts,
    connectors = [],
    team,
    teamName,
    color,
    bands,
    dark = false,
  }: {
    rows: ChartRow[]
    xMax: number
    starts: SeasonStart[]
    connectors?: Connector[]
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
  const BAND_FONT_PX = CHART_FONT_PX
  const TEAM_FONT_PX = LABEL_FONT_PX

  // Gutters are measured with canvas text metrics, so re-measure once the web fonts have loaded.
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

  // D-11 (WR-04): only draw the line-end logo once its image has actually loaded. A 404 or blocked
  // image would otherwise leave an empty disc, a gap before the label and a widened gutter.
  const logoUrl = $derived(logosEnabled() ? logoSrc(team) : null)
  let logoOk = $state<string | null>(null)
  $effect(() => {
    const s = logoUrl
    if (!s) return
    let live = true
    const img = new Image()
    img.onload = () => {
      if (live) logoOk = s
    }
    img.onerror = () => {
      if (live && logoOk === s) logoOk = null
    }
    img.src = s
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

  $effect(() => {
    if (width <= 0) return
    void fontsTick
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
    // One small logo at the highlighted line's last point (D-10); the label sits just past it.
    const logoPx = width >= 900 ? 24 : LOGO_MARK_PX
    const src = logoUrl
    const drawLogo = !!src && src === logoOk && last.length > 0
    const labelDx = drawLogo ? logoPx / 2 + 4 : TEAM_DX
    const teamCol = Math.ceil(TEAM_DX + textWidth([team, 'WWW'], TEAM_FONT_PX, 600) + (drawLogo ? logoPx + 4 : 0))
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
      Plot.line(rows, {
        x: 'x',
        y: 'y',
        z: 'team',
        stroke: BACKGROUND_STROKE,
        // 31 background lines; scale ink with width so they stay a texture, not a grey mass.
        strokeOpacity: width >= 900 ? 0.16 : wide ? 0.12 : 0.08,
        strokeWidth: width >= 900 ? 0.75 : wide ? 0.6 : 0.5,
      }),
      Plot.line(highlightRows, { x: 'x', y: 'y', stroke: teamStroke(color), strokeWidth: HIGHLIGHT_WIDTH }),
      // Offseason move (regression + draft): dashed, across the season gap, highlighted team only.
      Plot.link(connectors, {
        x1: 'x1',
        y1: 'y1',
        x2: 'x2',
        y2: 'y2',
        stroke: teamStroke(color),
        strokeWidth: 1.5,
        strokeDasharray: '3,3',
        strokeOpacity: 0.8,
      }),
    )
    if (drawLogo) {
      // Dark mode: logos sit on a light disc so dark marks stay legible.
      if (dark) marks.push(Plot.dot(last, { x: 'x', y: 'y', r: logoPx / 2, fill: 'var(--logo-disc)', stroke: 'none' }))
      marks.push(Plot.image(last, { x: 'x', y: 'y', src: () => src, width: dark ? logoPx * 0.76 : logoPx }))
    }
    marks.push(
      Plot.text(last, {
        x: 'x',
        y: 'y',
        text: () => team,
        dx: labelDx,
        textAnchor: 'start',
        fill: 'var(--text)',
        fontSize: TEAM_FONT_PX,
        fontWeight: 600,
        clip: false,
      }),
    )

    const plot = Plot.plot(
      withTheme({
        width,
        height: wide ? 400 : 280,
        marginLeft: 32,
        marginRight: teamCol + bandCol,
        // room for the end-of-line logo when the team ends at y=100 (12-UI-REVIEW #7)
        marginTop: drawLogo ? 24 : undefined,
        x: baseAxis({
          domain: [0, xMax],
          ticks: ticks.map((d) => d.x),
          tickFormat: (v: number) => {
            const s = seasonAt.get(v)
            if (s === undefined) return ''
            return wide ? String(s) : `’${String(s).slice(-2)}`
          },
        }),
        y: valueAxis({ domain: [0, 100], ticks: [0, 20, 40, 60, 80, 100], tickFormat: (v: number) => String(Math.round(v)) }),
        marks,
      }),
    )
    plot.setAttribute('role', 'img')
    plot.setAttribute('aria-label', `Mood score over time for all teams since ${starts[0]?.season ?? 1999}, ${teamName} highlighted, dashed segments mark offseason changes`)
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
    font-family: var(--font-mono);
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
    font-family: var(--font-mono);
    font-size: var(--text-micro);
    line-height: 1.4;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .legend li {
    display: inline-flex;
    align-items: center;
    gap: var(--space-xs);
  }
  .swatch {
    inline-size: 10px;
    block-size: 10px;
    border-radius: 0;
    opacity: 0.6;
    flex: none;
  }
</style>

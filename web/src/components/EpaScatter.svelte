<script lang="ts">
  import * as Plot from '@observablehq/plot'
  import { chartHeight, diagonals, epaTicks, epaTip, paddedDomain, signed, type EpaPoint } from '../lib/explore'
  import { highlightColor } from '../lib/history'
  import { CHART_FONT_PX, baseAxis, withTheme } from '../lib/plotTheme'
  import { go } from '../lib/route.svelte'
  import { teamHash } from '../lib/router'
  import { attachClick, logoMarks } from '../lib/scatterMarks'
  import type { Meta } from '../lib/types'

  let {
    points,
    means,
    season,
    week,
    latest,
    pinned,
    dark = false,
    meta,
    ariaLabel,
  }: {
    points: EpaPoint[]
    means: { off: number; def: number }
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

  const QUADRANTS = [
    { text: 'GOOD AT BOTH', frameAnchor: 'top-right', textAnchor: 'end', dx: -8, dy: 8 },
    { text: 'ALL OFFENSE', frameAnchor: 'bottom-right', textAnchor: 'end', dx: -8, dy: -8 },
    { text: 'ALL DEFENSE', frameAnchor: 'top-left', textAnchor: 'start', dx: 8, dy: 8 },
    { text: 'STRUGGLING ON BOTH', frameAnchor: 'bottom-left', textAnchor: 'start', dx: 8, dy: -8 },
  ] as const

  $effect(() => {
    if (width <= 0 || points.length === 0) return
    const size = width >= 640 ? 28 : 20
    const pinSize = size + 8
    const inset = pinSize / 2 + 4
    const pin = pinned ? points.find((p) => p.franchise === pinned) : undefined
    const others = pin ? points.filter((p) => p.franchise !== pin.franchise) : points

    const offs = points.map((p) => p.off).concat(means.off)
    const defs = points.map((p) => p.def).concat(means.def)
    const xd = paddedDomain(Math.min(...offs), Math.max(...offs))
    const yd = paddedDomain(Math.min(...defs), Math.max(...defs))
    const tick = (v: number) => signed(v, 2)
    const colorOf = (F: string) => meta.teams[F]?.primary ?? ''

    const marks: Plot.Markish[] = [
      Plot.link(diagonals(xd, yd), { x1: 'x1', y1: 'y1', x2: 'x2', y2: 'y2', stroke: 'var(--grid)', strokeWidth: 1, clip: true }),
      Plot.ruleX([means.off], { stroke: 'var(--text-muted)', strokeWidth: 1, strokeDasharray: '4,3' }),
      Plot.ruleY([means.def], { stroke: 'var(--text-muted)', strokeWidth: 1, strokeDasharray: '4,3' }),
    ]
    if (width >= 400) {
      for (const q of QUADRANTS) {
        marks.push(
          Plot.text([q.text], {
            text: (d: string) => d,
            frameAnchor: q.frameAnchor,
            textAnchor: q.textAnchor,
            dx: q.dx,
            dy: q.dy,
            fontSize: CHART_FONT_PX,
            fill: 'var(--text-muted)',
          }),
        )
      }
    }
    marks.push(...logoMarks(others, { x: 'off', y: 'def', size, opacity: pin ? 0.5 : 1, dark, colorOf }))
    if (pin) {
      const t = meta.teams[pin.franchise]
      const bg = getComputedStyle(document.documentElement).getPropertyValue('--bg')
      const ring = highlightColor(t?.primary ?? '', t?.secondary ?? '', bg, dark)
      marks.push(
        ...logoMarks([pin], { x: 'off', y: 'def', size: pinSize, opacity: 1, dark, ringColor: ring, colorOf, pinnedText: true }),
      )
    }
    marks.push(
      Plot.tip(
        points,
        Plot.pointer({
          x: 'off',
          y: 'def',
          title: epaTip,
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
        marginRight: 16,
        marginBottom: 36,
        marginLeft: 48,
        x: baseAxis({
          domain: xd,
          inset,
          ticks: epaTicks(xd, width),
          tickFormat: tick,
          label: 'Offense EPA/play →',
          labelAnchor: 'right',
          labelArrow: 'none',
        }),
        y: baseAxis({
          domain: yd,
          reverse: true,
          inset,
          ticks: epaTicks(yd, width),
          tickFormat: tick,
          label: '↑ Defense, EPA/play allowed (flipped)',
          labelAnchor: 'top',
          labelArrow: 'none',
        }),
        marks,
      }),
    )
    plot.setAttribute('role', 'img')
    plot.setAttribute('aria-label', ariaLabel)
    plot.setAttribute('tabindex', '-1')
    attachClick<EpaPoint>(plot, (d) => (latest ? teamHash(d.franchise) : teamHash(d.franchise, season, week)), go)
    container.replaceChildren(plot)
    return () => plot.remove()
  })
</script>

<div class="chart" bind:clientWidth={width} bind:this={container}></div>

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
</style>

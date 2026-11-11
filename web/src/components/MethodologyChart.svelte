<script lang="ts">
  import * as Plot from '@observablehq/plot'
  import { formatMetric, type ChartMetric, type ChartRow, xDomain } from '../lib/methodology'

  let {
    rows,
    metric,
    label,
    eloRef = 'elo',
  }: {
    rows: ChartRow[]
    metric: ChartMetric
    /** Accessible name prefix, e.g. "Rank correlation". */
    label: string
    /** Candidate key drawn as the dashed reference line in each period. */
    eloRef?: string
  } = $props()

  let width = $state(0)
  let container: HTMLDivElement

  const axisLabel = $derived(
    metric === 'brier' ? 'Next-game Brier score (lower is better)' : 'Rank correlation with the next 8 games (higher is better)',
  )

  // narrow screens wrap candidate names onto two lines, so rows need more room
  const rowPx = (w: number) => (w < 500 ? 40 : 30)
  const FONT_PX = 14

  $effect(() => {
    if (width <= 0 || rows.length === 0) return
    const periods = [...new Set(rows.map((r) => r.period))]
    const labels = [...new Set(rows.map((r) => r.label))]
    const refs = rows.filter((r) => r.key === eloRef)
    const marginLeft = width < 500 ? 120 : 150
    const dp = metric === 'brier' ? 3 : 2

    const plot = Plot.plot({
      width,
      height: periods.length * (labels.length * rowPx(width) + 36) + 40,
      marginLeft,
      marginRight: 16,
      marginTop: 28,
      style: { fontSize: `${FONT_PX}px`, color: 'var(--text-muted)', background: 'transparent', fontFamily: 'inherit' },
      x: { domain: xDomain(rows), label: null, ticks: width < 500 ? 4 : 6, tickFormat: (v: number) => formatMetric(v, dp) },
      y: { domain: labels, label: null, axis: null },
      fy: { domain: periods, label: null, axis: null, padding: 0.22 },
      marks: [
        Plot.gridX({ stroke: 'var(--border)', strokeOpacity: 1, ticks: width < 500 ? 4 : 6 }),
        Plot.axisY({
          tickSize: 0,
          // wrap long candidate names into the left margin instead of clipping them
          lineWidth: (marginLeft - 12) / FONT_PX,
          fill: 'var(--text-muted)',
        }),
        Plot.text(periods, {
          fy: (d: string) => d,
          text: (d: string) => d,
          frameAnchor: 'top-left',
          dx: -marginLeft,
          dy: -20,
          fill: 'var(--text)',
          fontWeight: 600,
          clip: false,
        }),
        Plot.ruleX(refs, { x: 'value', fy: 'period', stroke: 'var(--border)', strokeWidth: 1.5, strokeDasharray: '4,3' }),
        Plot.ruleY(rows, { x1: 'lo', x2: 'hi', y: 'label', fy: 'period', stroke: 'var(--text-muted)', strokeWidth: 1.5 }),
        Plot.dot(rows, {
          x: 'value',
          y: 'label',
          fy: 'period',
          r: 4,
          fill: (d: ChartRow) => (d.key === 'composite' ? 'var(--accent)' : 'var(--text-muted)'),
          stroke: 'none',
        }),
      ],
    })
    const summary = periods
      .map((p) => {
        const c = rows.find((r) => r.period === p && r.key === 'composite')
        const e = rows.find((r) => r.period === p && r.key === eloRef)
        return `${p}: feel-good score ${formatMetric(c?.value, 3)}, Elo alone ${formatMetric(e?.value, 3)}`
      })
      .join('; ')
    plot.setAttribute('role', 'img')
    plot.setAttribute('aria-label', `${label}. ${axisLabel}. ${summary}.`)
    container.replaceChildren(plot)
    return () => plot.remove()
  })
</script>

<figure class="figure">
  <div class="chart" bind:clientWidth={width} bind:this={container}></div>
  <figcaption>{axisLabel}. Dots are the value, whiskers the 95% interval; the dashed line marks Elo alone.</figcaption>
</figure>

<style>
  .figure {
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-xs);
  }
  .chart {
    inline-size: 100%;
    min-width: 0;
    overflow: hidden;
  }
  .chart :global(svg) {
    display: block;
    max-inline-size: 100%;
  }
  .chart :global(g[aria-label$='-axis tick']) {
    stroke: var(--border);
  }
  figcaption {
    color: var(--text-muted);
    font-size: var(--text-label);
    line-height: var(--lh-label);
  }
</style>

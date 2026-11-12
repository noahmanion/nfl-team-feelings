<script lang="ts">
  import * as Plot from '@observablehq/plot'
  import { formatMetric, type ChartMetric, type ChartRow, xDomain } from '../lib/methodology'
  import { CHART_FONT_PX, valueAxis, withTheme } from '../lib/plotTheme'
  import ChartFrame from './ChartFrame.svelte'

  let {
    rows,
    metric,
    label,
    intervalNote = 'Whiskers are 95% bootstrap intervals.',
    eloRef = 'elo',
  }: {
    rows: ChartRow[]
    metric: ChartMetric
    /** Accessible name prefix, e.g. "Rank correlation". */
    label: string
    /** Sentence naming the interval method(s) behind the whiskers (WR-04). */
    intervalNote?: string
    /** Candidate key drawn as the dashed reference line in each period. */
    eloRef?: string
  } = $props()

  let width = $state(0)
  let container: HTMLDivElement

  const axisLabel = $derived(
    metric === 'brier' ? 'Next-game Brier score (lower is better)' : 'Rank correlation with the next 8 games (higher is better)',
  )

  const headline = $derived(
    metric === 'spearman_n8'
      ? 'Which method ranks teams best'
      : metric === 'brier'
        ? 'Which method calls single games best'
        : label,
  )
  const dek = $derived(
    metric === 'spearman_n8'
      ? 'Rank correlation with each team’s next 8 games, by test period. Higher is better.'
      : metric === 'brier'
        ? 'Next-game Brier score, by test period. Lower is better.'
        : axisLabel,
  )

  // narrow screens wrap candidate names onto two lines, so rows need more room
  const rowPx = (w: number) => (w < 500 ? 40 : 30)
  const FONT_PX = CHART_FONT_PX

  $effect(() => {
    if (width <= 0 || rows.length === 0) return
    const periods = [...new Set(rows.map((r) => r.period))]
    const labels = [...new Set(rows.map((r) => r.label))]
    const refs = rows.filter((r) => r.key === eloRef)
    const marginLeft = width < 500 ? 120 : 150
    const dp = metric === 'brier' ? 3 : 2

    const plot = Plot.plot(
      withTheme({
        width,
        height: periods.length * (labels.length * rowPx(width) + 36) + 40,
        marginLeft,
        marginRight: 16,
        marginTop: 28,
        // valueAxis turns the x grid on; the global app.css rule paints it solid in --grid (D-28).
        x: valueAxis({ domain: xDomain(rows), ticks: width < 500 ? 4 : 6, tickFormat: (v: number) => formatMetric(v, dp) }),
        y: { domain: labels, label: null, axis: null },
        fy: { domain: periods, label: null, axis: null, padding: 0.22 },
        marks: [
          Plot.axisY({
            tickSize: 0,
            // wrap long candidate names into the left margin instead of clipping them
            lineWidth: (marginLeft - 12) / FONT_PX,
            // the theme font is mono, so wrap with monospace metrics
            monospace: true,
            fontFamily: 'var(--font-mono)',
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
          Plot.ruleX(refs, { x: 'value', fy: 'period', stroke: 'var(--text-muted)', strokeWidth: 1.5, strokeDasharray: '4,3' }),
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
      }),
    )
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

<ChartFrame
  id={`method-${metric}`}
  level={3}
  {headline}
  {dek}
  notes={`Dots are the value; the dashed line marks Elo alone. ${intervalNote}`}
>
  <div class="chart" bind:clientWidth={width} bind:this={container}></div>
</ChartFrame>

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
</style>

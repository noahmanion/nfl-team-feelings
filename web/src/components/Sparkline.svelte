<script lang="ts">
  import * as Plot from '@observablehq/plot'
  import { pickHighlight } from '../lib/history'
  import { sparkDomain } from '../lib/team'

  let {
    series,
    primary,
    secondary,
    baseline = 50,
  }: { series: { week: number; score: number }[]; primary?: string; secondary?: string; baseline?: number } =
    $props()

  const HEIGHT = 80

  let width = $state(0)
  let container = $state<HTMLDivElement>()

  // Follow the colour scheme so the line keeps 3:1 contrast against --bg.
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
    if (!primary || !secondary) return 'var(--text)'
    const bg = getComputedStyle(document.documentElement).getPropertyValue('--bg')
    const pick = pickHighlight(primary, secondary, bg, dark)
    return pick === 'primary' ? primary.trim() : pick === 'secondary' ? secondary.trim() : 'var(--text)'
  })

  const label = $derived(
    series.length >= 2 ? `Score this season: from ${series[0].score} to ${series[series.length - 1].score} (low ${Math.min(...series.map((p) => p.score))}, high ${Math.max(...series.map((p) => p.score))})` : '',
  )

  $effect(() => {
    if (!container || width <= 0 || series.length < 2) return
    // Padded domain around the season's range; the min/max labels keep the zoomed scale honest.
    const { lo, hi, domain } = sparkDomain(series)
    const x0 = series[0].week
    const extremes = hi === lo ? [{ week: x0, score: hi }] : [{ week: x0, score: hi }, { week: x0, score: lo }]
    const plot = Plot.plot({
      width,
      height: HEIGHT,
      margin: 6,
      marginLeft: 28,
      axis: null,
      x: { domain: [x0, series[series.length - 1].week] },
      y: { domain },
      style: { background: 'transparent' },
      marks: [
        // "average team" reference, only when it falls inside the zoomed range
        ...(baseline >= domain[0] && baseline <= domain[1]
          ? [Plot.ruleY([baseline], { stroke: 'var(--border)', strokeDasharray: '2,3' })]
          : []),
        Plot.lineY(series, { x: 'week', y: 'score', stroke: color, strokeWidth: 2 }),
        Plot.dot(series.slice(-1), { x: 'week', y: 'score', fill: color, r: 3 }),
        Plot.text(extremes, {
          x: 'week',
          y: 'score',
          text: (d: { score: number }) => String(d.score),
          textAnchor: 'end',
          dx: -6,
          fill: 'var(--text-muted)',
          fontSize: 11,
          fontVariant: 'tabular-nums',
        }),
      ],
    })
    plot.setAttribute('aria-hidden', 'true')
    container.replaceChildren(plot)
    return () => plot.remove()
  })
</script>

{#if series.length >= 2}
  <div class="spark" role="img" aria-label={label} bind:clientWidth={width} bind:this={container}></div>
{/if}

<style>
  .spark {
    inline-size: 100%;
    min-width: 0;
    block-size: 80px;
    overflow: hidden;
  }
  .spark :global(svg) {
    display: block;
    max-inline-size: 100%;
  }
</style>

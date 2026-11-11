<script lang="ts">
  import * as Plot from '@observablehq/plot'
  import { pickHighlight } from '../lib/history'

  let {
    series,
    primary,
    secondary,
  }: { series: { week: number; score: number }[]; primary?: string; secondary?: string } = $props()

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
    series.length >= 2 ? `Score this season: from ${series[0].score} to ${series[series.length - 1].score}` : '',
  )

  $effect(() => {
    if (!container || width <= 0 || series.length < 2) return
    const plot = Plot.plot({
      width,
      height: 48,
      margin: 4,
      axis: null,
      x: { domain: [series[0].week, series[series.length - 1].week] },
      y: { domain: [0, 100] },
      style: { background: 'transparent' },
      marks: [
        Plot.ruleY([50], { stroke: 'var(--border)' }),
        Plot.lineY(series, { x: 'week', y: 'score', stroke: color, strokeWidth: 2 }),
        Plot.dot(series.slice(-1), { x: 'week', y: 'score', fill: color, r: 3 }),
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
    block-size: 48px;
    overflow: hidden;
  }
  .spark :global(svg) {
    display: block;
    max-inline-size: 100%;
  }
</style>

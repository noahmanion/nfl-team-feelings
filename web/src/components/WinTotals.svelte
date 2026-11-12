<script lang="ts">
  import ChartFrame from './ChartFrame.svelte'
  import { highlightColor } from '../lib/history'
  import type { TeamFile } from '../lib/types'
  import { winTotalsView } from '../lib/winTotals'

  // DATA-03 (D-19): preseason Vegas line and model expectation against the actual pace, on an
  // HTML number line (0..reg_games) with a legend. All copy and positions come from winTotalsView.
  let {
    file,
    loading,
    season,
    rec,
    primary,
    secondary,
  }: {
    file: TeamFile | null
    loading: boolean
    season: number
    rec: { wins: number; losses: number; ties: number } | null
    primary: string
    secondary: string
  } = $props()

  const view = $derived(file ? winTotalsView(file, season, rec) : null)
  const byKey = (key: 'vegas' | 'model' | 'pace') => view?.rows.find((r) => r.key === key && r.pos !== null) ?? null
  const vegas = $derived(byKey('vegas'))
  const model = $derived(byKey('model'))
  const paceRow = $derived(byKey('pace'))

  // Track the colour scheme so the pace dot keeps contrast (same pattern as HistoryPage).
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
    if (typeof document === 'undefined') return 'var(--text)'
    const bg = getComputedStyle(document.documentElement).getPropertyValue('--bg')
    return highlightColor(primary, secondary, bg, dark)
  })

  const HEADLINE = 'Preseason expectations'
  const tickClass = (i: number, n: number) => (i === 0 ? 'first' : i === n - 1 ? 'last' : '')
</script>

{#if loading}
  <ChartFrame id="expect-heading" level={3} headline={HEADLINE}>
    <p class="loading" role="status">Loading expectations…</p>
  </ChartFrame>
{:else if view}
  <ChartFrame
    id="expect-heading"
    level={3}
    headline={HEADLINE}
    dek={view.dek}
    notes={view.notes}
    source={view.source}
  >
    <div class="numline" aria-hidden="true">
      <span class="track"></span>
      {#if model}<span class="mk ring" style:left="{model.pos}%"></span>{/if}
      {#if vegas}<span class="mk bar" style:left="{vegas.pos}%"></span>{/if}
      {#if paceRow}<span class="mk dot" style:left="{paceRow.pos}%" style:--dot={color}></span>{/if}
      {#each view.ticks as t, i (t)}
        <span class="tick {tickClass(i, view.ticks.length)}" style:left="{(t / view.regGames) * 100}%">{t}</span>
      {/each}
    </div>
    <ul class="legend">
      {#each view.rows as r (r.key)}
        <li>
          <span class="glyph" aria-hidden="true">
            {#if r.pos !== null}
              <span class="g {r.key === 'vegas' ? 'bar' : r.key === 'model' ? 'ring' : 'dot'}" style:--dot={color}></span>
            {/if}
          </span>
          <span class="label">{r.label}{#if r.suffix}<span class="suffix">{r.suffix}</span>{/if}</span>
          <span class="value num">{r.value}</span>
        </li>
      {/each}
    </ul>
  </ChartFrame>
{/if}

<style>
  .loading {
    color: var(--text-muted);
    font-size: var(--text-label);
    line-height: var(--lh-label);
  }
  .numline {
    position: relative;
    block-size: 40px;
    inline-size: 100%;
  }
  .track {
    position: absolute;
    inset-inline: 0;
    top: 11px;
    block-size: 2px;
    background: var(--border);
  }
  .mk {
    position: absolute;
    top: 12px;
    transform: translate(-50%, -50%);
    box-sizing: border-box;
  }
  .ring,
  .g.ring {
    inline-size: 12px;
    block-size: 12px;
    border-radius: 50%;
    border: 2px solid var(--text-muted);
    background: var(--bg);
  }
  .bar {
    inline-size: 2px;
    block-size: 20px;
    background: var(--text);
  }
  .g.bar {
    block-size: 12px;
  }
  .dot,
  .g.dot {
    inline-size: 12px;
    block-size: 12px;
    border-radius: 50%;
    background: var(--dot);
  }
  .tick {
    position: absolute;
    top: 24px;
    transform: translateX(-50%);
    font-family: var(--font-mono);
    font-size: var(--text-micro);
    line-height: 1;
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;
  }
  .tick.first {
    transform: none;
  }
  .tick.last {
    transform: translateX(-100%);
  }
  .legend {
    margin: var(--space-md) 0 0;
    padding: 0;
    list-style: none;
  }
  .legend li {
    display: grid;
    grid-template-columns: 16px minmax(0, 1fr) auto;
    column-gap: var(--space-sm);
    align-items: baseline;
    padding: var(--space-sm) 0;
    border-bottom: 1px solid var(--border);
  }
  .glyph {
    display: flex;
    align-items: center;
    justify-content: center;
    align-self: center;
    block-size: 16px;
  }
  .g {
    display: block;
    box-sizing: border-box;
  }
  .label {
    min-width: 0;
    font-size: var(--text-label);
    line-height: var(--lh-label);
    color: var(--text);
    overflow-wrap: anywhere;
  }
  .suffix {
    color: var(--text-muted);
  }
  .value {
    font-family: var(--font-mono);
    font-size: var(--text-label);
    line-height: var(--lh-label);
    font-weight: var(--weight-semibold);
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
</style>

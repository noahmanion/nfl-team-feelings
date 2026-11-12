<script lang="ts">
  import Badge from './Badge.svelte'
  import { findSeason } from '../lib/data'
  import { tickLabel, weekLabel } from '../lib/format'
  import type { Meta } from '../lib/types'

  let {
    meta,
    season,
    week,
    isLatest,
    partial,
    disabled = false,
    onSeasonChange,
    onWeekInput,
    onLatest,
  }: {
    meta: Meta | null
    season: number
    week: number
    isLatest: boolean
    partial: boolean
    disabled?: boolean
    onSeasonChange: (season: number) => void
    onWeekInput: (week: number) => void
    onLatest: () => void
  } = $props()

  const seasons = $derived(meta ? [...meta.seasons].sort((a, b) => b.season - a.season) : [])
  const seasonMeta = $derived(meta ? findSeason(meta, season) : undefined)
  const maxWeek = $derived(seasonMeta?.max_week ?? 0)
  const label = $derived(seasonMeta ? weekLabel(week, seasonMeta) : '')
  const inProgress = $derived(partial && isLatest)

  // First, last regular-season week (when reached and distinct from the end), last available week.
  const ticks = $derived.by(() => {
    if (!seasonMeta) return []
    const out = [{ week: 0, text: tickLabel(0, seasonMeta) }]
    const reg = seasonMeta.reg_weeks
    if (reg > 0 && reg < maxWeek) out.push({ week: reg, text: tickLabel(reg, seasonMeta) })
    if (maxWeek > 0) out.push({ week: maxWeek, text: tickLabel(maxWeek, seasonMeta) })
    return out
  })
  const tickPos = (w: number) => (maxWeek > 0 ? (w / maxWeek) * 100 : 0)
</script>

<form class="scrubber" role="search" aria-label="Choose season and week" onsubmit={(e) => e.preventDefault()}>
  <label class="season-label" for="season-select">Season</label>
  <select
    id="season-select"
    class="season-select"
    value={season}
    {disabled}
    onchange={(e) => onSeasonChange(Number(e.currentTarget.value))}
  >
    {#each seasons as s (s.season)}
      <option value={s.season}>{s.season}</option>
    {/each}
  </select>

  <div class="week">
    <label class="week-label" for="week-range">Week</label>
    <output for="week-range">{label}</output>
    {#if inProgress}<Badge variant="accent">In progress</Badge>{/if}
  </div>

  <div class="range">
    <input
      id="week-range"
      type="range"
      min="0"
      max={maxWeek}
      step="1"
      value={week}
      aria-valuetext={label}
      {disabled}
      oninput={(e) => onWeekInput(e.currentTarget.valueAsNumber)}
    />
    <div class="ticks" aria-hidden="true">
      {#each ticks as t (t.week)}
        <span
          class="tick"
          class:first={t.week === 0}
          class:last={t.week === maxWeek && maxWeek > 0}
          style:left="{tickPos(t.week)}%">{t.text}</span
        >
      {/each}
    </div>
  </div>

  <button
    type="button"
    class="latest"
    aria-label="Jump to the latest week"
    disabled={disabled || isLatest}
    onclick={onLatest}>Latest</button
  >
</form>

<style>
  .scrubber {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-areas:
      'slabel slabel'
      'select latest'
      'week week'
      'range range';
    column-gap: var(--space-sm);
    row-gap: var(--space-xs);
    padding: var(--space-md);
    background: var(--surface);
    border: 0;
    border-bottom: 1px solid var(--border);
    border-radius: 0;
    margin-bottom: var(--space-lg);
  }
  .season-label,
  .week-label {
    color: var(--text-muted);
    font-size: var(--text-label);
    line-height: var(--lh-label);
  }
  .season-label {
    grid-area: slabel;
  }
  .season-select {
    grid-area: select;
    min-width: 0;
    block-size: var(--tap-min);
    padding: 0 var(--space-sm);
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    font: inherit;
  }
  .week {
    grid-area: week;
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--space-sm);
    margin-top: var(--space-sm);
  }
  output {
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
    font-size: var(--text-body);
    line-height: var(--lh-body);
    font-weight: var(--weight-semibold);
  }
  .range {
    grid-area: range;
    min-width: 0;
  }
  input[type='range'] {
    display: block;
    inline-size: 100%;
    block-size: var(--tap-min);
    margin: 0;
    accent-color: var(--accent);
    cursor: pointer;
  }
  input[type='range']:disabled {
    cursor: default;
  }
  .ticks {
    position: relative;
    block-size: calc(var(--text-label) * var(--lh-label));
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
    font-size: var(--text-label);
    line-height: var(--lh-label);
  }
  .tick {
    position: absolute;
    top: 0;
    transform: translateX(-50%);
    white-space: nowrap;
  }
  .tick.first {
    transform: none;
  }
  .tick.last {
    left: auto !important;
    right: 0;
    transform: none;
  }
  .latest {
    grid-area: latest;
    block-size: var(--tap-min);
    padding: 0 var(--space-md);
    background: var(--accent);
    color: var(--on-accent);
    border: 1px solid transparent;
    border-radius: var(--radius-md);
    font: inherit;
    font-weight: var(--weight-bold);
    cursor: pointer;
    transition:
      background-color 120ms ease,
      color 120ms ease;
  }
  .latest:disabled {
    background: var(--border);
    color: var(--text-muted);
    cursor: default;
  }
  select:focus-visible,
  input:focus-visible,
  button:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }

  @media (min-width: 1024px) {
    .scrubber {
      position: sticky;
      top: 0;
      z-index: 1;
      grid-template-columns: auto auto auto minmax(0, 1fr) auto;
      grid-template-areas: 'slabel select week range latest';
      align-items: center;
      column-gap: var(--space-md);
      /* room for the tick labels, which hang below the track */
      padding-bottom: calc(var(--space-md) + var(--text-label) * var(--lh-label));
    }
    .week {
      margin-top: 0;
      min-width: 13ch;
    }
    .range {
      /* keep the ticks under the track while the track lines up with the other controls */
      margin-bottom: calc(-1 * var(--text-label) * var(--lh-label));
    }
  }
</style>

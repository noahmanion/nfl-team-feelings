<script lang="ts">
  import Badge from './Badge.svelte'
  import Delta from './Delta.svelte'
  import PinButton from './PinButton.svelte'
  import MoodLabel from './MoodLabel.svelte'
  import TeamChip from './TeamChip.svelte'
  import { bandIndex, changeText, formatRecord, moodToken } from '../lib/format'
  import { teamHash } from '../lib/router'
  import type { Band, Row, TeamMeta } from '../lib/types'

  let {
    row,
    team,
    bands,
    season,
    week,
    latest = true,
    pinned = null,
  }: {
    row: Row
    team: TeamMeta | undefined
    bands: Band[]
    season: number
    week: number
    latest?: boolean
    /** Validated pinned team (validMyTeam), or null. */
    pinned?: string | null
  } = $props()

  const mine = $derived(pinned !== null && pinned === row.franchise)

  const href = $derived(latest ? teamHash(row.franchise) : teamHash(row.franchise, season, week))

  // Stripe follows the exported band (hysteresis-adjusted, same as the label), never the raw score.
  const bandIdx = $derived(bandIndex(row.band, bands))
  const stripe = $derived(bandIdx < 0 ? 'var(--border)' : `var(--mood-${moodToken(bandIdx, bands.length)})`)
  const name = $derived(team?.name ?? row.franchise)
  // Defensive: malformed data renders "–", never "NaN"/"null"/"undefined".
  const ok = (n: unknown): n is number => typeof n === 'number' && Number.isFinite(n)
  const num = (n: unknown): string => (ok(n) ? String(n) : '–')
  const record = $derived(
    ok(row.wins) && ok(row.losses) ? formatRecord(row.wins, row.losses, ok(row.ties) ? row.ties : 0) : '–',
  )
  const elo = $derived(ok(row.elo) ? `Elo ${Math.round(row.elo)}` : '–')

  const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

  const recordText = $derived(
    ok(row.wins) && ok(row.losses)
      ? `${row.wins} and ${row.losses}${ok(row.ties) && row.ties > 0 ? ` and ${plural(row.ties, 'tie')}` : ''}`
      : 'record unavailable',
  )
  const srText = $derived(
    `${num(row.rank)}. ${name}, ${recordText}. Score ${ok(row.score) ? row.score : 'unavailable'}, ${row.label ?? ''}. ${changeText(row, week)}${mine ? ' My team.' : ''}`,
  )
</script>

<li id="row-{row.franchise}" class:mine>
  <a class="row" {href} style:--stripe-color={stripe}>
    <span class="visually-hidden">{srText}</span>
    <span class="rank" aria-hidden="true">{num(row.rank)}</span>
    <span class="team" aria-hidden="true">
      <TeamChip primary={team?.primary} secondary={team?.secondary} />
      <span class="abbr">{row.franchise}</span>
      <span class="name">{name}</span>
      {#if mine}<span class="mine-badge"><Badge variant="neutral">My team</Badge></span>{/if}
    </span>
    <span class="line2" aria-hidden="true">
      <span class="record">{record}</span>
      <span class="mood"><MoodLabel emoji={row.emoji} label={row.label} /></span>
    </span>
    <span class="score-cell" aria-hidden="true">
      <span class="score" class:missing={!ok(row.score)}>{num(row.score)}</span>
      <span class="elo">{elo}</span>
    </span>
    <span class="change" aria-hidden="true">
      <Delta value={row.score_delta} kind="score" />
      <span class="rank-delta"><Delta value={row.rank_delta} kind="rank" /></span>
    </span>
  </a>
  <span class="pin-slot"><PinButton abbr={row.franchise} {name} /></span>
</li>

<style>
  li {
    position: relative;
  }
  .pin-slot {
    position: absolute;
    inset-block-start: 50%;
    inset-inline-end: var(--space-xs);
    transform: translateY(-50%);
  }
  .mine .row {
    background: color-mix(in srgb, var(--accent) 6%, var(--surface));
  }
  .mine-badge {
    flex: none;
    display: inline-flex;
  }
  .row {
    display: grid;
    grid-template-columns: 28px minmax(0, 1fr) auto;
    grid-template-rows: auto auto;
    column-gap: var(--space-sm);
    row-gap: var(--space-xs);
    align-items: center;
    padding: var(--space-md);
    /* room for the absolutely positioned pin button so it never covers score/delta */
    padding-inline-end: calc(var(--tap-min) + var(--space-sm));
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: var(--stripe-width) solid var(--stripe-color);
    border-radius: var(--radius-md);
    color: inherit;
    text-decoration: none;
  }
  .row:hover {
    background: var(--bg);
  }
  .row:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  .rank {
    grid-column: 1;
    white-space: nowrap;
    grid-row: 1;
    font-size: var(--text-label);
    line-height: var(--lh-label);
    font-weight: var(--weight-semibold);
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;
  }
  .team {
    grid-column: 2;
    grid-row: 1;
    display: flex;
    align-items: center;
    gap: var(--space-xs);
    min-width: 0;
  }
  .abbr {
    flex: none;
    font-weight: var(--weight-semibold);
    letter-spacing: 0.02em;
  }
  .name {
    min-width: 0;
    margin-left: var(--space-xs);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .line2 {
    grid-column: 2;
    grid-row: 2;
    display: flex;
    align-items: baseline;
    gap: var(--space-sm);
    min-width: 0;
  }
  .record {
    flex: none;
    font-size: var(--text-label);
    line-height: var(--lh-label);
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;
  }
  .mood {
    display: flex;
    min-width: 0;
  }
  .score-cell {
    grid-column: 3;
    grid-row: 1;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    white-space: nowrap;
  }
  .score {
    font-size: var(--text-display);
    line-height: var(--lh-display);
    font-weight: var(--weight-semibold);
    font-variant-numeric: tabular-nums;
  }
  .score.missing {
    color: var(--text-muted);
  }
  .elo,
  .rank-delta {
    display: none;
  }
  .change {
    grid-column: 3;
    grid-row: 2;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    white-space: nowrap;
  }

  @media (min-width: 1024px) {
    .row {
      grid-template-columns: 48px minmax(0, 1fr) 80px 72px minmax(0, 280px) 72px;
      grid-template-rows: auto;
      column-gap: var(--space-md);
      padding: var(--space-sm) var(--space-md);
      padding-inline-end: calc(var(--tap-min) + var(--space-sm));
    }
    .rank,
    .team,
    .score-cell,
    .change {
      grid-row: 1;
    }
    .line2 {
      display: contents;
    }
    .record {
      grid-column: 3;
      grid-row: 1;
    }
    .score-cell {
      grid-column: 4;
    }
    .mood {
      grid-column: 5;
      grid-row: 1;
    }
    .change {
      grid-column: 6;
    }
    .elo {
      display: block;
      font-size: var(--text-label);
      line-height: var(--lh-label);
      color: var(--text-muted);
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }
    .rank-delta {
      display: block;
    }
  }
</style>

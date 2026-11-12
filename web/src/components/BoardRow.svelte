<script lang="ts">
  import Badge from './Badge.svelte'
  import Delta from './Delta.svelte'
  import PinButton from './PinButton.svelte'
  import MoodLabel from './MoodLabel.svelte'
  import TeamLogo from './TeamLogo.svelte'
  import { bandIndex, changeText, formatRecord, moodToken } from '../lib/format'
  import { teamHash } from '../lib/router'
  import { eraAbbr, eraName } from '../lib/teamNames'
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
  // Era-correct identity for the viewed season (D-16); the pin button keeps the current name.
  const name = $derived(eraName(row.franchise, season, { teams: team ? { [row.franchise]: team } : {} }))
  const abbr = $derived(eraAbbr(row.franchise, season))
  const currentName = $derived(team?.name ?? row.franchise)
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
  <a class="row" {href}>
    <span class="visually-hidden">{srText}</span>
    <span class="rank" aria-hidden="true">{num(row.rank)}</span>
    <span class="team" aria-hidden="true">
      <TeamLogo franchise={row.franchise} primary={team?.primary} secondary={team?.secondary} size={24} />
      <span class="abbr">{abbr}</span>
      <span class="name">{name}</span>
      {#if mine}<span class="mine-badge"><Badge variant="neutral">My team</Badge></span>{/if}
    </span>
    <span class="line2" aria-hidden="true">
      <span class="record-block">
        <span class="record">{record}</span>
        <span class="elo">{elo}</span>
      </span>
      <span class="mood"><MoodLabel emoji={row.emoji} label={row.label} /></span>
    </span>
    <span class="score-cell" aria-hidden="true" style:--band={stripe}>
      <span class="score">{num(row.score)}</span>
    </span>
    <span class="change" aria-hidden="true">
      <Delta value={row.score_delta} kind="score" />
      <span class="rank-delta"><Delta value={row.rank_delta} kind="rank" /></span>
    </span>
  </a>
  <span class="pin-slot"><PinButton abbr={row.franchise} name={currentName} /></span>
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
  .row {
    display: grid;
    grid-template-columns: 28px minmax(0, 1fr) auto var(--score-cell);
    grid-template-rows: auto auto;
    column-gap: var(--space-sm);
    row-gap: var(--space-xs);
    align-items: center;
    min-block-size: 48px;
    padding: var(--space-sm) var(--space-md);
    /* room for the absolutely positioned pin button so it never covers score/delta */
    padding-inline-end: calc(var(--tap-min) + var(--space-sm));
    background: transparent;
    border-bottom: 1px solid var(--border);
    border-radius: 0;
    color: inherit;
    text-decoration: none;
    transition: background-color 120ms ease;
  }
  .row:hover {
    background: var(--surface-hover);
  }
  /* My team: accent outline over the tint; declared before .row:focus-visible so the keyboard
     focus ring still wins on the pinned row (IN-05). */
  .mine .row {
    background: color-mix(in srgb, var(--accent) 6%, var(--bg));
    outline: 2px solid var(--accent);
    outline-offset: -2px;
  }
  @media (prefers-color-scheme: dark) {
    .mine .row {
      background: color-mix(in srgb, var(--accent) 8%, var(--bg));
    }
  }
  .row:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: -2px;
  }
  .mine-badge {
    flex: none;
    display: inline-flex;
  }
  .rank {
    grid-column: 1;
    grid-row: 1;
    white-space: nowrap;
    font-family: var(--font-mono);
    font-size: var(--text-label);
    line-height: var(--lh-label);
    font-weight: var(--weight-semibold);
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;
  }
  .team {
    grid-column: 2 / 4;
    grid-row: 1;
    display: flex;
    align-items: center;
    gap: var(--space-xs);
    min-width: 0;
  }
  .abbr {
    flex: none;
    margin-left: var(--space-xs);
    font-weight: var(--weight-bold);
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
  .record-block {
    flex: none;
    display: flex;
    flex-direction: column;
  }
  .record,
  .elo {
    font-family: var(--font-mono);
    font-size: var(--text-label);
    line-height: var(--lh-label);
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  .mood {
    display: flex;
    min-width: 0;
  }
  /* Shaded score cell (12-UI-SPEC Color): band tint with a solid 4px band edge. The band comes from
     the exported label (bandIndex), never the raw score. No muted text inside the cell. */
  .score-cell {
    grid-column: 4;
    grid-row: 1 / 3;
    align-self: stretch;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    inline-size: var(--score-cell);
    /* full row height: cancel the row's block padding */
    margin-block: calc(-1 * var(--space-sm));
    padding: 0 var(--space-sm);
    background: color-mix(in srgb, var(--band) var(--cell-tint), var(--bg));
    box-shadow: inset var(--stripe-width) 0 0 var(--band);
    white-space: nowrap;
  }
  .score {
    font-family: var(--font-mono);
    font-size: var(--text-heading);
    line-height: var(--lh-heading);
    font-weight: var(--weight-semibold);
    color: var(--text);
    font-variant-numeric: tabular-nums;
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
      grid-template-columns: 32px minmax(0, 1fr) 80px var(--score-cell) minmax(0, 280px) 72px;
      grid-template-rows: auto;
      column-gap: var(--space-md);
      padding: var(--space-sm) var(--space-md);
      padding-inline-end: calc(var(--tap-min) + var(--space-sm));
    }
    .rank,
    .team,
    .change {
      grid-row: 1;
    }
    .team {
      grid-column: 2;
    }
    .line2 {
      display: contents;
    }
    .record-block {
      grid-column: 3;
      grid-row: 1;
      align-items: flex-end;
      text-align: right;
    }
    .score-cell {
      grid-column: 4;
      grid-row: 1;
    }
    .mood {
      grid-column: 5;
      grid-row: 1;
    }
    .change {
      grid-column: 6;
    }
    .elo,
    .rank-delta {
      display: block;
    }
  }
</style>

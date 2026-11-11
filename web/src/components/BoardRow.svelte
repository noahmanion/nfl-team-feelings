<script lang="ts">
  import Delta from './Delta.svelte'
  import MoodLabel from './MoodLabel.svelte'
  import TeamChip from './TeamChip.svelte'
  import { bandIndexForLabel, formatRecord, moodToken } from '../lib/format'
  import type { Band, Row, TeamMeta } from '../lib/types'

  let { row, team, bands, week }: { row: Row; team: TeamMeta | undefined; bands: Band[]; week: number } = $props()

  // Stripe follows the visible label (hysteresis), never the raw score.
  const bandIdx = $derived(bandIndexForLabel(row.label, bands))
  const stripe = $derived(bandIdx < 0 ? 'var(--border)' : `var(--mood-${moodToken(bandIdx, bands.length)})`)
  const name = $derived(team?.name ?? row.franchise)
  const record = $derived(formatRecord(row.wins, row.losses, row.ties))

  const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

  function changeText(r: Row, wk: number): string {
    if (wk === 0 || r.score_delta == null) return 'No change, preseason.'
    const sd = r.score_delta
    const rd = r.rank_delta ?? 0
    if (sd === 0 && rd === 0) return 'No change from last week.'
    const score = sd > 0 ? `Up ${plural(sd, 'point')}` : sd < 0 ? `Down ${plural(-sd, 'point')}` : 'Same score'
    const rank = rd > 0 ? `up ${plural(rd, 'spot')}` : rd < 0 ? `down ${plural(-rd, 'spot')}` : 'same spot'
    return `${score}, ${rank} from last week.`
  }

  const recordText = $derived(
    `${row.wins} and ${row.losses}${row.ties > 0 ? ` and ${plural(row.ties, 'tie')}` : ''}`,
  )
  const srText = $derived(
    `${row.rank}. ${name}, ${recordText}. Score ${row.score}, ${row.label}. ${changeText(row, week)}`,
  )
</script>

<li class="row" style:--stripe-color={stripe}>
  <span class="visually-hidden">{srText}</span>
  <span class="rank" aria-hidden="true">{row.rank}</span>
  <span class="team" aria-hidden="true">
    <TeamChip primary={team?.primary} secondary={team?.secondary} />
    <span class="abbr">{row.franchise}</span>
    <span class="name">{name}</span>
  </span>
  <span class="line2" aria-hidden="true">
    <span class="record">{record}</span>
    <span class="mood"><MoodLabel emoji={row.emoji} label={row.label} /></span>
  </span>
  <span class="score-cell" aria-hidden="true">
    <span class="score">{row.score}</span>
    <span class="elo">{row.elo == null ? '–' : `Elo ${row.elo}`}</span>
  </span>
  <span class="change" aria-hidden="true">
    <Delta value={row.score_delta} kind="score" />
    <span class="rank-delta"><Delta value={row.rank_delta} kind="rank" /></span>
  </span>
</li>

<style>
  .row {
    display: grid;
    grid-template-columns: 28px minmax(0, 1fr) auto;
    grid-template-rows: auto auto;
    column-gap: var(--space-sm);
    row-gap: var(--space-xs);
    align-items: center;
    padding: var(--space-md);
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: var(--stripe-width) solid var(--stripe-color);
    border-radius: var(--radius-md);
  }
  .rank {
    grid-column: 1;
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
  }
  .score {
    font-size: var(--text-display);
    line-height: var(--lh-display);
    font-weight: var(--weight-semibold);
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
  }

  @media (min-width: 1024px) {
    .row {
      grid-template-columns: 48px minmax(0, 1fr) 80px 72px minmax(0, 280px) 72px;
      grid-template-rows: auto;
      column-gap: var(--space-md);
      padding: var(--space-sm) var(--space-md);
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

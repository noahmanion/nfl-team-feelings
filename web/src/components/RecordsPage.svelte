<script lang="ts">
  import Badge from './Badge.svelte'
  import Sep from './Sep.svelte'
  import StatusPanel from './StatusPanel.svelte'
  import TeamChip from './TeamChip.svelte'
  import { findSeason, loadRecords } from '../lib/data'
  import { formatRecord, moodToken, weekLabel } from '../lib/format'
  import { validMyTeam } from '../lib/myteam'
  import { myTeam } from '../lib/myteam.svelte'
  import { dateRange, formatDate, formatDays, seasonsSpan, streakLine } from '../lib/records'
  import { teamHash } from '../lib/router'
  import type { ExtremeEntry, Meta, RecordsFile, StreakEntry } from '../lib/types'

  let { meta }: { meta: Meta } = $props()

  let records = $state<RecordsFile | null>(null)
  let failed = $state(false)
  let retry = $state(0)

  // Stale-response guard: only the latest request may land.
  $effect(() => {
    void retry
    failed = false
    let live = true
    loadRecords(meta).then(
      (d) => {
        if (live) records = d
      },
      (err) => {
        console.error(err)
        if (live) failed = true
      },
    )
    return () => {
      live = false
    }
  })

  const teamName = (abbr: string) => meta.teams[abbr]?.name ?? abbr

  // Stripe from the score's mood band (score-based here: records carry no hysteresis band).
  function scoreStripe(score: number): string {
    const i = meta.bands.findIndex((b) => score >= b.min && score <= b.max)
    return i < 0 ? 'var(--border)' : `var(--mood-${moodToken(i, meta.bands.length)})`
  }
  const streakStripe = (kind: 'misery' | 'joy') =>
    meta.bands.length ? `var(--mood-${kind === 'misery' ? 0 : 6})` : 'var(--border)'

  function whenLabel(e: ExtremeEntry): string {
    const s = findSeason(meta, e.season)
    return s ? weekLabel(e.week, s) : `Week ${e.week}`
  }

  const streakHref = (s: StreakEntry) =>
    s.active || s.end_season == null || s.end_week == null
      ? teamHash(s.franchise)
      : teamHash(s.franchise, s.end_season, s.end_week)

  const mine = $derived(validMyTeam(myTeam.abbr, meta.teams))
  const myStreak = $derived(mine && records ? streakLine(records.active?.[mine]) : null)

  const excludedText = $derived(
    records?.excluded.map((x) => `the ${x.season} ${teamName(x.franchise)}`).join(' and ') ?? '',
  )
</script>

<article class="records" aria-labelledby="records-heading">
  <header class="intro">
    <h2 id="records-heading">Records</h2>
    <p>Every team-season since 1999, scored the same way. Streaks count calendar days.</p>
    {#if records}<p class="muted">As of {formatDate(records.as_of)}</p>{/if}
  </header>

  {#if failed}
    <StatusPanel
      variant="error"
      title="Couldn’t load the records"
      body="The records data didn’t load."
      actions={[{ label: 'Try again', onClick: () => retry++ }]}
    />
  {:else if !records}
    <p class="muted" role="status">Loading…</p>
  {:else}
    {#if mine && myStreak}
      <p class="mine-line">
        Your team: <a href={teamHash(mine)}>{myStreak}</a>
      </p>
    {/if}

    {#snippet extremes(id: string, title: string, list: ExtremeEntry[], caption: string)}
      <section aria-labelledby={id}>
        <h3 id={id}>{title}</h3>
        <ol class="rows">
          {#each list as e, i (`${e.season}-${e.franchise}`)}
            {@const tm = meta.teams[e.franchise]}
            <li class:mine={e.franchise === mine}>
              <a class="row" href={teamHash(e.franchise, e.season, e.week)} style:--stripe-color={scoreStripe(e.score)}>
                <span class="rank">{i + 1}</span>
                <span class="team">
                  <TeamChip primary={tm?.primary} secondary={tm?.secondary} />
                  <span class="name">{e.season} {teamName(e.franchise)}</span>
                  {#if e.franchise === mine}<span class="mine-badge"><Badge variant="neutral">My team</Badge></span>{/if}
                </span>
                <span class="meta">
                  {formatRecord(e.wins, e.losses, e.ties)}<Sep />{whenLabel(e)}<Sep />{formatDate(e.date)}<Sep />Season avg {e.mean}
                </span>
                <span class="big"><span class="visually-hidden">{caption} </span>{e.score}</span>
              </a>
            </li>
          {/each}
        </ol>
      </section>
    {/snippet}

    {#snippet streaks(id: string, title: string, list: StreakEntry[], kind: 'misery' | 'joy')}
      <section aria-labelledby={id}>
        <h3 id={id}>{title}</h3>
        <ol class="rows">
          {#each list as s, i (`${s.franchise}-${s.start}`)}
            {@const tm = meta.teams[s.franchise]}
            <li class:mine={s.franchise === mine}>
              <a class="row" href={streakHref(s)} style:--stripe-color={streakStripe(kind)}>
                <span class="rank">{i + 1}</span>
                <span class="team">
                  <TeamChip primary={tm?.primary} secondary={tm?.secondary} />
                  <span class="name">{teamName(s.franchise)} {seasonsSpan(s)}</span>
                  {#if s.franchise === mine}<span class="mine-badge"><Badge variant="neutral">My team</Badge></span>{/if}
                </span>
                <span class="meta">
                  {dateRange(s.start, s.end)}{#if s.active}<span class="still"><Badge variant="accent">Still going</Badge></span>{/if}
                </span>
                <span class="big days">{formatDays(s.days)}</span>
              </a>
            </li>
          {/each}
        </ol>
      </section>
    {/snippet}

    {@render extremes('saddest-heading', 'Saddest fanbases ever', records.saddest, 'Lowest score')}
    {@render extremes('happiest-heading', 'Happiest fanbases ever', records.happiest, 'Highest score')}
    {@render streaks('misery-heading', 'Longest misery streaks', records.misery, 'misery')}
    {@render streaks('joy-heading', 'Longest joy streaks', records.joy, 'joy')}

    <p class="footnote muted">
      Saddest and happiest rank each team-season by its lowest or highest weekly score, then by its regular-season
      average. A misery streak is every day spent under 20; a joy streak, every day at 80 or higher.
      {#if excludedText}
        The 1999 Browns and 2002 Texans are left out: as expansion teams they start from an assumed rating, not
        results.
      {/if}
    </p>
  {/if}
</article>

<style>
  .records {
    max-width: 680px;
    display: flex;
    flex-direction: column;
    gap: var(--space-xl);
    font-size: var(--text-body);
    line-height: var(--lh-body);
    min-width: 0;
  }
  .intro {
    display: flex;
    flex-direction: column;
    gap: var(--space-xs);
  }
  h2 {
    font-size: var(--text-display);
    line-height: var(--lh-display);
    font-weight: var(--weight-semibold);
  }
  section {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
    min-width: 0;
  }
  h3 {
    font-size: var(--text-heading);
    line-height: var(--lh-heading);
    font-weight: var(--weight-semibold);
  }
  .muted {
    color: var(--text-muted);
  }
  .rows {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
    margin: 0;
    padding: 0;
    list-style: none;
  }
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
    color: inherit;
    text-decoration: none;
  }
  .row:hover {
    background: var(--bg);
  }
  /* My team (UI-SPEC rule 7): same tint as the board row, stripe unchanged. */
  .mine .row {
    background: color-mix(in srgb, var(--accent) 6%, var(--surface));
  }
  .mine-badge {
    flex: none;
    display: inline-flex;
  }
  .mine-line {
    font-weight: var(--weight-semibold);
  }
  .row:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
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
    gap: var(--space-sm);
    min-width: 0;
  }
  .name {
    min-width: 0;
    font-weight: var(--weight-semibold);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .meta {
    grid-column: 2 / -1;
    grid-row: 2;
    min-width: 0;
    font-size: var(--text-label);
    line-height: var(--lh-label);
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;
  }
  .big {
    grid-column: 3;
    grid-row: 1;
    font-size: var(--text-display);
    line-height: var(--lh-display);
    font-weight: var(--weight-semibold);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  .big.days {
    font-size: var(--text-heading);
    line-height: var(--lh-heading);
  }
  .still {
    margin-left: var(--space-sm);
  }
  .footnote {
    font-size: var(--text-label);
    line-height: var(--lh-label);
  }
</style>

<script lang="ts">
  import Badge from './Badge.svelte'
  import Sep from './Sep.svelte'
  import StatusPanel from './StatusPanel.svelte'
  import TeamLogo from './TeamLogo.svelte'
  import { findSeason, loadRecords } from '../lib/data'
  import { formatRecord, moodToken, weekLabel } from '../lib/format'
  import { validMyTeam } from '../lib/myteam'
  import { myTeam } from '../lib/myteam.svelte'
  import { dateRange, formatDate, formatDays, seasonsSpan, streakLine } from '../lib/records'
  import { teamHash } from '../lib/router'
  import { eraName } from '../lib/teamNames'
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

  // Era-correct name for a given season (D-16, D-18); active streaks use the current name.
  const teamName = (abbr: string, season: number) => eraName(abbr, season, meta)
  const currentName = (abbr: string) => meta.teams[abbr]?.name ?? abbr

  // Stripe from the score's mood band (score-based here: records carry no hysteresis band).
  function scoreStripe(score: number): string {
    const i = meta.bands.findIndex((b) => score >= b.min && score <= b.max)
    return i < 0 ? 'var(--border)' : `var(--mood-${moodToken(i, meta.bands.length)})`
  }
  // lowest band for misery, highest for joy, mapped through moodToken like scoreStripe (IN-03)
  const streakStripe = (kind: 'misery' | 'joy') => {
    const n = meta.bands.length
    return n ? `var(--mood-${moodToken(kind === 'misery' ? 0 : n - 1, n)})` : 'var(--border)'
  }

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

  // Footnote built from records.excluded (IN-02), so it follows season_config.SEEDS.
  const excludedText = $derived.by(() => {
    const xs = records?.excluded ?? []
    if (xs.length === 0) return ''
    const names = xs.map((x) => `the ${x.season} ${teamName(x.franchise, x.season)}`)
    const list = names.length <= 2 ? names.join(' and ') : `${names.slice(0, -1).join(', ')} and ${names.at(-1)}`
    const sentence = `${list} ${xs.length === 1 ? 'is' : 'are'} left out: as expansion teams they start from an assumed rating, not results.`
    return sentence.charAt(0).toUpperCase() + sentence.slice(1)
  })
</script>

<article class="records" aria-labelledby="records-heading">
  <header class="intro">
    <h2 id="records-heading">Records</h2>
    <p class="dek">Every team-season since 1999, scored the same way. Streaks count calendar days.</p>
    {#if records}<p class="as-of">As of {formatDate(records.as_of)}</p>{/if}
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
              <a class="row" href={teamHash(e.franchise, e.season, e.week)} style:--band={scoreStripe(e.score)}>
                <span class="rank">{i + 1}</span>
                <span class="team">
                  <TeamLogo franchise={e.franchise} primary={tm?.primary} secondary={tm?.secondary} size={24} />
                  <span class="name">{e.season} {teamName(e.franchise, e.season)}</span>
                  {#if e.franchise === mine}<span class="mine-badge"><Badge variant="neutral">My team</Badge></span>{/if}
                </span>
                <span class="meta">
                  <span class="num">{formatRecord(e.wins, e.losses, e.ties)}</span><Sep />{whenLabel(e)}<Sep />{formatDate(
                    e.date,
                  )}<Sep />Season avg <span class="num">{e.mean}</span>
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
              <a class="row" href={streakHref(s)} style:--band={streakStripe(kind)}>
                <span class="rank">{i + 1}</span>
                <span class="team">
                  <TeamLogo franchise={s.franchise} primary={tm?.primary} secondary={tm?.secondary} size={24} />
                  <span class="name"
                    >{s.active ? currentName(s.franchise) : teamName(s.franchise, s.start_season)} {seasonsSpan(s)}</span
                  >
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
      average. A season in progress joins those two lists once its regular season ends. A misery streak is every day
      spent under 20; a joy streak, every day at 80 or higher.
      {excludedText}
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
    font-size: var(--text-heading);
    line-height: var(--lh-heading);
    font-weight: var(--weight-bold);
  }
  .dek {
    color: var(--text-muted);
    max-width: var(--prose-max);
  }
  .as-of {
    font-family: var(--font-mono);
    font-size: var(--text-micro);
    line-height: var(--lh-micro);
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--text-muted);
  }
  /* Rule-topped sections (D-22): no box, background or radius. */
  section {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
    min-width: 0;
    border-top: 1px solid var(--border);
    padding-top: var(--space-md);
  }
  h3 {
    font-size: var(--text-heading);
    line-height: var(--lh-heading);
    font-weight: var(--weight-bold);
  }
  .muted {
    color: var(--text-muted);
  }
  .rows {
    display: flex;
    flex-direction: column;
    gap: 0;
    margin: 0;
    padding: 0;
    list-style: none;
  }
  /* Board-row style: bottom rule only, transparent background, radius 0. */
  .row {
    display: grid;
    grid-template-columns: 28px minmax(0, 1fr) auto;
    grid-template-rows: auto auto;
    column-gap: var(--space-sm);
    row-gap: var(--space-xs);
    align-items: center;
    padding: var(--space-sm) 0 var(--space-sm) var(--space-sm);
    border-bottom: 1px solid var(--border);
    color: inherit;
    text-decoration: none;
  }
  .row:hover {
    background: var(--surface-hover);
  }
  /* My team (UI-SPEC rule 7): same tint and accent outline as the board row; the shaded value
     cell keeps its band tint. Before .row:focus-visible so the focus ring still wins. */
  .mine .row {
    background: color-mix(in srgb, var(--accent) 6%, var(--bg));
    outline: 2px solid var(--accent);
    outline-offset: -2px;
  }
  .mine-badge {
    flex: none;
    display: inline-flex;
  }
  .mine-line {
    font-weight: var(--weight-bold);
  }
  .row:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  .rank {
    grid-column: 1;
    grid-row: 1;
    font-family: var(--font-mono);
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
    font-weight: var(--weight-bold);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .meta {
    grid-column: 2;
    grid-row: 2;
    min-width: 0;
    font-size: var(--text-label);
    line-height: var(--lh-label);
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;
  }
  /* Shaded value cell (12-UI-SPEC Color): band tint with a solid 4px band edge, full row height.
     No muted text inside. */
  .big {
    grid-column: 3;
    grid-row: 1 / span 2;
    align-self: stretch;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    box-sizing: border-box;
    min-inline-size: var(--score-cell);
    min-block-size: 48px;
    padding: 0 var(--space-sm);
    background: color-mix(in srgb, var(--band) var(--cell-tint), var(--bg));
    /* band edge as a left border (same look as the board's inset edge; this page has no shadows) */
    border-left: var(--stripe-width) solid var(--band);
    color: var(--text);
    font-family: var(--font-mono);
    font-size: var(--text-heading);
    line-height: var(--lh-heading);
    font-weight: var(--weight-semibold);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  .big.days {
    font-size: var(--text-body);
    line-height: var(--lh-body);
  }
  .still {
    margin-left: var(--space-sm);
  }
  .footnote {
    font-size: var(--text-label);
    line-height: var(--lh-label);
    max-width: var(--prose-max);
  }
</style>

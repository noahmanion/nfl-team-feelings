<script lang="ts">
  import CalloutCards from './CalloutCards.svelte'
  import ChartFrame from './ChartFrame.svelte'
  import Delta from './Delta.svelte'
  import FactorBars from './FactorBars.svelte'
  import MoodLabel from './MoodLabel.svelte'
  import PinButton from './PinButton.svelte'
  import RecentGames from './RecentGames.svelte'
  import Sep from './Sep.svelte'
  import Sparkline from './Sparkline.svelte'
  import StatusPanel from './StatusPanel.svelte'
  import TeamLogo from './TeamLogo.svelte'
  import WinTotals from './WinTotals.svelte'
  import { cardCallouts, forTeam, forWeek } from '../lib/callouts'
  import { findSeason, loadGames, loadRecords, loadSeason, loadTeam } from '../lib/data'
  import { bandIndex, formatRecord, moodToken, weekLabel } from '../lib/format'
  import { formatDate, streakLine } from '../lib/records'
  import { boardHash, historyHash, teamHash } from '../lib/router'
  import { findTeamRow, playoffText, recentGames, seasonSeries, stepWeek } from '../lib/team'
  import { eraName, eraText } from '../lib/teamNames'
  import type { ActiveStreak, GamesFile, Meta, SeasonFile, TeamFile } from '../lib/types'
  import { winTotalsView } from '../lib/winTotals'

  let { meta, team, season, week, latest }: { meta: Meta; team: string; season: number; week: number; latest: boolean } =
    $props()

  const teamMeta = $derived(meta.teams[team])
  // Era-correct name for the viewed season (D-16); the pin button keeps the current name.
  const name = $derived(eraName(team, season, meta))
  const currentName = $derived(teamMeta?.name ?? team)

  // Header logo: 32px below 1024px, 48px at desktop widths. Starts at 32 for first paint.
  let innerWidth = $state(0)
  const wide = $derived(innerWidth >= 1024)
  const seasonMeta = $derived(findSeason(meta, season))
  const prevSeason = $derived(findSeason(meta, season - 1) ? season - 1 : null)

  // Arriving from a board row deep in the list: start at the top of the team page.
  $effect(() => {
    void team
    window.scrollTo(0, 0)
  })

  // ---- season file (header, bars, sparkline): stale responses ignored ----
  let seasonFile = $state<SeasonFile | null>(null)
  let seasonFailed = $state(false)
  let retry = $state(0)

  $effect(() => {
    void retry
    const s = season
    seasonFailed = false
    let live = true
    loadSeason(meta, s).then(
      (f) => {
        if (live) seasonFile = f
      },
      (err) => {
        console.error(err)
        if (live) seasonFailed = true
      },
    )
    return () => {
      live = false
    }
  })

  // ---- games files (this season + last season for the cross-over): failure only hits that section ----
  let gamesFiles = $state<{ key: string; files: GamesFile[] } | null>(null)
  let gamesFailed = $state(false)
  let gamesRetry = $state(0)
  const gamesKey = $derived(`${season}|${prevSeason ?? ''}`)

  $effect(() => {
    void gamesRetry
    const key = gamesKey
    const wanted = [season, ...(prevSeason !== null ? [prevSeason] : [])]
    gamesFailed = false
    let live = true
    Promise.all(wanted.map((s) => loadGames(meta, s))).then(
      (files) => {
        if (live) gamesFiles = { key, files }
      },
      (err) => {
        console.error(err)
        if (live) gamesFailed = true
      },
    )
    return () => {
      live = false
    }
  })

  // ---- active streak (latest view only): records.json, failure-tolerant (no line on error) ----
  let streak = $state<{ team: string; active: ActiveStreak | null; asOf: string | null } | null>(null)

  $effect(() => {
    const t = team
    if (!latest) return
    let live = true
    loadRecords(meta).then(
      (r) => {
        if (live) streak = { team: t, active: r.active?.[t] ?? null, asOf: r.as_of ?? null }
      },
      (err) => {
        console.error(err)
        if (live) streak = { team: t, active: null, asOf: null }
      },
    )
    return () => {
      live = false
    }
  })

  // ---- team file (preseason expectations, D-21): display-only extra, failure omits the section ----
  let teamFile = $state<{ team: string; file: TeamFile | null; failed?: boolean } | null>(null)

  $effect(() => {
    const t = team
    let live = true
    loadTeam(meta, t).then(
      (file) => {
        if (live) teamFile = { team: t, file }
      },
      (err) => {
        console.error(err)
        if (live) teamFile = { team: t, file: null, failed: true }
      },
    )
    return () => {
      live = false
    }
  })

  const activeStreak = $derived(latest && streak?.team === team ? streak.active : null)
  const streakText = $derived(streakLine(activeStreak))
  const streakAsOf = $derived(latest && streak?.team === team ? streak.asOf : null)
  // the same date the latest board card counts through (WR-01, IN-07): the count is frozen at export
  const asOfText = $derived(streakAsOf ? ` (as of ${formatDate(streakAsOf)})` : '')

  const ready = $derived(seasonFile?.season === season)
  const row = $derived(ready && seasonFile ? findTeamRow(seasonFile, team, week) : undefined)
  const series = $derived(ready && seasonFile ? seasonSeries(seasonFile, team).filter((p) => p.week <= week) : [])
  // With the streak line shown, drop this team's misery/joy cards: the latest week's card counts
  // through the same export date (WR-01), so it would only repeat the line.
  const teamCallouts = $derived(
    ready && seasonFile
      ? cardCallouts(forTeam(forWeek(seasonFile, week), team)).filter(
          (c) => !(streakText && (c.type === 'misery' || c.type === 'joy')),
        )
      : [],
  )
  const games = $derived(gamesFiles?.key === gamesKey ? recentGames(gamesFiles.files, team, season, week) : null)

  const when = $derived(`${season} · ${seasonMeta ? weekLabel(week, seasonMeta) : `Week ${week}`}`)
  const ok = (n: unknown): n is number => typeof n === 'number' && Number.isFinite(n)
  const tf = $derived(teamFile?.team === team ? teamFile : null)
  const expectLoading = $derived(!tf)
  const viewRec = $derived(
    row && ok(row.wins) && ok(row.losses) ? { wins: row.wins, losses: row.losses, ties: ok(row.ties) ? row.ties : 0 } : null,
  )
  // Omit on failure or when the season has neither a Vegas line nor an expectation (UI-SPEC states).
  const showExpect = $derived(
    !tf?.failed && (expectLoading || (!!tf?.file && winTotalsView(tf.file, season, viewRec) !== null)),
  )
  const record = $derived(
    row && ok(row.wins) && ok(row.losses) ? formatRecord(row.wins, row.losses, ok(row.ties) ? row.ties : 0) : '–',
  )
  const baseline = $derived(meta.baseline ?? 50)
  // Shaded score cell: band from the exported label (hysteresis-adjusted), never the raw score.
  const bandIdx = $derived(row ? bandIndex(row.band, meta.bands) : -1)
  const band = $derived(bandIdx < 0 ? 'var(--border)' : `var(--mood-${moodToken(bandIdx, meta.bands.length)})`)
  // Same condition FactorBars uses before it falls back to "Factor breakdown unavailable".
  const hasPoints = $derived(!!row?.points)
  const odds = $derived(row ? playoffText(row.playoff_prob) : null)
  const qb = $derived(row?.qb ? `QB ${row.qb}` : null)

  // Past weeks: step one week back/forward (across seasons); the step that reaches meta.latest
  // goes to the team's latest page.
  const stepHash = (s: { season: number; week: number } | null): string | null =>
    !s ? null : s.season === meta.latest.season && s.week === meta.latest.week ? teamHash(team) : teamHash(team, s.season, s.week)
  const prevHash = $derived(latest ? null : stepHash(stepWeek(meta, season, week, -1)))
  const nextHash = $derived(latest ? null : stepHash(stepWeek(meta, season, week, 1)))
</script>

{#snippet weekNav()}
  {#if !latest}
    <nav class="week-nav" aria-label="Weeks">
      <!-- each separator travels with the link after it, so a wrapped 375px line never ends in "·" -->
      {#if prevHash}<a href={prevHash}>← Prev week</a>{/if}{#if nextHash}<span class="item"
          >{#if prevHash}<Sep />{/if}<a href={nextHash}>Next week →</a></span
        >{/if}<span class="item"
        >{#if prevHash || nextHash}<Sep />{/if}<a href={boardHash(season, week)}>See the board for this week</a></span
      >
    </nav>
  {/if}
{/snippet}

<svelte:window bind:innerWidth />

<article class="team-page" aria-labelledby="team-heading">
  {#if seasonFailed}
    <StatusPanel
      variant="error"
      title="Couldn’t load {name}"
      body="That season’s data didn’t load. Try again in a moment."
      actions={[{ label: 'Try again', onClick: () => retry++ }]}
    />
  {:else if !ready}
    <p class="loading" role="status">Loading {name}…</p>
  {:else if !row}
    <h2 id="team-heading" class="visually-hidden">{name}</h2>
    <StatusPanel variant="empty" title="No {name} data for {season}">
      We don’t have a {name} score for {when}.
      {#if !latest}<a href={teamHash(team)}>See {name} now →</a>{/if}
    </StatusPanel>
    {@render weekNav()}
  {:else}
    <header class="head">
      <div class="who">
        <div class="name-line">
          <TeamLogo franchise={team} primary={teamMeta?.primary} secondary={teamMeta?.secondary} size={wide ? 48 : 32} />
          <h2 id="team-heading">{name}</h2>
          {#if teamMeta}<PinButton abbr={team} name={currentName} />{/if}
        </div>
        <p class="sub">
          {when}{#if !latest}<Sep /><a href={teamHash(team)}>Now</a>{/if}
        </p>
        <p class="sub"><span class="num">{record}</span><Sep /><span>Rank <span class="num">#{row.rank}</span></span></p>
        {#if odds || qb}
          <p class="sub">
            {#if odds}<span>{odds}</span>{/if}{#if odds && qb}<Sep />{/if}{#if qb}<span>{qb}</span>{/if}
          </p>
        {/if}
      </div>
      <div class="score-cell">
        <span class="score" style:--band={band}><span class="visually-hidden">Score </span>{ok(row.score) ? row.score : '–'}</span>
        <Delta value={row.score_delta} kind="score" />
        {#if week === 0 && ok(row.score_delta)}<span class="delta-note">vs end of last season</span>{/if}
      </div>
      <div class="mood"><MoodLabel emoji={row.emoji} label={row.label} size="heading" /></div>
    </header>
    {@render weekNav()}

    {#if streakText && activeStreak}
      <p class="streak">{streakText}, since {formatDate(activeStreak.start)}{asOfText}</p>
    {/if}
    {#if row.blurb}<p class="blurb">{eraText(row.blurb, team, season)}</p>{/if}
    {#if row.draft?.text}<p class="draft-note">{row.draft.text}</p>{/if}

    <CalloutCards callouts={teamCallouts} {meta} heading="Callouts" level={3} />

    <div class="columns">
      <section class="block" aria-labelledby="why-heading">
        <ChartFrame
          id="why-heading"
          level={3}
          headline={hasPoints && ok(row.score) ? `Where the ${row.score} comes from` : 'Score breakdown'}
          dek={hasPoints && ok(row.score)
            ? `Points each factor adds to or takes from an average team (${baseline}). Together they sum to the score.`
            : undefined}
        >
          <FactorBars points={row.points} factors={meta.factors ?? []} {baseline} score={row.score} />
        </ChartFrame>
      </section>

      <div class="right">
        {#if showExpect}
          <section class="block" aria-labelledby="expect-heading">
            <WinTotals
              file={tf?.file ?? null}
              loading={expectLoading}
              {season}
              rec={viewRec}
              primary={teamMeta?.primary ?? ''}
              secondary={teamMeta?.secondary ?? ''}
            />
          </section>
        {/if}

        <section class="block" aria-labelledby="games-heading">
          <h3 id="games-heading">Recent games</h3>
          {#if gamesFailed}
            <StatusPanel
              variant="error"
              title="Couldn’t load recent games"
              body="The game list didn’t load."
              actions={[{ label: 'Try again', onClick: () => gamesRetry++ }]}
            />
          {:else if games}
            <RecentGames {games} {meta} currentSeason={season} />
          {:else}
            <p class="loading" role="status">Loading games…</p>
          {/if}

          {#if series.length >= 2}
            <h3 class="spark-heading">This season</h3>
            <Sparkline {series} primary={teamMeta?.primary} secondary={teamMeta?.secondary} {baseline} />
          {/if}
          <a class="more" href={historyHash(team)}>Mood over time →</a>
        </section>
      </div>
    </div>
  {/if}
</article>

<style>
  .team-page {
    display: flex;
    flex-direction: column;
    gap: var(--space-lg);
    min-width: 0;
  }
  .loading {
    color: var(--text-muted);
  }
  .head {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    column-gap: var(--space-md);
    row-gap: var(--space-sm);
    align-items: start;
  }
  .who {
    display: flex;
    flex-direction: column;
    gap: var(--space-xs);
    min-width: 0;
  }
  .name-line {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    min-width: 0;
  }
  h2 {
    min-width: 0;
    font-size: var(--text-display);
    line-height: var(--lh-display);
    font-weight: var(--weight-bold);
    overflow-wrap: anywhere;
  }
  .sub {
    color: var(--text-muted);
    font-size: var(--text-label);
    line-height: var(--lh-label);
    font-variant-numeric: tabular-nums;
  }
  .score-cell {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: var(--space-xs);
    white-space: nowrap;
  }
  /* Shaded score cell (12-UI-SPEC Color): band tint with a solid 4px band edge. No muted text inside. */
  .score {
    display: inline-flex;
    align-items: center;
    justify-content: flex-end;
    box-sizing: border-box;
    min-inline-size: 72px;
    min-block-size: 56px;
    padding: 0 var(--space-sm) 0 calc(var(--stripe-width) + var(--space-sm));
    background: color-mix(in srgb, var(--band) var(--cell-tint), var(--bg));
    box-shadow: inset var(--stripe-width) 0 0 var(--band);
    color: var(--text);
    font-family: var(--font-mono);
    font-size: var(--text-display);
    line-height: var(--lh-display);
    font-weight: var(--weight-semibold);
    font-variant-numeric: tabular-nums;
  }
  .mood {
    grid-column: 1 / -1;
    display: flex;
    min-width: 0;
  }
  .blurb {
    font-size: var(--text-body);
    line-height: var(--lh-body);
  }
  .week-nav {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    font-size: var(--text-label);
    line-height: var(--lh-label);
  }
  .week-nav .item {
    display: inline-flex;
    align-items: center;
    white-space: nowrap;
  }
  .week-nav a {
    display: inline-flex;
    align-items: center;
    min-block-size: var(--tap-min);
  }
  /* Narrow screens: links wrap, so drop the dots and space with a gap (no line starts with "·"). */
  @media (max-width: 639px) {
    .week-nav {
      column-gap: var(--space-md);
    }
    .week-nav :global(.sep) {
      display: none;
    }
  }
  .streak {
    font-size: var(--text-body);
    line-height: var(--lh-body);
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;
  }
  .delta-note {
    font-size: var(--text-label);
    line-height: var(--lh-label);
    color: var(--text-muted);
  }
  .draft-note {
    font-size: var(--text-body);
    line-height: var(--lh-body);
    color: var(--text-muted);
  }
  /* sections carry their own rule-top spacing, so the stack itself adds no gap */
  .columns {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  /* right column (>=1024): expectations above recent games; one grid item, the .block rules space it */
  .right {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  /* Rule-topped sections (D-22): no box, background or radius. */
  .block {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
    min-width: 0;
    border-top: 1px solid var(--border);
    padding-top: var(--space-md);
    margin-top: var(--space-xl);
  }
  h3 {
    font-size: var(--text-heading);
    line-height: var(--lh-heading);
    font-weight: var(--weight-bold);
  }
  .spark-heading {
    border-top: 1px solid var(--border);
    padding-top: var(--space-md);
    margin-top: var(--space-xl);
  }
  .more {
    align-self: flex-start;
    display: inline-flex;
    align-items: center;
    min-block-size: var(--tap-min);
  }
  @media (min-width: 1024px) {
    .columns {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      column-gap: var(--space-2xl);
    }
  }
</style>

<script lang="ts">
  import Delta from './Delta.svelte'
  import FactorBars from './FactorBars.svelte'
  import MoodLabel from './MoodLabel.svelte'
  import RecentGames from './RecentGames.svelte'
  import Sparkline from './Sparkline.svelte'
  import StatusPanel from './StatusPanel.svelte'
  import TeamChip from './TeamChip.svelte'
  import { findSeason, loadGames, loadSeason } from '../lib/data'
  import { formatRecord, weekLabel } from '../lib/format'
  import { historyHash, teamHash } from '../lib/router'
  import { findTeamRow, recentGames, seasonSeries } from '../lib/team'
  import type { GamesFile, Meta, SeasonFile } from '../lib/types'

  let { meta, team, season, week, latest }: { meta: Meta; team: string; season: number; week: number; latest: boolean } =
    $props()

  const teamMeta = $derived(meta.teams[team])
  const name = $derived(teamMeta?.name ?? team)
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

  const ready = $derived(seasonFile?.season === season)
  const row = $derived(ready && seasonFile ? findTeamRow(seasonFile, team, week) : undefined)
  const series = $derived(ready && seasonFile ? seasonSeries(seasonFile, team).filter((p) => p.week <= week) : [])
  const games = $derived(gamesFiles?.key === gamesKey ? recentGames(gamesFiles.files, team, season, week) : null)

  const when = $derived(`${season} · ${seasonMeta ? weekLabel(week, seasonMeta) : `Week ${week}`}`)
  const ok = (n: unknown): n is number => typeof n === 'number' && Number.isFinite(n)
  const record = $derived(
    row && ok(row.wins) && ok(row.losses) ? formatRecord(row.wins, row.losses, ok(row.ties) ? row.ties : 0) : '–',
  )
  const baseline = $derived(meta.baseline ?? 50)
</script>

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
  {:else}
    <header class="head">
      <div class="who">
        <div class="name-line">
          <TeamChip primary={teamMeta?.primary} secondary={teamMeta?.secondary} size={24} />
          <h2 id="team-heading">{name}</h2>
        </div>
        <p class="sub">
          {when}{#if !latest}<span class="sep" aria-hidden="true">·</span><a href={teamHash(team)}>Now</a>{/if}
        </p>
        <p class="sub"><span>{record}</span><span class="sep" aria-hidden="true">·</span><span>Rank #{row.rank}</span></p>
      </div>
      <div class="score-cell">
        <span class="score"><span class="visually-hidden">Score </span>{ok(row.score) ? row.score : '–'}</span>
        <Delta value={row.score_delta} kind="score" />
      </div>
      <div class="mood"><MoodLabel emoji={row.emoji} label={row.label} size="heading" /></div>
    </header>

    {#if row.blurb}<p class="blurb">{row.blurb}</p>{/if}

    <div class="columns">
      <section class="block" aria-labelledby="why-heading">
        <h3 id="why-heading">Score breakdown</h3>
        <FactorBars points={row.points} factors={meta.factors ?? []} {baseline} score={row.score} />
      </section>

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
          <Sparkline {series} primary={teamMeta?.primary} secondary={teamMeta?.secondary} />
        {/if}
        <a class="more" href={historyHash(team)}>Mood over time →</a>
      </section>
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
    font-weight: var(--weight-semibold);
    overflow-wrap: anywhere;
  }
  .sub {
    color: var(--text-muted);
    font-size: var(--text-label);
    line-height: var(--lh-label);
    font-variant-numeric: tabular-nums;
  }
  /* Svelte trims whitespace inside elements, so the separator gets its spacing from margin */
  .sep {
    margin-inline: var(--space-xs);
  }
  .score-cell {
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
  .mood {
    grid-column: 1 / -1;
    display: flex;
    min-width: 0;
  }
  .blurb {
    font-size: var(--text-body);
    line-height: var(--lh-body);
  }
  .columns {
    display: flex;
    flex-direction: column;
    gap: var(--space-xl);
    min-width: 0;
  }
  .block {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
    min-width: 0;
  }
  h3 {
    font-size: var(--text-heading);
    line-height: var(--lh-heading);
    font-weight: var(--weight-semibold);
  }
  .spark-heading {
    margin-top: var(--space-md);
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
      gap: var(--space-2xl);
    }
  }
</style>

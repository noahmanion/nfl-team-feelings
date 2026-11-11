// Pure helpers for the team deep-dive page (SITE-02). No DOM, no fetch.
import type { FactorMeta, GamesFile, Meta, Row, SeasonFile } from './types'

export interface RecentGame {
  season: number
  week: number
  opp: string
  home: boolean
  neutral: boolean
  result: 'W' | 'L' | 'T'
  pf: number
  pa: number
  margin: number
}

/**
 * The team's last n played games as of (season, week), newest first. A game is eligible when
 * it is from an earlier season, or from this season with asof_week <= week (so the week-9 page
 * never shows a week-10 result even though the file holds the whole schedule). Unplayed games
 * (null scores) are skipped. Pass the current and previous season files to cross into last season.
 */
export function recentGames(files: GamesFile[], team: string, season: number, week: number, n = 6): RecentGame[] {
  const out: (RecentGame & { day: string })[] = []
  for (const f of files) {
    if (f.season > season) continue
    for (let i = 0; i < f.week.length; i++) {
      const isHome = f.home[i] === team
      if (!isHome && f.away[i] !== team) continue
      if (f.season === season && f.asof_week[i] > week) continue
      const hs = f.home_score[i]
      const as = f.away_score[i]
      if (hs == null || as == null) continue
      const pf = isHome ? hs : as
      const pa = isHome ? as : hs
      out.push({
        season: f.season,
        week: f.week[i],
        opp: isHome ? f.away[i] : f.home[i],
        home: isHome,
        neutral: !!f.neutral?.[i],
        result: pf > pa ? 'W' : pf < pa ? 'L' : 'T',
        pf,
        pa,
        margin: pf - pa,
        day: f.gameday?.[i] ?? '',
      })
    }
  }
  out.sort((a, b) => b.season - a.season || (a.day < b.day ? 1 : a.day > b.day ? -1 : 0) || b.week - a.week)
  return out.slice(0, n).map(({ day: _day, ...g }) => g)
}

export interface BarRow {
  key: string
  label: string
  description: string
  points: number
}

/**
 * Factor bars: every factor in meta order (missing points count as 0), sorted by |points| desc
 * with meta order as the tiebreak. All of them are shown, so the visible bars plus the baseline
 * add up to the score. scale = max(1, max|points|) so the largest bar spans half the track.
 */
export function barRows(points: Record<string, number>, factors: FactorMeta[]): { rows: BarRow[]; scale: number } {
  const rows = factors.map((f, i) => {
    const p = points[f.key]
    return { i, key: f.key, label: f.label, description: f.description, points: typeof p === 'number' && Number.isFinite(p) ? p : 0 }
  })
  rows.sort((a, b) => Math.abs(b.points) - Math.abs(a.points) || a.i - b.i)
  const clean = rows.map(({ i: _i, ...r }) => r)
  const scale = Math.max(1, ...clean.map((r) => Math.abs(r.points)))
  return { rows: clean, scale }
}

export const findTeamRow = (file: SeasonFile, team: string, week: number): Row | undefined =>
  file.weeks[String(week)]?.find((r) => r.franchise === team)

/** This season's score per week for one team, sorted by week. Weeks without a row are skipped. */
export function seasonSeries(file: SeasonFile, team: string): { week: number; score: number }[] {
  const out: { week: number; score: number }[] = []
  for (const [w, rows] of Object.entries(file.weeks)) {
    const r = rows.find((x) => x.franchise === team)
    if (r && typeof r.score === 'number' && Number.isFinite(r.score)) out.push({ week: Number(w), score: r.score })
  }
  return out.sort((a, b) => a.week - b.week)
}

/** Integer with an explicit sign: '+12', '−7' (U+2212), '0'. */
export const signed = (n: number): string => (n > 0 ? `+${n}` : n < 0 ? `−${Math.abs(n)}` : '0')

/**
 * Sparkline y-domain: the season's score range padded by max(3, 15% of the range), clamped to
 * 0..100, so a team moving 85 -> 96 is visible instead of a flat line on a fixed 0..100 scale.
 * lo/hi are the real extremes (for the min/max labels).
 */
export function sparkDomain(series: { score: number }[]): { lo: number; hi: number; domain: [number, number] } {
  const scores = series.map((p) => p.score)
  const lo = Math.min(...scores)
  const hi = Math.max(...scores)
  const pad = Math.max(3, (hi - lo) * 0.15)
  return { lo, hi, domain: [Math.max(0, lo - pad), Math.min(100, hi + pad)] }
}

/** Team-page stat for the row's playoff odds (already an integer 0–100); null when unknown. */
export function playoffText(p: number | null | undefined): string | null {
  if (typeof p !== 'number' || !Number.isFinite(p)) return null
  return `Playoff odds ${Math.round(p)}%`
}

/**
 * The (season, week) one step before (dir -1) or after (dir +1) the given one, crossing season
 * boundaries (week 0 <-> the previous season's last week). Never steps past meta.latest or before
 * the first season. null when there is no such week.
 */
export function stepWeek(meta: Meta, season: number, week: number, dir: -1 | 1): { season: number; week: number } | null {
  const seasons = [...meta.seasons].sort((a, b) => a.season - b.season)
  const i = seasons.findIndex((s) => s.season === season)
  if (i < 0) return null
  let next: { season: number; week: number } | null
  if (dir === -1) {
    next = week > 0 ? { season, week: week - 1 } : i > 0 ? { season: seasons[i - 1].season, week: seasons[i - 1].max_week } : null
  } else {
    next = week < seasons[i].max_week ? { season, week: week + 1 } : i < seasons.length - 1 ? { season: seasons[i + 1].season, week: 0 } : null
  }
  if (!next) return null
  const { season: ls, week: lw } = meta.latest
  return next.season > ls || (next.season === ls && next.week > lw) ? null : next
}

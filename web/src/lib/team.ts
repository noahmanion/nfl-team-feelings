// Pure helpers for the team deep-dive page (SITE-02). No DOM, no fetch.
import type { FactorMeta, GamesFile, Row, SeasonFile } from './types'

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
 * with meta order as the tiebreak. Top `top` are shown, the rest go under "All factors".
 * scale = max(1, max|points|) so the largest bar spans half the track.
 */
export function barRows(
  points: Record<string, number>,
  factors: FactorMeta[],
  baseline: number,
  top = 4,
): { shown: BarRow[]; rest: BarRow[]; scale: number; total: number } {
  const rows = factors.map((f, i) => {
    const p = points[f.key]
    return { i, key: f.key, label: f.label, description: f.description, points: typeof p === 'number' && Number.isFinite(p) ? p : 0 }
  })
  rows.sort((a, b) => Math.abs(b.points) - Math.abs(a.points) || a.i - b.i)
  const clean = rows.map(({ i: _i, ...r }) => r)
  const scale = Math.max(1, ...clean.map((r) => Math.abs(r.points)))
  const total = baseline + clean.reduce((s, r) => s + r.points, 0)
  return { shown: clean.slice(0, top), rest: clean.slice(top), scale, total }
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

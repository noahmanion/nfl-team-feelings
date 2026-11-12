import type { EpaFile } from './types'

/** Season-to-date efficiency for one franchise. Means are play-weighted; null when no plays. */
export interface EpaAgg {
  off_epa: number | null
  def_epa: number | null
  off_sr: number | null
  def_sr: number | null
  off_plays: number
  def_plays: number
  games: number
}

/** Play-weighted season-to-date EPA/play and success rate per franchise over rows with week <= `week`
 * (offense weighted by off_plays, defense by def_plays). Franchises with no such rows are absent. */
export function seasonToDate(f: EpaFile, week: number): Record<string, EpaAgg> {
  const acc: Record<string, { oe: number; de: number; os: number; ds: number; op: number; dp: number; g: number }> = {}
  for (let i = 0; i < f.franchise.length; i++) {
    if (f.week[i] > week) continue
    const a = (acc[f.franchise[i]] ??= { oe: 0, de: 0, os: 0, ds: 0, op: 0, dp: 0, g: 0 })
    const op = f.off_plays[i]
    const dp = f.def_plays[i]
    a.g += 1
    if (op > 0) {
      a.oe += f.off_epa[i] * op
      a.os += f.off_sr[i] * op
      a.op += op
    }
    if (dp > 0) {
      a.de += f.def_epa[i] * dp
      a.ds += f.def_sr[i] * dp
      a.dp += dp
    }
  }
  const out: Record<string, EpaAgg> = {}
  for (const [team, a] of Object.entries(acc)) {
    out[team] = {
      off_epa: a.op > 0 ? a.oe / a.op : null,
      off_sr: a.op > 0 ? a.os / a.op : null,
      def_epa: a.dp > 0 ? a.de / a.dp : null,
      def_sr: a.dp > 0 ? a.ds / a.dp : null,
      off_plays: a.op,
      def_plays: a.dp,
      games: a.g,
    }
  }
  return out
}

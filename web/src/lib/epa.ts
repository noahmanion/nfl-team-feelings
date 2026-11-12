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
  // separate denominators per rate (WR-05): a null rate is skipped, never counted as 0
  type Acc = { oe: number; de: number; os: number; ds: number; oep: number; dep: number; osp: number; dsp: number
    op: number; dp: number; g: number }
  const acc: Record<string, Acc> = {}
  for (let i = 0; i < f.franchise.length; i++) {
    if (f.week[i] > week) continue
    const a = (acc[f.franchise[i]] ??= { oe: 0, de: 0, os: 0, ds: 0, oep: 0, dep: 0, osp: 0, dsp: 0, op: 0, dp: 0, g: 0 })
    const op = f.off_plays[i] ?? 0
    const dp = f.def_plays[i] ?? 0
    const oe = f.off_epa[i], os = f.off_sr[i], de = f.def_epa[i], ds = f.def_sr[i]
    a.g += 1
    if (op > 0) {
      a.op += op
      if (oe != null) { a.oe += oe * op; a.oep += op }
      if (os != null) { a.os += os * op; a.osp += op }
    }
    if (dp > 0) {
      a.dp += dp
      if (de != null) { a.de += de * dp; a.dep += dp }
      if (ds != null) { a.ds += ds * dp; a.dsp += dp }
    }
  }
  const out: Record<string, EpaAgg> = {}
  for (const [team, a] of Object.entries(acc)) {
    out[team] = {
      off_epa: a.oep > 0 ? a.oe / a.oep : null,
      off_sr: a.osp > 0 ? a.os / a.osp : null,
      def_epa: a.dep > 0 ? a.de / a.dep : null,
      def_sr: a.dsp > 0 ? a.ds / a.dsp : null,
      off_plays: a.op,
      def_plays: a.dp,
      games: a.g,
    }
  }
  return out
}

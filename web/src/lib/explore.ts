// Pure logic for the Explore page (EXPL-02 EPA scatter, EXPL-03 record vs evidence). The Svelte
// components stay thin: every number, rank, join, line fit, empty-state decision and copy string
// they show comes from here.

import type { EpaAgg } from './epa'
import { logoSrc } from './logos'
import { eraAbbr, eraName, eraText, isActiveFranchise } from './teamNames'
import type { EpaFile, Meta, Row } from './types'

export interface EpaPoint { franchise: string; abbr: string; name: string; src: string | null; off: number; def: number;
  offSr: number | null; defSr: number | null; net: number; offRank: number; defRank: number; games: number;
  wins: number; losses: number; ties: number }
export interface RecordPoint { franchise: string; abbr: string; name: string; nick: string; src: string | null;
  x: number; y: number; wins: number; losses: number; ties: number; gp: number; label: string; emoji: string;
  gap: number | null }
/** y = a + b·x */
export interface Line { a: number; b: number }
export type EpaEmpty = 'no-games' | 'no-pbp' | 'no-week' | null

const MINUS = '−'
const EN = '–'

/**
 * Regular-season-only view of an EpaFile. The Explore EPA chart is regular season only, so EPA,
 * the games count and the W–L record (frozen at the regular-season record in playoff weeks) all
 * describe the same games. In playoff weeks the chart shows the full regular season.
 */
export const regOnly = (f: EpaFile): EpaFile => {
  const keep = f.game_type.map((t, i) => (t === 'REG' ? i : -1)).filter((i) => i >= 0)
  const pick = <T,>(a: T[]) => keep.map((i) => a[i])
  return { ...f, game_id: pick(f.game_id), week: pick(f.week), game_type: pick(f.game_type), franchise: pick(f.franchise),
    opponent: pick(f.opponent), off_epa: pick(f.off_epa), off_plays: pick(f.off_plays), off_sr: pick(f.off_sr),
    def_epa: pick(f.def_epa), def_plays: pick(f.def_plays), def_sr: pick(f.def_sr) }
}

/** Competition ranking (1, 2, 2, 4): rank = 1 + number of strictly better values. */
export function competitionRank(values: number[], desc: boolean): number[] {
  return values.map((v) => 1 + values.filter((o) => (desc ? o > v : o < v)).length)
}

/** Inner join of snapshot rows and season-to-date EPA; teams without both rates are dropped. */
export function epaPoints(rows: Row[], agg: Record<string, EpaAgg>, season: number, meta: Pick<Meta, 'teams'>): EpaPoint[] {
  const base = rows.flatMap((r) => {
    const a = agg[r.franchise]
    if (!a || !isActiveFranchise(r.franchise, season) || a.off_epa == null || a.def_epa == null) return []
    return [{ r, a, off: a.off_epa, def: a.def_epa }]
  })
  const offRanks = competitionRank(base.map((b) => b.off), true)
  const defRanks = competitionRank(base.map((b) => b.def), false)
  return base.map(({ r, a, off, def }, i) => ({
    franchise: r.franchise, abbr: eraAbbr(r.franchise, season), name: eraName(r.franchise, season, meta),
    src: logoSrc(r.franchise), off, def, offSr: a.off_sr, defSr: a.def_sr, net: off - def,
    offRank: offRanks[i], defRank: defRanks[i], games: a.games, wins: r.wins, losses: r.losses, ties: r.ties,
  }))
}

/** Play-weighted league means (offense by off_plays, defense by def_plays); null rates are skipped. */
export function leagueMeans(aggs: EpaAgg[]): { off: number | null; def: number | null } {
  let oe = 0, op = 0, de = 0, dp = 0
  for (const a of aggs) {
    if (a.off_epa != null && a.off_plays > 0) { oe += a.off_epa * a.off_plays; op += a.off_plays }
    if (a.def_epa != null && a.def_plays > 0) { de += a.def_epa * a.def_plays; dp += a.def_plays }
  }
  return { off: op > 0 ? oe / op : null, def: dp > 0 ? de / dp : null }
}

/** (W + 0.5·T) / GP; null with no games. */
export function winPct(w: number, l: number, t: number): number | null {
  const gp = w + l + t
  return gp === 0 ? null : (w + 0.5 * t) / gp
}

/** Win % (x) against feel-good score (y); teams with no games and HOU before 2002 are excluded. */
export function recordPoints(rows: Row[], season: number, meta: Pick<Meta, 'teams'>): RecordPoint[] {
  return rows.flatMap((r) => {
    const x = winPct(r.wins, r.losses, r.ties)
    if (x == null || !isActiveFranchise(r.franchise, season)) return []
    return [{ franchise: r.franchise, abbr: eraAbbr(r.franchise, season), name: eraName(r.franchise, season, meta),
      nick: meta.teams[r.franchise]?.nick ?? r.franchise, src: logoSrc(r.franchise), x, y: r.score,
      wins: r.wins, losses: r.losses, ties: r.ties, gp: r.wins + r.losses + r.ties, label: r.label, emoji: r.emoji,
      gap: null }]
  })
}

/** Least squares of y on x; null for fewer than 3 points or zero x-variance. */
export function fitLine(pts: { x: number; y: number }[]): Line | null {
  const n = pts.length
  if (n < 3) return null
  const mx = pts.reduce((s, p) => s + p.x, 0) / n
  const my = pts.reduce((s, p) => s + p.y, 0) / n
  const sxx = pts.reduce((s, p) => s + (p.x - mx) ** 2, 0)
  if (sxx === 0) return null
  const b = pts.reduce((s, p) => s + (p.x - mx) * (p.y - my), 0) / sxx
  return { a: my - b * mx, b }
}

/** gap = score minus the typical score for that win % (null without a line). */
export function withGaps(points: RecordPoint[], line: Line | null): RecordPoint[] {
  return points.map((p) => ({ ...p, gap: line ? p.y - (line.a + line.b * p.x) : null }))
}

/** Generated record dek naming the biggest gaps either way, or the neutral fallback. */
export function recordDek(points: RecordPoint[], line: Line | null, season: number, weekLabelText: string,
  meta: Pick<Meta, 'teams'>): string {
  const fallback = `Win percentage against feel-good score, ${season} through ${weekLabelText}.`
  if (!line) return fallback
  let hi: RecordPoint | null = null, lo: RecordPoint | null = null
  for (const p of points) {
    if (p.gap == null) continue
    if (p.gap > 0 && (!hi || p.gap > hi.gap!)) hi = p
    if (p.gap < 0 && (!lo || p.gap < lo.gap!)) lo = p
  }
  if (!hi || !lo || (Math.abs(hi.gap!) < 1 && Math.abs(lo.gap!) < 1)) return fallback
  const nick = (p: RecordPoint) => meta.teams[p.franchise]?.nick ?? p.nick
  const a = eraText(`The ${nick(hi)} look better than their ${recordText(hi.wins, hi.losses, hi.ties)} record`, hi.franchise, season)
  const b = eraText(`the ${nick(lo)} look worse than theirs.`, lo.franchise, season)
  return `${a}; ${b}`
}

const snap = (v: number) => Math.round(v * 100) / 100

/** Data extent padded by 0.03, then expanded outward to the nearest 0.05. */
export function paddedDomain(min: number, max: number): [number, number] {
  const lo = Math.floor((min - 0.03) / 0.05 + 1e-9) * 0.05
  const hi = Math.ceil((max + 0.03) / 0.05 - 1e-9) * 0.05
  return [snap(lo) + 0, snap(hi) + 0]
}

/** Axis ticks: step 0.1 for a span of at least 0.3, else 0.05; at most 6 ticks below 640px. */
export function epaTicks([d0, d1]: [number, number], width: number): number[] {
  const step = d1 - d0 >= 0.3 - 1e-9 ? 0.1 : 0.05
  const k0 = Math.ceil(d0 / step - 1e-9), k1 = Math.floor(d1 / step + 1e-9)
  let ks: number[] = []
  for (let k = k0; k <= k1; k++) ks.push(k)
  let mult = 2
  while (width < 640 && ks.length > 6) {
    const m = mult
    ks = ks.filter((k) => k % m === 0)
    mult *= 2
  }
  return ks.map((k) => snap(k * step) + 0)
}

/** Tier diagonals: off − def = c for every multiple of 0.1 crossing the frame (slope 1). */
export function diagonals([x0, x1]: [number, number], [y0, y1]: [number, number]) {
  const out: { x1: number; y1: number; x2: number; y2: number }[] = []
  for (let k = Math.ceil((x0 - y1) / 0.1 - 1e-9); k <= Math.floor((x1 - y0) / 0.1 + 1e-9); k++) {
    const c = k / 10
    out.push({ x1: x0, y1: x0 - c, x2: x1, y2: x1 - c })
  }
  return out
}

/** "+0.123" / "−0.05" (U+2212) / "0.00"; a value that rounds to zero is unsigned. */
export function signed(v: number, dp: number): string {
  const s = Math.abs(v).toFixed(dp)
  if (Number(s) === 0) return s
  return (v > 0 ? '+' : MINUS) + s
}

export const pct = (v: number, dp: number): string => `${(v * 100).toFixed(dp)}%`
export const gapText = (v: number): string => `${signed(v, 1)} pts`
/** En-dash record: "6–2", "6–2–1" (formatRecord in format.ts keeps its hyphen). */
export const recordText = (w: number, l: number, t: number): string => (t > 0 ? `${w}${EN}${l}${EN}${t}` : `${w}${EN}${l}`)
/** clamp(width × 0.8, 320, 560) */
export const chartHeight = (w: number): number => Math.min(560, Math.max(320, Math.round(w * 0.8)))

/** Click-through: mouse navigates at once; touch arms on the first tap, navigates on a second tap of the same team. */
export function tapAction(pointerType: string, armed: string | null, picked: string | null): { go: boolean; armed: string | null } {
  if (!picked) return { go: false, armed: null }
  if (pointerType === 'mouse') return { go: true, armed: null }
  return picked === armed ? { go: true, armed: null } : { go: false, armed: picked }
}

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`
const pctOrDash = (v: number | null) => (v == null ? EN : pct(v, 1))

export function epaTip(p: EpaPoint): string {
  return [
    p.name,
    `Offense ${signed(p.off, 3)} EPA/play · #${p.offRank}`,
    `Defense ${signed(p.def, 3)} allowed · #${p.defRank}`,
    `Success ${pctOrDash(p.offSr)} off · ${pctOrDash(p.defSr)} def`,
    `${recordText(p.wins, p.losses, p.ties)} · ${plural(p.games, 'game')}`,
  ].join('\n')
}

export function recordTip(p: RecordPoint): string {
  const lines = [p.name, `${recordText(p.wins, p.losses, p.ties)} · ${pct(p.x, 1)}`, `Score ${p.y} · ${p.emoji} ${p.label}`]
  if (p.gap != null) lines.push(`${gapText(p.gap)} vs typical for this record`)
  return lines.join('\n')
}

export function epaEmpty(args: { season: number; week: number; gamesPlayed: number; epaSeasons?: number[]; nPoints: number }): EpaEmpty {
  if (args.week === 0 || args.gamesPlayed === 0) return 'no-games'
  if (!args.epaSeasons || !args.epaSeasons.includes(args.season)) return 'no-pbp'
  if (args.nPoints === 0) return 'no-week'
  return null
}

export function emptyCopy(kind: Exclude<EpaEmpty, null>, season: number, weekLabelText: string, firstEpaSeason: number): string {
  if (kind === 'no-games') return `No games played yet in ${season}. Pick a later week.`
  if (kind === 'no-pbp') return `No play-by-play efficiency data for ${season}. Pick ${firstEpaSeason} or later.`
  return `No efficiency data through ${weekLabelText} yet. Check back after the play-by-play update.`
}

// Pure helpers for the mood-over-time chart (SITE-03). No DOM, no Plot import.
import type { HistoryFile, Row } from './types'

export interface ChartRow { team: string; x: number; y: number }
export interface SeasonStart { season: number; x: number }
export interface Point { score: number; key: string }

export const seasonOf = (key: string): number => Number(key.split('-')[0])
export const weekOf = (key: string): number => Number(key.split('-')[1])

/**
 * Tidy rows for Plot. x advances by 1 per key, plus one empty slot at each season
 * boundary; every team gets a NaN row in that slot so Plot breaks the line there.
 * Null scores become NaN (also a break).
 */
export function toRows(h: HistoryFile): { rows: ChartRow[]; xs: number[]; xMax: number } {
  const xs: number[] = []
  let x = 0
  let prev: number | null = null
  for (const k of h.keys) {
    const s = seasonOf(k)
    if (prev !== null && s !== prev) x += 1
    xs.push(x)
    x += 1
    prev = s
  }
  const rows: ChartRow[] = []
  for (const [team, scores] of Object.entries(h.teams)) {
    for (let i = 0; i < h.keys.length; i++) {
      if (i > 0 && seasonOf(h.keys[i]) !== seasonOf(h.keys[i - 1])) rows.push({ team, x: xs[i] - 1, y: NaN })
      const v = scores[i]
      rows.push({ team, x: xs[i], y: v == null ? NaN : v })
    }
  }
  return { rows, xs, xMax: xs.length ? xs[xs.length - 1] : 0 }
}

export interface Connector { team: string; x1: number; y1: number; x2: number; y2: number }

/**
 * One segment per team per season boundary: from the team's last non-null score of season S
 * (searched within S only) to week 0 of S+1. No segment when either end is missing.
 * toRows keeps its NaN gap; these are drawn on top as the dashed offseason move.
 */
export function connectors(h: HistoryFile, xs: number[], team?: string): Connector[] {
  const out: Connector[] = []
  for (const [t, scores] of Object.entries(h.teams)) {
    if (team && t !== team) continue
    for (let i = 1; i < h.keys.length; i++) {
      const prevSeason = seasonOf(h.keys[i - 1])
      if (seasonOf(h.keys[i]) === prevSeason) continue
      let a = i - 1
      while (a >= 0 && seasonOf(h.keys[a]) === prevSeason && scores[a] == null) a--
      if (a < 0 || seasonOf(h.keys[a]) !== prevSeason) continue
      const y1 = scores[a]
      const y2 = scores[i]
      if (y1 == null || y2 == null) continue
      out.push({ team: t, x1: xs[a], y1, x2: xs[i], y2 })
    }
  }
  return out
}

/** x of each season's first key, in key order. */
export function seasonStarts(h: HistoryFile, xs: number[]): SeasonStart[] {
  const out: SeasonStart[] = []
  h.keys.forEach((k, i) => {
    const s = seasonOf(k)
    if (!out.length || out[out.length - 1].season !== s) out.push({ season: s, x: xs[i] })
  })
  return out
}

/**
 * Season ticks: every 2nd season at >= 500px wide, every 5th below. The first season
 * is added only when it is at least `every` seasons before the next tick, so no two
 * ticks are ever closer than the step (1999 and 2000 would otherwise overlap).
 */
export function tickSeasons(starts: SeasonStart[], width: number): SeasonStart[] {
  if (!starts.length) return []
  const every = width >= 500 ? 2 : 5
  const picked = starts.filter((d) => d.season % every === 0)
  const first = starts[0]
  if (!picked.length || (picked[0] !== first && picked[0].season - first.season >= every)) picked.unshift(first)
  return picked
}

// ---- colour contrast (WCAG 2.x) ----

/** Parse '#rgb' or '#rrggbb' (whitespace tolerated). Anything else returns null. */
export function parseHex(value: string | null | undefined): [number, number, number] | null {
  if (typeof value !== 'string') return null
  const v = value.trim()
  let m = /^#([0-9a-f])([0-9a-f])([0-9a-f])$/i.exec(v)
  if (m) return [m[1], m[2], m[3]].map((c) => parseInt(c + c, 16)) as [number, number, number]
  m = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(v)
  if (m) return [m[1], m[2], m[3]].map((c) => parseInt(c, 16)) as [number, number, number]
  return null
}

export function relLuminance(hex: string): number {
  const rgb = parseHex(hex)
  if (!rgb) return NaN
  const [r, g, b] = rgb.map((c) => {
    const s = c / 255
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

/** WCAG contrast ratio, 1..21. NaN when either colour is not a hex value. */
export function contrastRatio(a: string, b: string): number {
  const la = relLuminance(a)
  const lb = relLuminance(b)
  if (Number.isNaN(la) || Number.isNaN(lb)) return NaN
  const [hi, lo] = la > lb ? [la, lb] : [lb, la]
  return (hi + 0.05) / (lo + 0.05)
}

// Mirrors --bg in app.css; used when the computed token can't be parsed as hex.
export const FALLBACK_BG = { light: '#ffffff', dark: '#141414' } as const

/**
 * Which colour to draw the highlighted team in: primary, else secondary, else the
 * text colour, using a 3:1 contrast threshold against the page background.
 * A background that isn't parseable hex falls back to the known light/dark --bg;
 * a team colour that isn't parseable hex counts as failing.
 */
export function pickHighlight(primary: string, secondary: string, bg: string, dark = false): 'primary' | 'secondary' | 'text' {
  const base = parseHex(bg) ? bg.trim() : dark ? FALLBACK_BG.dark : FALLBACK_BG.light
  const ok = (c: string) => contrastRatio(c, base) >= 3 // NaN >= 3 is false
  if (ok(primary)) return 'primary'
  if (ok(secondary)) return 'secondary'
  return 'text'
}

/**
 * The highlight stroke for a team: its primary (or secondary) colour when that clears 3:1 on the
 * page background; otherwise the primary tinted toward white (dark mode) or black (light mode)
 * in 10% steps until it does, so the highlighted team always keeps a team hue (UI review fix).
 * Returns 'var(--text)' only when no team colour parses.
 */
export function highlightColor(primary: string, secondary: string, bg: string, dark = false): string {
  const pick = pickHighlight(primary, secondary, bg, dark)
  if (pick === 'primary') return primary.trim()
  if (pick === 'secondary') return secondary.trim()
  const base = parseHex(bg) ? bg.trim() : dark ? FALLBACK_BG.dark : FALLBACK_BG.light
  const rgb = parseHex(primary) ?? parseHex(secondary)
  if (!rgb) return 'var(--text)'
  const target = dark ? 255 : 0
  const hex = (c: number[]) => '#' + c.map((v) => Math.round(v).toString(16).padStart(2, '0')).join('')
  for (let t = 0.1; t <= 1.0001; t += 0.1) {
    const c = hex(rgb.map((v) => v + (target - v) * t))
    if (contrastRatio(c, base) >= 3) return c
  }
  return 'var(--text)'
}

// ---- summary points ----

/** Minimum non-null score; earliest key on ties. */
export function lowPoint(h: HistoryFile, team: string): Point | null {
  const scores = h.teams[team]
  if (!scores) return null
  let best: Point | null = null
  scores.forEach((v, i) => {
    if (v == null) return
    if (!best || v < best.score) best = { score: v, key: h.keys[i] }
  })
  return best
}

/** Last non-null score. */
export function currentPoint(h: HistoryFile, team: string): Point | null {
  const scores = h.teams[team]
  if (!scores) return null
  for (let i = scores.length - 1; i >= 0; i--) {
    const v = scores[i]
    if (v != null) return { score: v, key: h.keys[i] }
  }
  return null
}

/** My team when it is on the latest board, else the top team. */
export const defaultTeam = (latestRows: Row[], myTeam?: string | null): string | undefined =>
  (myTeam && latestRows.some((r) => r.franchise === myTeam) ? myTeam : undefined) ?? latestRows[0]?.franchise

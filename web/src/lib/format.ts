import type { Band, SeasonMeta } from './types'

// Fallback only: the pipeline emits week_labels per season (labels come from game_type there).
const POSTSEASON = ['Wild Card', 'Divisional', 'Conference Championships', 'Super Bowl']

export function weekLabel(week: number, season: SeasonMeta): string {
  const fromData = season.week_labels?.[String(week)]
  if (fromData) return fromData
  if (week === 0) return 'Preseason'
  if (week <= season.reg_weeks) return `Week ${week}`
  return POSTSEASON[week - season.reg_weeks - 1] ?? `Week ${week}`
}

export function formatRecord(wins: number, losses: number, ties: number): string {
  return ties > 0 ? `${wins}-${losses}-${ties}` : `${wins}-${losses}`
}

export type DeltaDir = 'up' | 'down' | 'none'

export function formatDelta(value: number | null | undefined): { text: string; dir: DeltaDir } {
  if (value == null || !Number.isFinite(value) || value === 0) return { text: '–', dir: 'none' }
  return value > 0 ? { text: `▲ ${value}`, dir: 'up' } : { text: `▼ ${Math.abs(value)}`, dir: 'down' }
}

const dateTime = new Intl.DateTimeFormat('en-US', {
  month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit',
})
const dateOnly = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' })

/** ISO timestamp -> "Nov 11, 2026, 9:42 AM" in the viewer's local time zone. */
export function formatDate(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : dateTime.format(d).replace(/ /g, ' ')
}

/** "YYYY-MM-DD" -> "Nov 9, 2026". Parsed as a local calendar date so it never shifts a day. */
export function formatDateOnly(ymd: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(ymd)
  if (!m) return ymd
  return dateOnly.format(new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])))
}

/** The row's band index (hysteresis-adjusted, from the export) if it is a valid index into bands, else -1. */
export function bandIndex(band: unknown, bands: Band[]): number {
  return typeof band === 'number' && Number.isInteger(band) && band >= 0 && band < bands.length ? band : -1
}

/** Map band index i of n bands onto the 7 --mood-N tokens. */
export function moodToken(i: number, n: number): number {
  return n <= 1 ? 0 : Math.round((i * 6) / (n - 1))
}

const POSTSEASON_TICKS = ['WC', 'Div', 'Conf', 'SB']

/** Short label under the slider track: "Pre", "Wk N", "WC", "Div", "Conf", "SB". Uses meta's reg_weeks. */
export function tickLabel(week: number, season: SeasonMeta): string {
  if (week === 0) return 'Pre'
  if (week <= season.reg_weeks) return `Wk ${week}`
  return POSTSEASON_TICKS[week - season.reg_weeks - 1] ?? `Wk ${week}`
}

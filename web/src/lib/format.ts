import type { Band, Row, SeasonMeta } from './types'

// Fallback only: the pipeline emits week_labels per season (labels come from game_type there).
const POSTSEASON = ['Wild Card', 'Divisional', 'Conference Championships', 'Super Bowl']

export function weekLabel(week: number, season: SeasonMeta): string {
  const fromData = season.week_labels?.[String(week)]
  if (fromData) return fromData
  if (week === 0) return 'Preseason'
  if (week <= season.reg_weeks) return `Week ${week}`
  return POSTSEASON[week - season.reg_weeks - 1] ?? `Week ${week}`
}

/**
 * Carry a week across a season change by meaning, not by number (reg_weeks differs by era):
 * preseason stays preseason, a regular-season week clamps to the new season's last regular week,
 * and a playoff round maps to the same round (Super Bowl -> Super Bowl). The result is clamped to
 * the new season's max_week, so an in-progress season lands on its latest week.
 */
export function carryWeek(week: number, from: SeasonMeta | undefined, to: SeasonMeta): number {
  const reg = from?.reg_weeks ?? to.reg_weeks
  const mapped = week <= 0 ? 0 : week <= reg ? Math.min(week, to.reg_weeks) : to.reg_weeks + (week - reg)
  return Math.max(0, Math.min(mapped, to.max_week))
}

export function formatRecord(wins: number, losses: number, ties: number): string {
  return ties > 0 ? `${wins}-${losses}-${ties}` : `${wins}-${losses}`
}

export type DeltaDir = 'up' | 'down' | 'none'

export function formatDelta(value: number | null | undefined): { text: string; dir: DeltaDir } {
  if (value == null || !Number.isFinite(value) || value === 0) return { text: '–', dir: 'none' }
  return value > 0 ? { text: `▲ ${value}`, dir: 'up' } : { text: `▼ ${Math.abs(value)}`, dir: 'down' }
}

const isNum = (n: unknown): n is number => typeof n === 'number' && Number.isFinite(n)
const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

/**
 * Board rank change in words: "▲1 spot" / "▼2 spots" / "no change", plus a screen-reader label.
 * A missing delta (no prior snapshot) is unknown, not unchanged: it renders "–" like formatDelta.
 */
export function formatRankDelta(value: number | null | undefined): { text: string; dir: DeltaDir; aria: string } {
  if (!isNum(value)) return { text: '–', dir: 'none', aria: 'No prior rank' }
  if (value === 0) return { text: 'no change', dir: 'none', aria: 'No change in rank' }
  const n = Math.abs(value)
  return value > 0
    ? { text: `▲${plural(n, 'spot')}`, dir: 'up', aria: `Up ${plural(n, 'spot')} in rank` }
    : { text: `▼${plural(n, 'spot')}`, dir: 'down', aria: `Down ${plural(n, 'spot')} in rank` }
}

/**
 * Board change sentence (screen-reader text). In season: vs last week. At week 0 the deltas
 * are vs the franchise's last snapshot of the prior season (07-04); null there (first season,
 * expansion team, or older data) reads as "No change, preseason."; a null delta in season reads
 * "No change from last week."
 */
export function changeText(r: Pick<Row, 'score_delta' | 'rank_delta'>, week: number): string {
  const pre = week === 0
  if (!isNum(r.score_delta)) return pre ? 'No change, preseason.' : 'No change from last week.'
  const sd = r.score_delta
  const rd = isNum(r.rank_delta) ? r.rank_delta : 0
  if (sd === 0 && rd === 0) return pre ? 'No change from the end of last season.' : 'No change from last week.'
  const score = sd > 0 ? `Up ${plural(sd, 'point')}` : sd < 0 ? `Down ${plural(-sd, 'point')}` : 'Same score'
  const rank = rd > 0 ? `up ${plural(rd, 'spot')}` : rd < 0 ? `down ${plural(-rd, 'spot')}` : 'same spot'
  return `${score}, ${rank}${pre ? ' vs end of last season.' : ' from last week.'}`
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

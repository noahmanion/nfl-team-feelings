// Formatting helpers for records.json (08-04): the records page and the team-page streak line.
import type { ActiveStreak, SeasonRecord } from './types'

const num = new Intl.NumberFormat('en-US')
// Dates in records.json are calendar days ("YYYY-MM-DD"): parse and format both in UTC so the
// viewer's time zone can never shift them by a day.
const dateFmt = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' })

/** 1231 -> "1,231 days"; 1 -> "1 day". */
export function formatDays(days: number): string {
  return `${num.format(days)} ${days === 1 ? 'day' : 'days'}`
}

/** "2005-09-11" -> "Sep 11, 2005" in every time zone. Unparseable input is returned as is. */
export function formatDate(ymd: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(ymd)
  if (!m) return ymd
  return dateFmt.format(new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]))))
}

/** "Sep 11, 2005 – Jan 3, 2010", or "… – now" for a streak that is still going. */
export function dateRange(start: string, end: string | null): string {
  return `${formatDate(start)} – ${end ? formatDate(end) : 'now'}`
}

/** Team-page line for an active streak, or null when there is none. */
export function streakLine(a: ActiveStreak | undefined | null): string | null {
  if (!a) return null
  const days = `${num.format(a.days)} straight ${a.days === 1 ? 'day' : 'days'}`
  return a.kind === 'misery' ? `Miserable for ${days}` : `Buying the jersey for ${days}`
}

/** "2005–2009", or "2024" when the streak sits inside one season. */
export function seasonsSpan(entry: { seasons: SeasonRecord[] }): string {
  const ss = entry.seasons.map((s) => s.season)
  if (ss.length === 0) return ''
  const lo = Math.min(...ss)
  const hi = Math.max(...ss)
  return lo === hi ? String(lo) : `${lo}–${hi}`
}

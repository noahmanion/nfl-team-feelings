import { describe, expect, it } from 'vitest'
import { dateRange, formatDate, formatDays, seasonsSpan, streakLine } from './records'

describe('formatDays', () => {
  it('pluralises and adds thousands separators', () => {
    expect(formatDays(1231)).toBe('1,231 days')
    expect(formatDays(1)).toBe('1 day')
    expect(formatDays(44)).toBe('44 days')
  })
})

describe('formatDate', () => {
  it('formats a calendar date without shifting it (UTC-safe)', () => {
    expect(formatDate('2005-09-11')).toBe('Sep 11, 2005')
    expect(formatDate('2010-01-01')).toBe('Jan 1, 2010')
    expect(formatDate('2026-12-31')).toBe('Dec 31, 2026')
  })
  it('returns unparseable input unchanged', () => {
    expect(formatDate('soon')).toBe('soon')
  })
})

describe('dateRange', () => {
  it('joins start and end with an en dash', () => {
    expect(dateRange('2005-09-11', '2010-01-03')).toBe('Sep 11, 2005 – Jan 3, 2010')
  })
  it('reads "now" for an open-ended streak', () => {
    expect(dateRange('2024-10-21', null)).toBe('Oct 21, 2024 – now')
  })
})

describe('streakLine', () => {
  const base = { start: '2024-10-21', start_season: 2024, start_week: 7 }
  it('describes misery and joy streaks', () => {
    expect(streakLine({ ...base, kind: 'misery', days: 751 })).toBe('Miserable for 751 straight days')
    expect(streakLine({ ...base, kind: 'joy', days: 1150 })).toBe('Buying the jersey for 1,150 straight days')
  })
  it('is null without an active streak', () => {
    expect(streakLine(undefined)).toBeNull()
  })
})

describe('seasonsSpan', () => {
  const s = (season: number) => ({ season, wins: 0, losses: 0, ties: 0 })
  it('spans first to last season with an en dash', () => {
    expect(seasonsSpan({ seasons: [s(2005), s(2006), s(2009)] })).toBe('2005–2009')
  })
  it('shows a single season once', () => {
    expect(seasonsSpan({ seasons: [s(2024)] })).toBe('2024')
  })
})

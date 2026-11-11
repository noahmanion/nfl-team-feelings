import { describe, expect, it } from 'vitest'
import {
  bandIndex,
  carryWeek,
  formatDate,
  formatDateOnly,
  formatDelta,
  formatRecord,
  moodToken,
  tickLabel,
  weekLabel,
} from './format'
import type { Band, SeasonMeta } from './types'

const season = (s: number, reg: number, labels: Record<string, string> = {}): SeasonMeta => ({
  season: s, max_week: reg + 4, reg_weeks: reg, n_teams: 32, week_labels: labels,
})

describe('carryWeek', () => {
  const s2010 = season(2010, 17) // weeks 18-21 = WC, Div, Conf, SB
  const s2021 = season(2021, 18) // weeks 19-22 = WC, Div, Conf, SB
  const inProgress: SeasonMeta = { ...season(2026, 18), max_week: 10 }
  it('keeps the playoff round', () => {
    expect(carryWeek(21, s2010, s2021)).toBe(22) // Super Bowl -> Super Bowl
    expect(carryWeek(22, s2021, s2010)).toBe(21)
    expect(carryWeek(19, s2021, s2010)).toBe(18) // Wild Card -> Wild Card
    expect(carryWeek(18, s2010, s2021)).toBe(19)
  })
  it('clamps regular weeks to the regular season', () => {
    expect(carryWeek(18, s2021, s2010)).toBe(17) // finale -> finale, not Wild Card
    expect(carryWeek(17, s2010, s2021)).toBe(17)
    expect(carryWeek(5, s2010, s2021)).toBe(5)
  })
  it('preseason stays preseason', () => expect(carryWeek(0, s2021, s2010)).toBe(0))
  it('clamps to max_week of an in-progress season', () => {
    expect(carryWeek(21, s2010, inProgress)).toBe(10)
    expect(carryWeek(12, s2010, inProgress)).toBe(10)
    expect(carryWeek(4, s2010, inProgress)).toBe(4)
  })
})

describe('formatRecord', () => {
  it('omits ties when zero', () => expect(formatRecord(7, 2, 0)).toBe('7-2'))
  it('shows ties when present', () => expect(formatRecord(7, 2, 1)).toBe('7-2-1'))
})

describe('formatDelta', () => {
  it('up', () => expect(formatDelta(4)).toEqual({ text: '▲ 4', dir: 'up' }))
  it('down uses absolute value', () => expect(formatDelta(-7)).toEqual({ text: '▼ 7', dir: 'down' }))
  it('zero', () => expect(formatDelta(0)).toEqual({ text: '–', dir: 'none' }))
  it('null', () => expect(formatDelta(null)).toEqual({ text: '–', dir: 'none' }))
  it('NaN never renders', () => expect(formatDelta(Number.NaN)).toEqual({ text: '–', dir: 'none' }))
})

describe('weekLabel', () => {
  it('prefers week_labels from meta', () => {
    expect(weekLabel(18, season(2020, 17, { '18': 'From data' }))).toBe('From data')
  })
  it('falls back to reg_weeks', () => {
    expect(weekLabel(0, season(2020, 17))).toBe('Preseason')
    expect(weekLabel(17, season(2020, 17))).toBe('Week 17')
    expect(weekLabel(18, season(2020, 17))).toBe('Wild Card')
    expect(weekLabel(19, season(2020, 17))).toBe('Divisional')
    expect(weekLabel(20, season(2020, 17))).toBe('Conference Championships')
    expect(weekLabel(21, season(2020, 17))).toBe('Super Bowl')
    expect(weekLabel(18, season(2021, 18))).toBe('Week 18')
    expect(weekLabel(22, season(2021, 18))).toBe('Super Bowl')
  })
})

describe('dates', () => {
  it('formatDateOnly never shifts the day', () => {
    expect(formatDateOnly('2026-11-09')).toBe('Nov 9, 2026')
    expect(formatDateOnly('2026-01-01')).toBe('Jan 1, 2026')
  })
  it('formatDate renders local date and time', () => {
    const d = new Date(2026, 10, 11, 9, 42)
    expect(formatDate(d.toISOString())).toBe('Nov 11, 2026, 9:42 AM')
  })
})

describe('bands', () => {
  const bands: Band[] = ['a', 'b', 'c', 'd', 'Cautiously smug', 'f', 'g'].map((label, i) => ({
    min: i * 10, max: i * 10 + 9, label, emoji: '',
  }))
  it('uses the exported band index', () => expect(bandIndex(4, bands)).toBe(4))
  it('out-of-range or malformed band is -1', () => {
    for (const b of [-1, 7, 2.5, Number.NaN, null, undefined, '4']) expect(bandIndex(b, bands)).toBe(-1)
  })
  it('moodToken is identity for 7 bands', () => {
    expect([0, 1, 2, 3, 4, 5, 6].map((i) => moodToken(i, 7))).toEqual([0, 1, 2, 3, 4, 5, 6])
  })
  it('moodToken spreads other counts over 0..6', () => {
    expect([0, 1, 2, 3, 4].map((i) => moodToken(i, 5))).toEqual([0, 2, 3, 5, 6])
  })
})

describe('tickLabel', () => {
  it('2020 (17 regular-season weeks)', () => {
    const s = season(2020, 17)
    expect(tickLabel(0, s)).toBe('Pre')
    expect(tickLabel(1, s)).toBe('Wk 1')
    expect(tickLabel(17, s)).toBe('Wk 17')
    expect(tickLabel(18, s)).toBe('WC')
    expect(tickLabel(19, s)).toBe('Div')
    expect(tickLabel(20, s)).toBe('Conf')
    expect(tickLabel(21, s)).toBe('SB')
  })
  it('2021 (18 regular-season weeks)', () => {
    const s = season(2021, 18)
    expect(tickLabel(18, s)).toBe('Wk 18')
    expect(tickLabel(19, s)).toBe('WC')
    expect(tickLabel(22, s)).toBe('SB')
  })
})

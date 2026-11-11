import { describe, expect, it } from 'vitest'
import {
  connectors,
  contrastRatio,
  currentPoint,
  lowPoint,
  parseHex,
  pickHighlight,
  seasonStarts,
  tickSeasons,
  toRows,
} from './history'
import type { HistoryFile } from './types'

// 2 seasons x 3 weeks, 2 teams; BBB is missing its first week.
const h: HistoryFile = {
  keys: ['2000-0', '2000-1', '2000-2', '2001-0', '2001-1', '2001-2'],
  teams: {
    AAA: [50, 40, 60, 40, 70, 80],
    BBB: [null, 30, 35, 90, 30, 20],
  },
}

describe('toRows', () => {
  const { rows, xs, xMax } = toRows(h)
  it('leaves a one-slot gap between seasons', () => {
    expect(xs).toEqual([0, 1, 2, 4, 5, 6])
    expect(xMax).toBe(6)
  })
  it('inserts exactly one NaN row per team at the boundary', () => {
    for (const team of ['AAA', 'BBB']) {
      const gap = rows.filter((r) => r.team === team && r.x === 3)
      expect(gap).toHaveLength(1)
      expect(Number.isNaN(gap[0].y)).toBe(true)
      expect(rows.filter((r) => r.team === team)).toHaveLength(7)
    }
  })
  it('turns nulls into NaN', () => {
    const first = rows.find((r) => r.team === 'BBB' && r.x === 0)
    expect(Number.isNaN(first?.y)).toBe(true)
    expect(rows.find((r) => r.team === 'AAA' && r.x === 4)?.y).toBe(40)
  })
})

describe('seasonStarts / tickSeasons', () => {
  const { xs } = toRows(h)
  it('finds the first x of each season', () => {
    expect(seasonStarts(h, xs)).toEqual([
      { season: 2000, x: 0 },
      { season: 2001, x: 4 },
    ])
  })
  it('thins ticks on narrow screens and never places two ticks closer than the step', () => {
    const starts = Array.from({ length: 28 }, (_, i) => ({ season: 1999 + i, x: i * 10 }))
    const wide = tickSeasons(starts, 960).map((d) => d.season)
    const narrow = tickSeasons(starts, 343).map((d) => d.season)
    // 1999 is dropped: 2000 is only one season after it
    expect(wide[0]).toBe(2000)
    expect(wide.every((s) => s % 2 === 0)).toBe(true)
    expect(narrow).toEqual([2000, 2005, 2010, 2015, 2020, 2025])
    expect(narrow.length).toBeLessThan(wide.length)
    for (const [ticks, step] of [[wide, 2], [narrow, 5]] as const) {
      for (let i = 1; i < ticks.length; i++) expect(ticks[i] - ticks[i - 1]).toBeGreaterThanOrEqual(step)
    }
  })
  it('keeps the first season only when no tick lands within a step of it', () => {
    const starts = Array.from({ length: 12 }, (_, i) => ({ season: 2002 + i, x: i * 10 }))
    expect(tickSeasons(starts, 343).map((d) => d.season)).toEqual([2005, 2010])
    const odd = Array.from({ length: 6 }, (_, i) => ({ season: 1997 + i, x: i * 10 }))
    expect(tickSeasons(odd, 960).map((d) => d.season)).toEqual([1998, 2000, 2002])
    expect(tickSeasons([{ season: 2001, x: 0 }], 960).map((d) => d.season)).toEqual([2001])
  })
})

describe('contrast', () => {
  it('computes WCAG ratios', () => {
    expect(contrastRatio('#FFFFFF', '#000000')).toBeCloseTo(21, 5)
    expect(contrastRatio('#123456', '#123456')).toBe(1)
    expect(contrastRatio('#fff', ' #000000 ')).toBeCloseTo(21, 5)
  })
  it('parses hex only', () => {
    expect(parseHex('rgb(0,0,0)')).toBeNull()
    expect(parseHex('')).toBeNull()
    expect(parseHex(' #0a0B0c ')).toEqual([10, 11, 12])
  })
  it('falls back from primary to secondary to text', () => {
    expect(pickHighlight('#00338D', '#C60C30', '#f6f6f3')).toBe('primary')
    expect(pickHighlight('#FFFFFF', '#C60C30', '#f6f6f3')).toBe('secondary')
    expect(pickHighlight('#FFFFFF', '#FFFF00', '#f6f6f3')).toBe('text')
    // dark background: navy fails, white secondary passes
    expect(pickHighlight('#002244', '#FFFFFF', '#121316')).toBe('secondary')
  })
  it('never silently passes on unparsable values', () => {
    // unparsable bg -> known light/dark --bg
    expect(pickHighlight('#002244', '#FFFFFF', 'var(--bg)')).toBe('primary')
    expect(pickHighlight('#002244', '#FFFFFF', '', true)).toBe('secondary')
    // unparsable team colours count as failing
    expect(pickHighlight('navy', 'nope', '#f6f6f3')).toBe('text')
  })
})

describe('lowPoint / currentPoint', () => {
  it('picks the earliest minimum and skips nulls', () => {
    expect(lowPoint(h, 'AAA')).toEqual({ score: 40, key: '2000-1' })
    expect(lowPoint(h, 'BBB')).toEqual({ score: 20, key: '2001-2' })
  })
  it('current is the last non-null score', () => {
    expect(currentPoint(h, 'AAA')).toEqual({ score: 80, key: '2001-2' })
    expect(currentPoint({ keys: ['2000-0', '2000-1'], teams: { X: [5, null] } }, 'X')).toEqual({ score: 5, key: '2000-0' })
  })
  it('unknown team is null', () => {
    expect(lowPoint(h, 'ZZZ')).toBeNull()
    expect(currentPoint(h, 'ZZZ')).toBeNull()
  })
})

describe('connectors', () => {
  const { xs } = toRows(h)
  it('bridges each season boundary from the last snapshot of S to week 0 of S+1', () => {
    expect(connectors(h, xs)).toEqual([
      { team: 'AAA', x1: 2, y1: 60, x2: 4, y2: 40 },
      { team: 'BBB', x1: 2, y1: 35, x2: 4, y2: 90 },
    ])
  })
  it('filters to one team', () => {
    expect(connectors(h, xs, 'AAA')).toEqual([{ team: 'AAA', x1: 2, y1: 60, x2: 4, y2: 40 }])
  })
  it('handles missing ends', () => {
    const g: HistoryFile = {
      keys: ['2000-0', '2000-1', '2000-2', '2001-0', '2001-1'],
      teams: {
        NOW0: [10, 20, 30, null, 5], // week 0 of S+1 missing -> none
        LAST: [10, 20, null, 40, 5], // last key of S missing -> starts at 2000-1
        GONE: [null, null, null, 40, 5], // all of S missing -> none
      },
    }
    const gx = toRows(g).xs
    expect(connectors(g, gx)).toEqual([{ team: 'LAST', x1: 1, y1: 20, x2: 4, y2: 40 }])
  })
  it('gives one segment per boundary across three seasons', () => {
    const g: HistoryFile = {
      keys: ['2000-0', '2000-1', '2001-0', '2001-1', '2002-0'],
      teams: { AAA: [1, 2, 3, 4, 5], BBB: [6, 7, 8, 9, 10] },
    }
    const out = connectors(g, toRows(g).xs)
    expect(out.filter((c) => c.team === 'AAA')).toEqual([
      { team: 'AAA', x1: 1, y1: 2, x2: 3, y2: 3 },
      { team: 'AAA', x1: 4, y1: 4, x2: 6, y2: 5 },
    ])
    expect(out.filter((c) => c.team === 'BBB')).toHaveLength(2)
  })
})

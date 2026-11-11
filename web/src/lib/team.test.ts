import { describe, expect, it } from 'vitest'
import { barRows, findTeamRow, recentGames, seasonSeries, signed, sparkDomain } from './team'
import type { FactorMeta, GamesFile, Row, SeasonFile } from './types'

type G = [week: number, asof: number, home: string, away: string, hs: number | null, as: number | null, day: string, neutral?: boolean]

function games(season: number, list: G[]): GamesFile {
  return {
    season,
    week: list.map((g) => g[0]),
    asof_week: list.map((g) => g[1]),
    home: list.map((g) => g[2]),
    away: list.map((g) => g[3]),
    home_score: list.map((g) => g[4]),
    away_score: list.map((g) => g[5]),
    game_type: list.map(() => 'REG'),
    gameday: list.map((g) => g[6]),
    neutral: list.map((g) => g[7] ?? false),
  }
}

// 2025: four AAA games at the end of the season.
const prev = games(2025, [
  [15, 15, 'AAA', 'BBB', 20, 10, '2025-12-14'],
  [16, 16, 'CCC', 'AAA', 17, 17, '2025-12-21'],
  [17, 17, 'AAA', 'DDD', 3, 30, '2025-12-28'],
  [18, 18, 'EEE', 'AAA', 21, 24, '2026-01-04'],
  [18, 18, 'BBB', 'CCC', 9, 6, '2026-01-04'],
])

// 2026: weeks 1-3 played, week 4 scheduled (null scores), week 10 also listed.
const cur = games(2026, [
  [1, 1, 'AAA', 'BBB', 27, 13, '2026-09-13'],
  [2, 2, 'CCC', 'AAA', 10, 14, '2026-09-20', true],
  [3, 3, 'AAA', 'DDD', 7, 21, '2026-09-27'],
  [4, 4, 'EEE', 'AAA', null, null, '2026-10-04'],
  [10, 10, 'AAA', 'CCC', 30, 0, '2026-11-15'],
])

describe('recentGames', () => {
  it('returns newest first, at most n, with W/L/T and margin from the team side', () => {
    const r = recentGames([cur, prev], 'AAA', 2026, 9)
    expect(r).toHaveLength(6)
    expect(r.map((g) => [g.season, g.week])).toEqual([
      [2026, 3],
      [2026, 2],
      [2026, 1],
      [2025, 18],
      [2025, 17],
      [2025, 16],
    ])
    expect(r[0]).toMatchObject({ opp: 'DDD', home: true, result: 'L', pf: 7, pa: 21, margin: -14 })
    expect(r[1]).toMatchObject({ opp: 'CCC', home: false, neutral: true, result: 'W', pf: 14, pa: 10, margin: 4 })
    expect(r[5]).toMatchObject({ opp: 'CCC', home: false, result: 'T', margin: 0 })
  })
  it('never shows a game after the page week (as-of filter) or an unplayed game', () => {
    const r = recentGames([cur, prev], 'AAA', 2026, 9, 20)
    expect(r.some((g) => g.season === 2026 && g.week > 9)).toBe(false)
    expect(r.some((g) => g.week === 4 && g.season === 2026)).toBe(false)
    const r10 = recentGames([cur, prev], 'AAA', 2026, 10, 1)
    expect(r10[0]).toMatchObject({ week: 10, result: 'W', margin: 30 })
  })
  it('fills from the previous season when the current one is short', () => {
    const r = recentGames([cur, prev], 'AAA', 2026, 1, 3)
    expect(r.map((g) => [g.season, g.week])).toEqual([
      [2026, 1],
      [2025, 18],
      [2025, 17],
    ])
  })
  it('week 0 returns only prior-season games', () => {
    const r = recentGames([cur, prev], 'AAA', 2026, 0)
    expect(r).toHaveLength(4)
    expect(r.every((g) => g.season === 2025)).toBe(true)
  })
  it('handles no files and unknown teams', () => {
    expect(recentGames([], 'AAA', 2026, 5)).toEqual([])
    expect(recentGames([cur, prev], 'ZZZ', 2026, 9)).toEqual([])
  })
})

const factors: FactorMeta[] = [
  { key: 'elo', label: 'Elo', weight: 1, description: 'Team strength' },
  { key: 'rec', label: 'Record', weight: 1, description: 'Season record' },
  { key: 'l16', label: 'Last 16', weight: -1, description: 'Recent form' },
  { key: 'mov', label: 'Margin', weight: 1, description: 'Margin of victory' },
  { key: 'luck', label: 'Luck', weight: -1, description: 'Close games' },
]

describe('barRows', () => {
  it('returns every factor, sorted by |points| desc with factor order as tiebreak', () => {
    const b = barRows({ elo: 10, rec: -20, l16: 5, mov: -5, luck: 1 }, factors)
    expect(b.rows.map((r) => r.key)).toEqual(['rec', 'elo', 'l16', 'mov', 'luck'])
    expect(b.scale).toBe(20)
    expect(b.rows[0]).toMatchObject({ label: 'Record', description: 'Season record', points: -20 })
  })
  it('visible bars plus the baseline add up to the score', () => {
    const pts = { elo: 49, rec: 10, l16: -13, mov: 12, luck: -11 }
    const b = barRows(pts, factors)
    expect(b.rows).toHaveLength(factors.length)
    expect(49 + b.rows.reduce((s, r) => s + r.points, 0)).toBe(96)
  })
  it('counts a factor missing from points as 0', () => {
    const b = barRows({ elo: 3 }, factors)
    expect(b.rows.map((r) => r.key)).toEqual(['elo', 'rec', 'l16', 'mov', 'luck'])
    expect(b.rows[4]).toMatchObject({ key: 'luck', points: 0 })
  })
  it('scale is at least 1', () => {
    expect(barRows({}, factors).scale).toBe(1)
  })
})

describe('signed', () => {
  it('uses + and U+2212', () => {
    expect(signed(12)).toBe('+12')
    expect(signed(-7)).toBe('−7')
    expect(signed(0)).toBe('0')
  })
})

const row = (franchise: string, score: number): Row => ({
  franchise, rank: 1, score, elo: 1500, band: 3, label: 'x', emoji: 'y', wins: 0, losses: 0, ties: 0, score_delta: null, rank_delta: null,
})
const season: SeasonFile = {
  season: 2026,
  weeks: { '2': [row('AAA', 60), row('BBB', 40)], '0': [row('AAA', 50)], '1': [row('BBB', 45), row('AAA', 55)] },
}

describe('findTeamRow / seasonSeries', () => {
  it('finds the row for a team and week', () => {
    expect(findTeamRow(season, 'AAA', 1)?.score).toBe(55)
    expect(findTeamRow(season, 'BBB', 0)).toBeUndefined()
    expect(findTeamRow(season, 'AAA', 7)).toBeUndefined()
  })
  it('builds a week-sorted score series', () => {
    expect(seasonSeries(season, 'AAA')).toEqual([
      { week: 0, score: 50 },
      { week: 1, score: 55 },
      { week: 2, score: 60 },
    ])
    expect(seasonSeries(season, 'BBB').map((p) => p.week)).toEqual([1, 2])
  })
})

describe('sparkDomain', () => {
  it('pads the season range by at least 3 points', () => {
    expect(sparkDomain([{ score: 85 }, { score: 96 }, { score: 90 }])).toEqual({ lo: 85, hi: 96, domain: [82, 99] })
  })
  it('pads by 15% of a wide range and clamps to 0..100', () => {
    const d = sparkDomain([{ score: 2 }, { score: 98 }])
    expect(d.lo).toBe(2)
    expect(d.hi).toBe(98)
    expect(d.domain).toEqual([0, 100])
  })
  it('handles a flat series', () => {
    expect(sparkDomain([{ score: 50 }, { score: 50 }]).domain).toEqual([47, 53])
  })
})

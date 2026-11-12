import { describe, expect, it } from 'vitest'
import { seasonToDate } from './epa'
import type { EpaFile } from './types'

// [week, franchise, opponent, off_epa, off_plays, off_sr, def_epa, def_plays, def_sr]
type R = [number, string, string, number, number, number, number, number, number]

function file(rows: R[]): EpaFile {
  return {
    season: 2025,
    note: 'test',
    game_id: rows.map((r, i) => `g${i}`),
    week: rows.map((r) => r[0]),
    game_type: rows.map((r) => (r[0] > 18 ? 'WC' : 'REG')),
    franchise: rows.map((r) => r[1]),
    opponent: rows.map((r) => r[2]),
    off_epa: rows.map((r) => r[3]),
    off_plays: rows.map((r) => r[4]),
    off_sr: rows.map((r) => r[5]),
    def_epa: rows.map((r) => r[6]),
    def_plays: rows.map((r) => r[7]),
    def_sr: rows.map((r) => r[8]),
  }
}

describe('seasonToDate', () => {
  const f = file([
    [1, 'KC', 'BAL', 0.1, 60, 0.5, -0.2, 50, 0.4],
    [2, 'KC', 'BUF', 0.2, 40, 0.4, 0.3, 70, 0.5],
    [1, 'BAL', 'KC', -0.2, 50, 0.4, 0.1, 60, 0.5],
    [19, 'KC', 'MIA', 1.0, 100, 1.0, 1.0, 100, 1.0],
  ])

  it('weights offense by off_plays and defense by def_plays', () => {
    const kc = seasonToDate(f, 2).KC
    expect(kc.off_epa).toBeCloseTo(0.14) // not 0.15
    expect(kc.off_sr).toBeCloseTo((0.5 * 60 + 0.4 * 40) / 100)
    expect(kc.def_epa).toBeCloseTo((-0.2 * 50 + 0.3 * 70) / 120)
    expect(kc.def_sr).toBeCloseTo((0.4 * 50 + 0.5 * 70) / 120)
    expect(kc.off_plays).toBe(100)
    expect(kc.def_plays).toBe(120)
    expect(kc.games).toBe(2)
  })

  it('excludes rows after the week cutoff', () => {
    const kc = seasonToDate(f, 1).KC
    expect(kc.off_epa).toBeCloseTo(0.1)
    expect(kc.games).toBe(1)
  })

  it('week 22 includes postseason rows', () => {
    const kc = seasonToDate(f, 22).KC
    expect(kc.games).toBe(3)
    expect(kc.off_epa).toBeCloseTo((0.1 * 60 + 0.2 * 40 + 1.0 * 100) / 200)
  })

  it('omits a franchise with no rows through the week', () => {
    const r = seasonToDate(f, 0)
    expect(r).toEqual({})
    expect(seasonToDate(f, 1).BUF).toBeUndefined()
    expect(Object.keys(seasonToDate(f, 1)).sort()).toEqual(['BAL', 'KC'])
  })

  it('zero plays give null means, never NaN, and still count games', () => {
    const z = seasonToDate(file([[1, 'NYJ', 'NE', 0, 0, 0, 0.1, 55, 0.45]]), 18).NYJ
    expect(z.off_epa).toBeNull()
    expect(z.off_sr).toBeNull()
    expect(z.def_epa).toBeCloseTo(0.1)
    expect(z.off_plays).toBe(0)
    expect(z.games).toBe(1)
  })

  it('skips null rates instead of treating them as 0 (WR-05)', () => {
    const g = file([
      [1, 'KC', 'BAL', 0.1, 60, 0.5, -0.2, 50, 0.4],
      [2, 'KC', 'BUF', 0.2, 40, 0.4, 0.3, 70, 0.5],
    ])
    g.off_sr[1] = null
    g.def_sr[1] = null
    const kc = seasonToDate(g, 2).KC
    expect(kc.off_sr).toBeCloseTo(0.5)
    expect(kc.def_sr).toBeCloseTo(0.4)
    expect(kc.off_epa).toBeCloseTo(0.14)
    expect(kc.off_plays).toBe(100)
  })
})

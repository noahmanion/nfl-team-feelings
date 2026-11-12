import { describe, expect, it } from 'vitest'
import {
  chartHeight, competitionRank, diagonals, emptyCopy, epaEmpty, epaPoints, epaTicks, epaTip, fitLine, gapText,
  leagueMeans, paddedDomain, pct, recordDek, recordPoints, recordText, recordTip, regOnly, signed, tapAction,
  winPct, withGaps,
} from './explore'
import type { EpaPoint, RecordPoint } from './explore'
import type { EpaAgg } from './epa'
import type { EpaFile, Meta, Row } from './types'

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

const team = (name: string, nick: string) => ({ name, nick, primary: '#000', secondary: '#fff' })
const meta = {
  teams: {
    KC: team('Kansas City Chiefs', 'Chiefs'), BUF: team('Buffalo Bills', 'Bills'), BAL: team('Baltimore Ravens', 'Ravens'),
    HOU: team('Houston Texans', 'Texans'), WAS: team('Washington Commanders', 'Commanders'),
    LV: team('Las Vegas Raiders', 'Raiders'), NYJ: team('New York Jets', 'Jets'),
  },
} as unknown as Meta

function row(franchise: string, score: number, wins: number, losses: number, ties = 0): Row {
  return { franchise, rank: 1, score, elo: null, band: 3, label: 'Fine', emoji: '🙂', wins, losses, ties,
    score_delta: null, rank_delta: null }
}

const agg = (off: number | null, def: number | null, op = 100, dp = 100, games = 2, osr: number | null = 0.5,
  dsr: number | null = 0.4): EpaAgg => ({ off_epa: off, def_epa: def, off_sr: osr, def_sr: dsr, off_plays: op,
  def_plays: dp, games })

describe('regOnly', () => {
  it('drops every non-REG index across all columns', () => {
    const f = file([
      [1, 'KC', 'BAL', 0.1, 60, 0.5, -0.2, 50, 0.4],
      [19, 'KC', 'MIA', 1.0, 100, 1.0, 1.0, 100, 1.0],
      [2, 'KC', 'BUF', 0.2, 40, 0.4, 0.3, 70, 0.5],
      [20, 'KC', 'BUF', 1.0, 100, 1.0, 1.0, 100, 1.0],
    ])
    f.game_type[3] = 'SB'
    const r = regOnly(f)
    for (const k of ['game_id', 'week', 'game_type', 'franchise', 'opponent', 'off_epa', 'off_plays', 'off_sr',
      'def_epa', 'def_plays', 'def_sr'] as const) expect(r[k]).toHaveLength(2)
    expect(r.game_type).toEqual(['REG', 'REG'])
    expect(r.week).toEqual([1, 2])
    expect(r.game_id).toEqual(['g0', 'g2'])
    expect(r.season).toBe(2025)
  })
})

describe('competitionRank', () => {
  it('ties share the lower number (1, 2, 2, 4)', () => {
    expect(competitionRank([0.2, 0.1, 0.1, 0.0], true)).toEqual([1, 2, 2, 4])
    expect(competitionRank([0.2, 0.1, 0.1, 0.0], false)).toEqual([4, 2, 2, 1])
  })
})

describe('epaPoints', () => {
  const rows = [row('KC', 70, 6, 2), row('BUF', 60, 5, 3), row('BAL', 50, 4, 4), row('NYJ', 40, 2, 6)]
  const aggs: Record<string, EpaAgg> = {
    KC: agg(0.2, -0.1), BUF: agg(0.1, 0.0), BAL: agg(0.1, -0.1), NYJ: agg(0.0, 0.1), MIA: agg(0.3, -0.3),
  }

  it('inner-joins on franchise and ranks offense desc, defense asc', () => {
    const p = epaPoints(rows, aggs, 2025, meta)
    expect(p.map((x) => x.franchise)).toEqual(['KC', 'BUF', 'BAL', 'NYJ']) // MIA has no row
    const by = Object.fromEntries(p.map((x) => [x.franchise, x]))
    expect([by.KC.offRank, by.BUF.offRank, by.BAL.offRank, by.NYJ.offRank]).toEqual([1, 2, 2, 4])
    expect([by.KC.defRank, by.BAL.defRank, by.BUF.defRank, by.NYJ.defRank]).toEqual([1, 1, 3, 4])
    expect(by.KC.net).toBeCloseTo(0.3)
    expect(by.KC.name).toBe('Kansas City Chiefs')
    expect(by.KC.wins).toBe(6)
    expect(by.KC.games).toBe(2)
    expect(by.KC.src).toMatch(/logos\/sm\/KC\.png$/)
  })

  it('drops teams with a null rate', () => {
    const p = epaPoints(rows, { ...aggs, BUF: agg(null, 0.1) }, 2025, meta)
    expect(p.map((x) => x.franchise)).not.toContain('BUF')
  })

  it('drops HOU before 2002 and uses era abbreviations', () => {
    const p = epaPoints([row('HOU', 50, 1, 1), row('LV', 50, 1, 1)], { HOU: agg(0, 0), LV: agg(0, 0) }, 2001, meta)
    expect(p.map((x) => x.franchise)).toEqual(['LV'])
    expect(p[0].abbr).toBe('OAK')
    expect(p[0].name).toBe('Oakland Raiders')
  })
})

describe('leagueMeans', () => {
  it('is play-weighted and skips null rates', () => {
    const m = leagueMeans([agg(0.1, 0.0, 100, 50), agg(-0.2, 0.3, 50, 150), agg(null, null, 70, 70)])
    expect(m.off).toBeCloseTo((0.1 * 100 - 0.2 * 50) / 150)
    expect(m.def).toBeCloseTo((0 * 50 + 0.3 * 150) / 200)
  })
  it('returns null fields with no plays', () => {
    expect(leagueMeans([])).toEqual({ off: null, def: null })
  })
})

describe('winPct and recordPoints', () => {
  it('counts ties as half; null with no games', () => {
    expect(winPct(6, 1, 1)).toBeCloseTo(0.8125)
    expect(winPct(0, 0, 0)).toBeNull()
  })
  it('excludes gp == 0 and HOU < 2002; y = score', () => {
    const p = recordPoints([row('KC', 71, 6, 2), row('BUF', 50, 0, 0), row('HOU', 40, 1, 0)], 2001, meta)
    expect(p.map((x) => x.franchise)).toEqual(['KC'])
    expect(p[0]).toMatchObject({ x: 0.75, y: 71, gp: 8, nick: 'Chiefs', gap: null, emoji: '🙂', label: 'Fine' })
  })
})

describe('fitLine and withGaps', () => {
  it('null for n < 3 or zero x-variance', () => {
    expect(fitLine([{ x: 0, y: 1 }, { x: 1, y: 2 }])).toBeNull()
    expect(fitLine([{ x: 0.5, y: 1 }, { x: 0.5, y: 2 }, { x: 0.5, y: 3 }])).toBeNull()
  })
  it('exact fit for a known set', () => {
    const l = fitLine([{ x: 0, y: 10 }, { x: 0.5, y: 50 }, { x: 1, y: 90 }])!
    expect(l.a).toBeCloseTo(10)
    expect(l.b).toBeCloseTo(80)
  })
  it('gap = y - (a + b x), null without a line', () => {
    const pts = recordPoints([row('KC', 71, 6, 2)], 2025, meta)
    expect(withGaps(pts, { a: 10, b: 80 })[0].gap).toBeCloseTo(1)
    expect(withGaps(pts, null)[0].gap).toBeNull()
  })
})

describe('recordDek', () => {
  const line = { a: 0, b: 100 }
  it('names the most over- and under-rated teams with en-dash records', () => {
    const pts = withGaps(recordPoints([row('KC', 80, 4, 4), row('BUF', 30, 6, 2), row('BAL', 25, 2, 6)], 2025, meta), line)
    expect(recordDek(pts, line, 2025, 'Week 8', meta))
      .toBe('The Chiefs look better than their 4–4 record; the Bills look worse than theirs.')
  })
  it('rewrites the Washington nick for 2015', () => {
    const pts = withGaps(recordPoints([row('WAS', 80, 4, 4), row('BUF', 30, 6, 2), row('BAL', 25, 2, 6)], 2015, meta), line)
    const d = recordDek(pts, line, 2015, 'Week 8', meta)
    expect(d).not.toMatch(/Commanders/)
    expect(d).toBe('Washington look better than their 4–4 record; the Bills look worse than theirs.')
  })
  it('falls back when the line is null or both gaps are small', () => {
    const fb = 'Win percentage against feel-good score, 2025 through Week 8.'
    const pts = recordPoints([row('KC', 50, 4, 4)], 2025, meta)
    expect(recordDek(pts, null, 2025, 'Week 8', meta)).toBe(fb)
    const small = withGaps(recordPoints([row('KC', 50.5, 4, 4), row('BUF', 74.6, 6, 2)], 2025, meta), line)
    expect(recordDek(small, line, 2025, 'Week 8', meta)).toBe(fb)
  })
})

describe('number formats', () => {
  it('signed uses + and U+2212', () => {
    expect(signed(0.1234, 3)).toBe('+0.123')
    expect(signed(-0.05, 2)).toBe('−0.05')
    expect(signed(0, 2)).toBe('0.00')
    expect(signed(-0.0001, 2)).toBe('0.00')
  })
  it('pct and gapText', () => {
    expect(pct(0.625, 1)).toBe('62.5%')
    expect(gapText(8.44)).toBe('+8.4 pts')
    expect(gapText(-3.1)).toBe('−3.1 pts')
  })
  it('recordText uses an en dash', () => {
    expect(recordText(6, 2, 0)).toBe('6–2')
    expect(recordText(6, 2, 1)).toBe('6–2–1')
  })
})

describe('domains, ticks, diagonals, height', () => {
  it('paddedDomain pads 0.03 then snaps outward to 0.05 without float noise', () => {
    expect(paddedDomain(-0.21, 0.18)).toEqual([-0.25, 0.25])
    expect(paddedDomain(-0.07, 0.17)).toEqual([-0.1, 0.2])
    expect(paddedDomain(0.02, 0.12)).toEqual([-0.05, 0.15])
  })
  it('epaTicks: 0.1 step for span >= 0.3, else 0.05; at most 6 below 640', () => {
    expect(epaTicks([-0.25, 0.25], 960)).toEqual([-0.2, -0.1, 0, 0.1, 0.2])
    expect(epaTicks([-0.1, 0.1], 960)).toEqual([-0.1, -0.05, 0, 0.05, 0.1])
    expect(epaTicks([-0.4, 0.4], 960)).toHaveLength(9)
    const narrow = epaTicks([-0.4, 0.4], 343)
    expect(narrow.length).toBeLessThanOrEqual(6)
    expect(narrow).toContain(0)
  })
  it('diagonals: one slope-1 segment per 0.1 net crossing the frame', () => {
    const d = diagonals([-0.2, 0.2], [-0.2, 0.2])
    expect(d).toHaveLength(9) // net -0.4..0.4
    for (const s of d) expect((s.y2 - s.y1) / (s.x2 - s.x1)).toBeCloseTo(1)
    expect(d.map((s) => Math.round((s.x1 - s.y1) * 10))).toEqual([-4, -3, -2, -1, 0, 1, 2, 3, 4])
  })
  it('chartHeight clamps width x 0.8 to 320..560', () => {
    expect(chartHeight(960)).toBe(560)
    expect(chartHeight(343)).toBe(320)
    expect(chartHeight(500)).toBe(400)
  })
})

describe('tapAction', () => {
  it('mouse navigates at once', () => expect(tapAction('mouse', null, 'KC')).toEqual({ go: true, armed: null }))
  it('touch arms first, navigates on a second tap of the same team', () => {
    expect(tapAction('touch', null, 'KC')).toEqual({ go: false, armed: 'KC' })
    expect(tapAction('touch', 'KC', 'KC')).toEqual({ go: true, armed: null })
    expect(tapAction('touch', 'KC', 'BUF')).toEqual({ go: false, armed: 'BUF' })
  })
  it('nothing picked clears the arm', () => {
    expect(tapAction('mouse', 'KC', null)).toEqual({ go: false, armed: null })
    expect(tapAction('touch', 'KC', null)).toEqual({ go: false, armed: null })
  })
})

describe('tooltips', () => {
  const ep: EpaPoint = { franchise: 'KC', abbr: 'KC', name: 'Kansas City Chiefs', src: null, off: 0.1234, def: -0.045,
    offSr: 0.482, defSr: 0.431, net: 0.168, offRank: 3, defRank: 5, games: 8, wins: 6, losses: 2, ties: 0 }
  it('epaTip has exactly 5 lines', () => {
    expect(epaTip(ep).split('\n')).toEqual([
      'Kansas City Chiefs',
      'Offense +0.123 EPA/play · #3',
      'Defense −0.045 allowed · #5',
      'Success 48.2% off · 43.1% def',
      '6–2 · 8 games',
    ])
  })
  it('epaTip shows – for null success rates', () => {
    expect(epaTip({ ...ep, offSr: null, defSr: null }).split('\n')[3]).toBe('Success – off · – def')
  })
  const rp: RecordPoint = { franchise: 'KC', abbr: 'KC', name: 'Kansas City Chiefs', nick: 'Chiefs', src: null, x: 0.75,
    y: 71, wins: 6, losses: 2, ties: 0, gp: 8, label: 'Feeling good', emoji: '😀', gap: 8.44 }
  it('recordTip has 4 lines, 3 without a gap', () => {
    expect(recordTip(rp).split('\n')).toEqual([
      'Kansas City Chiefs', '6–2 · 75.0%', 'Score 71 · 😀 Feeling good', '+8.4 pts vs typical for this record',
    ])
    expect(recordTip({ ...rp, gap: null }).split('\n')).toHaveLength(3)
  })
})

describe('empty states', () => {
  const base = { season: 2025, week: 5, gamesPlayed: 70, epaSeasons: [1999, 2025], nPoints: 32 }
  it('epaEmpty decides in order', () => {
    expect(epaEmpty({ ...base, week: 0 })).toBe('no-games')
    expect(epaEmpty({ ...base, gamesPlayed: 0 })).toBe('no-games')
    expect(epaEmpty({ ...base, epaSeasons: [1999] })).toBe('no-pbp')
    expect(epaEmpty({ ...base, epaSeasons: undefined })).toBe('no-pbp')
    expect(epaEmpty({ ...base, nPoints: 0 })).toBe('no-week')
    expect(epaEmpty(base)).toBeNull()
  })
  it('emptyCopy matches the UI-SPEC strings', () => {
    expect(emptyCopy('no-games', 2025, 'Preseason', 1999)).toBe('No games played yet in 2025. Pick a later week.')
    expect(emptyCopy('no-pbp', 1998, 'Week 3', 1999))
      .toBe('No play-by-play efficiency data for 1998. Pick 1999 or later.')
    expect(emptyCopy('no-week', 2026, 'Week 10', 1999))
      .toBe('No efficiency data through Week 10 yet. Check back after the play-by-play update.')
  })
})

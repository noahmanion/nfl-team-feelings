import { describe, expect, it } from 'vitest'
import { finished, lineTicks, markerPos, pace, winsText, winTotalsView } from './winTotals'
import type { WinTotalsInput } from './winTotals'

const SOURCE = 'SOURCE: NFLVERSE (2003–2020) · COVERS / DRAFTKINGS (2021+)'

const file: WinTotalsInput = {
  vegas_win_totals: {
    season: [2015, 2022, 2023, 2026],
    line: [9.5, 11.5, 11.5, 10.5],
    line_type: ['nflverse', 'preseason_close', 'preseason_close', 'preseason_open'],
    used_in_score: [true, false, false, false],
  },
  expectation: {
    season: [2001, 2015, 2022, 2023, 2026],
    exp_total: [7.6, 9.4, 11.2, 11.0, 8.1],
    source: ['model', 'vegas', 'model', 'model', 'model'],
    reg_games: [16, 16, 17, 17, 17],
  },
}

describe('pace / finished / ticks / winsText', () => {
  it('pace', () => {
    expect(pace(6, 2, 0, 17)).toBe(12.8)
    expect(pace(0, 0, 0, 17)).toBeNull()
    expect(pace(6, 1, 1, 17)).toBe(13.8)
  })
  it('finished', () => {
    expect(finished(13, 4, 0, 17)).toBe(true)
    expect(finished(8, 8, 0, 16)).toBe(true)
    expect(finished(6, 2, 0, 17)).toBe(false)
  })
  it('lineTicks', () => {
    expect(lineTicks(17)).toEqual([0, 4, 8, 12, 17])
    expect(lineTicks(16)).toEqual([0, 4, 8, 12, 16])
  })
  it('winsText', () => {
    expect(winsText(13, 0)).toBe('13')
    expect(winsText(8, 1)).toBe('8.5')
  })
  it('markerPos clamps to 0..100', () => {
    expect(markerPos(8.5, 17)).toBeCloseTo(50)
    expect(markerPos(-1, 17)).toBe(0)
    expect(markerPos(20, 17)).toBe(100)
  })
})

describe('winTotalsView', () => {
  it('2015: Vegas used in score, no model row', () => {
    const v = winTotalsView(file, 2015, { wins: 6, losses: 2, ties: 0 })!
    expect(v.regGames).toBe(16)
    expect(v.ticks).toEqual([0, 4, 8, 12, 16])
    expect(v.rows.map((r) => r.key)).toEqual(['vegas', 'pace'])
    expect(v.rows[0]).toMatchObject({ label: 'Vegas preseason (used in score)', value: '9.5' })
    expect(v.rows[0].suffix).toBeUndefined()
    expect(v.rows[0].pos).toBeCloseTo((9.5 / 16) * 100)
    expect(v.notes).toBe('The score uses this line, normalized to the league average.')
    expect(v.source).toBe(SOURCE)
  })

  it('2023: Vegas display only plus the model row', () => {
    const v = winTotalsView(file, 2023, { wins: 6, losses: 2, ties: 0 })!
    expect(v.rows.map((r) => r.key)).toEqual(['vegas', 'model', 'pace'])
    expect(v.rows[0].label).toBe('Vegas preseason (display only, not used in score)')
    expect(v.rows[1]).toMatchObject({ label: 'Model preseason (used in score)', value: '11.0' })
    expect(v.notes).toBe('Shown for context. The score uses the model’s preseason expectation for this season.')
    expect(v.source).toBe(SOURCE)
  })

  it('2026 opening line gets the suffix', () => {
    const v = winTotalsView(file, 2026, { wins: 6, losses: 2, ties: 0 })!
    expect(v.rows[0].suffix).toBe(' · opening line, not the final preseason number')
  })

  it('2001: model only', () => {
    const v = winTotalsView(file, 2001, { wins: 4, losses: 4, ties: 0 })!
    expect(v.rows.map((r) => r.key)).toEqual(['model', 'pace'])
    expect(v.dek).toBe('The model expected 7.6 wins. They’re on pace for 8.0 wins.')
    expect(v.notes).toBe('No Vegas line on file before 2003. The score uses the model’s preseason expectation.')
    expect(v.source).toBeUndefined()
  })

  it('2027 with no Vegas line yet: model only, no "before 2003" note', () => {
    const f: WinTotalsInput = {
      vegas_win_totals: file.vegas_win_totals,
      expectation: { season: [2027], exp_total: [9.2], source: ['model'], reg_games: [17] },
    }
    const v = winTotalsView(f, 2027, { wins: 2, losses: 1, ties: 0 })!
    expect(v.rows.map((r) => r.key)).toEqual(['model', 'pace'])
    expect(v.notes).toBe('No Vegas line on file for this season yet. The score uses the model’s preseason expectation.')
    expect(v.source).toBeUndefined()
  })

  it('pace row: in progress, finished, week 0', () => {
    const mid = winTotalsView(file, 2023, { wins: 6, losses: 2, ties: 0 })!
    expect(mid.rows[2]).toMatchObject({ key: 'pace', label: 'On pace for 12.8 wins (6–2 after 8 games)', value: '12.8' })
    expect(mid.rows[2].pos).toBeCloseTo((12.8 / 17) * 100)
    expect(mid.dek).toBe('Vegas set the line at 11.5 wins. They’re on pace for 12.8 wins.')

    const tie = winTotalsView(file, 2023, { wins: 6, losses: 1, ties: 1 })!
    expect(tie.rows[2].label).toBe('On pace for 13.8 wins (6–1–1 after 8 games)')

    const done = winTotalsView(file, 2022, { wins: 13, losses: 3, ties: 1 })!
    expect(done.rows[2]).toMatchObject({ label: 'Finished 13–3–1', value: '13.5' })
    expect(done.dek).toBe('Vegas set the line at 11.5 wins. They finished with 13.5 wins.')

    const pre = winTotalsView(file, 2023, { wins: 0, losses: 0, ties: 0 })!
    expect(pre.rows[2]).toMatchObject({ label: 'No games yet.', value: '–', pos: null })
    expect(pre.dek).toBe('Vegas set the line at 11.5 wins. No games yet.')
    expect(winTotalsView(file, 2023, null)!.rows[2].label).toBe('No games yet.')
  })

  it('returns null when the season has neither a Vegas row nor an expectation', () => {
    expect(winTotalsView(file, 1999, { wins: 1, losses: 0, ties: 0 })).toBeNull()
  })

  it('falls back to 16/17 games without an expectation block', () => {
    const noExp: WinTotalsInput = { vegas_win_totals: file.vegas_win_totals }
    expect(winTotalsView(noExp, 2015, null)!.regGames).toBe(16)
    expect(winTotalsView(noExp, 2023, null)!.regGames).toBe(17)
    expect(winTotalsView(noExp, 2023, null)!.rows.map((r) => r.key)).toEqual(['vegas', 'pace'])
  })
})

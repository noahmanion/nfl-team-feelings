import { render } from 'svelte/server'
import { describe, expect, it } from 'vitest'
import WinTotals from '../components/WinTotals.svelte'
import type { TeamFile } from './types'

// SSR smoke test of WinTotals.svelte (13-UI-SPEC "Component Contract: WinTotals.svelte").
const file: TeamFile = {
  franchise: 'BUF', name: 'Buffalo Bills', nick: 'Bills', primary: '#00338D', secondary: '#C60C30',
  history: { season: [], week: [], score: [], elo: [], label: [] },
  vegas_win_totals: { season: [2010, 2024], line: [5.5, 10], over_odds: [null, -110], under_odds: [null, -110],
    line_type: ['preseason_close', 'preseason_close'], source: ['nflverse', 'covers'], used_in_score: [true, false] },
  expectation: { season: [2010, 2024], exp_total: [5.5, 10.7], source: ['vegas', 'model'], reg_games: [16, 17] },
}
const base = { primary: '#00338D', secondary: '#C60C30', loading: false }

describe('WinTotals', () => {
  it('renders a display-only Vegas line, the model row and the pace for 2021+', () => {
    const { body } = render(WinTotals, { props: { ...base, file, season: 2024, rec: { wins: 6, losses: 2, ties: 0 } } })
    expect(body).toContain('Preseason expectations')
    expect(body).toContain('Vegas preseason (display only, not used in score)')
    expect(body).toContain('Model preseason (used in score)')
    expect(body).toContain('On pace for 12.8 wins (6–2 after 8 games)')
    expect(body).toContain('COVERS / DRAFTKINGS')
  })

  it('labels a 2003–2020 line as used in score with no model row', () => {
    const { body } = render(WinTotals, { props: { ...base, file, season: 2010, rec: { wins: 4, losses: 12, ties: 0 } } })
    expect(body).toContain('Vegas preseason (used in score)')
    expect(body).not.toContain('Model preseason')
    expect(body).toContain('Finished 4–12')
    expect(body).toContain('normalized to the league average')
  })

  it('shows the loading status and renders nothing for a season with no data', () => {
    expect(render(WinTotals, { props: { ...base, file: null, loading: true, season: 2024, rec: null } }).body)
      .toContain('Loading expectations…')
    expect(render(WinTotals, { props: { ...base, file, season: 2001, rec: null } }).body).not.toContain('Preseason')
  })
})

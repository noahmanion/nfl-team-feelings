import { describe, expect, it } from 'vitest'
import {
  chartRows, deltaText, effectText, foldText, formatCI, formatDelta, formatDeltaCI, formatMetric, formatWeight, HOLDOUT_PENDING, verdictLead, xDomain,
} from './methodology'
import type { Methodology, PeriodMetrics } from './types'

const pm = (vals: Record<string, number>, ci = true): PeriodMetrics =>
  Object.fromEntries(Object.entries(vals).map(([k, v]) => [k, { value: v, ci: ci ? [v - 0.02, v + 0.02] as [number, number] : null }]))

const base: Methodology = {
  version: 1,
  frozen: { fitted_at: '2026-11-11', fit_seasons: [1999, 2021], alpha: 0.01, n: 100 },
  target: { n: 8, text: 't' },
  split: { train: [1999, 2021], walk_forward: [2003, 2021], holdout: [2022, 2025], live: 2026, reference: [1999, 2021] },
  factors: [],
  candidates: [
    { key: 'elo', label: 'Elo alone' }, { key: 'season_wpct', label: 'Season win %' },
    { key: 'last16', label: 'Last 16 games' }, { key: 'pd_pg', label: 'Point differential' },
    { key: 'composite', label: 'Feel-good score' }, { key: 'spread', label: 'Vegas spread (market ceiling)', brier_only: true },
  ],
  walk_forward: {
    seasons: [2003, 2021], label: 'Walk-forward 2003–21 (refit each season)',
    spearman_n8: { ...pm({ composite: 0.52, season_wpct: 0.4, last16: 0.45, pd_pg: 0.46 }), elo: { value: 0.51, ci: null } },
    spearman_n4: {},
    brier: pm({ composite: 0.218, elo: 0.22, season_wpct: 0.23, last16: 0.226, pd_pg: 0.228, spread: 0.211 }),
    diff: null,
  },
  holdout: null,
  notes: [],
}

describe('formatters', () => {
  it('formats weights with a Unicode minus', () => {
    expect(formatWeight(2.59)).toBe('+2.59')
    expect(formatWeight(-0.56)).toBe('−0.56')
    expect(formatWeight(0)).toBe('0.00')
    expect(formatWeight(-0)).toBe('0.00')
  })
  it('effect, fold and delta text', () => {
    expect(effectText('helps')).toBe('Raises the score when high')
    expect(effectText('hurts')).toBe('Lowers the score when high')
    expect(effectText('none')).toBe('No effect at this weight')
    expect(foldText({ k: 19, of: 19 })).toBe('Same sign in 19 of 19 seasons')
    expect(foldText(null)).toBe('—')
    expect(deltaText(null, 0.5114)).toBe('baseline')
    expect(deltaText(0.0028, null)).toBe('+0.0028')
    expect(deltaText(-0.0008, null)).toBe('−0.0008')
  })
  it('metrics and intervals', () => {
    expect(formatMetric(0.52653, 3)).toBe('0.527')
    expect(formatCI([0.512, 0.54], 3)).toBe('0.512 to 0.540')
    expect(formatMetric(-0.0004, 3)).toBe('0.000')
    expect(formatMetric(-0.0123, 3)).toBe('−0.012')
  })
  it('signed differences and intervals', () => {
    expect(formatDelta(0.003892, 3)).toBe('+0.004')
    expect(formatDelta(-0.001355, 3)).toBe('−0.001')
    expect(formatDelta(-0.0004, 3)).toBe('0.000')
    expect(formatDelta(null)).toBe('—')
    expect(formatDeltaCI([-0.022531, 0.029375], 3)).toBe('−0.023 to +0.029')
    expect(formatDeltaCI([-0.03, -0.01], 3)).toBe('−0.030 to −0.010')
    expect(formatDeltaCI(null)).toBe('—')
  })
})

describe('chartRows', () => {
  it('walk-forward only when holdout is null, in candidate order, null ci collapses', () => {
    const rows = chartRows(base, 'spearman_n8')
    expect(rows.map((r) => r.key)).toEqual(['elo', 'season_wpct', 'last16', 'pd_pg', 'composite'])
    expect(new Set(rows.map((r) => r.period))).toEqual(new Set(['Walk-forward 2003–21 (refit each season)']))
    expect(rows[0]).toEqual({ period: 'Walk-forward 2003–21 (refit each season)', key: 'elo', label: 'Elo alone', value: 0.51, lo: 0.51, hi: 0.51 })
  })
  it('brier includes the spread ceiling', () => {
    const rows = chartRows(base, 'brier')
    expect(rows.find((r) => r.key === 'spread')?.label).toBe('Vegas spread (market ceiling)')
  })
  it('adds holdout rows when present', () => {
    const m: Methodology = {
      ...base,
      holdout: {
        seasons: [2022, 2025], label: 'Holdout 2022–25 (frozen weights)', evaluated_at: 'x', verdict: 'slight',
        headline: 'Made-up headline.', pass: false, spearman_n8: pm({ composite: 0.3, elo: 0.29 }), spearman_n4: {},
        brier: {}, diff: null, diagnostic: null, rerun: false,
      },
    }
    const rows = chartRows(m, 'spearman_n8')
    expect(rows.filter((r) => r.period.startsWith('Holdout')).map((r) => r.key)).toEqual(['elo', 'composite'])
    expect(verdictLead(m)).toBe('Made-up headline.')
  })
  it('pads the x domain by 10% of the span', () => {
    const [lo, hi] = xDomain([
      { period: 'p', key: 'a', label: 'a', value: 0.5, lo: 0.4, hi: 0.5 },
      { period: 'p', key: 'b', label: 'b', value: 0.6, lo: 0.55, hi: 0.6 },
    ])
    expect(lo).toBeCloseTo(0.38)
    expect(hi).toBeCloseTo(0.62)
  })
  it('verdict lead is the pending sentence while the holdout is null', () => {
    expect(verdictLead(base)).toBe(HOLDOUT_PENDING)
    expect(HOLDOUT_PENDING).toBe('The 2022–25 holdout is evaluated once, after the weights were frozen. It hasn’t run yet.')
  })
})

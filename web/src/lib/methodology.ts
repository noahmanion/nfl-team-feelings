// Pure formatting helpers for the methodology page (06-04). Decimals are allowed here only for
// weights and metrics (factor rows, tables, chart axes).
import type { FoldSign, Effect, Methodology, PeriodMetrics } from './types'

const MINUS = '−'

export const HOLDOUT_PENDING = 'The 2022–25 holdout is evaluated once, after the weights were frozen. It hasn’t run yet.'

function signed(x: number, dp: number): string {
  const r = Number(x.toFixed(dp))
  if (r === 0) return (0).toFixed(dp)
  return r > 0 ? `+${r.toFixed(dp)}` : `${MINUS}${Math.abs(r).toFixed(dp)}`
}

/** Signed 2 dp with a Unicode minus: +2.59, −0.56, 0.00. */
export const formatWeight = (w: number): string => signed(w, 2)

export function effectText(e: Effect): string {
  if (e === 'helps') return 'Raises the score when high'
  if (e === 'hurts') return 'Lowers the score when high'
  return 'No effect at this weight'
}

export const foldText = (f: FoldSign | null): string => (f ? `Same sign in ${f.k} of ${f.of} seasons` : '—')

/** Δ Spearman when the factor is added; the first factor (no delta, a baseline) shows 'baseline'. */
export function deltaText(delta: number | null, baseline: number | null): string {
  if (delta == null) return baseline == null ? '—' : 'baseline'
  return signed(delta, 4)
}

export function formatMetric(x: number | null | undefined, dp = 3): string {
  if (x == null || !Number.isFinite(x)) return '—'
  const s = x.toFixed(dp)
  return s.startsWith('-') ? MINUS + s.slice(1) : s
}

export const formatCI = (ci: [number, number] | null | undefined, dp = 3): string =>
  ci ? `${formatMetric(ci[0], dp)}–${formatMetric(ci[1], dp)}` : '—'

export type ChartMetric = 'spearman_n8' | 'brier'
export interface ChartRow { period: string; key: string; label: string; value: number; lo: number; hi: number }

const ORDER = ['elo', 'season_wpct', 'last16', 'pd_pg', 'composite', 'spread']

function periods(m: Methodology): { label: string; block: Record<ChartMetric, PeriodMetrics> }[] {
  const out: { label: string; block: Record<ChartMetric, PeriodMetrics> }[] = []
  if (m.walk_forward) out.push({ label: m.walk_forward.label, block: m.walk_forward })
  if (m.holdout) out.push({ label: m.holdout.label, block: m.holdout })
  return out
}

/** Candidates in chart order; brier_only ones (the spread) only for Brier. */
export function chartCandidates(m: Methodology, metric: ChartMetric) {
  return m.candidates
    .filter((c) => metric === 'brier' || !c.brier_only)
    .slice()
    .sort((a, b) => ORDER.indexOf(a.key) - ORDER.indexOf(b.key))
}

export function chartRows(m: Methodology, metric: ChartMetric): ChartRow[] {
  const rows: ChartRow[] = []
  const cands = chartCandidates(m, metric)
  for (const p of periods(m)) {
    for (const c of cands) {
      const v = p.block[metric]?.[c.key]
      if (!v || v.value == null) continue
      rows.push({
        period: p.label, key: c.key, label: c.label, value: v.value,
        lo: v.ci ? v.ci[0] : v.value, hi: v.ci ? v.ci[1] : v.value,
      })
    }
  }
  return rows
}

export function periodLabels(m: Methodology): string[] {
  return periods(m).map((p) => p.label)
}

/** [min lo, max hi] padded by 10% of the span on each side. */
export function xDomain(rows: ChartRow[]): [number, number] {
  if (rows.length === 0) return [0, 1]
  const lo = Math.min(...rows.map((r) => r.lo))
  const hi = Math.max(...rows.map((r) => r.hi))
  const pad = (hi - lo) * 0.1 || Math.abs(lo) * 0.1 || 0.01
  return [lo - pad, hi + pad]
}

export function verdictLead(m: Methodology): string {
  if (!m.holdout) return HOLDOUT_PENDING
  return m.holdout.headline ?? HOLDOUT_PENDING
}

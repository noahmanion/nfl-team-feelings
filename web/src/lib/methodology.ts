// Pure formatting helpers for the methodology page (06-04). Decimals are allowed here only for
// weights and metrics (factor rows, tables, chart axes).
import type { FoldSign, Effect, Methodology, PeriodMetrics } from './types'

const MINUS = '−'

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

/** Unsigned metric value; a tiny negative that rounds to zero shows as 0.000, never −0.000. */
export function formatMetric(x: number | null | undefined, dp = 3): string {
  if (x == null || !Number.isFinite(x)) return '—'
  const s = (Number(x.toFixed(dp)) + 0).toFixed(dp)
  return s.startsWith('-') ? MINUS + s.slice(1) : s
}

/** Metric interval as "0.512 to 0.540" (no dash between bounds, so negative bounds stay readable). */
export const formatCI = (ci: [number, number] | null | undefined, dp = 3): string =>
  ci ? `${formatMetric(ci[0], dp)} to ${formatMetric(ci[1], dp)}` : '—'

/** Signed difference: +0.004, −0.001, 0.000. */
export const formatDelta = (x: number | null | undefined, dp = 3): string =>
  x == null || !Number.isFinite(x) ? '—' : signed(x, dp)

/** Signed difference interval: "−0.023 to +0.029". */
export const formatDeltaCI = (ci: [number, number] | null | undefined, dp = 3): string =>
  ci ? `${formatDelta(ci[0], dp)} to ${formatDelta(ci[1], dp)}` : '—'

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

type CIMethod = { spearman?: string; brier?: string }
// `ci_method` is emitted by the pipeline per period (WR-04); read structurally so types.ts stays untouched.
const methodOf = (block: unknown, metric: ChartMetric): string | null => {
  const cm = (block as { ci_method?: CIMethod } | null)?.ci_method
  return (metric === 'brier' ? cm?.brier : cm?.spearman) ?? null
}

/** "season-block" / "team-season" / "season-week" interval method for a period's plotted `ci`. */
export function ciMethodText(block: unknown, metric: ChartMetric): string | null {
  return methodOf(block, metric)
}

/** Figure caption naming the interval method per period, and warning when they differ. */
export function intervalCaption(m: Methodology, metric: ChartMetric): string {
  const ps: { label: string; block: unknown }[] = []
  if (m.walk_forward) ps.push({ label: m.walk_forward.label, block: m.walk_forward })
  if (m.holdout) ps.push({ label: m.holdout.label, block: m.holdout })
  const parts = ps
    .map((p) => ({ label: p.label, method: methodOf(p.block, metric) }))
    .filter((p): p is { label: string; method: string } => p.method != null)
  if (parts.length === 0) return 'Whiskers are 95% bootstrap intervals.'
  const list = parts.map((p) => `${p.method} for ${p.label}`).join('; ')
  const differ = new Set(parts.map((p) => p.method)).size > 1
  return `Whiskers are 95% bootstrap intervals (${list}).${differ ? ' The resampling methods differ, so compare whisker widths across periods with care.' : ''}`
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

export const RERUN_WARNING = '(Re-run with --force, which breaks the pre-registration.)'

/** The holdout headline, or the pipeline's `holdout_pending` note (the only copy of that sentence). A
 *  result re-run with --force carries a warning. */
export function verdictLead(m: Methodology): string {
  const pending = m.notes.find((n) => n.key === 'holdout_pending')?.text ?? ''
  if (!m.holdout) return pending
  const lead = m.holdout.headline ?? pending
  return m.holdout.rerun ? `${lead} ${RERUN_WARNING}`.trim() : lead
}

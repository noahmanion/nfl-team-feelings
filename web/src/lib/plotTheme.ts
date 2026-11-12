// Shared Observable Plot theme (D-07, D-28). Pure TS so every chart, and its tests, can import it
// without Svelte. Headlines, deks and source lines are HTML in ChartFrame, never Plot titles.

export const CHART_FONT_PX = 12 // ticks, band labels
export const LABEL_FONT_PX = 14 // direct labels at series ends
export const HIGHLIGHT_WIDTH = 2.5
export const BACKGROUND_STROKE = 'var(--text-muted)'
export const GRID_STROKE = 'var(--grid)'
export const LOGO_MARK_PX = 20 // HistoryChart end-of-line logo (24 at width >= 900)

export const themeStyle = {
  fontFamily: 'var(--font-mono)',
  fontSize: `${CHART_FONT_PX}px`,
  color: 'var(--text-muted)',
  background: 'transparent',
  overflow: 'visible',
}

const HEX = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i
const CSS_VAR = /^var\(--[a-z0-9-]+\)$/

/** Team highlight stroke: the color pickHighlight already chose; '' or invalid -> 'var(--text)'. */
export function teamStroke(color: string | null | undefined): string {
  if (color && (HEX.test(color) || CSS_VAR.test(color))) return color
  return 'var(--text)'
}

/**
 * Value-axis options: grid on, no domain line, no ticks, no axis title (the unit goes in the dek).
 * Plot 0.6.19 hard-codes grid strokeOpacity 0.1, so the global app.css rule restores full opacity
 * and paints grid lines in --grid (D-28); don't fight it per chart.
 */
export function valueAxis(extra: object = {}): object {
  return { grid: true, tickSize: 0, line: false, label: null, ...extra }
}

/** Category/time axis: no grid, no ticks, no line. */
export function baseAxis(extra: object = {}): object {
  return { grid: false, tickSize: 0, line: false, label: null, ...extra }
}

/** Merge the theme into Plot options. Caller options win; style is shallow-merged. */
export function withTheme<T extends object>(options: T): T {
  const raw = (options as { style?: unknown }).style
  const style = raw !== null && typeof raw === 'object' ? raw : {}
  return { ...options, style: { ...themeStyle, ...style } } as T
}

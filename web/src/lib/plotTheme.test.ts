import { describe, expect, it } from 'vitest'
import { baseAxis, teamStroke, themeStyle, valueAxis, withTheme } from './plotTheme'

// D-07 shared chart theme contract (12-UI-SPEC "Shared Chart Theme Contract").
describe('withTheme', () => {
  it('merges the theme without clobbering caller style keys', () => {
    const out = withTheme({ width: 300, style: { fontSize: '14px' } })
    expect(out.width).toBe(300)
    // T is inferred from the input, so the merged theme keys are only visible at runtime
    const style = out.style as Record<string, string>
    expect(style.fontSize).toBe('14px')
    expect(style.fontFamily).toBe('var(--font-mono)')
    expect(style.background).toBe('transparent')
  })

  it('applies themeStyle as-is when the caller has no style and adds no title keys', () => {
    const out = withTheme({ width: 1 }) as Record<string, unknown>
    expect(out.style).toEqual(themeStyle)
    expect(out).not.toHaveProperty('title')
    expect(out).not.toHaveProperty('subtitle')
    expect(out).not.toHaveProperty('caption')
  })

  it('mutates neither its input nor themeStyle', () => {
    const before = { ...themeStyle }
    const input = { width: 2, style: { color: 'red' } }
    const out = withTheme(input)
    expect(input).toEqual({ width: 2, style: { color: 'red' } })
    expect(out).not.toBe(input)
    expect(out.style).not.toBe(input.style)
    expect(out.style).not.toBe(themeStyle)
    expect(themeStyle).toEqual(before)
  })
})

describe('teamStroke', () => {
  it('passes valid hex colors and CSS custom properties through', () => {
    expect(teamStroke('#E31837')).toBe('#E31837')
    expect(teamStroke('#fff')).toBe('#fff')
    expect(teamStroke('var(--text)')).toBe('var(--text)')
  })

  it('falls back to var(--text) for empty or invalid input', () => {
    expect(teamStroke('')).toBe('var(--text)')
    expect(teamStroke(null)).toBe('var(--text)')
    expect(teamStroke(undefined)).toBe('var(--text)')
    expect(teamStroke('red; x')).toBe('var(--text)')
  })
})

describe('axes', () => {
  it('valueAxis has a grid, no ticks, no domain line, no label', () => {
    const a = valueAxis() as Record<string, unknown>
    expect(a.tickSize).toBe(0)
    expect(a.grid).toBe(true)
    expect(a.line).toBe(false)
    expect(a.label).toBeNull()
  })

  it('valueAxis passes extra options through', () => {
    const a = valueAxis({ ticks: [0, 50] }) as Record<string, unknown>
    expect(a.ticks).toEqual([0, 50])
  })

  it('baseAxis has no grid and no ticks', () => {
    const a = baseAxis() as Record<string, unknown>
    expect(a.grid).toBe(false)
    expect(a.tickSize).toBe(0)
  })
})

// DESIGN-02: every Plot chart builds its options through withTheme, and no chart uses Plot titles.
const chartSources = import.meta.glob('../components/{HistoryChart,MethodologyChart,Sparkline}.svelte', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>
const sourceOf = (name: string) => chartSources[`../components/${name}.svelte`] ?? ''

describe('chart sources use the theme', () => {
  it('finds all three Plot charts', () => {
    expect(Object.keys(chartSources)).toHaveLength(3)
  })

  it.each(['HistoryChart', 'MethodologyChart', 'Sparkline'])('%s uses withTheme and no Plot titles', (name) => {
    const src = sourceOf(name)
    expect(src).toContain('withTheme(')
    expect(src).toMatch(/from '\.\.\/lib\/plotTheme'/)
    expect(src).not.toMatch(/\b(title|subtitle|caption)\s*:/)
  })

  it('MethodologyChart sits inside ChartFrame', () => {
    expect(sourceOf('MethodologyChart')).toContain('<ChartFrame')
  })

  it('HistoryChart draws exactly one logo image mark', () => {
    expect(sourceOf('HistoryChart').split('Plot.image(').length - 1).toBe(1)
  })
})

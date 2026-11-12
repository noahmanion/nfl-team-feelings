import { describe, expect, it } from 'vitest'
import { baseAxis, teamStroke, themeStyle, valueAxis, withTheme } from './plotTheme'

// D-07 shared chart theme contract (12-UI-SPEC "Shared Chart Theme Contract").
describe('withTheme', () => {
  it('merges the theme without clobbering caller style keys', () => {
    const out = withTheme({ width: 300, style: { fontSize: '14px' } })
    expect(out.width).toBe(300)
    expect(out.style.fontSize).toBe('14px')
    expect(out.style.fontFamily).toBe('var(--font-mono)')
    expect(out.style.background).toBe('transparent')
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

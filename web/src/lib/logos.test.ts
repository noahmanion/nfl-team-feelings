import { describe, expect, it } from 'vitest'
import { FRANCHISES, logoSrc, logosEnabled } from './logos'

const pngs = Object.keys(import.meta.glob('/public/logos/sm/*.png'))
const metaFiles = import.meta.glob('/public/data/meta.json', { import: 'default', eager: true }) as Record<
  string,
  { teams: Record<string, unknown> }
>

describe('logosEnabled', () => {
  it('is on unless VITE_LOGOS is "off" (case and whitespace insensitive)', () => {
    expect(logosEnabled(undefined)).toBe(true)
    expect(logosEnabled('on')).toBe(true)
    expect(logosEnabled('')).toBe(true)
    expect(logosEnabled('off')).toBe(false)
    expect(logosEnabled('OFF')).toBe(false)
    expect(logosEnabled(' off ')).toBe(false)
  })
})

describe('logoSrc', () => {
  it('returns the small local path for a known franchise', () => {
    expect(logoSrc('KC')).toBe('/logos/sm/KC.png')
  })
  it('returns null for anything else', () => {
    expect(logoSrc('kc')).toBeNull()
    expect(logoSrc('XXX')).toBeNull()
    expect(logoSrc(null)).toBeNull()
    expect(logoSrc(undefined)).toBeNull()
    expect(logoSrc('../KC')).toBeNull()
  })
})

describe('small logo derivatives', () => {
  const base = pngs.map((p) => p.split('/').pop()!.replace(/\.png$/, '')).sort()
  it('exist for exactly the 32 franchises', () => {
    expect(FRANCHISES).toHaveLength(32)
    expect(base).toEqual([...FRANCHISES].sort())
  })
  it('match the team keys in meta.json', () => {
    const meta = Object.values(metaFiles)[0]
    expect(meta).toBeDefined()
    expect(base).toEqual(Object.keys(meta.teams).sort())
  })
})

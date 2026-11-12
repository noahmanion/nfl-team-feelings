import { describe, expect, it } from 'vitest'

// D-15: the Explore page frames gaps as "better/worse than their record", never as chance.
// Scans the Explore sources (types.ts is out of scope: it documents pipeline fields).
const sources = import.meta.glob(
  [
    '../components/ExplorePage.svelte',
    '../components/EpaScatter.svelte',
    '../components/RecordScatter.svelte',
    '../components/ExploreTable.svelte',
    './explore.ts',
  ],
  { query: '?raw', import: 'default', eager: true },
) as Record<string, string>

// Built from parts so this file never matches itself.
const BANNED = new RegExp(['lu', 'ck'].join(''), 'i')

describe('no chance framing on Explore', () => {
  it('scans all five Explore sources', () => {
    expect(Object.keys(sources)).toHaveLength(5)
  })

  it('no Explore source uses the banned word', () => {
    const offenders = Object.entries(sources)
      .filter(([, src]) => BANNED.test(src))
      .map(([path]) => path)
    expect(offenders).toEqual([])
  })

  it('the pattern would catch it in any case', () => {
    expect(BANNED.test('Un' + 'lu' + 'cky')).toBe(true)
    expect(BANNED.test('LU' + 'CK')).toBe(true)
  })
})

import { describe, expect, it } from 'vitest'
import { MY_TEAM_KEY, readMyTeam, validMyTeam, writeMyTeam, type StorageLike } from './myteam'

function fake(initial: Record<string, string> = {}): StorageLike & { data: Record<string, string> } {
  const data = { ...initial }
  return {
    data,
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => {
      data[k] = v
    },
    removeItem: (k) => {
      delete data[k]
    },
  }
}

const throwing: StorageLike = {
  getItem: () => {
    throw new Error('SecurityError')
  },
  setItem: () => {
    throw new Error('QuotaExceededError')
  },
  removeItem: () => {
    throw new Error('SecurityError')
  },
}

const teams = { BUF: {}, KC: {} }

describe('myteam storage', () => {
  it('uses the fgs.myTeam key', () => {
    expect(MY_TEAM_KEY).toBe('fgs.myTeam')
  })
  it('reads the stored value', () => {
    expect(readMyTeam(fake({ [MY_TEAM_KEY]: 'BUF' }))).toBe('BUF')
  })
  it('reads null when nothing is stored', () => {
    expect(readMyTeam(fake())).toBeNull()
  })
  it('reads null without storage', () => {
    expect(readMyTeam(undefined)).toBeNull()
  })
  it('reads null when getItem throws', () => {
    expect(readMyTeam(throwing)).toBeNull()
  })
  it('writes a string', () => {
    const s = fake()
    expect(writeMyTeam(s, 'KC')).toBe(true)
    expect(s.data[MY_TEAM_KEY]).toBe('KC')
  })
  it('removes on null', () => {
    const s = fake({ [MY_TEAM_KEY]: 'KC' })
    expect(writeMyTeam(s, null)).toBe(true)
    expect(MY_TEAM_KEY in s.data).toBe(false)
  })
  it('returns false without storage or when storage throws', () => {
    expect(writeMyTeam(undefined, 'KC')).toBe(false)
    expect(writeMyTeam(throwing, 'KC')).toBe(false)
    expect(writeMyTeam(throwing, null)).toBe(false)
  })
})

describe('validMyTeam', () => {
  it('accepts a known team', () => {
    expect(validMyTeam('BUF', teams)).toBe('BUF')
  })
  it.each([null, undefined, '', 'XYZ', 'buf', '__proto__', 'constructor', '<script>'])('rejects %s', (v) => {
    expect(validMyTeam(v as string | null, teams)).toBeNull()
  })
  it('rejects when teams are missing', () => {
    expect(validMyTeam('BUF', undefined)).toBeNull()
  })
})

import { describe, expect, it } from 'vitest'
import { boardHash, parseHash } from './router'

describe('parseHash', () => {
  it('empty and root hashes are the latest board', () => {
    expect(parseHash('')).toEqual({ kind: 'latest' })
    expect(parseHash('#')).toEqual({ kind: 'latest' })
    expect(parseHash('#/')).toEqual({ kind: 'latest' })
  })
  it('parses board routes', () => {
    expect(parseHash('#/board/2007/21')).toEqual({ kind: 'board', season: 2007, week: 21 })
    expect(parseHash('#/board/2007/21/')).toEqual({ kind: 'board', season: 2007, week: 21 })
    expect(parseHash('#/board/1999/0')).toEqual({ kind: 'board', season: 1999, week: 0 })
  })
  it('stays pure: out-of-range seasons still parse (App validates against meta)', () => {
    expect(parseHash('#/board/1800/3')).toEqual({ kind: 'board', season: 1800, week: 3 })
  })
  it('flags malformed routes as invalid', () => {
    expect(parseHash('#/board/abc/1')).toEqual({ kind: 'invalid' })
    expect(parseHash('#/board/2007')).toEqual({ kind: 'invalid' })
    expect(parseHash('#/board/2007/123')).toEqual({ kind: 'invalid' })
    expect(parseHash('#/nope')).toEqual({ kind: 'invalid' })
  })
  it('recognises routes reserved for later phases', () => {
    for (const h of ['#/team/BUF', '#/team/BUF/2024/3', '#/history', '#/records', '#/methodology']) {
      expect(parseHash(h)).toEqual({ kind: 'reserved' })
    }
  })
})

describe('boardHash', () => {
  it('builds the board hash', () => expect(boardHash(2007, 21)).toBe('#/board/2007/21'))
  it('round-trips through parseHash', () => {
    for (const [s, w] of [[1999, 0], [2020, 21], [2026, 9]]) {
      expect(parseHash(boardHash(s, w))).toEqual({ kind: 'board', season: s, week: w })
    }
  })
})

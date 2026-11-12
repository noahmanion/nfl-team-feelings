import { describe, expect, it } from 'vitest'
import { boardHash, exploreHash, historyHash, methodologyHash, parseHash, recordsHash, teamHash } from './router'

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
  it('parses history routes, uppercasing the team', () => {
    expect(parseHash('#/history')).toEqual({ kind: 'history' })
    expect(parseHash('#/history/')).toEqual({ kind: 'history' })
    expect(parseHash('#/history/buf')).toEqual({ kind: 'history', team: 'BUF' })
    expect(parseHash('#/history/BUF/')).toEqual({ kind: 'history', team: 'BUF' })
    expect(parseHash('#/history/det')).toEqual({ kind: 'history', team: 'DET' })
    expect(parseHash('#/history/TOOLONG')).toEqual({ kind: 'invalid' })
    expect(parseHash('#/history/B1')).toEqual({ kind: 'invalid' })
  })
  it('no longer reserves #/records', () => {
    for (const h of ['#/records', '#/records/']) {
      expect(parseHash(h)).not.toEqual({ kind: 'reserved' })
    }
  })
})

describe('team routes', () => {
  it('parses team routes, uppercasing the team', () => {
    expect(parseHash('#/team/buf')).toEqual({ kind: 'team', team: 'BUF' })
    expect(parseHash('#/team/BUF/')).toEqual({ kind: 'team', team: 'BUF' })
    expect(parseHash('#/team/BUF/2024/5')).toEqual({ kind: 'team', team: 'BUF', season: 2024, week: 5 })
    expect(parseHash('#/team/kc/1999/0/')).toEqual({ kind: 'team', team: 'KC', season: 1999, week: 0 })
  })
  it('parses a team season without a week (App redirects it to the team page)', () => {
    expect(parseHash('#/team/buf/2024')).toEqual({ kind: 'team', team: 'BUF', season: 2024 })
  })
  it('flags malformed team routes as invalid', () => {
    expect(parseHash('#/team/TOOLONG')).toEqual({ kind: 'invalid' })
    expect(parseHash('#/team/B1')).toEqual({ kind: 'invalid' })
    expect(parseHash('#/team/BUF/2024/')).toEqual({ kind: 'team', team: 'BUF', season: 2024 })
    expect(parseHash('#/team/BUF/24')).toEqual({ kind: 'invalid' })
    expect(parseHash('#/team')).toEqual({ kind: 'invalid' })
  })
  it('builds team hashes', () => {
    expect(teamHash('kc')).toBe('#/team/KC')
    expect(teamHash('KC', 2024, 3)).toBe('#/team/KC/2024/3')
    expect(teamHash('KC', 2024, 0)).toBe('#/team/KC/2024/0')
  })
  it('round-trips through parseHash', () => {
    expect(parseHash(teamHash('det'))).toEqual({ kind: 'team', team: 'DET' })
    expect(parseHash(teamHash('DEN', 2026, 9))).toEqual({ kind: 'team', team: 'DEN', season: 2026, week: 9 })
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

describe('historyHash', () => {
  it('builds history hashes', () => {
    expect(historyHash()).toBe('#/history')
    expect(historyHash('det')).toBe('#/history/DET')
  })
  it('round-trips through parseHash', () => {
    expect(parseHash(historyHash())).toEqual({ kind: 'history' })
    expect(parseHash(historyHash('KC'))).toEqual({ kind: 'history', team: 'KC' })
  })
})

describe('methodology route', () => {
  it('parses #/methodology with and without a trailing slash', () => {
    expect(parseHash('#/methodology')).toEqual({ kind: 'methodology' })
    expect(parseHash('#/methodology/')).toEqual({ kind: 'methodology' })
  })
  it('round-trips methodologyHash', () => {
    expect(methodologyHash).toBe('#/methodology')
    expect(parseHash(methodologyHash)).toEqual({ kind: 'methodology' })
  })
})

describe('records route', () => {
  it('parses #/records with and without a trailing slash', () => {
    expect(parseHash('#/records')).toEqual({ kind: 'records' })
    expect(parseHash('#/records/')).toEqual({ kind: 'records' })
    expect(parseHash('#/records/x')).toEqual({ kind: 'invalid' })
  })
  it('round-trips recordsHash', () => {
    expect(recordsHash).toBe('#/records')
    expect(parseHash(recordsHash)).toEqual({ kind: 'records' })
  })
})

describe('explore route', () => {
  it('parses #/explore with and without a trailing slash', () => {
    expect(parseHash('#/explore')).toEqual({ kind: 'explore' })
    expect(parseHash('#/explore/')).toEqual({ kind: 'explore' })
  })
  it('parses an explicit season/week and a season alone', () => {
    expect(parseHash('#/explore/2025/10')).toEqual({ kind: 'explore', season: 2025, week: 10 })
    expect(parseHash('#/explore/2025/10/')).toEqual({ kind: 'explore', season: 2025, week: 10 })
    expect(parseHash('#/explore/2025')).toEqual({ kind: 'explore', season: 2025 })
  })
  it('flags malformed explore routes as invalid', () => {
    expect(parseHash('#/explore/abc')).toEqual({ kind: 'invalid' })
    expect(parseHash('#/explore/2025/123')).toEqual({ kind: 'invalid' })
  })
  it('builds explore hashes (latest unless both season and week are given)', () => {
    expect(exploreHash()).toBe('#/explore')
    expect(exploreHash(2025)).toBe('#/explore')
    expect(exploreHash(2025, 10)).toBe('#/explore/2025/10')
    expect(exploreHash(1999, 0)).toBe('#/explore/1999/0')
  })
  it('round-trips through parseHash', () => {
    expect(parseHash(exploreHash())).toEqual({ kind: 'explore' })
    expect(parseHash(exploreHash(2025, 10))).toEqual({ kind: 'explore', season: 2025, week: 10 })
  })
})

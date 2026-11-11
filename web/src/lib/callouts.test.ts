import { describe, expect, it } from 'vitest'
import { calloutHref, cardCallouts, forTeam, forWeek, moverCallouts, orderCallouts } from './callouts'
import { teamHash } from './router'
import type { Callout, CalloutType, SeasonFile } from './types'

const c = (type: CalloutType, franchise: string, week = 9, season = 2026): Callout => ({
  type, season, week, franchise, headline: `${franchise} ${type}`, detail: 'd', evidence: null, stat: 1, start: null, band: 3,
})

const list = [c('worried', 'CLE'), c('hopeful', 'SEA'), c('mover_up', 'HOU'), c('mover_down', 'CLE'), c('hopeful', 'CLE'),
  c('misery', 'TEN'), c('joy', 'KC'), c('mover_up', 'SEA')]

describe('forWeek', () => {
  const file: SeasonFile = { season: 2008, weeks: {}, callouts: { '10': [c('worried', 'NYG', 10, 2008)] } }
  it('returns that week’s callouts', () => {
    expect(forWeek(file, 10)).toHaveLength(1)
  })
  it('returns [] for a missing week, an old file without callouts, or no file', () => {
    expect(forWeek(file, 3)).toEqual([])
    expect(forWeek({ season: 2008, weeks: {} }, 10)).toEqual([])
    expect(forWeek(null, 10)).toEqual([])
    expect(forWeek(undefined, 10)).toEqual([])
  })
})

describe('forTeam / cardCallouts / moverCallouts', () => {
  it('filters to one franchise, order kept', () => {
    expect(forTeam(list, 'CLE').map((x) => x.type)).toEqual(['worried', 'mover_down', 'hopeful'])
  })
  it('keeps only card types, order kept', () => {
    expect(cardCallouts(list).map((x) => x.franchise)).toEqual(['CLE', 'SEA', 'CLE', 'TEN', 'KC'])
  })
  it('splits movers into up and down, order kept', () => {
    const m = moverCallouts(list)
    expect(m.up.map((x) => x.franchise)).toEqual(['HOU', 'SEA'])
    expect(m.down.map((x) => x.franchise)).toEqual(['CLE'])
  })
})

describe('orderCallouts', () => {
  it('puts my team first, stably', () => {
    const out = orderCallouts(list, 'CLE')
    expect(out.slice(0, 3).map((x) => x.type)).toEqual(['worried', 'mover_down', 'hopeful'])
    expect(out.slice(3).map((x) => x.franchise)).toEqual(['SEA', 'HOU', 'TEN', 'KC', 'SEA'])
  })
  it('null or unknown team keeps the order', () => {
    expect(orderCallouts(list, null)).toEqual(list)
    expect(orderCallouts(list, 'ZZZ')).toEqual(list)
  })
  it('never mutates the input', () => {
    const copy = list.slice()
    const out = orderCallouts(list, 'KC')
    expect(list).toEqual(copy)
    expect(out).not.toBe(list)
    expect(orderCallouts(list, null)).not.toBe(list)
  })
})

describe('calloutHref', () => {
  it('is always the stable season/week team link', () => {
    const x = c('worried', 'cle', 10, 2008)
    expect(calloutHref(x)).toBe(teamHash('cle', 2008, 10))
    expect(calloutHref(x)).toBe('#/team/CLE/2008/10')
  })
})

import { describe, expect, it } from 'vitest'
import { eraAbbr, eraName, eraText, isActiveFranchise } from './teamNames'
import type { Meta } from './types'

const t = (name: string) => ({ name, nick: '', primary: '#000000', secondary: '#ffffff' })
const meta = {
  teams: {
    LAC: t('Los Angeles Chargers'),
    LA: t('Los Angeles Rams'),
    LV: t('Las Vegas Raiders'),
    WAS: t('Washington Commanders'),
    KC: t('Kansas City Chiefs'),
    HOU: t('Houston Texans'),
  },
} as Pick<Meta, 'teams'>

describe('eraName', () => {
  it('Chargers: San Diego through 2016, meta name from 2017', () => {
    expect(eraName('LAC', 2010, meta)).toBe('San Diego Chargers')
    expect(eraName('LAC', 2016, meta)).toBe('San Diego Chargers')
    expect(eraName('LAC', 2017, meta)).toBe('Los Angeles Chargers')
  })
  it('Rams: St. Louis through 2015, meta name from 2016', () => {
    expect(eraName('LA', 2015, meta)).toBe('St. Louis Rams')
    expect(eraName('LA', 2016, meta)).toBe('Los Angeles Rams')
  })
  it('Raiders: Oakland through 2019, meta name from 2020', () => {
    expect(eraName('LV', 2019, meta)).toBe('Oakland Raiders')
    expect(eraName('LV', 2020, meta)).toBe('Las Vegas Raiders')
  })
  it('Washington: plain through 2019, Football Team 2020-2021, meta name from 2022', () => {
    expect(eraName('WAS', 2005, meta)).toBe('Washington')
    expect(eraName('WAS', 2019, meta)).toBe('Washington')
    expect(eraName('WAS', 2020, meta)).toBe('Washington Football Team')
    expect(eraName('WAS', 2021, meta)).toBe('Washington Football Team')
    expect(eraName('WAS', 2022, meta)).toBe('Washington Commanders')
  })
  it('unchanged franchises use the meta name; unknown codes fall back to the code', () => {
    expect(eraName('KC', 2005, meta)).toBe('Kansas City Chiefs')
    expect(eraName('XXX', 2010, meta)).toBe('XXX')
  })
})

describe('eraAbbr', () => {
  it('maps relocated franchises to their era codes at each boundary', () => {
    expect(eraAbbr('LAC', 2016)).toBe('SD')
    expect(eraAbbr('LAC', 2017)).toBe('LAC')
    expect(eraAbbr('LA', 2015)).toBe('STL')
    expect(eraAbbr('LA', 2016)).toBe('LA')
    expect(eraAbbr('LV', 2019)).toBe('OAK')
    expect(eraAbbr('LV', 2020)).toBe('LV')
  })
  it('keeps WAS and other codes as-is', () => {
    expect(eraAbbr('WAS', 2005)).toBe('WAS')
    expect(eraAbbr('WAS', 2020)).toBe('WAS')
    expect(eraAbbr('WAS', 2024)).toBe('WAS')
    expect(eraAbbr('KC', 2010)).toBe('KC')
  })
})

describe('isActiveFranchise', () => {
  it('HOU starts in 2002; everyone else is always active', () => {
    expect(isActiveFranchise('HOU', 2001)).toBe(false)
    expect(isActiveFranchise('HOU', 2002)).toBe(true)
    expect(isActiveFranchise('KC', 1999)).toBe(true)
  })
})

describe('eraText', () => {
  it('rewrites to Washington through 2019', () => {
    expect(eraText('The Commanders are a below-average team', 'WAS', 2005)).toBe('Washington are a below-average team')
    expect(eraText('Commanders fans have been miserable', 'WAS', 2010).startsWith('Washington fans')).toBe(true)
    expect(eraText('Commanders +7', 'WAS', 2019)).toBe('Washington +7')
  })
  it('rewrites to Football Team in 2020-2021, keeping the article', () => {
    expect(eraText('The Commanders are good', 'WAS', 2020)).toBe('The Football Team are good')
    expect(eraText('Recent form: the Commanders are hot', 'WAS', 2021)).toBe('Recent form: the Football Team are hot')
    expect(eraText('Commanders +2', 'WAS', 2021)).toBe('Football Team +2')
  })
  it('leaves text unchanged from 2022, for other franchises, and for empty input', () => {
    expect(eraText('The Commanders are good', 'WAS', 2022)).toBe('The Commanders are good')
    expect(eraText('The Commanders are good', 'KC', 2005)).toBe('The Commanders are good')
    expect(eraText('', 'WAS', 2005)).toBe('')
    expect(eraText(null as unknown as string, 'WAS', 2005)).toBe('')
  })
})

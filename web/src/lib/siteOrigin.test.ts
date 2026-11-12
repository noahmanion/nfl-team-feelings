import { describe, expect, it } from 'vitest'
import { FALLBACK_ORIGIN, resolveSiteOrigin } from './siteOrigin'

describe('resolveSiteOrigin', () => {
  it('prefers an explicit SITE_ORIGIN', () => {
    expect(
      resolveSiteOrigin({
        SITE_ORIGIN: 'https://example.com',
        VERCEL_PROJECT_PRODUCTION_URL: 'foo.vercel.app',
      }),
    ).toBe('https://example.com')
  })

  it('falls back to https:// + VERCEL_PROJECT_PRODUCTION_URL', () => {
    expect(resolveSiteOrigin({ VERCEL_PROJECT_PRODUCTION_URL: 'foo.vercel.app' })).toBe(
      'https://foo.vercel.app',
    )
  })

  it('uses the hard-coded fallback when nothing is set', () => {
    expect(FALLBACK_ORIGIN).toBe('https://nfl-team-feelings.vercel.app')
    expect(resolveSiteOrigin({})).toBe(FALLBACK_ORIGIN)
    expect(resolveSiteOrigin({ SITE_ORIGIN: '  ', VERCEL_PROJECT_PRODUCTION_URL: '' })).toBe(
      FALLBACK_ORIGIN,
    )
  })

  it('strips trailing slashes', () => {
    expect(resolveSiteOrigin({ SITE_ORIGIN: 'https://example.com/' })).toBe('https://example.com')
    expect(resolveSiteOrigin({ VERCEL_PROJECT_PRODUCTION_URL: 'foo.vercel.app//' })).toBe(
      'https://foo.vercel.app',
    )
  })
})

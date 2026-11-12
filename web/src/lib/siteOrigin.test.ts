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

  it('tolerates a VERCEL_PROJECT_PRODUCTION_URL that already includes a scheme', () => {
    expect(resolveSiteOrigin({ VERCEL_PROJECT_PRODUCTION_URL: 'https://foo.vercel.app' })).toBe(
      'https://foo.vercel.app',
    )
    expect(resolveSiteOrigin({ VERCEL_PROJECT_PRODUCTION_URL: 'http://foo.vercel.app/' })).toBe(
      'https://foo.vercel.app',
    )
  })

  it('accepts http origins and normalizes case', () => {
    expect(resolveSiteOrigin({ SITE_ORIGIN: 'http://localhost:4173' })).toBe(
      'http://localhost:4173',
    )
    expect(resolveSiteOrigin({ SITE_ORIGIN: 'HTTPS://Example.COM/' })).toBe('https://example.com')
  })

  it('throws on a schemeless SITE_ORIGIN', () => {
    expect(() => resolveSiteOrigin({ SITE_ORIGIN: 'example.com' })).toThrow(/absolute http\(s\)/)
    expect(() => resolveSiteOrigin({ SITE_ORIGIN: 'localhost:5173' })).toThrow(/absolute http\(s\)/)
    expect(() => resolveSiteOrigin({ SITE_ORIGIN: '/relative/path' })).toThrow(/absolute http\(s\)/)
  })

  it('throws on non-http(s) schemes and unparseable values', () => {
    expect(() => resolveSiteOrigin({ SITE_ORIGIN: 'ftp://example.com' })).toThrow(
      /absolute http\(s\)/,
    )
    expect(() => resolveSiteOrigin({ SITE_ORIGIN: 'javascript:alert(1)' })).toThrow(
      /absolute http\(s\)/,
    )
    expect(() => resolveSiteOrigin({ SITE_ORIGIN: 'https://exa mple.com' })).toThrow(
      /absolute http\(s\)/,
    )
    expect(() => resolveSiteOrigin({ VERCEL_PROJECT_PRODUCTION_URL: 'bad host<' })).toThrow(
      /absolute http\(s\)/,
    )
  })

  it('never returns characters that break out of an HTML attribute', () => {
    const origin = resolveSiteOrigin({ SITE_ORIGIN: 'https://example.com/a"b<c>' })
    expect(origin).not.toMatch(/["<>]/)
    expect(origin).toBe('https://example.com/a%22b%3Cc%3E')
  })
})

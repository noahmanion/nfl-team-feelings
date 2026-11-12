import { describe, expect, it } from 'vitest'

// LOGO-01: team logos are committed under public/logos and served locally. No source file may
// reference an external logo host at runtime (ESPN CDN or the broken nflverse Wikipedia URLs).
const sources = import.meta.glob(['../**/*.{ts,svelte}', '!./nohotlink.test.ts'], {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>
const html = import.meta.glob('../../index.html', { query: '?raw', import: 'default', eager: true }) as Record<
  string,
  string
>

// Built from parts so this file never matches itself.
const hosts = ['espn' + 'cdn', 'wiki' + 'pedia'].join('|')
const EXTERNAL_LOGO = new RegExp(`(${hosts})\\.(com|org)\\/\\S*\\.(png|svg)`, 'i')

describe('no logo hotlinking', () => {
  it('scans the app sources and index.html', () => {
    expect(Object.keys(sources).length).toBeGreaterThan(10)
    expect(Object.keys(html)).toHaveLength(1)
  })

  it('has no external logo URL anywhere', () => {
    const offenders = Object.entries({ ...sources, ...html })
      .filter(([, src]) => EXTERNAL_LOGO.test(src))
      .map(([path]) => path)
    expect(offenders).toEqual([])
  })

  it('the pattern would catch a hotlink', () => {
    expect(EXTERNAL_LOGO.test('src="https://a.' + 'espn' + 'cdn.com/i/teamlogos/nfl/500/kc.png"')).toBe(true)
  })
})

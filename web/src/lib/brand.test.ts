/// <reference types="node" />
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

// DESIGN-01 / D-01, D-02, D-06: fonts are self-hosted via exact-pinned Fontsource packages,
// imported before app.css; no third-party font host and no 538 branding in shipped source.
const mainRaw = Object.values(
  import.meta.glob('../main.ts', { query: '?raw', import: 'default', eager: true }) as Record<string, string>,
)[0]
const pkgRaw = Object.values(
  import.meta.glob('../../package.json', { query: '?raw', import: 'default', eager: true }) as Record<string, string>,
)[0]
// Vitest stubs CSS modules (even with ?raw), so CSS files are read from disk instead.
const readCss = (rel: string) => readFileSync(new URL(rel, import.meta.url), 'utf8')
const cssRaw = readCss('../app.css')
const tsSvelte = import.meta.glob(['../**/*.{ts,svelte}', '!./brand.test.ts'], {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>
const css = Object.fromEntries(Object.keys(import.meta.glob('../**/*.css')).map((p) => [p, readCss(p)]))
const sources = { ...tsSvelte, ...css }
const html = import.meta.glob('../../index.html', { query: '?raw', import: 'default', eager: true }) as Record<
  string,
  string
>
const all = { ...sources, ...html }

// Built from parts so this file never matches itself.
const FONT_HOSTS = ['fonts.' + 'googleapis', 'fonts.' + 'gstatic']
const BRAND_538 = new RegExp(['five', 'thirty', 'eight'].join('') + '|\\b' + '53' + '8\\b', 'i')

const FONT_IMPORTS = ['@fontsource-variable/inter', '@fontsource/ibm-plex-mono/400.css', '@fontsource/ibm-plex-mono/600.css']

describe('brand guard', () => {
  it('main.ts imports the fonts before app.css', () => {
    const cssAt = mainRaw.indexOf('./app.css')
    expect(cssAt).toBeGreaterThan(-1)
    for (const spec of FONT_IMPORTS) {
      const at = mainRaw.indexOf(`'${spec}'`)
      expect(at, spec).toBeGreaterThan(-1)
      expect(at, spec).toBeLessThan(cssAt)
    }
  })

  it('package.json pins Fontsource exactly', () => {
    const pkg = JSON.parse(pkgRaw)
    expect(pkg.dependencies['@fontsource-variable/inter']).toBe('5.3.0')
    expect(pkg.dependencies['@fontsource/ibm-plex-mono']).toBe('5.3.0')
    expect(pkg.devDependencies['@fontsource/inter']).toBe('5.3.0')
  })

  it('scans the app sources and index.html', () => {
    expect(Object.keys(sources).length).toBeGreaterThan(10)
    expect(css['../app.css']?.length ?? 0).toBeGreaterThan(100)
    expect(Object.keys(html)).toHaveLength(1)
  })

  it('has no font CDN reference', () => {
    const offenders = Object.entries(all)
      .filter(([, src]) => FONT_HOSTS.some((h) => src.includes(h)))
      .map(([path]) => path)
    expect(offenders).toEqual([])
  })

  it('has no 538 branding string', () => {
    const offenders = Object.entries(all)
      .filter(([, src]) => BRAND_538.test(src))
      .map(([path]) => path)
    expect(offenders).toEqual([])
  })

  it('the 538 pattern would catch a credit', () => {
    expect(BRAND_538.test('Inspired by ' + 'Five' + 'Thirty' + 'Eight')).toBe(true)
    expect(BRAND_538.test('the ' + '53' + '8 model')).toBe(true)
    expect(BRAND_538.test('15380')).toBe(false)
  })

  it('app.css declares Inter Variable and IBM Plex Mono families', () => {
    expect(cssRaw).toMatch(/--font-sans:[^;]*'Inter Variable'/)
    expect(cssRaw).toMatch(/--font-mono:[^;]*'IBM Plex Mono'/)
  })
})

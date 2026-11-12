import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { buildShare } from './share.mjs'
import { shareTargets, teamImagePath, teamSharePath, calloutSharePath, calloutImagePath } from '../src/lib/share.ts'

const webRoot = fileURLToPath(new URL('..', import.meta.url))
const dataDir = join(webRoot, 'public/data')
const logoDir = join(webRoot, 'public/logos')
const meta = JSON.parse(readFileSync(join(dataDir, 'meta.json'), 'utf8'))
const ORIGIN = 'https://example.test'

/** Expected per-target rows/callouts, computed from the committed data (never hardcoded). */
function expected() {
  const files = new Map()
  const out = []
  for (const t of shareTargets(meta)) {
    if (!files.has(t.season)) files.set(t.season, JSON.parse(readFileSync(join(dataDir, `snapshots/${t.season}.json`), 'utf8')))
    const f = files.get(t.season)
    out.push({ ...t, rows: f.weeks?.[String(t.week)] ?? [], callouts: f.callouts?.[String(t.week)] ?? [] })
  }
  return out
}

function assertPng(file) {
  const buf = readFileSync(file)
  expect(buf.subarray(1, 4).toString('latin1')).toBe('PNG')
  expect(buf.readUInt32BE(16)).toBe(1200)
  expect(buf.readUInt32BE(20)).toBe(630)
  expect(buf.length).toBeLessThanOrEqual(300 * 1024)
}

function walk(dir, name, acc = []) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name)
    if (e.isDirectory()) walk(p, name, acc)
    else if (e.name === name) acc.push(p)
  }
  return acc
}

describe('buildShare (integration against public/data)', () => {
  let tmp
  let summary
  const lines = []
  const exp = expected()
  const nPages = exp.reduce((n, t) => (t.rows.length ? n + t.rows.length + t.callouts.length : n), 0)

  beforeAll(async () => {
    tmp = mkdtempSync(join(tmpdir(), 'fgs-share-'))
    summary = await buildShare({ dataDir, outDir: tmp, logoDir, env: { SITE_ORIGIN: ORIGIN }, log: (l) => lines.push(l) })
  }, 120_000)
  afterAll(() => tmp && rmSync(tmp, { recursive: true, force: true }))

  it('has at least one target with rows', () => {
    expect(exp.length).toBeGreaterThan(0)
    expect(nPages).toBeGreaterThan(0)
  })

  it('returns a summary whose counts match the data', () => {
    expect(summary.pages).toBe(nPages)
    expect(summary.cards).toBe(summary.pages + 1)
    expect(summary.targets).toBe(exp.filter((t) => t.rows.length > 0).length)
    expect(summary.seconds).toBeGreaterThan(0)
    expect(summary.msPerCard).toBeGreaterThan(0)
    expect(summary.maxKB).toBeLessThanOrEqual(300)
    expect(lines.some((l) => /^share: rendered \d+ cards in [\d.]+s \(\d+ms\/card avg\)$/.test(l))).toBe(true)
  })

  it('writes one PNG + index.html per team row and per callout', () => {
    for (const t of exp) {
      for (const r of t.rows) {
        assertPng(join(tmp, teamImagePath(r.franchise, t.season, t.week)))
        expect(existsSync(join(tmp, teamSharePath(r.franchise, t.season, t.week), 'index.html'))).toBe(true)
      }
      for (const c of t.callouts) {
        assertPng(join(tmp, calloutImagePath(c)))
        expect(existsSync(join(tmp, calloutSharePath(c), 'index.html'))).toBe(true)
      }
    }
    const pages = walk(join(tmp, 's'), 'index.html')
    expect(pages.length).toBe(nPages)
  })

  it('the latest target has a BUF page and its first callout has a page', () => {
    const last = exp.at(-1)
    if (last.rows.some((r) => r.franchise === 'BUF')) {
      expect(existsSync(join(tmp, teamImagePath('BUF', last.season, last.week)))).toBe(true)
      expect(existsSync(join(tmp, teamSharePath('BUF', last.season, last.week), 'index.html'))).toBe(true)
    }
    if (last.callouts.length) expect(existsSync(join(tmp, calloutSharePath(last.callouts[0]), 'index.html'))).toBe(true)
  })

  it('every page has absolute og:image (existing file) and self og:url', () => {
    for (const page of walk(join(tmp, 's'), 'index.html')) {
      const html = readFileSync(page, 'utf8')
      const img = html.match(/property="og:image" content="([^"]+)"/)[1]
      expect(img.startsWith(ORIGIN + '/og/')).toBe(true)
      const file = join(tmp, img.slice(ORIGIN.length))
      expect(existsSync(file) && statSync(file).size > 0).toBe(true)
      const url = html.match(/property="og:url" content="([^"]+)"/)[1]
      const dir = '/' + page.slice(tmp.length + 1, -'index.html'.length).split('\\').join('/')
      expect(url).toBe(ORIGIN + dir)
      expect(url.endsWith('/')).toBe(true)
    }
  })

  it('re-renders og-default.png', () => {
    assertPng(join(tmp, 'og-default.png'))
  })

  it('succeeds with VITE_LOGOS=off (chip cards)', async () => {
    const tmp2 = mkdtempSync(join(tmpdir(), 'fgs-share-off-'))
    try {
      const s = await buildShare({ dataDir, outDir: tmp2, logoDir, env: { SITE_ORIGIN: ORIGIN, VITE_LOGOS: 'off' }, log: () => {} })
      expect(s.pages).toBe(nPages)
      assertPng(join(tmp2, 'og-default.png'))
    } finally {
      rmSync(tmp2, { recursive: true, force: true })
    }
  }, 120_000)
})

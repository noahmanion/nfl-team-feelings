import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import {
  SHARE_LAUNCH,
  calloutCopyUrl,
  calloutId,
  calloutImagePath,
  calloutShareHash,
  calloutShareMeta,
  calloutSharePath,
  escapeHtml,
  hasSharePage,
  shareTargets,
  sharePageHtml,
  teamCopyUrl,
  teamImagePath,
  teamShareMeta,
  teamSharePath,
} from './share.ts'
import { teamHash } from './router.ts'
import type { Meta, SeasonMeta } from './types'

const realMeta = JSON.parse(
  readFileSync(fileURLToPath(new URL('../../public/data/meta.json', import.meta.url)), 'utf8'),
) as Meta

function season(s: number, maxWeek: number): SeasonMeta {
  const week_labels: Record<string, string> = {}
  for (let w = 0; w <= maxWeek; w++) week_labels[String(w)] = w === 0 ? 'Preseason' : `Week ${w}`
  return { season: s, max_week: maxWeek, reg_weeks: 18, n_teams: 32, week_labels }
}
const synthMeta = { seasons: [season(2025, 22), season(2026, 12), season(2027, 2)] }

const hou = { season: 2026, week: 9, franchise: 'HOU', type: 'mover_up' as const }
const deep = (h: string) => 'DEEP' + h
const ORIGIN = 'http://localhost:4173'

describe('path builders', () => {
  it('builds team share and image paths (FR uppercased, week unpadded)', () => {
    expect(teamSharePath('buf', 2026, 9)).toBe('/s/team/BUF/2026-w9/')
    expect(teamImagePath('BUF', 2026, 9)).toBe('/og/team/BUF/2026-w9.png')
    expect(teamSharePath('NE', 2027, 12)).toBe('/s/team/NE/2027-w12/')
  })

  it('builds callout id, share and image paths', () => {
    expect(calloutId(hou)).toBe('2026/9/HOU-mover-up')
    expect(calloutSharePath(hou)).toBe('/s/c/2026/9/HOU-mover-up/')
    expect(calloutImagePath(hou)).toBe('/og/c/2026/9/HOU-mover-up.png')
    expect(calloutId({ season: 2026, week: 9, franchise: 'CLE', type: 'worried' })).toBe('2026/9/CLE-worried')
  })

  it('callout share hash equals the season/week team hash (calloutHref)', () => {
    expect(calloutShareHash(hou)).toBe(teamHash('HOU', 2026, 9))
    expect(calloutShareHash(hou)).toBe('#/team/HOU/2026/9')
  })
})

describe('launch gate', () => {
  it('launches at 2026 week 9', () => {
    expect(SHARE_LAUNCH).toEqual({ season: 2026, week: 9 })
  })

  it('hasSharePage against the real meta', () => {
    expect(hasSharePage(2026, 8, realMeta)).toBe(false)
    expect(hasSharePage(2026, 9, realMeta)).toBe(true)
    expect(hasSharePage(2026, 10, realMeta)).toBe(false)
    expect(hasSharePage(2025, 22, realMeta)).toBe(false)
  })

  it('hasSharePage for a later season and a missing season', () => {
    expect(hasSharePage(2027, 1, synthMeta)).toBe(true)
    expect(hasSharePage(2027, 0, synthMeta)).toBe(true)
    expect(hasSharePage(2027, 3, synthMeta)).toBe(false)
    expect(hasSharePage(2028, 1, synthMeta)).toBe(false)
  })

  it('shareTargets on the real meta is just the launch week', () => {
    expect(shareTargets(realMeta)).toEqual([{ season: 2026, week: 9 }])
  })

  it('shareTargets agrees with hasSharePage on a synthetic meta, sorted ascending', () => {
    const targets = shareTargets(synthMeta)
    for (const t of targets) expect(hasSharePage(t.season, t.week, synthMeta)).toBe(true)
    const expected: { season: number; week: number }[] = []
    for (const s of synthMeta.seasons)
      for (let w = 0; w <= 30; w++) if (hasSharePage(s.season, w, synthMeta)) expected.push({ season: s.season, week: w })
    expect(targets).toEqual(expected)
    expect(targets[0]).toEqual({ season: 2026, week: 9 })
    expect(targets.at(-1)).toEqual({ season: 2027, week: 2 })
    expect(targets).toHaveLength(4 + 3)
  })

  it('shareTargets sorts numerically even when label keys are out of order', () => {
    const odd = { seasons: [{ ...season(2027, 0), week_labels: { '10': 'x', '2': 'y', '0': 'z' } }, season(2026, 10)] }
    expect(shareTargets(odd)).toEqual([
      { season: 2026, week: 9 },
      { season: 2026, week: 10 },
      { season: 2027, week: 0 },
      { season: 2027, week: 2 },
      { season: 2027, week: 10 },
    ])
  })
})

describe('escapeHtml', () => {
  it('escapes hostile input', () => {
    const out = escapeHtml(`<script>"x"&'y'</script>`)
    expect(out).not.toMatch(/[<>"']/)
    expect(out.replace(/&(amp|lt|gt|quot|#39);/g, '')).not.toContain('&')
    expect(out).toBe('&lt;script&gt;&quot;x&quot;&amp;&#39;y&#39;&lt;/script&gt;')
  })

  it('escapes & before the other entities (no double encoding of the others)', () => {
    expect(escapeHtml('a & <b>')).toBe('a &amp; &lt;b&gt;')
    expect(escapeHtml('&lt;')).toBe('&amp;lt;')
  })
})

describe('copy URL helpers', () => {
  it('teamCopyUrl uses the share page for a launched week', () => {
    expect(teamCopyUrl({ team: 'BUF', season: 2026, week: 9 }, realMeta, ORIGIN, deep)).toBe(
      'http://localhost:4173/s/team/BUF/2026-w9/',
    )
  })

  it('teamCopyUrl falls back to the hash deep link before launch', () => {
    expect(teamCopyUrl({ team: 'BUF', season: 2026, week: 8 }, realMeta, ORIGIN, deep)).toBe('DEEP#/team/BUF/2026/8')
  })

  it('teamCopyUrl on the latest view pins meta.latest', () => {
    expect(teamCopyUrl({ team: 'buf', latest: true }, realMeta, ORIGIN, deep)).toBe(
      'http://localhost:4173/s/team/BUF/2026-w9/',
    )
  })

  it('teamCopyUrl on a latest view without a share page falls back to the unpinned hash', () => {
    const pre = { ...realMeta, latest: { season: 2026, week: 8 } }
    expect(teamCopyUrl({ team: 'BUF', latest: true }, pre, ORIGIN, deep)).toBe('DEEP#/team/BUF')
  })

  it('calloutCopyUrl branches on the launch gate', () => {
    expect(calloutCopyUrl(hou, realMeta, ORIGIN, deep)).toBe('http://localhost:4173/s/c/2026/9/HOU-mover-up/')
    expect(calloutCopyUrl({ ...hou, week: 8 }, realMeta, ORIGIN, deep)).toBe('DEEP#/team/HOU/2026/8')
    expect(calloutCopyUrl({ ...hou, season: 2025, week: 3 }, realMeta, ORIGIN, deep)).toBe('DEEP#/team/HOU/2025/3')
  })
})

describe('sharePageHtml', () => {
  const base = {
    origin: 'https://example.test',
    sharePath: '/s/team/BUF/2026-w9/',
    imagePath: '/og/team/BUF/2026-w9.png',
    hash: '#/team/BUF/2026/9',
    title: 'Buffalo Bills: 87, Planning the parade',
    description: 'Week 9 · 2026. #2 of 32 at 7-1.',
    imageAlt: 'alt text',
    linkName: 'Buffalo Bills',
  }
  const html = sharePageHtml(base)

  it('emits absolute og/twitter/canonical tags on the given origin', () => {
    expect(html).toContain('property="og:image" content="https://example.test/og/team/BUF/2026-w9.png"')
    expect(html).toContain('property="og:url" content="https://example.test/s/team/BUF/2026-w9/"')
    expect(html).toContain('rel="canonical" href="https://example.test/s/team/BUF/2026-w9/"')
    expect(html).toContain('name="twitter:card" content="summary_large_image"')
    expect(html).toContain('name="twitter:image" content="https://example.test/og/team/BUF/2026-w9.png"')
    expect(html).toContain('property="og:image:width" content="1200"')
    expect(html).toContain('property="og:image:height" content="630"')
    expect(html).toContain('<title>Buffalo Bills: 87, Planning the parade | Feel-Good Score</title>')
    expect(html.startsWith('<!doctype html>')).toBe(true)
    expect(html).not.toContain('http-equiv')
  })

  it('puts every og:/twitter: tag before the single script', () => {
    const script = html.indexOf('<script')
    expect(script).toBeGreaterThan(0)
    expect(html.indexOf('<script', script + 1)).toBe(-1)
    const tagIdx = [...html.matchAll(/(property="og:|name="twitter:|rel="canonical")/g)].map((m) => m.index ?? -1)
    expect(tagIdx.length).toBe(16)
    for (const i of tagIdx) expect(i).toBeLessThan(script)
  })

  it('redirects to the root-relative hash and links to it', () => {
    expect(html).toContain(`location.replace('/' + "#/team/BUF/2026/9")`)
    expect(html).toContain('href="/#/team/BUF/2026/9"')
    expect(html).toContain('Open Buffalo Bills on Feel-Good Score →')
    expect(html).toMatch(/facebookexternalhit/)
  })

  it('cannot be broken out of by hostile title or hash', () => {
    const evil = sharePageHtml({
      ...base,
      title: '</script><script>alert(1)</script>',
      description: '"><img src=x onerror=alert(1)>',
      linkName: "O'Brien <b>",
      hash: '#/x</script><script>alert(2)</script>',
    })
    expect(evil.match(/<script/g)?.length).toBe(1)
    expect(evil).not.toContain('</script><')
    expect(evil).not.toContain('<img')
    expect(evil).toContain('O&#39;Brien &lt;b&gt;')
    expect(evil).toContain('\\u003c/script>')
  })
})

describe('share page meta copy', () => {
  const row = { score: 87, label: 'Planning the parade', rank: 2, wins: 7, losses: 1, ties: 0 }

  it('teamShareMeta for BUF 2026 week 9', () => {
    const m = teamShareMeta(row, 'BUF', 2026, 9, realMeta)
    expect(m.title).toBe('Buffalo Bills: 87, Planning the parade')
    expect(m.description.startsWith('Week 9 · 2026. #2 of 32 at 7-1.')).toBe(true)
    expect(m.description).toBe(
      'Week 9 · 2026. #2 of 32 at 7-1. How Bills fans should feel right now, by the Feel-Good Score.',
    )
    expect(m.imageAlt).toBe('Buffalo Bills feel-good score: 87 out of 100, “Planning the parade”. Week 9, 2026.')
    expect(m.linkName).toBe('Buffalo Bills')
  })

  it('teamShareMeta renders a non-finite score as an en dash and ties in the record', () => {
    const m = teamShareMeta({ ...row, score: Number.NaN, ties: 1 }, 'BUF', 2026, 9, realMeta)
    expect(m.title).toBe('Buffalo Bills: –, Planning the parade')
    expect(m.description).toContain('at 7-1-1.')
  })

  it('teamShareMeta uses era names', () => {
    const m = teamShareMeta(row, 'LV', 2026, 9, { ...realMeta, seasons: [...realMeta.seasons] })
    expect(m.title.startsWith('Las Vegas Raiders:')).toBe(true)
    const old = teamShareMeta(row, 'LV', 2015, 3, realMeta)
    expect(old.title.startsWith('Oakland Raiders:')).toBe(true)
  })

  const joy = {
    type: 'joy' as const, season: 2026, week: 9, franchise: 'BUF',
    headline: 'Bills fans have been buying the jersey for 1,151 straight days',
    detail: 'Score 80 or higher since Sep 18, 2023, as of Nov 12, 2026.',
    evidence: null, stat: 1151, start: null, band: 6,
  }

  it('calloutShareMeta uses the headline alone when it starts with the nickname', () => {
    const m = calloutShareMeta(joy, realMeta)
    expect(m.title).toBe('Bills fans have been buying the jersey for 1,151 straight days')
    expect(m.description).toBe('Score 80 or higher since Sep 18, 2023, as of Nov 12, 2026. Week 9 · 2026, on the Feel-Good Score.')
    expect(m.imageAlt).toBe('Buffalo Bills: Bills fans have been buying the jersey for 1,151 straight days. Score 80 or higher since Sep 18, 2023, as of Nov 12, 2026.')
    expect(m.linkName).toBe('Buffalo Bills')
  })

  it('calloutShareMeta prefixes the era name otherwise', () => {
    const worried = { ...joy, type: 'worried' as const, franchise: 'CLE', headline: '5-4, but you should feel worried', detail: 'The Browns have the 16th-best record but the 25th-best score.' }
    const m = calloutShareMeta(worried, realMeta)
    expect(m.title).toBe('Cleveland Browns: 5-4, but you should feel worried')
  })
})

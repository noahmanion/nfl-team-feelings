import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import {
  SHARE_LAUNCH,
  calloutCopyUrl,
  calloutId,
  calloutImagePath,
  calloutShareHash,
  calloutSharePath,
  escapeHtml,
  hasSharePage,
  shareTargets,
  teamCopyUrl,
  teamImagePath,
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

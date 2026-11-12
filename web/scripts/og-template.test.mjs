import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { CARD, ARROW, KICKER, renderPng, clampText, cardRuns, teamCard, calloutCard, siteCard } from './og-template.mjs'

const webRoot = fileURLToPath(new URL('..', import.meta.url))

/** Slice only the first (light) `:root { … }` block of app.css (Pitfall 9). */
function lightRoot() {
  const css = readFileSync(webRoot + 'src/app.css', 'utf8')
  const start = css.indexOf(':root {')
  let depth = 0
  for (let i = css.indexOf('{', start); i < css.length; i++) {
    if (css[i] === '{') depth++
    else if (css[i] === '}' && --depth === 0) return css.slice(start, i + 1)
  }
  throw new Error('unterminated :root')
}
function token(block, name) {
  const m = block.match(new RegExp(`--${name}:\\s*([^;]+);`))
  if (!m) throw new Error(`token --${name} missing`)
  return m[1].trim().toLowerCase()
}
const hex = (c) => '#' + c.map((v) => v.toString(16).padStart(2, '0')).join('')
const rgb = (s) => [1, 3, 5].map((i) => parseInt(s.slice(i, i + 2), 16))
const tintOf = (s) => hex(rgb(s).map((c) => Math.round(255 + 0.16 * (c - 255))))

function assertPng(buf) {
  expect(buf.subarray(1, 4).toString('latin1')).toBe('PNG')
  expect(buf.readUInt32BE(16)).toBe(1200)
  expect(buf.readUInt32BE(20)).toBe(630)
  expect(buf.length).toBeLessThanOrEqual(300 * 1024)
}

describe('CARD tokens (D-07 drift guard)', () => {
  const root = lightRoot()
  it('mood[0..6] match light --mood-N', () => {
    for (let i = 0; i < 7; i++) expect(CARD.mood[i]).toBe(token(root, `mood-${i}`))
  })
  it('bg/text/muted/rule/border match light tokens', () => {
    expect(CARD.bg).toBe(token(root, 'bg'))
    expect(CARD.text).toBe(token(root, 'text'))
    expect(CARD.muted).toBe(token(root, 'text-muted'))
    expect(CARD.rule).toBe(token(root, 'rule-strong'))
    expect(CARD.border).toBe(token(root, 'border'))
  })
  it('tints are mood at 16% over white', () => {
    for (let i = 0; i < 7; i++) expect(CARD.tint[i]).toBe(tintOf(CARD.mood[i]))
    expect(CARD.tintNone).toBe(tintOf(CARD.border))
  })
})

describe('renderPng glyph guard (D-05)', () => {
  const h = (type, style, ...c) => ({ type, props: { style, children: c.length <= 1 ? c[0] : c } })
  it('rejects a raw arrow', async () => {
    await expect(renderPng(h('div', { display: 'flex' }, 'A → B'), 'test')).rejects.toThrow(/share: missing glyph U\+2192 .*\(test\)/)
  })
  it('rejects emoji', async () => {
    await expect(renderPng(h('div', { display: 'flex' }, 'Party 🎉'), 'emoji')).rejects.toThrow(/missing glyph/)
  })
  it('renders covered punctuation to a 1200x630 PNG', async () => {
    const png = await renderPng(h('div', { display: 'flex', fontSize: 40 }, 'It’s · 7–1 · −25 … #2'), 'ok')
    assertPng(png)
  })
})

describe('clampText', () => {
  it('leaves the 65-char Seahawks headline unchanged', () => {
    const s = 'Seahawks fans have been buying the jersey for 1,497 straight days'
    expect(clampText(s, 68)).toBe(s)
  })
  it('clamps long text at a word boundary with an ellipsis', () => {
    const s = 'The quick brown fox jumps over the lazy dog and keeps running until the end of the long road'
    expect(s.length).toBeGreaterThan(68)
    const out = clampText(s, 68)
    expect(out.length).toBeLessThanOrEqual(69)
    expect(out.endsWith('…')).toBe(true)
    const body = out.slice(0, -1)
    expect(s.startsWith(body)).toBe(true)
    expect(s[body.length]).toBe(' ')
  })
})

describe('cardRuns', () => {
  it('splits on the arrow and interleaves ARROW', () => {
    expect(cardRuns('It’s fine. Everything’s fine. → Cautiously smug')).toEqual(['It’s fine. Everything’s fine.', ARROW, 'Cautiously smug'])
  })
  it('returns a single run without an arrow', () => {
    expect(cardRuns('Still Cautiously smug')).toEqual(['Still Cautiously smug'])
  })
})

// ---- Task 2: card trees ----
const meta = JSON.parse(readFileSync(webRoot + 'public/data/meta.json', 'utf8'))
const snap = JSON.parse(readFileSync(webRoot + 'public/data/snapshots/2026.json', 'utf8'))
const bands = meta.bands
const host = 'nfl-team-feelings.vercel.app'
const BUF = 'data:image/png;base64,' + readFileSync(webRoot + 'public/logos/BUF.png').toString('base64')
const base = { name: 'Buffalo Bills', score: 87, rank: 2, nTeams: 32, record: '7-1', dateStamp: 'Week 9 · 2026', logo: BUF, primary: '#00338D', secondary: '#C60C30', host, bands }

function texts(node, out = []) {
  if (node == null || node === false) return out
  if (typeof node === 'string' || typeof node === 'number') out.push(String(node))
  else if (Array.isArray(node)) node.forEach((n) => texts(n, out))
  else if (node.props) texts(node.props.children, out)
  return out
}

describe('teamCard', () => {
  it('has the 7 expected band labels in meta', () => {
    expect(bands.map((b) => b.label)).toContain('It’s fine. Everything’s fine.')
    expect(bands).toHaveLength(7)
  })
  bands.forEach((b, i) => {
    it(`renders band ${i} "${b.label}"`, async () => {
      assertPng(await renderPng(teamCard({ ...base, label: b.label, band: i }), `band ${i}`))
    })
  })
  it('renders a 2-line name with a logo', async () => {
    assertPng(await renderPng(teamCard({ ...base, name: 'Washington Commanders', label: bands[3].label, band: 3 }), 'WAS'))
  })
  it('renders the chip when logo is null', async () => {
    const tree = teamCard({ ...base, logo: null, label: bands[5].label, band: 5 })
    expect(JSON.stringify(tree)).toContain('linear-gradient(135deg, #00338D 0%')
    assertPng(await renderPng(tree, 'chip'))
  })
  it('renders a solid fallback chip for an invalid color', async () => {
    const tree = teamCard({ ...base, logo: null, primary: 'red', label: bands[5].label, band: 5 })
    expect(JSON.stringify(tree)).not.toContain('linear-gradient')
    expect(JSON.stringify(tree)).toContain(CARD.chipFallback)
    assertPng(await renderPng(tree, 'chip-fallback'))
  })
  it('uses the border stripe for an unknown band', async () => {
    const tree = teamCard({ ...base, label: 'Mystery', band: -1 })
    expect(tree.props.children[0].props.style.backgroundColor).toBe(CARD.border)
    assertPng(await renderPng(tree, 'unknown band'))
  })
  it('shows an en dash for a non-finite score', () => {
    const tree = teamCard({ ...base, score: NaN, label: bands[3].label, band: 3 })
    expect(texts(tree)).toContain('–')
    expect(texts(tree)).not.toContain('NaN')
  })
})

describe('calloutCard', () => {
  const c = { name: 'Cleveland Browns', headline: '5-4, but you should feel worried', detail: 'The Browns have the 16th-best record but the 25th-best score.', band: 1, bands, dateStamp: 'Week 9 · 2026', logo: BUF, primary: '#311D00', secondary: '#FF3C00', host }
  for (const type of Object.keys(KICKER)) {
    it(`renders type ${type}`, async () => {
      const tree = calloutCard({ ...c, type })
      expect(texts(tree)).toContain(KICKER[type])
      assertPng(await renderPng(tree, type))
    })
  }
  it('renders an unknown type with no kicker', async () => {
    const tree = calloutCard({ ...c, type: 'weird' })
    for (const k of Object.values(KICKER)) expect(texts(tree)).not.toContain(k)
    assertPng(await renderPng(tree, 'unknown type'))
  })
  it('renders the longest real mover detail with a drawn arrow', async () => {
    let detail = ''
    for (const w in snap.callouts) for (const x of snap.callouts[w]) if (x.detail.includes('→') && x.detail.length > detail.length) detail = x.detail
    expect(detail).toContain('→')
    const tree = calloutCard({ ...c, type: 'mover_up', headline: 'Browns +16', detail, logo: null })
    expect(JSON.stringify(tree)).not.toContain('→')
    assertPng(await renderPng(tree, 'mover'))
  })
  it('renders the 65-char Seahawks headline unclamped', async () => {
    const headline = 'Seahawks fans have been buying the jersey for 1,497 straight days'
    expect(clampText(headline, 68)).toBe(headline)
    const tree = calloutCard({ ...c, type: 'joy', name: 'Seattle Seahawks', headline, band: 5 })
    expect(texts(tree)).toContain(headline)
    assertPng(await renderPng(tree, 'seahawks'))
  })
})

describe('siteCard', () => {
  it('renders 1200x630', async () => {
    assertPng(await renderPng(siteCard({ host }), 'site'))
  })
})

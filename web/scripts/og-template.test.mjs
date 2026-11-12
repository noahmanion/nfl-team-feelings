import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { CARD, ARROW, renderPng, clampText, cardRuns } from './og-template.mjs'

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

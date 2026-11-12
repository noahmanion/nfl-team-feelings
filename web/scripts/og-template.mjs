// Share-card templates and renderer (Phase 14, SHARE-01). Plain ESM, no JSX.
// satori turns an element tree into SVG; resvg-js rasterizes it to a 1200x630 PNG.
import satori from 'satori'
import { Resvg } from '@resvg/resvg-js'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { setImmediate as tick } from 'node:timers/promises'
import { bandIndex, moodToken } from '../src/lib/format.ts'

/** Card tokens (14-UI-SPEC "Card token object"). A test pins these to app.css's light :root. */
export const CARD = {
  w: 1200, h: 630,
  pad: 64,
  stripe: 12,
  bg: '#ffffff',
  text: '#222222',
  muted: '#6b6b6b',
  rule: '#222222',
  border: '#e3e3e3',
  mood: ['#7f1d1d', '#c2410c', '#b7791f', '#8a8d93', '#2f9e8f', '#15803d', '#0b5d3b'],
  tint: ['#ebdbdb', '#f5e1d8', '#f3eadb', '#ecedee', '#deefed', '#daebe0', '#d8e5e0'],
  tintNone: '#fbfbfb',
  chipFallback: '#6b6b6b',
  chipOutline: 'rgba(0,0,0,0.18)',
}

// Static WOFF files only (satori reads WOFF/TTF/OTF; D-03 amended: 400/700 in both families).
const require = createRequire(import.meta.url)
const font = (spec, name, weight) => ({ name, weight, style: 'normal', data: readFileSync(require.resolve(spec)) })
export const FONTS = [
  font('@fontsource/inter/files/inter-latin-400-normal.woff', 'Inter', 400),
  font('@fontsource/inter/files/inter-latin-700-normal.woff', 'Inter', 700),
  font('@fontsource/ibm-plex-mono/files/ibm-plex-mono-latin-400-normal.woff', 'IBM Plex Mono', 400),
  font('@fontsource/ibm-plex-mono/files/ibm-plex-mono-latin-700-normal.woff', 'IBM Plex Mono', 700),
]

/** Element tree helper. Callers set display:'flex' on any element with more than one child. */
export const h = (type, style, ...children) => ({ type, props: { style, children: children.length <= 1 ? children[0] : children } })

/** Drawn arrow, standing in for U+2192, which neither font covers. */
export const ARROW = {
  type: 'svg',
  props: {
    width: 36, height: 36, viewBox: '0 0 24 24',
    children: {
      type: 'path',
      props: { d: 'M4 12h14M13 6l6 6-6 6', stroke: '#6b6b6b', strokeWidth: 2.5, fill: 'none', strokeLinecap: 'round', strokeLinejoin: 'round' },
    },
  },
}

/** Split text on '→' into trimmed runs with ARROW between them. */
export function cardRuns(text) {
  const runs = String(text).split('→').map((s) => s.trim())
  const out = []
  runs.forEach((r, i) => {
    if (i > 0) out.push(ARROW)
    if (r) out.push(r)
  })
  // Drop a leading/trailing arrow left by an empty run at either end.
  while (out[0] === ARROW) out.shift()
  while (out.at(-1) === ARROW) out.pop()
  return out
}

/** Cut at the last word boundary at or before `max`, then append '…'. Unchanged when it fits. */
export function clampText(s, max) {
  s = String(s ?? '')
  if (s.length <= max) return s
  let cut = s.lastIndexOf(' ', max)
  if (cut <= 0) cut = max
  const body = s.slice(0, cut).replace(/[\s.,;:!?·–—-]+$/u, '')
  return body + '…'
}

/** Band → stripe and tint colors, with the site's --border fallback for unknown bands. */
export function bandColors(band, bands) {
  const idx = bandIndex(band, bands)
  if (idx < 0) return { stripe: CARD.border, tint: CARD.tintNone }
  const n = moodToken(idx, bands.length)
  return { stripe: CARD.mood[n], tint: CARD.tint[n] }
}

const cp = (seg) => [...new Set([...seg].map((c) => 'U+' + c.codePointAt(0).toString(16).toUpperCase().padStart(4, '0')))].join(',')

let renders = 0
export const renderStats = () => ({ count: renders })

/** Render a tree to PNG. Rejects with 'share: missing glyph …' instead of drawing tofu. */
export async function renderPng(tree, where) {
  const svg = await satori(tree, {
    width: CARD.w,
    height: CARD.h,
    fonts: FONTS,
    loadAdditionalAsset: async (_code, segment) => {
      throw new Error(`share: missing glyph ${cp(segment)} in "${segment}" (${where})`)
    },
  })
  const png = new Resvg(svg, { fitTo: { mode: 'original' }, font: { loadSystemFonts: false } }).render().asPng()
  renders++
  // Pitfall 1: resvg pixmaps live in native memory; collect and yield periodically.
  if (renders % 25 === 0) {
    globalThis.gc?.()
    await tick()
  }
  return png
}

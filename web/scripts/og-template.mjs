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

// ---- Card trees (14-UI-SPEC geometry) ----

const HEX = /^#[0-9A-Fa-f]{6}$/
const MONO = 'IBM Plex Mono'
const meta24 = { fontFamily: MONO, fontWeight: 400, fontSize: 24, lineHeight: '32px', textTransform: 'uppercase', letterSpacing: 0.96, color: CARD.muted }

/** Callout type → kicker text. Unknown types get no kicker. */
export const KICKER = { worried: 'Worried', hopeful: 'Hopeful', misery: 'Misery', joy: 'Joy', mover_up: 'Rising', mover_down: 'Falling' }

function frame(stripe, ...body) {
  return h(
    'div',
    { width: CARD.w, height: CARD.h, display: 'flex', flexDirection: 'column', backgroundColor: CARD.bg, fontFamily: 'Inter', color: CARD.text },
    stripe,
    h('div', { display: 'flex', flexDirection: 'column', justifyContent: 'space-between', flexGrow: 1, padding: `${CARD.pad - CARD.stripe}px ${CARD.pad}px ${CARD.pad}px` }, ...body),
  )
}

const solidStripe = (color) => h('div', { display: 'flex', width: CARD.w, height: CARD.stripe, flex: 'none', backgroundColor: color })

function footer(host) {
  return h(
    'div',
    { display: 'flex', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderTop: `2px solid ${CARD.rule}`, paddingTop: 16 },
    h('div', { fontFamily: 'Inter', fontWeight: 700, fontSize: 24, lineHeight: '32px', color: CARD.text }, 'Feel-Good Score'),
    h('div', { fontFamily: MONO, fontWeight: 400, fontSize: 24, lineHeight: '32px', color: CARD.muted }, String(host ?? '')),
  )
}

/** Logo image, or the TeamChip-style gradient chip (D-04). The chip has no letters. */
export function logoBox(logo, size, primary, secondary, radius) {
  if (logo) return { type: 'img', props: { src: logo, width: size, height: size, style: { width: size, height: size, flex: 'none', objectFit: 'contain' } } }
  const ok = HEX.test(primary ?? '') && HEX.test(secondary ?? '')
  const fill = ok
    ? { backgroundImage: `linear-gradient(135deg, ${primary} 0%, ${primary} 50%, ${secondary} 50%, ${secondary} 100%)` }
    : { backgroundColor: CARD.chipFallback }
  return h('div', { display: 'flex', boxSizing: 'border-box', width: size, height: size, flex: 'none', borderRadius: radius, border: `2px solid ${CARD.chipOutline}`, ...fill })
}

const body = (...rows) => h('div', { display: 'flex', flexDirection: 'column' }, ...rows)
const gap = (n) => h('div', { display: 'flex', height: n, flex: 'none' })

/** Team card (D-08): score + mood label claim, rank + record support. */
export function teamCard(vm) {
  const { stripe, tint } = bandColors(vm.band, vm.bands ?? [])
  const name = String(vm.name ?? '')
  const big = name.length <= 28
  const score = Number.isFinite(vm.score) ? String(Math.round(vm.score)) : '–'
  const identity = h(
    'div',
    { display: 'flex', flexDirection: 'row', alignItems: 'center', gap: 32, width: 688, height: 192 },
    logoBox(vm.logo, 144, vm.primary, vm.secondary, 12),
    h(
      'div',
      { display: 'flex', flexDirection: 'column', gap: 4, width: 512 },
      h('div', { fontWeight: 700, fontSize: big ? 56 : 36, lineHeight: big ? '62px' : '44px', color: CARD.text }, name),
      h('div', { fontFamily: MONO, fontWeight: 400, fontSize: 36, lineHeight: '44px', color: CARD.muted }, `#${vm.rank} of ${vm.nTeams} · ${vm.record}`),
    ),
  )
  const scoreCol = h(
    'div',
    { display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 8, width: 352 },
    h(
      'div',
      { display: 'flex', boxSizing: 'border-box', alignItems: 'center', justifyContent: 'flex-end', width: 352, height: 192, backgroundColor: tint, borderLeft: `${CARD.stripe}px solid ${stripe}`, paddingRight: 24 },
      h('div', { fontFamily: MONO, fontWeight: 700, fontSize: 160, lineHeight: '160px', color: CARD.text }, score),
    ),
    h('div', { ...meta24 }, 'out of 100'),
  )
  return frame(
    solidStripe(stripe),
    body(
      h('div', { ...meta24 }, String(vm.dateStamp ?? '')),
      gap(32),
      h('div', { display: 'flex', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' }, identity, scoreCol),
      gap(32),
      h(
        'div',
        { display: 'flex', boxSizing: 'border-box', alignItems: 'center', width: 1072, height: 88, backgroundColor: tint, borderLeft: `${CARD.stripe}px solid ${stripe}`, paddingLeft: 24 },
        h('div', { fontWeight: 700, fontSize: 36, lineHeight: '44px', color: CARD.text }, String(vm.label ?? '')),
      ),
    ),
    footer(vm.host),
  )
}

/** Callout card (D-09/D-10): kicker, who, clamped headline claim, detail support. */
export function calloutCard(vm) {
  const { stripe } = bandColors(vm.band, vm.bands ?? [])
  const kicker = KICKER[vm.type]
  const detailText = String(vm.detail ?? '')
  const detailStyle = { fontWeight: 400, fontSize: 36, lineHeight: '44px', color: CARD.muted }
  const detail = detailText.includes('→')
    ? h('div', { ...detailStyle, display: 'flex', flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', columnGap: 16 }, ...cardRuns(detailText).map((r) => (typeof r === 'string' ? h('div', {}, r) : r)))
    : h('div', { ...detailStyle, display: 'block', lineClamp: 2 }, clampText(detailText, 110))
  return frame(
    solidStripe(stripe),
    body(
      h(
        'div',
        { display: 'flex', flexDirection: 'row', justifyContent: kicker ? 'space-between' : 'flex-end', height: 32 },
        ...(kicker ? [h('div', { fontWeight: 700, fontSize: 24, lineHeight: '32px', textTransform: 'uppercase', letterSpacing: 0.96, color: CARD.text }, kicker)] : []),
        h('div', { ...meta24 }, String(vm.dateStamp ?? '')),
      ),
      gap(32),
      h(
        'div',
        { display: 'flex', flexDirection: 'row', alignItems: 'center', gap: 24, height: 80 },
        logoBox(vm.logo, 80, vm.primary, vm.secondary, 8),
        h('div', { fontWeight: 700, fontSize: 36, lineHeight: '44px', color: CARD.text }, String(vm.name ?? '')),
      ),
      gap(32),
      h(
        'div',
        { display: 'flex', boxSizing: 'border-box', flexDirection: 'column', gap: 16, width: 1072, borderLeft: `${CARD.stripe}px solid ${stripe}`, paddingLeft: 24 },
        h('div', { display: 'block', lineClamp: 2, fontWeight: 700, fontSize: 56, lineHeight: '62px', color: CARD.text }, clampText(vm.headline, 68)),
        detail,
      ),
    ),
    footer(vm.host),
  )
}

const scale = (height) => h('div', { display: 'flex', flexDirection: 'row', width: '100%', height, flex: 'none' }, ...CARD.mood.map((c) => h('div', { display: 'flex', flexGrow: 1, height, backgroundColor: c })))

/** Site-default card (D-06): no logo, no date. */
export function siteCard({ host }) {
  return frame(
    scale(CARD.stripe),
    body(
      h('div', { ...meta24 }, 'Every NFL team · Every week'),
      gap(32),
      h('div', { display: 'block', lineClamp: 2, width: 1072, fontWeight: 700, fontSize: 56, lineHeight: '62px', color: CARD.text }, 'How should you feel about your NFL team?'),
      gap(16),
      h('div', { display: 'block', lineClamp: 2, width: 1072, fontWeight: 400, fontSize: 36, lineHeight: '44px', color: CARD.muted }, 'A momentum-weighted, backtested score from 0 to 100, with a mood label on top.'),
      gap(32),
      h('div', { display: 'flex', width: 1072 }, scale(24)),
      gap(8),
      h(
        'div',
        { display: 'flex', flexDirection: 'row', justifyContent: 'space-between', width: 1072 },
        h('div', { fontFamily: MONO, fontWeight: 400, fontSize: 24, lineHeight: '32px', color: CARD.muted }, '0'),
        h('div', { fontFamily: MONO, fontWeight: 400, fontSize: 24, lineHeight: '32px', color: CARD.muted }, '100'),
      ),
    ),
    footer(host),
  )
}

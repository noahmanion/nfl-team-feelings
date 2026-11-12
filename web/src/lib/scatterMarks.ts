// Shared Plot marks and click handling for the Explore scatters (EXPL-02, EXPL-03). DOM/Plot-bound,
// so it is not a pure lib: the numbers and copy come from lib/explore.ts. Logos only come from the
// local `src` that logoSrc built; nothing here ever points at an external URL.

import * as Plot from '@observablehq/plot'
import { tapAction } from './explore'
import { CHART_FONT_PX, teamStroke } from './plotTheme'

export interface LogoOpts {
  x: string
  y: string
  size: number
  opacity: number
  dark: boolean
  /** Pinned team: ring drawn under the mark in this color. */
  ringColor?: string
  colorOf: (franchise: string) => string
  /** Pinned styling for the logos-off fallback (bigger dot, bold abbreviation). */
  pinnedText?: boolean
}

type LogoDatum = { franchise: string; abbr: string; src: string | null }

/** Ring (pinned only), then per team a dark-mode disc + logo image, or a colored dot + abbreviation when no logo. */
export function logoMarks<T extends LogoDatum>(data: T[], opts: LogoOpts): Plot.Markish[] {
  const { x, y, size, opacity, dark, ringColor, colorOf, pinnedText = false } = opts
  const marks: Plot.Markish[] = []
  if (data.length === 0) return marks
  const withLogo = data.filter((d) => d.src)
  const noLogo = data.filter((d) => !d.src)
  if (ringColor) {
    marks.push(Plot.dot(data, { x, y, r: size / 2 + 3, stroke: ringColor, strokeWidth: 2, fill: 'none' }))
  }
  if (withLogo.length > 0) {
    if (dark) {
      marks.push(Plot.dot(withLogo, { x, y, r: size / 2 + 2, fill: 'var(--logo-disc)', stroke: 'none', opacity }))
    }
    marks.push(Plot.image(withLogo, { x, y, src: (d: T) => d.src, width: dark ? size * 0.76 : size, opacity }))
  }
  if (noLogo.length > 0) {
    marks.push(
      Plot.dot(noLogo, {
        x,
        y,
        r: pinnedText ? 8 : 6,
        fill: (d: T) => teamStroke(colorOf(d.franchise)),
        stroke: 'var(--bg)',
        strokeWidth: 1,
        opacity,
      }),
      Plot.text(noLogo, {
        x,
        y,
        text: 'abbr',
        dx: 8,
        textAnchor: 'start',
        fontSize: CHART_FONT_PX,
        fill: 'var(--text)',
        fontWeight: pinnedText ? 600 : 400,
        opacity,
      }),
    )
  }
  return marks
}

/**
 * Click-through on a Plot svg: mouse clicks navigate at once; touch arms on the first tap (the tip
 * shows) and navigates on a second tap of the same team (tapAction). Plot's `value` is the pointed datum.
 */
export function attachClick<T extends { franchise: string }>(
  plot: SVGSVGElement | HTMLElement,
  href: (d: T) => string,
  navigate: (h: string) => void,
): void {
  const val = () => (plot as unknown as { value: T | null | undefined }).value ?? null
  let pointerType = 'mouse'
  let armed: string | null = null
  plot.addEventListener('pointerdown', (e) => {
    pointerType = (e as PointerEvent).pointerType || 'mouse'
  })
  plot.addEventListener('input', () => {
    plot.style.cursor = val() ? 'pointer' : ''
  })
  plot.addEventListener('click', () => {
    // Plot updates `value` in a requestAnimationFrame after the pointer event; on a touch tap
    // (no prior hover) it is still null at click time, so read it one frame later.
    requestAnimationFrame(() => {
      const v = val()
      const r = tapAction(pointerType, armed, v?.franchise ?? null)
      armed = r.armed
      if (r.go && v) navigate(href(v))
    })
  })
}

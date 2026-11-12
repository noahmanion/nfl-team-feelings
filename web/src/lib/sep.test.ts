import { compile } from 'svelte/compiler'
import { describe, expect, it } from 'vitest'

// WR-01 regression guard: the "·" separator on header/meta lines collapsed twice ("0%·QB") because
// spacing depended on a per-component `.sep` rule reaching a conditionally rendered span. Now the
// only separator is <Sep />, which owns its spacing.
const sources = import.meta.glob('../components/*.svelte', { query: '?raw', import: 'default', eager: true }) as Record<
  string,
  string
>
const sepSource = sources['../components/Sep.svelte']

describe('Sep separator', () => {
  it('owns its horizontal spacing in its own scoped style', () => {
    expect(sepSource).toBeDefined()
    const out = compile(sepSource, { filename: 'Sep.svelte', generate: 'server' })
    expect(out.css?.code).toMatch(/\.sep\.svelte-[a-z0-9]+\s*\{[^}]*margin-inline:\s*var\(--space-xs\)/)
    expect(out.js.code).toContain('aria-hidden')
    expect(out.js.code).toContain('·')
  })

  it('is the only place a dot separator element is hand-rolled', () => {
    const offenders = Object.entries(sources)
      .filter(([path]) => !path.endsWith('/Sep.svelte'))
      .filter(([, src]) => /class="sep"|<span[^>]*>\s*·\s*<\/span>/.test(src))
      .map(([path]) => path)
    expect(offenders).toEqual([])
  })

  it('travels with the following link in the site nav, so wrapped lines never end in a dangling dot', () => {
    const header = sources['../components/SiteHeader.svelte']
    const nav = /<nav[\s\S]*?<\/nav>/.exec(header)?.[0] ?? ''
    // every separator sits right before a link, inside a no-wrap item
    expect(nav.match(/<Sep \/>/g)?.length).toBe(4)
    expect(nav.match(/<span class="item"\s*><Sep \/><a /g)?.length).toBe(4)
    expect(nav).not.toMatch(/<\/a>\s*<Sep \/>/)
    expect(header).toMatch(/\.item\s*\{[^}]*white-space:\s*nowrap/)
  })

  it('is used on every team page header meta line and the past-week nav', () => {
    const team = sources['../components/TeamPage.svelte']
    // three header separators (when · Now, record · rank, odds · QB) + two in the week nav
    // (Prev week · Next week · See the board)
    expect(team.match(/<Sep \/>/g)?.length).toBe(5)
    const nav = /<nav class="week-nav"[\s\S]*?<\/nav>/.exec(team)?.[0] ?? ''
    expect(nav.match(/<Sep \/>/g)?.length).toBe(2)
    expect(nav).toContain('boardHash(season, week)')
  })
})

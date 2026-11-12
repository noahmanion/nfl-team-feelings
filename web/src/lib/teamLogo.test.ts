import { render } from 'svelte/server'
import { afterEach, describe, expect, it, vi } from 'vitest'
import TeamChip from '../components/TeamChip.svelte'
import TeamLogo from '../components/TeamLogo.svelte'

// SSR checks of the TeamLogo contract (D-11, D-13, D-14). The live onerror fallback is covered by
// Playwright in plan 07.
describe('TeamLogo', () => {
  afterEach(() => vi.unstubAllEnvs())

  it('renders the small local logo for a known franchise', () => {
    const { body } = render(TeamLogo, {
      props: { franchise: 'KC', primary: '#E31837', secondary: '#FFB81C', size: 24 },
    })
    expect(body).toContain('src="/logos/sm/KC.png"')
    expect(body).toContain('width="24"')
    expect(body).toContain('loading="lazy"')
    expect(body).toContain('decoding="async"')
    expect(body).not.toContain('class="chip')
  })

  it('falls back to the chip for an unknown franchise', () => {
    const { body } = render(TeamLogo, { props: { franchise: 'XXX', primary: '#000000', secondary: '#ffffff' } })
    expect(body).toContain('chip')
    expect(body).not.toContain('<img')
  })

  it('renders the chip when VITE_LOGOS=off', () => {
    vi.stubEnv('VITE_LOGOS', 'off')
    const { body } = render(TeamLogo, { props: { franchise: 'KC', primary: '#E31837', secondary: '#FFB81C' } })
    expect(body).toContain('chip')
    expect(body).not.toContain('<img')
  })

  it('is decorative by default', () => {
    const { body } = render(TeamLogo, { props: { franchise: 'KC' } })
    expect(body).toContain('alt=""')
    expect(body).toContain('aria-hidden="true"')
  })
})

describe('TeamChip sizes', () => {
  it('sets --chip-size from the size prop', () => {
    expect(render(TeamChip, { props: { size: 48 } }).body).toContain('--chip-size: 48px')
    expect(render(TeamChip, { props: { size: 24 } }).body).toContain('--chip-size: 24px')
  })
})

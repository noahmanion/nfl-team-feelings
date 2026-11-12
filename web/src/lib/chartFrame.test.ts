import { createRawSnippet } from 'svelte'
import { render } from 'svelte/server'
import { describe, expect, it } from 'vitest'
import ChartFrame from '../components/ChartFrame.svelte'

// SSR checks of the ChartFrame contract (D-08, 12-UI-SPEC "Component Contract: ChartFrame.svelte").
const children = createRawSnippet(() => ({ render: () => '<div class="probe"></div>' }))

describe('ChartFrame', () => {
  it('renders headline, dek, body, source and notes, labelled by the heading', () => {
    const { body } = render(ChartFrame, {
      props: { id: 'cf1', headline: 'H', dek: 'D', notes: 'N.', level: 3, children },
    })
    expect(body).toContain('<figure')
    expect(body).toContain('aria-labelledby="cf1"')
    expect(body).toContain('<h3')
    expect(body).toContain('id="cf1"')
    expect(body).toContain('>H<')
    expect(body).toContain('>D<')
    expect(body).toContain('SOURCE: NFLVERSE · FEEL-GOOD SCORE')
    expect(body).toContain('NOTES: N.')
    expect(body).toContain('<div class="probe"></div>')
  })

  it('omits the dek and notes when not given but keeps the source line', () => {
    const { body } = render(ChartFrame, { props: { id: 'cf2', headline: 'H', children } })
    expect(body).not.toContain('cf-dek')
    expect(body).not.toContain('NOTES:')
    expect(body).toContain('SOURCE: NFLVERSE · FEEL-GOOD SCORE')
    expect(body).toContain('<h3')
  })

  it('renders an h2 at level 2', () => {
    const { body } = render(ChartFrame, { props: { id: 'cf3', headline: 'H', level: 2, children } })
    expect(body).toContain('<h2')
    expect(body).not.toContain('<h3')
  })

  it('renders the default source line when no source is given', () => {
    const { body } = render(ChartFrame, { props: { id: 'cf4', headline: 'H', children } })
    expect(body).toContain('SOURCE: NFLVERSE · FEEL-GOOD SCORE')
  })

  it('renders a custom source line instead of the default', () => {
    const source = 'SOURCE: NFLVERSE (2003–2020) · COVERS / DRAFTKINGS (2021+)'
    const { body } = render(ChartFrame, { props: { id: 'cf5', headline: 'H', source, children } })
    expect(body).toContain(source)
    expect(body).not.toContain('SOURCE: NFLVERSE · FEEL-GOOD SCORE')
  })

  it('hides the footer when footer is false (loading state)', () => {
    const { body } = render(ChartFrame, { props: { id: 'cf6', headline: 'H', notes: 'N.', footer: false, children } })
    expect(body).not.toContain('cf-foot')
    expect(body).not.toContain('SOURCE:')
    expect(body).toContain('<div class="probe"></div>')
  })
})

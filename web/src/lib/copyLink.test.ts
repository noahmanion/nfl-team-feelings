import { describe, expect, it } from 'vitest'
import { copyText, deepLink, type CopyDoc } from './copyLink'

function fakeDoc(execResult: boolean | 'throw', opts: { selects?: boolean; focuses?: boolean } = {}) {
  const { selects = true, focuses = true } = opts
  const state = {
    appended: 0, removed: 0, value: '', readonly: false, cmd: '', focused: false, range: [-1, -1],
    buttonRefocused: 0, active: null as unknown,
  }
  const button = { focus: () => void (state.buttonRefocused++, (state.active = button)) }
  state.active = button
  const ta = {
    set value(v: string) {
      state.value = v
    },
    setAttribute: (k: string) => {
      if (k === 'readonly') state.readonly = true
    },
    style: {},
    focus: () => {
      if (focuses) {
        state.focused = true
        state.active = ta
      }
    },
    select: () => {},
    setSelectionRange: (a: number, b: number) => {
      if (selects) state.range = [a, b]
    },
    get selectionStart() {
      return state.range[0]
    },
    get selectionEnd() {
      return state.range[1]
    },
    remove: () => void state.removed++,
  }
  const doc: CopyDoc = {
    body: { appendChild: () => void state.appended++ },
    createElement: () => ta as unknown as HTMLTextAreaElement,
    get activeElement() {
      return state.active as Element
    },
    execCommand: (cmd: string) => {
      state.cmd = cmd
      if (execResult === 'throw') throw new Error('nope')
      return execResult
    },
  }
  return { doc, state }
}

describe('copyText', () => {
  it('uses the Clipboard API in a secure context', async () => {
    let got = ''
    const clipboard = { writeText: async (t: string) => void (got = t) }
    expect(await copyText('x', { isSecureContext: true, clipboard })).toBe('copied')
    expect(got).toBe('x')
  })

  it('falls back to execCommand when writeText rejects, and cleans up the textarea', async () => {
    const { doc, state } = fakeDoc(true)
    const clipboard = { writeText: () => Promise.reject(new Error('NotAllowedError')) }
    expect(await copyText('link', { isSecureContext: true, clipboard, doc })).toBe('copied')
    expect(state).toMatchObject({ appended: 1, removed: 1, value: 'link', readonly: true, cmd: 'copy' })
    expect(state.focused).toBe(true)
    expect(state.range).toEqual([0, 4])
  })

  it('restores focus to the previously focused element (the Copy button)', async () => {
    const { doc, state } = fakeDoc(true)
    expect(await copyText('link', { isSecureContext: false, doc })).toBe('copied')
    expect(state.buttonRefocused).toBe(1)
  })

  it('returns manual without claiming a copy when the text could not be selected', async () => {
    const { doc, state } = fakeDoc(true, { selects: false })
    expect(await copyText('link', { isSecureContext: false, doc })).toBe('manual')
    expect(state.cmd).toBe('')
    expect(state.removed).toBe(1)
  })

  it('returns manual when the textarea never takes focus', async () => {
    const { doc, state } = fakeDoc(true, { focuses: false })
    expect(await copyText('link', { isSecureContext: false, doc })).toBe('manual')
    expect(state.cmd).toBe('')
  })

  it('skips the Clipboard API outside a secure context', async () => {
    let called = false
    const clipboard = { writeText: async () => void (called = true) }
    const { doc } = fakeDoc(true)
    expect(await copyText('x', { isSecureContext: false, clipboard, doc })).toBe('copied')
    expect(called).toBe(false)
  })

  it('returns manual when execCommand returns false (textarea still removed)', async () => {
    const { doc, state } = fakeDoc(false)
    expect(await copyText('x', { isSecureContext: false, doc })).toBe('manual')
    expect(state.removed).toBe(1)
  })

  it('returns manual when execCommand throws', async () => {
    const { doc, state } = fakeDoc('throw')
    const clipboard = { writeText: () => Promise.reject(new Error('no')) }
    expect(await copyText('x', { isSecureContext: true, clipboard, doc })).toBe('manual')
    expect(state.removed).toBe(1)
  })

  it('returns manual when not secure and there is no document', async () => {
    expect(await copyText('x', { isSecureContext: false })).toBe('manual')
  })

  it('default env does not throw in node', async () => {
    expect(await copyText('x')).toBe('manual')
  })
})

describe('deepLink', () => {
  it('returns just the hash outside a browser', () => {
    expect(deepLink('#/team/CLE/2026/9')).toBe('#/team/CLE/2026/9')
  })
})

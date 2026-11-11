// Copy a link with a three-tier fallback (08-RESEARCH Pattern 6): Clipboard API (secure context only),
// then a temporary readonly textarea + execCommand('copy'), then 'manual' (caller shows the URL).

export interface CopyDoc {
  createElement(tag: 'textarea'): HTMLTextAreaElement
  execCommand(cmd: string): boolean
  body: { appendChild(n: Node): unknown } | null
  /** Focus owner before the copy; focus goes back to it afterwards (e.g. the Copy button). */
  readonly activeElement?: Element | null
}
export interface CopyEnv {
  isSecureContext: boolean
  clipboard?: { writeText(text: string): Promise<void> } | null
  doc?: CopyDoc | null
}

function defaultEnv(): CopyEnv {
  return {
    isSecureContext: typeof window !== 'undefined' && !!window.isSecureContext,
    clipboard: typeof navigator !== 'undefined' ? (navigator.clipboard ?? null) : null,
    doc: typeof document !== 'undefined' ? document : null,
  }
}

export async function copyText(text: string, env: CopyEnv = defaultEnv()): Promise<'copied' | 'manual'> {
  try {
    if (env.isSecureContext && env.clipboard?.writeText) {
      await env.clipboard.writeText(text)
      return 'copied'
    }
  } catch {
    // fall through to execCommand
  }
  // WR-04: execCommand only copies the *active* selection, and Chromium returns true whenever the
  // command is enabled, copied or not. So the textarea is focused, selected with setSelectionRange
  // (iOS Safari ignores select() on a readonly field), and the tier only counts as a success when
  // the textarea really holds focus and the whole text is selected. Focus is restored afterwards.
  const doc = env.doc
  const prev = (doc?.activeElement ?? null) as HTMLElement | null
  try {
    if (doc?.body) {
      const ta = doc.createElement('textarea')
      ta.value = text
      ta.setAttribute('readonly', '')
      ta.style.position = 'fixed'
      ta.style.top = '0'
      ta.style.left = '0'
      ta.style.opacity = '0'
      doc.body.appendChild(ta)
      let ok = false
      try {
        ta.focus()
        ta.select()
        ta.setSelectionRange(0, text.length)
        const selected = doc.activeElement === ta && ta.selectionStart === 0 && ta.selectionEnd === text.length
        ok = selected && doc.execCommand('copy')
      } finally {
        ta.remove()
        restoreFocus(prev)
      }
      if (ok) return 'copied'
    }
  } catch {
    // fall through to manual
  }
  return 'manual'
}

function restoreFocus(el: HTMLElement | null) {
  try {
    if (el && typeof el.focus === 'function') el.focus()
  } catch {
    // focus is best effort
  }
}

/** Absolute URL for a hash route; just the hash outside a browser. */
export function deepLink(hash: string): string {
  if (typeof location === 'undefined') return hash
  return `${location.origin}${location.pathname}${hash}`
}

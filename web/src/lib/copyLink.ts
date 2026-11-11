// Copy a link with a three-tier fallback (08-RESEARCH Pattern 6): Clipboard API (secure context only),
// then a temporary readonly textarea + execCommand('copy'), then 'manual' (caller shows the URL).

export interface CopyDoc {
  createElement(tag: 'textarea'): HTMLTextAreaElement
  execCommand(cmd: string): boolean
  body: { appendChild(n: Node): unknown } | null
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
  try {
    const doc = env.doc
    if (doc?.body) {
      const ta = doc.createElement('textarea')
      ta.value = text
      ta.setAttribute('readonly', '')
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      doc.body.appendChild(ta)
      let ok = false
      try {
        ta.select()
        ok = doc.execCommand('copy')
      } finally {
        ta.remove()
      }
      if (ok) return 'copied'
    }
  } catch {
    // fall through to manual
  }
  return 'manual'
}

/** Absolute URL for a hash route; just the hash outside a browser. */
export function deepLink(hash: string): string {
  if (typeof location === 'undefined') return hash
  return `${location.origin}${location.pathname}${hash}`
}

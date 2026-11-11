// Tiny hash router (D-11). Pure: no DOM access; validation against meta happens in App.

export type Route =
  | { kind: 'latest' }
  | { kind: 'board'; season: number; week: number }
  | { kind: 'reserved' } // later-phase routes: fall back to #/ silently
  | { kind: 'invalid' }

const BOARD = /^\/board\/(\d{4})\/(\d{1,2})\/?$/
const RESERVED = [/^\/team\/[A-Za-z]{2,3}(\/\d{4}\/\d{1,2})?\/?$/, /^\/(history|records|methodology)\/?$/]

export function parseHash(hash: string): Route {
  const h = hash.replace(/^#/, '')
  if (h === '' || h === '/') return { kind: 'latest' }
  const m = BOARD.exec(h)
  if (m) return { kind: 'board', season: Number(m[1]), week: Number(m[2]) }
  if (RESERVED.some((re) => re.test(h))) return { kind: 'reserved' }
  return { kind: 'invalid' }
}

export const boardHash = (season: number, week: number): string => `#/board/${season}/${week}`

// Tiny hash router (D-11). Pure: no DOM access; validation against meta happens in App.

export type Route =
  | { kind: 'latest' }
  | { kind: 'board'; season: number; week: number }
  | { kind: 'history'; team?: string }
  | { kind: 'reserved' } // later-phase routes: fall back to #/ silently
  | { kind: 'invalid' }

const BOARD = /^\/board\/(\d{4})\/(\d{1,2})\/?$/
const HISTORY = /^\/history(?:\/([A-Za-z]{2,3}))?\/?$/
const RESERVED = [/^\/team\/[A-Za-z]{2,3}(\/\d{4}\/\d{1,2})?\/?$/, /^\/(records|methodology)\/?$/]

export function parseHash(hash: string): Route {
  const h = hash.replace(/^#/, '')
  if (h === '' || h === '/') return { kind: 'latest' }
  const m = BOARD.exec(h)
  if (m) return { kind: 'board', season: Number(m[1]), week: Number(m[2]) }
  const hm = HISTORY.exec(h)
  if (hm) return hm[1] ? { kind: 'history', team: hm[1].toUpperCase() } : { kind: 'history' }
  if (RESERVED.some((re) => re.test(h))) return { kind: 'reserved' }
  return { kind: 'invalid' }
}

export const boardHash = (season: number, week: number): string => `#/board/${season}/${week}`

/** '#/history' or '#/history/ABBR'. The abbr is validated against meta.teams by the page. */
export const historyHash = (team?: string): string => (team ? `#/history/${team.toUpperCase()}` : '#/history')

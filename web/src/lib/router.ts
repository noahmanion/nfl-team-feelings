// Tiny hash router (D-11). Pure: no DOM access; validation against meta happens in App.

export type Route =
  | { kind: 'latest' }
  | { kind: 'board'; season: number; week: number }
  | { kind: 'history'; team?: string }
  | { kind: 'team'; team: string; season?: number; week?: number }
  | { kind: 'methodology' }
  | { kind: 'records' }
  | { kind: 'reserved' } // later-phase routes: fall back to #/ silently
  | { kind: 'invalid' }

const BOARD = /^\/board\/(\d{4})\/(\d{1,2})\/?$/
const HISTORY = /^\/history(?:\/([A-Za-z]{2,3}))?\/?$/
const TEAM = /^\/team\/([A-Za-z]{2,3})(?:\/(\d{4})(?:\/(\d{1,2}))?)?\/?$/
const METHODOLOGY = /^\/methodology\/?$/
const RECORDS = /^\/records\/?$/
// No routes are reserved right now; kept so a future placeholder route can fall back to #/.
const RESERVED: RegExp[] = []

export function parseHash(hash: string): Route {
  const h = hash.replace(/^#/, '')
  if (h === '' || h === '/') return { kind: 'latest' }
  const m = BOARD.exec(h)
  if (m) return { kind: 'board', season: Number(m[1]), week: Number(m[2]) }
  const hm = HISTORY.exec(h)
  if (hm) return hm[1] ? { kind: 'history', team: hm[1].toUpperCase() } : { kind: 'history' }
  const tm = TEAM.exec(h)
  if (tm) {
    const team = tm[1].toUpperCase()
    if (!tm[2]) return { kind: 'team', team }
    // '/team/ABBR/season' (no week) parses with season only; App sends it to the team's latest page
    return tm[3] ? { kind: 'team', team, season: Number(tm[2]), week: Number(tm[3]) } : { kind: 'team', team, season: Number(tm[2]) }
  }
  if (METHODOLOGY.test(h)) return { kind: 'methodology' }
  if (RECORDS.test(h)) return { kind: 'records' }
  if (RESERVED.some((re) => re.test(h))) return { kind: 'reserved' }
  return { kind: 'invalid' }
}

export const boardHash = (season: number, week: number): string => `#/board/${season}/${week}`

/** '#/history' or '#/history/ABBR'. The abbr is validated against meta.teams by the page. */
export const historyHash = (team?: string): string => (team ? `#/history/${team.toUpperCase()}` : '#/history')

/** '#/team/ABBR' (latest) or '#/team/ABBR/season/week'. Validated against meta by App. */
export const teamHash = (team: string, season?: number, week?: number): string =>
  season === undefined || week === undefined
    ? `#/team/${team.toUpperCase()}`
    : `#/team/${team.toUpperCase()}/${season}/${week}`

export const methodologyHash = '#/methodology'
export const recordsHash = '#/records'

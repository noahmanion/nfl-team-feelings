// Pinned "my team" (SITE-08). Pure and node-testable: storage is injected.

export const MY_TEAM_KEY = 'fgs.myTeam'

export interface StorageLike {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
  removeItem(key: string): void
}

/** Stored abbreviation, or null when absent / storage unavailable / storage throws. */
export function readMyTeam(storage: StorageLike | undefined): string | null {
  if (!storage) return null
  try {
    const v = storage.getItem(MY_TEAM_KEY)
    return typeof v === 'string' ? v : null
  } catch {
    return null
  }
}

/** Persist (string) or clear (null). Never throws; false when nothing was saved. */
export function writeMyTeam(storage: StorageLike | undefined, abbr: string | null): boolean {
  if (!storage) return false
  try {
    if (abbr === null) storage.removeItem(MY_TEAM_KEY)
    else storage.setItem(MY_TEAM_KEY, abbr)
    return true
  } catch {
    return false
  }
}

/** abbr when it is an own key of teams (exact match), else null. Use before classes, ids or hashes. */
export function validMyTeam(abbr: string | null | undefined, teams: Record<string, unknown> | null | undefined): string | null {
  if (typeof abbr !== 'string' || !abbr || !teams) return null
  return Object.prototype.hasOwnProperty.call(teams, abbr) ? abbr : null
}

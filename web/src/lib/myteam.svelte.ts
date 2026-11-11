import { MY_TEAM_KEY, readMyTeam, writeMyTeam, type StorageLike } from './myteam'

// Touching localStorage itself can throw (sandboxed iframes, disabled cookies).
function getStore(): StorageLike | undefined {
  try {
    return typeof localStorage === 'undefined' ? undefined : localStorage
  } catch {
    return undefined
  }
}

const store = getStore()

/** Raw pinned value. Always pass through validMyTeam(myTeam.abbr, meta.teams) before use. */
export const myTeam = $state<{ abbr: string | null }>({ abbr: readMyTeam(store) })

/** Update in memory first, so the pin still works for this session when storage fails. */
export function setMyTeam(abbr: string | null): void {
  myTeam.abbr = abbr
  writeMyTeam(store, abbr)
}

/** Pin abbr, or unpin when it is already the pinned team. */
export function toggleMyTeam(abbr: string): void {
  setMyTeam(myTeam.abbr === abbr ? null : abbr)
}

if (typeof window !== 'undefined') {
  window.addEventListener('storage', (e) => {
    if (e.key === MY_TEAM_KEY || e.key === null) myTeam.abbr = readMyTeam(store)
  })
}

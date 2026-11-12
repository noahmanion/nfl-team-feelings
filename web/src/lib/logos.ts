// Team logo helpers (D-11..D-13). Logos are served locally from public/logos/sm (96px derivatives
// built by scripts/logos-sm.sh); nothing is hotlinked.

import { logosOff } from './logoSwitch'

/** The 32 current franchise codes, matching meta.json team keys and the logo filenames. */
export const FRANCHISES = [
  'ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE', 'DAL', 'DEN', 'DET', 'GB', 'HOU', 'IND', 'JAX', 'KC',
  'LA', 'LAC', 'LV', 'MIA', 'MIN', 'NE', 'NO', 'NYG', 'NYJ', 'PHI', 'PIT', 'SEA', 'SF', 'TB', 'TEN', 'WAS',
] as const

const KNOWN: ReadonlySet<string> = new Set(FRANCHISES)

/**
 * Logo kill switch. VITE_LOGOS is read at build time, so a takedown is: set VITE_LOGOS=off and
 * rebuild. Only the value "off" (any case, trimmed) disables logos; every TeamLogo then renders its
 * chip, and the build (vite.config.ts dropLogos) deletes dist/logos so no logo file is deployed.
 */
export function logosEnabled(env: unknown = import.meta.env.VITE_LOGOS): boolean {
  return !logosOff(env)
}

/** Local small-logo URL for a known franchise code, or null for anything else. */
export function logoSrc(f: string | null | undefined): string | null {
  if (typeof f !== 'string' || !/^[A-Z]{2,3}$/.test(f) || !KNOWN.has(f)) return null
  return `${import.meta.env.BASE_URL}logos/sm/${f}.png`
}

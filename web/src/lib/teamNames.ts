import type { Meta } from './types'

// Era-correct team identity (D-16..D-19). Franchise codes are stable across relocations; display
// names and abbreviations follow the season being shown.

/** Display name for a franchise as it was known in `season`; falls back to the code if unknown. */
export function eraName(franchise: string, season: number, meta: Pick<Meta, 'teams'>): string {
  if (franchise === 'LV' && season <= 2019) return 'Oakland Raiders'
  if (franchise === 'LAC' && season <= 2016) return 'San Diego Chargers'
  if (franchise === 'LA' && season <= 2015) return 'St. Louis Rams'
  if (franchise === 'WAS' && season <= 2019) return 'Washington'
  if (franchise === 'WAS' && season <= 2021) return 'Washington Football Team'
  return meta.teams[franchise]?.name ?? franchise
}

/** Abbreviation for a franchise as it was known in `season` (OAK, SD, STL before relocation). */
export function eraAbbr(franchise: string, season: number): string {
  if (franchise === 'LV' && season <= 2019) return 'OAK'
  if (franchise === 'LAC' && season <= 2016) return 'SD'
  if (franchise === 'LA' && season <= 2015) return 'STL'
  return franchise
}

/** False only for HOU before its 2002 expansion season. */
export function isActiveFranchise(franchise: string, season: number): boolean {
  return !(franchise === 'HOU' && season < 2002)
}

/**
 * Rewrite pipeline-generated "Commanders" copy for Washington seasons up to 2021 (D-26).
 * Pipeline copy is frozen, so this is a display-only rewrite; other franchises and seasons pass
 * through unchanged.
 */
export function eraText(text: string, franchise: string, season: number): string {
  if (typeof text !== 'string') return ''
  if (franchise !== 'WAS' || season > 2021) return text
  if (season <= 2019) {
    return text.replace(/\b[Tt]he Commanders\b/g, 'Washington').replace(/\bCommanders\b/g, 'Washington')
  }
  return text.replace(/\b([Tt]he) Commanders\b/g, '$1 Football Team').replace(/\bCommanders\b/g, 'Football Team')
}

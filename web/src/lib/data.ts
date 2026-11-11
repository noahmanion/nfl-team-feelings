import type { HistoryFile, Meta, SeasonFile, SeasonMeta, WeekFile } from './types'

export const dataUrl = (path: string): string => `${import.meta.env.BASE_URL}data/${path}`

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(dataUrl(path), init)
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`)
  return (await res.json()) as T
}

export const loadMeta = (): Promise<Meta> => getJson<Meta>('meta.json', { cache: 'no-store' })
export const loadLatest = (): Promise<WeekFile> => getJson<WeekFile>('latest.json', { cache: 'no-store' })

// Session cache of season files. Rejected fetches are evicted so "Try again" refetches.
const seasonCache = new Map<number, Promise<SeasonFile>>()

export function loadSeason(meta: Meta, season: number): Promise<SeasonFile> {
  const cached = seasonCache.get(season)
  if (cached) return cached
  const p = getJson<SeasonFile>(`snapshots/${season}.json?v=${encodeURIComponent(meta.generated_at)}`)
  seasonCache.set(season, p)
  p.catch(() => {
    if (seasonCache.get(season) === p) seasonCache.delete(season)
  })
  return p
}

// history.json is one file; cache a single promise per meta.generated_at (a new export
// replaces it), evicted on failure.
let historyCache: { key: string; p: Promise<HistoryFile> } | null = null

export function loadHistory(meta: Meta): Promise<HistoryFile> {
  if (historyCache && historyCache.key === meta.generated_at) return historyCache.p
  const p = getJson<HistoryFile>(`history.json?v=${encodeURIComponent(meta.generated_at)}`)
  const entry = { key: meta.generated_at, p }
  historyCache = entry
  p.catch(() => {
    if (historyCache === entry) historyCache = null
  })
  return p
}

export const findSeason = (meta: Meta, season: number): SeasonMeta | undefined =>
  meta.seasons.find((s) => s.season === season)

export const isLatest = (meta: Meta, season: number, week: number): boolean =>
  meta.latest.season === season && meta.latest.week === week

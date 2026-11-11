import type { Meta, SeasonFile, SeasonMeta, WeekFile } from './types'

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

export const findSeason = (meta: Meta, season: number): SeasonMeta | undefined =>
  meta.seasons.find((s) => s.season === season)

export const isLatest = (meta: Meta, season: number, week: number): boolean =>
  meta.latest.season === season && meta.latest.week === week

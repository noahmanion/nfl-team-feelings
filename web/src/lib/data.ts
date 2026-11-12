import type { Callout, EpaFile, GamesFile, HistoryFile, Meta, Methodology, RecordsFile, SeasonFile, SeasonMeta, WeekFile } from './types'

export const dataUrl = (path: string): string => `${import.meta.env.BASE_URL}data/${path}`

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(dataUrl(path), init)
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`)
  return (await res.json()) as T
}

export const loadMeta = (): Promise<Meta> => getJson<Meta>('meta.json', { cache: 'no-store' })
export const loadLatest = (): Promise<WeekFile> => getJson<WeekFile>('latest.json', { cache: 'no-store' })
/** callouts.json: the latest week's callouts (same freshness rule as latest.json). */
export const loadCallouts = (): Promise<Callout[]> => getJson<Callout[]>('callouts.json', { cache: 'no-store' })

// Session cache of season files, keyed by meta.generated_at + season (a new export must not be
// served a stale season). Rejected fetches are evicted so "Try again" refetches.
const seasonCache = new Map<string, Promise<SeasonFile>>()

export function loadSeason(meta: Meta, season: number): Promise<SeasonFile> {
  const key = `${meta.generated_at}|${season}`
  const cached = seasonCache.get(key)
  if (cached) return cached
  const p = getJson<SeasonFile>(`snapshots/${season}.json?v=${encodeURIComponent(meta.generated_at)}`)
  seasonCache.set(key, p)
  p.catch(() => {
    if (seasonCache.get(key) === p) seasonCache.delete(key)
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

// methodology.json: one file, cached per meta.generated_at, evicted on failure.
let methodologyCache: { key: string; p: Promise<Methodology> } | null = null

export function loadMethodology(meta: Meta): Promise<Methodology> {
  if (methodologyCache && methodologyCache.key === meta.generated_at) return methodologyCache.p
  const p = getJson<Methodology>(`methodology.json?v=${encodeURIComponent(meta.generated_at)}`)
  const entry = { key: meta.generated_at, p }
  methodologyCache = entry
  p.catch(() => {
    if (methodologyCache === entry) methodologyCache = null
  })
  return p
}

// records.json (08-03): one file, cached per meta.generated_at, evicted on failure.
let recordsCache: { key: string; p: Promise<RecordsFile> } | null = null

export function loadRecords(meta: Meta): Promise<RecordsFile> {
  if (recordsCache && recordsCache.key === meta.generated_at) return recordsCache.p
  const p = getJson<RecordsFile>(`records.json?v=${encodeURIComponent(meta.generated_at)}`)
  const entry = { key: meta.generated_at, p }
  recordsCache = entry
  p.catch(() => {
    if (recordsCache === entry) recordsCache = null
  })
  return p
}

// games/{season}.json: session cache keyed by meta.generated_at + season, evicted on failure.
const gamesCache = new Map<string, Promise<GamesFile>>()

export function loadGames(meta: Meta, season: number): Promise<GamesFile> {
  const key = `${meta.generated_at}|${season}`
  const cached = gamesCache.get(key)
  if (cached) return cached
  const p = getJson<GamesFile>(`games/${season}.json?v=${encodeURIComponent(meta.generated_at)}`)
  gamesCache.set(key, p)
  p.catch(() => {
    if (gamesCache.get(key) === p) gamesCache.delete(key)
  })
  return p
}

// Per-team-game EPA files: same cache pattern as loadGames (keyed by generated_at + season, evicted on failure).
const epaCache = new Map<string, Promise<EpaFile>>()

export function loadEpa(meta: Meta, season: number): Promise<EpaFile> {
  const key = `${meta.generated_at}|${season}`
  const cached = epaCache.get(key)
  if (cached) return cached
  const p = getJson<EpaFile>(`epa/${season}.json?v=${encodeURIComponent(meta.generated_at)}`)
  epaCache.set(key, p)
  p.catch(() => {
    if (epaCache.get(key) === p) epaCache.delete(key)
  })
  return p
}

export const findSeason = (meta: Meta, season: number): SeasonMeta | undefined =>
  meta.seasons.find((s) => s.season === season)

export const isLatest = (meta: Meta, season: number, week: number): boolean =>
  meta.latest.season === season && meta.latest.week === week

import type { Meta, WeekFile } from './types'

export const dataUrl = (path: string): string => `${import.meta.env.BASE_URL}data/${path}`

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(dataUrl(path), { cache: 'no-store' })
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`)
  return (await res.json()) as T
}

export const loadMeta = (): Promise<Meta> => getJson<Meta>('meta.json')
export const loadLatest = (): Promise<WeekFile> => getJson<WeekFile>('latest.json')

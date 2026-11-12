// Share URL scheme, launch gate, share page HTML and copy-URL selection (14-01, D-11..D-24).
// Single source of truth for both the app (copy-link buttons) and the Node build (scripts/share.mjs).
// Node 24 imports this file directly via type stripping, so: erasable TS only (no enums, namespaces,
// parameter properties, import.meta.env), and every value import carries an explicit .ts extension.
import { teamHash } from './router.ts'
import type { Callout, Meta } from './types'

/** First (season, week) that gets share pages (D-19). Earlier weeks keep hash deep links. */
export const SHARE_LAUNCH = { season: 2026, week: 9 } as const

type CalloutKey = Pick<Callout, 'season' | 'week' | 'franchise' | 'type'>
export interface ShareTarget { season: number; week: number }

/** '/s/team/BUF/2026-w9/' (D-12, D-14: week-versioned, trailing slash). */
export const teamSharePath = (fr: string, season: number, week: number): string =>
  `/s/team/${fr.toUpperCase()}/${season}-w${week}/`

/** '/og/team/BUF/2026-w9.png'. */
export const teamImagePath = (fr: string, season: number, week: number): string =>
  `/og/team/${fr.toUpperCase()}/${season}-w${week}.png`

/** '2026/9/HOU-mover-up' (D-13). */
export const calloutId = (c: CalloutKey): string =>
  `${c.season}/${c.week}/${c.franchise.toUpperCase()}-${c.type.replace(/_/g, '-')}`

export const calloutSharePath = (c: CalloutKey): string => `/s/c/${calloutId(c)}/`
export const calloutImagePath = (c: CalloutKey): string => `/og/c/${calloutId(c)}.png`

/** Same as callouts.ts calloutHref (not imported: its extensionless import breaks Node). */
export const calloutShareHash = (c: Pick<Callout, 'franchise' | 'season' | 'week'>): string =>
  teamHash(c.franchise, c.season, c.week)

/** True when (season, week) is at or after SHARE_LAUNCH and the week exists in meta (D-24). */
export function hasSharePage(season: number, week: number, meta: Pick<Meta, 'seasons'>): boolean {
  const afterLaunch = season > SHARE_LAUNCH.season || (season === SHARE_LAUNCH.season && week >= SHARE_LAUNCH.week)
  if (!afterLaunch) return false
  const s = meta.seasons.find((x) => x.season === season)
  return !!s && Object.prototype.hasOwnProperty.call(s.week_labels ?? {}, String(week))
}

/** Every (season, week) with a share page, ascending. Built from hasSharePage, so build and app agree. */
export function shareTargets(meta: Pick<Meta, 'seasons'>): ShareTarget[] {
  const out: ShareTarget[] = []
  for (const s of meta.seasons) {
    for (const key of Object.keys(s.week_labels ?? {})) {
      const week = Number(key)
      if (Number.isInteger(week) && String(week) === key && hasSharePage(s.season, week, meta)) {
        out.push({ season: s.season, week })
      }
    }
  }
  return out.sort((a, b) => a.season - b.season || a.week - b.week)
}

/** Escape text for HTML text and attribute contexts (D-15). & first. */
export function escapeHtml(s: string): string {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

export interface TeamCopyView { team: string; season?: number; week?: number; latest?: boolean }

/**
 * URL for the team header copy button (D-23). With a share page: origin + share path, always pinned
 * to a week (meta.latest on the latest view). Otherwise the same hash the page is on, via `deep`.
 */
export function teamCopyUrl(
  view: TeamCopyView,
  meta: Pick<Meta, 'seasons' | 'latest'>,
  origin: string,
  deep: (hash: string) => string,
): string {
  const s = view.latest ? meta.latest.season : view.season
  const w = view.latest ? meta.latest.week : view.week
  if (s !== undefined && w !== undefined && hasSharePage(s, w, meta)) return origin + teamSharePath(view.team, s, w)
  return deep(view.latest ? teamHash(view.team) : teamHash(view.team, view.season, view.week))
}

/** URL for a callout card copy button (D-22). */
export function calloutCopyUrl(
  c: CalloutKey,
  meta: Pick<Meta, 'seasons'>,
  origin: string,
  deep: (hash: string) => string,
): string {
  return hasSharePage(c.season, c.week, meta) ? origin + calloutSharePath(c) : deep(calloutShareHash(c))
}

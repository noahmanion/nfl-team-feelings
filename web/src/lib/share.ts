// Share URL scheme, launch gate, share page HTML and copy-URL selection (14-01, D-11..D-24).
// Single source of truth for both the app (copy-link buttons) and the Node build (scripts/share.mjs).
// Node 24 imports this file directly via type stripping, so: erasable TS only (no enums, namespaces,
// parameter properties, import.meta.env), and every value import carries an explicit .ts extension.
import { formatRecord, weekLabel } from './format.ts'
import { teamHash } from './router.ts'
import { eraName, eraText } from './teamNames.ts'
import type { Callout, Meta, Row } from './types'

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

// ---- Share page meta copy (UI-SPEC "Share page meta copy") ----

export interface ShareMeta { title: string; description: string; imageAlt: string; linkName: string }
type MetaForCopy = Pick<Meta, 'seasons' | 'teams'>

function seasonOf(season: number, meta: Pick<Meta, 'seasons'>) {
  return meta.seasons.find((s) => s.season === season) ?? { season, max_week: 0, reg_weeks: 18, n_teams: 32, week_labels: {} }
}

/** Era-correct nickname ("Bills"; "Football Team" for WAS 2020-21). */
function eraNick(team: string, season: number, meta: MetaForCopy): string {
  return eraText(meta.teams[team]?.nick ?? eraName(team, season, meta), team, season)
}

/** Team share page copy for one (team, season, week). */
export function teamShareMeta(
  row: Pick<Row, 'score' | 'label' | 'rank' | 'wins' | 'losses' | 'ties'>,
  team: string,
  season: number,
  week: number,
  meta: MetaForCopy,
): ShareMeta {
  const name = eraName(team, season, meta)
  const sm = seasonOf(season, meta)
  const wl = weekLabel(week, sm)
  const score = Number.isFinite(row.score) ? String(row.score) : '–'
  const record = formatRecord(row.wins, row.losses, row.ties)
  return {
    title: `${name}: ${score}, ${row.label}`,
    description: `${wl} · ${season}. #${row.rank} of ${sm.n_teams} at ${record}. How ${eraNick(team, season, meta)} fans should feel right now, by the Feel-Good Score.`,
    imageAlt: `${name} feel-good score: ${score} out of 100, “${row.label}”. ${wl}, ${season}.`,
    linkName: name,
  }
}

/** Callout share page copy. Headlines already led by the nickname are used alone. */
export function calloutShareMeta(
  c: Pick<Callout, 'season' | 'week' | 'franchise' | 'headline' | 'detail'>,
  meta: MetaForCopy,
): ShareMeta {
  const name = eraName(c.franchise, c.season, meta)
  const headline = eraText(c.headline, c.franchise, c.season)
  const detail = eraText(c.detail, c.franchise, c.season)
  const wl = weekLabel(c.week, seasonOf(c.season, meta))
  const nick = eraNick(c.franchise, c.season, meta)
  return {
    title: headline.startsWith(nick) ? headline : `${name}: ${headline}`,
    description: `${detail} ${wl} · ${c.season}, on the Feel-Good Score.`,
    imageAlt: `${name}: ${headline}. ${detail}`,
    linkName: name,
  }
}

// ---- Share page HTML (UI-SPEC "Share Page Fallback HTML", D-15/D-17) ----

export interface SharePageInput extends ShareMeta {
  /** Absolute site origin, no trailing slash (resolveSiteOrigin). */
  origin: string
  sharePath: string
  imagePath: string
  /** Hash route to redirect humans to, e.g. '#/team/BUF/2026/9'. */
  hash: string
}

// Link-preview fetchers stay on the page (a JS-running previewer would otherwise follow the redirect).
const CRAWLER_RE = '/bot|facebookexternalhit|facebot|twitterbot|slack|linkedin|discord|whatsapp|telegram|embedly|applebot/i'

/**
 * Full static HTML for a share page. All og/twitter tags precede the single script (crawlers read
 * only the head start); every interpolated value is escaped; the script hash is JSON-encoded with
 * '<' as \u003c so data can never close the script tag. No meta refresh.
 */
export function sharePageHtml(p: SharePageInput): string {
  const e = escapeHtml
  const url = e(p.origin + p.sharePath)
  const img = e(p.origin + p.imagePath)
  const title = e(p.title)
  const desc = e(p.description)
  const alt = e(p.imageAlt)
  const H = JSON.stringify(p.hash).replace(/</g, '\\u003c')
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>${title} | Feel-Good Score</title>
<meta name="description" content="${desc}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Feel-Good Score">
<meta property="og:title" content="${title}">
<meta property="og:description" content="${desc}">
<meta property="og:url" content="${url}">
<meta property="og:image" content="${img}">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="${alt}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${title}">
<meta name="twitter:description" content="${desc}">
<meta name="twitter:image" content="${img}">
<meta name="twitter:image:alt" content="${alt}">
<link rel="canonical" href="${url}">
<script>if (!${CRAWLER_RE}.test(navigator.userAgent)) location.replace('/' + ${H})</script>
</head>
<body style="margin:0;background:#ffffff;color:#222222;font:400 16px/1.5 system-ui,-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif">
<main style="max-width:680px;margin:0 auto;padding:48px 24px">
<p style="margin:0 0 16px;font-weight:700">Feel-Good Score</p>
<h1 style="margin:0 0 8px;font-size:28px;line-height:1.1;font-weight:700">${title}</h1>
<p style="margin:0 0 24px;color:#6b6b6b">${desc}</p>
<p style="margin:0"><a href="/${e(p.hash)}" style="color:#1f5fbf">Open ${e(p.linkName)} on Feel-Good Score →</a></p>
</main>
</body>
</html>
`
}

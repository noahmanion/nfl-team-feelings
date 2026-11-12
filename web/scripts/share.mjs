// Build-time share step (14-03, D-01, D-16, D-18..D-21).
// Runs after `vite build`: renders a 1200x630 PNG + a static share page for every team row and
// every callout of every share target week (>= SHARE_LAUNCH), re-renders og-default.png, then
// self-checks that every page's og:image file exists. Logs timing + memory (D-20).
//
// Node 24 imports the .ts helpers directly (type stripping). Only import Node-safe lib modules here
// (explicit .ts extensions, no import.meta.env); the app-only callout/logo helpers break under Node (Pitfall 5).
import { mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import {
  calloutImagePath,
  calloutShareHash,
  calloutShareMeta,
  calloutSharePath,
  sharePageHtml,
  shareTargets,
  teamImagePath,
  teamShareMeta,
  teamSharePath,
} from '../src/lib/share.ts'
import { teamHash } from '../src/lib/router.ts'
import { eraName, eraText } from '../src/lib/teamNames.ts'
import { formatRecord, weekLabel } from '../src/lib/format.ts'
import { resolveSiteOrigin } from '../src/lib/siteOrigin.ts'
import { logosOff } from '../src/lib/logoSwitch.ts'
import { calloutCard, renderPng, siteCard, teamCard } from './og-template.mjs'

const CARD_WARN_KB = 300
const PROJECT_CARDS_PER_WEEK = 45
const PROJECT_WEEKS = 14

const readJson = (p) => JSON.parse(readFileSync(p, 'utf8'))

function writeOut(outDir, rel, data) {
  const file = join(outDir, rel)
  mkdirSync(dirname(file), { recursive: true })
  writeFileSync(file, data)
  return file
}

/**
 * Render every share card + page into outDir. Returns
 * { cards, pages, seconds, msPerCard, maxKB, targets }.
 */
export async function buildShare({ dataDir, outDir, logoDir, env = {}, log = console.log }) {
  if (!process.features?.typescript) throw new Error('share: Node 24+ required (run nvm use 24)')
  const t0 = performance.now()

  const meta = readJson(join(dataDir, 'meta.json'))
  const origin = resolveSiteOrigin(env)
  const host = new URL(origin).host
  const off = logosOff(env.VITE_LOGOS)

  // Logo cache: FR -> data URI or null (chip). Off -> always null (D-04).
  const logos = new Map()
  const logoFor = (fr) => {
    if (off) return null
    if (logos.has(fr)) return logos.get(fr)
    let uri = null
    try {
      uri = 'data:image/png;base64,' + readFileSync(join(logoDir, `${fr}.png`)).toString('base64')
    } catch {
      log(`share: logo missing for ${fr}, using chip`)
    }
    logos.set(fr, uri)
    return uri
  }

  // A missing or corrupt snapshot file is a build error, not "no rows": the app's copy buttons
  // (hasSharePage) already point at these weeks, so skipping would ship links that 404 (WR-02).
  const seasons = new Map()
  const seasonFile = (season) => {
    if (!seasons.has(season)) {
      const file = join(dataDir, `snapshots/${season}.json`)
      try {
        seasons.set(season, readJson(file))
      } catch (err) {
        throw new Error(`share: cannot read ${file} (${err?.message ?? err}); copy links for ${season} would 404`)
      }
    }
    return seasons.get(season)
  }

  let cards = 0
  let maxBytes = 0
  let targets = 0
  const pages = []

  const emitCard = async (tree, imagePath) => {
    const png = await renderPng(tree, imagePath)
    writeOut(outDir, imagePath, png)
    cards++
    if (png.length > maxBytes) maxBytes = png.length
    if (png.length > CARD_WARN_KB * 1024) log(`share: warning ${imagePath} is ${Math.round(png.length / 1024)} KB (> ${CARD_WARN_KB} KB)`)
  }
  const emitPage = (sharePath, html) => {
    writeOut(outDir, sharePath + 'index.html', html)
    pages.push(sharePath)
  }

  for (const { season, week } of shareTargets(meta)) {
    const file = seasonFile(season)
    const rows = file?.weeks?.[String(week)] ?? []
    const callouts = file?.callouts?.[String(week)] ?? []
    if (!rows.length) {
      throw new Error(`share: no snapshot rows for ${season} w${week}, but hasSharePage lists it (copy links would 404)`)
    }
    targets++
    const sm = meta.seasons.find((s) => s.season === season)
    const dateStamp = weekLabel(week, sm) + ' · ' + season

    // Team cards (D-21).
    for (const row of rows) {
      const fr = row.franchise
      const team = meta.teams[fr] ?? {}
      const imagePath = teamImagePath(fr, season, week)
      const sharePath = teamSharePath(fr, season, week)
      await emitCard(
        teamCard({
          name: eraName(fr, season, meta),
          score: row.score,
          label: row.label,
          band: row.band,
          bands: meta.bands,
          rank: row.rank,
          nTeams: sm.n_teams,
          record: formatRecord(row.wins, row.losses, row.ties),
          dateStamp,
          logo: logoFor(fr),
          primary: team.primary,
          secondary: team.secondary,
          host,
        }),
        imagePath,
      )
      emitPage(sharePath, sharePageHtml({ origin, sharePath, imagePath, hash: teamHash(fr, season, week), ...teamShareMeta(row, fr, season, week, meta) }))
    }

    // Callout cards.
    for (const c of callouts) {
      const fr = c.franchise
      const team = meta.teams[fr] ?? {}
      const imagePath = calloutImagePath(c)
      const sharePath = calloutSharePath(c)
      await emitCard(
        calloutCard({
          type: c.type,
          name: eraName(fr, c.season, meta),
          headline: eraText(c.headline, fr, c.season),
          detail: eraText(c.detail, fr, c.season),
          band: c.band,
          bands: meta.bands,
          dateStamp,
          logo: logoFor(fr),
          primary: team.primary,
          secondary: team.secondary,
          host,
        }),
        imagePath,
      )
      emitPage(sharePath, sharePageHtml({ origin, sharePath, imagePath, hash: calloutShareHash(c), ...calloutShareMeta(c, meta) }))
    }
  }

  // Site-default card (D-06): overwrite the committed placeholder in the output.
  await emitCard(siteCard({ host }), '/og-default.png')

  // Self-check: every page's og:image exists and is non-empty.
  for (const sharePath of pages) {
    const html = readFileSync(join(outDir, sharePath, 'index.html'), 'utf8')
    const img = html.match(/property="og:image" content="([^"]+)"/)?.[1] ?? ''
    const rel = img.startsWith(origin) ? img.slice(origin.length) : ''
    let ok = false
    try {
      ok = !!rel && statSync(join(outDir, rel)).size > 0
    } catch {
      ok = false
    }
    if (!ok) throw new Error(`share: og:image missing for ${sharePath}`)
  }

  const ms = performance.now() - t0
  const seconds = Math.round(ms / 10) / 100
  const msPerCard = Math.max(1, Math.round(ms / Math.max(cards, 1)))
  const maxKB = Math.round(maxBytes / 1024)
  const rssMB = Math.round(process.memoryUsage().rss / 1024 / 1024)
  const projected = Math.round((msPerCard * PROJECT_CARDS_PER_WEEK * PROJECT_WEEKS) / 1000)
  log(`share: rendered ${cards} cards in ${seconds}s (${msPerCard}ms/card avg)`)
  log(`share: ${pages.length} pages, ${targets} target weeks, largest card ${maxKB} KB, rss ${rssMB} MB`)
  log(`share: projected full season (~${PROJECT_WEEKS} weeks) ≈ ${projected}s`)

  return { cards, pages: pages.length, seconds, msPerCard, maxKB, targets }
}

async function main() {
  const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
  const { loadEnv } = await import('vite')
  // Same VITE_* source as vite.config.ts's config.env (.env files + process.env).
  const env = { ...process.env, ...loadEnv('production', webRoot, 'VITE_') }
  await buildShare({
    dataDir: join(webRoot, 'dist/data'),
    outDir: join(webRoot, 'dist'),
    // public/logos, not dist/logos: dropLogos deletes dist/logos when logos are off.
    logoDir: join(webRoot, 'public/logos'),
    env,
  })
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((err) => {
    console.error(err?.message ?? err)
    process.exit(1)
  })
}

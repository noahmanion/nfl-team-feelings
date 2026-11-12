// Build-time site origin for absolute share-tag URLs (og:url, og:image, canonical).
// Pure: takes an env-like record so it can be unit tested and used from vite.config.ts.

export const FALLBACK_ORIGIN = 'https://nfl-team-feelings.vercel.app'

export function resolveSiteOrigin(env: Record<string, string | undefined>): string {
  const explicit = env.SITE_ORIGIN?.trim()
  const vercelHost = env.VERCEL_PROJECT_PRODUCTION_URL?.trim()
  const origin = explicit ? explicit : vercelHost ? `https://${vercelHost}` : FALLBACK_ORIGIN
  return origin.replace(/\/+$/, '')
}

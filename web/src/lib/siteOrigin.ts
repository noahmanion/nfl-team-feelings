// Build-time site origin for absolute share-tag URLs (og:url, og:image, canonical).
// Pure: takes an env-like record so it can be unit tested and used from vite.config.ts.
// Throws on anything that isn't an absolute http(s) URL so a bad env value fails the
// build instead of emitting relative/broken share tags. Normalizing through URL also
// percent-encodes characters like `"` and `<`, so the result is safe to paste into
// an HTML attribute.

export const FALLBACK_ORIGIN = 'https://nfl-team-feelings.vercel.app'

export function resolveSiteOrigin(env: Record<string, string | undefined>): string {
  const explicit = env.SITE_ORIGIN?.trim()
  // Vercel sets this as a bare host, but tolerate a value that already has a scheme.
  const vercelHost = env.VERCEL_PROJECT_PRODUCTION_URL?.trim().replace(/^https?:\/\//i, '')
  const raw = explicit ? explicit : vercelHost ? `https://${vercelHost}` : FALLBACK_ORIGIN

  let url: URL
  try {
    url = new URL(raw)
  } catch {
    throw new Error(`SITE_ORIGIN must be an absolute http(s) URL, got: ${raw}`)
  }
  if (url.protocol !== 'https:' && url.protocol !== 'http:') {
    throw new Error(`SITE_ORIGIN must be an absolute http(s) URL, got: ${raw}`)
  }
  return (url.origin + url.pathname).replace(/\/+$/, '')
}

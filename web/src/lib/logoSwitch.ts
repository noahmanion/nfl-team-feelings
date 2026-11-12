// Logo kill switch predicate. Pure (no import.meta.env) so both the app (logos.ts) and the
// build (vite.config.ts, which strips dist/logos when off) share one definition.

/** True only when the VITE_LOGOS value is "off" (any case, trimmed). */
export function logosOff(value: unknown): boolean {
  return typeof value === 'string' && value.trim().toLowerCase() === 'off'
}

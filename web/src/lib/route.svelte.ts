import { parseHash, type Route } from './router'

// Single source of truth for the current view. Wrapped in an object because an
// exported $state primitive can't be reassigned from other modules.
export const route = $state<{ current: Route }>({ current: parseHash(location.hash) })

window.addEventListener('hashchange', () => {
  route.current = parseHash(location.hash)
})

/** Navigate with a history entry (season change, Latest). hashchange updates the route. */
export function go(hash: string): void {
  if (location.hash === hash || (hash === '#/' && location.hash === '')) {
    route.current = parseHash(hash)
    return
  }
  location.hash = hash
}

/** Rewrite the hash without a history entry. replaceState doesn't fire hashchange (Pitfall 6). */
export function replace(hash: string): void {
  history.replaceState(null, '', hash)
  route.current = parseHash(hash)
}

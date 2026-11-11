// Pure helpers over the 08-01 callout contract (callouts.json + snapshots/{season}.json `callouts`).
import { teamHash } from './router'
import type { Callout, CalloutType, SeasonFile } from './types'

/** Callout types rendered as cards (movers go to the movers strip). */
export const CARD_TYPES: readonly CalloutType[] = ['worried', 'hopeful', 'misery', 'joy']

/** A week's callouts from a season file; [] for a missing week or an older file without `callouts`. */
export function forWeek(file: SeasonFile | null | undefined, week: number): Callout[] {
  return file?.callouts?.[String(week)] ?? []
}

/** Only one franchise's callouts, order kept. */
export const forTeam = (list: Callout[], abbr: string): Callout[] => list.filter((c) => c.franchise === abbr)

/** Card callouts (worried / hopeful / misery / joy), order kept. */
export const cardCallouts = (list: Callout[]): Callout[] => list.filter((c) => CARD_TYPES.includes(c.type))

/** Movers split into risers and fallers, order kept. */
export function moverCallouts(list: Callout[]): { up: Callout[]; down: Callout[] } {
  return { up: list.filter((c) => c.type === 'mover_up'), down: list.filter((c) => c.type === 'mover_down') }
}

/** Stable: myTeam's callouts first (relative order kept), then the rest. Never mutates the input. */
export function orderCallouts(list: Callout[], myTeam: string | null): Callout[] {
  if (!myTeam) return list.slice()
  return [...list.filter((c) => c.franchise === myTeam), ...list.filter((c) => c.franchise !== myTeam)]
}

/** The stable deep link for a callout: always the season/week form, never latest. */
export const calloutHref = (c: Pick<Callout, 'franchise' | 'season' | 'week'>): string =>
  teamHash(c.franchise, c.season, c.week)

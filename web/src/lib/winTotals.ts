// Pure DATA-03 logic for the team page "Preseason expectations" block (D-19, D-20). The
// WinTotals component renders the view model returned by winTotalsView and nothing else.

import { recordText } from './explore'

/** Structural slice of teams/{F}.json, so the full TeamFile satisfies it. */
export interface WinTotalsInput {
  vegas_win_totals: { season: number[]; line: number[]; line_type: string[]; used_in_score: boolean[] }
  expectation?: { season: number[]; exp_total: (number | null)[]; source: (string | null)[]; reg_games: number[] }
}
export interface LegendRow { key: 'vegas' | 'model' | 'pace'; label: string; suffix?: string; value: string; pos: number | null }
export interface WinTotalsView { regGames: number; ticks: number[]; rows: LegendRow[]; dek: string; notes: string; source?: string }

export const SOURCE_LINE = 'SOURCE: NFLVERSE (2003–2020) · COVERS / DRAFTKINGS (2021+)'

/** (W + 0.5·T) / GP × reg_games, 1 dp; null with no games. */
export const pace = (w: number, l: number, t: number, reg: number): number | null => {
  const gp = w + l + t
  return gp === 0 ? null : Math.round(((w + 0.5 * t) / gp) * reg * 10) / 10
}
/** The regular season is over when GP reaches reg_games. */
export const finished = (w: number, l: number, t: number, reg: number): boolean => w + l + t >= reg
/** Multiples of 4 up to reg_games − 2, plus reg_games: 17 → [0,4,8,12,17]; 16 → [0,4,8,12,16]. */
export const lineTicks = (reg: number): number[] =>
  [...Array.from({ length: Math.floor((reg - 2) / 4) + 1 }, (_, i) => i * 4), reg]
/** Wins counting ties as half: "13", "8.5". */
export const winsText = (w: number, t: number): string => {
  const v = w + 0.5 * t
  return Number.isInteger(v) ? String(v) : v.toFixed(1)
}
/** Marker left position in percent of the 0..reg_games track, clamped. */
export const markerPos = (value: number, reg: number): number => Math.min(100, Math.max(0, (value / reg) * 100))

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

export function winTotalsView(file: WinTotalsInput, season: number,
  rec: { wins: number; losses: number; ties: number } | null): WinTotalsView | null {
  const vw = file.vegas_win_totals
  const vi = vw ? vw.season.indexOf(season) : -1
  const ex = file.expectation
  const ei = ex ? ex.season.indexOf(season) : -1
  if (vi < 0 && ei < 0) return null

  const regGames = ei >= 0 ? ex!.reg_games[ei] : season <= 2020 ? 16 : 17
  const expTotal = ei >= 0 ? ex!.exp_total[ei] : null
  const isModel = ei >= 0 && ex!.source[ei] === 'model' && expTotal != null
  const rows: LegendRow[] = []
  let lead: string

  if (vi >= 0) {
    const line = vw.line[vi]
    rows.push({
      key: 'vegas',
      label: vw.used_in_score[vi] ? 'Vegas preseason (used in score)' : 'Vegas preseason (display only, not used in score)',
      ...(vw.line_type[vi] === 'preseason_open' ? { suffix: ' · opening line, not the final preseason number' } : {}),
      value: line.toFixed(1),
      pos: markerPos(line, regGames),
    })
    lead = `Vegas set the line at ${line.toFixed(1)} wins.`
  } else if (expTotal != null) {
    lead = `The model expected ${expTotal.toFixed(1)} wins.`
  } else {
    return null
  }
  if (isModel) {
    rows.push({ key: 'model', label: 'Model preseason (used in score)', value: expTotal!.toFixed(1), pos: markerPos(expTotal!, regGames) })
  }

  const gp = rec ? rec.wins + rec.losses + rec.ties : 0
  let tail: string
  if (!rec || gp === 0) {
    rows.push({ key: 'pace', label: 'No games yet.', value: '–', pos: null })
    tail = 'No games yet.'
  } else if (finished(rec.wins, rec.losses, rec.ties, regGames)) {
    const w = winsText(rec.wins, rec.ties)
    rows.push({ key: 'pace', label: `Finished ${recordText(rec.wins, rec.losses, rec.ties)}`, value: w,
      pos: markerPos(rec.wins + 0.5 * rec.ties, regGames) })
    tail = `They finished with ${w}.`
  } else {
    const p = pace(rec.wins, rec.losses, rec.ties, regGames)!
    rows.push({ key: 'pace',
      label: `On pace for ${p.toFixed(1)} wins (${recordText(rec.wins, rec.losses, rec.ties)} after ${plural(gp, 'game')})`,
      value: p.toFixed(1), pos: markerPos(p, regGames) })
    tail = `They’re on pace for ${p.toFixed(1)}.`
  }

  const notes = vi < 0
    ? 'No Vegas line on file before 2003. The score uses the model’s preseason expectation.'
    : vw.used_in_score[vi]
      ? 'The score uses this line, normalized to the league average.'
      : 'Shown for context. The score uses the model’s preseason expectation for this season.'

  return { regGames, ticks: lineTicks(regGames), rows, dek: `${lead} ${tail}`, notes,
    ...(vi >= 0 ? { source: SOURCE_LINE } : {}) }
}

// Mirror of the pipeline JSON contract (pipeline/src/fgs/export.py, D-06).

export interface Band { min: number; max: number; label: string; emoji: string }
/** conf/division: current alignment, not era-correct (11-03). Optional so older JSON still types. */
export interface TeamMeta { name: string; nick: string; primary: string; secondary: string; conf?: string; division?: string }
export interface SeasonMeta { season: number; max_week: number; reg_weeks: number; n_teams: number; week_labels: Record<string, string> }
export interface FactorMeta { key: string; label: string; weight: number; description: string }
export interface Meta { version: number; score_kind: string; generated_at: string; data_through: string;
  latest: { season: number; week: number }; partial_week: boolean; seasons: SeasonMeta[];
  bands: Band[]; hysteresis: number; teams: Record<string, TeamMeta>; factors?: FactorMeta[]; baseline?: number
  /** Offseason (draft) settings (07-04). */
  offseason?: { draft: { weight: number; display_only: boolean; chart: string; decay: number[] } }
  /** Seasons with an epa/{season}.json file (11-03). */
  epa_seasons?: number[] }
/** Draft capital vs original slots, week-0 rows only (07-04). */
export interface DraftInfo {
  /** Stuart chart points vs original slots, 1 dp (signed). */
  surplus: number
  /** Capped, per-draft z, 2 dp. */
  z: number
  /** 1..262; null when the surplus rounds to 0 ("about even with their original slots"). */
  equiv_pick: number | null
  /** 1 = most capital over slot in that draft. */
  rank: number
  /** Full display sentence, generated in the pipeline. */
  text: string
  /** True only when offseason.draft.weight != 0. */
  moves_score: boolean
}
export interface Row { franchise: string; rank: number; score: number; elo: number | null; band: number; label: string; emoji: string;
  wins: number; losses: number; ties: number; score_delta: number | null; rank_delta: number | null; contribs?: Record<string, number>;
  /** Integer points per factor; baseline + Σpoints === score (04-01). */
  points?: Record<string, number>; blurb?: string;
  /** Simulated playoff odds, integer 0–100 (actual result 100/0 once the regular season is over); null without sims (05-05). */
  playoff_prob?: number | null; expectation_source?: 'vegas' | 'model' | null; qb?: string | null
  /** Week-0 rows only; null when not derivable (e.g. 1999) (07-04). */
  draft?: DraftInfo | null }
export interface WeekFile { season: number; week: number; rows: Row[] }
/** Callout card / mover (08-01; pipeline/src/fgs/export.py). */
export type CalloutType = 'worried' | 'hopeful' | 'mover_up' | 'mover_down' | 'misery' | 'joy'
export interface Callout { type: CalloutType; season: number; week: number; franchise: string;
  headline: string; detail: string; evidence: string | null; stat: number; start: string | null; band: number }
export interface SeasonFile { season: number; weeks: Record<string, Row[]>
  /** Per-week callouts (08-01); optional so older cached files still type-check. */
  callouts?: Record<string, Callout[]> }
// records.json (08-03; pipeline/src/fgs/records.py)
export interface ExtremeEntry { season: number; franchise: string; score: number; week: number; date: string;
  wins: number; losses: number; ties: number; mean: number }
export interface SeasonRecord { season: number; wins: number; losses: number; ties: number }
export interface StreakEntry { franchise: string; start: string; end: string | null; days: number; active: boolean;
  start_season: number; start_week: number; end_season: number | null; end_week: number | null; seasons: SeasonRecord[] }
export type StreakKind = 'misery' | 'joy'
export interface ActiveStreak { kind: StreakKind; start: string; days: number; start_season: number; start_week: number }
export interface ExcludedSeason { season: number; franchise: string; reason: string }
export interface NotableEntry { season: number; franchise: string; list: string; rank: number; score: number; mean: number;
  wins: number; losses: number; ties: number }
export interface RecordsFile { as_of: string; saddest: ExtremeEntry[]; happiest: ExtremeEntry[]; misery: StreakEntry[];
  joy: StreakEntry[]; active: Record<string, ActiveStreak>; excluded: ExcludedSeason[]; notable: NotableEntry[] }
export interface HistoryFile { keys: string[]; teams: Record<string, (number | null)[]> }
/** games/{season}.json, columnar (04-01). asof_week = first snapshot week that includes the result. */
export interface GamesFile { season: number; week: number[]; asof_week: number[]; home: string[]; away: string[];
  home_score: (number | null)[]; away_score: (number | null)[]; game_type: string[]; gameday: string[]; neutral: boolean[] }

// methodology.json (06-04; pipeline/src/fgs/methodology.py)
export type Effect = 'helps' | 'hurts' | 'none'
export interface FoldSign { k: number; of: number }
export interface MethodologyFactor { key: string; label: string; description: string; weight: number;
  sign: '+' | '-' | '0'; effect: Effect; fold_sign: FoldSign | null;
  delta_spearman_n8: number | null; baseline_spearman_n8: number | null }
export interface Candidate { key: string; label: string; brier_only?: boolean }
export type CI = [number, number]
export interface MetricCI { value: number | null; ci: CI | null; ci_season?: CI | null }
export type PeriodMetrics = Record<string, MetricCI>
export interface DiffMetric { value: number | null; ci_season?: CI; ci_cluster?: CI; seasons_won?: number; of?: number;
  per_season?: unknown }
export type DiffBlock = Record<string, DiffMetric>
export interface WalkForwardBlock { seasons: [number, number]; label: string; spearman_n8: PeriodMetrics;
  spearman_n4: PeriodMetrics; brier: PeriodMetrics; diff: DiffBlock | null }
export interface HoldoutBlock { seasons: [number, number]; label: string; evaluated_at: string | null;
  verdict: 'yes' | 'slight' | 'no' | null; headline: string | null; pass: boolean | null;
  spearman_n8: PeriodMetrics; spearman_n4: PeriodMetrics; brier: PeriodMetrics; diff: DiffBlock | null;
  diagnostic: { vs_exp_zeroed: { spearman_n8: number; diff_vs_elo: { value: number; ci_cluster?: CI } } | null } | null;
  rerun: boolean }
export interface Note { key: string; text: string; values: Record<string, number> }
export interface Methodology {
  version: number
  frozen: { fitted_at: string; fit_seasons: [number, number]; alpha: number; n: number } | null
  target: { n: number; text: string }
  split: { train: [number, number]; walk_forward: [number, number]; holdout: [number, number]; live: number;
    reference: [number, number] }
  factors: MethodologyFactor[]
  candidates: Candidate[]
  walk_forward: WalkForwardBlock | null
  holdout: HoldoutBlock | null
  notes: Note[]
}

/** epa/{season}.json: columnar, one row per played team-game with pbp (11-03). def_* = the opponent's off_*.
 * Play counts are never null (0 when a side had no qualifying plays); the per-play rates can be null
 * then (WR-05), so consumers must skip null rates rather than treat them as 0. */
export interface EpaFile { season: number; note: string; game_id: string[]; week: number[]; game_type: string[];
  franchise: string[]; opponent: string[]; off_epa: (number | null)[]; off_plays: number[]; off_sr: (number | null)[];
  def_epa: (number | null)[]; def_plays: number[]; def_sr: (number | null)[] }

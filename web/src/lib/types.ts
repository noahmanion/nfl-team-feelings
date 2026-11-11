// Mirror of the pipeline JSON contract (pipeline/src/fgs/export.py, D-06).

export interface Band { min: number; max: number; label: string; emoji: string }
export interface TeamMeta { name: string; nick: string; primary: string; secondary: string }
export interface SeasonMeta { season: number; max_week: number; reg_weeks: number; n_teams: number; week_labels: Record<string, string> }
export interface FactorMeta { key: string; label: string; weight: number; description: string }
export interface Meta { version: number; score_kind: string; generated_at: string; data_through: string;
  latest: { season: number; week: number }; partial_week: boolean; seasons: SeasonMeta[];
  bands: Band[]; hysteresis: number; teams: Record<string, TeamMeta>; factors?: FactorMeta[]; baseline?: number }
export interface Row { franchise: string; rank: number; score: number; elo: number | null; band: number; label: string; emoji: string;
  wins: number; losses: number; ties: number; score_delta: number | null; rank_delta: number | null; contribs?: Record<string, number>;
  /** Integer points per factor; baseline + Σpoints === score (04-01). */
  points?: Record<string, number>; blurb?: string;
  /** Simulated playoff odds, integer 0–100 (actual result 100/0 once the regular season is over); null without sims (05-05). */
  playoff_prob?: number | null; expectation_source?: 'vegas' | 'model' | null; qb?: string | null }
export interface WeekFile { season: number; week: number; rows: Row[] }
export interface SeasonFile { season: number; weeks: Record<string, Row[]> }
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
export interface DiffMetric { value: number; ci_season?: CI; ci_cluster?: CI; seasons_won?: number; of?: number;
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

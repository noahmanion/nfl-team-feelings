// Mirror of the pipeline JSON contract (pipeline/src/fgs/export.py, D-06).

export interface Band { min: number; max: number; label: string; emoji: string }
export interface TeamMeta { name: string; nick: string; primary: string; secondary: string }
export interface SeasonMeta { season: number; max_week: number; reg_weeks: number; n_teams: number; week_labels: Record<string, string> }
export interface FactorMeta { key: string; label: string; weight: number; description: string }
export interface Meta { version: number; score_kind: string; generated_at: string; data_through: string;
  latest: { season: number; week: number }; partial_week: boolean; seasons: SeasonMeta[];
  bands: Band[]; hysteresis: number; teams: Record<string, TeamMeta>; factors?: FactorMeta[] }
export interface Row { franchise: string; rank: number; score: number; elo: number | null; band: number; label: string; emoji: string;
  wins: number; losses: number; ties: number; score_delta: number | null; rank_delta: number | null; contribs?: Record<string, number> }
export interface WeekFile { season: number; week: number; rows: Row[] }
export interface SeasonFile { season: number; weeks: Record<string, Row[]> }
export interface HistoryFile { keys: string[]; teams: Record<string, (number | null)[]> }

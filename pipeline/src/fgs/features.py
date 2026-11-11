"""As-of factor values per (season, week, franchise).

Every value uses only games with asof_week <= week (the week the result became known), so a
snapshot never sees its own future. Pure: no file I/O. This module must stay independent of
the dev-only evaluation harness (leakage firewall).

- elo:           from the snapshot grid
- season_record: REG win % (ties 0.5); 0.5 before a team's first REG result
- last16:        win % over the most recent up-to-16 played games, REG + playoffs, ties 0.5,
                 crossing season boundaries; 0.5 with no prior games
- pd_pg:         season-to-date REG point differential per game; 0.0 with no games
                 (a baseline only, not a score factor)
- mov:           mean point margin over the last 8 played games (REG + playoffs, crossing
                 seasons), each game's margin capped at +/-24 before averaging; 0.0 with no games
- sow:           mean over the last 8 played games of (result - p_avg), result 1/0.5/0 and
                 p_avg the chance a league-average (MEAN_ELO) team beats that opponent (its
                 pre-game Elo) at that venue; 0.0 with no games
- streak:        signed current streak (+k after k straight wins, -k after k straight losses),
                 a tie resets it to 0, capped at +/-8, carried across seasons; 0.0 with no games
- luck:          one-score wins minus one-score losses (|margin| <= 8, ties excluded) over the
                 last 16 played games (REG + playoffs, crossing seasons); 0.0 with no games
- epa_traj:      opponent-adjusted net EPA/play trajectory: EWMA (half-life 4 games, crossing
                 seasons) minus this season's mean (fgs.efficiency); 0.0 with no game yet this
                 season or without pbp_games
- qb_trend:      the current starting QB's form level (research revision A1): dropback-weighted
                 EWMA (half-life 4) of his EPA/dropback over his own starts on any team, any
                 season; 0.0 for a QB with < 2 starts, at week 0, or without pbp_games. CONTEXT's
                 literal "QB form minus team season-to-date" was measured and logged (worse).
- playoff_prob, exp_wins: the season simulator's (fgs.sim) playoff probability and expected final
                 REG wins as of this snapshot (as-of features, not score factors); 0.0 without sim
- exp_total, expectation_source: the team-season's preseason expectation (fgs.expectation):
                 normalized Vegas win total ("vegas", 2003-2020) else the model's week-0 sim
                 exp_wins ("model"); null without sim
- vs_exp:        win % so far minus the preseason expectation's pace (MODEL-08):
                 ((wins + 0.5*ties) - exp_total / reg_games(season) * gp) / max(gp, 1), gp = the
                 snapshot's as-of REG games; 0.0 at week 0 and without sim. Phase 6 flag (RESEARCH
                 Pitfall 1): its signal is learned mostly on Vegas-sourced rows (2003-2020), while
                 2021+ (holdout and live season) is always model-sourced.
- po_trend:      playoff-odds trend (MODEL-12): playoff_prob(season, week) minus
                 playoff_prob(season, max(week - 3, 0)), same season, raw sim values (never the
                 export's post-season display override); 0.0 at week 0, for a missing lag and
                 without sim
- qb_name, qb_new: display columns (not factors): the current QB's name (null at week 0 / no
                 pbp) and whether he has fewer than 2 starts (False without pbp)
"""

import numpy as np
import polars as pl

from fgs import efficiency, expectation
from fgs.season_config import MEAN_ELO, hfa_for, reg_games

FEATURE_COLUMNS = ["elo", "season_record", "last16", "pd_pg", "mov", "sow", "streak", "luck", "epa_traj", "qb_trend",
                   "playoff_prob", "exp_wins", "vs_exp", "po_trend"]
GAME_FACTORS = ["mov", "sow", "streak", "luck"]
LAST_N = 16
MOV_N, MOV_CAP = 8, 24
SOW_N = 8
STREAK_CAP = 8
LUCK_N, ONE_SCORE = 16, 8
PO_LAG = 3


def _last16(snap: pl.DataFrame, team_games: pl.DataFrame) -> pl.DataFrame:
    games = (
        team_games.filter(pl.col("played"))
        .with_columns((pl.col("season").cast(pl.Int64) * 100 + pl.col("asof_week").cast(pl.Int64)).alias("key"))
        .sort("franchise_id", "key", "game_id")
        .with_columns(pl.col("outcome").cast(pl.Float64).cum_sum().over("franchise_id").alias("cum_o"))
        .with_columns(
            (pl.col("cum_o") - pl.col("cum_o").shift(LAST_N).over("franchise_id").fill_null(0.0)).alias("o16"),
            pl.int_range(1, pl.len() + 1).over("franchise_id").clip(upper_bound=LAST_N).alias("n16"),
        )
        # several games can share a key; the last row per key holds the window ending there
        .group_by("franchise_id", "key", maintain_order=True)
        .last()
        .select("franchise_id", "key", (pl.col("o16") / pl.col("n16")).alias("last16"))
        .sort("key")
    )
    return (
        snap.with_columns((pl.col("season").cast(pl.Int64) * 100 + pl.col("week").cast(pl.Int64)).alias("key"))
        .sort("key")
        .join_asof(games, on="key", by="franchise_id", strategy="backward", check_sortedness=False)
        .with_columns(pl.col("last16").fill_null(0.5))
        .drop("key")
    )


def _pd_pg(snap: pl.DataFrame, team_games: pl.DataFrame) -> pl.DataFrame:
    reg = (
        team_games.filter(pl.col("played") & pl.col("is_reg"))
        .with_columns(
            pl.col("season").cast(pl.Int32),
            pl.col("asof_week").cast(pl.Int32).alias("week"),
            (pl.col("points_for") - pl.col("points_against")).cast(pl.Float64).alias("pd"),
        )
        .group_by("franchise_id", "season", "week")
        .agg(pl.col("pd").sum(), pl.len().alias("n"))
        .sort("franchise_id", "season", "week")
        .with_columns(
            pl.col("pd").cum_sum().over("franchise_id", "season").alias("cum_pd"),
            pl.col("n").cum_sum().over("franchise_id", "season").alias("cum_n"),
        )
        .select("franchise_id", "season", "week", (pl.col("cum_pd") / pl.col("cum_n")).alias("pd_pg"))
        .sort("week")
    )
    return (
        snap.sort("week")
        .join_asof(reg, on="week", by=["franchise_id", "season"], strategy="backward", check_sortedness=False)
        .with_columns(pl.col("pd_pg").fill_null(0.0))
    )


def _hfa_table(seasons) -> pl.DataFrame:
    # private copy: features must not import the evaluation harness (leakage firewall)
    seasons = sorted({int(x) for x in seasons})
    return pl.DataFrame(
        {"season": seasons, "hfa": [hfa_for(x) for x in seasons]},
        schema={"season": pl.Int32, "hfa": pl.Float64},
    )


_PLAY_ORDER = ["gameday", "gametime", "game_id"]  # same tiebreak order as the Elo replay


def _per_game(team_games: pl.DataFrame) -> pl.DataFrame:
    """Played team-games in as-of order with per-game quantities (margin, capped margin,
    p_avg = chance a league-average team beats this opponent at this venue, sow_g)."""
    played = team_games.filter(pl.col("played"))
    opp = played.select("game_id", pl.col("franchise_id").alias("opponent_id"), pl.col("elo_pre").alias("opp_elo_pre"))
    return (
        played.join(opp, on=["game_id", "opponent_id"], how="left")
        .join(_hfa_table(played["season"].unique().to_list()), on="season", how="left")
        .with_columns(
            (pl.col("points_for") - pl.col("points_against")).cast(pl.Float64).alias("margin"),
            pl.when(pl.col("neutral")).then(0.0).when(pl.col("is_home")).then(pl.col("hfa"))
            .otherwise(-pl.col("hfa")).alias("hfa_s"),
            (pl.col("season").cast(pl.Int64) * 100 + pl.col("asof_week").cast(pl.Int64)).alias("key"),
        )
        .with_columns(
            pl.col("margin").clip(-MOV_CAP, MOV_CAP).alias("m_cap"),
            (1.0 / (1.0 + 10 ** (-(MEAN_ELO - pl.col("opp_elo_pre") + pl.col("hfa_s")) / 400))).alias("p_avg"),
        )
        .with_columns(
            (pl.col("outcome").cast(pl.Float64) - pl.col("p_avg")).alias("sow_g"),
            ((pl.col("margin") > 0) & (pl.col("margin") <= ONE_SCORE)).cast(pl.Float64).alias("cw"),
            ((pl.col("margin") < 0) & (pl.col("margin") >= -ONE_SCORE)).cast(pl.Float64).alias("cl"),
        )
        # play order within one as-of key (a postponed game shares a key with a later one)
        .sort(["franchise_id", "key", *_PLAY_ORDER], nulls_last=True)
    )


def _win(col: str, n: int) -> pl.Expr:
    """Sum over the last n rows per franchise (cumsum minus shifted cumsum)."""
    c = pl.col(col).cum_sum().over("franchise_id")
    return c - c.shift(n).over("franchise_id").fill_null(0.0)


def _cnt(n: int) -> pl.Expr:
    return pl.int_range(1, pl.len() + 1).over("franchise_id").clip(upper_bound=n)


def _asof(snap: pl.DataFrame, per_key: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    """Join the last per-game row at or before each snapshot key; nulls (no games) -> 0.0."""
    last = (
        per_key.group_by("franchise_id", "key", maintain_order=True)
        .last()
        .select("franchise_id", "key", *cols)
        .sort("key")
    )
    return (
        snap.with_columns((pl.col("season").cast(pl.Int64) * 100 + pl.col("week").cast(pl.Int64)).alias("key"))
        .sort("key")
        .join_asof(last, on="key", by="franchise_id", strategy="backward", check_sortedness=False)
        .with_columns(pl.col(c).fill_null(0.0) for c in cols)
        .drop("key")
    )


def _streak(fid: np.ndarray, outcome: np.ndarray) -> np.ndarray:
    """Sequential signed streak per franchise (rows already sorted by franchise, then as-of order)."""
    out = np.zeros(len(outcome), dtype=float)
    cur, prev = 0, None
    for i, (f, o) in enumerate(zip(fid, outcome)):
        if f != prev:
            cur, prev = 0, f
        if o == 1:
            cur = max(cur, 0) + 1
        elif o == 0:
            cur = min(cur, 0) - 1
        else:
            cur = 0
        cur = max(-STREAK_CAP, min(STREAK_CAP, cur))
        out[i] = cur
    return out


def _game_factors(snap: pl.DataFrame, team_games: pl.DataFrame) -> pl.DataFrame:
    g = _per_game(team_games)
    g = g.with_columns(
        pl.Series("streak", _streak(g["franchise_id"].to_numpy(), g["outcome"].cast(pl.Float64).to_numpy()))
    )
    g = g.with_columns(
        (_win("m_cap", MOV_N) / _cnt(MOV_N)).alias("mov"),
        (_win("sow_g", SOW_N) / _cnt(SOW_N)).alias("sow"),
        (_win("cw", LUCK_N) - _win("cl", LUCK_N)).alias("luck"),
    )
    return _asof(snap, g, GAME_FACTORS)


def _sim_columns(snap: pl.DataFrame, sim: pl.DataFrame | None, vegas: pl.DataFrame | None) -> pl.DataFrame:
    if sim is None:
        return snap.with_columns(
            pl.lit(0.0).alias("playoff_prob"), pl.lit(0.0).alias("exp_wins"),
            pl.lit(None, pl.Float64).alias("exp_total"), pl.lit(None, pl.String).alias("expectation_source"),
            pl.lit(0.0).alias("vs_exp"), pl.lit(0.0).alias("po_trend"),
        )
    s = sim.select(
        pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32), "franchise_id",
        pl.col("playoff_prob").cast(pl.Float64), pl.col("exp_wins").cast(pl.Float64),
    )
    lag = s.select(
        "season", "franchise_id", pl.col("week").alias("lag_week"), pl.col("playoff_prob").alias("_p_lag"),
    )
    return (
        snap.join(s, on=["season", "week", "franchise_id"], how="left")
        .with_columns((pl.col("week") - PO_LAG).clip(lower_bound=0).cast(pl.Int32).alias("lag_week"))
        .join(lag, on=["season", "franchise_id", "lag_week"], how="left")
        # raw sim values; a missing current or lagged value -> 0.0 (CONTEXT MODEL-12)
        .with_columns((pl.col("playoff_prob") - pl.col("_p_lag")).fill_null(0.0).alias("po_trend"))
        .drop("lag_week", "_p_lag")
        .with_columns(pl.col("playoff_prob").fill_null(0.0), pl.col("exp_wins").fill_null(0.0))
        .join(expectation.expectations(sim, vegas), on=["season", "franchise_id"], how="left")
        .with_columns(_vs_exp())
    )


def _vs_exp() -> pl.Expr:
    gp = (pl.col("wins") + pl.col("losses") + pl.col("ties")).cast(pl.Float64)
    ng = pl.col("season").map_elements(lambda s: float(reg_games(s)), return_dtype=pl.Float64)
    pace = pl.col("exp_total") / ng * gp
    return (
        ((pl.col("wins") + 0.5 * pl.col("ties")) - pace) / pl.max_horizontal(gp, pl.lit(1.0))
    ).fill_null(0.0).alias("vs_exp")


def build_features(
    snapshots: pl.DataFrame, team_games: pl.DataFrame, *, pbp_games: pl.DataFrame | None = None,
    sim: pl.DataFrame | None = None, vegas: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """Snapshot rows (same height and keys) plus season_record, last16, pd_pg, the game factors,
    the pbp factors (0.0 when pbp_games, the pbp.team_game_epa frame, is None) and the sim columns
    (sim = fgs.sim.simulate_all frame, vegas = expectation.vegas_expectations frame)."""
    snap = snapshots.with_columns(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32))
    snap = snap.with_columns(pl.col("win_pct").fill_null(0.5).cast(pl.Float64).alias("season_record"))
    snap = _last16(snap, team_games)
    snap = _pd_pg(snap, team_games)
    snap = _game_factors(snap, team_games)
    if pbp_games is None:
        snap = snap.with_columns(
            pl.lit(0.0).alias("epa_traj"), pl.lit(0.0).alias("qb_trend"),
            pl.lit(None, pl.String).alias("qb_name"), pl.lit(False).alias("qb_new"),
        )
    else:
        snap = efficiency.epa_factors(snap, team_games, pbp_games)
    snap = _sim_columns(snap, sim, vegas)
    return snap.sort("season", "week", "franchise_id")

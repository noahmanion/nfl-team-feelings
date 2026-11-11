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
"""

import polars as pl

from fgs.season_config import MEAN_ELO, hfa_for

FEATURE_COLUMNS = ["elo", "season_record", "last16", "pd_pg", "mov"]
GAME_FACTORS = ["mov"]
LAST_N = 16
MOV_N, MOV_CAP = 8, 24


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
        .with_columns((pl.col("outcome").cast(pl.Float64) - pl.col("p_avg")).alias("sow_g"))
        .sort("franchise_id", "key", "game_id")
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


def _game_factors(snap: pl.DataFrame, team_games: pl.DataFrame) -> pl.DataFrame:
    g = _per_game(team_games).with_columns(
        (_win("m_cap", MOV_N) / _cnt(MOV_N)).alias("mov"),
    )
    return _asof(snap, g, GAME_FACTORS)


def build_features(snapshots: pl.DataFrame, team_games: pl.DataFrame) -> pl.DataFrame:
    """Snapshot rows (same height and keys) plus season_record, last16, pd_pg and the game factors. No nulls added."""
    snap = snapshots.with_columns(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32))
    snap = snap.with_columns(pl.col("win_pct").fill_null(0.5).cast(pl.Float64).alias("season_record"))
    snap = _last16(snap, team_games)
    snap = _pd_pg(snap, team_games)
    snap = _game_factors(snap, team_games)
    return snap.sort("season", "week", "franchise_id")

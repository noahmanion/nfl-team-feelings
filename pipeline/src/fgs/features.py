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
"""

import polars as pl

FEATURE_COLUMNS = ["elo", "season_record", "last16", "pd_pg"]
LAST_N = 16


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


def build_features(snapshots: pl.DataFrame, team_games: pl.DataFrame) -> pl.DataFrame:
    """Snapshot rows (same height and keys) plus season_record, last16, pd_pg. No nulls added."""
    snap = snapshots.with_columns(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32))
    snap = snap.with_columns(pl.col("win_pct").fill_null(0.5).cast(pl.Float64).alias("season_record"))
    snap = _last16(snap, team_games)
    snap = _pd_pg(snap, team_games)
    return snap.sort("season", "week", "franchise_id")

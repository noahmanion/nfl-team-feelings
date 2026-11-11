"""(season, week, franchise) grid: Elo after all games with week <= w, plus REG-only W-L-T."""

import polars as pl

SNAPSHOT_COLUMNS = ["season", "week", "franchise_id", "elo", "wins", "losses", "ties", "win_pct"]


def build_grid(games_with_elo: pl.DataFrame, team_games: pl.DataFrame, sparse: pl.DataFrame) -> pl.DataFrame:
    keys = ["season", "week", "franchise_id"]
    # Last *played* week per season (not last scheduled), so the current season ends at the latest result.
    wk = "asof_week" if "asof_week" in games_with_elo.columns else "week"
    wmax = (
        games_with_elo.filter(pl.col("played"))
        .group_by("season")
        .agg(pl.col(wk).max().cast(pl.Int32).alias("wmax"))
    )
    teams = team_games.select("season", "franchise_id").unique()
    grid = (
        teams.join(wmax, on="season")
        .with_columns(pl.int_ranges(0, pl.col("wmax") + 1).alias("week"))
        .explode("week")
        .drop("wmax")
        .with_columns(pl.col("week").cast(pl.Int32), pl.col("season").cast(pl.Int32))
    )
    sparse = (
        sparse.with_columns(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32))
        .group_by(keys, maintain_order=True)
        .last()
    )
    # Records are keyed by asof_week (the week a result became known), matching the Elo keys.
    asof = pl.col("asof_week") if "asof_week" in team_games.columns else pl.col("week")
    reg = (
        team_games.filter(pl.col("is_reg") & pl.col("played"))
        .with_columns(asof.alias("week"))
        .group_by(keys)
        .agg(
            (pl.col("outcome") == 1.0).sum().alias("w"),
            (pl.col("outcome") == 0.0).sum().alias("l"),
            (pl.col("outcome") == 0.5).sum().alias("t"),
        )
        .sort(keys)
        .with_columns(
            pl.col(c).cum_sum().over("franchise_id", "season").alias(n)
            for c, n in (("w", "wins"), ("l", "losses"), ("t", "ties"))
        )
        .select(
            pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32), "franchise_id",
            "wins", "losses", "ties",
        )
    )
    snap = (
        grid.join(sparse, on=keys, how="left")
        .join(reg, on=keys, how="left")
        .sort("franchise_id", "season", "week")
        .with_columns(
            pl.col(c).forward_fill().over("franchise_id", "season")
            for c in ("elo", "wins", "losses", "ties")
        )
        .with_columns(pl.col(c).fill_null(0).cast(pl.Int32) for c in ("wins", "losses", "ties"))
    )
    n = pl.col("wins") + pl.col("losses") + pl.col("ties")
    snap = snap.with_columns(
        pl.when(n > 0).then((pl.col("wins") + 0.5 * pl.col("ties")) / n).otherwise(None).alias("win_pct")
    )
    return snap.select(SNAPSHOT_COLUMNS).sort("season", "week", "franchise_id")

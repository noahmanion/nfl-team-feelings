"""pbp efficiency factors: epa_traj (opponent-adjusted EPA trajectory) and qb_trend (current QB form).

Pure: no file I/O. Inputs are team_games (fgs.games) and the pbp.team_game_epa frame. Every
value at a snapshot (season, week) uses only games with asof_week <= week. This module must
stay independent of the dev-only evaluation harness (leakage firewall) and of fgs.features
(features imports this module, not the other way round).

- epa_traj: per played team-game with pbp (inner join; a game without pbp is absent from the
  sequence, not 0), adj_epa = net_epa + opp_prior_net, where opp_prior_net is the opponent's
  EWMA (half-life 4 games) of its raw net_epa over its games strictly before this one (crossing
  seasons; none -> 0). epa_traj = EWMA_h4(adj_epa) over the franchise's games (crossing seasons)
  minus the season-to-date mean of adj_epa. A snapshot with no game yet this season -> 0.0.
"""

import polars as pl

EPA_HALF_LIFE = 4
OPP_HALF_LIFE = 4


def _key(week_col: str) -> pl.Expr:
    return (pl.col("season").cast(pl.Int64) * 100 + pl.col(week_col).cast(pl.Int64)).alias("key")


def per_game(team_games: pl.DataFrame, tge: pl.DataFrame) -> pl.DataFrame:
    """Played team-games with pbp, in as-of order, plus opp_prior_net, adj_epa and epa_traj."""
    played = team_games.filter(pl.col("played"))
    cols = [c for c in tge.columns if c not in ("season",)]
    g = (
        played.join(tge.select(cols), on=["game_id", "franchise_id"], how="inner")
        .filter(pl.col("net_epa").is_not_null())
        .with_columns(_key("asof_week"))
        .sort("franchise_id", "key", "game_id")
        .with_columns(
            pl.col("net_epa").ewm_mean(half_life=OPP_HALF_LIFE, adjust=True).shift(1).over("franchise_id")
            .alias("prior_net")
        )
    )
    opp = g.select("game_id", pl.col("franchise_id").alias("opponent_id"), pl.col("prior_net").alias("opp_prior_net"))
    g = (
        g.join(opp, on=["game_id", "opponent_id"], how="left")
        .with_columns((pl.col("net_epa") + pl.col("opp_prior_net").fill_null(0.0)).alias("adj_epa"))
        .sort("franchise_id", "key", "game_id")
    )
    smean = pl.col("adj_epa").cum_sum().over("franchise_id", "season") / pl.int_range(1, pl.len() + 1).over(
        "franchise_id", "season"
    )
    return g.with_columns(
        (pl.col("adj_epa").ewm_mean(half_life=EPA_HALF_LIFE, adjust=True).over("franchise_id") - smean).alias(
            "epa_traj"
        )
    )


def epa_factors(snap: pl.DataFrame, team_games: pl.DataFrame, tge: pl.DataFrame) -> pl.DataFrame:
    """snap + epa_traj (as of each snapshot; same rows, no nulls)."""
    g = per_game(team_games, tge)
    last = (
        g.group_by("franchise_id", "key", maintain_order=True)
        .last()
        .select("franchise_id", "key", pl.col("season").cast(pl.Int32).alias("g_season"), "epa_traj")
        .sort("key")
    )
    out = (
        snap.with_columns(_key("week"))
        .sort("key")
        .join_asof(last, on="key", by="franchise_id", strategy="backward", check_sortedness=False)
    )
    return out.with_columns(
        pl.when(pl.col("g_season") == pl.col("season")).then(pl.col("epa_traj").fill_null(0.0))
        .otherwise(0.0).cast(pl.Float64).alias("epa_traj")
    ).drop("key", "g_season")

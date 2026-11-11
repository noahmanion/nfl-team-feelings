"""Backtest harness: the locked target, metrics, and walk-forward baselines.

DEV-ONLY. This module looks at *future* games (the target is the next N games), so it must
never be imported by features.py or score.py. That one-way dependency is the leakage firewall:
backtest -> features is fine, features/score -> backtest is not.

Target (README "Backtest target"): mean adjusted margin over a team's next N games in the
same season (REG + playoffs). Adjusted margin = margin + (opp_elo_pre - 1505)/25 - hfa_signed/25.
Only opponent strength and venue are adjusted for, never the team's own rating.
"""

import numpy as np
import polars as pl

from fgs.season_config import MEAN_ELO, hfa_for

KEYS = ["season", "week", "franchise_id"]


def _hfa_table(seasons) -> pl.DataFrame:
    seasons = sorted({int(s) for s in seasons})
    return pl.DataFrame(
        {"season": seasons, "hfa": [hfa_for(s) for s in seasons]},
        schema={"season": pl.Int32, "hfa": pl.Float64},
    )


def adjusted_margins(team_games: pl.DataFrame) -> pl.DataFrame:
    """One row per played team-game with its opponent- and venue-adjusted margin (`adj`)."""
    played = team_games.filter(pl.col("played")).with_columns(pl.col("season").cast(pl.Int32))
    opp = played.select(
        "game_id", pl.col("franchise_id").alias("opponent_id"), pl.col("elo_pre").alias("opp_elo_pre")
    )
    return (
        played.join(opp, on=["game_id", "opponent_id"], how="left")
        .join(_hfa_table(played["season"].unique().to_list()), on="season", how="left")
        .with_columns(
            (pl.col("points_for") - pl.col("points_against")).cast(pl.Float64).alias("margin"),
            pl.when(pl.col("neutral")).then(0.0)
            .when(pl.col("is_home")).then(pl.col("hfa"))
            .otherwise(-pl.col("hfa")).alias("hfa_s"),
        )
        .with_columns(
            # margin - expected margin of a league-average (1505) team vs this opponent at this venue
            (pl.col("margin") - (MEAN_ELO - pl.col("opp_elo_pre") + pl.col("hfa_s")) / 25).alias("adj")
        )
        .select(
            "season", pl.col("asof_week").cast(pl.Int32), "franchise_id", "game_id",
            "margin", "opp_elo_pre", "hfa_s", "adj",
        )
        .sort("franchise_id", "season", "asof_week", "game_id")
    )


def targets(team_games: pl.DataFrame, snapshots: pl.DataFrame, ns=(4, 8)) -> pl.DataFrame:
    """Per snapshot (season, week, franchise): y{N} = mean adj over the next min(N, remaining)
    same-season games with asof_week > week; null when fewer than 2 remain."""
    am = adjusted_margins(team_games).with_row_index("gidx")
    # Global cumulative sum with a leading 0: sum of rows [a, b) = C[b] - C[a].
    C = np.concatenate([[0.0], np.cumsum(am["adj"].to_numpy())])

    team_season = am.group_by("franchise_id", "season").agg(
        pl.col("gidx").min().alias("off"), pl.len().alias("ntot")
    )
    # Number of games played with asof_week <= w, per (team, season, w) where it changes.
    done = (
        am.group_by("franchise_id", "season", "asof_week")
        .agg(pl.len().alias("c"))
        .sort("franchise_id", "season", "asof_week")
        .with_columns(pl.col("c").cum_sum().over("franchise_id", "season").alias("k"))
        .select("franchise_id", "season", pl.col("asof_week").alias("week"), "k")
    )
    s = (
        snapshots.select(KEYS)
        .with_columns(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32))
        .sort("week")
        .join_asof(done.sort("week"), on="week", by=["franchise_id", "season"], strategy="backward",
                   check_sortedness=False)
        .join(team_season, on=["franchise_id", "season"], how="left")
        .with_columns(pl.col("k").fill_null(0), pl.col("ntot").fill_null(0), pl.col("off").fill_null(0))
    )
    k = s["k"].to_numpy().astype(np.int64)
    ntot = s["ntot"].to_numpy().astype(np.int64)
    off = s["off"].to_numpy().astype(np.int64)
    cols = []
    for n in ns:
        m = np.minimum(n, ntot - k)
        ok = m >= 2
        start = off + k
        end = start + np.where(ok, m, 0)
        val = np.full(len(s), np.nan)
        val[ok] = (C[end[ok]] - C[start[ok]]) / m[ok]
        cols.append(pl.Series(f"y{n}", val, dtype=pl.Float64).fill_nan(None))
    return s.select(KEYS).with_columns(cols).sort(KEYS)

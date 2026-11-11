"""Derived game tables. Team identity always comes from home_team/away_team, never game_id."""

import polars as pl

from fgs.franchises import RAW_TO_FRANCHISE, unknown_codes

GAME_COLUMNS = [
    "game_id", "season", "week", "game_type", "gameday", "gametime",
    "raw_home", "raw_away", "home_id", "away_id", "home_score", "away_score",
    "result", "neutral", "played", "is_reg", "div_game", "spread_line",
    "home_qb_id", "home_qb_name", "away_qb_id", "away_qb_name",
]
SORT_KEYS = ["season", "week", "gameday", "gametime", "game_id"]


def build_games(raw: pl.DataFrame) -> pl.DataFrame:
    bad = unknown_codes(raw)
    if bad:
        raise ValueError(f"unknown team codes in schedules: {sorted(bad)}")
    games = raw.with_columns(
        pl.col("home_team").alias("raw_home"),
        pl.col("away_team").alias("raw_away"),
        pl.col("home_team").replace(RAW_TO_FRANCHISE).alias("home_id"),
        pl.col("away_team").replace(RAW_TO_FRANCHISE).alias("away_id"),
        (pl.col("location") == "Neutral").fill_null(False).alias("neutral"),
        pl.col("result").is_not_null().alias("played"),
        (pl.col("game_type") == "REG").alias("is_reg"),
    )
    # Optional columns: keep schema stable even if a slim raw frame is passed in.
    missing = [c for c in GAME_COLUMNS if c not in games.columns]
    games = games.with_columns(pl.lit(None).alias(c) for c in missing)
    return games.select(GAME_COLUMNS).sort(SORT_KEYS, nulls_last=True)


def _outcome(margin: pl.Expr) -> pl.Expr:
    return (
        pl.when(margin > 0).then(1.0)
        .when(margin < 0).then(0.0)
        .when(margin == 0).then(0.5)
        .otherwise(None)
    )


def build_team_games(games: pl.DataFrame) -> pl.DataFrame:
    """Two rows per game, one from each team's perspective."""
    has_elo = "elo_pre_home" in games.columns

    def side(home: bool) -> pl.DataFrame:
        me, opp = ("home", "away") if home else ("away", "home")
        margin = pl.col("result") if home else -pl.col("result")
        elo_pre = pl.col(f"elo_pre_{me}") if has_elo else pl.lit(None, pl.Float64)
        elo_post = pl.col(f"elo_post_{me}") if has_elo else pl.lit(None, pl.Float64)
        return games.select(
            "game_id", "season", "week", "game_type", "is_reg",
            pl.col(f"{me}_id").alias("franchise_id"),
            pl.col(f"{opp}_id").alias("opponent_id"),
            pl.lit(home).alias("is_home"),
            "neutral", "played",
            pl.col(f"{me}_score").alias("points_for"),
            pl.col(f"{opp}_score").alias("points_against"),
            _outcome(margin).cast(pl.Float64).alias("outcome"),
            elo_pre.cast(pl.Float64).alias("elo_pre"),
            elo_post.cast(pl.Float64).alias("elo_post"),
        )

    return pl.concat([side(True), side(False)]).sort(
        "season", "week", "game_id", "is_home", descending=[False, False, False, True]
    )

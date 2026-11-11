"""As-of helpers over the derived games frame: latest played week, data-through date, week progress."""

import polars as pl


def latest_played(games: pl.DataFrame, season: int | None = None) -> tuple[int, int] | None:
    """(season, week) of the latest played game, from cached data only (D-24)."""
    played = games.filter(pl.col("played"))
    if season is not None:
        played = played.filter(pl.col("season") == season)
    if played.is_empty():
        return None
    s = played["season"].max() if season is None else season
    return int(s), int(played.filter(pl.col("season") == s)["week"].max())


def data_through(games: pl.DataFrame, season: int, week: int) -> str:
    """Max gameday among played games at or before (season, week)."""
    played = games.filter(
        pl.col("played")
        & ((pl.col("season") < season) | ((pl.col("season") == season) & (pl.col("week") <= week)))
    )
    return str(played["gameday"].max()) if not played.is_empty() else "n/a"


def week_progress(games: pl.DataFrame, season: int, week: int) -> tuple[int, int]:
    """(played, total) games in one (season, week)."""
    wk = games.filter((pl.col("season") == season) & (pl.col("week") == week))
    return int(wk["played"].sum()), wk.height

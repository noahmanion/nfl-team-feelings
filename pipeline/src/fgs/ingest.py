"""Raw nflverse pulls, cached as parquet we own (not nflreadpy's 24h cache)."""

from pathlib import Path

import polars as pl

from fgs.paths import CACHE_DIR


def load_schedules(refresh: bool = False, cache_dir: Path = CACHE_DIR) -> pl.DataFrame:
    """All seasons of schedules/results. Reads the cache unless missing or refresh=True."""
    path = Path(cache_dir) / "schedules.parquet"
    if path.exists() and not refresh:
        return pl.read_parquet(path)

    import nflreadpy
    from nflreadpy.config import update_config

    update_config(cache_mode="off")  # we own the cache; avoid nflreadpy's memory/fs cache
    df = nflreadpy.load_schedules()  # no args = every season, one file
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(path)
    return df


def load_teams(refresh: bool = False, cache_dir: Path = CACHE_DIR) -> pl.DataFrame:
    """Team names/colors (current franchises plus legacy rows). Reads the cache unless missing or refresh=True."""
    path = Path(cache_dir) / "teams.parquet"
    if path.exists() and not refresh:
        return pl.read_parquet(path)

    import nflreadpy
    from nflreadpy.config import update_config

    update_config(cache_mode="off")
    df = nflreadpy.load_teams()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(path)
    return df

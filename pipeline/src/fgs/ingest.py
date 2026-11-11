"""Raw nflverse pulls, cached as parquet we own (not nflreadpy's 24h cache)."""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import polars as pl

from fgs.paths import CACHE_DIR


@contextmanager
def nflreadpy_uncached() -> Iterator[None]:
    """Turn nflreadpy's own cache off for one download, then restore the caller's setting (IN-05):
    we own the cache, but must not change process-wide nflreadpy state."""
    from nflreadpy.config import get_config, update_config

    prev = get_config().cache_mode
    update_config(cache_mode="off")
    try:
        yield
    finally:
        update_config(cache_mode=prev)


def save_cache(df: pl.DataFrame, name: str, cache_dir: Path = CACHE_DIR) -> None:
    """Write one raw cache file, via a temp file + rename so a crash never leaves it half-written."""
    path = Path(cache_dir) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    df.write_parquet(tmp)
    os.replace(tmp, path)


def load_schedules(refresh: bool = False, cache_dir: Path = CACHE_DIR, write_cache: bool = True) -> pl.DataFrame:
    """All seasons of schedules/results. Reads the cache unless missing or refresh=True.

    write_cache=False downloads without touching the cache (refresh checks first, then saves).
    """
    path = Path(cache_dir) / "schedules.parquet"
    if path.exists() and not refresh:
        return pl.read_parquet(path)

    import nflreadpy

    with nflreadpy_uncached():  # we own the cache; avoid nflreadpy's memory/fs cache
        df = nflreadpy.load_schedules()  # no args = every season, one file
    if write_cache:
        save_cache(df, "schedules.parquet", cache_dir)
    return df


def load_teams(refresh: bool = False, cache_dir: Path = CACHE_DIR, write_cache: bool = True) -> pl.DataFrame:
    """Team names/colors (current franchises plus legacy rows). Reads the cache unless missing or refresh=True."""
    path = Path(cache_dir) / "teams.parquet"
    if path.exists() and not refresh:
        return pl.read_parquet(path)

    import nflreadpy

    with nflreadpy_uncached():
        df = nflreadpy.load_teams()
    if write_cache:
        save_cache(df, "teams.parquet", cache_dir)
    return df

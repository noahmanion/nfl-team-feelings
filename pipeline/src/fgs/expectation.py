"""Preseason expectations per team-season (MODEL-08 input).

Source per team-season:
  vegas  nflverse win_totals (2003-2020), normalized per season so the league mean is
         reg_games/2: vegas_norm = line - mean(line over season) + reg_games(season)/2
  model  the simulator's week-0 exp_wins, everywhere else

Caveat (RESEARCH Pitfall 1): the Vegas signal covers 2003-2020 only. 2021+ (the 2022-2025
holdout and the live season) is always model-sourced. Hand-entered 2021+ totals are
deferred (v2). Flag for Phase 6: a weight learned mostly on Vegas rows is applied to
model rows at deployment.

load_win_totals does I/O (one cached CSV); the other functions are pure.
"""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path

import polars as pl

from fgs.franchises import RAW_TO_FRANCHISE
from fgs.paths import CACHE_DIR
from fgs.season_config import reg_games

WIN_TOTALS_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/win_totals.csv"


def load_win_totals(refresh: bool = False, cache_dir: Path = CACHE_DIR) -> pl.DataFrame:
    """nflverse win totals (season, team, line, over_odds, under_odds). Frozen file: downloaded
    once into the cache and only re-fetched with refresh=True."""
    path = Path(cache_dir) / "win_totals.csv"
    if refresh or not path.exists():
        with urllib.request.urlopen(WIN_TOTALS_URL, timeout=30) as r:
            data = r.read()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)
    return pl.read_csv(path)


def vegas_expectations(wt: pl.DataFrame) -> pl.DataFrame:
    """Map legacy codes (OAK/SD/STL) to franchises and normalize lines per season."""
    out = wt.select(
        pl.col("season").cast(pl.Int32),
        pl.col("team").replace(RAW_TO_FRANCHISE).alias("franchise_id"),
        pl.col("line").cast(pl.Float64).alias("vegas_line"),
    )
    half = out["season"].map_elements(lambda s: reg_games(s) / 2, return_dtype=pl.Float64)
    return (
        out.with_columns(half.alias("_half"))
        .with_columns(
            (pl.col("vegas_line") - pl.col("vegas_line").mean().over("season") + pl.col("_half")).alias("vegas_norm")
        )
        .drop("_half")
        .sort("season", "franchise_id")
    )


def expectations(sim: pl.DataFrame, vegas: pl.DataFrame | None = None) -> pl.DataFrame:
    """One row per (season, franchise_id) in sim week 0: exp_total + expectation_source."""
    w0 = sim.filter(pl.col("week") == 0).select(
        pl.col("season").cast(pl.Int32), "franchise_id", pl.col("exp_wins").cast(pl.Float64)
    )
    if vegas is None:
        v = pl.DataFrame(schema={"season": pl.Int32, "franchise_id": pl.String, "vegas_norm": pl.Float64})
    else:
        v = vegas.select(pl.col("season").cast(pl.Int32), "franchise_id", "vegas_norm")
    j = w0.join(v, on=["season", "franchise_id"], how="left")
    return j.select(
        "season",
        "franchise_id",
        pl.coalesce("vegas_norm", "exp_wins").alias("exp_total"),
        pl.when(pl.col("vegas_norm").is_not_null()).then(pl.lit("vegas")).otherwise(pl.lit("model")).alias("expectation_source"),
    ).sort("season", "franchise_id")

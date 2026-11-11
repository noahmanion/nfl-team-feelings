"""Play-by-play: slim per-season cache (I/O) and per-team-game EPA aggregates (pure)."""

from collections.abc import Iterable
from datetime import timedelta
from pathlib import Path

import polars as pl

from fgs.franchises import CANONICAL, RAW_TO_FRANCHISE
from fgs.ingest import save_cache
from fgs.paths import CACHE_DIR

SLIM_COLUMNS = [
    "game_id", "season", "week", "season_type", "posteam", "defteam", "play_type",
    "pass", "rush", "qb_dropback", "qb_kneel", "qb_spike", "epa", "wp", "success",
    "passer_id", "passer", "passer_player_id", "passer_player_name", "rusher_player_id",
]
WP_LO, WP_HI = 0.05, 0.95  # garbage-time filter (inclusive)
LOW_CONFIDENCE_LAST = 2000  # 1999-2000 pbp is thinner (null qb_dropback, missing games)
KNOWN_NO_PBP = frozenset({"1999_01_BAL_STL", "2000_03_SD_KC", "2000_06_BUF_MIA"})
PBP_SUBDIR = "pbp"

TGE_COLUMNS = [
    "game_id", "season", "franchise_id", "off_epa", "off_plays", "off_sr", "def_epa", "def_plays",
    "net_epa", "team_db", "team_db_epa_sum", "qb_id", "qb_name", "dropbacks", "qb_epa", "qb_sr",
    "low_confidence",
]


def cached_seasons(cache_dir: Path = CACHE_DIR) -> list[int]:
    """Seasons with a slim pbp parquet in the cache, ascending."""
    d = Path(cache_dir) / PBP_SUBDIR
    if not d.is_dir():
        return []
    return sorted(int(p.stem) for p in d.glob("*.parquet") if p.stem.isdigit())


def load_pbp_season(
    season: int, refresh: bool = False, cache_dir: Path = CACHE_DIR, write_cache: bool = True
) -> pl.DataFrame:
    """One season of slim pbp. Reads the cache unless missing or refresh=True.

    write_cache=False downloads without touching the cache (refresh checks first, then saves).
    """
    path = Path(cache_dir) / PBP_SUBDIR / f"{season}.parquet"
    if path.exists() and not refresh:
        return pl.read_parquet(path)

    import nflreadpy
    from nflreadpy.config import update_config

    update_config(cache_mode="off")  # we own the cache
    df = nflreadpy.load_pbp(season).select(SLIM_COLUMNS)
    if write_cache:
        save_cache(df, f"{PBP_SUBDIR}/{season}.parquet", cache_dir)
    return df


def load_all_pbp(
    seasons: Iterable[int], cache_dir: Path = CACHE_DIR, refresh_seasons: Iterable[int] = (),
    write_cache: bool = True,
) -> pl.DataFrame:
    """Concat slim pbp over seasons (downloading any missing; re-downloading refresh_seasons)."""
    refresh = set(refresh_seasons)
    frames = [
        load_pbp_season(s, refresh=s in refresh, cache_dir=cache_dir, write_cache=write_cache)
        for s in seasons
    ]
    if not frames:
        return pl.DataFrame()
    return pl.concat(frames, how="diagonal_relaxed")


def scrimmage(p: pl.DataFrame) -> pl.DataFrame:
    """Garbage-time-filtered scrimmage plays, with franchise codes, qb_id and qb_name."""
    return p.filter(
        ((pl.col("pass") == 1) | (pl.col("rush") == 1))
        & (pl.col("qb_kneel").fill_null(0) == 0)
        & (pl.col("qb_spike").fill_null(0) == 0)  # spikes have pass=1
        & (pl.col("play_type").fill_null("") != "no_play")
        & pl.col("epa").is_not_null()
        & pl.col("posteam").is_not_null() & (pl.col("posteam") != "")
        & pl.col("wp").is_between(WP_LO, WP_HI)
    ).with_columns(
        pl.col("posteam").replace(RAW_TO_FRANCHISE),
        pl.col("defteam").replace(RAW_TO_FRANCHISE),
        pl.col("qb_dropback").fill_null(0),  # null dropback (1999-2000) = not a dropback
    ).with_columns(
        # passer_player_id is null on scrambles; nflfastR's passer_id includes them
        pl.coalesce(
            "passer_id", "passer_player_id",
            pl.when(pl.col("qb_dropback") == 1).then(pl.col("rusher_player_id")),
        ).alias("qb_id"),
        pl.coalesce("passer", "passer_player_name").alias("qb_name"),
    )


def team_game_epa(p: pl.DataFrame) -> pl.DataFrame:
    """Slim pbp -> one row per (game_id, franchise_id): off/def/net EPA per play + primary QB."""
    s = scrimmage(p)
    bad = (set(s["posteam"].drop_nulls()) | set(s["defteam"].drop_nulls())) - CANONICAL
    if bad:
        raise ValueError(f"unknown team codes in pbp: {sorted(bad)}")
    s = s.with_columns(pl.col("season").cast(pl.Int32))
    off = s.group_by("game_id", "season", pl.col("posteam").alias("franchise_id")).agg(
        pl.col("epa").mean().alias("off_epa"), pl.len().alias("off_plays"),
        pl.col("success").mean().alias("off_sr"))
    dfn = s.group_by("game_id", "season", pl.col("defteam").alias("franchise_id")).agg(
        pl.col("epa").mean().alias("def_epa"), pl.len().alias("def_plays"))
    db = s.filter(pl.col("qb_dropback") == 1)
    team_db = db.group_by("game_id", pl.col("posteam").alias("franchise_id")).agg(
        pl.len().alias("team_db"), pl.col("epa").sum().alias("team_db_epa_sum"))
    qb = (
        db.filter(pl.col("qb_id").is_not_null())
        .group_by("game_id", pl.col("posteam").alias("franchise_id"), "qb_id")
        .agg(pl.len().alias("dropbacks"), pl.col("epa").mean().alias("qb_epa"),
             pl.col("success").mean().alias("qb_sr"),
             pl.col("qb_name").drop_nulls().first().alias("qb_name"))
        .sort("game_id", "franchise_id", "dropbacks", "qb_id", descending=[False, False, True, False])
        .group_by("game_id", "franchise_id", maintain_order=True).first()  # ties -> lowest id
    )
    out = (
        off.join(dfn, on=["game_id", "season", "franchise_id"], how="full", coalesce=True)
        .join(team_db, on=["game_id", "franchise_id"], how="left")
        .join(qb, on=["game_id", "franchise_id"], how="left")
        .with_columns(
            (pl.col("off_epa") - pl.col("def_epa")).alias("net_epa"),
            (pl.col("season") <= LOW_CONFIDENCE_LAST).alias("low_confidence"),
            pl.col("off_plays").cast(pl.Int64), pl.col("def_plays").cast(pl.Int64),
            pl.col("team_db").cast(pl.Int64), pl.col("dropbacks").cast(pl.Int64),
        )
    )
    return out.select(TGE_COLUMNS).sort("game_id", "franchise_id")


PBP_LAG_DAYS = 3  # nflverse posts schedule results hours to days before the pbp release is rebuilt


def _missing_pbp(tge: pl.DataFrame, team_games: pl.DataFrame) -> tuple[list[str], list[str]]:
    """Played games without pbp (minus KNOWN_NO_PBP), split into (hard gaps, lagging).

    Lagging (WR-02) = a current-season game (the latest season with a played game) played within
    PBP_LAG_DAYS of that season's latest played gameday, or any current-season game when the
    pbp has no current-season games at all (release not posted yet). The window is relative to
    the data, not the wall clock, so the split is reproducible. team_games without season/gameday
    columns (synthetic frames) treat every gap as hard."""
    played_tg = team_games.filter(pl.col("played"))
    played = set(played_tg["game_id"].to_list())
    have = set(tge["game_id"].to_list())
    missing = played - have - KNOWN_NO_PBP
    lag: set[str] = set()
    if missing and {"season", "gameday"} <= set(played_tg.columns):
        g = played_tg.select("game_id", "season", pl.col("gameday").cast(pl.String).str.to_date(strict=False))
        current = g["season"].max()
        cur = g.filter(pl.col("season") == current)
        cur_ids = set(cur["game_id"].to_list())
        if not cur_ids & have:
            lag = missing & cur_ids
        else:
            latest = cur["gameday"].max()
            if latest is not None:
                lo = latest - timedelta(days=PBP_LAG_DAYS)
                lag = missing & set(cur.filter(pl.col("gameday") >= lo)["game_id"].to_list())
    return sorted(missing - lag), sorted(lag)


def check_pbp(tge: pl.DataFrame, team_games: pl.DataFrame) -> list[str]:
    """Coverage: every played game has pbp (except KNOWN_NO_PBP and the lagging current-season
    games reported by pbp_lag), every pbp game is a played schedule game, and every pbp
    team-game has both an offense and a defense EPA."""
    out: list[str] = []
    played = set(team_games.filter(pl.col("played"))["game_id"].to_list())
    have = set(tge["game_id"].to_list())
    hard, _ = _missing_pbp(tge, team_games)
    for g in hard:
        out.append(f"{g}: played game has no pbp")
    for g in sorted(have - played):
        out.append(f"{g}: pbp game is not a played schedule game")
    nulls = tge.filter(pl.col("off_epa").is_null() | pl.col("def_epa").is_null())
    for g, t in nulls.select("game_id", "franchise_id").head(10).iter_rows():
        out.append(f"{g} {t}: null off_epa or def_epa")
    if nulls.height > 10:
        out.append(f"... {nulls.height} team-games with null off/def EPA in total")
    return out


def pbp_lag(tge: pl.DataFrame, team_games: pl.DataFrame) -> list[str]:
    """Warnings (never failures): recent current-season games whose pbp is not released yet.
    Their efficiency factors use the pbp that is available (a game without pbp is absent from
    the EPA sequence, not 0) until a later refresh picks the pbp up."""
    _, lag = _missing_pbp(tge, team_games)
    return [f"{g}: played game has no pbp yet (pbp release lags the schedule)" for g in lag]

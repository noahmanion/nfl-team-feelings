import polars as pl
import pytest

from fgs.paths import CACHE_DIR

# (game_id, season, week, game_type, gameday, home_id, away_id, home_score, away_score, neutral)
_ROWS = [
    ("2023_01_MIA_BUF", 2023, 1, "REG", "2023-09-10", "BUF", "MIA", 24, 17, False),
    ("2023_01_NYJ_NE", 2023, 1, "REG", "2023-09-10", "NE", "NYJ", 10, 10, False),  # tie
    ("2023_02_NE_MIA", 2023, 2, "REG", "2023-09-17", "MIA", "NE", 20, 13, False),
    ("2023_02_BUF_NYJ", 2023, 2, "REG", "2023-09-17", "NYJ", "BUF", 14, 31, True),  # neutral
    ("2023_03_NYJ_MIA", 2023, 3, "REG", "2023-09-24", "MIA", "NYJ", 27, 3, False),  # BUF, NE bye
    ("2023_19_MIA_BUF", 2023, 19, "WC", "2024-01-14", "BUF", "MIA", 34, 31, False),  # playoff
    ("2024_01_BUF_NYJ", 2024, 1, "REG", "2024-09-08", "NYJ", "BUF", 20, 23, False),
    ("2024_01_NE_MIA", 2024, 1, "REG", "2024-09-08", "MIA", "NE", 17, 24, False),
    ("2024_02_NE_BUF", 2024, 2, "REG", "2024-09-15", "BUF", "NE", None, None, False),  # unplayed
    ("2024_02_MIA_NYJ", 2024, 2, "REG", "2024-09-15", "NYJ", "MIA", 21, 20, False),
]


def make_games(rows) -> pl.DataFrame:
    """Build a frame in the post-normalization games schema from compact tuples."""
    recs = []
    for gid, season, week, gtype, day, h, a, hs, as_, neutral in rows:
        result = None if hs is None else hs - as_
        recs.append(
            dict(
                game_id=gid, season=season, week=week, game_type=gtype, gameday=day,
                gametime="13:00", raw_home=h, raw_away=a, home_id=h, away_id=a,
                home_score=hs, away_score=as_, result=result, neutral=neutral,
                played=result is not None, is_reg=gtype == "REG",
            )
        )
    return pl.DataFrame(
        recs,
        schema={
            "game_id": pl.String, "season": pl.Int32, "week": pl.Int32, "game_type": pl.String,
            "gameday": pl.String, "gametime": pl.String, "raw_home": pl.String,
            "raw_away": pl.String, "home_id": pl.String, "away_id": pl.String,
            "home_score": pl.Int32, "away_score": pl.Int32, "result": pl.Int32,
            "neutral": pl.Boolean, "played": pl.Boolean, "is_reg": pl.Boolean,
        },
    )


@pytest.fixture
def synthetic_games() -> pl.DataFrame:
    """Tiny 2-season league: one tie, one neutral, one unplayed, one playoff, BUF/NE bye in 2023 wk3."""
    return make_games(_ROWS)


@pytest.fixture
def real_cache():
    path = CACHE_DIR / "schedules.parquet"
    if not path.exists():
        pytest.skip("no cached schedules; run `uv run fgs build` first")
    return path

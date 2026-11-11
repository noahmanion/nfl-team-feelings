import polars as pl
import pytest

from conftest import make_games
from fgs.elo import replay
from fgs.features import FEATURE_COLUMNS, build_features
from fgs.games import build_team_games
from fgs.snapshots import SNAPSHOT_COLUMNS, build_grid


def _feats(games: pl.DataFrame) -> pl.DataFrame:
    g, sparse = replay(games)
    tg = build_team_games(g)
    return build_features(build_grid(g, tg, sparse), tg)


def _v(df, season, week, team, col):
    return df.filter(
        (pl.col("season") == season) & (pl.col("week") == week) & (pl.col("franchise_id") == team)
    )[col].item()


def test_season_record_ties_week0_and_playoffs(synthetic_games):
    f = _feats(synthetic_games)
    assert _v(f, 2023, 0, "BUF", "season_record") == 0.5
    assert _v(f, 2024, 0, "NE", "season_record") == 0.5
    assert _v(f, 2023, 1, "NE", "season_record") == 0.5  # tie counts half
    assert _v(f, 2023, 2, "NE", "season_record") == pytest.approx(0.25)
    # MIA 2-1 in REG; the wild-card loss does not move it.
    assert _v(f, 2023, 3, "MIA", "season_record") == pytest.approx(2 / 3)
    assert _v(f, 2023, 19, "MIA", "season_record") == pytest.approx(2 / 3)
    assert _v(f, 2023, 19, "BUF", "season_record") == 1.0


def test_season_record_week1_bye():
    games = make_games([
        ("g1", 2023, 1, "REG", "2023-09-10", "A", "B", 20, 10, False),  # C on bye
        ("g2", 2023, 2, "REG", "2023-09-17", "C", "A", 30, 10, False),
    ])
    f = _feats(games)
    assert _v(f, 2023, 1, "C", "season_record") == 0.5
    assert _v(f, 2023, 2, "C", "season_record") == 1.0
    assert _v(f, 2023, 1, "B", "season_record") == 0.0


def test_last16_crosses_season_boundary_with_playoffs(synthetic_games):
    f = _feats(synthetic_games)
    assert _v(f, 2024, 0, "BUF", "last16") == 1.0
    assert _v(f, 2024, 0, "NE", "last16") == pytest.approx(0.25)       # T, L
    assert _v(f, 2024, 0, "NYJ", "last16") == pytest.approx(0.5 / 3)   # T, L, L
    # MIA: L, W, W in REG plus the playoff L -> 2/4 (would be 2/3 without the playoff game).
    assert _v(f, 2024, 0, "MIA", "last16") == pytest.approx(0.5)
    assert _v(f, 2024, 1, "MIA", "last16") == pytest.approx(2 / 5)


def test_last16_no_prior_games_is_half(synthetic_games):
    f = _feats(synthetic_games)
    for team in ("BUF", "MIA", "NE", "NYJ"):
        assert _v(f, 2023, 0, team, "last16") == 0.5
    assert _v(f, 2023, 1, "BUF", "last16") == 1.0  # one game available -> its outcome


def test_last16_uses_only_latest_16():
    # A wins weeks 1-10, loses weeks 11-20.
    rows = []
    for w in range(1, 21):
        hs, as_ = (20, 10) if w <= 10 else (10, 20)
        rows.append((f"g{w}", 2023, w, "REG", f"2023-09-{w:02d}", "A", "B", hs, as_, False))
    f = _feats(make_games(rows))
    assert _v(f, 2023, 20, "A", "last16") == pytest.approx(6 / 16)
    assert _v(f, 2023, 20, "B", "last16") == pytest.approx(10 / 16)
    assert _v(f, 2023, 12, "A", "last16") == pytest.approx(10 / 12)


def test_pd_pg_hand_computed(synthetic_games):
    f = _feats(synthetic_games)
    assert _v(f, 2023, 0, "BUF", "pd_pg") == 0.0
    assert _v(f, 2023, 2, "BUF", "pd_pg") == pytest.approx((7 + 17) / 2)
    assert _v(f, 2023, 3, "BUF", "pd_pg") == pytest.approx(12.0)   # bye week carries forward
    assert _v(f, 2023, 19, "BUF", "pd_pg") == pytest.approx(12.0)  # playoff excluded
    assert _v(f, 2023, 3, "NYJ", "pd_pg") == pytest.approx((0 - 17 - 24) / 3)


def test_build_features_shape_and_no_nulls(synthetic_games):
    g, sparse = replay(synthetic_games)
    tg = build_team_games(g)
    snap = build_grid(g, tg, sparse)
    f = build_features(snap, tg)
    assert f.height == snap.height
    assert f.select("season", "week", "franchise_id").equals(snap.select("season", "week", "franchise_id"))
    assert set(SNAPSHOT_COLUMNS) | set(FEATURE_COLUMNS) <= set(f.columns)
    for c in ("season_record", "last16", "pd_pg"):
        assert f[c].null_count() == 0
        assert not f[c].is_nan().any()

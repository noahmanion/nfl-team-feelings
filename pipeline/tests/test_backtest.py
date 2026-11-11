import polars as pl
import pytest

from fgs.backtest import adjusted_margins, targets

TG_SCHEMA = {
    "game_id": pl.String, "season": pl.Int32, "week": pl.Int32, "asof_week": pl.Int32,
    "franchise_id": pl.String, "opponent_id": pl.String, "is_home": pl.Boolean, "neutral": pl.Boolean,
    "played": pl.Boolean, "points_for": pl.Int32, "points_against": pl.Int32, "elo_pre": pl.Float64,
}


def _tg(games) -> pl.DataFrame:
    """games: (game_id, season, week, home, away, home_pts, away_pts, neutral, home_elo, away_elo)."""
    recs = []
    for gid, s, w, h, a, hp, ap, neu, he, ae in games:
        played = hp is not None
        recs.append(dict(game_id=gid, season=s, week=w, asof_week=w, franchise_id=h, opponent_id=a,
                         is_home=True, neutral=neu, played=played, points_for=hp, points_against=ap, elo_pre=he))
        recs.append(dict(game_id=gid, season=s, week=w, asof_week=w, franchise_id=a, opponent_id=h,
                         is_home=False, neutral=neu, played=played, points_for=ap, points_against=hp, elo_pre=ae))
    return pl.DataFrame(recs, schema=TG_SCHEMA)


def _snaps(rows) -> pl.DataFrame:
    return pl.DataFrame(rows, schema={"season": pl.Int32, "week": pl.Int32, "franchise_id": pl.String}, orient="row")


def test_target_adjusted_margins_hand_computed():
    # 2023: HFA = 45 Elo points -> 1.8 points.
    tg = _tg([
        ("g1", 2023, 1, "A", "B", 24, 17, False, 1550.0, 1480.0),  # A home
        ("g2", 2023, 2, "C", "A", 20, 27, False, 1520.0, 1560.0),  # A away
        ("g3", 2023, 3, "B", "C", 10, 13, True, 1470.0, 1510.0),   # neutral
    ])
    am = adjusted_margins(tg)
    got = {(r["game_id"], r["franchise_id"]): r["adj"] for r in am.iter_rows(named=True)}
    expected = {
        ("g1", "A"): 7 + (1480 - 1505) / 25 - 45 / 25,    # 4.2
        ("g1", "B"): -7 + (1550 - 1505) / 25 + 45 / 25,   # -3.4
        ("g2", "C"): -7 + (1560 - 1505) / 25 - 45 / 25,   # -6.6
        ("g2", "A"): 7 + (1520 - 1505) / 25 + 45 / 25,    # 9.4
        ("g3", "B"): -3 + (1510 - 1505) / 25,             # -2.8
        ("g3", "C"): 3 + (1470 - 1505) / 25,              # 1.6
    }
    assert set(got) == set(expected)
    for key, val in expected.items():
        assert got[key] == pytest.approx(val, abs=1e-9)
    hfa = {(r["game_id"], r["franchise_id"]): r["hfa_s"] for r in am.iter_rows(named=True)}
    assert hfa[("g1", "A")] == 45.0 and hfa[("g2", "A")] == -45.0 and hfa[("g3", "B")] == 0.0


def _x_league():
    # X plays Y three times in 2023 (weeks 1-3), all at neutral sites vs a 1505 opponent so adj == margin,
    # then twice in 2024. Plus one unplayed 2023 game that must be ignored.
    return _tg([
        ("a", 2023, 1, "X", "Y", 10, 0, True, 1505.0, 1505.0),
        ("b", 2023, 2, "X", "Y", 3, 0, True, 1505.0, 1505.0),
        ("c", 2023, 3, "X", "Y", 0, 7, True, 1505.0, 1505.0),
        ("u", 2023, 4, "X", "Y", None, None, True, 1505.0, 1505.0),
        ("d", 2024, 1, "X", "Y", 100, 0, True, 1505.0, 1505.0),
        ("e", 2024, 2, "X", "Y", 50, 0, True, 1505.0, 1505.0),
    ])


def _t(df, season, week, team, col):
    return df.filter((pl.col("season") == season) & (pl.col("week") == week) & (pl.col("franchise_id") == team))[col].item()


def test_target_short_window_and_min_two_games():
    snaps = _snaps([(2023, w, f) for w in range(4) for f in ("X", "Y")])
    t = targets(_x_league(), snaps)
    assert t.height == snaps.height
    assert _t(t, 2023, 0, "X", "y4") == pytest.approx((10 + 3 - 7) / 3)
    assert _t(t, 2023, 0, "X", "y8") == pytest.approx((10 + 3 - 7) / 3)
    assert _t(t, 2023, 0, "Y", "y8") == pytest.approx((-10 - 3 + 7) / 3)
    # Week 2: one game left -> skipped for both N.
    assert _t(t, 2023, 2, "X", "y4") is None
    assert _t(t, 2023, 2, "X", "y8") is None
    assert _t(t, 2023, 3, "X", "y8") is None


def test_target_window_after_week_and_within_season():
    snaps = _snaps([(s, w, f) for s in (2023, 2024) for w in range(4) for f in ("X", "Y")])
    t = targets(_x_league(), snaps)
    # Week 1 sees only weeks 2 and 3 of 2023; the big 2024 wins never leak in.
    assert _t(t, 2023, 1, "X", "y8") == pytest.approx((3 - 7) / 2)
    assert _t(t, 2023, 1, "X", "y4") == pytest.approx((3 - 7) / 2)
    assert _t(t, 2024, 0, "X", "y8") == pytest.approx(75.0)
    assert _t(t, 2024, 1, "X", "y8") is None


def test_target_n4_caps_window():
    games = [(f"g{w}", 2023, w, "X", "Y", w, 0, True, 1505.0, 1505.0) for w in range(1, 11)]
    t = targets(_tg(games), _snaps([(2023, 0, "X"), (2023, 5, "X")]))
    assert _t(t, 2023, 0, "X", "y4") == pytest.approx((1 + 2 + 3 + 4) / 4)
    assert _t(t, 2023, 0, "X", "y8") == pytest.approx(sum(range(1, 9)) / 8)
    assert _t(t, 2023, 5, "X", "y8") == pytest.approx((6 + 7 + 8 + 9 + 10) / 5)

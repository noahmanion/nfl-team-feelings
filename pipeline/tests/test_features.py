import polars as pl
import pytest

from conftest import make_games
from fgs.elo import replay
from fgs.features import FEATURE_COLUMNS, build_features
from fgs.games import build_team_games
from fgs.season_config import MEAN_ELO, hfa_for
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
    for c in FEATURE_COLUMNS[1:]:
        assert f[c].null_count() == 0
        assert not f[c].is_nan().any()


def test_mov_hand_computed(synthetic_games):
    f = _feats(synthetic_games)
    for team in ("BUF", "MIA", "NE", "NYJ"):
        assert _v(f, 2023, 0, team, "mov") == 0.0  # no prior games
    assert _v(f, 2023, 2, "BUF", "mov") == pytest.approx((7 + 17) / 2)
    assert _v(f, 2023, 3, "BUF", "mov") == pytest.approx(12.0)  # bye carries forward
    assert _v(f, 2024, 0, "BUF", "mov") == pytest.approx(9.0)   # last season incl. the WC game
    assert _v(f, 2024, 1, "BUF", "mov") == pytest.approx(7.5)
    assert _v(f, 2023, 3, "MIA", "mov") == pytest.approx((-7 + 7 + 24) / 3)


def test_mov_caps_each_game_and_uses_last_8():
    # A wins week 1 by 40 (capped to 24), then weeks 2-9 by 10. B mirrors.
    rows = [("g1", 2023, 1, "REG", "2023-09-01", "A", "B", 50, 10, False)]
    for w in range(2, 10):
        rows.append((f"g{w}", 2023, w, "REG", f"2023-09-{w:02d}", "A", "B", 20, 10, False))
    f = _feats(make_games(rows))
    assert _v(f, 2023, 1, "A", "mov") == pytest.approx(24.0)
    assert _v(f, 2023, 1, "B", "mov") == pytest.approx(-24.0)
    assert _v(f, 2023, 2, "A", "mov") == pytest.approx((24 + 10) / 2)
    assert _v(f, 2023, 8, "A", "mov") == pytest.approx((24 + 7 * 10) / 8)
    assert _v(f, 2023, 9, "A", "mov") == pytest.approx(10.0)  # week-1 game has left the window


def _p_avg(tg, game_id, team, hfa_s):
    opp = tg.filter((pl.col("game_id") == game_id) & (pl.col("franchise_id") != team))["elo_pre"].item()
    return 1.0 / (1.0 + 10 ** (-(MEAN_ELO - opp + hfa_s) / 400))


def test_sow_hand_computed(synthetic_games):
    g, sparse = replay(synthetic_games)
    tg = build_team_games(g)
    f = build_features(build_grid(g, tg, sparse), tg)
    h = hfa_for(2023)
    for team in ("BUF", "MIA", "NE", "NYJ"):
        assert _v(f, 2023, 0, team, "sow") == 0.0
    b1 = 1.0 - _p_avg(tg, "2023_01_MIA_BUF", "BUF", +h)   # BUF home win
    b2 = 1.0 - _p_avg(tg, "2023_02_BUF_NYJ", "BUF", 0.0)  # neutral win
    assert _v(f, 2023, 1, "BUF", "sow") == pytest.approx(b1)
    assert _v(f, 2023, 2, "BUF", "sow") == pytest.approx((b1 + b2) / 2)
    n1 = 0.5 - _p_avg(tg, "2023_01_NYJ_NE", "NE", +h)     # tie at home
    n2 = 0.0 - _p_avg(tg, "2023_02_NE_MIA", "NE", -h)     # away loss
    assert _v(f, 2023, 1, "NE", "sow") == pytest.approx(n1)
    assert _v(f, 2023, 2, "NE", "sow") == pytest.approx((n1 + n2) / 2)
    assert _v(f, 2023, 3, "NE", "sow") == pytest.approx((n1 + n2) / 2)  # bye carries


def test_streak_hand_computed(synthetic_games):
    f = _feats(synthetic_games)
    for team in ("BUF", "MIA", "NE", "NYJ"):
        assert _v(f, 2023, 0, team, "streak") == 0.0
    for (s, w, v) in [(2023, 1, 1), (2023, 2, 2), (2023, 3, 2), (2023, 19, 3), (2024, 0, 3), (2024, 1, 4)]:
        assert _v(f, s, w, "BUF", "streak") == v
    for (s, w, v) in [(2023, 1, 0), (2023, 2, -1), (2024, 1, 1)]:
        assert _v(f, s, w, "NE", "streak") == v
    for (s, w, v) in [(2023, 1, 0), (2023, 2, -1), (2023, 3, -2), (2024, 1, -3), (2024, 2, 1)]:
        assert _v(f, s, w, "NYJ", "streak") == v


def test_streak_caps_and_resets():
    # A beats B weeks 1-10, B wins week 11, tie week 12.
    rows = [(f"g{w}", 2023, w, "REG", f"2023-09-{w:02d}", "A", "B", 20, 10, False) for w in range(1, 11)]
    rows.append(("g11", 2023, 11, "REG", "2023-09-11", "A", "B", 10, 20, False))
    rows.append(("g12", 2023, 12, "REG", "2023-09-12", "A", "B", 10, 10, False))
    f = _feats(make_games(rows))
    assert _v(f, 2023, 10, "A", "streak") == 8
    assert _v(f, 2023, 10, "B", "streak") == -8
    assert _v(f, 2023, 11, "A", "streak") == -1
    assert _v(f, 2023, 11, "B", "streak") == 1
    assert _v(f, 2023, 12, "A", "streak") == 0


def test_luck_hand_computed(synthetic_games):
    f = _feats(synthetic_games)
    assert _v(f, 2024, 1, "BUF", "luck") == 3
    assert _v(f, 2024, 2, "MIA", "luck") == -3
    assert _v(f, 2023, 1, "NE", "luck") == 0  # tie excluded
    assert _v(f, 2023, 2, "NE", "luck") == -1
    assert _v(f, 2024, 1, "NE", "luck") == 0
    for team in ("BUF", "MIA", "NE", "NYJ"):
        assert _v(f, 2023, 0, team, "luck") == 0.0


def test_luck_boundary_and_window():
    # week 1: A wins by 8 (counts); week 2: A wins by 9 (does not); weeks 3-18: A wins by 3.
    rows = [("g1", 2023, 1, "REG", "2023-09-01", "A", "B", 18, 10, False),
            ("g2", 2023, 2, "REG", "2023-09-02", "A", "B", 19, 10, False)]
    for w in range(3, 19):
        rows.append((f"g{w}", 2023, w, "REG", f"2023-09-{w:02d}", "A", "B", 13, 10, False))
    f = _feats(make_games(rows))
    assert _v(f, 2023, 1, "A", "luck") == 1
    assert _v(f, 2023, 1, "B", "luck") == -1
    assert _v(f, 2023, 2, "A", "luck") == 1
    # 17 one-score wins by week 18 (g1 + g3..g18); window holds g3..g18 -> 16
    assert _v(f, 2023, 18, "A", "luck") == 16
    assert _v(f, 2023, 18, "B", "luck") == -16


def test_streak_follows_play_order_within_one_asof_key():
    # Two games sharing one as-of key: the game played later (by gameday) must decide the streak,
    # even when its game_id sorts first.
    from fgs.features import _per_game, _streak

    tg = pl.DataFrame({
        "game_id": ["2023_01_A_B", "2023_02_A_C"], "season": [2023, 2023], "week": [2, 1],
        "asof_week": [2, 2], "game_type": ["REG", "REG"], "is_reg": [True, True],
        "gameday": ["2023-09-20", "2023-09-14"], "gametime": ["13:00", "13:00"],
        "franchise_id": ["A", "A"], "opponent_id": ["B", "C"], "is_home": [True, True],
        "neutral": [False, False], "played": [True, True],
        "points_for": [10, 20], "points_against": [20, 10], "outcome": [0.0, 1.0],
        "elo_pre": [1505.0, 1505.0], "elo_post": [1505.0, 1505.0],
    })
    g = _per_game(tg)
    assert g["game_id"].to_list() == ["2023_02_A_C", "2023_01_A_B"]
    assert _streak(g["franchise_id"].to_numpy(), g["outcome"].to_numpy()).tolist() == [1.0, -1.0]


# --- vs_exp (MODEL-08) ----------------------------------------------------------------------

def _vs_inputs():
    """Hand-built snapshot grid + sim + vegas frames for BUF in 2003 (16 games) and 2022 (17)."""
    S = {"season": pl.Int32, "week": pl.Int32, "franchise_id": pl.String}
    snaps = pl.DataFrame(
        [  # season, week, wins, losses, ties
            dict(season=s, week=w, franchise_id="BUF", elo=1505.0, wins=wi, losses=lo, ties=ti,
                 win_pct=None if wi + lo + ti == 0 else (wi + 0.5 * ti) / (wi + lo + ti))
            for s, w, wi, lo, ti in [(2003, 0, 0, 0, 0), (2003, 4, 3, 1, 0), (2022, 0, 0, 0, 0), (2022, 4, 2, 1, 1)]
        ],
        schema={**S, "elo": pl.Float64, "wins": pl.Int64, "losses": pl.Int64, "ties": pl.Int64, "win_pct": pl.Float64},
    )
    sim = pl.DataFrame(
        [dict(season=s, week=w, franchise_id="BUF", playoff_prob=0.5, exp_wins=e)
         for s, w, e in [(2003, 0, 7.0), (2003, 4, 9.0), (2022, 0, 8.5), (2022, 4, 9.5)]],
        schema={**S, "playoff_prob": pl.Float64, "exp_wins": pl.Float64},
    )
    vegas = pl.DataFrame(
        {"season": [2003], "franchise_id": ["BUF"], "vegas_line": [10.5], "vegas_norm": [10.0]},
        schema={"season": pl.Int32, "franchise_id": pl.String, "vegas_line": pl.Float64, "vegas_norm": pl.Float64},
    )
    tg = build_team_games(make_games([("g", 2003, 1, "REG", "2003-09-07", "BUF", "MIA", 20, 10, False)]))
    return snaps, tg, sim, vegas


def test_vs_exp_vegas_and_model():
    snaps, tg, sim, vegas = _vs_inputs()
    f = build_features(snaps, tg, sim=sim, vegas=vegas)
    assert _v(f, 2003, 4, "BUF", "vs_exp") == pytest.approx((3 - 10 / 16 * 4) / 4)  # 0.125, Vegas 10 of 16
    assert _v(f, 2003, 4, "BUF", "expectation_source") == "vegas"
    assert _v(f, 2003, 4, "BUF", "exp_total") == 10.0
    assert _v(f, 2022, 4, "BUF", "vs_exp") == pytest.approx((2.5 - 8.5 / 17 * 4) / 4)  # 0.125, model wk-0 8.5 of 17
    assert _v(f, 2022, 4, "BUF", "expectation_source") == "model"
    assert _v(f, 2022, 4, "BUF", "exp_total") == 8.5  # week-0 exp_wins, not the week-4 sim


def test_vs_exp_week0_zero_and_source_set():
    snaps, tg, sim, vegas = _vs_inputs()
    f = build_features(snaps, tg, sim=sim, vegas=vegas)
    w0 = f.filter(pl.col("week") == 0)
    assert w0["vs_exp"].to_list() == [0.0, 0.0]
    assert w0["expectation_source"].to_list() == ["vegas", "model"]
    assert f["expectation_source"].null_count() == 0 and f["vs_exp"].null_count() == 0


def test_vs_exp_without_vegas_is_model_sourced():
    snaps, tg, sim, _ = _vs_inputs()
    f = build_features(snaps, tg, sim=sim, vegas=None)
    assert set(f["expectation_source"].to_list()) == {"model"}
    assert _v(f, 2003, 4, "BUF", "vs_exp") == pytest.approx((3 - 7.0 / 16 * 4) / 4)


def test_vs_exp_zero_without_sim():
    snaps, tg, _, _ = _vs_inputs()
    f = build_features(snaps, tg)
    assert (f["vs_exp"] == 0.0).all() and f["expectation_source"].null_count() == f.height


# --- po_trend (MODEL-12) --------------------------------------------------------------------

def _po_inputs():
    """BUF across 2002 (wk 16) and 2003 (wk 0, 1, 2, 5) with hand-set raw sim playoff_prob."""
    S = {"season": pl.Int32, "week": pl.Int32, "franchise_id": pl.String}
    pts = [(2002, 16, 0.90), (2003, 0, 0.20), (2003, 1, 0.30), (2003, 2, 0.35), (2003, 5, 0.60)]
    snaps = pl.DataFrame(
        [dict(season=s, week=w, franchise_id="BUF", elo=1505.0, wins=0, losses=0, ties=0, win_pct=None)
         for s, w, _ in pts],
        schema={**S, "elo": pl.Float64, "wins": pl.Int64, "losses": pl.Int64, "ties": pl.Int64, "win_pct": pl.Float64},
    )
    sim = pl.DataFrame(
        [dict(season=s, week=w, franchise_id="BUF", playoff_prob=p, exp_wins=8.0) for s, w, p in pts],
        schema={**S, "playoff_prob": pl.Float64, "exp_wins": pl.Float64},
    )
    tg = build_team_games(make_games([("g", 2003, 1, "REG", "2003-09-07", "BUF", "MIA", 20, 10, False)]))
    return snaps, tg, sim


def test_po_trend_three_week_lag():
    snaps, tg, sim = _po_inputs()
    f = build_features(snaps, tg, sim=sim)
    assert _v(f, 2003, 5, "BUF", "po_trend") == pytest.approx(0.60 - 0.35)  # p(5) - p(2)
    assert _v(f, 2003, 2, "BUF", "po_trend") == pytest.approx(0.35 - 0.20)  # p(2) - p(max(-1, 0))
    assert _v(f, 2003, 0, "BUF", "po_trend") == 0.0


def test_po_trend_lag_stays_in_season():
    snaps, tg, sim = _po_inputs()
    f = build_features(snaps, tg, sim=sim)
    assert _v(f, 2003, 1, "BUF", "po_trend") == pytest.approx(0.30 - 0.20)  # 2003 week 0, not 2002
    assert "po_trend" in FEATURE_COLUMNS


def test_po_trend_zero_without_sim():
    snaps, tg, _ = _po_inputs()
    f = build_features(snaps, tg)
    assert (f["po_trend"] == 0.0).all()

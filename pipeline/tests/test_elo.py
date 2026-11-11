import math

import polars as pl
import pytest

from conftest import make_games
from fgs.elo import EloParams, mov_mult, replay, update, win_prob
from fgs.games import build_team_games
from fgs.season_config import hfa_for
from fgs.snapshots import build_grid


def _game(games: pl.DataFrame, gid: str) -> dict:
    return games.filter(pl.col("game_id") == gid).row(0, named=True)


# --- pure math (D-14, D-15) -------------------------------------------------

def test_mov_mult_home_win_includes_hfa():
    assert mov_mult(7, 65.0, 1.0) == pytest.approx(math.log(8) * 2.2 / (0.065 + 2.2), abs=1e-12)


def test_mov_mult_away_win_uses_winner_view():
    assert mov_mult(-7, 65.0, 0.0) == pytest.approx(math.log(8) * 2.2 / (-0.065 + 2.2), abs=1e-12)


def test_mov_mult_tie_fixed_denominator():
    assert mov_mult(0, 123.0, 0.5) == pytest.approx(math.log(2) * 2.2, abs=1e-12)
    assert mov_mult(0, -400.0, 0.5) == pytest.approx(math.log(2) * 2.2, abs=1e-12)


def test_mov_mult_min_margin_one():
    # max(|MOV|, 1): a 1-point win and a 0-margin path share ln(2)
    assert mov_mult(1, 0.0, 1.0) == pytest.approx(math.log(2), abs=1e-12)


def test_win_prob_even():
    assert win_prob(0.0) == 0.5


def test_neutral_equal_ratings_even_odds():
    _, _, p = update(1500.0, 1500.0, 3, 0.0, 20.0)
    assert p == 0.5


@pytest.mark.parametrize("margin", [7, -7, 0, 35, -1])
def test_update_zero_sum(margin):
    h, a = 1580.0, 1470.0
    nh, na, _ = update(h, a, margin, 45.0, 20.0)
    assert abs((nh - h) + (na - a)) < 1e-9


def test_hfa_by_era():
    assert [hfa_for(s) for s in (2005, 2015, 2020, 2026)] == [65.0, 58.0, 30.0, 45.0]


# --- replay semantics (D-10..D-13, D-16, D-17, D-19) ------------------------

def test_tie_scores_half_and_moves_teams_together(synthetic_games):
    games, _ = replay(synthetic_games)
    g = _game(games, "2023_01_NYJ_NE")  # NE (home) 10-10 NYJ, both start at 1505
    assert g["elo_pre_home"] == g["elo_pre_away"] == 1505.0
    d_home = g["elo_post_home"] - g["elo_pre_home"]
    d_away = g["elo_post_away"] - g["elo_pre_away"]
    assert d_home < 0 < d_away  # home was favored by HFA, so a tie costs it
    assert d_home == pytest.approx(-d_away, abs=1e-12)
    expected = 20.0 * math.log(2) * 2.2 * (0.5 - win_prob(hfa_for(2023)))
    assert d_home == pytest.approx(expected, abs=1e-9)
    tg = build_team_games(games).filter(pl.col("game_id") == "2023_01_NYJ_NE")
    assert tg["outcome"].to_list() == [0.5, 0.5]


def test_neutral_game_uses_zero_hfa(synthetic_games):
    games, _ = replay(synthetic_games)
    g = _game(games, "2023_02_BUF_NYJ")
    assert g["p_home"] == pytest.approx(win_prob(g["elo_pre_home"] - g["elo_pre_away"]), abs=1e-12)
    h = _game(games, "2023_02_NE_MIA")  # non-neutral, same week
    assert h["p_home"] == pytest.approx(
        win_prob(h["elo_pre_home"] - h["elo_pre_away"] + hfa_for(2023)), abs=1e-12
    )


def test_unplayed_game_skipped(synthetic_games):
    games, sparse = replay(synthetic_games)
    g = _game(games, "2024_02_NE_BUF")
    for c in ("elo_pre_home", "elo_pre_away", "elo_post_home", "elo_post_away", "p_home"):
        assert g[c] is None
    wk2 = sparse.filter((pl.col("season") == 2024) & (pl.col("week") == 2))
    assert set(wk2["franchise_id"]) == {"NYJ", "MIA"}
    tg = build_team_games(games).filter(pl.col("game_id") == "2024_02_NE_BUF")
    assert tg["outcome"].to_list() == [None, None]


def test_zero_sum_every_played_game(synthetic_games):
    games, _ = replay(synthetic_games)
    played = games.filter(pl.col("played"))
    drift = (
        (pl.col("elo_post_home") - pl.col("elo_pre_home"))
        + (pl.col("elo_post_away") - pl.col("elo_pre_away"))
    ).abs().max()
    assert played.select(drift).item() < 1e-9


def test_season_regression_one_third(synthetic_games):
    _, sparse = replay(synthetic_games)
    final_2023 = sparse.filter(pl.col("season") == 2023).group_by("franchise_id").last()
    week0_2024 = sparse.filter((pl.col("season") == 2024) & (pl.col("week") == 0))
    joined = final_2023.join(week0_2024, on="franchise_id", suffix="_w0")
    assert joined.height == 4
    for r in joined.iter_rows(named=True):
        assert r["elo_w0"] == pytest.approx(1505 / 3 + (2 / 3) * r["elo"], abs=1e-9)


def test_playoff_moves_elo(synthetic_games):
    games, _ = replay(synthetic_games)
    g = _game(games, "2023_19_MIA_BUF")
    assert g["elo_post_home"] != g["elo_pre_home"]


def test_seeds_cle_1999_hou_2002():
    rows = [
        ("1999_01_PIT_CLE", 1999, 1, "REG", "1999-09-12", "CLE", "PIT", 0, 43, False),
        ("2002_01_DAL_HOU", 2002, 1, "REG", "2002-09-08", "HOU", "DAL", 19, 10, False),
        ("2002_01_CLE_KC", 2002, 1, "REG", "2002-09-08", "CLE", "KC", 39, 40, False),
    ]
    games, sparse = replay(make_games(rows), EloParams())
    w0 = {
        (r["season"], r["franchise_id"]): r["elo"]
        for r in sparse.filter(pl.col("week") == 0).iter_rows(named=True)
    }
    assert w0[(1999, "CLE")] == 1300.0
    assert w0[(1999, "PIT")] == 1505.0
    assert w0[(2002, "HOU")] == 1300.0
    assert w0[(2002, "DAL")] == 1505.0  # first appearance in 2002, not a seeded team


# --- snapshot grid (D-18, D-23) --------------------------------------------

def test_grid_bye_forward_fill_and_reg_only_records(synthetic_games):
    games, sparse = replay(synthetic_games)
    tg = build_team_games(games)
    snap = build_grid(games, tg, sparse)
    buf = snap.filter((pl.col("franchise_id") == "BUF") & (pl.col("season") == 2023)).sort("week")
    assert buf["week"].to_list() == list(range(0, 20))
    by_week = {r["week"]: r for r in buf.iter_rows(named=True)}
    assert by_week[3]["elo"] == by_week[2]["elo"]  # bye week carries rating
    assert (by_week[0]["wins"], by_week[0]["losses"], by_week[0]["ties"]) == (0, 0, 0)
    assert by_week[0]["win_pct"] is None
    # WC win moves Elo but not the REG record
    assert by_week[19]["elo"] != by_week[18]["elo"]
    assert (by_week[19]["wins"], by_week[19]["losses"]) == (2, 0)
    ne = snap.filter((pl.col("franchise_id") == "NE") & (pl.col("season") == 2023) & (pl.col("week") == 3))
    assert ne.select("wins", "losses", "ties", "win_pct").row(0) == (0, 1, 1, 0.25)

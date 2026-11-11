"""pbp efficiency factors (fgs.efficiency): hand-computed epa_traj on a tiny 3-team, 2-season fixture."""

import polars as pl
import pytest

from conftest import make_games
from fgs import efficiency
from fgs.cli import derive_games
from fgs.elo import replay
from fgs.games import build_team_games

R = 0.5 ** (1 / 4)  # adjust=True EWMA weight ratio per step at half-life 4


def ewm(xs):
    """Hand EWMA (adjust=True, h=4): sum r^i x_{t-i} / sum r^i."""
    ws = [R ** (len(xs) - 1 - i) for i in range(len(xs))]
    return sum(w * x for w, x in zip(ws, xs)) / sum(ws)


def wewm(vals, dbs):
    """Dropback-weighted EWMA: ewm(v*db) / ewm(db)."""
    return ewm([v * d for v, d in zip(vals, dbs)]) / ewm(dbs)


ROWS = [
    ("g1", 2020, 1, "REG", "2020-09-13", "A", "B", 20, 10, False),
    ("g2", 2020, 2, "REG", "2020-09-20", "A", "C", 20, 10, False),
    ("g3", 2020, 3, "REG", "2020-09-27", "B", "C", 20, 10, False),
    ("g4", 2021, 1, "REG", "2021-09-12", "B", "C", 20, 10, False),  # A on bye in week 1
    ("g5", 2021, 2, "REG", "2021-09-19", "A", "B", 20, 10, False),
    ("g6", 2021, 3, "REG", "2021-09-26", "A", "C", 20, 10, False),
    ("g7", 2021, 4, "REG", "2021-10-03", "A", "C", 20, 10, False),  # played, but no pbp row
]
NET = {  # (game, team) -> net_epa
    ("g1", "A"): 0.2, ("g1", "B"): -0.2,
    ("g2", "A"): 0.1, ("g2", "C"): -0.1,
    ("g3", "B"): 0.3, ("g3", "C"): -0.3,
    ("g4", "B"): 0.05, ("g4", "C"): -0.05,
    ("g5", "A"): 0.4, ("g5", "B"): -0.4,
    ("g6", "A"): -0.1, ("g6", "C"): 0.1,
}


def _tge(net=NET) -> pl.DataFrame:
    return pl.DataFrame(
        [{"game_id": g, "season": 2020 if g in ("g1", "g2", "g3") else 2021,
          "franchise_id": t, "net_epa": v} for (g, t), v in net.items()],
        schema={"game_id": pl.String, "season": pl.Int32, "franchise_id": pl.String, "net_epa": pl.Float64},
    )


def _team_games(rows=ROWS) -> pl.DataFrame:
    g, _ = replay(make_games(rows))
    return build_team_games(g)


def _snap(weeks) -> pl.DataFrame:
    return pl.DataFrame(
        [{"season": s, "week": w, "franchise_id": t} for s, w in weeks for t in ("A", "B", "C")],
        schema={"season": pl.Int32, "week": pl.Int32, "franchise_id": pl.String},
    )


def _val(df, season, week, team, col="epa_traj"):
    return df.filter((pl.col("season") == season) & (pl.col("week") == week) & (pl.col("franchise_id") == team))[col].item()


def test_epa_traj_opponent_term():
    g = efficiency.per_game(_team_games(), _tge())
    opp = {(r["game_id"], r["franchise_id"]): r["opp_prior_net"] for r in g.to_dicts()}
    assert opp[("g1", "A")] is None and opp[("g1", "B")] is None  # first-ever games: no prior
    assert opp[("g2", "A")] is None  # C's first game
    assert opp[("g2", "C")] == pytest.approx(0.2)  # A's EWMA of one value
    assert opp[("g5", "A")] == pytest.approx(ewm([-0.2, 0.3, 0.05]))  # B's games strictly before g5
    adj = {(r["game_id"], r["franchise_id"]): r["adj_epa"] for r in g.to_dicts()}
    assert adj[("g1", "A")] == pytest.approx(0.2)  # null opponent term -> 0
    assert adj[("g5", "A")] == pytest.approx(0.4 + ewm([-0.2, 0.3, 0.05]))


def _a_adj():
    return [0.2, 0.1, 0.4 + ewm([-0.2, 0.3, 0.05]), -0.1 + ewm([-0.1, -0.3, -0.05])]


def test_epa_traj_hand_computed():
    f = efficiency.epa_factors(_snap([(2021, 3), (2021, 4)]), _team_games(), _tge())
    adj = _a_adj()
    want = ewm(adj) - (adj[2] + adj[3]) / 2  # EWMA crosses seasons; mean is this season only
    assert _val(f, 2021, 3, "A") == pytest.approx(want)
    assert _val(f, 2021, 4, "A") == pytest.approx(want)  # g7 has no pbp: skipped, value carried


def test_epa_traj_zero_week0_and_before_first_game():
    f = efficiency.epa_factors(_snap([(2020, 0), (2021, 0), (2021, 1), (2021, 2)]), _team_games(), _tge())
    assert f.filter(pl.col("week") == 0)["epa_traj"].to_list() == [0.0] * 6
    assert _val(f, 2021, 1, "A") == 0.0  # bye: last season had games, but none yet this season
    b4 = 0.05 + ewm([-0.1, -0.3])  # B's one 2021 game: EWMA still spans last season
    assert _val(f, 2021, 1, "B") == pytest.approx(ewm([-0.2, 0.3 - 0.1, b4]) - b4)
    adj = _a_adj()
    assert _val(f, 2021, 2, "A") == pytest.approx(ewm(adj[:3]) - adj[2])


def test_epa_traj_game_without_pbp_is_absent():
    with_g7 = efficiency.per_game(_team_games(), _tge())
    without = efficiency.per_game(_team_games(ROWS[:-1]), _tge())
    cols = ["game_id", "franchise_id", "adj_epa", "epa_traj"]
    assert with_g7.select(cols).equals(without.select(cols))


def test_epa_traj_zero_without_pbp():
    feats = derive_games(make_games(ROWS), weights={"elo": 1.0})["features"]
    assert "epa_traj" in feats.columns and (feats["epa_traj"] == 0.0).all()

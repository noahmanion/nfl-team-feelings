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
    ).with_columns(  # no QB info in the epa fixture
        pl.lit(None, pl.String).alias("qb_id"), pl.lit(None, pl.String).alias("qb_name"),
        pl.lit(None, pl.Float64).alias("qb_epa"), pl.lit(None, pl.Int64).alias("dropbacks"),
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


def _real_codes(rows):
    """derive_games runs the season simulator, which needs franchises with a division."""
    code = {"A": "BUF", "B": "MIA", "C": "NE"}
    return [(*r[:5], code[r[5]], code[r[6]], *r[7:]) for r in rows]


def test_epa_traj_zero_without_pbp():
    feats = derive_games(make_games(_real_codes(ROWS)), weights={"elo": 1.0})["features"]
    assert "epa_traj" in feats.columns and (feats["epa_traj"] == 0.0).all()


# --- qb_trend ------------------------------------------------------------------------------

QB_ROWS = [
    ("q1", 2020, 1, "REG", "2020-09-13", "A", "B", 20, 10, False),
    ("q2", 2020, 2, "REG", "2020-09-20", "A", "C", 20, 10, False),
    ("q3", 2021, 1, "REG", "2021-09-12", "B", "C", 20, 10, False),  # A on bye
    ("q4", 2021, 2, "REG", "2021-09-19", "A", "B", 20, 10, False),
    ("q5", 2021, 3, "REG", "2021-09-26", "A", "C", 20, 10, False),
]
# (game, team) -> (qb_id, qb_epa, dropbacks). Q1 starts twice for A in 2020, then once for B in 2021;
# A switches to Q2 in 2021.
QB = {
    ("q1", "A"): ("Q1", 0.3, 40), ("q1", "B"): ("QB_B", 0.0, 30),
    ("q2", "A"): ("Q1", 0.1, 10), ("q2", "C"): ("QB_C", 0.0, 30),
    ("q3", "B"): ("QB_B", 0.0, 30), ("q3", "C"): ("QB_C", 0.0, 30),
    ("q4", "A"): ("Q2", -0.2, 35), ("q4", "B"): ("Q1", 0.2, 30),
    ("q5", "A"): ("Q2", 0.5, 25), ("q5", "C"): ("QB_C", 0.0, 30),
}
NAMES = {"Q1": "Q. One", "Q2": "Q. Two", "QB_B": "B. Passer", "QB_C": "C. Passer"}


def _qb_tge() -> pl.DataFrame:
    return pl.DataFrame(
        [{"game_id": g, "season": 2020 if g in ("q1", "q2") else 2021, "franchise_id": t, "net_epa": 0.0,
          "qb_id": q, "qb_name": NAMES[q], "qb_epa": e, "dropbacks": d} for (g, t), (q, e, d) in QB.items()],
        schema={"game_id": pl.String, "season": pl.Int32, "franchise_id": pl.String, "net_epa": pl.Float64,
                "qb_id": pl.String, "qb_name": pl.String, "qb_epa": pl.Float64, "dropbacks": pl.Int64},
    )


def _qb_feats(weeks):
    return efficiency.epa_factors(_snap(weeks), _team_games(QB_ROWS), _qb_tge())


def test_qb_new_then_form():
    f = _qb_feats([(2020, 1), (2020, 2)])
    assert _val(f, 2020, 1, "A", "qb_trend") == 0.0 and _val(f, 2020, 1, "A", "qb_new") is True
    assert _val(f, 2020, 1, "A", "qb_name") == "Q. One"
    assert _val(f, 2020, 2, "A", "qb_trend") == pytest.approx(wewm([0.3, 0.1], [40, 10]))
    assert _val(f, 2020, 2, "A", "qb_new") is False


def test_qb_dropback_weighting():
    form = _val(_qb_feats([(2020, 2)]), 2020, 2, "A", "qb_trend")
    by_hand = (R * 0.3 * 40 + 0.1 * 10) / (R * 40 + 10)
    assert form == pytest.approx(by_hand)
    assert form > ewm([0.3, 0.1])  # the 40-dropback game pulls harder than the 10-dropback one


def test_qb_form_follows_qb_across_teams_and_seasons():
    f = _qb_feats([(2021, 2)])
    assert _val(f, 2021, 2, "B", "qb_trend") == pytest.approx(wewm([0.3, 0.1, 0.2], [40, 10, 30]))
    assert _val(f, 2021, 2, "B", "qb_name") == "Q. One" and _val(f, 2021, 2, "B", "qb_new") is False


def test_qb_change_resets_team():
    f = _qb_feats([(2021, 1), (2021, 2), (2021, 3)])
    assert _val(f, 2021, 2, "A", "qb_trend") == 0.0  # Q2's first start; Q1's history no longer drives A
    assert _val(f, 2021, 2, "A", "qb_new") is True and _val(f, 2021, 2, "A", "qb_name") == "Q. Two"
    assert _val(f, 2021, 3, "A", "qb_trend") == pytest.approx(wewm([-0.2, 0.5], [35, 25]))
    assert _val(f, 2021, 1, "A", "qb_trend") == pytest.approx(wewm([0.3, 0.1], [40, 10]))  # bye: Q1 carried


def test_qb_week0_zero():
    f = _qb_feats([(2021, 0)])
    assert f["qb_trend"].to_list() == [0.0] * 3
    assert f["qb_name"].to_list() == [None] * 3 and f["qb_new"].to_list() == [False] * 3


def test_qb_without_pbp():
    feats = derive_games(make_games(_real_codes(QB_ROWS)), weights={"elo": 1.0})["features"]
    assert (feats["qb_trend"] == 0.0).all() and not feats["qb_new"].any() and feats["qb_name"].null_count() == feats.height

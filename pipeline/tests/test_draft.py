"""Draft surplus (DATA-06, MODEL-16): synthetic engine tests + real-cache acceptance (skips without cache)."""

import numpy as np
import polars as pl
import pytest

from conftest import make_games
from fgs import draft
from fgs.franchises import CANONICAL
from fgs.games import build_team_games

PFR_CODES = ("ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GNB HOU IND JAX KAN LAC LAR LVR MIA MIN NOR NWE "
             "NYG NYJ OAK PHI PIT SDG SEA SFO STL TAM TEN WAS").split()


# ---------- synthetic builders ----------

def _team_games(season: int, results, playoffs=()) -> pl.DataFrame:
    """results: (home, away, home_score, away_score) REG games; playoffs: (game_type, home, away, hs, as)."""
    rows = []
    for i, (h, a, hs, as_) in enumerate(results):
        rows.append((f"{season}_r{i}_{a}_{h}", season, 1 + i, "REG", f"{season}-09-{10 + i:02d}", h, a, hs, as_, False))
    for i, (gt, h, a, hs, as_) in enumerate(playoffs):
        rows.append((f"{season}_p{i}_{a}_{h}", season, 19 + i, gt, f"{season + 1}-01-{10 + i:02d}", h, a, hs, as_, False))
    return build_team_games(make_games(rows))


def _league4(season: int = 2009) -> pl.DataFrame:
    """4-team prior season. REG win%: A 0/3 (worst), B 1/3, C 2/3, D 3/3. C and D meet in the WC
    and again in the SB (synthetic): C lost the SB (grp 4), D won it (grp 5). Order A, B, C, D."""
    reg = [
        ("A", "B", 10, 20), ("A", "C", 10, 20), ("A", "D", 10, 20),
        ("B", "C", 20, 30), ("B", "D", 10, 20), ("C", "D", 10, 20),
    ]
    po = [("WC", "D", "C", 27, 10), ("SB", "D", "C", 20, 10)]
    return _team_games(season, reg, po)


def _values(n: int = 8) -> np.ndarray:
    """Descending synthetic chart: pick 1 -> n, ..., pick n -> 1, later picks -> 0."""
    v = np.zeros(draft.MAX_PICK + 1)
    v[0] = np.nan
    v[1:n + 1] = np.arange(n, 0, -1, dtype=float)
    return v


def _picks(year: int, rounds: list[list[str]]) -> pl.DataFrame:
    rows, p = [], 1
    for r, teams in enumerate(rounds, start=1):
        for t in teams:
            rows.append({"season": year, "round": r, "pick": p, "franchise_id": t})
            p += 1
    return pl.DataFrame(rows, schema={"season": pl.Int32, "round": pl.Int32, "pick": pl.Int32,
                                      "franchise_id": pl.String})


def _sur(tbl: pl.DataFrame, year: int) -> dict[str, float]:
    return dict(tbl.filter(pl.col("season") == year).select("franchise_id", "surplus").iter_rows())


# ---------- PFR map ----------

def test_pfr_map_covers_all_codes():
    mapped = {draft.map_pfr(c) for c in PFR_CODES}
    assert mapped <= CANONICAL
    assert len(mapped) == 32
    assert draft.map_pfr("LAR") == "LA" and draft.map_pfr("SDG") == "LAC" and draft.map_pfr("OAK") == "LV"


def test_pfr_unknown_code_raises():
    with pytest.raises(ValueError, match="unknown PFR team code"):
        draft.map_pfr("XXX")


def test_pfr_normalize_picks_raises_on_unknown():
    raw = pl.DataFrame({"season": [2010, 2010], "round": [1, 1], "pick": [1, 2], "team": ["GNB", "XXX"]})
    with pytest.raises(ValueError):
        draft.normalize_picks(raw)


def test_pfr_normalize_picks_shape():
    raw = pl.DataFrame({"season": [1998, 2010, 2010], "round": [1, 1, 1], "pick": [1, 2, 1],
                        "team": ["GNB", "KAN", "TAM"]})
    out = draft.normalize_picks(raw)
    assert out.columns == ["season", "round", "pick", "franchise_id"]
    assert out["franchise_id"].to_list() == ["TB", "KC"]  # 1998 dropped, sorted by pick
    assert out.schema["season"] == pl.Int32 and out.schema["pick"] == pl.Int32


# ---------- standings / original order ----------

def test_order_standings_stage_groups():
    st = draft.standings(_league4(), 2009).sort("franchise_id")
    assert st["franchise_id"].to_list() == ["A", "B", "C", "D"]
    assert st["grp"].to_list() == [0, 0, 4, 5]
    assert st["wp"].to_list() == pytest.approx([0.0, 1 / 3, 2 / 3, 1.0])


def test_order_round1_by_stage_then_wp():
    order = draft.original_order(_league4(), 2010, n_rounds=2)
    assert order[0] == ["A", "B", "C", "D"]
    assert order[1] == ["A", "B", "C", "D"]  # no ties: same order every round


def test_order_sos_breaks_wp_ties():
    # A, B, D all .500 (non-playoff); SOS A .25 < D .5 < B .75 -> lower SOS picks first.
    reg = [("A", "C", 20, 10), ("A", "D", 10, 20), ("B", "D", 20, 10), ("B", "E", 10, 20),
           ("D", "C", 20, 10), ("E", "D", 20, 10), ("E", "C", 20, 10)]
    st = draft.standings(_team_games(2009, reg), 2009)
    s = dict(st.select("franchise_id", "sos").iter_rows())
    assert s["A"] < s["B"]
    assert draft.original_order(_team_games(2009, reg), 2010, n_rounds=1)[0] == ["C", "A", "D", "B", "E"]


def test_order_tie_rotation():
    # A and B both 0-1 vs C and D with identical SOS -> tied group (A, B) rotates in round 2.
    reg = [("A", "C", 10, 20), ("B", "D", 10, 20), ("C", "D", 20, 20)]
    order = draft.original_order(_team_games(2009, reg), 2010, n_rounds=3)
    assert order[0][:2] == ["A", "B"]
    assert order[1][:2] == ["B", "A"]
    assert order[2][:2] == ["A", "B"]


def test_order_expansion_first():
    order = draft.original_order(_league4(2001), 2002, n_rounds=7)
    assert all(r[0] == "HOU" for r in order)
    assert all(r[1:] == ["A", "B", "C", "D"] for r in order)


def test_order_forfeit_removes_slot_and_charges_owner():
    tg = _league4()
    vals = _values(8)
    # B forfeits its round-1 pick (slot 2): actual round 1 has 3 picks.
    picks = _picks(2010, [["A", "C", "D"], ["A", "B", "C", "D"]])
    tbl = draft.surplus_table(tg, picks, vals, forfeits={(2010, 1): ["B"]})
    s = _sur(tbl, 2010)
    # charged values[first pick of round (1) + B's index (1)] = values[2] = 7
    assert s["B"] == -7.0
    assert s["A"] == 0.0 and s["C"] == 0.0 and s["D"] == 0.0


# ---------- alignment ----------

def test_align_identical_all_matches():
    o = ["A", "B", "C", "D"]
    assert draft.align(o, list(o)) == [(0, 0), (1, 1), (2, 2), (3, 3)]


def test_align_swap_is_substitution():
    path = draft.align(["A", "B", "C", "D"], ["A", "C", "C", "D"])
    assert path == [(0, 0), (1, 1), (2, 2), (3, 3)]
    assert all(i is not None and j is not None for i, j in path)


def test_align_free_tail_insertion():
    path = draft.align(["A", "B", "C"], ["A", "B", "C", "B"], free_tail=True)
    assert path == [(0, 0), (1, 1), (2, 2), (None, 3)]


def test_align_missing_slot_is_deletion():
    path = draft.align(["A", "B", "C", "D"], ["A", "B", "D"], free_tail=False)
    assert (2, None) in path
    assert [p for p in path if p[0] is not None and p[1] is not None] == [(0, 0), (1, 1), (3, 2)]


# ---------- surplus ----------

def test_surplus_untraded_is_zero():
    tbl = draft.surplus_table(_league4(), _picks(2010, [["A", "B", "C", "D"], ["A", "B", "C", "D"]]), _values())
    assert tbl.columns == ["season", "franchise_id", "slot", "orig_value", "used_value", "surplus"]
    assert tbl.height == 4
    for v in tbl["surplus"].to_list():
        assert v == 0.0  # exactly
    assert dict(tbl.select("franchise_id", "slot").iter_rows()) == {"A": 1, "B": 2, "C": 3, "D": 4}


def test_surplus_trade_moves_value_between_two_teams():
    # A's round-2 pick (#5, value 4) is used by B.
    tbl = draft.surplus_table(_league4(), _picks(2010, [["A", "B", "C", "D"], ["B", "B", "C", "D"]]), _values())
    s = _sur(tbl, 2010)
    assert s["A"] == -4.0 and s["B"] == 4.0
    assert s["A"] == -s["B"]
    assert s["C"] == 0.0 and s["D"] == 0.0
    assert sum(s.values()) == 0.0


def test_surplus_forfeit_only_hurts_owner():
    # C's round-2 slot vanished (found by alignment, not the table): 3 picks in round 2.
    tbl = draft.surplus_table(_league4(), _picks(2010, [["A", "B", "C", "D"], ["A", "B", "D"]]), _values())
    s = _sur(tbl, 2010)
    assert s["C"] < 0
    assert s["A"] == 0.0 and s["B"] == 0.0 and s["D"] == 0.0
    assert sum(s.values()) == pytest.approx(s["C"])


def test_surplus_comp_tail_excluded():
    rounds = [["A", "B", "C", "D"], ["A", "B", "C", "D"], ["A", "B", "C", "D", "B"]]
    tbl = draft.surplus_table(_league4(), _picks(2010, rounds), _values(16))
    assert all(v == 0.0 for v in tbl["surplus"].to_list())


def test_surplus_derivable_years_only():
    tg = pl.concat([_league4(2009), _league4(2010)])
    picks = pl.concat([_picks(y, [["A", "B", "C", "D"]]) for y in (2010, 2012)])
    tbl = draft.surplus_table(tg, picks, _values())
    # 2011 has standings but no picks; 2012 has picks but no 2011 standings
    assert sorted(set(tbl["season"].to_list())) == [2010]


def test_surplus_skips_years_before_first_draft():
    tbl = draft.surplus_table(_league4(1998), _picks(1999, [["A", "B", "C", "D"]]), _values())
    assert tbl.is_empty()


# ---------- winsor / z ----------

def _sur_frame(rows):
    return pl.DataFrame(rows, schema={"season": pl.Int32, "franchise_id": pl.String, "surplus": pl.Float64},
                        orient="row")


def test_winsor_bounds_percentiles():
    s = _sur_frame([(2005, f"T{i}", float(i)) for i in range(101)] + [(2023, "X", 1e6)])
    lo, hi = draft.winsor_bounds(s)
    assert (lo, hi) == (5.0, 95.0)  # 2023 ignored


def test_winsor_draft_z_clip_and_standardize():
    s = _sur_frame([(2005, "A", -100.0), (2005, "B", 0.0), (2005, "C", 1.0), (2005, "D", 100.0),
                    (2006, "A", 3.0), (2006, "B", 3.0)])
    z = draft.draft_z(s, (-10.0, 10.0))
    a = z.filter(pl.col("season") == 2005)["draft_z"].to_numpy()
    assert a.mean() == pytest.approx(0.0, abs=1e-12)
    assert a.std() == pytest.approx(1.0)
    raw = np.array([-10.0, 0.0, 1.0, 10.0])
    assert a == pytest.approx((raw - raw.mean()) / raw.std())
    assert z.filter(pl.col("season") == 2006)["draft_z"].to_list() == [0.0, 0.0]


def test_winsor_frozen_bounds_season_independent():
    s1 = _sur_frame([(2005, "A", -3.0), (2005, "B", 1.0), (2005, "C", 2.0)])
    s2 = pl.concat([s1, _sur_frame([(2006, "A", 50.0), (2006, "B", -50.0)])])
    z1 = draft.draft_z(s1, (-10.0, 10.0)).filter(pl.col("season") == 2005)["draft_z"]
    z2 = draft.draft_z(s2, (-10.0, 10.0)).filter(pl.col("season") == 2005)["draft_z"]
    assert z1.to_list() == z2.to_list()


# ---------- decay / equiv / noun ----------

def test_decay_schedule():
    assert [draft.decay(w) for w in range(6)] == [1.0, 0.75, 0.5, 0.25, 0.0, 0.0]


def test_equiv_pick_smallest_at_or_below():
    v = _values(8)  # pick p -> 9 - p
    assert draft.equiv_pick(8.0, v) == 1
    assert draft.equiv_pick(-7.5, v) == 2
    assert draft.equiv_pick(1.0, v) == 8
    assert draft.equiv_pick(0.5, v) == 9  # first zero-valued pick
    v2 = np.full(draft.MAX_PICK + 1, 5.0)
    assert draft.equiv_pick(1.0, v2) == draft.MAX_PICK


@pytest.mark.parametrize("p,noun", [
    (1, "#1 overall pick"), (2, "top-5 pick"), (5, "top-5 pick"), (6, "early first-round pick"),
    (15, "early first-round pick"), (16, "mid-first-round pick"), (24, "mid-first-round pick"),
    (25, "late first-round pick"), (32, "late first-round pick"), (33, "second-round pick"),
    (64, "second-round pick"), (65, "later-round pick"),
])
def test_equiv_pick_noun_buckets(p, noun):
    assert draft.pick_noun(p) == noun


# ---------- DATA-06 checks (synthetic) ----------

def test_checks_draft_coverage_and_sum():
    from fgs import checks

    rows = [(y, f"T{i}", 1, 0.0, 0.0, 0.0) for y in (2000, 2001) for i in range(31)]
    rows += [(2002, f"T{i}", 1, 0.0, 0.0, 0.0) for i in range(32)]
    ok = pl.DataFrame(rows, schema=draft.SURPLUS_SCHEMA, orient="row")
    assert checks.check_draft_coverage(ok) == []
    assert checks.check_draft_sum(ok) == []
    short = ok.filter(~((pl.col("season") == 2002) & (pl.col("franchise_id") == "T0")))
    assert any("2002" in m for m in checks.check_draft_coverage(short))
    plus = ok.with_columns(pl.when(pl.col("franchise_id") == "T0").then(1.0).otherwise(0.0).alias("surplus"))
    assert len(checks.check_draft_sum(plus)) == 3
    # no draft cache -> both checks pass vacuously (synthetic fixtures carry no draft)
    run = {n: f(None, {"draft": None}, None) for n, f in checks.CHECKS if n.startswith("draft")}
    assert run == {"draft_coverage": [], "draft_sum": []}


# ---------- real cache (skips without it) ----------

@pytest.fixture(scope="module")
def real_draft():
    from fgs.games import build_games
    from fgs.paths import CACHE_DIR

    need = [CACHE_DIR / f for f in ("draft_picks.parquet", "draft_values.csv", "schedules.parquet")]
    if not all(p.exists() for p in need):
        pytest.skip("no cached draft data; run `uv run fgs build` first")
    raw_picks = pl.read_parquet(need[0])
    picks = draft.normalize_picks(raw_picks)
    values = draft.value_table(pl.read_csv(need[1]))
    tg = build_team_games(build_games(pl.read_parquet(need[2])))  # standings need outcomes only, no Elo
    return {"raw": raw_picks, "picks": picks, "values": values, "tg": tg,
            "surplus": draft.surplus_table(tg, picks, values)}


def test_coverage_real(real_draft):
    picks, sur = real_draft["picks"], real_draft["surplus"]
    years = sorted(set(picks["season"].to_list()))
    assert years[0] == 1999 and years == list(range(1999, years[-1] + 1))
    n = dict(picks.group_by("season").agg(pl.col("franchise_id").n_unique()).iter_rows())
    for y in years:
        assert n[y] == (31 if y <= 2001 else 32), y
    assert int(picks["pick"].max()) <= draft.MAX_PICK
    assert not np.isnan(real_draft["values"][1:]).any()
    assert sorted(set(sur["season"].to_list())) == list(range(2000, years[-1] + 1))


def _slot1_untraded(tg, picks, y) -> tuple[str, bool]:
    """(slot-1 franchise, True when all its aligned picks are its own and it gained no regular picks)."""
    order = draft.original_order(tg, y)
    t = order[0][0]
    dy = picks.filter(pl.col("season") == y)
    for r in range(1, draft.N_ROUNDS + 1):
        if t in draft.FORFEITS_R12.get((y, r), []):
            return t, False
        pr = dy.filter(pl.col("round") == r).sort("pick")
        act = pr["franchise_id"].to_list()
        o = [x for x in order[r - 1] if x not in draft.FORFEITS_R12.get((y, r), [])]
        for si, pj in draft.align(o, act, free_tail=r >= 3):
            owner = o[si] if si is not None else None
            user = act[pj] if pj is not None and si is not None else None
            if (owner == t) != (user == t) or (owner == t and pj is None):
                return t, False
    return t, True


def test_acceptance_slot1_untraded_zero(real_draft):
    tg, picks, sur = real_draft["tg"], real_draft["picks"], real_draft["surplus"]
    s = {(y, f): v for y, f, v in sur.select("season", "franchise_id", "surplus").iter_rows()}
    clean = []
    for y in sorted(set(sur["season"].to_list())):
        t, untraded = _slot1_untraded(tg, picks, y)
        if untraded:
            assert s[(y, t)] == 0.0, (y, t, s[(y, t)])
            clean.append((y, t))
    assert (2020, "CIN") in clean
    assert s[(2020, "CIN")] == 0.0


def test_acceptance_sum_nonpositive(real_draft):
    sums = real_draft["surplus"].group_by("season").agg(pl.col("surplus").sum())
    assert (sums["surplus"] <= 1e-9).all()


def test_acceptance_slot_neutral(real_draft):
    from fgs.backtest import spearman  # tests may use the harness; draft.py may not

    t = real_draft["surplus"].filter(pl.col("season").is_between(2000, 2021))
    rho = spearman(t["surplus"].to_numpy(), t["slot"].to_numpy())
    assert -0.15 <= rho <= 0.15


def test_acceptance_known_trades(real_draft):
    s = {(y, f): v for y, f, v in real_draft["surplus"].select("season", "franchise_id", "surplus").iter_rows()}
    assert s[(2020, "MIA")] > 20
    assert s[(2018, "CLE")] > 20
    assert s[(2012, "LV")] < -20
    assert s[(2022, "LA")] < -15


def test_winsor_real(real_draft):
    sur = real_draft["surplus"]
    lo, hi = draft.winsor_bounds(sur)
    assert abs(lo - -17.29) <= 0.5 and abs(hi - 16.19) <= 0.5
    assert sur.filter(pl.col("season") == 1999).is_empty()

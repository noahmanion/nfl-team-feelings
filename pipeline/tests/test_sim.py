"""Season simulator: tiebreak chain, conservation, determinism, version/cache, real data."""

import time

import numpy as np
import polars as pl
import pytest

from conftest import make_games
from fgs import season_config as sc
from fgs import sim
from conftest import derive_inputs

SEASON = 2023


def _g(rows):
    """rows: (gid, week, home, away, home_score, away_score) for SEASON; score None = unplayed."""
    full = [(gid, SEASON, wk, "REG", f"2023-09-{10 + wk:02d}", h, a, hs, as_, False) for gid, wk, h, a, hs, as_ in rows]
    return make_games(full).with_columns(pl.col("week").alias("asof_week"))


def _tiny(monkeypatch, divs, spots):
    monkeypatch.setattr(sc, "divisions", lambda season: divs)
    monkeypatch.setattr(sc, "playoff_teams", lambda season: spots)


def _run(games, elo, week=99, **kw):
    kw.setdefault("sigma", 0.0)
    teams, pp, ew = sim.simulate_season(games, elo, week, **kw)
    return dict(zip(teams, pp)), dict(zip(teams, ew))


# --- tiebreak chain (tiny 1-conference league, 2 divisions, 2 spots = 2 division winners) ---


def test_tiebreak_head_to_head(monkeypatch):
    _tiny(monkeypatch, {"X D1": ["A", "B"], "X D2": ["C", "D"]}, 2)
    g = _g([
        ("g1", 1, "A", "B", 20, 10),  # A beats B
        ("g2", 2, "C", "A", 20, 10),
        ("g3", 3, "B", "D", 20, 10),
        ("g4", 4, "C", "D", 20, 10),
    ])
    p, _ = _run(g, dict.fromkeys("ABCD", 1500.0))
    assert p["A"] == 1.0 and p["B"] == 0.0


def test_tiebreak_division_pct(monkeypatch):
    _tiny(monkeypatch, {"X D1": ["A", "B", "E"], "X D2": ["C", "D"]}, 2)
    g = _g([
        ("g1", 1, "A", "B", 20, 10),
        ("g2", 2, "B", "A", 20, 10),  # split h2h
        ("g3", 3, "A", "E", 20, 10),
        ("g4", 4, "E", "B", 20, 10),
        ("g5", 5, "B", "C", 20, 10),
        ("g6", 6, "C", "A", 20, 10),
        ("g7", 7, "C", "D", 20, 10),
    ])
    p, ew = _run(g, dict.fromkeys("ABCDE", 1500.0))
    assert ew["A"] == ew["B"] == 2.0
    assert p["A"] == 1.0 and p["B"] == 0.0 and p["E"] == 0.0


def test_tiebreak_random(monkeypatch):
    _tiny(monkeypatch, {"X D1": ["A", "B"], "X D2": ["C", "D"]}, 2)
    g = _g([("g1", 1, "A", "B", 20, 10), ("g2", 2, "B", "A", 20, 10), ("g3", 3, "C", "D", 20, 10)])
    p, _ = _run(g, dict.fromkeys("ABCD", 1500.0), n_sims=2000)
    assert abs(p["A"] - 0.5) < 0.05 and abs(p["A"] + p["B"] - 1.0) < 1e-12


def test_favourite_wins_remaining(monkeypatch):
    _tiny(monkeypatch, {"X D1": ["A", "B"], "X D2": ["C", "D"]}, 2)
    g = _g([
        ("g1", 1, "A", "B", None, None),
        ("g2", 2, "C", "A", None, None),
        ("g3", 3, "B", "D", None, None),
        ("g4", 4, "D", "C", 30, 0),  # known: D beat C
    ])
    elo = {"A": 3500.0, "B": 1500.0, "C": 1500.0, "D": -500.0}
    p, ew = _run(g, elo)
    assert ew == {"A": 2.0, "B": 1.0, "C": 0.0, "D": 1.0}
    assert p["A"] == 1.0


# --- conservation, determinism, degenerate leagues ---


def _full_league(n_rounds=8, n_played=3, seed=0):
    rng = np.random.default_rng(seed)
    teams = sorted(t for d in sc.DIVISIONS_2002_ON.values() for t in d)
    rows = []
    for r in range(n_rounds):
        perm = rng.permutation(teams)
        for k in range(0, len(perm), 2):
            h, a = perm[k], perm[k + 1]
            if r < n_played:
                hs, as_ = [(24, 17), (10, 20), (13, 13)][rng.integers(3)]
            else:
                hs = as_ = None
            rows.append((f"{SEASON}_{r + 1:02d}_{a}_{h}", r + 1, h, a, hs, as_))
    g = _g(rows)
    elo = {t: float(1505 + rng.normal(0, 80)) for t in teams}
    return g, elo


def test_sums_conserved():
    g, elo = _full_league()
    for week in (0, 3):
        teams, pp, ew = sim.simulate_season(g, elo, week, n_sims=500)
        assert abs(pp.sum() - sc.playoff_teams(SEASON)) < 1e-9
        assert abs(ew.sum() - g.height) < 1e-3


def test_determinism_and_order_independence():
    g, elo = _full_league()
    a = sim.simulate_season(g, elo, 3, n_sims=500)
    b = sim.simulate_season(g, elo, 3, n_sims=500)
    c = sim.simulate_season(g.sample(fraction=1.0, shuffle=True, seed=7), elo, 3, n_sims=500)
    for x in (b, c):
        assert x[0] == a[0]
        np.testing.assert_array_equal(x[1], a[1])
        np.testing.assert_array_equal(x[2], a[2])
    d = sim.simulate_season(g, elo, 3, n_sims=500, seed=1)
    assert not np.array_equal(d[1], a[1])


def test_empty_divisions_small_league(synthetic_games):
    g = synthetic_games.filter(pl.col("is_reg")).with_columns(pl.col("week").alias("asof_week"))
    for season in (2023, 2024):
        sg = g.filter(pl.col("season") == season)
        teams, pp, ew = sim.simulate_season(sg, dict.fromkeys(["BUF", "MIA", "NE", "NYJ"], 1505.0), 1, n_sims=200)
        assert teams == ["BUF", "MIA", "NE", "NYJ"]
        assert ((pp >= 0) & (pp <= 1)).all()
        # 1 division winner + 3 AFC wildcards; only 4 teams exist -> all of them make it
        assert abs(pp.sum() - 4) < 1e-12
        assert abs(ew.sum() - sg.height) < 1e-6


def test_team_without_division_raises(monkeypatch):
    _tiny(monkeypatch, {"X D1": ["A", "B"]}, 1)
    g = _g([("g1", 1, "A", "Z", 20, 10)])
    with pytest.raises(KeyError, match="Z"):
        sim.simulate_season(g, {"A": 1500.0, "Z": 1500.0}, 1)


# --- model_version + cache ---


def test_version_changes_with_params(monkeypatch):
    base = sim.model_version()
    assert sim.model_version() == base
    assert sim.model_version(n_sims=1000) != base
    assert sim.model_version(sigma=50.0) != base
    assert sim.model_version(seed=1) != base
    monkeypatch.setattr(sc, "HFA_BY_ERA", ((1999, 9999, 50.0),))
    assert sim.model_version() != base
    monkeypatch.undo()
    import dataclasses

    orig = sim.EloParams
    monkeypatch.setattr(sim, "EloParams", lambda: dataclasses.replace(orig(), k=25.0))
    assert sim.model_version() != base
    monkeypatch.undo()
    assert sim.model_version() == base


def test_version_covers_simulator_source(monkeypatch):
    """WR-06: editing the simulator code changes the cache key without a manual SIM_VERSION bump."""
    import hashlib
    from pathlib import Path

    assert sim.SIM_CODE_HASH == hashlib.sha256(Path(sim.__file__).read_bytes()).hexdigest()
    base = sim.model_version()
    monkeypatch.setattr(sim, "SIM_CODE_HASH", "edited")
    assert sim.model_version() != base


def _two_seasons():
    g, elo = _full_league(n_rounds=4, n_played=2)
    g2 = g.with_columns(pl.lit(2022, dtype=pl.Int32).alias("season"), ("x" + pl.col("game_id")).alias("game_id"))
    games = pl.concat([g, g2])
    snaps = pl.DataFrame(
        [
            dict(season=s, week=w, franchise_id=t, elo=e + w)
            for s in (2022, 2023)
            for w in (0, 1, 2)
            for t, e in elo.items()
        ],
        schema={"season": pl.Int32, "week": pl.Int32, "franchise_id": pl.String, "elo": pl.Float64},
    )
    return games, snaps


def test_version_cache_incremental(monkeypatch, tmp_path):
    games, snaps = _two_seasons()
    calls = []
    real = sim.simulate_season

    def counting(sg, *a, **k):
        calls.append(int(sg["season"][0]))
        return real(sg, *a, **k)

    monkeypatch.setattr(sim, "simulate_season", counting)
    first = sim.simulate_all(games, snaps, n_sims=200, cache_dir=tmp_path)
    assert (tmp_path / f"{sim.model_version(200, sim.SIGMA, sim.SEED)}.parquet").exists()
    assert set(calls) == {2022, 2023} and len(calls) == 6

    calls.clear()
    again = sim.simulate_all(games, snaps, n_sims=200, cache_dir=tmp_path)
    assert calls == []
    assert again.equals(first)

    # change one 2023 result -> only 2023 recomputed, equal to a cold run
    gid = games.filter((pl.col("season") == 2023) & pl.col("played"))["game_id"][0]
    games2 = games.with_columns(
        pl.when(pl.col("game_id") == gid).then(-pl.col("result") - 1).otherwise(pl.col("result")).alias("result")
    )
    calls.clear()
    warm = sim.simulate_all(games2, snaps, n_sims=200, cache_dir=tmp_path)
    assert set(calls) == {2023}
    cold = sim.simulate_all(games2, snaps, n_sims=200)
    assert warm.equals(cold)
    assert warm.columns == ["season", "week", "franchise_id", "playoff_prob", "exp_wins", "input_digest"]


def test_cache_write_deferred(tmp_path):
    games, snaps = _two_seasons()
    path = tmp_path / f"{sim.model_version(200, sim.SIGMA, sim.SEED)}.parquet"
    out = sim.simulate_all(games, snaps, n_sims=200, cache_dir=tmp_path, write_cache=False)
    assert not path.exists()  # read-only: refresh writes after the checks pass
    assert out["input_digest"].n_unique() == 2
    sim.save_sim_cache(out, tmp_path, sim.model_version(200, sim.SIGMA, sim.SEED))
    assert pl.read_parquet(path).equals(out)
    assert not list(tmp_path.glob("*.tmp"))


def test_input_digest_covers_game_order():
    """WR-05: a moved kickoff (no result change) reorders the uniform draws, so it must change the digest."""
    g = _g([("g1", 1, "A", "B", 20, 10), ("g2", 2, "C", "D", None, None), ("g3", 2, "A", "C", None, None)])
    snaps = pl.DataFrame({"week": [0, 0, 0, 0], "franchise_id": list("ABCD"), "elo": [1500.0] * 4})
    base = sim.input_digest(g, snaps)
    moved = g.with_columns(pl.when(pl.col("game_id") == "g2").then(pl.lit("2023-09-30")).otherwise(pl.col("gameday"))
                           .alias("gameday"))
    assert sim.input_digest(moved, snaps) != base
    assert sim.input_digest(g.reverse(), snaps) == base  # row order of the input frame is irrelevant


# --- real data (skips without the schedules cache) ---


@pytest.fixture(scope="module")
def real_sim():
    from fgs.paths import CACHE_DIR

    if not (CACHE_DIR / "schedules.parquet").exists():
        pytest.skip("no cached schedules; run `uv run fgs build` first")
    from fgs.cli import derive
    from fgs.ingest import load_schedules

    d = derive(load_schedules(), scored=False, **derive_inputs())
    t = time.time()
    out = d["sim"]  # computed by derive (session sim cache)
    print(f"\nsimulate_all: {out.select('season', 'week').unique().height} snapshots in {time.time() - t:.1f}s")
    return d, out


def test_real_sums(real_sim):
    d, out = real_sim
    n_reg = d["games"].filter(pl.col("is_reg")).group_by("season").len().rename({"len": "n_reg"})
    s = out.group_by("season", "week").agg(pl.col("playoff_prob").sum().alias("sp"), pl.col("exp_wins").sum().alias("sw"))
    s = s.join(n_reg, on="season")
    spots = np.array([sc.playoff_teams(x) for x in s["season"]])
    assert np.abs(s["sp"].to_numpy() - spots).max() < 1e-6
    assert np.abs(s["sw"].to_numpy() - s["n_reg"].to_numpy()).max() < 1e-3


def test_real_field(real_sim):
    d, out = real_sim
    post = d["games"].filter(~pl.col("is_reg"))
    actual = pl.concat([
        post.select("season", pl.col("home_id").alias("franchise_id")),
        post.select("season", pl.col("away_id").alias("franchise_id")),
    ]).unique().with_columns(pl.lit(1).alias("made"))
    last = out.filter(pl.col("season").is_between(1999, 2021)).filter(
        pl.col("week") == pl.col("season").map_elements(sc.reg_weeks, return_dtype=pl.Int32)
    )
    j = last.join(actual, on=["season", "franchise_id"], how="left").with_columns(pl.col("made").fill_null(0))
    acc = float((1 - (j["playoff_prob"] - j["made"]).abs()).mean())
    print(f"\nend-of-REG field accuracy 1999-2021: {acc:.4f} over {j.height} team-seasons")
    assert j.height > 700
    assert acc >= 0.97


def test_real_vegas_corr(real_sim):
    from fgs.paths import CACHE_DIR

    if not (CACHE_DIR / "win_totals.csv").exists():
        pytest.skip("no cached win_totals.csv")
    from fgs.expectation import load_win_totals, vegas_expectations

    d, out = real_sim
    v = vegas_expectations(load_win_totals())
    w0 = out.filter(pl.col("week") == 0).select("season", "franchise_id", "exp_wins")
    j = v.join(w0, on=["season", "franchise_id"])
    assert j.height == 576
    r = float(np.corrcoef(j["exp_wins"], j["vegas_line"])[0, 1])
    per = j.group_by("season").agg(pl.corr("exp_wins", "vegas_line").alias("r"))["r"]
    tg = d["team_games"].filter(pl.col("is_reg"), pl.col("played"))
    act = tg.group_by("season", "franchise_id").agg(pl.col("outcome").sum().alias("wins"))
    ja = j.join(act, on=["season", "franchise_id"])
    r_mw = float(np.corrcoef(ja["exp_wins"], ja["wins"])[0, 1])
    r_vw = float(np.corrcoef(ja["vegas_line"], ja["wins"])[0, 1])
    print(
        f"\nr(model wk0, vegas)={r:.3f} per-season {per.min():.2f}-{per.max():.2f}; "
        f"sd model={j['exp_wins'].std():.2f} vegas={j['vegas_line'].std():.2f}; "
        f"r(actual): model={r_mw:.3f} vegas={r_vw:.3f}"
    )
    assert r >= 0.7

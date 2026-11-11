"""Synthetic property tests for the paired bootstrap engine (no real data, no holdout seasons)."""

import math

import numpy as np

from fgs import bootstrap as bs
from fgs.backtest import spearman


def _synthetic(seed=0):
    rng = np.random.default_rng(seed)
    seasons, teams, weeks = [2018, 2019, 2020, 2021], 32, 17
    season = np.repeat(seasons, teams * weeks)
    team = np.tile(np.repeat(np.arange(teams), weeks), len(seasons))
    week = np.tile(np.arange(weeks), teams * len(seasons))
    team_strength = rng.normal(size=(len(seasons), teams))
    signal = team_strength[np.searchsorted(seasons, season), team]
    y = signal + rng.normal(scale=0.7, size=signal.size)
    a = signal + rng.normal(scale=0.2, size=signal.size)
    b = rng.normal(size=signal.size)
    return season, team, week, y, a, b


def test_season_blocks():
    blocks = bs.season_blocks(np.array([2018, 2018, 2019, 2020, 2020, 2020]))
    assert [b.tolist() for b in blocks] == [[0, 1], [2], [3, 4, 5]]


def test_stratified_clusters_preserve_rows_and_counts():
    season, team, *_ = _synthetic()
    strata = bs.stratified_clusters(season, team)
    assert len(strata) == 4
    assert all(len(s) == 32 for s in strata)
    assert sum(len(c) for s in strata for c in s) == season.size
    # string keys work too
    strata_s = bs.stratified_clusters(season, team.astype(str))
    assert sum(len(c) for s in strata_s for c in s) == season.size


def test_draw_stratified_keeps_cluster_count_per_season():
    season, team, *_ = _synthetic()
    strata = bs.stratified_clusters(season, team)
    rng = np.random.default_rng(1)
    for _ in range(5):
        idx = bs.draw_stratified(rng, strata)
        # every cluster here has 17 rows, so per-season row counts == 32 clusters * 17
        for s in (2018, 2019, 2020, 2021):
            assert int((season[idx] == s).sum()) == 32 * 17


def test_draw_blocks_draws_k_blocks():
    blocks = bs.season_blocks(np.array([1, 1, 2, 3, 3, 3]))
    rng = np.random.default_rng(3)
    for _ in range(10):
        idx = bs.draw_blocks(rng, blocks)
        # length must be a sum of 3 block sizes from {2,1,3}
        assert 3 <= idx.size <= 9


def test_distinct_block_resamples():
    assert bs.distinct_block_resamples(4) == 35
    assert bs.distinct_block_resamples(19) == math.comb(37, 19)


def _fns(y, a, b):
    return {"a": lambda i: spearman(a[i], y[i]), "b": lambda i: spearman(b[i], y[i])}


def test_deterministic_with_seed():
    season, team, _, y, a, b = _synthetic()
    blocks = bs.season_blocks(season)
    draw = lambda rng: bs.draw_blocks(rng, blocks)  # noqa: E731
    r1 = bs.paired_bootstrap(_fns(y, a, b), draw, diffs={"a_b": ("a", "b")}, B=200, seed=7)
    r2 = bs.paired_bootstrap(_fns(y, a, b), draw, diffs={"a_b": ("a", "b")}, B=200, seed=7)
    r3 = bs.paired_bootstrap(_fns(y, a, b), draw, diffs={"a_b": ("a", "b")}, B=200, seed=8)
    assert r1 == r2
    assert r1["stats"]["a"]["ci"] != r3["stats"]["a"]["ci"]
    assert r1["B"] == 200 and r1["seed"] == 7


def test_identical_predictors_give_zero_diff():
    season, team, _, y, a, _b = _synthetic()
    strata = bs.stratified_clusters(season, team)
    fns = {"x": lambda i: spearman(a[i], y[i]), "x2": lambda i: spearman(a[i], y[i])}
    r = bs.paired_bootstrap(fns, lambda rng: bs.draw_stratified(rng, strata),
                            diffs={"d": ("x", "x2")}, B=300)
    assert r["diffs"]["d"]["ci"] == [0.0, 0.0]
    assert r["diffs"]["d"]["sd"] == 0.0
    assert r["diffs"]["d"]["n_finite"] == 300


def test_strong_vs_noise_lower_bound_positive_both_methods():
    season, team, _, y, a, b = _synthetic()
    blocks = bs.season_blocks(season)
    strata = bs.stratified_clusters(season, team)
    for draw in (lambda rng: bs.draw_blocks(rng, blocks), lambda rng: bs.draw_stratified(rng, strata)):
        r = bs.paired_bootstrap(_fns(y, a, b), draw, diffs={"a_b": ("a", "b")}, B=300)
        lo, hi = r["diffs"]["a_b"]["ci"]
        assert lo > 0 and hi >= lo


def test_none_recorded_as_nan_and_skipped():
    counter = {"n": 0}

    def flaky(i):
        counter["n"] += 1
        return None if counter["n"] % 2 == 0 else float(len(i))

    r = bs.paired_bootstrap({"f": flaky, "c": lambda i: 1.0}, lambda rng: np.arange(5),
                            diffs={"d": ("f", "c")}, B=10)
    assert r["stats"]["f"]["n_finite"] == 5
    assert r["stats"]["f"]["ci"] == [5.0, 5.0]
    assert r["diffs"]["d"]["n_finite"] == 5
    assert r["diffs"]["d"]["ci"] == [4.0, 4.0]


def test_all_none_gives_none_ci():
    r = bs.paired_bootstrap({"f": lambda i: None}, lambda rng: np.arange(3), B=5)
    assert r["stats"]["f"]["ci"] is None
    assert r["stats"]["f"]["sd"] is None
    assert r["stats"]["f"]["n_finite"] == 0
    assert bs.percentile_ci([float("nan")]) is None

import json
import math

import numpy as np

import polars as pl
import pytest

from fgs import cli
from fgs.backtest import (
    adjusted_margins, choose_alpha, propose_weights, ridge_fit, run_backtest, targets, test_seasons,
)
from fgs.ingest import load_schedules
from fgs.paths import WEIGHTS_PATH
from fgs.score import load_weights

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


# ---------------------------------------------------------------------------
# Walk-forward baselines (real cache)
# ---------------------------------------------------------------------------



@pytest.fixture(scope="module")
def real_report():
    from fgs.paths import CACHE_DIR

    if not (CACHE_DIR / "schedules.parquet").exists():
        pytest.skip("no cached schedules; run `uv run fgs build` first")
    raw = load_schedules()
    return raw, run_backtest(cli.derive(raw))


def test_holdout_test_seasons():
    assert test_seasons(False)[0] == 2003 and test_seasons(False)[-1] == 2021
    assert test_seasons(True)[-1] == 2025
    assert 2026 not in test_seasons(True)


def test_holdout_sealed_by_default(real_report):
    raw, report = real_report
    assert report["test_seasons"][-1] == 2021 and not report["include_holdout"]
    for name, c in report["candidates"].items():
        if c["per_season"] is None:
            continue
        for n in ("N4", "N8"):
            assert all(int(s) < 2022 for s in c["per_season"][n]), name
    # Rewriting every 2024 result must not change the default report at all.
    swapped = raw.with_columns(
        pl.when(pl.col("season") == 2024).then(pl.col("away_score")).otherwise(pl.col("home_score")).alias("home_score"),
        pl.when(pl.col("season") == 2024).then(pl.col("home_score")).otherwise(pl.col("away_score")).alias("away_score"),
        pl.when(pl.col("season") == 2024).then(-pl.col("result")).otherwise(pl.col("result")).alias("result"),
    )
    assert run_backtest(cli.derive(swapped)) == report


def test_baselines_real_cache(real_report):
    _, report = real_report
    c = report["candidates"]
    assert {"elo", "season_wpct", "last16", "pd_pg", "spread"} <= set(c)
    assert 0.215 <= c["elo"]["brier"] <= 0.23
    assert c["spread"]["brier"] < c["elo"]["brier"]
    assert c["elo"]["N8"]["all"]["spearman"] > 0.4
    assert c["season_wpct"]["N8"]["wk0"]["spearman"] is None
    json.dumps(report, allow_nan=False)


def test_cli_backtest_writes_json(real_cache, tmp_path, monkeypatch, capsys):
    import fgs.paths

    monkeypatch.setattr(cli, "DERIVED_DIR", tmp_path)
    # WR-05: the backtest must not need a valid weights.yaml (it proposes them)
    monkeypatch.setattr(fgs.paths, "WEIGHTS_PATH", tmp_path / "missing-weights.yaml")
    assert cli.main(["backtest"]) == 0
    out = capsys.readouterr().out
    assert "Spearman" in out and "spread" in out
    data = json.loads((tmp_path / "backtest.json").read_text())
    assert data["test_seasons"][-1] == 2021


# ---------------------------------------------------------------------------
# Ridge composites and the weights proposal (plan 03-02)
# ---------------------------------------------------------------------------

def test_ridge_fit_recovers_coefficients_and_shrinks():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(2000, 2))
    y = 2 * X[:, 0] - 1 * X[:, 1] + 3 + rng.normal(0, 0.05, 2000)
    w, b = ridge_fit(X, y, 0.0)
    assert np.allclose(w, [2, -1], atol=0.05) and abs(b - 3) < 0.05
    w1, _ = ridge_fit(X, y, 1.0)
    assert np.linalg.norm(w1) < np.linalg.norm(w)


def test_choose_alpha_returns_grid_value():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(400, 2))
    y = X[:, 0] + rng.normal(0, 1, 400)
    a = choose_alpha(X, y, np.repeat([1, 2, 3, 4], 100))
    assert a in (0.0, 1e-3, 1e-2, 1e-1, 1.0)


def test_propose_weights_holdout_sealed(real_report):
    raw, _ = real_report
    prop = propose_weights(cli.derive(raw))
    assert prop["seasons"] == [1999, 2021] and prop["target"] == "y8"
    late = pl.col("season") >= 2022
    swapped = raw.with_columns(
        pl.when(late).then(pl.col("away_score")).otherwise(pl.col("home_score")).alias("home_score"),
        pl.when(late).then(pl.col("home_score")).otherwise(pl.col("away_score")).alias("away_score"),
        pl.when(late).then(-pl.col("result")).otherwise(pl.col("result")).alias("result"),
    )
    assert propose_weights(cli.derive(swapped)) == prop


def test_ridge_composites_in_report(real_report):
    raw, report = real_report
    c = report["candidates"]
    for name in ("ridge:elo", "ridge:+season_record", "ridge:+last16", "ridge:+mov"):
        assert name in c and c[name]["N8"]["all"]["spearman"] is not None
        assert c[name]["last_fold_weights"]["season"] == 2021
    assert c["ridge:+last16"]["N8"]["all"]["spearman"] >= c["ridge:elo"]["N8"]["all"]["spearman"] - 0.005
    assert 0.516 <= c["ridge:+mov"]["N8"]["all"]["spearman"] <= 0.520
    prop = propose_weights(cli.derive(raw))
    assert set(prop["weights"]) == {"elo", "season_record", "last16", "mov"}
    assert all(math.isfinite(v) for v in prop["weights"].values())


def test_weights_yaml_loads():
    w = load_weights(WEIGHTS_PATH)
    assert list(w) == ["elo", "season_record", "last16", "mov"]

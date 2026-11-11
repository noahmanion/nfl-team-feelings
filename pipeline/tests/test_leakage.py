"""BACK-03 leakage test: no future game may move a past snapshot's factors, contributions or score.

Runs the exact production path (derive -> features -> composite -> score_frame). A snapshot
for (season, week) includes week `week`'s own games, so "the future" here is always the weeks
after the latest week with any played game; filling unplayed games inside a partially played
week would legitimately change that week, so those are never touched.
"""

import functools
import re
from pathlib import Path

import polars as pl
import pytest

import fgs
from fgs import cli, explain, features, mood, season_config
from fgs.cli import derive, derive_games
from fgs.mood import score_frame
from conftest import _ROWS, make_games

KEY = ["season", "week", "franchise_id"]
FLOAT_EXACT = [c for c in features.FEATURE_COLUMNS] + ["composite"]  # + every z_* / contrib_* column
EXACT = ["score", "band", "rank", "score_delta", "rank_delta", "label"]
TOL = 1e-12


def _with_points(derived: dict) -> pl.DataFrame:
    feats = derived["features"]
    return explain.add_points(score_frame(feats), list(derived["weights"]), mood.reference_values(feats))


@functools.cache
def _inputs() -> dict:
    return cli.cached_inputs()  # read the pbp cache once per session


def _pipeline(raw: pl.DataFrame) -> pl.DataFrame:
    return _with_points(derive(raw, **_inputs()))


def _assert_unchanged(before: pl.DataFrame, after: pl.DataFrame) -> None:
    floats = FLOAT_EXACT + [c for c in before.columns if c.startswith(("z_", "contrib_"))]
    exact = EXACT + [c for c in before.columns if c.startswith("pts_")]
    assert any(c.startswith("contrib_") for c in floats) and any(c.startswith("pts_") for c in exact)
    j = before.select(KEY + floats + exact).join(after.select(KEY + floats + exact), on=KEY, how="inner", suffix="_n")
    assert j.height == before.height, f"{before.height - j.height} pre-existing snapshot rows disappeared"
    for c in floats:
        bad = j.filter((pl.col(c) - pl.col(f"{c}_n")).abs() > TOL)
        assert bad.is_empty(), f"{c} changed in {bad.height} rows, e.g. {bad.select(KEY).head(3).to_dicts()}"
    for c in exact:
        bad = j.filter(~pl.col(c).eq_missing(pl.col(f"{c}_n")))
        assert bad.is_empty(), f"{c} changed in {bad.height} rows, e.g. {bad.select(KEY).head(3).to_dicts()}"


def _latest_played(raw: pl.DataFrame) -> tuple[int, int]:
    played = raw.filter(pl.col("result").is_not_null())
    s = int(played["season"].max())
    return s, int(played.filter(pl.col("season") == s)["week"].max())


def _set_result(raw: pl.DataFrame, mask: pl.Expr, home, away) -> pl.DataFrame:
    result = None if home is None else home - away
    return raw.with_columns(
        pl.when(mask).then(pl.lit(v)).otherwise(pl.col(c)).cast(raw.schema[c]).alias(c)
        for c, v in (("home_score", home), ("away_score", away), ("result", result))
    )


@pytest.fixture(scope="module")
def real_raw():
    from fgs.paths import CACHE_DIR

    path = CACHE_DIR / "schedules.parquet"
    if not path.exists():
        pytest.skip("no cached schedules; run `uv run fgs build` first")
    return pl.read_parquet(path)


@pytest.fixture(scope="module")
def real_base(real_raw):
    return _pipeline(real_raw)


def test_fake_future_games_change_nothing(real_raw, real_base):
    s, w = _latest_played(real_raw)
    future = pl.col("result").is_null() & ((pl.col("season") > s) | ((pl.col("season") == s) & (pl.col("week") > w)))
    if real_raw.filter(future).is_empty():
        pytest.skip("no unplayed games after the latest played week")
    fake = _pipeline(_set_result(real_raw, future, 60, 0))  # every future home team wins 60-0
    assert fake.height > real_base.height  # the fake games really were played
    _assert_unchanged(real_base, fake)


def test_truncating_future_keeps_past(real_raw, real_base):
    s, w = _latest_played(real_raw)
    if w < 3:
        pytest.skip(f"{s}: only {w} weeks played")
    cut = w - 2
    truncated = _pipeline(_set_result(real_raw, (pl.col("season") == s) & (pl.col("week") > cut), None, None))
    kept = real_base.filter((pl.col("season") < s) | (pl.col("week") <= cut))
    assert kept.height < real_base.height
    _assert_unchanged(kept, truncated)


def test_fake_future_pbp_changes_nothing(real_raw, real_base):
    """Future games get played (60-0) AND get extreme pbp rows: no past snapshot may move."""
    tge = _inputs()["pbp_games"]
    if tge is None:
        pytest.skip("no cached pbp; run `uv run fgs build` first")
    s, w = _latest_played(real_raw)
    future = pl.col("result").is_null() & ((pl.col("season") > s) | ((pl.col("season") == s) & (pl.col("week") > w)))
    if real_raw.filter(future).is_empty():
        pytest.skip("no unplayed games after the latest played week")
    faked = _set_result(real_raw, future, 60, 0)
    tg = derive(faked, scored=False)["team_games"]
    new = tg.join(tge.select("game_id", "franchise_id"), on=["game_id", "franchise_id"], how="anti").filter(
        pl.col("played") & ((pl.col("season") > s) | ((pl.col("season") == s) & (pl.col("week") > w)))
    )  # future games only (a few old games legitimately have no pbp)
    assert not new.is_empty()
    template = tge.row(0, named=True)
    rows = [
        template | {"game_id": r["game_id"], "season": r["season"], "franchise_id": r["franchise_id"],
                    "off_epa": 5.0, "def_epa": -5.0, "net_epa": 10.0, "qb_id": "FAKE-QB", "qb_name": "Fake QB",
                    "dropbacks": 60, "qb_epa": 5.0, "team_db": 60, "team_db_epa_sum": 300.0}
        for r in new.select("game_id", "season", "franchise_id").to_dicts()
    ]
    fake_tge = pl.concat([tge, pl.DataFrame(rows, schema=tge.schema)])
    fake = _with_points(derive(faked, pbp_games=fake_tge))
    assert fake.height > real_base.height
    _assert_unchanged(real_base, fake)


def test_synthetic_leakage(monkeypatch):
    monkeypatch.setattr(season_config, "REF_SEASONS", (2023, 2023))
    weights = {"elo": 1.0, "season_record": 0.5, "last16": -0.5}
    # Move the fixture's unplayed game to a week of its own, after the latest played week (2024 wk 2).
    rows = [(r[0], r[1], 3, *r[3:]) if r[7] is None else r for r in _ROWS]
    games = make_games(rows)

    def run(g):
        feats = derive_games(g, weights=weights)["features"]
        return explain.add_points(score_frame(feats), list(weights), mood.reference_values(feats))

    base = run(games)
    filled = games.with_columns(
        pl.when(pl.col("played")).then(pl.col(c)).otherwise(pl.lit(v)).cast(games.schema[c]).alias(c)
        for c, v in (("home_score", 30), ("away_score", 3), ("result", 27), ("played", True))
    )
    after = run(filled)
    assert after.height > base.height and int(after.filter(pl.col("season") == 2024)["week"].max()) == 3
    _assert_unchanged(base, after)


def test_backtest_not_imported_upstream():
    src = Path(fgs.__file__).parent
    imp = re.compile(r"^\s*(from|import)\s+[\w., ]*backtest", re.M)
    for name in ("features.py", "score.py", "mood.py", "export.py", "explain.py", "efficiency.py", "pbp.py"):
        code = "\n".join(line.split("#", 1)[0] for line in (src / name).read_text().splitlines())
        assert not imp.search(code), f"{name} imports the backtest harness"

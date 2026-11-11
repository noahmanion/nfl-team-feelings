"""Expectations: win-total mapping/normalization and source tagging (pure, no network)."""

import io

import polars as pl
import pytest

from fgs.expectation import expectations, load_win_totals, vegas_expectations

CSV = """season,team,line,over_odds,under_odds
2010,OAK,5.5,-110,-110
2010,SD,10.5,-120,100
2010,STL,4.5,-110,-110
2010,NE,10,-110,-110
2021,BUF,11,-110,-110
2021,KC,12.5,-110,-110
"""


@pytest.fixture
def wt():
    return pl.read_csv(io.StringIO(CSV))


def test_mapping_and_normalization(wt):
    v = vegas_expectations(wt)
    assert v.columns == ["season", "franchise_id", "vegas_line", "vegas_norm"]
    assert v.schema["season"] == pl.Int32
    assert set(v.filter(pl.col("season") == 2010)["franchise_id"]) == {"LV", "LAC", "LA", "NE"}
    for season, n, games in ((2010, 4, 16), (2021, 2, 17)):
        s = v.filter(pl.col("season") == season)["vegas_norm"].sum()
        assert s == pytest.approx(n * games / 2)
    # ordering preserved within a season
    x = dict(zip(*v.filter(pl.col("season") == 2010).select("franchise_id", "vegas_norm").to_dict().values()))
    assert x["LAC"] > x["NE"] > x["LV"] > x["LA"]


def _sim():
    rows = [
        (2010, 0, "LV", 6.0), (2010, 0, "MIA", 8.0), (2010, 1, "LV", 7.0),
        (2022, 0, "BUF", 10.0),
    ]
    return pl.DataFrame(
        [dict(season=s, week=w, franchise_id=t, playoff_prob=0.5, exp_wins=e) for s, w, t, e in rows],
        schema={"season": pl.Int32, "week": pl.Int32, "franchise_id": pl.String, "playoff_prob": pl.Float64, "exp_wins": pl.Float64},
    )


def test_expectations_source_tag(wt):
    v = vegas_expectations(wt)
    e = expectations(_sim(), v)
    assert e.columns == ["season", "franchise_id", "exp_total", "expectation_source"]
    assert e.height == 3  # week-0 rows only
    d = {(r["season"], r["franchise_id"]): r for r in e.to_dicts()}
    lv = v.filter((pl.col("season") == 2010) & (pl.col("franchise_id") == "LV"))["vegas_norm"][0]
    assert d[(2010, "LV")]["expectation_source"] == "vegas" and d[(2010, "LV")]["exp_total"] == lv
    assert d[(2010, "MIA")] == {"season": 2010, "franchise_id": "MIA", "exp_total": 8.0, "expectation_source": "model"}
    assert d[(2022, "BUF")]["expectation_source"] == "model"


def test_expectations_without_vegas():
    e = expectations(_sim())
    assert set(e["expectation_source"]) == {"model"}
    assert e["exp_total"].to_list() == [6.0, 8.0, 10.0]


def test_load_win_totals_reads_cache(tmp_path, monkeypatch):
    (tmp_path / "win_totals.csv").write_text(CSV)

    def boom(*a, **k):
        raise AssertionError("network used")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    assert load_win_totals(cache_dir=tmp_path).height == 6

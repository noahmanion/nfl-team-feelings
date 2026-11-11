"""Phase 8 records (INSIGHT-03, INSIGHT-04): extremes, exclusions, tiebreaks, streak records, markdown."""

import json
from datetime import date, timedelta

import polars as pl
import pytest

from fgs import insights, records
from fgs.paths import CACHE_DIR

D = date.fromisoformat


def _scored(rows: list[dict]) -> pl.DataFrame:
    base = {"season": 2020, "week": 1, "wins": 0, "losses": 0, "ties": 0, "score": 50, "composite": 0.0}
    return pl.DataFrame(
        [{**base, **r} for r in rows],
        schema={"season": pl.Int32, "week": pl.Int32, "franchise_id": pl.String, "wins": pl.Int64,
                "losses": pl.Int64, "ties": pl.Int64, "score": pl.Int32, "composite": pl.Float64},
    )


def _dates(season: int, n: int, start: str = "09-10") -> pl.DataFrame:
    d0 = D(f"{season}-{start}")
    rows = [(season, 0, D(f"{season}-04-25"))] + [(season, w, d0 + timedelta(days=7 * (w - 1))) for w in range(1, n + 1)]
    return pl.DataFrame(rows, orient="row", schema={"season": pl.Int32, "week": pl.Int32, "date": pl.Date})


def _season(fid: str, scores: list[int], season: int = 2020, comp: float = 0.0, w0: int | None = None) -> list[dict]:
    """Weeks 1..len(scores) (week 0 optional), wins accumulate on score >= 50."""
    rows, w_, l_ = [], 0, 0
    if w0 is not None:
        rows.append({"franchise_id": fid, "season": season, "week": 0, "score": w0, "composite": comp})
    for i, sc in enumerate(scores, 1):
        w_, l_ = (w_ + 1, l_) if sc >= 50 else (w_, l_ + 1)
        rows.append({"franchise_id": fid, "season": season, "week": i, "score": sc, "wins": w_, "losses": l_,
                     "composite": comp})
    return rows


def test_extremes_one_entry_per_team_season_reg_only():
    rows = _season("AAA", [30] * 17) + [{"franchise_id": "AAA", "week": 18, "score": 0, "wins": 9, "losses": 9}]  # POST
    rows += _season("AAA", [40] * 17, w0=0)[0:1]  # week 0 (preseason) never counts
    ext = records.team_season_extremes(_scored(rows), _dates(2020, 18))
    assert len(ext["saddest"]) == 1
    e = ext["saddest"][0]
    assert e["score"] == 30 and e["week"] == 1 and (e["wins"], e["losses"]) == (0, 17)


def test_extremes_week_is_first_time_min_reached():
    ext = records.team_season_extremes(_scored(_season("AAA", [40, 20, 10, 10, 30])), _dates(2020, 5))
    e = ext["saddest"][0]
    assert e["score"] == 10 and e["week"] == 3 and e["date"] == "2020-09-24"
    h = ext["happiest"][0]
    assert h["score"] == 40 and h["week"] == 1


def test_extremes_exclude_expansion_seeds():
    rows = _season("CLE", [0] * 16, season=1999) + _season("BUF", [5] * 16, season=1999)
    ext = records.team_season_extremes(_scored(rows), _dates(1999, 16))
    assert [(e["season"], e["franchise"]) for e in ext["saddest"]] == [(1999, "BUF")]


def test_extremes_tiebreak_mean_then_composite_input_order_independent():
    rows = (_season("AAA", [0, 30, 30]) + _season("BBB", [0, 10, 10]) + _season("CCC", [0, 10, 10], comp=-1.0)
            + _season("DDD", [0, 10, 10], comp=-1.0))
    a = records.team_season_extremes(_scored(rows), _dates(2020, 3))
    b = records.team_season_extremes(_scored(rows[::-1]), _dates(2020, 3))
    order = [e["franchise"] for e in a["saddest"]]
    assert order == ["CCC", "DDD", "BBB", "AAA"]  # same min 0; mean; composite; franchise
    assert order == [e["franchise"] for e in b["saddest"]]


def test_extremes_happiest_tiebreak_desc():
    rows = _season("AAA", [100, 60]) + _season("BBB", [100, 90]) + _season("CCC", [100, 90], comp=2.0)
    ext = records.team_season_extremes(_scored(rows), _dates(2020, 2))
    assert [e["franchise"] for e in ext["happiest"]] == ["CCC", "BBB", "AAA"]
    assert ext["happiest"][0]["mean"] == 95


def _runs(rows, dates, as_of):
    return insights.all_runs(insights.timelines(_scored(rows), dates), as_of)


def test_streak_records_order_and_seasons_records():
    dates = pl.concat([_dates(2020, 3), _dates(2021, 3)])
    rows = (_season("AAA", [5, 5, 5], 2020) + _season("AAA", [5, 60, 60], 2021, w0=5)
            + _season("BBB", [5, 60, 60], 2020) + _season("BBB", [60, 60, 60], 2021, w0=60))
    run_df = _runs(rows, dates, D("2022-01-01"))
    recs = records.final_records(_scored(rows))
    out = records.streak_records(run_df, "misery", recs, 2021)
    assert [r["franchise"] for r in out] == ["AAA", "BBB"]
    a = out[0]
    assert a["start"] == "2020-09-10" and a["end"] == "2021-09-17" and not a["active"]
    assert (a["start_season"], a["start_week"], a["end_season"], a["end_week"]) == (2020, 1, 2021, 1)
    assert a["seasons"] == [{"season": 2020, "wins": 0, "losses": 3, "ties": 0},
                            {"season": 2021, "wins": 2, "losses": 1, "ties": 0}]


def test_streak_records_active_through_latest_season_and_active_map():
    dates = pl.concat([_dates(2020, 2), _dates(2021, 2)])
    rows = _season("AAA", [90, 90], 2020) + _season("AAA", [90, 90], 2021, w0=90) + _season("BBB", [50, 50], 2020)
    run_df = _runs(rows, dates, D("2021-12-01"))
    out = records.streak_records(run_df, "joy", records.final_records(_scored(rows)), 2021)
    assert out[0]["active"] and out[0]["end"] is None and [s["season"] for s in out[0]["seasons"]] == [2020, 2021]
    assert out[0]["days"] == (D("2021-12-01") - D("2020-09-10")).days
    act = records.active_streaks(run_df)
    assert set(act) == {"AAA"} and act["AAA"]["kind"] == "joy" and act["AAA"]["start"] == "2020-09-10"


def test_streak_records_tiebreak_start_then_franchise():
    dates = _dates(2020, 4)
    rows = _season("BBB", [5, 5, 60, 60]) + _season("AAA", [5, 5, 60, 60]) + _season("CCC", [60, 5, 5, 60])
    out = records.streak_records(_runs(rows, dates, D("2021-01-01")), "misery", {}, 2020)
    assert [r["franchise"] for r in out] == ["AAA", "BBB", "CCC"]


def test_extremes_skip_in_progress_season():
    """WR-08: a season with unplayed REG games never ranks among the "ever" extremes."""
    from conftest import make_games
    games = make_games([("g1", 2020, 1, "REG", "2020-09-10", "AAA", "BBB", 1, 0, False),
                        ("g1b", 2020, 2, "REG", "2020-09-17", "AAA", "BBB", 1, 0, False),
                        ("g2", 2021, 1, "REG", "2021-09-09", "AAA", "BBB", 1, 0, False),
                        ("g3", 2021, 2, "REG", "2021-09-16", "AAA", "BBB", None, None, False)])
    assert records.in_progress_seasons(games) == {2021}
    rows = _season("AAA", [30, 40], 2020) + _season("AAA", [0], 2021) + _season("BBB", [100], 2021)  # all dated
    dates = pl.concat([_dates(2020, 2), _dates(2021, 1)])
    ext = records.team_season_extremes(_scored(rows), dates, records.in_progress_seasons(games))
    assert [(e["season"], e["franchise"]) for e in ext["saddest"]] == [(2020, "AAA")]
    assert [(e["season"], e["franchise"]) for e in ext["happiest"]] == [(2020, "AAA")]
    r = records.build_records(_scored(rows), games, D("2021-09-20"))
    assert {e["season"] for e in r["saddest"] + r["happiest"]} == {2020}


def _contract(scored, games, as_of):
    return records.build_records(scored, games, as_of)


def test_build_records_contract_and_notable_rank():
    from conftest import make_games
    games = make_games([(f"g{w}", 2008, w, "REG", (D("2008-09-07") + timedelta(days=7 * (w - 1))).isoformat(),
                         "DET", "AAA", 1, 0, False) for w in range(1, 4)])
    rows = _season("DET", [1, 1, 1], 2008) + _season("AAA", [0, 0, 0], 2008) + _season("BBB", [90, 90, 90], 2008)
    r = records.build_records(_scored(rows), games, D("2008-12-01"))
    assert set(r) == {"as_of", "saddest", "happiest", "misery", "joy", "active", "excluded", "notable"}
    assert r["as_of"] == "2008-12-01"
    assert set(r["saddest"][0]) == {"season", "franchise", "score", "week", "date", "wins", "losses", "ties", "mean"}
    assert {(e["season"], e["franchise"]) for e in r["excluded"]} == {(1999, "CLE"), (2002, "HOU")}
    assert r["notable"] == [{"season": 2008, "franchise": "DET", "list": "saddest", "rank": 2, "score": 1, "mean": 1,
                             "wins": 0, "losses": 3, "ties": 0}]
    assert set(r["misery"][0]) == {"franchise", "start", "end", "days", "active", "start_season", "start_week",
                                   "end_season", "end_week", "seasons"}
    assert set(r["active"]) == {"DET", "AAA", "BBB"}
    json.dumps(r, allow_nan=False)


def test_records_check_md_sections():
    from conftest import make_games
    games = make_games([("g1", 2007, 1, "REG", "2007-09-09", "NE", "AAA", 1, 0, False)])
    rows = _season("NE", [100], 2007) + _season("AAA", [5], 2007)
    md = records.records_check_md(records.build_records(_scored(rows), games, D("2008-01-01")))
    assert md.count("| # |") == 4
    for s in ("Notable non-entries", "## Excluded", "1999 CLE", "2002 HOU", "Reviewer checklist", "2007 NE"):
        assert s in md, s
    assert "Final REG 1-0; max score 100 first reached Week 1 (2007-09-09); REG mean 100" in md
    assert "2007-09-09 → still going; seasons: 2007 0-1" in md


def test_records_on_real_data_shape(real_inputs):
    if not (CACHE_DIR / "schedules.parquet").exists():
        pytest.skip("no cached schedules")
    from fgs.cli import derive
    from fgs.ingest import load_schedules
    from fgs.mood import score_frame

    derived = derive(load_schedules(), **real_inputs)
    r = records.build_records(score_frame(derived["features"]), derived["games"], D("2026-11-11"))
    assert all(len(r[k]) == 10 for k in ("saddest", "happiest", "misery", "joy"))
    seeds = {(1999, "CLE"), (2002, "HOU")}
    assert not any((e["season"], e["franchise"]) in seeds for e in r["saddest"] + r["happiest"])
    live = records.in_progress_seasons(derived["games"])
    assert not any(e["season"] in live for e in r["saddest"] + r["happiest"])
    assert {n["list"] for n in r["notable"]} == {"saddest", "happiest"} and len(r["notable"]) == 3
    json.dumps(r, allow_nan=False)
    md = records.records_check_md(r)
    assert "Notable non-entries" in md and md.count("| # |") == 4


def test_records_check_key_ignores_the_date_but_not_the_records(tmp_path, monkeypatch):
    """IN-06: a new export date (and the active-streak day counts it moves) never rewrites
    RECORDS_CHECK.md; any real change does."""
    from conftest import make_games
    from fgs import cli, paths

    games = make_games([("g1", 2007, 1, "REG", "2007-09-09", "NE", "AAA", 1, 0, False)])
    rows = _season("NE", [100], 2007) + _season("AAA", [5], 2007)
    r1 = records.build_records(_scored(rows), games, D("2008-01-01"))
    r2 = records.build_records(_scored(rows), games, D("2008-02-01"))
    assert r1["active"]["NE"]["days"] != r2["active"]["NE"]["days"]
    assert records.records_check_key(r1) == records.records_check_key(r2)
    r3 = records.build_records(_scored(_season("NE", [90], 2007) + _season("AAA", [5], 2007)), games, D("2008-02-01"))
    assert records.records_check_key(r3) != records.records_check_key(r1)

    path = tmp_path / "RECORDS_CHECK.md"
    monkeypatch.setattr(paths, "RECORDS_CHECK_PATH", path)
    assert cli._write_records_check({"records.json": r1}) == (path, True)
    first = path.read_text()
    assert "as of 2008-01-01" in first
    assert cli._write_records_check({"records.json": r2}) == (path, False)
    assert path.read_text() == first
    assert cli._write_records_check({"records.json": r3}) == (path, True)
    assert "as of 2008-02-01" in path.read_text()

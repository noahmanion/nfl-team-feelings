"""Phase 8 insights: record rank / perception gap (INSIGHT-02), movers (INSIGHT-06), copy helpers."""

import polars as pl
import pytest

from fgs import insights, season_config
from fgs.paths import CACHE_DIR

CALLOUT_KEYS = {"type", "season", "week", "franchise", "headline", "detail", "evidence", "stat", "start", "band"}
NICKS = {f: f"{f}nick" for f in ("AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH")}
EV = {
    "train_seasons": [1999, 2021],
    "hopeful": {"n": 504, "d_margin": 3.64, "team_win": 0.547, "peer_win": 0.448},
    "worried": {"n": 556, "d_margin": -3.15, "team_win": 0.4654, "peer_win": 0.543},
}


def _scored(rows: list[dict]) -> pl.DataFrame:
    """Scored-like frame: defaults for every column the insights read."""
    base = {"season": 2020, "week": 5, "wins": 0, "losses": 0, "ties": 0, "rank": 1, "score": 50,
            "score_delta": None, "rank_delta": None, "band": 3, "label": "L3"}
    return pl.DataFrame(
        [{**base, **r} for r in rows],
        schema={"season": pl.Int32, "week": pl.Int32, "franchise_id": pl.String, "wins": pl.Int64,
                "losses": pl.Int64, "ties": pl.Int64, "rank": pl.Int32, "score": pl.Int32,
                "score_delta": pl.Int32, "rank_delta": pl.Int32, "band": pl.Int32, "label": pl.String},
    )


def _tg(rows: list[tuple]) -> pl.DataFrame:
    """team_games-like: (season, asof_week, franchise, is_reg, played, pf, pa)."""
    return pl.DataFrame(
        rows, orient="row",
        schema={"season": pl.Int32, "asof_week": pl.Int32, "franchise_id": pl.String, "is_reg": pl.Boolean,
                "played": pl.Boolean, "points_for": pl.Int32, "points_against": pl.Int32},
    )


def _ranked(rows: list[dict]) -> pl.DataFrame:
    """record_ranks-like frame for the flag/callout tests (gap = record_rank - rank)."""
    df = _scored(rows)
    rr = [r.get("record_rank", 1) for r in rows]
    return df.with_columns(pl.Series("record_rank", rr, dtype=pl.Int32)).with_columns(
        (pl.col("record_rank") - pl.col("rank")).alias("gap")
    )


# --- record rank ----------------------------------------------------------------------------------

def _rr(df: pl.DataFrame) -> dict[str, int]:
    return dict(zip(df["franchise_id"], df["record_rank"]))


def test_gap_record_rank_point_differential_breaks_win_pct_ties():
    s = _scored([
        {"franchise_id": "AAA", "wins": 1, "losses": 1, "rank": 1},
        {"franchise_id": "BBB", "wins": 1, "losses": 1, "rank": 2},
        {"franchise_id": "CCC", "wins": 2, "losses": 0, "rank": 3},
    ])
    tg = _tg([(2020, 1, "AAA", True, True, 20, 17), (2020, 2, "AAA", True, True, 10, 10),  # +3
              (2020, 1, "BBB", True, True, 30, 10), (2020, 3, "BBB", True, True, 0, 10),   # +10
              (2020, 1, "CCC", True, True, 7, 6)])
    out = insights.record_ranks(s, tg)
    assert _rr(out) == {"CCC": 1, "BBB": 2, "AAA": 3}
    assert dict(zip(out["franchise_id"], out["gap"])) == {"CCC": -2, "BBB": 0, "AAA": 2}


def test_gap_record_rank_franchise_breaks_full_ties():
    s = _scored([{"franchise_id": f, "wins": 1, "losses": 1, "rank": i + 1} for i, f in enumerate(["CCC", "AAA", "BBB"])])
    out = insights.record_ranks(s, _tg([]))
    assert _rr(out) == {"AAA": 1, "BBB": 2, "CCC": 3}


def test_gap_record_rank_zero_games_is_500_and_ties_count_half():
    s = _scored([
        {"franchise_id": "AAA", "wins": 1, "losses": 0},
        {"franchise_id": "BBB", "wins": 0, "losses": 0, "ties": 0},
        {"franchise_id": "CCC", "wins": 0, "losses": 1},
        {"franchise_id": "DDD", "wins": 1, "losses": 1, "ties": 1},  # .500, PD 0 -> after BBB? same wp+pd -> id
    ])
    out = insights.record_ranks(s, _tg([]))
    assert _rr(out) == {"AAA": 1, "BBB": 2, "DDD": 3, "CCC": 4}


def test_gap_point_differential_counts_only_played_reg_games_known_by_the_week():
    s = _scored([
        {"franchise_id": "AAA", "week": 2, "wins": 1, "losses": 1},
        {"franchise_id": "BBB", "week": 2, "wins": 1, "losses": 1},
    ])
    tg = _tg([
        (2020, 1, "AAA", True, True, 10, 0),     # +10 counts
        (2020, 3, "AAA", True, True, 0, 50),     # future: ignored
        (2020, 1, "BBB", True, True, 20, 0),     # +20 counts
        (2020, 2, "BBB", False, True, 0, 40),    # postseason row: ignored
        (2020, 2, "BBB", True, False, 0, 40),    # unplayed: ignored
        (2019, 1, "AAA", True, True, 99, 0),     # other season: ignored
    ])
    out = insights.record_ranks(s, tg)
    assert dict(zip(out["franchise_id"], out["pd"])) == {"AAA": 10, "BBB": 20}
    assert _rr(out) == {"BBB": 1, "AAA": 2}


# --- gap flags / callouts -------------------------------------------------------------------------

def test_gap_flags_window_threshold_and_flavor():
    # 2020: reg_weeks 17 -> eligible weeks 4..16
    rows = [
        {"franchise_id": "AAA", "week": 3, "record_rank": 20, "rank": 2},   # week 3: never
        {"franchise_id": "BBB", "week": 4, "record_rank": 20, "rank": 12},  # +8 hopeful
        {"franchise_id": "CCC", "week": 4, "record_rank": 3, "rank": 11},   # -8 worried
        {"franchise_id": "DDD", "week": 4, "record_rank": 10, "rank": 3},   # +7: below threshold
        {"franchise_id": "EEE", "week": 16, "record_rank": 30, "rank": 1},  # last eligible week
        {"franchise_id": "FFF", "week": 17, "record_rank": 30, "rank": 1},  # final REG week: never
        {"franchise_id": "GGG", "week": 19, "record_rank": 30, "rank": 1},  # postseason: never
    ]
    f = insights.gap_flags(_ranked(rows))
    assert dict(zip(f["franchise_id"], f["flavor"])) == {"BBB": "hopeful", "CCC": "worried", "EEE": "hopeful"}


def test_gap_flags_use_reg_weeks_of_the_season():
    rows = [{"franchise_id": "AAA", "season": 2021, "week": 17, "record_rank": 30, "rank": 1},  # rw 18 -> ok
            {"franchise_id": "BBB", "season": 2020, "week": 17, "record_rank": 30, "rank": 1}]  # rw 17 -> no
    assert insights.gap_flags(_ranked(rows))["franchise_id"].to_list() == ["AAA"]


def test_gap_callouts_cap_keeps_largest_gaps_per_flavor():
    hopeful = [{"franchise_id": f, "record_rank": 20 + i, "rank": 12} for i, f in
               enumerate(["AAA", "BBB", "CCC", "DDD", "EEE"])]  # gaps 8..12
    worried = [{"franchise_id": "FFF", "record_rank": 1, "rank": 10}, {"franchise_id": "GGG", "record_rank": 2, "rank": 11}]
    out = insights.gap_callouts(_ranked(hopeful + worried), NICKS, EV)
    hope = [c["franchise"] for c in out if c["type"] == "hopeful"]
    assert hope == ["EEE", "DDD", "CCC"]
    assert sorted(c["franchise"] for c in out if c["type"] == "worried") == ["FFF", "GGG"]
    # uncapped flags still see all five
    assert insights.gap_flags(_ranked(hopeful + worried)).height == 7


def test_gap_callouts_cap_tiebreak_is_smaller_score_rank():
    rows = [{"franchise_id": f, "record_rank": r + 9, "rank": r} for f, r in
            [("AAA", 9), ("BBB", 4), ("CCC", 6), ("DDD", 2)]]  # all gap +9
    out = insights.gap_callouts(_ranked(rows), NICKS, EV)
    assert [c["franchise"] for c in out] == ["DDD", "BBB", "CCC"]


def test_gap_callout_copy_keys_and_stat():
    rows = [{"franchise_id": "AAA", "wins": 3, "losses": 1, "record_rank": 2, "rank": 13, "band": 2},
            {"franchise_id": "BBB", "wins": 1, "losses": 2, "ties": 1, "record_rank": 21, "rank": 1, "band": 5}]
    out = {c["franchise"]: c for c in insights.gap_callouts(_ranked(rows), NICKS, EV)}
    w, h = out["AAA"], out["BBB"]
    assert set(w) == CALLOUT_KEYS and set(h) == CALLOUT_KEYS
    assert w["type"] == "worried" and w["stat"] == -11 and w["band"] == 2 and w["start"] is None
    assert w["headline"] == "3-1, but you should feel worried"
    assert w["detail"] == "The AAAnick have the 2nd-best record but the 13th-best score."
    assert w["evidence"] == ("Teams with a gap this big won 47% of their next 8 games; teams with the same "
                             "record won 54% (556 cases, 1999–2021).")
    assert h["type"] == "hopeful" and h["stat"] == 20
    assert h["headline"] == "1-2-1, but better days are coming"
    assert h["detail"] == "The BBBnick have the 21st-best record but the best score."
    assert (w["season"], w["week"]) == (2020, 5) and isinstance(w["season"], int) and isinstance(w["stat"], int)


def test_gap_callouts_without_evidence_have_null_evidence():
    rows = [{"franchise_id": "AAA", "record_rank": 20, "rank": 1}]
    assert insights.gap_callouts(_ranked(rows), NICKS, None)[0]["evidence"] is None


# --- copy -----------------------------------------------------------------------------------------

def test_copy_record_text():
    assert insights.record_text(8, 2, 0) == "8-2"
    assert insights.record_text(5, 4, 1) == "5-4-1"


@pytest.mark.parametrize("n,txt", [(1, "best"), (2, "2nd-best"), (3, "3rd-best"), (4, "4th-best"), (11, "11th-best"),
                                   (12, "12th-best"), (13, "13th-best"), (21, "21st-best"), (22, "22nd-best"),
                                   (23, "23rd-best"), (32, "32nd-best")])
def test_copy_ordinal_best(n, txt):
    assert insights.ordinal_best(n) == txt


def test_copy_evidence_text():
    ev = {"train_seasons": [1999, 2021], "hopeful": {"n": 504, "d_margin": 3.6, "team_win": 0.5474, "peer_win": 0.4481}}
    assert insights.evidence_text("hopeful", ev) == (
        "Teams with a gap this big won 55% of their next 8 games; teams with the same record won 45% "
        "(504 cases, 1999–2021).")
    assert insights.evidence_text("hopeful", None) is None


@pytest.mark.parametrize("entry", [
    {"n": 0, "d_margin": None, "team_win": None, "peer_win": None},  # what peer_stats writes for no cases
    {"n": 5, "team_win": None, "peer_win": 0.4},
    {"n": 5, "team_win": "0.5", "peer_win": 0.4},
    None,  # flavor key missing
])
def test_copy_evidence_text_zero_or_bad_cases_gives_no_line(entry):
    """WR-03: no evidence line (and no crash) for an empty or malformed flavor."""
    ev = {"train_seasons": [1999, 2021], "worried": {"n": 9, "team_win": 0.4, "peer_win": 0.5}}
    if entry is not None:
        ev["hopeful"] = entry
    assert insights.evidence_text("hopeful", ev) is None
    assert insights.evidence_text("worried", ev) is not None


def test_gap_callouts_with_zero_case_evidence_do_not_crash():
    """WR-03: gap callouts still ship (evidence None) when a flavor has no cases."""
    ev = {"train_seasons": [1999, 2021], "hopeful": {"n": 0, "d_margin": None, "team_win": None, "peer_win": None},
          "worried": {"n": 0, "d_margin": None, "team_win": None, "peer_win": None}}
    rows = [{"franchise_id": "AAA", "wins": 3, "losses": 1, "record_rank": 2, "rank": 13},
            {"franchise_id": "BBB", "wins": 1, "losses": 3, "record_rank": 21, "rank": 1}]
    out = insights.gap_callouts(_ranked(rows), NICKS, ev)
    assert {c["type"] for c in out} == {"hopeful", "worried"} and all(c["evidence"] is None for c in out)


# --- movers ---------------------------------------------------------------------------------------

def _mover_frame(deltas: dict[str, tuple[int | None, int | None, int]], week: int = 5) -> pl.DataFrame:
    """deltas: franchise -> (score_delta, rank_delta, rank) for `week`; week-1 rows give prev labels."""
    rows = []
    for f, (sd, rd, rk) in deltas.items():
        rows.append({"franchise_id": f, "week": week - 1, "rank": rk, "label": "Old", "band": 1})
        rows.append({"franchise_id": f, "week": week, "score_delta": sd, "rank_delta": rd, "rank": rk,
                     "label": "New" if f != "AAA" else "Old", "band": 4})
    return _scored(rows)


def test_movers_top_three_each_way_with_tiebreaks():
    s = _mover_frame({
        "AAA": (9, 3, 5), "BBB": (5, 1, 9), "CCC": (5, 4, 12), "DDD": (5, 4, 3), "EEE": (2, 0, 20),
        "FFF": (-7, -2, 25), "GGG": (-1, 0, 18), "HHH": (0, 0, 15),
    })
    out = [c for c in insights.movers(s, NICKS) if c["week"] == 5]
    up = [c["franchise"] for c in out if c["type"] == "mover_up"]
    down = [c["franchise"] for c in out if c["type"] == "mover_down"]
    assert up == ["AAA", "DDD", "CCC"]  # 9; then 5s by |rank_delta| (4,4 -> rank 3 before 12), BBB out
    assert down == ["FFF", "GGG"]       # fewer than 3 fallers; zero delta never qualifies
    assert all(set(c) == CALLOUT_KEYS for c in out)


def test_movers_copy_and_stat():
    s = _mover_frame({"AAA": (9, 3, 5), "BBB": (-6, -2, 9)})
    out = {c["franchise"]: c for c in insights.movers(s, NICKS)}
    assert out["AAA"]["headline"] == "AAAnick +9" and out["AAA"]["stat"] == 9
    assert out["AAA"]["detail"] == "Still Old"
    assert out["BBB"]["headline"] == "BBBnick −6" and out["BBB"]["stat"] == -6
    assert out["BBB"]["detail"] == "Old → New"
    assert out["BBB"]["band"] == 4 and out["BBB"]["evidence"] is None and out["BBB"]["start"] is None


def test_movers_never_in_week_zero():
    s = _mover_frame({"AAA": (9, 3, 5), "BBB": (-6, -2, 9)}, week=1)
    w0 = _scored([{"franchise_id": "CCC", "week": 0, "score_delta": 20, "rank_delta": 5, "season": 2021}])
    out = insights.movers(pl.concat([s, w0]), NICKS)
    assert {c["week"] for c in out} == {1}


# --- assembly -------------------------------------------------------------------------------------

def test_callouts_by_week_orders_gaps_then_movers():
    s = _scored([
        {"franchise_id": "AAA", "week": 4, "wins": 0, "losses": 3, "rank": 1, "score_delta": 4, "rank_delta": 1},
        *[{"franchise_id": f, "week": 4, "wins": 2, "losses": 1, "rank": i + 2, "score_delta": -1 - i, "rank_delta": 0}
          for i, f in enumerate(["BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH"])],
        {"franchise_id": "ZZZ", "week": 4, "wins": 3, "losses": 0, "rank": 9, "score_delta": 0, "rank_delta": 0},
    ])
    by = insights.callouts_by_week(s, _tg([]), NICKS, EV)
    types = [c["type"] for c in by[(2020, 4)]]
    assert types[:2] in (["hopeful", "worried"], ["worried", "hopeful"])  # |gap| 8 and 8
    assert types[2:] == ["mover_up", "mover_down", "mover_down", "mover_down"]


# --- fingerprint ----------------------------------------------------------------------------------

def test_fingerprint_deterministic_order_independent_and_sensitive():
    a = insights.weights_fingerprint({"elo": 2.59, "mov": 1.24, "offseason.draft": 0.0})
    b = insights.weights_fingerprint({"offseason.draft": 0.0, "mov": 1.24, "elo": 2.59})
    assert a == b and len(a) == 12 and all(c in "0123456789abcdef" for c in a)
    assert insights.weights_fingerprint({"elo": 2.59, "mov": 1.25, "offseason.draft": 0.0}) != a
    assert insights.weights_fingerprint({"elo": 2.59, "mov": 1.24, "offseason.draft": 0.1}) != a


def test_fingerprint_weights_includes_offseason_draft():
    cfg = {"weight": 0.0, "display_only": True}
    m = insights.fingerprint_weights({"elo": 2.59}, cfg)
    assert m == {"elo": 2.59, "offseason.draft": 0.0, "offseason.draft.display_only": 1.0}
    assert insights.weights_fingerprint(m) != insights.weights_fingerprint(
        insights.fingerprint_weights({"elo": 2.59}, {"weight": 0.5, "display_only": False}))


# --- real data ------------------------------------------------------------------------------------

def test_gap_callouts_rate_on_real_data(real_inputs):
    if not (CACHE_DIR / "schedules.parquet").exists():
        pytest.skip("no cached schedules")
    from fgs.cli import derive
    from fgs.ingest import load_schedules
    from fgs.mood import score_frame

    derived = derive(load_schedules(), **real_inputs)
    ranked = insights.record_ranks(score_frame(derived["features"]), derived["team_games"])
    out = insights.gap_callouts(ranked, {}, None)
    per = pl.DataFrame({"s": [c["season"] for c in out], "w": [c["week"] for c in out]}).group_by("s", "w").len()
    eligible = ranked.filter(
        (pl.col("week") >= season_config.GAP_FIRST_WEEK)
        & (pl.col("week") <= pl.col("season").map_elements(season_config.reg_weeks, return_dtype=pl.Int32) - 1)
    ).select("season", "week").n_unique()
    mean = len(out) / eligible
    assert 1.5 <= mean <= 6, mean
    assert per["len"].max() <= 2 * season_config.GAP_CAP



# --- snapshot dates and streaks (INSIGHT-03) ------------------------------------------------------

from datetime import date  # noqa: E402

from conftest import make_games  # noqa: E402

D = date.fromisoformat


def test_draft_date_table_fallback_and_clamp(monkeypatch):
    assert season_config.draft_date(2014, D("2026-11-11")) == D("2014-05-10")
    monkeypatch.setattr(season_config, "DRAFT_END", {})
    assert season_config.draft_date(2027, D("2027-11-01")) == D("2027-09-01")
    assert season_config.draft_date(2027, D("2027-05-20")) == D("2027-05-20")  # clamped: never in the future


def test_snapshot_dates_last_played_gameday_per_asof_week_and_draft_week0():
    g = make_games([
        ("a", 2023, 1, "REG", "2023-09-07", "BUF", "MIA", 1, 0, False),
        ("b", 2023, 1, "REG", "2023-09-11", "NE", "NYJ", 1, 0, False),   # MNF: week 1 date
        ("c", 2023, 2, "REG", "2023-09-17", "MIA", "NE", 1, 0, False),
        ("d", 2023, 2, "REG", "2023-09-18", "NYJ", "BUF", None, None, False),  # unplayed: ignored
    ])
    out = insights.snapshot_dates(g, D("2026-11-11"))
    got = {(s, w): d for s, w, d in out.iter_rows()}
    assert got == {(2023, 0): D("2023-04-29"), (2023, 1): D("2023-09-11"), (2023, 2): D("2023-09-17")}


def test_snapshot_dates_use_asof_week_when_present():
    g = make_games([
        ("a", 2023, 1, "REG", "2023-09-10", "BUF", "MIA", 1, 0, False),
        ("b", 2023, 1, "REG", "2023-09-20", "NE", "NYJ", 1, 0, False),  # postponed: known in week 2
    ]).with_columns(pl.Series("asof_week", [1, 2], dtype=pl.Int32))
    got = {(s, w): d for s, w, d in insights.snapshot_dates(g, D("2026-11-11")).iter_rows()}
    assert got[(2023, 1)] == D("2023-09-10") and got[(2023, 2)] == D("2023-09-20")


AS_OF = D("2021-01-01")


def test_streak_runs_ended_active_and_days():
    ds = [D("2020-01-01"), D("2020-01-11"), D("2020-01-21"), D("2020-02-01"), D("2020-02-11")]
    out = insights.runs(ds, [10, 5, 50, 3, 1], lambda x: x <= 19, AS_OF)
    assert [(r["start"], r["end"], r["days"], r["active"]) for r in out] == [
        (D("2020-01-01"), D("2020-01-21"), 20, False),
        (D("2020-02-01"), None, (AS_OF - D("2020-02-01")).days, True),
    ]
    assert insights.runs(ds, [50] * 5, lambda x: x <= 19, AS_OF) == []


def _tl(rows):
    """scored-like rows (franchise, season, week, score) for timelines()."""
    return _scored([{"franchise_id": f, "season": s, "week": w, "score": sc} for f, s, w, sc in rows])


def _dates(rows):
    return pl.DataFrame(rows, orient="row", schema={"season": pl.Int32, "week": pl.Int32, "date": pl.Date})


def test_streak_crosses_season_boundary_as_one_run():
    dates = _dates([(2020, 0, D("2020-04-25")), (2020, 1, D("2020-09-14")), (2020, 2, D("2020-09-21")),
                    (2021, 0, D("2021-05-01")), (2021, 1, D("2021-09-13"))])
    s = _tl([("AAA", 2020, 0, 50), ("AAA", 2020, 1, 15), ("AAA", 2020, 2, 10), ("AAA", 2021, 0, 12),
             ("AAA", 2021, 1, 40)])
    r = insights.all_runs(insights.timelines(s, dates), D("2021-12-01")).filter(pl.col("kind") == "misery")
    assert r.height == 1
    row = r.row(0, named=True)
    assert row["start"] == D("2020-09-14") and row["end"] == D("2021-09-13") and not row["active"]
    assert row["days"] == (D("2021-09-13") - D("2020-09-14")).days
    assert (row["start_season"], row["start_week"], row["end_season"], row["end_week"]) == (2020, 1, 2021, 0)


def test_streak_timelines_drop_seeded_week0_rows():
    dates = _dates([(1999, 0, D("1999-04-18")), (1999, 1, D("1999-09-13"))])
    s = _tl([("CLE", 1999, 0, 2), ("CLE", 1999, 1, 5), ("BUF", 1999, 0, 5), ("BUF", 1999, 1, 5)])
    tl = insights.timelines(s, dates)
    assert tl.filter(pl.col("franchise_id") == "CLE")["week"].to_list() == [1]
    assert tl.filter(pl.col("franchise_id") == "BUF")["week"].to_list() == [0, 1]
    r = insights.all_runs(tl, D("1999-12-01")).filter(pl.col("franchise_id") == "CLE").row(0, named=True)
    assert r["start"] == D("1999-09-13") and r["active"]  # week-1+ misery still counts


def test_streak_timelines_raise_on_undated_snapshot():
    with pytest.raises(ValueError, match="no date"):
        insights.timelines(_tl([("AAA", 2020, 3, 50)]), _dates([(2020, 0, D("2020-04-25"))]))


def test_streak_joy_threshold_inclusive_and_misery_is_under_20():
    assert insights.streak_cond("joy")(80) and not insights.streak_cond("joy")(79)
    assert insights.streak_cond("misery")(19) and not insights.streak_cond("misery")(20)


def _weekly(n_weeks: int, start: date, step: int = 7) -> pl.DataFrame:
    from datetime import timedelta
    return _dates([(2020, w, start + timedelta(days=step * w)) for w in range(n_weeks)])


def test_streak_callouts_floor_and_one_per_kind_longest_wins():
    dates = _weekly(20, D("2020-01-01"))  # weeks 0..19, 7 days apart
    s = _tl([*[("AAA", 2020, w, 5) for w in range(20)],             # misery from day 0
             *[("BBB", 2020, w, 5 if w >= 3 else 50) for w in range(20)],  # shorter misery
             *[("CCC", 2020, w, 90) for w in range(20)]])             # joy from day 0
    tl = insights.timelines(s, dates)
    bands = {(2020, w, f): 1 for w in range(20) for f in ("AAA", "BBB", "CCC")}
    out = insights.streak_callouts(insights.all_runs(tl, D("2020-06-01")), dates, NICKS, bands)
    weeks = sorted({c["week"] for c in out})
    assert weeks == list(range(15, 20))  # 15 * 7 = 105 >= 100; 14 * 7 = 98 < 100
    for w in weeks:
        cs = [c for c in out if c["week"] == w]
        assert sorted(c["type"] for c in cs) == ["joy", "misery"]
        m = next(c for c in cs if c["type"] == "misery")
        assert m["franchise"] == "AAA" and m["stat"] == 7 * w and m["start"] == "2020-01-01"
    c = out[0]
    assert set(c) == CALLOUT_KEYS and c["evidence"] is None and c["band"] == 1
    assert c["headline"] == "AAAnick fans have been miserable for 105 straight days"
    assert c["detail"] == "Score under 20 since Jan 1, 2020, as of Apr 15, 2020."
    j = next(x for x in out if x["type"] == "joy")
    assert j["headline"] == "CCCnick fans have been buying the jersey for 105 straight days"
    assert j["detail"] == "Score 80 or higher since Jan 1, 2020, as of Apr 15, 2020."


def test_streak_callouts_latest_week_counts_through_as_of():
    """WR-01: the latest week counts through the export date (same as records.json active); earlier
    weeks keep their own week date."""
    dates = _weekly(20, D("2020-01-01"))  # week 19 = 2020-05-13
    s = _tl([("AAA", 2020, w, 5) for w in range(20)])
    tl = insights.timelines(s, dates)
    bands = {(2020, w, "AAA"): 1 for w in range(20)}
    as_of = D("2020-05-20")
    run_df = insights.all_runs(tl, as_of)
    out = insights.streak_callouts(run_df, dates, NICKS, bands, latest=(2020, 19), as_of=as_of)
    by_week = {c["week"]: c for c in out}
    assert by_week[19]["stat"] == 140 == run_df.filter(pl.col("active"))["days"].item()
    assert by_week[19]["detail"].endswith("as of May 20, 2020.")
    assert by_week[18]["stat"] == 7 * 18 and by_week[18]["detail"].endswith("as of May 6, 2020.")


def test_streak_callouts_skip_ended_runs():
    dates = _weekly(20, D("2020-01-01"))
    s = _tl([("AAA", 2020, w, 5 if w < 16 else 50) for w in range(20)])  # ends at week 16
    out = insights.streak_callouts(insights.all_runs(insights.timelines(s, dates), D("2020-06-01")), dates, NICKS,
                                   {(2020, w, "AAA"): 1 for w in range(20)})
    assert [c["week"] for c in out] == [15]


def test_streak_date_text_and_thousands():
    assert insights.date_text(D("2005-09-11")) == "Sep 11, 2005"


def test_callouts_by_week_streaks_between_gaps_and_movers():
    from datetime import timedelta
    dates_games = make_games([(f"g{w}", 2020, w, "REG", (D("2020-09-01") + timedelta(days=7 * w)).isoformat(),
                               "AAA", "BBB", 1, 0, False) for w in range(1, 18)])
    rows = [{"franchise_id": "AAA", "week": w, "score": 5, "score_delta": 1 if w == 17 else 0, "rank_delta": 0}
            for w in range(0, 18)]
    by = insights.callouts_by_week(_scored(rows), _tg([]), NICKS, None, games=dates_games, as_of=D("2021-01-01"))
    types = [c["type"] for c in by[(2020, 17)]]
    assert types == ["misery", "mover_up"]
    assert insights.callouts_by_week(_scored(rows), _tg([]), NICKS, None).get((2020, 17)) is not None
    assert all(c["type"] != "misery" for cs in insights.callouts_by_week(_scored(rows), _tg([]), NICKS, None).values()
               for c in cs)


def test_snapshot_dates_increase_per_franchise_on_real_data(real_inputs):
    if not (CACHE_DIR / "schedules.parquet").exists():
        pytest.skip("no cached schedules")
    from fgs.cli import derive
    from fgs.ingest import load_schedules
    from fgs.mood import score_frame

    derived = derive(load_schedules(), **real_inputs)
    dates = insights.snapshot_dates(derived["games"], D("2026-11-11"))
    tl = insights.timelines(score_frame(derived["features"]), dates)  # raises if any snapshot is undated
    bad = tl.with_columns(pl.col("date").diff().over("franchise_id").alias("_d")).filter(
        pl.col("_d").is_not_null() & (pl.col("_d") <= pl.duration(days=0)))
    assert bad.height == 0, bad.head()

"""fgs.pbp: synthetic-play unit tests + real-cache integration tests (skip without a pbp cache)."""

import polars as pl
import pytest

from fgs import pbp
from fgs.franchises import CANONICAL
from fgs.paths import CACHE_DIR

G1 = "2001_01_MIA_BUF"  # BUF home, MIA away
G2 = "2000_01_NYJ_NE"   # low-confidence season


def _play(gid, off, dfn, epa, *, pass_=0, rush=0, db=0, wp=0.5, success=None, pt=None,
          kneel=0, spike=0, passer_id=None, passer=None, ppid=None, ppname=None, rusher=None,
          rusher_name=None):
    season = int(gid[:4])
    if success is None:
        success = None if epa is None else int(epa > 0)
    if pt is None:
        pt = "pass" if pass_ else ("run" if rush else "no_play")
    return dict(
        game_id=gid, season=season, week=1, season_type="REG", posteam=off, defteam=dfn,
        play_type=pt, **{"pass": pass_}, rush=rush, qb_dropback=db, qb_kneel=kneel, qb_spike=spike,
        epa=epa, wp=wp, success=success, passer_id=passer_id, passer=passer,
        passer_player_id=ppid, passer_player_name=ppname, rusher_player_id=rusher,
        rusher_player_name=rusher_name,
    )


def _plays(rows) -> pl.DataFrame:
    schema = {
        "game_id": pl.String, "season": pl.Int32, "week": pl.Int32, "season_type": pl.String,
        "posteam": pl.String, "defteam": pl.String, "play_type": pl.String,
        "pass": pl.Float64, "rush": pl.Float64, "qb_dropback": pl.Float64, "qb_kneel": pl.Float64,
        "qb_spike": pl.Float64, "epa": pl.Float64, "wp": pl.Float64, "success": pl.Float64,
        "passer_id": pl.String, "passer": pl.String, "passer_player_id": pl.String,
        "passer_player_name": pl.String, "rusher_player_id": pl.String, "rusher_player_name": pl.String,
    }
    assert list(schema) == pbp.SLIM_COLUMNS
    return pl.DataFrame(rows, schema=schema)


def _synthetic() -> pl.DataFrame:
    q1 = dict(passer_id="Q1", passer="Q.One")
    rows = [
        # --- G1, BUF offense (kept: 0.5, 0.8, 0.2, -1.0) ---
        _play(G1, "BUF", "MIA", 0.5, pass_=1, db=1, ppid="Q1", ppname="Q.One", **q1),
        _play(G1, "BUF", "MIA", 0.8, rush=1, db=1, rusher="Q1", pt="run", **q1),  # scramble: ppid null
        _play(G1, "BUF", "MIA", 0.2, rush=1, rusher="R1"),
        _play(G1, "BUF", "MIA", -1.0, pass_=1, db=1, passer_id="Q9", passer="Q.Nine", ppid="Q9"),
        # dropped BUF plays
        _play(G1, "BUF", "MIA", -0.1, pass_=1, db=1, spike=1, ppid="Q1", **q1),        # spike
        _play(G1, "BUF", "MIA", -0.2, kneel=1, pt="qb_kneel"),                          # kneel
        _play(G1, "BUF", "MIA", 2.0, pass_=1, db=1, pt="no_play", ppid="Q1", **q1),    # no_play
        _play(G1, "BUF", "MIA", None, pass_=1, db=1, ppid="Q1", **q1),                 # null epa
        _play(G1, "BUF", "MIA", 3.0, pass_=1, db=1, wp=0.97, ppid="Q1", **q1),         # garbage time
        # --- G1, MIA offense (kept: -0.4, 0.1, 0.0 at the wp=0.05 boundary) ---
        _play(G1, "MIA", "BUF", -0.4, pass_=1, db=1, passer_id="Q5", passer="Q.Five", ppid="Q5"),
        _play(G1, "MIA", "BUF", 0.1, rush=1, rusher="R5"),
        _play(G1, "MIA", "BUF", 0.0, pass_=1, db=1, wp=0.05, success=0, passer_id="Q5", ppid="Q5",
              ppname="Q.Five"),  # passer null -> name falls back to passer_player_name
        _play(G1, "", "BUF", 5.0, rush=1),                                              # posteam ''
        # --- G2, NE offense: B7 and A1 tie on 1 dropback -> A1 (lower id) ---
        _play(G2, "NE", "NYJ", 0.4, pass_=1, db=1, passer_id="B7", passer="B.Seven", ppid="B7"),
        _play(G2, "NE", "NYJ", -0.2, pass_=1, db=1, passer_id="A1", passer="A.One", ppid="A1"),
        # --- G2, NYJ offense: null qb_dropback is not a dropback ---
        _play(G2, "NYJ", "NE", -0.5, rush=1, rusher="R7"),
        _play(G2, "NYJ", "NE", 0.3, pass_=1, db=None, passer_id="N1", passer="N.One", ppid="N1"),
    ]
    return _plays(rows)


def _row(df, gid, team) -> dict:
    rows = df.filter((pl.col("game_id") == gid) & (pl.col("franchise_id") == team)).to_dicts()
    assert len(rows) == 1
    return rows[0]


def test_scrimmage_keeps_only_clean_scrimmage_plays():
    s = pbp.scrimmage(_synthetic())
    assert sorted(s["epa"].to_list()) == sorted([0.5, 0.8, 0.2, -1.0, -0.4, 0.1, 0.0, 0.4, -0.2, -0.5, 0.3])
    assert s.filter(pl.col("posteam") == "").height == 0
    scramble = s.filter(pl.col("epa") == 0.8).row(0, named=True)
    assert scramble["qb_id"] == "Q1" and scramble["qb_name"] == "Q.One"


def test_team_game_epa_columns_and_shape():
    t = pbp.team_game_epa(_synthetic())
    assert t.columns == pbp.TGE_COLUMNS
    assert t.height == 4
    assert t.select("game_id", "franchise_id").is_unique().all()
    assert t["game_id"].to_list() == sorted(t["game_id"].to_list())


def test_team_game_epa_off_def_net_means():
    t = pbp.team_game_epa(_synthetic())
    buf, mia = _row(t, G1, "BUF"), _row(t, G1, "MIA")
    assert buf["off_epa"] == pytest.approx(0.125)       # (0.5 + 0.8 + 0.2 - 1.0) / 4
    assert buf["off_plays"] == 4
    assert buf["off_sr"] == pytest.approx(0.75)
    assert mia["off_epa"] == pytest.approx(-0.1)        # (-0.4 + 0.1 + 0.0) / 3
    assert mia["off_plays"] == 3
    assert mia["off_sr"] == pytest.approx(1 / 3)
    assert buf["def_epa"] == pytest.approx(-0.1) and buf["def_plays"] == 3
    assert mia["def_epa"] == pytest.approx(0.125) and mia["def_plays"] == 4
    assert buf["net_epa"] == pytest.approx(0.225)
    assert mia["net_epa"] == pytest.approx(-0.225)
    ne, nyj = _row(t, G2, "NE"), _row(t, G2, "NYJ")
    assert ne["off_epa"] == pytest.approx(0.1) and nyj["off_epa"] == pytest.approx(-0.1)
    assert ne["net_epa"] == pytest.approx(0.2)


def test_team_game_primary_qb_counts_scrambles():
    t = pbp.team_game_epa(_synthetic())
    buf = _row(t, G1, "BUF")
    assert buf["qb_id"] == "Q1" and buf["qb_name"] == "Q.One"
    assert buf["dropbacks"] == 2
    assert buf["qb_epa"] == pytest.approx(0.65)         # (0.5 + 0.8) / 2
    assert buf["qb_sr"] == pytest.approx(1.0)
    assert buf["team_db"] == 3
    assert buf["team_db_epa_sum"] == pytest.approx(0.3)  # 0.5 + 0.8 - 1.0
    mia = _row(t, G1, "MIA")
    assert mia["qb_id"] == "Q5" and mia["qb_name"] == "Q.Five"
    assert mia["qb_epa"] == pytest.approx(-0.2) and mia["qb_sr"] == pytest.approx(0.0)


def test_team_game_primary_qb_tie_lowest_id_and_null_dropback():
    t = pbp.team_game_epa(_synthetic())
    ne = _row(t, G2, "NE")
    assert ne["qb_id"] == "A1" and ne["dropbacks"] == 1 and ne["qb_epa"] == pytest.approx(-0.2)
    nyj = _row(t, G2, "NYJ")
    assert nyj["qb_id"] is None and nyj["dropbacks"] is None and nyj["team_db"] is None


def test_team_game_low_confidence_by_season():
    t = pbp.team_game_epa(_synthetic())
    lc = dict(zip(t["game_id"], t["low_confidence"]))
    assert lc[G2] is True and lc[G1] is False
    assert t["season"].dtype == pl.Int32


def test_scramble_only_qb_gets_name():
    """IN-02: a QB whose only dropbacks were scrambles gets his name from rusher_player_name."""
    plays = _plays([
        _play(G1, "BUF", "MIA", 0.4, rush=1, db=1, rusher="Q7", rusher_name="Q.Seven", pt="run"),
        _play(G1, "BUF", "MIA", 0.1, rush=1, rusher="R1", rusher_name="R.One", pt="run"),  # designed run
        _play(G1, "MIA", "BUF", 0.2, pass_=1, db=1, passer_id="Q5", passer="Q.Five", ppid="Q5"),
    ])
    buf = _row(pbp.team_game_epa(plays), G1, "BUF")
    assert buf["qb_id"] == "Q7" and buf["qb_name"] == "Q.Seven"
    # an old slim cache without the column still works (name stays null)
    old = pbp.team_game_epa(plays.drop("rusher_player_name"))
    assert _row(old, G1, "BUF")["qb_id"] == "Q7" and _row(old, G1, "BUF")["qb_name"] is None


def test_team_game_epa_rejects_unknown_codes():
    bad = _plays([_play(G1, "XXX", "BUF", 0.1, rush=1)])
    with pytest.raises(ValueError, match="XXX"):
        pbp.team_game_epa(bad)


def _tg(game_ids, played=True):
    return pl.DataFrame(
        [dict(game_id=g, franchise_id=t, played=played) for g in game_ids for t in ("AAA", "BBB")]
    )


def test_check_pbp_known_gaps_pass():
    t = pbp.team_game_epa(_synthetic())
    tg = pl.concat([_tg([G1, G2]), _tg(sorted(pbp.KNOWN_NO_PBP)), _tg(["2001_02_X_Y"], played=False)])
    assert pbp.check_pbp(t, tg) == []


def test_check_pbp_flags_new_gap_and_extra_game():
    t = pbp.team_game_epa(_synthetic())
    fails = pbp.check_pbp(t, _tg([G1, "2001_05_NE_MIA"]))
    assert any("2001_05_NE_MIA" in f and "no pbp" in f for f in fails)
    assert any(G2 in f and "not a played schedule game" in f for f in fails)


def test_check_pbp_flags_null_off_def():
    t = pbp.team_game_epa(_synthetic()).with_columns(
        pl.when(pl.col("franchise_id") == "BUF").then(None).otherwise(pl.col("def_epa")).alias("def_epa"))
    fails = pbp.check_pbp(t, _tg([G1, G2]))
    assert any("BUF" in f and "null" in f for f in fails)


def _tg_dated(rows):
    """team_games with season/gameday: rows = (game_id, season, gameday)."""
    return pl.DataFrame(
        [dict(game_id=g, season=s, gameday=d, franchise_id=t, played=True) for g, s, d in rows for t in ("AAA", "BBB")]
    )


def test_pbp_lag_recent_current_season_gap_warns_not_fails():
    """WR-02: a current-season game played within PBP_LAG_DAYS of the latest played gameday and
    missing from pbp is a warning; an older current-season gap still fails."""
    t = pbp.team_game_epa(_synthetic())  # has G1 (2001) and G2 (2000)
    tg = _tg_dated([
        (G2, 2000, "2000-09-03"), (G1, 2001, "2001-09-09"),
        ("2001_02_NE_NYJ", 2001, "2001-09-16"),  # 7 days before latest -> hard gap
        ("2001_03_NE_MIA", 2001, "2001-09-21"),  # 2 days before latest -> lagging
        ("2001_03_BUF_IND", 2001, "2001-09-23"),  # latest -> lagging
    ])
    fails = pbp.check_pbp(t, tg)
    assert fails == ["2001_02_NE_NYJ: played game has no pbp"]
    warns = pbp.pbp_lag(t, tg)
    assert len(warns) == 2 and all("no pbp yet" in w for w in warns)
    assert any("2001_03_NE_MIA" in w for w in warns) and any("2001_03_BUF_IND" in w for w in warns)


def test_pbp_lag_missing_current_season_file_warns():
    """No current-season pbp at all (file not released yet): every current-season gap warns."""
    t = pbp.team_game_epa(_synthetic()).filter(pl.col("season") == 2000)
    tg = _tg_dated([(G2, 2000, "2000-09-03"), (G1, 2001, "2001-09-09"), ("2001_05_NE_MIA", 2001, "2001-10-07")])
    assert pbp.check_pbp(t, tg) == []
    assert len(pbp.pbp_lag(t, tg)) == 2
    # a prior-season gap is never lagging
    tg_old = _tg_dated([(G2, 2000, "2000-09-03"), ("2000_02_NE_MIA", 2000, "2000-09-10"), (G1, 2001, "2001-09-09")])
    assert pbp.check_pbp(pbp.team_game_epa(_synthetic()), tg_old) == ["2000_02_NE_MIA: played game has no pbp"]


# --- real cache --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def real_tge():
    seasons = pbp.cached_seasons(CACHE_DIR)
    if not seasons or not (CACHE_DIR / "schedules.parquet").exists():
        pytest.skip("no pbp cache; run `uv run fgs build` first")
    return pbp.team_game_epa(pbp.load_all_pbp(seasons, CACHE_DIR, write_cache=False))


def test_real_codes_and_shape(real_tge):
    assert set(real_tge["franchise_id"]) <= CANONICAL
    assert real_tge.height == 2 * real_tge["game_id"].n_unique()
    assert real_tge.height >= 14818
    lc = real_tge.filter(pl.col("low_confidence"))["season"].unique().sort().to_list()
    assert lc == [1999, 2000]


def test_real_coverage_is_known_gaps_only(real_tge):
    from fgs.games import build_games, build_team_games
    from fgs.ingest import load_schedules

    games = build_games(load_schedules(cache_dir=CACHE_DIR))
    played = set(games.filter(pl.col("played"))["game_id"].to_list())
    assert played - set(real_tge["game_id"]) == set(pbp.KNOWN_NO_PBP)
    assert pbp.check_pbp(real_tge, build_team_games(games)) == []

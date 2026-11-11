"""Snapshot grid semantics: byes, week 0, REG-only records, playoff weeks, current-season cutoff."""

import polars as pl
import pytest

from fgs.elo import replay
from fgs.games import build_team_games
from fgs.season_config import MEAN_ELO, n_teams
from fgs.snapshots import SNAPSHOT_COLUMNS, build_grid


@pytest.fixture
def syn(synthetic_games):
    games, sparse = replay(synthetic_games)
    tg = build_team_games(games)
    return games, tg, build_grid(games, tg, sparse)


def _at(snap: pl.DataFrame, season: int, week: int, team: str) -> dict:
    rows = snap.filter(
        (pl.col("season") == season) & (pl.col("week") == week) & (pl.col("franchise_id") == team)
    )
    assert rows.height == 1, (season, week, team, rows.height)
    return rows.row(0, named=True)


# ---- synthetic -------------------------------------------------------------------------------

def test_columns_are_phase2_contract(syn):
    assert syn[2].columns == SNAPSHOT_COLUMNS
    assert SNAPSHOT_COLUMNS == ["season", "week", "franchise_id", "elo", "wins", "losses", "ties", "win_pct"]


def test_grid_is_dense_and_has_no_null_elo(syn):
    games, _, snap = syn
    for season in (2023, 2024):
        wmax = games.filter((pl.col("season") == season) & pl.col("played"))["week"].max()
        assert snap.filter(pl.col("season") == season).height == 4 * (wmax + 1)
    assert snap["elo"].null_count() == 0
    assert snap.filter(pl.col("season") == 2023)["week"].max() == 19
    assert snap.filter(pl.col("season") == 2024)["week"].max() == 2  # unplayed wk2 game, but NYJ-MIA played


def test_bye_week_carries_elo_forward(syn):
    snap = syn[2]
    for team in ("BUF", "NE"):  # both idle in 2023 week 3
        assert _at(snap, 2023, 3, team)["elo"] == _at(snap, 2023, 2, team)["elo"]
    # and through the empty REG weeks 4..18
    assert _at(snap, 2023, 18, "NYJ")["elo"] == _at(snap, 2023, 3, "NYJ")["elo"]


def test_week0_is_regressed_prior_final(syn):
    snap = syn[2]
    for team in ("BUF", "MIA", "NE", "NYJ"):
        prev = _at(snap, 2023, 19, team)["elo"]
        assert _at(snap, 2024, 0, team)["elo"] == pytest.approx(MEAN_ELO / 3 + 2 / 3 * prev, abs=1e-9)
    for team in ("BUF", "MIA", "NE", "NYJ"):  # first season: no games yet, unseeded = mean
        r = _at(snap, 2023, 0, team)
        assert r["elo"] == MEAN_ELO
        assert (r["wins"], r["losses"], r["ties"], r["win_pct"]) == (0, 0, 0, None)


def test_tie_counts_once_for_both_and_records_are_reg_only(syn):
    _, tg, snap = syn
    for team in ("NE", "NYJ"):
        r = _at(snap, 2023, 1, team)
        assert (r["wins"], r["losses"], r["ties"]) == (0, 0, 1)
        assert r["win_pct"] == 0.5
    reg_played = (
        tg.filter((pl.col("season") == 2023) & pl.col("is_reg") & pl.col("played"))
        .group_by("franchise_id").len()
    )
    for team, n in reg_played.iter_rows():
        r = _at(snap, 2023, 18, team)
        assert r["wins"] + r["losses"] + r["ties"] == n


def test_playoff_game_moves_elo_not_record(syn):
    snap = syn[2]
    for team in ("BUF", "MIA"):
        before, after = _at(snap, 2023, 18, team), _at(snap, 2023, 19, team)
        assert after["elo"] != before["elo"]
        assert (after["wins"], after["losses"], after["ties"]) == (
            before["wins"], before["losses"], before["ties"]
        )
    for team in ("NE", "NYJ"):  # not in the playoffs: frozen
        assert _at(snap, 2023, 19, team)["elo"] == _at(snap, 2023, 18, team)["elo"]


def test_unplayed_game_counts_for_nothing(syn):
    snap = syn[2]
    for team in ("BUF", "NE"):  # 2024 wk2 NE@BUF has no result
        wk1, wk2 = _at(snap, 2024, 1, team), _at(snap, 2024, 2, team)
        assert (wk2["wins"], wk2["losses"], wk2["ties"], wk2["elo"]) == (
            wk1["wins"], wk1["losses"], wk1["ties"], wk1["elo"]
        )
        assert wk2["wins"] + wk2["losses"] + wk2["ties"] == 1


# ---- real data -------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def real():
    from fgs.paths import CACHE_DIR

    path = CACHE_DIR / "schedules.parquet"
    if not path.exists():
        pytest.skip("no cached schedules; run `uv run fgs build` first")
    from fgs.cli import derive

    raw = pl.read_parquet(path)
    return raw, derive(raw)


def test_real_2025_grid_and_eliminated_team_frozen(real):
    _, d = real
    snap, tg = d["snapshots"], d["team_games"]
    s25 = snap.filter(pl.col("season") == 2025)
    assert s25["franchise_id"].n_unique() == 32
    assert s25.height == 32 * 23
    assert s25["week"].min() == 0 and s25["week"].max() == 22
    last = (
        tg.filter((pl.col("season") == 2025) & pl.col("played"))
        .sort("week").group_by("franchise_id").last()
    )
    eliminated = last.filter(pl.col("week") < 22)
    assert eliminated.height >= 30
    for team, elo_post in eliminated.select("franchise_id", "elo_post").iter_rows():
        assert _at(snap, 2025, 22, team)["elo"] == elo_post


def test_real_team_counts_and_final_weeks(real):
    _, d = real
    snap, games = d["snapshots"], d["games"]
    assert snap.filter(pl.col("season") == 1999)["franchise_id"].n_unique() == 31
    max_season = games["season"].max()
    last = snap.group_by("season").agg(pl.col("week").max().alias("w")).sort("season")
    for season, w in last.iter_rows():
        if season < max_season:
            assert w == (21 if season <= 2020 else 22), season
            sb = games.filter((pl.col("season") == season) & (pl.col("game_type") == "SB"))
            assert sb["week"].to_list() == [w]
        assert snap.filter(pl.col("season") == season)["franchise_id"].n_unique() == n_teams(season)


def test_real_current_season_ends_at_latest_played_week(real):
    _, d = real
    snap, games = d["snapshots"], d["games"]
    cur = games["season"].max()
    latest = games.filter((pl.col("season") == cur) & pl.col("played"))["week"].max()
    assert snap.filter(pl.col("season") == cur)["week"].max() == latest
    if cur == 2026:
        assert latest < 18


def test_check_snapshot_grid(real):
    from fgs.checks import CHECKS, check_snapshot_grid

    _, d = real
    snap, games = d["snapshots"], d["games"]
    assert check_snapshot_grid(snap, games) == []
    assert "snapshot_grid" in [name for name, _ in CHECKS]

    dropped = snap.slice(1, snap.height - 1)  # removes 1999 week 0 for one team
    assert check_snapshot_grid(dropped, games) != []

    nulled = snap.with_row_index().with_columns(
        pl.when(pl.col("index") == 500).then(None).otherwise(pl.col("elo")).alias("elo")
    ).drop("index")
    assert check_snapshot_grid(nulled, games) != []

    duped = pl.concat([snap, snap.head(1)])
    assert check_snapshot_grid(duped, games) != []

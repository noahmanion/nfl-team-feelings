import re

import polars as pl
import pytest

from fgs.paths import CACHE_DIR

ROW = re.compile(r"^\s*(\d+)\s+([A-Z]{2,3})\s+(\d+)\s+(\d+-\d+-\d+)\s*$")


def _rows(out: str) -> list[tuple[int, str, int, str]]:
    return [
        (int(m[1]), m[2], int(m[3]), m[4])
        for line in out.splitlines()
        if (m := ROW.match(line))
    ]


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """Build from the cached schedules into a temp derived dir; never touches data/derived or the network."""
    if not (CACHE_DIR / "schedules.parquet").exists():
        pytest.skip("no cached schedules; run `uv run fgs build` first")
    import fgs.cli as cli

    mp = pytest.MonkeyPatch()
    mp.setattr(cli, "DERIVED_DIR", tmp_path_factory.mktemp("derived"))
    try:
        assert cli.main(["build"]) == 0
        yield cli.main
    finally:
        mp.undo()


def _latest_played(cache_path) -> tuple[int, int] | None:
    """(season, week) of the latest played game in the cached schedules, or None."""
    raw = pl.read_parquet(cache_path)
    played = raw.filter(pl.col("result").is_not_null())
    if played.is_empty():
        return None
    season = played["season"].max()
    week = played.filter(pl.col("season") == season)["week"].max()
    return int(season), int(week)


def test_build_then_elo_prints_ranking(built, capsys):
    from fgs.franchises import CANONICAL

    latest = _latest_played(CACHE_DIR / "schedules.parquet")
    if latest is None:
        pytest.skip("cache has no played games")
    season, week = latest
    capsys.readouterr()
    assert built(["elo", "--season", str(season), "--week", str(week)]) == 0
    out = capsys.readouterr().out
    rows = _rows(out)
    assert f"{season} week {week}" in out
    assert len(rows) == 32
    assert "BUF" in out
    assert {team for _, team, _, _ in rows} <= CANONICAL
    assert [r[0] for r in rows] == list(range(1, 33))


def test_week0_1999_seeds(built, capsys):
    capsys.readouterr()
    assert built(["elo", "--season", "1999", "--week", "0"]) == 0
    rows = _rows(capsys.readouterr().out)
    assert len(rows) == 31
    by_team = {team: elo for _, team, elo, _ in rows}
    assert by_team["CLE"] == 1300
    assert rows[0][2] == 1505
    assert all(elo == 1505 for team, elo in by_team.items() if team != "CLE")
    assert all(rec == "0-0-0" for *_, rec in rows)

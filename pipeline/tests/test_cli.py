"""`fgs elo` as-of semantics on synthetic derived data in a tmp dir (no network, no real cache)."""

import re

import pytest

import fgs.cli as cli
from fgs.elo import replay
from fgs.games import build_team_games
from fgs.snapshots import build_grid

ROW = re.compile(r"^\s*(\d+)\s+([A-Z]{2,3})\s+(\d+)\s+(\d+-\d+-\d+)\s*$")


def _rows(out: str) -> list[str]:
    return [m[2] for line in out.splitlines() if (m := ROW.match(line))]


@pytest.fixture
def derived(synthetic_games, tmp_path, monkeypatch):
    games, sparse = replay(synthetic_games)
    tg = build_team_games(games)
    out = {"games": games, "team_games": tg, "snapshots": build_grid(games, tg, sparse)}
    out["games"].write_parquet(tmp_path / "games.parquet")
    out["snapshots"].write_parquet(tmp_path / "elo_snapshots.parquet")
    monkeypatch.setattr(cli, "DERIVED_DIR", tmp_path)
    return out


def test_default_is_latest_season_latest_played_week(derived, capsys):
    assert cli.main(["elo"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("2024 week 2 (data through 2024-09-15)")
    assert len(_rows(out)) == 4


def test_season_only_uses_that_seasons_latest_week(derived, capsys):
    assert cli.main(["elo", "--season", "2023"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "2023 week 19 (data through 2024-01-14)"


def test_explicit_week_header_uses_games_up_to_that_week(derived, capsys):
    assert cli.main(["elo", "--season", "2023", "--week", "3"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "2023 week 3 (data through 2023-09-24)"
    assert "partial week" not in out


def test_beyond_latest_played_week_errors(derived, capsys):
    assert cli.main(["elo", "--season", "2024", "--week", "5"]) == 1
    err = capsys.readouterr().err
    assert "2024 week 5 not played yet; latest played week is 2" in err


def test_season_not_in_data_errors_with_range(derived, capsys):
    assert cli.main(["elo", "--season", "1998"]) == 1
    err = capsys.readouterr().err
    assert "1998" in err and "2023-2024" in err


def test_partial_week_note(derived, capsys):
    assert cli.main(["elo", "--season", "2024", "--week", "2"]) == 0
    out = capsys.readouterr().out
    assert "partial week: 1 of 2 games played" in out.splitlines()[0]


def test_top_limits_rows_and_default_prints_all(derived, capsys):
    assert cli.main(["elo", "--season", "2023", "--week", "1", "--top", "2"]) == 0
    assert len(_rows(capsys.readouterr().out)) == 2
    assert cli.main(["elo", "--season", "2023", "--week", "1"]) == 0
    assert len(_rows(capsys.readouterr().out)) == 4


def test_week0_uses_prior_data_and_lists_all_teams(derived, capsys):
    assert cli.main(["elo", "--season", "2024", "--week", "0"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "2024 week 0 (data through 2024-01-14)"
    assert len(_rows(out)) == 4


def test_build_prints_data_through(derived, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_schedules", lambda refresh=False: derived["games"])
    monkeypatch.setattr(cli, "derive", lambda raw: derived)
    assert cli.main(["build"]) == 0
    assert "data through 2024-09-15" in capsys.readouterr().out

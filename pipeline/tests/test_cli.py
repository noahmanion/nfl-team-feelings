"""`fgs elo` as-of semantics on synthetic derived data in a tmp dir (no network, no real cache)."""

import re
import shutil

import pytest

import fgs.cli as cli

ROW = re.compile(r"^\s*(\d+)\s+([A-Z]{2,3})\s+(\d+)\s+(\d+-\d+-\d+)\s*$")


def _rows(out: str) -> list[str]:
    return [m[2] for line in out.splitlines() if (m := ROW.match(line))]


@pytest.fixture
def derived(synthetic_games, tmp_path, monkeypatch):
    out = cli.derive_games(synthetic_games)
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


@pytest.mark.parametrize("top", ["0", "-3"])
def test_top_rejects_non_positive(derived, capsys, top):
    assert cli.main(["elo", "--season", "2023", "--week", "1", "--top", top]) == 1
    assert "--top must be >= 1" in capsys.readouterr().err


def test_week0_uses_prior_data_and_lists_all_teams(derived, capsys):
    assert cli.main(["elo", "--season", "2024", "--week", "0"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "2024 week 0 (data through 2024-01-14)"
    assert len(_rows(out)) == 4


def test_build_prints_data_through(derived, tmp_path, monkeypatch, capsys):
    import polars as pl

    tge = pl.DataFrame({"game_id": ["g"], "franchise_id": ["BUF"]})
    calls = []
    monkeypatch.setattr(cli, "load_schedules", lambda refresh=False: derived["games"])
    monkeypatch.setattr(cli, "load_all_pbp", lambda seasons, cache_dir, refresh_seasons=(): calls.append(
        (list(seasons), list(refresh_seasons))))
    monkeypatch.setattr(cli, "team_game_epa", lambda plays: tge)
    monkeypatch.setattr(cli, "load_win_totals", lambda: "wt")
    monkeypatch.setattr(cli, "vegas_expectations", lambda wt: None)
    monkeypatch.setattr(cli.draft, "load_draft_picks", lambda refresh=False: pl.DataFrame(
        {"season": [2024], "round": [1], "pick": [1], "team": ["BUF"]}))
    monkeypatch.setattr(cli.draft, "load_draft_values", lambda: pl.DataFrame(
        {"pick": list(range(1, 263)), "stuart": [1.0] * 262}))
    seen = {}
    monkeypatch.setattr(cli, "derive", lambda raw, pbp_games=None, **kw: (
        seen.update(kw), {**derived, "team_game_epa": pbp_games})[1])
    assert cli.main(["build"]) == 0
    assert calls == [(list(range(1999, 2025)), [])]
    out = capsys.readouterr().out
    assert "data through 2024-09-15" in out
    assert "pbp: 1 team-games, seasons 1999-2024" in out
    assert (tmp_path / "team_game_epa.parquet").exists()
    assert seen["sim_cache_dir"] == cli.sim_cache_dir() and "vegas" in seen
    assert seen["draft_picks"]["franchise_id"].to_list() == ["BUF"] and len(seen["draft_values"]) == 263


# --- fgs refresh: check-then-write (network mocked by reading the caches) -------------------

def _cached_inputs():
    from fgs.paths import CACHE_DIR
    if not (CACHE_DIR / "schedules.parquet").exists() or not (CACHE_DIR / "teams.parquet").exists():
        pytest.skip("no cached schedules/teams")
    from fgs.ingest import load_schedules, load_teams
    return load_schedules(), load_teams()


def _mock_pbp(monkeypatch, current):
    """Network mock for pbp: the 'download' of `current` reads the real cache (or a tiny synthetic
    frame without one); earlier seasons are served from the real cache via cli.load_all_pbp."""
    import polars as pl

    from fgs import pbp
    from fgs.paths import CACHE_DIR

    real = pbp.cached_seasons(CACHE_DIR)
    if real:
        earlier = [s for s in real if s < current]
        monkeypatch.setattr(cli, "cached_seasons", lambda cache_dir: earlier)
        monkeypatch.setattr(cli, "load_all_pbp", lambda seasons, cache_dir, **kw: pbp.load_all_pbp(
            seasons, CACHE_DIR, write_cache=False))
    calls = []

    def fake_load(season, refresh=False, cache_dir=None, write_cache=True):
        calls.append((season, refresh, write_cache))
        if real and season in real:
            return pbp.load_pbp_season(season, cache_dir=CACHE_DIR, write_cache=False)
        return pl.DataFrame(schema={c: pl.String for c in pbp.SLIM_COLUMNS})  # no plays

    monkeypatch.setattr(cli, "load_pbp_season", fake_load)
    return calls


def _current(raw):
    return cli.pbp_seasons(raw)[-1]


CACHE_FILES = ("schedules.parquet", "teams.parquet")
FROZEN_FILES = ("win_totals.csv", "draft_values.csv")


def _fake_draft_picks(refresh=False, cache_dir=None, write_cache=True):
    """Network mock for the draft picks 'download': the real cache, else a failed download."""
    import polars as pl

    from fgs.paths import CACHE_DIR
    path = CACHE_DIR / "draft_picks.parquet"
    if not path.exists():
        raise OSError("no network in tests")
    return pl.read_parquet(path)


@pytest.fixture
def refresh_dirs(tmp_path, monkeypatch):
    derived_dir, web_dir, cache_dir = tmp_path / "derived", tmp_path / "web", tmp_path / "cache"
    for d in (derived_dir, web_dir):
        d.mkdir()
        (d / "SENTINEL").write_bytes(b"untouched\n")
    cache_dir.mkdir()
    for f in CACHE_FILES:  # stand-ins for the last good raw cache
        (cache_dir / f).write_bytes(b"good cache: " + f.encode())
    from fgs.paths import CACHE_DIR as REAL_CACHE
    for frozen in FROZEN_FILES:  # frozen files; refresh must not hit the network
        if (REAL_CACHE / frozen).exists():
            shutil.copy(REAL_CACHE / frozen, cache_dir / frozen)
    monkeypatch.setattr(cli.draft, "load_draft_picks", _fake_draft_picks)
    monkeypatch.setattr(cli, "DERIVED_DIR", derived_dir)
    monkeypatch.setattr(cli, "WEB_DATA_DIR", web_dir)
    monkeypatch.setattr(cli, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(cli, "SIM_CACHE_DIR", None)  # sim cache under the tmp derived dir
    return derived_dir, web_dir, cache_dir


def test_refresh_aborts_without_writing_on_bad_code(refresh_dirs, monkeypatch, capsys):
    import polars as pl
    raw, teams = _cached_inputs()
    bad = raw.head(1).with_columns(pl.lit("XXX").alias("home_team"), pl.lit("2099_01_XXX_BUF").alias("game_id"))
    monkeypatch.setattr(cli, "load_schedules", lambda **kw: pl.concat([raw, bad]))
    monkeypatch.setattr(cli, "load_teams", lambda **kw: teams)
    _mock_pbp(monkeypatch, _current(raw))
    assert cli.main(["refresh"]) == 1
    cap = capsys.readouterr()
    assert "FAIL" in cap.out and "cache and JSON not updated" in cap.err
    derived_dir, web_dir, cache_dir = refresh_dirs
    for d in (derived_dir, web_dir):
        assert [p.name for p in d.iterdir()] == ["SENTINEL"]
        assert (d / "SENTINEL").read_bytes() == b"untouched\n"
    assert sorted(p.name for p in cache_dir.iterdir() if p.name not in FROZEN_FILES) == list(CACHE_FILES)  # no pbp/ or picks
    for f in CACHE_FILES:  # the bad download never replaced the good raw cache
        assert (cache_dir / f).read_bytes() == b"good cache: " + f.encode()


def test_refresh_happy_path_writes_parquet_and_json(refresh_dirs, monkeypatch, capsys):
    raw, teams = _cached_inputs()
    calls = []
    monkeypatch.setattr(cli, "load_schedules", lambda **kw: (calls.append(kw), raw)[1])
    monkeypatch.setattr(cli, "load_teams", lambda **kw: (calls.append(kw), teams)[1])
    current = _current(raw)
    pbp_calls = _mock_pbp(monkeypatch, current)
    assert cli.main(["refresh"]) == 0
    assert calls == [{"refresh": True, "write_cache": False}, {"refresh": True, "write_cache": False}]
    from fgs.pbp import cached_seasons
    from fgs.paths import CACHE_DIR
    if cached_seasons(CACHE_DIR):  # only the current season is re-downloaded, in memory
        assert pbp_calls == [(current, True, False)]
    derived_dir, web_dir, cache_dir = refresh_dirs
    import polars as pl
    assert pl.read_parquet(cache_dir / "schedules.parquet").equals(raw)  # cache saved only after checks
    assert pl.read_parquet(cache_dir / "teams.parquet").equals(teams)
    if (CACHE_DIR / "draft_picks.parquet").exists():  # picks saved only after checks pass
        assert (cache_dir / "draft_picks.parquet").exists()
    for f in ("games.parquet", "team_games.parquet", "elo_snapshots.parquet", "features.parquet"):
        assert (derived_dir / f).exists()
    if cached_seasons(CACHE_DIR):  # pbp saved only after checks pass
        assert (cache_dir / "pbp" / f"{current}.parquet").exists()
        assert sorted(p.name for p in (cache_dir / "pbp").iterdir()) == [f"{current}.parquet"]
        assert (derived_dir / "team_game_epa.parquet").exists()
    sims = list((derived_dir / "sim").glob("*.parquet"))  # written only after checks pass
    assert [p.name for p in sims] == [f"{cli.sim.model_version()}.parquet"]
    for f in ("meta.json", "latest.json", "callouts.json", "history.json"):
        assert (web_dir / f).exists()
    assert len(list((web_dir / "teams").iterdir())) == 32
    assert any((web_dir / "snapshots").iterdir())
    out = capsys.readouterr().out
    assert "all checks passed" in out and re.search(r"refreshed in \d+\.\ds: exported", out)
    if (CACHE_DIR / "draft_picks.parquet").exists():
        assert re.search(r"^ok\s+draft_coverage$", out, re.M) and re.search(r"^ok\s+draft_sum$", out, re.M)
    assert not (cache_dir / cli.REFRESH_MARKER).exists()  # write sequence completed


def test_interrupted_refresh_blocks_export_and_fails_check(refresh_dirs, monkeypatch, capsys):
    """WR-03: a crash mid-write leaves the marker; export refuses and check fails until a refresh completes."""
    raw, _ = _cached_inputs()
    derived_dir, web_dir, cache_dir = refresh_dirs
    (cache_dir / cli.REFRESH_MARKER).write_text("refresh started\n")
    assert cli.main(["export"]) == 1
    assert "interrupted mid-write" in capsys.readouterr().err
    assert [p.name for p in web_dir.iterdir()] == ["SENTINEL"]
    monkeypatch.setattr(cli, "load_schedules", lambda **kw: raw)
    monkeypatch.setattr(cli, "cached_inputs", lambda: {"pbp_games": None, "vegas": None})
    assert cli.main(["check"]) == 1
    assert "FAIL  refresh_complete" in capsys.readouterr().out


def test_refresh_tolerates_missing_current_season_pbp(refresh_dirs, monkeypatch, capsys):
    """WR-02: the current season's pbp download fails (release not posted / lagging the schedule).
    Refresh still succeeds: the lagging games are a warning, not a failed check, and nothing is
    written for the season that failed to download."""
    from fgs import pbp
    from fgs.paths import CACHE_DIR

    if not pbp.cached_seasons(CACHE_DIR):
        pytest.skip("no pbp cache")
    raw, teams = _cached_inputs()
    monkeypatch.setattr(cli, "load_schedules", lambda **kw: raw)
    monkeypatch.setattr(cli, "load_teams", lambda **kw: teams)
    current = _current(raw)
    _mock_pbp(monkeypatch, current)

    def missing(season, **kw):
        raise FileNotFoundError(f"no pbp release for {season}")

    monkeypatch.setattr(cli, "load_pbp_season", missing)
    assert cli.main(["refresh"]) == 0
    cap = capsys.readouterr()
    assert "pbp download failed" in cap.err
    assert "warn  pbp_lag" in cap.out and "all checks passed" in cap.out
    cache_dir = refresh_dirs[2]
    assert not (cache_dir / "pbp" / f"{current}.parquet").exists()


def test_refresh_recomputes_only_current_season(refresh_dirs, monkeypatch, capsys):
    """Warm the tmp sim cache as of last week (current season's latest played week unplayed),
    then refresh: only the current season is re-simulated, once per snapshot week."""
    import polars as pl

    from fgs import sim

    raw, teams = _cached_inputs()
    derived_dir = refresh_dirs[0]
    current = _current(raw)
    played = raw.filter(pl.col("result").is_not_null() & (pl.col("season") == current))
    if played.is_empty():
        pytest.skip("current season has no played games")
    last_week = int(played["week"].max())
    stale = raw.with_columns(
        pl.when((pl.col("season") == current) & (pl.col("week") == last_week)).then(None)
        .otherwise(pl.col(c)).alias(c)
        for c in ("home_score", "away_score", "result")
    )
    cli.derive(stale, scored=False, sim_cache_dir=derived_dir / "sim")  # warm cache, last week

    monkeypatch.setattr(cli, "load_schedules", lambda **kw: raw)
    monkeypatch.setattr(cli, "load_teams", lambda **kw: teams)
    _mock_pbp(monkeypatch, current)
    calls = []
    real = sim.simulate_season

    def counting(sg, *a, **k):
        calls.append(int(sg["season"][0]))
        return real(sg, *a, **k)

    monkeypatch.setattr(sim, "simulate_season", counting)
    assert cli.main(["refresh"]) == 0
    snaps = pl.read_parquet(derived_dir / "elo_snapshots.parquet")
    n_weeks = snaps.filter(pl.col("season") == current)["week"].n_unique()
    assert set(calls) == {current} and len(calls) == n_weeks
    assert "refreshed in" in capsys.readouterr().out


def test_unscored_derive_needs_no_weights_file(synthetic_games, tmp_path, monkeypatch):
    import fgs.paths

    monkeypatch.setattr(fgs.paths, "WEIGHTS_PATH", tmp_path / "missing.yaml")
    out = cli.derive_games(synthetic_games, scored=False)
    assert set(out) == {"games", "team_games", "snapshots", "team_game_epa", "sim", "vegas", "draft", "draft_values"}
    assert out["draft"] is None and out["draft_values"] is None  # no draft inputs given
    assert out["sim"].height == out["snapshots"].height  # sims run even when unscored
    assert out["team_game_epa"] is None


def test_derive_carries_pbp_games(synthetic_games, monkeypatch):
    import polars as pl

    from fgs.pbp import TGE_COLUMNS

    # one pbp row for a game that is not in the schedule: carried through, joins to nothing
    tge = pl.DataFrame({"game_id": ["g"], "season": [2023], "franchise_id": ["BUF"]}).with_columns(
        pl.lit(None, pl.Float64).alias(c) for c in TGE_COLUMNS if c not in ("game_id", "season", "franchise_id")
    ).with_columns(pl.col("season").cast(pl.Int32), pl.col("qb_id").cast(pl.String), pl.col("qb_name").cast(pl.String))
    assert cli.derive_games(synthetic_games, scored=False, pbp_games=tge)["team_game_epa"] is tge
    assert cli.derive_games(synthetic_games, None, None, pbp_games=tge)["team_game_epa"] is tge


# --- Phase 7 review fixes: winsor caps (IN-05, IN-06) ------------------------------------------

def _sur_frame():
    import polars as pl

    rows = [(2005, f"T{i}", float(i)) for i in range(101)]
    return pl.DataFrame(rows, schema={"season": pl.Int32, "franchise_id": pl.String, "surplus": pl.Float64},
                        orient="row")


def test_draft_winsor_uses_frozen_caps(capsys):
    assert cli.draft_winsor(_sur_frame(), {"winsor": (-1.0, 2.0)}) == (-1.0, 2.0)
    assert capsys.readouterr().err == ""


def test_draft_winsor_missing_warns_and_recomputes(capsys):
    """IN-06: no offseason.draft.winsor no longer drops the draft display data silently."""
    assert cli.draft_winsor(_sur_frame(), {"winsor": None}) == (5.0, 95.0)
    assert "no offseason.draft.winsor" in capsys.readouterr().err

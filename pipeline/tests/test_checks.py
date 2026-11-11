"""Integration tests for fgs.checks and `fgs check` on the real cached schedules (skip if no cache)."""

import polars as pl
import pytest

from fgs import checks, cli, season_config
from fgs.cli import derive
from fgs.ingest import load_schedules
from fgs.paths import CACHE_DIR
from conftest import derive_inputs


@pytest.fixture(scope="module")
def real_cache():
    # Module-scoped override of conftest.real_cache so module-scoped fixtures can depend on it.
    path = CACHE_DIR / "schedules.parquet"
    if not path.exists():
        pytest.skip("no cached schedules; run `uv run fgs build` first")
    return path


@pytest.fixture(scope="module")
def real_raw(real_cache):
    return load_schedules(cache_dir=real_cache.parent)


@pytest.fixture(scope="module")
def real_derived(real_raw):
    return derive(real_raw, **derive_inputs())


def test_columns(real_raw):
    assert checks.check_columns(real_raw) == []


def test_codes_known(real_raw):
    assert checks.check_codes(real_raw) == []


def test_config_coverage(real_derived):
    assert checks.check_config_coverage(real_derived["games"]) == []


def test_divisions(real_derived):
    assert checks.check_divisions(real_derived["games"]) == []


def test_team_counts_31_then_32(real_derived):
    games = real_derived["games"]
    assert checks.check_team_counts(games) == []
    per = pl.concat([games.select("season", f=pl.col("home_id")), games.select("season", f=pl.col("away_id"))])
    counts = dict(per.unique().group_by("season").len().iter_rows())
    assert counts[2001] == 31 and counts[2002] == 32


def test_games_per_team(real_derived):
    games = real_derived["games"]
    assert checks.check_games_per_team(games) == []
    reg22 = games.filter((pl.col("season") == 2022) & pl.col("is_reg"))
    for team in ("BUF", "CIN"):
        n = reg22.filter((pl.col("home_id") == team) | (pl.col("away_id") == team)).height
        assert n == 16, team


def test_games_per_team_detects_missing_game(real_derived):
    games = real_derived["games"]
    victim = games.filter((pl.col("season") == 2010) & pl.col("is_reg")).row(0, named=True)
    fails = checks.check_games_per_team(games.filter(pl.col("game_id") != victim["game_id"]))
    assert any(f.startswith(f"2010 {victim['home_id']}:") for f in fails)
    assert any(f.startswith(f"2010 {victim['away_id']}:") for f in fails)


def test_continuity(real_derived):
    assert checks.check_continuity(real_derived["games"], real_derived["snapshots"]) == []
    w0 = real_derived["snapshots"].filter(pl.col("week") == 0)
    max_season = real_derived["games"]["season"].max()  # every scheduled season has week-0 rows
    for team in ("LV", "LAC", "LA", "WAS"):
        seasons = set(w0.filter(pl.col("franchise_id") == team)["season"].to_list())
        assert set(range(1999, max_season + 1)) <= seasons, team


def test_continuity_detects_reset(real_derived):
    snaps = real_derived["snapshots"].with_columns(
        pl.when((pl.col("season") == 2020) & (pl.col("week") == 0) & (pl.col("franchise_id") == "LV"))
        .then(pl.lit(1505.0)).otherwise(pl.col("elo")).alias("elo")
    )
    fails = checks.check_continuity(real_derived["games"], snaps)
    assert any(f.startswith("2020 LV:") for f in fails)


def test_result_consistency(real_derived):
    assert checks.check_result_consistency(real_derived["games"]) == []


def test_elo_zero_sum(real_derived):
    assert checks.check_elo_zero_sum(real_derived["games"]) == []


def test_league_mean(real_derived):
    assert checks.check_league_mean(real_derived["snapshots"]) == []


def test_elo_sanity(real_derived):
    """Coarse plausibility: top-5 Elo teams are not losing, bottom-5 are not winning.

    Uses >= rather than > so a legitimately .500 or tied team cannot fail the test; the
    human-style plausibility review happens in plan 03. Evaluated at the final REG week of the
    latest *completed* season (Super Bowl played), so early-season noise and the calendar
    cannot make it fail.
    """
    snaps, games = real_derived["snapshots"], real_derived["games"]
    season = games.filter((pl.col("game_type") == "SB") & pl.col("played"))["season"].max()
    week = season_config.reg_weeks(season)
    latest = snaps.filter((pl.col("season") == season) & (pl.col("week") == week)).sort("elo", descending=True)
    assert latest.height == season_config.n_teams(season)
    for r in latest.head(5).iter_rows(named=True):
        assert r["wins"] >= r["losses"], r
    for r in latest.tail(5).iter_rows(named=True):
        assert r["losses"] >= r["wins"], r


def test_divisions_detects_wrong_table(real_derived, monkeypatch):
    bad = {k: list(v) for k, v in season_config.DIVISIONS_2002_ON.items()}
    bad["AFC East"][0], bad["NFC East"][0] = bad["NFC East"][0], bad["AFC East"][0]
    monkeypatch.setattr(season_config, "DIVISIONS_2002_ON", bad)
    assert checks.check_divisions(real_derived["games"]) != []


def test_check_cli_real_data(real_raw, capsys):
    assert cli.main(["check"]) == 0
    out = capsys.readouterr().out
    assert "FAIL" not in out and "all checks passed" in out


def test_check_cli_never_writes_sim_cache(monkeypatch):
    """IN-01: `fgs check` is read-only; it reuses the sim cache but never rewrites it."""
    seen = {}
    monkeypatch.setattr(cli, "load_schedules", lambda *a, **k: None)
    monkeypatch.setattr(cli, "cached_inputs", lambda: {"pbp_games": None, "vegas": None})
    monkeypatch.setattr(cli, "_checked_derive", lambda raw, **kw: (seen.update(kw), (True, None, None))[1])
    assert cli.main(["check"]) == 0
    assert seen["sim_write_cache"] is False and seen["sim_cache_dir"] == cli.sim_cache_dir()


def test_check_cli_bad_code(real_raw, monkeypatch, capsys):
    tampered = real_raw.with_row_index("_i").with_columns(
        pl.when(pl.col("_i") == 0).then(pl.lit("XXX")).otherwise(pl.col("home_team")).alias("home_team")
    ).drop("_i")
    monkeypatch.setattr(cli, "load_schedules", lambda *a, **k: tampered)
    assert cli.main(["check"]) == 1
    out = capsys.readouterr().out
    assert "XXX" in out and "FAIL  codes" in out


def test_pbp_coverage_real(real_derived, real_raw):
    if real_derived["team_game_epa"] is None:
        pytest.skip("no pbp cache; run `uv run fgs build` first")
    results = dict(checks.run_checks(real_raw, real_derived))
    assert "pbp_coverage" in results
    assert results["pbp_coverage"] == []


def test_pbp_coverage_skipped_without_pbp(real_raw):
    d = derive(real_raw, scored=False, sim_cache_dir=derive_inputs()["sim_cache_dir"])
    assert dict(checks.run_checks(real_raw, d))["pbp_coverage"] == []


def test_sim_sums_real(real_derived, real_raw):
    assert real_derived["sim"] is not None
    assert dict(checks.run_checks(real_raw, real_derived))["sim_sums"] == []


def test_sim_sums_tampered(real_derived):
    sim = real_derived["sim"]
    s, w = 2010, 5
    hit = (pl.col("season") == s) & (pl.col("week") == w) & (pl.col("franchise_id") == "BUF")
    bad = sim.with_columns(pl.when(hit).then(pl.col("playoff_prob") + 0.01).otherwise(pl.col("playoff_prob")).alias("playoff_prob"))
    fails = checks.check_sim(bad, real_derived["games"])
    assert fails == [f"{s} week {w}: playoff_prob sums to {season_config.playoff_teams(s) + 0.01:.6f}, expected 12"]
    worse = bad.with_columns(pl.when(hit).then(pl.col("exp_wins") - 1).otherwise(pl.col("exp_wins")).alias("exp_wins"))
    assert len(checks.check_sim(worse, real_derived["games"])) == 2


def test_sim_sums_skip_synthetic(synthetic_games):
    d = cli.derive_games(synthetic_games, scored=False)
    bad = d["sim"].with_columns(pl.col("playoff_prob") * 0)
    assert checks.check_sim(bad, d["games"]) == []  # 4-team league: not a real season shape


def test_week_date_order(real_derived):
    assert checks.check_week_date_order(real_derived["games"]) == []


def test_continuity_follows_params(real_raw):
    """Continuity validates the params replay actually used, not hardcoded defaults (WR-04)."""
    from fgs.elo import EloParams

    params = EloParams(revert=0.25)
    d = derive(real_raw, params)
    assert checks.check_continuity(d["games"], d["snapshots"], params) == []
    assert checks.check_continuity(d["games"], d["snapshots"]) != []  # default revert disagrees


def test_vegas_coverage():
    """WR-04: missing win_totals for 2003-2020 seasons fails loudly; out-of-range leagues pass."""
    games = pl.DataFrame({"season": [2002, 2003, 2004, 2021]})
    vegas = pl.DataFrame({"season": [2003, 2004], "franchise_id": ["BUF", "BUF"]})
    assert checks.check_vegas_coverage(games, vegas) == []
    assert checks.check_vegas_coverage(games, vegas.filter(pl.col("season") == 2003)) == [
        "2004: no Vegas win totals; expectations would be model-sourced"]
    fails = checks.check_vegas_coverage(games, None)
    assert len(fails) == 1 and "2003-2004" in fails[0]
    assert checks.check_vegas_coverage(pl.DataFrame({"season": [2023, 2024]}), None) == []


def test_sim_coverage():
    """WR-08: sim keys must equal snapshot keys."""
    snaps = pl.DataFrame({"season": [2010, 2010, 2010], "week": [0, 0, 1], "franchise_id": ["A", "B", "A"]})
    assert checks.check_sim_coverage(snaps, snaps) == []
    fails = checks.check_sim_coverage(snaps.head(2), snaps)
    assert fails == ["1 snapshot rows without a sim row, e.g. 2010 week 1 A"]
    assert checks.check_sim_coverage(snaps, snaps.head(2)) == ["1 sim rows without a snapshot, e.g. 2010 week 1 A"]

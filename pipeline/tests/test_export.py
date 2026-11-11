"""JSON contract written by `fgs export` (D-06, D-07, D-17). Real-cache tests skip when caches are missing."""

import json

import polars as pl
import pytest

import fgs.cli as cli
from fgs.asof import week_progress
from fgs.cli import derive
from fgs.export import build_export, team_meta, write_export
from fgs.franchises import CANONICAL, normalize_code
from fgs.ingest import load_schedules, load_teams
from fgs.mood import BANDS
from fgs.paths import CACHE_DIR
from fgs.season_config import n_teams

ROW_KEYS = {"franchise", "rank", "score", "elo", "band", "label", "emoji",
            "wins", "losses", "ties", "score_delta", "rank_delta"}
META_KEYS = {"version", "score_kind", "generated_at", "data_through", "latest", "partial_week",
             "seasons", "bands", "hysteresis", "teams"}
GEN = "2026-11-11T18:40:00+00:00"


def _fake_teams() -> pl.DataFrame:
    codes = sorted(CANONICAL) + ["LAR", "OAK", "SD", "STL"]
    return pl.DataFrame({
        "team_abbr": codes,
        "team_name": [f"{c} Name" for c in codes],
        "team_nick": [f"{c} Nick" for c in codes],
        "team_color": ["#ffc20e"] * len(codes),
        "team_color2": ["#00338d"] * len(codes),
    })


def test_team_meta_filters_and_uppercases():
    meta = team_meta(_fake_teams())
    assert set(meta) == set(CANONICAL) and len(meta) == 32
    assert not {"LAR", "OAK", "SD", "STL"} & set(meta)
    assert meta["BUF"] == {"name": "BUF Name", "nick": "BUF Nick", "primary": "#FFC20E", "secondary": "#00338D"}


# --- real cache ----------------------------------------------------------------------------

@pytest.fixture(scope="module")
def real_files():
    if not (CACHE_DIR / "schedules.parquet").exists() or not (CACHE_DIR / "teams.parquet").exists():
        pytest.skip("no cached schedules/teams; run `uv run fgs export` once first")
    derived = derive(load_schedules())
    return derived, build_export(derived, load_teams(), generated_at=GEN)


def _all_rows(files):
    for path, obj in files.items():
        if path.startswith("snapshots/"):
            for week, rows in obj["weeks"].items():
                for r in rows:
                    yield obj["season"], int(week), r


def test_contract_files(real_files):
    derived, files = real_files
    seasons = sorted(derived["snapshots"]["season"].unique().to_list())
    assert {"meta.json", "latest.json", "history.json", "callouts.json"} <= set(files)
    assert sorted(int(p[10:-5]) for p in files if p.startswith("snapshots/")) == seasons
    assert sorted(p[6:-5] for p in files if p.startswith("teams/")) == sorted(CANONICAL)
    assert files["callouts.json"] == []


def test_contract_meta(real_files):
    _, files = real_files
    meta = files["meta.json"]
    assert set(meta) == META_KEYS
    assert meta["score_kind"] == "elo" and meta["version"] == 1 and meta["generated_at"] == GEN
    assert meta["hysteresis"] == 2 and len(meta["bands"]) == 7 and len(meta["teams"]) == 32
    assert [b["label"] for b in meta["bands"]] == [b["label"] for b in BANDS]
    for s in meta["seasons"]:
        assert set(s) == {"season", "max_week", "reg_weeks", "n_teams", "week_labels"}
        assert set(s["week_labels"]) == {str(w) for w in range(s["max_week"] + 1)}
        assert s["week_labels"]["0"] == "Preseason"
        if s["max_week"] > s["reg_weeks"]:
            assert s["week_labels"][str(s["reg_weeks"] + 1)] == "Wild Card"
        if s["max_week"] == s["reg_weeks"] + 4:
            assert s["week_labels"][str(s["max_week"])] == "Super Bowl"
    by = {s["season"]: s for s in meta["seasons"]}
    assert by[2020]["reg_weeks"] == 17 and by[2020]["week_labels"]["18"] == "Wild Card"
    assert by[2021]["reg_weeks"] == 18 and by[2021]["week_labels"]["22"] == "Super Bowl"


def test_contract_rows(real_files):
    _, files = real_files
    meta = files["meta.json"]
    by_week: dict[tuple[int, int], list] = {}
    for season, week, r in _all_rows(files):
        assert set(r) == ROW_KEYS
        for k in ROW_KEYS - {"franchise", "label", "emoji"}:
            assert r[k] is None or type(r[k]) is int, (season, week, k, r[k])
        assert 0 <= r["score"] <= 100
        assert r["label"] == meta["bands"][r["band"]]["label"]
        assert r["emoji"] == meta["bands"][r["band"]]["emoji"]
        if week == 0:
            assert r["score_delta"] is None and r["rank_delta"] is None
        by_week.setdefault((season, week), []).append(r)
    for (season, _week), rows in by_week.items():
        assert [r["rank"] for r in rows] == list(range(1, n_teams(season) + 1))


def test_contract_latest(real_files):
    _, files = real_files
    meta, latest = files["meta.json"], files["latest.json"]
    s, w = meta["latest"]["season"], meta["latest"]["week"]
    assert latest["season"] == s and latest["week"] == w
    assert latest["rows"] == files[f"snapshots/{s}.json"]["weeks"][str(w)]
    scores = [r["score"] for r in latest["rows"]]
    assert scores[0] >= 90 and scores[-1] <= 10


def test_contract_history_and_teams(real_files):
    _, files = real_files
    hist = files["history.json"]
    assert len(hist["teams"]) == 32
    assert all(len(v) == len(hist["keys"]) for v in hist["teams"].values())
    assert hist["keys"][0] == "1999-0"
    assert hist["teams"]["HOU"][0] is None and hist["teams"]["BUF"][0] is not None
    buf = files["teams/BUF.json"]
    assert buf["franchise"] == "BUF" and buf["name"] == "Buffalo Bills"
    h = buf["history"]
    assert set(h) == {"season", "week", "score", "elo", "label"}
    assert len({len(v) for v in h.values()}) == 1


def test_contract_written_files(real_files, tmp_path):
    _, files = real_files
    (tmp_path / "teams").mkdir()
    (tmp_path / "teams" / "STALE.json").write_text("{}")
    write_export(files, tmp_path)
    assert not (tmp_path / "teams" / "STALE.json").exists()
    text = (tmp_path / "latest.json").read_text(encoding="utf-8")
    assert "\\u" not in text and "\\ud83" not in text
    assert "’" in (tmp_path / "meta.json").read_text(encoding="utf-8")
    assert json.loads(text) == files["latest.json"]
    assert len(list((tmp_path / "teams").iterdir())) == 32


def test_write_export_failure_keeps_previous_export(tmp_path):
    out = tmp_path / "data"
    write_export({"meta.json": {"v": 1}, "teams/BUF.json": {"t": 1}}, out)
    bad = {"meta.json": {"v": 2}, "teams/BUF.json": {"t": 2}, "zzz.json": {"x": object()}}  # fails mid-write
    with pytest.raises(TypeError):
        write_export(bad, out)
    assert json.loads((out / "meta.json").read_text()) == {"v": 1}
    assert json.loads((out / "teams" / "BUF.json").read_text()) == {"t": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["data"]  # no temp dirs left behind
    write_export({"meta.json": {"v": 3}}, out)
    assert sorted(p.name for p in out.iterdir()) == ["meta.json"]
    assert [p.name for p in tmp_path.iterdir()] == ["data"]


def test_latest_partial_week_synthetic():
    """Partial week can't be seen on today's data: un-play the last game of the latest week."""
    if not (CACHE_DIR / "schedules.parquet").exists() or not (CACHE_DIR / "teams.parquet").exists():
        pytest.skip("no cached schedules/teams")
    raw = load_schedules()
    played = raw.filter(pl.col("result").is_not_null())
    s = played["season"].max()
    w = played.filter(pl.col("season") == s)["week"].max()
    last = played.filter((pl.col("season") == s) & (pl.col("week") == w)).sort("gameday")["game_id"][-1]
    mutated = raw.with_columns(
        [pl.when(pl.col("game_id") == last).then(None).otherwise(pl.col(c)).alias(c)
         for c in ("result", "home_score", "away_score")]
    )
    files = build_export(derive(mutated), load_teams(), generated_at=GEN)
    meta = files["meta.json"]
    assert meta["latest"] == {"season": s, "week": w}
    assert meta["partial_week"] is True


def test_cli_export_writes_to_monkeypatched_dir(tmp_path, monkeypatch, capsys):
    if not (CACHE_DIR / "schedules.parquet").exists() or not (CACHE_DIR / "teams.parquet").exists():
        pytest.skip("no cached schedules/teams")
    monkeypatch.setattr(cli, "WEB_DATA_DIR", tmp_path)
    assert cli.main(["export"]) == 0
    assert (tmp_path / "meta.json").exists()
    assert "exported" in capsys.readouterr().out


# --- partial weeks (calendar-robust: derive (s, w) from the data, never hardcode) ------------

def _raw_and_latest():
    if not (CACHE_DIR / "schedules.parquet").exists() or not (CACHE_DIR / "teams.parquet").exists():
        pytest.skip("no cached schedules/teams")
    raw = load_schedules()
    played = raw.filter(pl.col("result").is_not_null())
    s = int(played["season"].max())
    w = int(played.filter(pl.col("season") == s)["week"].max())
    return raw, s, w


def test_partial_current_week_by_kickoff():
    raw, s, w = _raw_and_latest()
    wk = raw.filter((pl.col("season") == s) & (pl.col("week") == w) & pl.col("result").is_not_null())
    if wk.height < 2:
        pytest.skip(f"{s} week {w} has only one played game")
    last = wk.sort(["gameday", "gametime"])["game_id"][-1]
    mutated = raw.with_columns(
        [pl.when(pl.col("game_id") == last).then(None).otherwise(pl.col(c)).alias(c)
         for c in ("result", "home_score", "away_score")]
    )
    meta = build_export(derive(mutated), load_teams(), generated_at=GEN)["meta.json"]
    assert meta["latest"] == {"season": s, "week": w}
    assert meta["partial_week"] is True


def test_partial_next_week_one_game_played():
    raw, s, w = _raw_and_latest()
    nxt = raw.filter((pl.col("season") == s) & (pl.col("week") == w + 1) & pl.col("result").is_null())
    if nxt.is_empty():
        pytest.skip(f"{s} has no unplayed game in week {w + 1}")
    g = nxt.sort(["gameday", "gametime"]).row(0, named=True)
    mutated = raw.with_columns(
        pl.when(pl.col("game_id") == g["game_id"]).then(pl.lit(v)).otherwise(pl.col(c)).cast(raw.schema[c]).alias(c)
        for c, v in (("home_score", 27), ("away_score", 20), ("result", 7))
    )
    files = build_export(derive(mutated), load_teams(), generated_at=GEN)
    meta = files["meta.json"]
    assert meta["latest"] == {"season": s, "week": w + 1}
    assert meta["partial_week"] is True
    weeks = files[f"snapshots/{s}.json"]["weeks"]
    now, prev = weeks[str(w + 1)], {r["franchise"]: r for r in weeks[str(w)]}
    assert len(now) == n_teams(s)
    playing = {normalize_code(g["home_team"]), normalize_code(g["away_team"])}
    for r in now:
        if r["franchise"] in playing:
            continue
        assert r["elo"] == prev[r["franchise"]]["elo"], r["franchise"]
        p = prev[r["franchise"]]
        assert (r["wins"], r["losses"], r["ties"]) == (p["wins"], p["losses"], p["ties"]), r["franchise"]
        # score_delta need not be 0: the composite is z-scored across all teams in the week,
        # so other teams' results move everyone's z a little.


def test_partial_flag_matches_week_progress_on_real_data(real_files):
    derived, files = real_files
    meta = files["meta.json"]
    played, total = week_progress(derived["games"], meta["latest"]["season"], meta["latest"]["week"])
    assert meta["partial_week"] is (played < total)
    if played == total:
        assert meta["partial_week"] is False

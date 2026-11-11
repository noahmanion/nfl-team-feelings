"""JSON contract written by `fgs export` (D-06, D-07, D-17). Real-cache tests skip when caches are missing."""

import json
import math
from datetime import date
import re

import polars as pl
import pytest
import yaml

import fgs.cli as cli
from fgs.asof import week_progress
from fgs.cli import derive
from fgs.explain import PHRASES
from fgs.export import _playoff_display, build_export, team_meta, write_export
from fgs.franchises import CANONICAL, normalize_code
from fgs.ingest import load_schedules, load_teams
from fgs.mood import BANDS
from fgs.paths import CACHE_DIR, WEIGHTS_PATH
from fgs.score import load_offseason, load_weights
from fgs import insights, paths, season_config
from fgs.season_config import SEEDS, n_teams, playoff_teams
from conftest import derive_inputs

ROW_KEYS = {"franchise", "rank", "score", "elo", "band", "label", "emoji",
            "wins", "losses", "ties", "score_delta", "rank_delta", "contribs", "points", "blurb",
            "playoff_prob", "expectation_source", "qb", "draft"}
DRAFT_KEYS = {"surplus", "z", "equiv_pick", "rank", "text", "moves_score"}
META_KEYS = {"version", "score_kind", "generated_at", "data_through", "latest", "partial_week",
             "seasons", "bands", "hysteresis", "teams", "factors", "baseline", "offseason"}
GEN = "2026-11-11T18:40:00+00:00"
CALLOUT_KEYS = {"type", "season", "week", "franchise", "headline", "detail", "evidence", "stat", "start", "band"}


def _matching_evidence(weights: dict, cfg: dict) -> dict:
    """The committed callout_evidence.json, re-fingerprinted for synthetic weights (tests only)."""
    ev = json.loads(paths.CALLOUT_EVIDENCE_PATH.read_text())
    return {**ev, "weights_fingerprint": insights.weights_fingerprint(insights.fingerprint_weights(weights, cfg))}


def _fake_teams() -> pl.DataFrame:
    codes = sorted(CANONICAL) + ["LAR", "OAK", "SD", "STL"]
    return pl.DataFrame({
        "team_abbr": codes,
        "team_name": [f"{c} Name" for c in codes],
        "team_nick": [f"{c} Nick" for c in codes],
        "team_color": ["#ffc20e"] * len(codes),
        "team_color2": ["#00338d"] * len(codes),
    })


def test_as_of_date_is_us_eastern():
    """WR-09: a post-MNF export (after 8 pm ET, already tomorrow in UTC) keeps the ET date."""
    from fgs.export import as_of_date
    assert as_of_date("2026-11-11T03:30:00+00:00") == date(2026, 11, 10)
    assert as_of_date("2026-11-11T18:40:00+00:00") == date(2026, 11, 11)
    assert as_of_date("2026-07-01T03:30:00") == date(2026, 6, 30)  # naive = UTC; EDT


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
    derived = derive(load_schedules(), **derive_inputs())
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
    assert {"meta.json", "latest.json", "history.json", "callouts.json", "methodology.json"} <= set(files)
    assert sorted(int(p[10:-5]) for p in files if p.startswith("snapshots/")) == seasons
    assert sorted(p[6:-5] for p in files if p.startswith("teams/")) == sorted(CANONICAL)
    assert isinstance(files["callouts.json"], list)
    assert sorted(int(p[6:-5]) for p in files if p.startswith("games/")) == seasons


def test_contract_meta(real_files):
    _, files = real_files
    meta = files["meta.json"]
    assert set(meta) == META_KEYS
    assert meta["score_kind"] == "composite" and meta["version"] == 1 and meta["generated_at"] == GEN
    assert meta["hysteresis"] == 2 and len(meta["bands"]) == 7 and len(meta["teams"]) == 32
    assert [b["label"] for b in meta["bands"]] == [b["label"] for b in BANDS]
    weights = load_weights()
    yaml_weights = yaml.safe_load(WEIGHTS_PATH.read_text())["weights"]
    cfg = load_offseason()
    extra = ["draft"] if cfg["weight"] != 0 else []
    assert [f["key"] for f in meta["factors"]] == list(weights) + extra and list(weights) == list(yaml_weights)
    assert meta["offseason"] == {"draft": {"weight": cfg["weight"], "display_only": cfg["display_only"],
                                           "chart": cfg["chart"], "decay": [1.0, 0.75, 0.5, 0.25]}}
    for f in meta["factors"]:
        if f["key"] == "draft":
            assert f["weight"] == cfg["weight"] and f["label"] == "Draft capital over slot"
            continue
        assert set(f) == {"key", "label", "weight", "description"}
        assert f["weight"] == yaml_weights[f["key"]] and f["label"] and f["description"]
    for s in meta["seasons"]:
        assert set(s) == {"season", "max_week", "reg_weeks", "n_teams", "week_labels"}
        assert set(s["week_labels"]) == {str(w) for w in range(s["max_week"] + 1)}
        assert s["week_labels"]["0"] == "Preseason (after draft)"
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
    factor_keys = [f["key"] for f in meta["factors"]]
    by_week: dict[tuple[int, int], list] = {}
    for season, week, r in _all_rows(files):
        assert set(r) == ROW_KEYS
        assert list(r["contribs"]) == factor_keys
        for v in r["contribs"].values():
            assert type(v) in (int, float) and math.isfinite(v) and round(v, 2) == v
        for k in ROW_KEYS - {"franchise", "label", "emoji", "contribs", "points", "blurb", "expectation_source", "qb",
                             "draft"}:
            assert r[k] is None or type(r[k]) is int, (season, week, k, r[k])
        assert 0 <= r["score"] <= 100
        assert r["label"] == meta["bands"][r["band"]]["label"]
        assert r["emoji"] == meta["bands"][r["band"]]["emoji"]
        by_week.setdefault((season, week), []).append(r)
    for (season, _week), rows in by_week.items():
        assert [r["rank"] for r in rows] == list(range(1, n_teams(season) + 1))


def test_week0_deltas_and_draft(real_files):
    """Week 0 compares with the end of last season; every derivable week-0 row carries draft info."""
    _, files = real_files
    meta = files["meta.json"]
    weight = meta["offseason"]["draft"]["weight"]
    first = min(s["season"] for s in meta["seasons"])
    for season, week, r in _all_rows(files):
        if week != 0:
            assert r["draft"] is None
            continue
        if season == first or (r["franchise"], season) == ("HOU", 2002):
            assert r["score_delta"] is None and r["rank_delta"] is None, (season, r["franchise"])
        else:
            assert type(r["score_delta"]) is int and type(r["rank_delta"]) is int, (season, r["franchise"])
        if season < 2000:
            assert r["draft"] is None
            continue
        d = r["draft"]
        assert d is not None and set(d) == DRAFT_KEYS, (season, r["franchise"])
        assert round(d["surplus"], 1) == d["surplus"] and round(d["z"], 2) == d["z"]
        if "about even" in d["text"]:
            assert d["equiv_pick"] is None
        else:
            assert type(d["equiv_pick"]) is int and 1 <= d["equiv_pick"] <= 262
        assert d["moves_score"] is (weight != 0)
        assert d["text"].startswith("Draft haul: ")
        assert d["text"].endswith(" — doesn't move the score." if weight == 0 else ".")
        assert "great draft" not in d["text"] and "drafted well" not in d["text"]
    for path, obj in files.items():
        if path.startswith("snapshots/") and obj["season"] >= 2000:
            rows = obj["weeks"]["0"]
            assert sorted(r["draft"]["rank"] for r in rows) == list(range(1, len(rows) + 1))
            by_rank = sorted(rows, key=lambda r: r["draft"]["rank"])
            assert all(a["draft"]["surplus"] >= b["draft"]["surplus"] for a, b in zip(by_rank, by_rank[1:]))


def test_contract_latest(real_files):
    _, files = real_files
    meta, latest = files["meta.json"], files["latest.json"]
    s, w = meta["latest"]["season"], meta["latest"]["week"]
    assert latest["season"] == s and latest["week"] == w
    assert latest["rows"] == files[f"snapshots/{s}.json"]["weeks"][str(w)]
    scores = [r["score"] for r in latest["rows"]]
    assert scores[0] >= 90 and scores[-1] <= 10


def test_latest_rank_follows_contrib_sum(real_files):
    """Board rank = composite order; rounded contribs sum to it within rounding."""
    _, files = real_files
    rows = files["latest.json"]["rows"]
    sums = [round(sum(r["contribs"].values()), 2) for r in rows]
    n = len(rows[0]["contribs"])
    for a, b in zip(sums, sums[1:]):
        assert a >= b - n * 0.005 - 1e-9, (a, b)  # tolerance: each 2dp contrib rounds by <= 0.005
    assert [r["rank"] for r in rows] == list(range(1, len(rows) + 1))


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
    files = build_export(derive(mutated, **derive_inputs()), load_teams(), generated_at=GEN)
    meta = files["meta.json"]
    assert meta["latest"] == {"season": s, "week": w}
    assert meta["partial_week"] is True


def test_cli_export_writes_to_monkeypatched_dir(tmp_path, monkeypatch, capsys):
    if not (CACHE_DIR / "schedules.parquet").exists() or not (CACHE_DIR / "teams.parquet").exists():
        pytest.skip("no cached schedules/teams")
    monkeypatch.setattr(cli, "WEB_DATA_DIR", tmp_path / "web")
    monkeypatch.setattr(paths, "RECORDS_CHECK_PATH", tmp_path / "RECORDS_CHECK.md")  # never the committed file
    assert cli.main(["export"]) == 0
    assert (tmp_path / "web" / "meta.json").exists() and (tmp_path / "web" / "records.json").exists()
    md = (tmp_path / "RECORDS_CHECK.md").read_text()
    assert "Notable non-entries" in md and md.count("| # |") == 4
    out = capsys.readouterr().out
    assert "exported" in out and "RECORDS_CHECK.md" in out


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
    meta = build_export(derive(mutated, **derive_inputs()), load_teams(), generated_at=GEN)["meta.json"]
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
    files = build_export(derive(mutated, **derive_inputs()), load_teams(), generated_at=GEN)
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


# --- WR-04: meta.factors weights are the ones that produced contrib_* ------------------------

def test_export_weights_come_from_derived_not_the_yaml(synthetic_games):
    from fgs.cli import derive_games
    from fgs.export import _export_weights

    w = {"elo": 2.0, "season_record": 1.0}  # deliberately not weights.yaml
    derived = derive_games(synthetic_games, weights=w)
    assert _export_weights(derived, derived["features"]) == w
    with pytest.raises(ValueError, match="does not equal"):
        _export_weights({**derived, "weights": {"elo": 3.0, "season_record": 1.0}}, derived["features"])
    with pytest.raises(ValueError, match="lacks"):
        _export_weights({**derived, "weights": {**w, "last16": 1.0}}, derived["features"])
    with pytest.raises(ValueError, match="not in the weights"):
        _export_weights({**derived, "weights": {"elo": 2.0}}, derived["features"])


def test_contribs_have_no_negative_zero(real_files):
    _, files = real_files
    for _, _, r in _all_rows(files):
        for v in r["contribs"].values():
            assert not (v == 0 and math.copysign(1.0, v) < 0), r
    assert not re.search(r"-0\.0[,}\]]", json.dumps(files["latest.json"], separators=(",", ":")))


# --- SITE-02 / INSIGHT-05: points, blurbs, games ----------------------------------------------

def test_points_sum_to_score(real_files):
    _, files = real_files
    meta = files["meta.json"]
    base = meta["baseline"]
    assert type(base) is int and 0 <= base <= 100
    keys = [f["key"] for f in meta["factors"]]
    for season, week, r in _all_rows(files):
        assert list(r["points"]) == keys
        assert all(type(v) is int for v in r["points"].values()), (season, week, r["points"])
        assert sum(r["points"].values()) == r["score"] - base, (season, week, r["franchise"])


def test_blurbs(real_files):
    _, files = real_files
    lead0 = "Preseason, carrying last season's form: the "
    leads0 = (lead0, "Preseason, carrying last season's form plus extra draft capital: the ",
              "Preseason, carrying last season's form minus some draft capital: the ")
    first = min(int(s["season"]) for s in files["meta.json"]["seasons"])
    for season, week, r in _all_rows(files):
        b = r["blurb"]
        assert isinstance(b, str) and b and b.endswith("."), (season, week, r["franchise"], b)
        if week == 0 and (r["franchise"], season) in SEEDS:
            assert b.endswith("are an expansion team starting below average."), b
        elif week == 0 and season == first:
            assert b.startswith("Preseason: no history yet, so the "), b
        elif week == 0:
            assert b.startswith(leads0), b
            d = r["draft"]
            if b.startswith(leads0[1]):
                assert d is not None and d["surplus"] > 0, b
            elif b.startswith(leads0[2]):
                assert d is not None and d["surplus"] < 0, b
        else:
            assert b.startswith("The ") and not b.startswith("Preseason"), b
        assert "0 straight" not in b and "1 straight" not in b, b


def test_blurbs_mov_and_sow_never_contradict(real_files):
    # CR-01: sow describes results vs schedule; it must never claim margins lag (or lead) the record
    _, files = real_files
    mov_hi = PHRASES[("mov", "hi")]
    for season, week, r in _all_rows(files):
        b = r["blurb"]
        assert "ahead of their margins" not in b and "behind their margins" not in b, b
        assert "lags behind" not in b, b
        if any(t in b for t in mov_hi):
            assert b.count("margin") <= 1, (season, week, r["franchise"], b)


def test_games_files(real_files):
    _, files = real_files
    for path, g in files.items():
        if not path.startswith("games/"):
            continue
        n = len(g["week"])
        for k in ("asof_week", "home", "away", "home_score", "away_score", "game_type", "gameday", "neutral"):
            assert len(g[k]) == n, (path, k)
        assert all((h is None) == (a is None) for h, a in zip(g["home_score"], g["away_score"])), path
        assert any(h is not None for h in g["home_score"]), f"{path}: no played games"
        assert set(g["home"]) | set(g["away"]) <= CANONICAL, path


# --- playoff odds display (MODEL-13, A5 override) -------------------------------------------

def test_playoff_display_unit(monkeypatch):
    """Season complete as of week 2 (REG asof <= 2) with the full post-season field known (2 spots
    here): weeks >= 2 show 100/0, week 1 raw."""
    monkeypatch.setattr(season_config, "playoff_teams", lambda season: 2)
    scored = pl.DataFrame({
        "season": [2010] * 6, "week": [1, 1, 2, 2, 3, 3], "franchise_id": ["A", "B"] * 3,
        "playoff_prob": [0.876, 0.124, 0.40, 0.60, 0.5, 0.5],
    })
    games = pl.DataFrame({
        "season": [2010] * 3, "game_type": ["REG", "REG", "WC"], "home_id": ["A", "B", "A"],
        "away_id": ["B", "A", "C"], "played": [True, True, False], "asof_week": [1, 2, 3], "is_reg": [True, True, False],
    })
    out = _playoff_display(scored, games).sort("week", "franchise_id")
    assert out["playoff_display"].to_list() == [88, 12, 100, 0, 100, 0]
    assert out["playoff_prob"].to_list() == scored["playoff_prob"].to_list()  # raw value untouched
    # no non-REG row yet -> no override
    assert _playoff_display(scored, games.filter(pl.col("is_reg")))["playoff_display"].to_list() == [88, 12, 40, 60, 50, 50]
    # an unplayed REG game -> no override
    open_reg = games.with_columns(pl.when(pl.col("asof_week") == 2).then(False).otherwise(pl.col("played")).alias("played"))
    assert _playoff_display(scored, open_reg)["playoff_display"].to_list()[2:4] == [40, 60]


def test_playoff_display_bye_team_wildcard_only():
    """CR-01: right after the REG season only wildcard rows exist; the bye team (B here, no
    non-REG row yet) must keep its raw sim value, not show 0, until the field is fully known."""
    scored = pl.DataFrame({
        "season": [2024] * 3, "week": [18] * 3, "franchise_id": ["A", "B", "D"],
        "playoff_prob": [1.0, 0.97, 0.02],
    })
    games = pl.DataFrame({
        "season": [2024] * 3, "game_type": ["REG", "REG", "WC"], "home_id": ["A", "B", "A"],
        "away_id": ["B", "D", "C"], "played": [True, True, False], "asof_week": [17, 18, 19],
        "is_reg": [True, True, False],
    })
    out = {r["franchise_id"]: r["playoff_display"] for r in _playoff_display(scored, games).iter_rows(named=True)}
    assert out == {"A": 100, "B": 97, "D": 2}  # field not known yet: non-WC teams keep raw values


def test_playoff_prob_range(real_files):
    _, files = real_files
    for season, week, r in _all_rows(files):
        p = r["playoff_prob"]
        assert p is None or (type(p) is int and 0 <= p <= 100), (season, week, p)
        assert r["expectation_source"] in ("vegas", "model", None)
        if r["expectation_source"] == "vegas":
            assert 2003 <= season <= 2020, (season, week)
        assert r["qb"] is None or isinstance(r["qb"], str)


def test_playoff_display_override(real_files):
    _, files = real_files
    meta = files["meta.json"]
    for sm in meta["seasons"]:
        season, rw = sm["season"], sm["reg_weeks"]
        if season == meta["latest"]["season"]:
            continue
        rows = files[f"snapshots/{season}.json"]["weeks"][str(rw)]
        probs = sorted(r["playoff_prob"] for r in rows)
        assert set(probs) == {0, 100}, season
        assert probs.count(100) == playoff_teams(season), season
    latest = files["latest.json"]["rows"]
    total = sum(r["playoff_prob"] for r in latest)
    assert abs(total - 100 * playoff_teams(meta["latest"]["season"])) <= 32
    assert {r["expectation_source"] for r in latest} == {"model"}


# --- Phase 6 (BACK-04): export/refresh never refit the weights ------------------------------

def test_export_never_refits(synthetic_games, monkeypatch):
    """With every fitting entry point patched to raise, the score path (synthetic league) and the
    full build_export (cached data, as test_latest_partial_week_synthetic) still succeed."""
    import fgs.backtest
    from fgs import explain, mood
    from fgs.cli import derive_games

    def boom(*a, **k):
        raise AssertionError("export path refit the weights")

    for name in ("ridge_fit", "propose_weights", "choose_alpha"):
        monkeypatch.setattr(fgs.backtest, name, boom)

    with monkeypatch.context() as m:
        m.setattr(season_config, "REF_SEASONS", (2023, 2023))  # synthetic league seasons
        derived = derive_games(synthetic_games)  # weights read from weights.yaml, never fit
        assert derived["weights"] == load_weights()
        feats = derived["features"]
        explain.add_points(mood.score_frame(feats), list(derived["weights"]), mood.reference_values(feats))

    if not (CACHE_DIR / "schedules.parquet").exists() or not (CACHE_DIR / "teams.parquet").exists():
        pytest.skip("no cached schedules/teams for the full build_export check")
    files = build_export(derive(load_schedules(), **derive_inputs()), load_teams(), generated_at=GEN)
    assert {f["key"] for f in files["meta.json"]["factors"]} == set(load_weights())


def test_contract_methodology(real_files):
    """methodology.json agrees with meta.json and weights.yaml; no holdout until the one-time run."""
    from fgs import paths

    _, files = real_files
    m, meta = files["methodology.json"], files["meta.json"]
    weights = load_weights()
    assert [f["key"] for f in m["factors"]] == [f["key"] for f in meta["factors"]] == list(weights)
    assert [f["weight"] for f in m["factors"]] == [f["weight"] for f in meta["factors"]] == list(weights.values())
    if not paths.HOLDOUT_JSON_PATH.exists():
        assert m["holdout"] is None
    assert m["walk_forward"] is not None and m["frozen"] is not None
    assert m["split"]["live"] == meta["latest"]["season"]
    json.dumps(m, allow_nan=False)


# --- Phase 7: the nonzero draft-weight path (synthetic, fake weight) ------------------------

def _draft_export(monkeypatch, cfg):
    """Synthetic 4-team 2023-2024 export with 2024 draft surplus BUF +50, MIA -30, NE 0.2, NYJ 5
    and the given offseason cfg. Returns (files, z by franchise)."""
    import numpy as np

    from conftest import make_games
    from fgs import score
    from fgs.cli import derive_games

    teams = ["BUF", "MIA", "NE", "NYJ"]
    rows = []
    for season in (2023, 2024):
        for w in range(1, 6):
            a, b, c, d = (teams[(w + i) % 4] for i in range(4))
            day = f"{season}-09-{w + 9:02d}"
            rows.append((f"{season}_{w:02d}_{b}_{a}", season, w, "REG", day, a, b, 20 + w, 17, False))
            rows.append((f"{season}_{w:02d}_{d}_{c}", season, w, "REG", day, c, d, 14, 21 + w, False))
    games = make_games(rows)
    real_reg_weeks = season_config.reg_weeks
    monkeypatch.setattr(season_config, "reg_weeks", lambda s: 5 if s in (2023, 2024) else real_reg_weeks(s))
    monkeypatch.setattr(season_config, "REF_SEASONS", (2023, 2023))

    weights = {"elo": 2.0, "season_record": 1.0}
    derived = derive_games(games, weights=weights, offseason={**cfg, "weight": 0.0, "display_only": True})
    feats = derived["features"].drop("composite_inseason", "draft_surplus", "draft_z")
    dz = pl.DataFrame({"season": [2024] * 4, "franchise_id": teams,
                       "surplus": [50.0, -30.0, 0.2, 5.0], "draft_z": [1.2, -1.5, 0.0, 0.3]})
    feats = score.apply_offseason(feats, dz, cfg)
    values = np.concatenate([[np.nan], np.linspace(60.0, 0.5, 262)])
    files = build_export({**derived, "features": feats, "offseason": cfg, "draft_values": values},
                         _fake_teams(), generated_at=GEN, evidence=_matching_evidence(weights, cfg))
    return files, dict(zip(dz["franchise_id"], dz["draft_z"]))


LIVE_CFG = {"weight": 1.0, "display_only": False, "chart": "stuart", "winsor": (-17.0, 16.0),
            "decay": [1.0, 0.75, 0.5, 0.25]}


def test_export_display_only_draft_never_leads_the_blurb(monkeypatch):
    """CR-03: with weight 0 the score carries no draft capital, so the week-0 lead must not say it
    does; the draft shows only in the separate display line."""
    files, _ = _draft_export(monkeypatch, {**LIVE_CFG, "weight": 0.0, "display_only": True})
    rows = files["snapshots/2024.json"]["weeks"]["0"]
    assert len(rows) == 4
    for r in rows:
        assert "draft" not in r["blurb"], r["blurb"]
        assert r["blurb"].startswith("Preseason, carrying last season's form: ")
        assert r["draft"]["text"].endswith("doesn't move the score.")


def test_export_with_live_draft_weight(monkeypatch):
    """A fake offseason weight of 1.0: draft is in contribs/points/meta.factors on weeks 0-3, 0.0
    from week 4, and every row's points still sum to score - baseline."""
    files, z = _draft_export(monkeypatch, LIVE_CFG)
    meta = files["meta.json"]
    assert [f["key"] for f in meta["factors"]] == ["elo", "season_record", "draft"]
    assert meta["factors"][-1]["label"] == "Draft capital over slot" and meta["factors"][-1]["weight"] == 1.0
    assert meta["offseason"]["draft"] == {"weight": 1.0, "display_only": False, "chart": "stuart",
                                          "decay": [1.0, 0.75, 0.5, 0.25]}
    assert all(s["week_labels"]["0"] == "Preseason (after draft)" for s in meta["seasons"])
    base = meta["baseline"]
    seen = 0
    for season, week, r in _all_rows(files):
        assert sum(r["points"].values()) == r["score"] - base
        assert list(r["contribs"]) == ["elo", "season_record", "draft"]
        if season == 2024 and week <= 3:
            assert r["contribs"]["draft"] == round(z[r["franchise"]] * (1 - week / 4), 2) + 0.0
        else:
            assert r["contribs"]["draft"] == 0.0
        if season == 2024 and week == 0:
            seen += 1
            d = r["draft"]
            assert d["moves_score"] is True and not d["text"].endswith("doesn't move the score.")
            assert d["rank"] == {"BUF": 1, "NYJ": 2, "NE": 3, "MIA": 4}[r["franchise"]]
            if r["franchise"] == "BUF":  # 50 >= values[64] (~45.6): the extra-capital lead
                assert r["blurb"].startswith("Preseason, carrying last season's form plus extra draft capital: ")
            if r["franchise"] == "NE":
                assert d["text"] == "Draft haul: about even with their original slots."
                assert d["equiv_pick"] is None
            else:
                assert type(d["equiv_pick"]) is int
        else:
            assert r["draft"] is None
    assert seen == 4
    assert all(r["score_delta"] is not None for r in files["snapshots/2024.json"]["weeks"]["0"])


def test_export_without_draft_values_has_null_draft(synthetic_games):
    """Real weights.yaml (weight 0), no draft inputs: _draft_info is None for every row."""
    from fgs import export
    from fgs.cli import derive_games

    derived = derive_games(synthetic_games)
    assert derived["draft_values"] is None and derived["features"]["draft_surplus"].null_count() == derived["features"].height
    ctx = {"values": None, "moves_score": False, "ranks": {}, "threshold": None}
    for r in derived["features"].iter_rows(named=True):
        assert export._draft_info(r, ctx) is None
    assert load_offseason()["weight"] == derived["offseason"]["weight"]


# --- Phase 8: callouts (INSIGHT-02 perception gap, INSIGHT-06 movers) -----------------------

def test_callouts_contract(real_files):
    _, files = real_files
    latest = files["meta.json"]["latest"]
    c = files["callouts.json"]
    assert isinstance(c, list)
    assert all(set(x) == CALLOUT_KEYS and (x["season"], x["week"]) == (latest["season"], latest["week"]) for x in c)
    snap = files[f"snapshots/{latest['season']}.json"]
    assert c == snap["callouts"].get(str(latest["week"]), [])
    total_gap = total_streak = 0
    for path, obj in files.items():
        if not path.startswith("snapshots/"):
            continue
        season = obj["season"]
        rw = season_config.reg_weeks(season)
        assert isinstance(obj["callouts"], dict) and set(obj["callouts"]) <= set(obj["weeks"])
        for wk, items in obj["callouts"].items():
            assert items, (season, wk)
            week = int(wk)
            franchises = {r["franchise"] for r in obj["weeks"][wk]}
            by_type: dict[str, int] = {}
            for x in items:
                assert set(x) == CALLOUT_KEYS and x["season"] == season and x["week"] == week
                assert x["franchise"] in franchises and isinstance(x["stat"], int)
                assert x["type"] in {"worried", "hopeful", "misery", "joy", "mover_up", "mover_down"}
                by_type[x["type"]] = by_type.get(x["type"], 0) + 1
                if x["type"] in ("misery", "joy"):
                    total_streak += 1
                    assert x["stat"] >= season_config.STREAK_CALLOUT_MIN_DAYS and x["evidence"] is None
                    assert x["start"] is not None and date.fromisoformat(x["start"]) and str(x["stat"]) in \
                        x["headline"].replace(",", "")
                    continue
                assert x["start"] is None
                if x["type"] in ("worried", "hopeful"):
                    total_gap += 1
                    assert season_config.GAP_FIRST_WEEK <= week <= rw - 1
                    assert x["evidence"] and "1999–2021" in x["evidence"]
                    assert (x["stat"] >= 8) if x["type"] == "hopeful" else (x["stat"] <= -8)
                else:
                    assert week >= 1 and x["evidence"] is None
                    assert (x["stat"] > 0) if x["type"] == "mover_up" else (x["stat"] < 0)
            assert all(n <= 3 for n in by_type.values()), (season, wk, by_type)
            assert by_type.get("misery", 0) <= 1 and by_type.get("joy", 0) <= 1, (season, wk, by_type)
    assert total_gap > 500 and total_streak > 100
    json.dumps(files["callouts.json"], allow_nan=False)
    json.dumps(files[f"snapshots/{latest['season']}.json"]["callouts"], allow_nan=False)


def test_export_refuses_stale_evidence(real_files):
    derived, _ = real_files
    ev = json.loads(paths.CALLOUT_EVIDENCE_PATH.read_text())
    for bad in ({"weights_fingerprint": "000000000000"}, {"threshold": 9}, {"first_week": 3},
                {"train_seasons": [1999, 2022]}):
        with pytest.raises(ValueError, match="stale") as e:
            build_export(derived, load_teams(), generated_at=GEN, evidence={**ev, **bad})
        assert "fgs evidence" in str(e.value)


def test_export_requires_evidence_file(real_files, tmp_path, monkeypatch):
    derived, _ = real_files
    monkeypatch.setattr(paths, "CALLOUT_EVIDENCE_PATH", tmp_path / "missing.json")
    with pytest.raises(ValueError, match="uv run fgs evidence"):
        build_export(derived, load_teams(), generated_at=GEN)


# --- Phase 8: records (INSIGHT-03, INSIGHT-04) -------------------------------------------------

def test_records_contract(real_files):
    _, files = real_files
    r = files["records.json"]
    assert set(r) == {"as_of", "saddest", "happiest", "misery", "joy", "active", "excluded", "notable"}
    assert r["as_of"] == GEN[:10]
    assert all(len(r[k]) == 10 for k in ("saddest", "happiest", "misery", "joy"))
    assert {(e["season"], e["franchise"]) for e in r["excluded"]} == {(1999, "CLE"), (2002, "HOU")}
    teams = set(files["meta.json"]["teams"])
    assert set(r["active"]) <= teams and all(a["kind"] in ("misery", "joy") for a in r["active"].values())
    for e in r["misery"] + r["joy"]:
        assert e["active"] == (e["end"] is None) and e["days"] > 0 and e["seasons"]
    json.dumps(r, allow_nan=False)

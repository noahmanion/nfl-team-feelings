"""Phase 8 dev-only evidence (fgs.evidence): leave-one-out peers, next-8 win%, holdout seal, CLI."""

import json

import numpy as np
import polars as pl
import pytest

from fgs import evidence, paths, season_config
from fgs.paths import CACHE_DIR

KEYS = {"threshold", "first_week", "train_seasons", "weights_fingerprint", "generated_at", "note", "hopeful", "worried"}


def _cases(rows: list[tuple]) -> pl.DataFrame:
    """(week, wins, losses, ties, y8, win8, flavor)."""
    return pl.DataFrame(rows, orient="row", schema={
        "week": pl.Int32, "wins": pl.Int64, "losses": pl.Int64, "ties": pl.Int64,
        "y8": pl.Float64, "win8": pl.Float64, "flavor": pl.String})


def test_peer_stats_leave_one_out_same_week_and_record():
    df = _cases([
        (5, 3, 1, 0, 6.0, 0.75, "hopeful"),   # case: peers are the two rows below (same week, 3-1-0)
        (5, 3, 1, 0, 2.0, 0.50, None),
        (5, 3, 1, 0, 0.0, 0.25, None),
        (6, 3, 1, 0, 100.0, 1.0, None),        # other week: not a peer
        (5, 3, 0, 1, 100.0, 1.0, None),        # other record: not a peer
        (5, 1, 3, 0, -4.0, 0.25, "worried"),   # case with one peer (another worried case)
        (5, 1, 3, 0, 2.0, 0.75, "worried"),
        (7, 0, 6, 0, -9.0, 0.0, "worried"),    # alone in its group: contributes no case
        (5, 3, 1, 0, None, None, None),        # undefined y8: never a peer
    ])
    out = evidence.peer_stats(df)
    h, w = out["hopeful"], out["worried"]
    assert h == {"n": 1, "d_margin": 5.0, "team_win": 0.75, "peer_win": 0.375}
    # worried: (-4 - 2) and (2 - -4) -> d mean 0; team win mean .5; peer win mean .5
    assert w == {"n": 2, "d_margin": 0.0, "team_win": 0.5, "peer_win": 0.5}


def test_peer_stats_undefined_case_is_not_counted():
    df = _cases([(5, 3, 1, 0, None, None, "hopeful"), (5, 3, 1, 0, 1.0, 0.5, None)])
    assert evidence.peer_stats(df)["hopeful"]["n"] == 0


def test_next_n_win_synthetic():
    from conftest import make_games
    from fgs.games import build_team_games

    # BUF plays weeks 1..4 (W, L, T, W); snapshot at week 1 -> next games 2..4: (0 + .5 + 1)/3
    rows = [
        ("2023_01_BUF_MIA", 2023, 1, "REG", "2023-09-10", "MIA", "BUF", 10, 20, False),
        ("2023_02_BUF_NE", 2023, 2, "REG", "2023-09-17", "NE", "BUF", 30, 20, False),
        ("2023_03_BUF_NYJ", 2023, 3, "REG", "2023-09-24", "NYJ", "BUF", 20, 20, False),
        ("2023_04_BUF_MIA", 2023, 4, "REG", "2023-10-01", "MIA", "BUF", 3, 17, False),
    ]
    tg = build_team_games(make_games(rows))
    snaps = pl.DataFrame({"season": [2023, 2023, 2023], "week": [1, 2, 3], "franchise_id": ["BUF"] * 3})
    out = evidence.next_n_win(tg, snaps, n=8).sort("week")
    assert out["win8"].to_list()[0] == pytest.approx(0.5)
    assert out["win8"].to_list()[1] == pytest.approx(0.75)
    assert out["win8"].to_list()[2] is None  # one game left


# --- real data ------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def real_scored():
    if not (CACHE_DIR / "schedules.parquet").exists():
        pytest.skip("no cached schedules; run `uv run fgs build` first")
    from conftest import derive_inputs
    from fgs.cli import derive
    from fgs.ingest import load_schedules
    from fgs.mood import score_frame

    derived = derive(load_schedules(), **derive_inputs())
    return score_frame(derived["features"]), derived["team_games"]


def test_next_n_win_null_pattern_matches_targets(real_scored):
    from fgs.backtest import targets

    scored, tg = real_scored
    snaps = scored.filter(pl.col("season") <= 2021).select("season", "week", "franchise_id")
    tg = tg.filter(pl.col("season") <= 2021)
    y = targets(tg, snaps, ns=(8,))
    w = evidence.next_n_win(tg, snaps, n=8)
    j = y.join(w, on=["season", "week", "franchise_id"], how="inner", validate="1:1")
    assert j.height == y.height
    assert (j["y8"].is_null() == j["win8"].is_null()).all()
    v = j["win8"].drop_nulls().to_numpy()
    assert ((v >= 0) & (v <= 1)).all()


def test_holdout_seal(real_scored):
    scored, tg = real_scored
    base = evidence.compute_evidence(scored, tg, "abc123abc123", "2026-01-01T00:00:00+00:00")
    assert set(base) == KEYS and base["train_seasons"] == [1999, 2021]
    assert base["threshold"] == season_config.GAP_THRESHOLD and base["first_week"] == season_config.GAP_FIRST_WEEK
    future = pl.col("season") > season_config.TRAIN_LAST_SEASON
    tg2 = tg.with_columns(
        pl.when(future).then(60).otherwise(pl.col("points_for")).cast(tg["points_for"].dtype).alias("points_for"),
        pl.when(future).then(0).otherwise(pl.col("points_against")).cast(tg["points_against"].dtype).alias("points_against"),
        pl.when(future).then(1.0).otherwise(pl.col("outcome")).alias("outcome"),
    )
    nmax = scored.group_by("season", "week").len()["len"].max()
    sc2 = scored.with_columns(
        pl.when(future).then(nmax + 1 - pl.col("rank")).otherwise(pl.col("rank")).cast(scored["rank"].dtype).alias("rank"))
    assert not sc2.equals(scored) and not tg2.equals(tg)
    assert evidence.compute_evidence(sc2, tg2, "abc123abc123", "2026-01-01T00:00:00+00:00") == base
    for f in ("hopeful", "worried"):
        assert base[f]["n"] > 100 and np.isfinite(base[f]["d_margin"])


def test_cli_evidence_writes_json(tmp_path, monkeypatch, real_scored):
    from fgs import cli

    out = tmp_path / "callout_evidence.json"
    monkeypatch.setattr(paths, "CALLOUT_EVIDENCE_PATH", out)
    assert cli.main(["evidence"]) == 0
    text = out.read_text()
    assert text.endswith("\n")
    d = json.loads(text)
    assert set(d) == KEYS and d["train_seasons"] == [1999, 2021] and len(d["weights_fingerprint"]) == 12
    json.dumps(d, allow_nan=False)

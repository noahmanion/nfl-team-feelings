import nflreadpy
import polars as pl
import pytest
from polars.testing import assert_frame_equal

from fgs.ingest import load_schedules

TINY = pl.DataFrame({"game_id": ["2026_01_A_B"], "season": [2026], "result": [3]})


def test_cache_written_then_reused_then_refreshed(tmp_path, monkeypatch):
    calls = []

    def fake():
        calls.append(1)
        return TINY

    monkeypatch.setattr(nflreadpy, "load_schedules", fake)
    first = load_schedules(cache_dir=tmp_path)
    assert (tmp_path / "schedules.parquet").exists()
    assert len(calls) == 1

    def boom():
        raise RuntimeError("network must not be touched when cached")

    monkeypatch.setattr(nflreadpy, "load_schedules", boom)
    assert_frame_equal(load_schedules(refresh=False, cache_dir=tmp_path), first)

    monkeypatch.setattr(nflreadpy, "load_schedules", fake)
    load_schedules(refresh=True, cache_dir=tmp_path)
    assert len(calls) == 2


def test_refresh_propagates_loader_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(nflreadpy, "load_schedules", lambda: (_ for _ in ()).throw(RuntimeError("down")))
    with pytest.raises(RuntimeError):
        load_schedules(refresh=True, cache_dir=tmp_path)

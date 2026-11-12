"""LOGO-01: one-shot ESPN logo download (mocked; no network) + committed-files guard."""

import hashlib
import inspect
import json
from pathlib import Path

import pytest

from fgs import cli, logos, paths
from fgs.franchises import CANONICAL

GOOD = b"\x89PNG\r\n\x1a\n" + b"\x00" * 2000


def _fake(calls: list[str]):
    def fetch(url: str) -> bytes:
        calls.append(url)
        return GOOD + url.encode()  # distinct bytes per team
    return fetch


def test_logo_url_mapping():
    assert logos.logo_url("KC") == "https://a.espncdn.com/i/teamlogos/nfl/500/kc.png"
    assert logos.logo_url("LA").endswith("/500/lar.png")
    assert logos.logo_url("WAS").endswith("/500/wsh.png")
    assert logos.logo_url("LV").endswith("/500/lv.png")
    with pytest.raises(ValueError):
        logos.logo_url("OAK")
    for f in CANONICAL:
        assert "wikipedia" not in logos.logo_url(f)


def test_mapping_matches_cached_teams():
    """Pitfall 4: /500/la.png and /500/was.png also return valid (wrong) PNGs."""
    p = paths.CACHE_DIR / "teams.parquet"
    if not p.exists():
        pytest.skip("teams cache missing")
    import polars as pl

    teams = pl.read_parquet(p).select("team_abbr", "team_logo_espn")
    espn = dict(zip(teams["team_abbr"].to_list(), teams["team_logo_espn"].to_list()))
    for f in sorted(CANONICAL):
        assert f in espn, f
        assert logos.logo_url(f).split("/500/")[1] == espn[f].split("/500/")[1], f


def test_validate_png():
    logos.validate_png(GOOD)
    with pytest.raises(ValueError):
        logos.validate_png(b"GIF89a" + b"\x00" * 2000)
    with pytest.raises(ValueError):
        logos.validate_png(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    with pytest.raises(ValueError):
        logos.validate_png((b"\x89PNG\r\n\x1a\n" + b"\x00" * 2000)[:1024])


def test_fetch_writes_skips_and_forces(tmp_path):
    calls: list[str] = []
    m = logos.fetch_logos(out_dir=tmp_path, fetch=_fake(calls), today="2026-11-11")
    assert len(calls) == 32
    assert sorted(p.name for p in tmp_path.glob("*.png")) == sorted(f"{f}.png" for f in CANONICAL)
    assert not list(tmp_path.glob("*.tmp"))

    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest == m
    assert list(manifest) == sorted(CANONICAL)
    kc = manifest["KC"]
    assert set(kc) == {"url", "sha256", "bytes", "fetched"}
    data = (tmp_path / "KC.png").read_bytes()
    assert kc["sha256"] == hashlib.sha256(data).hexdigest() and kc["bytes"] == len(data)
    assert kc["url"] == logos.logo_url("KC") and kc["fetched"] == "2026-11-11"

    calls.clear()
    m2 = logos.fetch_logos(out_dir=tmp_path, fetch=_fake(calls), today="2026-12-01")
    assert calls == []
    assert m2 == manifest  # skipped files keep their original fetched date

    logos.fetch_logos(out_dir=tmp_path, force=True, fetch=_fake(calls), today="2026-12-01")
    assert len(calls) == 32
    assert json.loads((tmp_path / "manifest.json").read_text())["KC"]["fetched"] == "2026-12-01"


def test_invalid_download_raises_without_partial(tmp_path):
    def bad(url: str) -> bytes:
        return b"<html>nope</html>"

    with pytest.raises(ValueError):
        logos.fetch_logos(out_dir=tmp_path, fetch=bad, today="2026-11-11")
    assert not list(tmp_path.glob("*.png")) and not list(tmp_path.glob("*.tmp"))
    assert not (tmp_path / "manifest.json").exists()


def test_cli_logos_subcommand_not_in_refresh(tmp_path, monkeypatch, capsys):
    with pytest.raises(SystemExit):
        cli.main(["logos", "--help"])
    assert "--force" in capsys.readouterr().out
    assert "logos" not in inspect.getsource(cli._cmd_refresh)

    monkeypatch.setattr(paths, "LOGOS_DIR", tmp_path)
    monkeypatch.setattr(logos, "_http_get", lambda url: GOOD + url.encode())
    assert cli.main(["logos"]) == 0
    assert len(list(tmp_path.glob("*.png"))) == 32


def test_committed_logos():
    d = paths.LOGOS_DIR
    if not d.exists():
        pytest.skip("web/public/logos not present")
    manifest = json.loads((d / "manifest.json").read_text())
    assert sorted(manifest) == sorted(CANONICAL)
    shas = set()
    for f in CANONICAL:
        data = (d / f"{f}.png").read_bytes()
        logos.validate_png(data)
        sha = hashlib.sha256(data).hexdigest()
        assert manifest[f]["sha256"] == sha and manifest[f]["bytes"] == len(data), f
        assert manifest[f]["url"] == logos.logo_url(f)
        shas.add(sha)
    assert len(shas) == 32  # a wrong code duplicating another team's image would collide
    assert not list(Path(d).glob("*.tmp"))

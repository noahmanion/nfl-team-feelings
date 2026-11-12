"""DATA-02: display-only 2021+ Vegas win totals. Validator accept/reject cases plus guards (D-12)
proving the lines can never reach vegas_expectations / vs_exp / the score."""

import ast
import re
import subprocess
from pathlib import Path

import polars as pl
import pytest

import fgs
from fgs import cli, paths, wintotals
from fgs.franchises import CANONICAL

F2021 = "win_totals_2021plus.csv"
F2026 = "win_totals_display_2026plus.csv"


def _raw(name: str) -> pl.DataFrame:
    return pl.read_csv(paths.INPUTS_DIR / name, infer_schema_length=0)


def _set(df: pl.DataFrame, i: int, col: str, val: str) -> pl.DataFrame:
    return df.with_columns(
        pl.when(pl.int_range(pl.len()) == i).then(pl.lit(val)).otherwise(pl.col(col)).alias(col)
    )


def _rejects(df: pl.DataFrame, name: str = F2021, match: str | None = None) -> None:
    with pytest.raises(ValueError, match=match):
        wintotals.validate(df, wintotals.FILES[name], name)


# --- accept ---------------------------------------------------------------------------------------

def test_committed_files_validate():
    for name, rng in wintotals.FILES.items():
        out = wintotals.validate(_raw(name), rng, name)
        assert out.height % 32 == 0 and set(out["franchise_id"]) == CANONICAL


def test_load_display_win_totals_shape():
    d = wintotals.load_display_win_totals()
    assert d.height == 192
    assert sorted(d["season"].unique().to_list()) == [2021, 2022, 2023, 2024, 2025, 2026]
    assert (d.group_by("season").len()["len"] == 32).all()
    assert set(d["franchise_id"]) == CANONICAL
    assert d.schema["line"] == pl.Float64 and d.schema["over_odds"] == pl.Int64


# --- reject ---------------------------------------------------------------------------------------

def test_rejects_wrong_or_reordered_columns():
    df = _raw(F2021)
    _rejects(df.select(df.columns[::-1]), match="columns")
    _rejects(df.drop("line_type"), match="columns")
    _rejects(df.rename({"line": "total"}), match="columns")


def test_rejects_season_outside_file_range():
    df = _raw(F2021)
    _rejects(_set(df, 0, "season", "2026"), match="outside")
    _rejects(_set(df, 0, "season", "2020"), match="outside")
    _rejects(_set(_raw(F2026), 0, "season", "2020"), F2026, match="outside")


def test_rejects_short_season():
    _rejects(_raw(F2021).slice(1), match="31 teams")


def test_rejects_duplicate_team():
    df = _raw(F2021)
    _rejects(_set(df, 1, "team", df["team"][0]), match="duplicate")


def test_rejects_unknown_team():
    _rejects(_set(_raw(F2021), 0, "team", "XXX"), match="unknown team")


@pytest.mark.parametrize("bad", ["7.3", "0", "-1", "-6.5", "abc", ""])
def test_rejects_bad_line(bad):
    _rejects(_set(_raw(F2021), 0, "line", bad), match="line")


def test_rejects_season_sum_out_of_tolerance():
    df = _raw(F2021)
    first = float(df["line"][0])
    _rejects(_set(df, 0, "line", str(first + 9.0)), match="sum")


@pytest.mark.parametrize("bad", ["http://example.com/x", "www.example.com/x", "/relative/path", "https://"])
def test_rejects_bad_source(bad):
    _rejects(_set(_raw(F2021), 0, "source", bad), match="https")


@pytest.mark.parametrize("bad", ["abc", "1.5"])
def test_rejects_bad_odds(bad):
    _rejects(_set(_raw(F2021), 0, "over_odds", bad), match="odds")
    _rejects(_set(_raw(F2021), 0, "under_odds", bad), match="odds")


def test_empty_odds_become_null():
    out = wintotals.validate(_set(_raw(F2021), 0, "over_odds", ""), wintotals.FILES[F2021], F2021)
    assert out["over_odds"].null_count() == 1


def test_rejects_unknown_line_type():
    _rejects(_set(_raw(F2021), 0, "line_type", "closing"), match="line_type")


def test_display_frame_rejects_overlap():
    d = wintotals.load_display_win_totals()
    fake = pl.DataFrame({"season": [2021], "team": ["KC"], "line": [10.5], "over_odds": [-110], "under_odds": [-110]})
    # 2021 is filtered out of the nflverse side, so no overlap; a forged 2020 display row does overlap
    assert wintotals.display_frame(fake, d).filter(pl.col("used_in_score")).height == 0
    nv = pl.DataFrame({"season": [2020], "team": ["KC"], "line": [11.5], "over_odds": [-110], "under_odds": [-110]})
    forged = d.head(1).with_columns(pl.lit(2020, pl.Int32).alias("season"), pl.lit("KC").alias("franchise_id"))
    with pytest.raises(ValueError, match="overlap"):
        wintotals.display_frame(nv, pl.concat([forged, d]))


def test_display_win_totals_degrades_on_bad_inputs(tmp_path, monkeypatch, capsys):
    """WR-01: a broken display-only file warns and drops the 2021+ rows; 2003-2020 rows still export."""
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "win_totals.csv").write_text("season,team,line,over_odds,under_odds\n2020,KC,11.5,-110,-110\n")
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    for name in wintotals.FILES:
        (inputs / name).write_text(",".join(wintotals.COLUMNS) + "\n")  # header only: "no rows"
    monkeypatch.setattr(paths, "INPUTS_DIR", inputs)
    out, skipped = cli._display_win_totals(cache)
    assert "WARNING" in capsys.readouterr().err
    assert len(skipped) == 2 and "skipped" in cli._skipped_msg(skipped)
    assert out.rows() == [("KC", 2020, 11.5, -110, -110, "nflverse", wintotals.WIN_TOTALS_URL, True)]


def test_display_win_totals_degrades_per_file(tmp_path, monkeypatch, capsys):
    """WR-01 (iteration 2): a malformed 2026plus file (e.g. a partial 2027 append) is skipped on its
    own; the valid write-once 2021-2025 lines survive and the skip is reported."""
    cache = tmp_path / "cache"
    cache.mkdir()
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / F2021).write_text((paths.INPUTS_DIR / F2021).read_text())
    good = (paths.INPUTS_DIR / F2026).read_text()
    partial = "\n".join(good.strip().splitlines()[1:4]).replace("2026,", "2027,")
    (inputs / F2026).write_text(good.rstrip("\n") + "\n" + partial + "\n")  # 3-team 2027 season
    monkeypatch.setattr(paths, "INPUTS_DIR", inputs)
    with pytest.raises(ValueError):
        wintotals.load_display_win_totals()  # strict path still raises
    out, skipped = cli._display_win_totals(cache)
    err = capsys.readouterr().err
    assert len(skipped) == 1 and F2026 in skipped[0] and F2026 in err and "WARNING" in err
    assert cli._skipped_msg([]) == ""
    seasons = sorted(set(out["season"].to_list()))
    assert seasons == [2021, 2022, 2023, 2024, 2025]
    assert out.height == 5 * 32 and not out["used_in_score"].any()


# --- guards (D-12) --------------------------------------------------------------------------------

def test_guard_cached_vegas_stops_at_2020():
    if not (paths.CACHE_DIR / "win_totals.csv").exists():
        pytest.skip("win_totals.csv not cached")
    v = cli._cached_vegas(paths.CACHE_DIR)
    assert v is not None and int(v["season"].max()) <= 2020


def test_guard_cached_vegas_drops_post_2020(tmp_path, capsys):
    """WR-02: a >2020 row in the cached CSV is dropped (with a warning), never passed through, and
    the 2020 expectation is unchanged by its presence."""
    rows = ["season,team,line,over_odds,under_odds", "2020,KC,11.5,-110,-110", "2020,BUF,8.5,-110,-110"]
    clean, dirty = tmp_path / "clean", tmp_path / "dirty"
    clean.mkdir()
    dirty.mkdir()
    (clean / "win_totals.csv").write_text("\n".join(rows) + "\n")
    (dirty / "win_totals.csv").write_text("\n".join(rows + ["2021,KC,12.5,-110,-110"]) + "\n")
    want = cli._cached_vegas(clean)
    assert "seasons > 2020" not in capsys.readouterr().err
    got = cli._cached_vegas(dirty)
    assert "seasons > 2020" in capsys.readouterr().err
    assert got is not None and int(got["season"].max()) <= 2020
    assert got.sort(got.columns).equals(want.sort(want.columns))


FORBIDDEN = ("wintotals", "INPUTS_DIR", "inputs/", "win_totals_2021plus", "display_2026plus")


def _strip_comments(text: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def test_guard_score_path_never_reads_inputs():
    src = Path(fgs.__file__).parent
    for name in ("expectation.py", "features.py", "score.py"):
        code = _strip_comments((src / name).read_text())
        hits = [t for t in FORBIDDEN if t in code]
        assert not hits, f"{name} references display-only win totals: {hits}"
    text = (src / "cli.py").read_text()
    tree = ast.parse(text)
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    for fn in ("derive_games", "derive", "cached_inputs", "_cached_vegas"):
        assert fn in funcs, f"cli.{fn} not found"
        code = _strip_comments(ast.get_source_segment(text, funcs[fn]))
        hits = [t for t in FORBIDDEN if t in code]
        assert not hits, f"cli.{fn} references display-only win totals: {hits}"


def test_guard_wintotals_importers():
    src = Path(fgs.__file__).parent
    imp = re.compile(r"^\s*(from|import)\s+[\w., ]*wintotals", re.M)
    hits = sorted(p.name for p in src.glob("*.py")
                  if p.name != "wintotals.py" and imp.search(_strip_comments(p.read_text())))
    assert set(hits) <= {"cli.py", "export.py"}, f"wintotals imported by {hits}"
    assert "cli.py" in hits


def test_guard_wintotals_not_fingerprinted():
    from fgs import fingerprint
    assert "wintotals.py" not in fingerprint.CODE_FILES
    assert all(name != "wintotals.py" for name, _ in fingerprint.CODE_FUNCS)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)


def test_guard_win_totals_2021plus_single_commit():
    root = paths.PIPELINE_ROOT.parent
    rel = "pipeline/inputs/win_totals_2021plus.csv"
    try:
        ok = _git(root, "rev-parse", "--is-inside-work-tree")
    except OSError:
        pytest.skip("git not available")
    if ok.stdout.strip() != "true":
        pytest.skip("not a git work tree")
    if _git(root, "rev-parse", "--is-shallow-repository").stdout.strip() == "true":
        pytest.skip("shallow clone")
    n = len(_git(root, "log", "--format=%H", "--", rel).stdout.split())
    if n == 0:
        pytest.skip("win_totals_2021plus.csv not committed yet")
    assert n == 1, f"{rel} has {n} commits; it is write-once (PREREGISTRATION_V2_DEVIATIONS A3.4)"
    dirty = _git(root, "status", "--porcelain", "--", rel).stdout.strip()
    assert not dirty, f"{rel} has uncommitted changes: {dirty}"

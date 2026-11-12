"""INTEG-01: frozen v1 scores and labels for seasons <= 2025 must never move.

Two checks against one pinned file (tests/golden/v1_scores_le2025.json):
- export check: the committed web/public/data/snapshots/{1999..2025}.json
- derive check: derive(load_schedules()) -> mood.score_frame, filtered to season <= 2025

Hash input: sorted rows of (season, week, franchise, score, label), one per line, UTF-8
(labels contain a curly apostrophe).

Re-pinning: `FGS_GOLDEN_REGEN=1 uv run python tests/test_golden_scores.py` from pipeline/.
Only for a deliberate, reviewed re-pin; never after a code change. Without the flag it refuses.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest

from fgs import paths

LAST = 2025
PIN = Path(__file__).parent / "golden" / "v1_scores_le2025.json"


def canon(rows) -> bytes:
    return "\n".join(f"{s},{w},{f},{sc},{lab}" for s, w, f, sc, lab in sorted(rows)).encode("utf-8")


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def pin_of(rows) -> dict:
    rows = list(rows)
    by_season: dict[int, list] = {}
    for r in rows:
        by_season.setdefault(r[0], []).append(r)
    return {
        "overall": _sha(canon(rows)),
        "per_season": {str(s): _sha(canon(rs)) for s, rs in sorted(by_season.items())},
        "rows": len(rows),
    }


def snapshots_dir(web_data_dir: Path | None = None) -> Path:
    return (web_data_dir or paths.WEB_DATA_DIR) / "snapshots"


def export_rows(web_data_dir: Path | None = None):
    for p in sorted(snapshots_dir(web_data_dir).glob("*.json")):
        if not p.stem.isdigit() or int(p.stem) > LAST:
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        season = int(d["season"])
        if season > LAST:
            continue
        for w, rows in d["weeks"].items():
            for r in rows:
                yield (season, int(w), r["franchise"], int(r["score"]), r["label"])


def derive_rows(scored: pl.DataFrame):
    sub = scored.filter(pl.col("season") <= LAST).select("season", "week", "franchise_id", "score", "label")
    for s, w, f, sc, lab in sub.iter_rows():
        yield (int(s), int(w), f, int(sc), lab)


def _compare(got: dict, want: dict, what: str) -> None:
    assert got["rows"] == want["rows"], f"{what}: {got['rows']} rows, pinned {want['rows']}"
    for season in sorted(want["per_season"], key=int):
        assert got["per_season"].get(season) == want["per_season"][season], (
            f"{what}: frozen scores/labels changed in season {season}"
        )
    assert set(got["per_season"]) == set(want["per_season"]), f"{what}: season set differs"
    assert got["overall"] == want["overall"], f"{what}: overall hash differs"


def _derive_pin(inputs: dict) -> dict:
    from fgs import cli, mood

    derived = cli.derive(cli.load_schedules(), **inputs)
    return pin_of(derive_rows(mood.score_frame(derived["features"])))


def test_golden_export_matches_pin():
    if not snapshots_dir().exists():
        pytest.skip("no exported snapshots")
    want = json.loads(PIN.read_text(encoding="utf-8"))
    _compare(pin_of(export_rows()), want, "export")


def test_golden_derive_matches_pin(real_cache):
    from conftest import derive_inputs

    want = json.loads(PIN.read_text(encoding="utf-8"))
    _compare(_derive_pin(derive_inputs()), want, "derive")


if __name__ == "__main__":
    if os.environ.get("FGS_GOLDEN_REGEN") != "1":
        sys.exit("refusing to re-pin: set FGS_GOLDEN_REGEN=1 (deliberate, reviewed re-pin only)")
    import tempfile

    from fgs import cli

    pin = pin_of(export_rows())
    with tempfile.TemporaryDirectory() as tmp:
        dpin = _derive_pin({**cli.cached_inputs(), "sim_cache_dir": Path(tmp)})
    if dpin != pin:
        sys.exit(f"refusing to re-pin: derive pin != export pin ({dpin['rows']} vs {pin['rows']} rows)")
    pin["generated_from"] = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=paths.PIPELINE_ROOT.parent,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    PIN.parent.mkdir(parents=True, exist_ok=True)
    PIN.write_text(json.dumps(pin, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"pinned {pin['rows']} rows, overall {pin['overall']}")

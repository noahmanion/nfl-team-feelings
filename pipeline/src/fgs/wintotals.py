"""Display-only Vegas preseason win totals for 2021+ (DATA-02, Phase 11).

These lines are shown next to a team's pace and NEVER feed vegas_expectations, vs_exp or the score.
The score's Vegas expectations stay the frozen nflverse 2003-2020 file (cli._cached_vegas enforces
<= 2020). This module is deliberately NOT in fingerprint.CODE_FILES; do not add it there.

Files (pipeline/inputs/, sourced and committed):
- win_totals_2021plus.csv: 2021-2025 closing lines. Write-once (PREREGISTRATION_V2_DEVIATIONS A3.4).
- win_totals_display_2026plus.csv: 2026+ lines. Future seasons are appended here, never to the 2021plus file.
"""

import re
from urllib.parse import urlparse

import polars as pl

from fgs import paths
from fgs.expectation import WIN_TOTALS_URL
from fgs.franchises import CANONICAL, RAW_TO_FRANCHISE
from fgs.season_config import reg_games

COLUMNS = ["season", "team", "line", "over_odds", "under_odds", "source", "entered_on", "line_type"]
LINE_TYPES = {"preseason_close", "preseason_open"}
FILES: dict[str, tuple[int, int | None]] = {
    "win_totals_2021plus.csv": (2021, 2025),
    "win_totals_display_2026plus.csv": (2026, None),
}
SUM_TOLERANCE = 8.0
TEAMS_PER_SEASON = 32
_INT = re.compile(r"^[+-]?\d+$")
_NUM = re.compile(r"^\d+(\.\d+)?$")
VALIDATED_SCHEMA = {
    "season": pl.Int32, "franchise_id": pl.Utf8, "line": pl.Float64, "over_odds": pl.Int64,
    "under_odds": pl.Int64, "source": pl.Utf8, "entered_on": pl.Utf8, "line_type": pl.Utf8,
}
DISPLAY_COLUMNS = ["franchise_id", "season", "line", "over_odds", "under_odds", "line_type", "source", "used_in_score"]


def _odds(v: str | None, where: str) -> int | None:
    if v is None or v.strip() == "":
        return None
    if not _INT.match(v.strip()):
        raise ValueError(f"{where}: odds {v!r} is not an integer or empty")
    return int(v.strip())


def validate(df: pl.DataFrame, file_seasons: tuple[int, int | None], name: str = "win totals") -> pl.DataFrame:
    """Validate an all-string frame (pl.read_csv(..., infer_schema_length=0)) against the D-11 rules and
    return it typed: season Int32, franchise_id, line Float64, over/under_odds Int64 (nullable), source,
    entered_on, line_type. Raises ValueError naming the file, season and row on the first failure."""
    if df.columns != COLUMNS:
        raise ValueError(f"{name}: columns {df.columns} != {COLUMNS}")
    lo, hi = file_seasons
    rows = []
    for i, r in enumerate(df.iter_rows(named=True), start=2):  # line 1 is the header
        where = f"{name} row {i}"
        s = (r["season"] or "").strip()
        if not _INT.match(s):
            raise ValueError(f"{where}: season {r['season']!r} is not an integer")
        season = int(s)
        if season < lo or (hi is not None and season > hi):
            raise ValueError(f"{where}: season {season} outside this file's range {lo}-{hi or 'open'}")
        team = (r["team"] or "").strip()
        fid = RAW_TO_FRANCHISE.get(team, team)
        if fid not in CANONICAL:
            raise ValueError(f"{where}: unknown team code {team!r}")
        lv = (r["line"] or "").strip()
        if not _NUM.match(lv):
            raise ValueError(f"{where}: line {r['line']!r} is not a positive number")
        line = float(lv)
        if line <= 0 or (line * 2) != int(line * 2):
            raise ValueError(f"{where}: line {line} must be a positive multiple of 0.5")
        src = (r["source"] or "").strip()
        u = urlparse(src)
        if u.scheme != "https" or not u.netloc:
            raise ValueError(f"{where}: source {src!r} is not an absolute https URL")
        lt = (r["line_type"] or "").strip()
        if lt not in LINE_TYPES:
            raise ValueError(f"{where}: line_type {lt!r} not in {sorted(LINE_TYPES)}")
        rows.append({
            "season": season, "franchise_id": fid, "line": line,
            "over_odds": _odds(r["over_odds"], where), "under_odds": _odds(r["under_odds"], where),
            "source": src, "entered_on": (r["entered_on"] or "").strip(), "line_type": lt,
        })
    if not rows:
        raise ValueError(f"{name}: no rows")
    out = pl.DataFrame(rows, schema=VALIDATED_SCHEMA)
    dup = out.group_by(["season", "franchise_id"]).len().filter(pl.col("len") > 1)
    if dup.height:
        raise ValueError(f"{name}: duplicate (season, team) {dup.select('season', 'franchise_id').rows()[:3]}")
    for (season,), part in out.group_by(["season"], maintain_order=True):
        if part.height != TEAMS_PER_SEASON:
            raise ValueError(f"{name} season {season}: {part.height} teams, expected {TEAMS_PER_SEASON}")
        total, want = float(part["line"].sum()), reg_games(int(season)) * 16
        if abs(total - want) > SUM_TOLERANCE:
            raise ValueError(f"{name} season {season}: lines sum to {total}, expected {want} +/- {SUM_TOLERANCE}")
    return out


def load_display_win_totals(inputs_dir=None) -> pl.DataFrame:
    """Both committed files, validated against their season ranges, sorted by season, franchise_id.
    Strict: raises on the first file that fails (used by the tests on the committed files)."""
    out, _ = _load_display(inputs_dir, strict=True)
    return out


def load_display_win_totals_lenient(inputs_dir=None) -> tuple[pl.DataFrame, list[str]]:
    """Per-file degradation (WR-01, iteration 2): each file is validated on its own; a file that fails
    is skipped and described in the returned problems list, while the files that validate are kept
    (so a bad 2026plus append never drops the write-once 2021-2025 lines)."""
    return _load_display(inputs_dir, strict=False)


def _load_display(inputs_dir, strict: bool) -> tuple[pl.DataFrame, list[str]]:
    d = paths.INPUTS_DIR if inputs_dir is None else inputs_dir  # read at call time
    frames, problems = [], []
    for fname, rng in FILES.items():
        try:
            frames.append(validate(pl.read_csv(d / fname, infer_schema_length=0), rng, fname))
        except (ValueError, OSError, pl.exceptions.PolarsError) as e:
            if strict:
                raise
            problems.append(f"{fname}: {type(e).__name__}: {e}")
    out = pl.concat(frames).sort(["season", "franchise_id"]) if frames else empty_display()
    dup = out.group_by(["season", "franchise_id"]).len().filter(pl.col("len") > 1)
    if dup.height:  # unreachable while FILES' season ranges are disjoint; kept as a guard
        raise ValueError(f"display win totals overlap across files: {dup.rows()[:3]}")
    return out, problems


def empty_display() -> pl.DataFrame:
    """A zero-row frame shaped like load_display_win_totals() (the runtime fallback when no committed
    display file validates: the export then carries only the nflverse 2003-2020 lines)."""
    return pl.DataFrame(schema=VALIDATED_SCHEMA)


def display_frame(nflverse_raw: pl.DataFrame | None, display: pl.DataFrame) -> pl.DataFrame:
    """Rows franchise_id, season, line, over_odds, under_odds, line_type, source, used_in_score for the
    export: nflverse 2003-2020 (used_in_score True, the lines the score actually used) plus the
    display-only 2021+ lines (used_in_score False)."""
    parts = []
    if nflverse_raw is not None and nflverse_raw.height:
        nv = nflverse_raw.filter(pl.col("season") <= 2020).select(
            pl.col("team").cast(pl.Utf8).replace(RAW_TO_FRANCHISE).alias("franchise_id"),
            pl.col("season").cast(pl.Int32),
            pl.col("line").cast(pl.Float64),
            pl.col("over_odds").cast(pl.Int64),
            pl.col("under_odds").cast(pl.Int64),
            pl.lit("nflverse").alias("line_type"),
            pl.lit(WIN_TOTALS_URL).alias("source"),
            pl.lit(True).alias("used_in_score"),
        )
        parts.append(nv)
    parts.append(display.select(
        "franchise_id", pl.col("season").cast(pl.Int32), "line", "over_odds", "under_odds", "line_type", "source",
        pl.lit(False).alias("used_in_score"),
    ))
    out = pl.concat(parts).sort(["franchise_id", "season"])
    dup = out.group_by(["season", "franchise_id"]).len().filter(pl.col("len") > 1)
    if dup.height:
        raise ValueError(f"nflverse and display win totals overlap on (season, franchise_id): {dup.rows()[:3]}")
    return out.select(DISPLAY_COLUMNS)

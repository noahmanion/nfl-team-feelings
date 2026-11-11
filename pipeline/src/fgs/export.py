"""The site JSON contract (D-06): the only interface between the pipeline and web/.

build_export is pure ({relative path: object}); write_export does the I/O.
"""

import json
import os
import re
import shutil
import tempfile
from pathlib import Path

import polars as pl

from fgs import asof, season_config
from fgs.franchises import CANONICAL
from fgs.mood import HYSTERESIS, bands_meta, score_frame

POSTSEASON = [("WC", "Wild Card"), ("DIV", "Divisional"), ("CON", "Conference Championships"), ("SB", "Super Bowl")]
_HEX = re.compile(r"^#[0-9A-F]{6}$")


def team_meta(teams: pl.DataFrame) -> dict[str, dict]:
    """Display metadata for the 32 canonical franchises (D-07). Drops LAR/OAK/SD/STL."""
    rows = teams.filter(pl.col("team_abbr").is_in(sorted(CANONICAL))).sort("team_abbr")
    assert rows.height == 32 and rows["team_abbr"].n_unique() == 32, f"expected 32 teams, got {rows.height}"
    out = {}
    for r in rows.iter_rows(named=True):
        primary, secondary = str(r["team_color"]).upper(), str(r["team_color2"]).upper()
        assert _HEX.match(primary) and _HEX.match(secondary), (r["team_abbr"], primary, secondary)
        out[r["team_abbr"]] = {"name": r["team_name"], "nick": r["team_nick"], "primary": primary, "secondary": secondary}
    return out


def _season_meta(season: int, snaps: pl.DataFrame, games: pl.DataFrame) -> dict:
    max_week = int(snaps["week"].max())
    g = games.filter(pl.col("season") == season)
    reg = g.filter(pl.col("game_type") == "REG")
    rw = int(reg["week"].max()) if not reg.is_empty() else season_config.reg_weeks(season)
    assert rw == season_config.reg_weeks(season), f"{season}: reg_weeks {rw} != config"
    labels = {"0": "Preseason"}
    for w in range(1, max_week + 1):
        if w <= rw:
            labels[str(w)] = f"Week {w}"
            continue
        types = g.filter(pl.col("week") == w)["game_type"].unique().to_list()
        idx = w - rw - 1
        assert len(types) == 1 and idx < len(POSTSEASON) and types[0] == POSTSEASON[idx][0], (season, w, types)
        labels[str(w)] = POSTSEASON[idx][1]
    return {
        "season": season, "max_week": max_week, "reg_weeks": rw,
        "n_teams": int(snaps["franchise_id"].n_unique()), "week_labels": labels,
    }


def _row(r: dict) -> dict:
    return {
        "franchise": r["franchise_id"], "rank": int(r["rank"]), "score": int(r["score"]),
        "elo": int(round(r["elo"])), "band": int(r["band"]), "label": r["label"], "emoji": r["emoji"],
        "wins": int(r["wins"]), "losses": int(r["losses"]), "ties": int(r["ties"]),
        "score_delta": None if r["score_delta"] is None else int(r["score_delta"]),
        "rank_delta": None if r["rank_delta"] is None else int(r["rank_delta"]),
    }


def build_export(derived: dict[str, pl.DataFrame], teams_df: pl.DataFrame, generated_at: str) -> dict[str, object]:
    games = derived["games"]
    scored = score_frame(derived["snapshots"]).sort(["season", "week", "rank"])
    teams = team_meta(teams_df)

    latest = asof.latest_played(games)
    assert latest is not None, "no played games"
    played, total = asof.week_progress(games, *latest)

    files: dict[str, object] = {}
    seasons_meta = []
    for season in sorted(scored["season"].unique().to_list()):
        snaps = scored.filter(pl.col("season") == season)
        seasons_meta.append(_season_meta(int(season), snaps, games))
        weeks: dict[str, list] = {}
        for r in snaps.iter_rows(named=True):
            weeks.setdefault(str(r["week"]), []).append(_row(r))
        files[f"snapshots/{season}.json"] = {"season": int(season), "weeks": weeks}

    s, w = latest
    files["latest.json"] = {"season": s, "week": w, "rows": files[f"snapshots/{s}.json"]["weeks"][str(w)]}

    files["meta.json"] = {
        "version": 1, "score_kind": "elo", "generated_at": generated_at,
        "data_through": asof.data_through(games, s, w),
        "latest": {"season": s, "week": w}, "partial_week": played < total,
        "seasons": seasons_meta, "bands": bands_meta(), "hysteresis": HYSTERESIS, "teams": teams,
    }

    keys = [f"{sm['season']}-{wk}" for sm in seasons_meta for wk in range(sm["max_week"] + 1)]
    index = {k: i for i, k in enumerate(keys)}
    hist: dict[str, list] = {f: [None] * len(keys) for f in sorted(teams)}
    for f, part in scored.sort(["season", "week"]).group_by("franchise_id", maintain_order=True):
        fid = f[0]
        for se, wk, sc in zip(part["season"], part["week"], part["score"]):
            hist[fid][index[f"{se}-{wk}"]] = int(sc)
        files[f"teams/{fid}.json"] = {
            "franchise": fid, **teams[fid],
            "history": {
                "season": part["season"].to_list(), "week": part["week"].to_list(),
                "score": part["score"].to_list(), "elo": [int(round(e)) for e in part["elo"]],
                "label": part["label"].to_list(),
            },
        }
    files["history.json"] = {"keys": keys, "teams": hist}
    files["callouts.json"] = []
    return files


def write_export(files: dict[str, object], out_dir: Path) -> None:
    """Replace out_dir with exactly `files`, all at once.

    Everything is written to a sibling temp dir first, then swapped in with two renames, so a
    crash mid-write never leaves a mix of old and new files (the old set stays in place). out_dir
    is owned by the export: anything else in it is dropped.
    """
    out_dir = Path(out_dir)
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    new = Path(tempfile.mkdtemp(dir=out_dir.parent, prefix=f".{out_dir.name}.new-"))
    new.chmod(0o755)  # mkdtemp makes it 0700; the swapped-in dir should look like a normal one
    try:
        for rel, obj in files.items():
            path = new / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    except BaseException:
        shutil.rmtree(new, ignore_errors=True)
        raise

    if not out_dir.exists():
        os.replace(new, out_dir)
        return
    old = Path(tempfile.mkdtemp(dir=out_dir.parent, prefix=f".{out_dir.name}.old-"))
    os.replace(out_dir, old)  # POSIX: renaming a dir onto an empty dir replaces it
    try:
        os.replace(new, out_dir)
    except BaseException:
        os.replace(old, out_dir)  # put the previous export back
        shutil.rmtree(new, ignore_errors=True)
        raise
    shutil.rmtree(old, ignore_errors=True)

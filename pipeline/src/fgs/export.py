"""The site JSON contract (D-06): the only interface between the pipeline and web/.

build_export is pure ({relative path: object}); write_export does the I/O.
"""

import json
import os
import re
import shutil
import tempfile
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl

from fgs import asof, draft, explain, fingerprint, insights, methodology, mood, paths, records, score, season_config
from fgs.franchises import CANONICAL
from fgs.mood import HYSTERESIS, bands_meta, score_frame
from fgs.season_config import SEEDS

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
    labels = {"0": "Preseason (after draft)"}
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


def _preseason(r: dict, first_season: int) -> str:
    """Week-0 blurb kind: seeded expansion/re-entry team, first season in the data, or carry-over."""
    if (r["franchise_id"], int(r["season"])) in SEEDS:
        return "expansion"
    return "fresh" if int(r["season"]) == first_season else "carry"


def _playoff_display(scored: pl.DataFrame, games: pl.DataFrame) -> pl.DataFrame:
    """Add playoff_display: the integer playoff odds fans see (round(100 * raw sim value)).

    A5 override (display only): once every REG game of a season is played with asof_week <= the
    snapshot week, franchises in any non-REG game row that season show 100. Everyone else shows 0
    only once the post-season field is fully known (playoff_teams(season) distinct franchises in
    non-REG rows); before that (e.g. wildcard week, when bye teams have no row yet) they keep the
    raw sim value. The raw playoff_prob column (the po_trend input) is left untouched
    (RESEARCH Pitfall 8)."""
    g = games.with_columns(pl.col("season").cast(pl.Int32))
    reg = g.filter(pl.col("is_reg")).group_by("season").agg(
        pl.col("played").all().alias("_reg_done"), pl.col("asof_week").max().cast(pl.Int32).alias("_reg_end"),
    )
    post = g.filter(~pl.col("is_reg"))
    post_teams = (
        pl.concat([post.select("season", pl.col("home_id").alias("franchise_id")),
                   post.select("season", pl.col("away_id").alias("franchise_id"))])
        .unique()
        .with_columns(pl.lit(True).alias("_in_post"))
    )
    # looked up at call time (season_config.playoff_teams) so tests can monkeypatch it
    n_post = post_teams.group_by("season").len().rename({"len": "_n_post"})
    n_post = n_post.with_columns(
        pl.Series("_spots", [season_config.playoff_teams(int(s)) for s in n_post["season"]], dtype=pl.Int64)
    )
    reg_done = pl.col("_reg_done").fill_null(False) & (pl.col("week") >= pl.col("_reg_end"))
    in_post = pl.col("_in_post").fill_null(False)
    field_known = pl.col("_n_post").fill_null(0) >= pl.col("_spots").fill_null(1 << 30)
    raw = (pl.col("playoff_prob") * 100).round(0).cast(pl.Int64)
    return (
        scored.with_columns(pl.col("season").cast(pl.Int32))
        .join(reg, on="season", how="left")
        .join(n_post, on="season", how="left")
        .join(post_teams, on=["season", "franchise_id"], how="left")
        .with_columns(
            pl.when(reg_done & in_post).then(100)
            .when(reg_done & field_known).then(0)
            .otherwise(raw).cast(pl.Int64).alias("playoff_display")
        )
        .drop("_reg_done", "_reg_end", "_n_post", "_spots", "_in_post")
    )


def _playoff_int(r: dict) -> int | None:
    """Displayed playoff odds as an int 0-100; None when the frame has no sim (no column)."""
    v = r.get("playoff_display")
    return None if v is None else int(v)


def _draft_ranks(scored: pl.DataFrame) -> dict[tuple[int, str], int]:
    """(season, franchise) -> 1-based rank of week-0 draft surplus within the season (highest first,
    ties by franchise id), over rows with a derivable draft only."""
    if "draft_surplus" not in scored.columns:
        return {}
    w0 = (
        scored.filter((pl.col("week") == 0) & pl.col("draft_surplus").is_not_null())
        .sort(["season", "draft_surplus", "franchise_id"], descending=[False, True, False])
        .with_columns(pl.int_range(1, pl.len() + 1).over("season").alias("_drank"))
    )
    return {(int(s), f): int(k) for s, f, k in zip(w0["season"], w0["franchise_id"], w0["_drank"])}


def _draft_info(r: dict, ctx: dict) -> dict | None:
    """Row.draft: only on week-0 rows with a derivable draft (and a value chart); None otherwise."""
    s = r.get("draft_surplus")
    values = ctx.get("values")
    if int(r["week"]) != 0 or s is None or values is None:
        return None
    moves = bool(ctx["moves_score"])
    return {
        "surplus": round(float(s), 1) + 0.0,
        "z": round(float(r["draft_z"]), 2) + 0.0,
        # null when the text says "about even with their original slots" (no pick equivalent)
        "equiv_pick": None if draft.is_even(float(s)) else draft.equiv_pick(float(s), values),
        "rank": ctx["ranks"][(int(r["season"]), r["franchise_id"])],
        "text": explain.draft_text(float(s), values, moves),
        "moves_score": moves,
    }


def _row(r: dict, factor_keys: list[str], nicks: dict[str, str], first_season: int,
         draft_ctx: dict | None = None) -> dict:
    """One snapshot row. draft_ctx = {"values", "moves_score", "ranks", "threshold"} (None: no draft)."""
    draft_ctx = draft_ctx or {}
    return {
        "franchise": r["franchise_id"], "rank": int(r["rank"]), "score": int(r["score"]),
        "elo": int(round(r["elo"])), "band": int(r["band"]), "label": r["label"], "emoji": r["emoji"],
        "wins": int(r["wins"]), "losses": int(r["losses"]), "ties": int(r["ties"]),
        "score_delta": None if r["score_delta"] is None else int(r["score_delta"]),
        "rank_delta": None if r["rank_delta"] is None else int(r["rank_delta"]),
        # + 0.0 turns -0.0 (negative weight * 0, or a tiny negative rounded) into 0.0
        "contribs": {k: round(float(r[f"contrib_{k}"]), 2) + 0.0 for k in factor_keys},
        "points": {k: int(r[f"pts_{k}"]) for k in factor_keys},
        "blurb": explain.blurb(
            r, factor_keys, nicks.get(r["franchise_id"], r["franchise_id"]), int(r["week"]),
            _preseason(r, first_season), draft_threshold=draft_ctx.get("threshold"),
        ),
        "playoff_prob": _playoff_int(r),
        # display columns; None when the features frame lacks them
        "expectation_source": r.get("expectation_source"),
        "qb": r.get("qb_name"),
        "draft": _draft_info(r, draft_ctx),
    }


def _games_file(games: pl.DataFrame, season: int) -> dict:
    """Columnar game list for one season (whole schedule; unplayed games keep null scores)."""
    g = games.filter(pl.col("season") == season).sort(["gameday", "gametime", "game_id"], nulls_last=True)
    played = pl.col("played")
    g = g.with_columns(
        pl.when(played).then(pl.col("home_score")).otherwise(None).alias("home_score"),
        pl.when(played).then(pl.col("away_score")).otherwise(None).alias("away_score"),
    )
    return {
        "season": int(season),
        "week": g["week"].to_list(), "asof_week": g["asof_week"].to_list(),
        "home": g["home_id"].to_list(), "away": g["away_id"].to_list(),
        "home_score": g["home_score"].to_list(), "away_score": g["away_score"].to_list(),
        "game_type": g["game_type"].to_list(), "gameday": g["gameday"].to_list(),
        "neutral": [bool(x) for x in g["neutral"].fill_null(False).to_list()],
    }


def _export_weights(derived: dict, scored: pl.DataFrame) -> dict[str, float]:
    """The weights that produced contrib_*: derived["weights"] when present (derive_games sets
    it), else weights.yaml. Either way, check contrib_f == w_f * z_f so meta.factors can never
    disagree with the shipped contributions (raises ValueError, not assert: survives python -O)."""
    weights = derived.get("weights")
    if weights is None:
        weights = score.load_weights()
    weights = dict(weights)
    missing = [c for k in weights for c in (f"z_{k}", f"contrib_{k}") if c not in scored.columns]
    if missing:
        raise ValueError(f"features frame lacks {missing}; it was not derived with these weights")
    # contrib_draft is the offseason term (weights.yaml offseason.draft), not a weights: factor
    extra = sorted(c for c in scored.columns if c.startswith("contrib_") and c != "contrib_draft"
                   and c.removeprefix("contrib_") not in weights)
    if extra:
        raise ValueError(f"features frame has contributions {extra} for factors not in the weights")
    for k, w in weights.items():
        err = scored.select((pl.col(f"contrib_{k}") - w * pl.col(f"z_{k}")).abs().max()).item()
        if err is not None and err > 1e-9:
            raise ValueError(f"contrib_{k} does not equal {w} * z_{k} (max diff {err:.3g}); weights mismatch")
    return weights


def _load_evidence(
    fp_weights: dict[str, float], evidence: dict | None = None, *, scored: pl.DataFrame, team_games: pl.DataFrame,
) -> dict:
    """The committed perception-gap base rates (pipeline/callout_evidence.json, read at call time via
    paths.CALLOUT_EVIDENCE_PATH unless passed in), checked against the current config so stale
    numbers can never ship (ValueError, not assert: survives python -O). WR-02: besides threshold,
    window and training seasons, the check covers every input that moves 1999-2021 score ranks
    (fgs.fingerprint): the weights, the Elo hyperparameters, the code version and a hash of the
    1999-2021 data (scored + team_games, so pass the frames the export ships). Only reads JSON:
    the export never imports fgs.evidence (it imports the backtest). A flavor with no usable cases
    (n=0, null rates) is accepted: insights.evidence_text then omits its evidence line (WR-03)."""
    if evidence is None:
        path = paths.CALLOUT_EVIDENCE_PATH
        if not path.exists():
            raise ValueError(f"{path} is missing; run `uv run fgs evidence` and commit it")
        evidence = json.loads(path.read_text(encoding="utf-8"))
    want = {
        "threshold": season_config.GAP_THRESHOLD,
        "first_week": season_config.GAP_FIRST_WEEK,
        "train_seasons": [1999, season_config.TRAIN_LAST_SEASON],
        **fingerprint.evidence_fingerprints(insights.weights_fingerprint(fp_weights), scored, team_games),
    }
    bad = {k: (evidence.get(k), v) for k, v in want.items() if evidence.get(k) != v}
    if bad:
        detail = ", ".join(f"{k} {have!r} != {need!r}" for k, (have, need) in bad.items())
        raise ValueError(f"callout_evidence.json is stale ({detail}); run `uv run fgs evidence` and commit it")
    return evidence


NFL_TZ = ZoneInfo("America/New_York")


def as_of_date(generated_at: str) -> date:
    """The export's calendar date in US Eastern time (WR-09): nflverse gamedays are local ET dates,
    so a UTC date would add a day to every active streak for exports run after 8 pm ET. A naive
    timestamp is taken as UTC."""
    ts = datetime.fromisoformat(generated_at)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=ZoneInfo("UTC"))
    return ts.astimezone(NFL_TZ).date()


def build_export(
    derived: dict, teams_df: pl.DataFrame, generated_at: str, *, evidence: dict | None = None,
) -> dict[str, object]:
    """evidence: the perception-gap base rates; None loads paths.CALLOUT_EVIDENCE_PATH. Either way it
    is validated against the current threshold, window, training seasons and the fgs.fingerprint
    hashes (weights, Elo params, code, 1999-2021 data)."""
    games = derived["games"]
    scored = score_frame(derived["features"]).sort(["season", "week", "rank"])
    teams = team_meta(teams_df)
    weights = _export_weights(derived, scored)
    cfg = derived.get("offseason") or score.load_offseason()
    draft_live = score.offseason_live(cfg)  # raises on a display_only / weight mismatch
    if draft_live and "contrib_draft" not in scored.columns:
        raise ValueError("offseason.draft weight is nonzero but the features carry no contrib_draft")
    factor_keys = list(weights) + (["draft"] if draft_live else [])
    ref = mood.reference_values(derived["features"])  # the same frozen reference score_frame used
    baseline = explain.baseline(ref)
    scored = explain.add_points(scored, factor_keys, ref)
    if derived.get("sim") is not None and "playoff_prob" in scored.columns:
        # restore the snapshot sort: the joins in _playoff_display may reorder rows
        scored = _playoff_display(scored, games).sort(["season", "week", "rank"])
    nicks = {abbr: t["nick"] for abbr, t in teams.items()}
    ev = _load_evidence(insights.fingerprint_weights(weights, cfg), evidence, scored=scored,
                        team_games=derived["team_games"])
    as_of = as_of_date(generated_at)  # active streaks count through the export date (US Eastern)
    latest = asof.latest_played(games)
    assert latest is not None, "no played games"
    # WR-01: the latest week's streak cards count through as_of, like records.json active
    by_week = insights.callouts_by_week(scored, derived["team_games"], nicks, ev, games=games, as_of=as_of,
                                        latest=latest)
    factors = [
        {"key": k, "label": score.FACTORS[k]["label"], "weight": w, "description": score.FACTORS[k]["description"]}
        for k, w in weights.items()
    ]
    if draft_live:
        od = score.OFFSEASON_FACTORS["draft"]
        factors.append({"key": "draft", "label": od["label"], "weight": cfg["weight"], "description": od["description"]})
    values = derived.get("draft_values")
    draft_ctx = {
        "values": values, "moves_score": draft_live, "ranks": _draft_ranks(scored),
        # the week-0 lead may mention draft capital only when the score carries it (CR-03); with
        # weight 0 the draft is shown only in its own "doesn't move the score" line
        "threshold": None if values is None or not draft_live else float(values[64]),
    }

    played, total = asof.week_progress(games, *latest)

    files: dict[str, object] = {}
    seasons_meta = []
    first_season = int(scored["season"].min())
    for season in sorted(scored["season"].unique().to_list()):
        snaps = scored.filter(pl.col("season") == season)
        seasons_meta.append(_season_meta(int(season), snaps, games))
        weeks: dict[str, list] = {}
        for r in snaps.iter_rows(named=True):
            weeks.setdefault(str(r["week"]), []).append(_row(r, factor_keys, nicks, first_season, draft_ctx))
        callouts = {str(w): by_week[(int(season), int(w))] for w in sorted({int(k) for k in weeks})
                    if by_week.get((int(season), int(w)))}
        files[f"snapshots/{season}.json"] = {"season": int(season), "weeks": weeks, "callouts": callouts}
        files[f"games/{season}.json"] = _games_file(games, int(season))

    s, w = latest
    files["latest.json"] = {"season": s, "week": w, "rows": files[f"snapshots/{s}.json"]["weeks"][str(w)]}

    files["meta.json"] = {
        "version": 1, "score_kind": "composite", "factors": factors, "baseline": baseline, "generated_at": generated_at,
        "data_through": asof.data_through(games, s, w),
        "latest": {"season": s, "week": w}, "partial_week": played < total,
        "seasons": seasons_meta, "bands": bands_meta(), "hysteresis": HYSTERESIS, "teams": teams,
        "offseason": {"draft": {
            "weight": cfg["weight"], "display_only": cfg["display_only"], "chart": cfg["chart"],
            "decay": [float(d) for d in cfg["decay"]],  # weeks 0-3: [1, 0.75, 0.5, 0.25]
        }},
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
    files["callouts.json"] = by_week.get((int(s), int(w)), [])  # the flat list for meta.latest
    files["records.json"] = records.build_records(scored, games, as_of)
    # built from committed evidence only (weights.yaml + FREEZE_RESULT + optional HOLDOUT_RESULT);
    # in `files` so write_export swaps it in atomically with everything else (Pitfall 3)
    files["methodology.json"] = methodology.build_methodology(weights, *methodology.load_evidence(), live=int(s))
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
            path.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False, allow_nan=False), encoding="utf-8")
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

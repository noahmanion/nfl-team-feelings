"""Phase 8 records (INSIGHT-03, INSIGHT-04): saddest/happiest team-seasons, longest misery/joy
streaks, every team's active streak, and the RECORDS_CHECK.md hand-check renderer.

Pure (polars + stdlib). Upstream of the backtest firewall: imports only fgs.insights and
fgs.season_config (never backtest or evidence).
"""

import math
from datetime import date

import polars as pl

from fgs import insights, season_config

TOP_N = 10
# Famous team-seasons the hand-check always shows with their full-list rank (RESEARCH Open Q4):
# membership in the top 10 is never asserted (Pitfall 9: the boundaries move with any weight change).
NOTABLE: tuple[tuple[int, str, str], ...] = ((2008, "DET", "saddest"), (2017, "CLE", "saddest"), (2007, "NE", "happiest"))


def _round(x: float) -> int:
    return int(math.floor(x + 0.5))


def _rec(w: int, l_: int, t: int) -> str:
    return insights.record_text(int(w), int(l_), int(t))


def _reg_rows(scored: pl.DataFrame) -> pl.DataFrame:
    rw = pl.col("season").map_elements(season_config.reg_weeks, return_dtype=pl.Int64)
    return scored.with_columns(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32)).filter(
        (pl.col("week") >= 1) & (pl.col("week") <= rw))


def final_records(scored: pl.DataFrame) -> dict[tuple[int, str], tuple[int, int, int]]:
    """(season, franchise) -> W-L-T on the last REG-week row (the latest one for a season in progress)."""
    last = _reg_rows(scored).sort("season", "franchise_id", "week").group_by(
        "season", "franchise_id", maintain_order=True).last()
    return {(int(s), f): (int(w), int(l_), int(t)) for s, f, w, l_, t in
            last.select("season", "franchise_id", "wins", "losses", "ties").iter_rows()}


def in_progress_seasons(games: pl.DataFrame) -> set[int]:
    """Seasons with at least one unplayed REG game (the current season until its REG ends)."""
    reg = games.filter(pl.col("is_reg") & ~pl.col("played"))
    return {int(s) for s in reg["season"].unique().to_list()}


def team_season_extremes(
    scored: pl.DataFrame, dates: pl.DataFrame, exclude_seasons: set[int] | frozenset[int] = frozenset(),
) -> dict[str, list[dict]]:
    """Full ranked lists {"saddest": [...], "happiest": [...]}, one entry per team-season.

    REG weeks only (1..reg_weeks); seeded expansion team-seasons (season_config.SEEDS) excluded, and
    so is every season in exclude_seasons (WR-08: build_records passes the in-progress season, whose
    partial-season mean is not comparable with a full season's and would rank on a partial sample).
    Saddest: min score asc, REG mean asc, min composite asc, season, franchise. Happiest: max score
    desc, REG mean desc, max composite desc, season, franchise (scores clip at 0/100, so the chain
    is what decides). week/date = first week the min/max was reached; W-L-T = last REG-week row."""
    is_seed = pl.lit(False)
    for f, s in season_config.SEEDS:
        is_seed = is_seed | ((pl.col("franchise_id") == f) & (pl.col("season") == s))
    reg = _reg_rows(scored).filter(~is_seed & ~pl.col("season").is_in(sorted(exclude_seasons)))
    reg = reg.join(dates, on=["season", "week"], how="left").sort("season", "franchise_id", "week")
    agg = reg.group_by("season", "franchise_id").agg(
        pl.col("score").min().alias("min"), pl.col("score").max().alias("max"),
        pl.col("score").mean().alias("mean"),
        pl.col("composite").min().alias("cmin"), pl.col("composite").max().alias("cmax"),
        pl.col("week").filter(pl.col("score") == pl.col("score").min()).first().alias("wmin"),
        pl.col("date").filter(pl.col("score") == pl.col("score").min()).first().alias("dmin"),
        pl.col("week").filter(pl.col("score") == pl.col("score").max()).first().alias("wmax"),
        pl.col("date").filter(pl.col("score") == pl.col("score").max()).first().alias("dmax"),
        pl.col("wins").last(), pl.col("losses").last(), pl.col("ties").last(),
    )

    def entries(df: pl.DataFrame, sc: str, wk: str, dt: str) -> list[dict]:
        return [{
            "season": int(r["season"]), "franchise": r["franchise_id"], "score": int(r[sc]), "week": int(r[wk]),
            "date": None if r[dt] is None else r[dt].isoformat(),
            "wins": int(r["wins"]), "losses": int(r["losses"]), "ties": int(r["ties"]), "mean": _round(r["mean"]),
        } for r in df.iter_rows(named=True)]

    sad = agg.sort(["min", "mean", "cmin", "season", "franchise_id"])
    happy = agg.sort(["max", "mean", "cmax", "season", "franchise_id"], descending=[True, True, True, False, False])
    return {"saddest": entries(sad, "min", "wmin", "dmin"), "happiest": entries(happy, "max", "wmax", "dmax")}


def _run_entry(r: dict, recs: dict, latest_season: int) -> dict:
    last = latest_season if r["active"] else int(r["end_season"])
    seasons = [{"season": y, "wins": recs[(y, r["franchise_id"])][0], "losses": recs[(y, r["franchise_id"])][1],
                "ties": recs[(y, r["franchise_id"])][2]}
               for y in range(int(r["start_season"]), last + 1) if (y, r["franchise_id"]) in recs]
    return {
        "franchise": r["franchise_id"], "start": r["start"].isoformat(),
        "end": None if r["end"] is None else r["end"].isoformat(), "days": int(r["days"]), "active": bool(r["active"]),
        "start_season": int(r["start_season"]), "start_week": int(r["start_week"]),
        "end_season": int(r["end_season"]), "end_week": int(r["end_week"]), "seasons": seasons,
    }


def streak_records(run_df: pl.DataFrame, kind: str, recs: dict, latest_season: int, n: int = TOP_N) -> list[dict]:
    """Longest runs of one kind: days desc, start asc, franchise asc. seasons = final REG record of
    every season from start_season to end_season (active runs: through latest_season)."""
    top = run_df.filter(pl.col("kind") == kind).sort(["days", "start", "franchise_id"],
                                                      descending=[True, False, False]).head(n)
    return [_run_entry(r, recs, latest_season) for r in top.iter_rows(named=True)]


def active_streaks(run_df: pl.DataFrame) -> dict[str, dict]:
    """{abbr: {kind, start, days, start_season, start_week}} for every team whose last snapshot is
    inside a misery or joy run (the two are disjoint, so at most one per team)."""
    out = {}
    for r in run_df.filter(pl.col("active")).sort("franchise_id", "kind").iter_rows(named=True):
        out[r["franchise_id"]] = {"kind": r["kind"], "start": r["start"].isoformat(), "days": int(r["days"]),
                                  "start_season": int(r["start_season"]), "start_week": int(r["start_week"])}
    return out


def build_records(scored: pl.DataFrame, games: pl.DataFrame, as_of: date) -> dict:
    """The records.json contract (plan 08-03)."""
    dates = insights.snapshot_dates(games, as_of)
    run_df = insights.all_runs(insights.timelines(scored, dates), as_of)
    ext = team_season_extremes(scored, dates, in_progress_seasons(games))
    recs = final_records(scored)
    latest = int(scored["season"].max())
    notable = []
    for season, fid, lst in NOTABLE:
        for i, e in enumerate(ext[lst]):
            if e["season"] == season and e["franchise"] == fid:
                notable.append({"season": season, "franchise": fid, "list": lst, "rank": i + 1, "score": e["score"],
                                "mean": e["mean"], "wins": e["wins"], "losses": e["losses"], "ties": e["ties"]})
                break
    return {
        "as_of": as_of.isoformat(),
        "saddest": ext["saddest"][:TOP_N],
        "happiest": ext["happiest"][:TOP_N],
        "misery": streak_records(run_df, "misery", recs, latest),
        "joy": streak_records(run_df, "joy", recs, latest),
        "active": active_streaks(run_df),
        "excluded": [{"season": s, "franchise": f, "reason": "expansion seed"}
                     for f, s in sorted(season_config.SEEDS, key=lambda k: (k[1], k[0]))],
        "notable": notable,
    }


# --- RECORDS_CHECK.md -----------------------------------------------------------------------------

def _extreme_table(rows: list[dict], word: str) -> list[str]:
    out = ["| # | Team-season | Score | When | Final REG | Sanity note |", "|---|---|---|---|---|---|"]
    for i, e in enumerate(rows, 1):
        rec = _rec(e["wins"], e["losses"], e["ties"])
        out.append(f"| {i} | {e['season']} {e['franchise']} | {e['score']} | Week {e['week']} ({e['date']}) | {rec} | "
                   f"Final REG {rec}; {word} score {e['score']} first reached Week {e['week']} ({e['date']}); "
                   f"REG mean {e['mean']} |")
    return out


def _streak_table(rows: list[dict]) -> list[str]:
    out = ["| # | Team | Days | When | Final REG records | Sanity note |", "|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        recs = ", ".join(f"{s['season']} {_rec(s['wins'], s['losses'], s['ties'])}" for s in r["seasons"])
        end = r["end"] or "still going"
        span = f"{r['start_season']} wk {r['start_week']} → {r['end_season']} wk {r['end_week']}"
        out.append(f"| {i} | {r['franchise']}{' (active)' if r['active'] else ''} | {r['days']:,} | {span} | {recs} | "
                   f"{r['start']} → {end}; seasons: {recs} |")
    return out


def records_check_md(records: dict) -> str:
    """Hand-check file for the verifier (pipeline/RECORDS_CHECK.md), rendered from records.json only."""
    lines = [
        "# RECORDS_CHECK",
        "",
        f"Generated by `fgs export` / `fgs refresh` from records.json (as of {records['as_of']}). "
        "Regenerated on every export: do not hand-edit. Compare each row against known NFL history.",
        "",
        "Rules: misery = score under 20, joy = score 80 or higher, measured in calendar days across season "
        "boundaries (week 0 dated at the draft's last day; week N at the last gameday of that week). Active "
        f"streaks count through {records['as_of']}. Team-season extremes use REG weeks only, one entry per "
        "team-season; ties at the 0/100 clip break by REG mean score, then composite. Expansion seeds are excluded, "
        "and a season in progress joins the team-season lists only once its last REG game is played.",
        "",
        f"## Saddest team-seasons (lowest score; top {len(records['saddest'])})",
        "",
        *_extreme_table(records["saddest"], "min"),
        "",
        f"## Happiest team-seasons (highest score; top {len(records['happiest'])})",
        "",
        *_extreme_table(records["happiest"], "max"),
        "",
        f"## Longest misery streaks (top {len(records['misery'])})",
        "",
        *_streak_table(records["misery"]),
        "",
        f"## Longest joy streaks (top {len(records['joy'])})",
        "",
        *_streak_table(records["joy"]),
        "",
        "## Notable non-entries",
        "",
        "Famous seasons shown with their rank on the FULL list (whether or not they made the top 10).",
        "",
        "| Team-season | List | Rank | Score | REG mean | Final REG |",
        "|---|---|---|---|---|---|",
        *[f"| {n['season']} {n['franchise']} | {n['list']} | {n['rank']} | {n['score']} | {n['mean']} | "
          f"{_rec(n['wins'], n['losses'], n['ties'])} |" for n in records["notable"]],
        "",
        "## Excluded",
        "",
        *[f"- {e['season']} {e['franchise']}: {e['reason']} (starts below the league mean by assumption, not by "
          "results; excluded from the team-season lists, and its week-0 row is dropped from streaks)"
          for e in records["excluded"]],
        "",
        "## Active streaks",
        "",
        *([f"- {abbr}: {a['kind']} since {a['start']} ({a['days']:,} days)" for abbr, a in
           sorted(records["active"].items())] or ["- none"]),
        "",
        "## Reviewer checklist",
        "",
        "- [ ] Saddest list is made of genuinely bad seasons (final records mostly 1-4 wins)",
        "- [ ] Happiest list is made of genuinely great seasons (2007 NE near the top)",
        "- [ ] No misery run contains a winning season; no joy run contains a losing one",
        "- [ ] Active streaks match the current standings",
        "- [ ] Notable non-entries ranks are plausible",
        "",
    ]
    return "\n".join(lines)

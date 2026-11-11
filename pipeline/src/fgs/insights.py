"""Phase 8 callouts: perception gaps (INSIGHT-02), misery/joy streaks (INSIGHT-03) and week-over-week
movers (INSIGHT-06). Also dates every snapshot (streaks are measured in calendar days).

Pure (polars + stdlib). Upstream of the backtest firewall: never imports fgs.backtest or
fgs.evidence. The base-rate evidence line comes in as a dict (the committed
pipeline/callout_evidence.json, loaded and validated by fgs.export).

Callout (every type has exactly these keys):
  type      worried | hopeful | misery | joy | mover_up | mover_down
  season, week, franchise
  headline, detail, evidence (str | None)
  stat      worried/hopeful: signed gap (record_rank - score rank); movers: score_delta;
            misery/joy: streak length in days as of that week's date (the latest week: the
            export date, matching records.json active)
  start     ISO date the streak started (misery/joy only); None otherwise
  band      the team's hysteresis band that week
"""

import hashlib
import json
from collections.abc import Callable
from datetime import date

import polars as pl

from fgs import asof, season_config

GAP_TYPES = ("hopeful", "worried")
MINUS = "−"
ARROW = "→"


# --- copy -----------------------------------------------------------------------------------------

def record_text(wins: int, losses: int, ties: int) -> str:
    """Mirrors web/src/lib/format.ts formatRecord: ties only when there are any."""
    return f"{wins}-{losses}-{ties}" if ties > 0 else f"{wins}-{losses}"


def ordinal_best(n: int) -> str:
    if n == 1:
        return "best"
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}-best"


def evidence_text(flavor: str, ev: dict | None) -> str | None:
    if ev is None:
        return None
    e = ev[flavor]
    lo, hi = ev["train_seasons"]
    return (f"Teams with a gap this big won {round(100 * e['team_win'])}% of their next 8 games; "
            f"teams with the same record won {round(100 * e['peer_win'])}% ({e['n']} cases, {lo}–{hi}).")


def _callout(type_: str, r: dict, headline: str, detail: str, evidence: str | None, stat: int) -> dict:
    return {
        "type": type_, "season": int(r["season"]), "week": int(r["week"]), "franchise": r["franchise_id"],
        "headline": headline, "detail": detail, "evidence": evidence, "stat": int(stat), "start": None,
        "band": int(r["band"]),
    }


# --- weights fingerprint --------------------------------------------------------------------------

def fingerprint_weights(weights: dict[str, float], offseason: dict | None) -> dict[str, float]:
    """The mapping the evidence fingerprint covers: the in-season weights plus the Phase 7 offseason
    draft term (weight and display_only), so changing either invalidates callout_evidence.json."""
    out = {k: float(v) for k, v in weights.items()}
    if offseason is not None:
        out["offseason.draft"] = float(offseason["weight"])
        out["offseason.draft.display_only"] = float(bool(offseason["display_only"]))
    return out


def weights_fingerprint(weights: dict[str, float]) -> str:
    blob = json.dumps({k: round(float(v), 6) for k, v in sorted(weights.items())}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


# --- perception gap -------------------------------------------------------------------------------

def record_ranks(scored: pl.DataFrame, team_games: pl.DataFrame) -> pl.DataFrame:
    """scored + pd, wp, record_rank, gap (record_rank - rank). season/week cast to Int32.

    Record rank per (season, week): REG win% (ties half; 0-0-0 = .500) desc, cumulative REG point
    differential of played games with asof_week <= week desc, franchise asc."""
    pd_ = (
        team_games.filter(pl.col("is_reg") & pl.col("played"))
        .group_by("season", "asof_week", "franchise_id")
        .agg((pl.col("points_for") - pl.col("points_against")).sum().alias("_d"))
        .sort("franchise_id", "season", "asof_week")
        .with_columns(pl.col("_d").cum_sum().over("franchise_id", "season").alias("pd"))
        .select(pl.col("season").cast(pl.Int32), pl.col("asof_week").cast(pl.Int32).alias("week"),
                "franchise_id", pl.col("pd").cast(pl.Int64))
    )
    s = (
        scored.drop([c for c in ("pd", "wp", "record_rank", "gap") if c in scored.columns])
        .with_columns(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32))
        .sort("week")
        .join_asof(pd_.sort("week"), on="week", by=["season", "franchise_id"], strategy="backward",
                   check_sortedness=False)
        .with_columns(pl.col("pd").fill_null(0))
    )
    n = pl.col("wins") + pl.col("losses") + pl.col("ties")
    s = s.with_columns(wp=pl.when(n > 0).then((pl.col("wins") + 0.5 * pl.col("ties")) / n).otherwise(0.5))
    return (
        s.sort(["season", "week", "wp", "pd", "franchise_id"], descending=[False, False, True, True, False])
        .with_columns(pl.int_range(1, pl.len() + 1, dtype=pl.Int32).over("season", "week").alias("record_rank"))
        .with_columns((pl.col("record_rank").cast(pl.Int64) - pl.col("rank").cast(pl.Int64)).alias("gap"))
        .sort(["season", "week", "rank"])
    )


def gap_flags(ranked: pl.DataFrame) -> pl.DataFrame:
    """All flagged rows (uncapped; fgs.evidence pools these): GAP_FIRST_WEEK <= week <=
    reg_weeks(season) - 1 and |gap| >= GAP_THRESHOLD; flavor hopeful (score better than record,
    gap > 0) or worried (gap < 0)."""
    t, first = season_config.GAP_THRESHOLD, season_config.GAP_FIRST_WEEK
    rw = pl.col("season").map_elements(lambda s: season_config.reg_weeks(s), return_dtype=pl.Int64)
    return (
        ranked.filter((pl.col("week") >= first) & (pl.col("week") <= rw - 1) & (pl.col("gap").abs() >= t))
        .with_columns(pl.when(pl.col("gap") > 0).then(pl.lit("hopeful")).otherwise(pl.lit("worried")).alias("flavor"))
    )


def _gap_sorted(flags: pl.DataFrame) -> pl.DataFrame:
    return (
        flags.with_columns(pl.col("gap").abs().alias("_ag"))
        .sort(["season", "week", "_ag", "rank", "franchise_id"], descending=[False, False, True, False, False])
    )


def gap_callouts(ranked: pl.DataFrame, nicks: dict[str, str], evidence: dict | None) -> list[dict]:
    """At most GAP_CAP per (season, week, flavor), largest |gap| then smaller score rank; within a
    week both flavors interleave in that order."""
    cap = season_config.GAP_CAP
    kept = (
        _gap_sorted(gap_flags(ranked))
        .with_columns(pl.int_range(pl.len()).over("season", "week", "flavor").alias("_i"))
        .filter(pl.col("_i") < cap)
    )
    out = []
    for r in _gap_sorted(kept).iter_rows(named=True):
        flavor = r["flavor"]
        rec = record_text(int(r["wins"]), int(r["losses"]), int(r["ties"]))
        tail = "you should feel worried" if flavor == "worried" else "better days are coming"
        nick = nicks.get(r["franchise_id"], r["franchise_id"])
        detail = (f"The {nick} have the {ordinal_best(int(r['record_rank']))} record but the "
                  f"{ordinal_best(int(r['rank']))} score.")
        out.append(_callout(flavor, r, f"{rec}, but {tail}", detail, evidence_text(flavor, evidence), r["gap"]))
    return out


# --- movers ---------------------------------------------------------------------------------------

def movers(scored: pl.DataFrame, nicks: dict[str, str]) -> list[dict]:
    """Top MOVERS_N risers (mover_up) and fallers (mover_down) per (season, week >= 1) by score_delta,
    delta != 0; ties by |score_delta|, |rank_delta| desc, rank asc, franchise asc. Week 0 (the
    offseason "vs end of last season" delta) never produces movers."""
    n = season_config.MOVERS_N
    s = (
        scored.with_columns(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32))
        .sort("franchise_id", "season", "week")
        .with_columns(pl.col("label").shift(1).over("franchise_id", "season").alias("_prev_label"))
        .filter((pl.col("week") >= 1) & pl.col("score_delta").is_not_null() & (pl.col("score_delta") != 0))
        .with_columns(pl.col("score_delta").abs().alias("_ad"), pl.col("rank_delta").abs().fill_null(0).alias("_ard"))
    )
    out = []
    for type_, cond in (("mover_up", pl.col("score_delta") > 0), ("mover_down", pl.col("score_delta") < 0)):
        top = (
            s.filter(cond)
            .sort(["season", "week", "_ad", "_ard", "rank", "franchise_id"],
                  descending=[False, False, True, True, False, False])
            .with_columns(pl.int_range(pl.len()).over("season", "week").alias("_i"))
            .filter(pl.col("_i") < n)
        )
        for r in top.iter_rows(named=True):
            d = int(r["score_delta"])
            nick = nicks.get(r["franchise_id"], r["franchise_id"])
            headline = f"{nick} +{d}" if d > 0 else f"{nick} {MINUS}{-d}"
            prev = r["_prev_label"]
            detail = f"{prev} {ARROW} {r['label']}" if prev is not None and prev != r["label"] else f"Still {r['label']}"
            out.append(_callout(type_, r, headline, detail, None, d))
    return out


# --- snapshot dates and streaks (INSIGHT-03) -------------------------------------------------------

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
STREAK_KINDS = ("misery", "joy")


def date_text(d: date) -> str:
    """'Sep 11, 2005' without any locale dependency."""
    return f"{_MONTHS[d.month - 1]} {d.day}, {d.year}"


def snapshot_dates(games: pl.DataFrame, as_of: date) -> pl.DataFrame:
    """(season, week, date) for every snapshot: week >= 1 = the last gameday of the played games
    with that asof_week; week 0 = season_config.draft_date(season, as_of) (post-draft)."""
    wk = pl.col("asof_week") if "asof_week" in games.columns else pl.col("week")
    played = (
        games.filter(pl.col("played"))
        .group_by(pl.col("season").cast(pl.Int32), wk.cast(pl.Int32).alias("week"))
        .agg(pl.col("gameday").max().str.to_date().alias("date"))
    )
    seasons = sorted(int(x) for x in games["season"].unique().to_list())
    w0 = pl.DataFrame(
        {"season": seasons, "week": [0] * len(seasons),
         "date": [season_config.draft_date(x, as_of) for x in seasons]},
        schema={"season": pl.Int32, "week": pl.Int32, "date": pl.Date},
    )
    return pl.concat([w0, played.select("season", "week", "date")]).sort("season", "week")


def timelines(scored: pl.DataFrame, dates: pl.DataFrame) -> pl.DataFrame:
    """Per-franchise dated score rows (franchise_id, season, week, date, score), sorted by date.
    The week-0 rows of seeded expansion team-seasons (season_config.SEEDS) are dropped: they
    reflect an assumed 1300 seed, not a result. Raises ValueError if a snapshot has no date."""
    seeds = list(season_config.SEEDS)
    is_seed_w0 = pl.lit(False)
    for f, se in seeds:
        is_seed_w0 = is_seed_w0 | ((pl.col("franchise_id") == f) & (pl.col("season") == se) & (pl.col("week") == 0))
    t = (
        scored.select(pl.col("franchise_id"), pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32),
                      pl.col("score").cast(pl.Int64))
        .join(dates, on=["season", "week"], how="left")
    )
    missing = t.filter(pl.col("date").is_null())
    if missing.height:
        raise ValueError(f"{missing.height} snapshots have no date, e.g. {missing.row(0, named=True)}")
    return (
        t.filter(~is_seed_w0)
        .sort("franchise_id", "date", "season", "week")
        .select("franchise_id", "season", "week", "date", "score")
    )


def runs(dates: list[date], scores: list[int], cond: Callable[[int], bool], as_of: date) -> list[dict]:
    """Maximal runs of consecutive rows meeting cond. start = first row's date; end = the date of the
    first row that breaks it (None if the run reaches the last row: active); days = (end or as_of)
    - start. i/j are the first/last row indexes inside the run."""
    ok = [bool(cond(x)) for x in scores]
    out, i, n = [], 0, len(dates)
    while i < n:
        if not ok[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and ok[j + 1]:
            j += 1
        end = dates[j + 1] if j + 1 < n else None
        out.append({"start": dates[i], "end": end, "active": end is None,
                    "days": ((end or as_of) - dates[i]).days, "i": i, "j": j})
        i = j + 1
    return out


def streak_cond(kind: str) -> Callable[[int], bool]:
    if kind == "misery":
        return lambda x: x <= season_config.MISERY_MAX
    if kind == "joy":
        return lambda x: x >= season_config.JOY_MIN
    raise ValueError(kind)


_RUN_SCHEMA = {
    "franchise_id": pl.String, "kind": pl.String, "start": pl.Date, "end": pl.Date, "days": pl.Int64,
    "active": pl.Boolean, "start_season": pl.Int32, "start_week": pl.Int32, "end_season": pl.Int32,
    "end_week": pl.Int32,
}


def all_runs(tl: pl.DataFrame, as_of: date) -> pl.DataFrame:
    """Every misery and joy run of every franchise (seasons are not boundaries). end_season/end_week
    are the last snapshot inside the run."""
    rows = []
    for (fid,), part in tl.sort("franchise_id", "date").group_by(["franchise_id"], maintain_order=True):
        d, sc = part["date"].to_list(), part["score"].to_list()
        se, wk = part["season"].to_list(), part["week"].to_list()
        for kind in STREAK_KINDS:
            for r in runs(d, sc, streak_cond(kind), as_of):
                i, j = r["i"], r["j"]
                rows.append({"franchise_id": fid, "kind": kind, "start": r["start"], "end": r["end"],
                             "days": r["days"], "active": r["active"], "start_season": se[i], "start_week": wk[i],
                             "end_season": se[j], "end_week": wk[j]})
    return pl.DataFrame(rows, schema=_RUN_SCHEMA)


def streak_callouts(
    run_df: pl.DataFrame, dates: pl.DataFrame, nicks: dict[str, str], bands: dict[tuple[int, int, str], int],
    *, latest: tuple[int, int] | None = None, as_of: date | None = None,
) -> list[dict]:
    """Per (season, week) with date d: the longest misery run and the longest joy run that are
    ongoing at d (start <= d and (end is None or end > d)) and at least STREAK_CALLOUT_MIN_DAYS
    old at the reference date. At most one per kind per week; ties: earlier start, then franchise.
    bands maps (season, week, franchise) -> the team's band that week. Copy never names the mood
    label (hysteresis can disagree with the raw threshold, RESEARCH Pitfall 7).

    Reference date (WR-01): days count through d, except for the `latest` (season, week), which
    counts through as_of (the export date), the same date records.json `active` uses, so the
    latest board card and the team page's streak line always show the same number. The detail
    names the reference date ("as of ...")."""
    floor = season_config.STREAK_CALLOUT_MIN_DAYS
    by_kind = {k: run_df.filter(pl.col("kind") == k).sort("start", "franchise_id").to_dicts() for k in STREAK_KINDS}
    out = []
    for season, week, d in dates.sort("season", "week").iter_rows():
        ref = max(as_of, d) if as_of is not None and (int(season), int(week)) == latest else d
        for kind in STREAK_KINDS:
            best = None
            for r in by_kind[kind]:
                if r["start"] > d:
                    break
                if r["end"] is not None and r["end"] <= d:
                    continue
                days = (ref - r["start"]).days
                if days >= floor and (best is None or days > best[0]):
                    best = (days, r)
            if best is None:
                continue
            days, r = best
            fid = r["franchise_id"]
            band = bands.get((int(season), int(week), fid))
            if band is None:
                continue  # no snapshot row for this team that week (cannot happen on the full grid)
            nick = nicks.get(fid, fid)
            if kind == "misery":
                headline = f"{nick} fans have been miserable for {days:,} straight days"
                detail = (f"Score under {season_config.MISERY_MAX + 1} since {date_text(r['start'])}, "
                          f"as of {date_text(ref)}.")
            else:
                headline = f"{nick} fans have been buying the jersey for {days:,} straight days"
                detail = (f"Score {season_config.JOY_MIN} or higher since {date_text(r['start'])}, "
                          f"as of {date_text(ref)}.")
            out.append({
                "type": kind, "season": int(season), "week": int(week), "franchise": fid,
                "headline": headline, "detail": detail, "evidence": None, "stat": int(days),
                "start": r["start"].isoformat(), "band": int(band),
            })
    return out


# --- assembly -------------------------------------------------------------------------------------

def callouts_by_week(
    scored: pl.DataFrame, team_games: pl.DataFrame, nicks: dict[str, str], evidence: dict | None,
    *, games: pl.DataFrame | None = None, as_of: date | None = None, latest: tuple[int, int] | None = None,
) -> dict[tuple[int, int], list[dict]]:
    """(season, week) -> gap callouts (by |gap|), then misery, joy, then mover_up, then mover_down.
    The single assembly point for every callout type. Streaks need games and as_of (to date the
    snapshots); without them only gaps and movers are produced. latest = the (season, week) whose
    streak days count through as_of (default: the latest played week of games)."""
    by: dict[tuple[int, int], list[dict]] = {}
    gaps = gap_callouts(record_ranks(scored, team_games), nicks, evidence)
    streaks: list[dict] = []
    if games is not None and as_of is not None:
        dates = snapshot_dates(games, as_of)
        bands = {(int(a), int(b), c): int(d) for a, b, c, d in
                 scored.select("season", "week", "franchise_id", "band").iter_rows()}
        if latest is None:
            latest = asof.latest_played(games)
        streaks = streak_callouts(all_runs(timelines(scored, dates), as_of), dates, nicks, bands,
                                  latest=latest, as_of=as_of)
    mv = movers(scored, nicks)
    for c in gaps + streaks + [m for m in mv if m["type"] == "mover_up"] + [m for m in mv if m["type"] == "mover_down"]:
        by.setdefault((c["season"], c["week"]), []).append(c)
    return by

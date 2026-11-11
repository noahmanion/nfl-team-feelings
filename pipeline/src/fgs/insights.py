"""Phase 8 callouts: perception gaps (INSIGHT-02) and week-over-week movers (INSIGHT-06).

Pure (polars + stdlib). Upstream of the backtest firewall: never imports fgs.backtest or
fgs.evidence. The base-rate evidence line comes in as a dict (the committed
pipeline/callout_evidence.json, loaded and validated by fgs.export).

Callout (every type has exactly these keys):
  type      worried | hopeful | mover_up | mover_down   (plan 08-03 adds misery | joy)
  season, week, franchise
  headline, detail, evidence (str | None)
  stat      worried/hopeful: signed gap (record_rank - score rank); movers: score_delta
  start     ISO date for streak types only; None here
  band      the team's hysteresis band that week
"""

import hashlib
import json

import polars as pl

from fgs import season_config

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


# --- assembly -------------------------------------------------------------------------------------

def callouts_by_week(
    scored: pl.DataFrame, team_games: pl.DataFrame, nicks: dict[str, str], evidence: dict | None,
) -> dict[tuple[int, int], list[dict]]:
    """(season, week) -> gap callouts (by |gap|), then mover_up, then mover_down. The single assembly
    point for every callout type (plan 08-03 adds streaks here)."""
    by: dict[tuple[int, int], list[dict]] = {}
    gaps = gap_callouts(record_ranks(scored, team_games), nicks, evidence)
    mv = movers(scored, nicks)
    for c in gaps + [m for m in mv if m["type"] == "mover_up"] + [m for m in mv if m["type"] == "mover_down"]:
        by.setdefault((c["season"], c["week"]), []).append(c)
    return by

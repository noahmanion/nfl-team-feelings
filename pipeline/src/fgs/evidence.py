"""DEV-ONLY: base rates behind the perception-gap callouts (INSIGHT-02).

Run by hand with `uv run fgs evidence`, which writes pipeline/callout_evidence.json; commit that
file. The export only reads the JSON (and refuses stale numbers); it never imports this module,
because this module imports fgs.backtest (downstream side of the firewall, test_leakage).

Only seasons <= season_config.TRAIN_LAST_SEASON (1999-2021) are used: both frames are filtered
before anything else runs, so the sealed 2022+ seasons can never move the numbers.

In-sample caveat: 1999-2021 is also the window the score weights were fit on, so these base rates
describe history; they are not an out-of-sample test.

Per flavor (hopeful: score rank >= GAP_THRESHOLD better than record rank; worried: the reverse),
pooled over every flagged team-week in REG weeks GAP_FIRST_WEEK..reg_weeks-1 (uncapped):
  n         cases with a defined next-8 target and at least one peer
  d_margin  mean(case y8 - peer mean y8), y8 = backtest.targets next-8 adjusted margin
  team_win  mean next-8 win% of the cases (ties half, playoffs included, same season)
  peer_win  mean of the peers' next-8 win%
Peers: every 1999-2021 team-week with the same week and the same W-L-T, leave-one-out.
"""

import numpy as np
import polars as pl

from fgs import insights, season_config
from fgs.backtest import targets

KEYS = ["season", "week", "franchise_id"]
NOTE = "In-sample: 1999-2021 is also the weight-fit window; describes history, not an out-of-sample test."


def next_n_win(team_games: pl.DataFrame, snaps: pl.DataFrame, n: int = 8) -> pl.DataFrame:
    """Per snapshot: win{n} = mean outcome over the next min(n, remaining) same-season played games
    with asof_week > week (ties 0.5, playoffs included); null when fewer than 2 remain. Same game
    order and index arithmetic as backtest.targets, so the null pattern matches y{n}."""
    g = (
        team_games.filter(pl.col("played"))
        .select(pl.col("season").cast(pl.Int32), pl.col("asof_week").cast(pl.Int32), "franchise_id", "game_id",
                pl.col("outcome").cast(pl.Float64))
        .sort("franchise_id", "season", "asof_week", "game_id")
        .with_row_index("gidx")
    )
    C = np.concatenate([[0.0], np.cumsum(g["outcome"].to_numpy())])
    team_season = g.group_by("franchise_id", "season").agg(pl.col("gidx").min().alias("off"), pl.len().alias("ntot"))
    done = (
        g.group_by("franchise_id", "season", "asof_week").agg(pl.len().alias("c"))
        .sort("franchise_id", "season", "asof_week")
        .with_columns(pl.col("c").cum_sum().over("franchise_id", "season").alias("k"))
        .select("franchise_id", "season", pl.col("asof_week").alias("week"), "k")
    )
    s = (
        snaps.select(KEYS).with_columns(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32))
        .sort("week")
        .join_asof(done.sort("week"), on="week", by=["franchise_id", "season"], strategy="backward",
                   check_sortedness=False)
        .join(team_season, on=["franchise_id", "season"], how="left")
        .with_columns(pl.col("k").fill_null(0), pl.col("ntot").fill_null(0), pl.col("off").fill_null(0))
    )
    k = s["k"].to_numpy().astype(np.int64)
    ntot = s["ntot"].to_numpy().astype(np.int64)
    off = s["off"].to_numpy().astype(np.int64)
    m = np.minimum(n, ntot - k)
    ok = m >= 2
    start = off + k
    end = start + np.where(ok, m, 0)
    val = np.full(len(s), np.nan)
    val[ok] = (C[end[ok]] - C[start[ok]]) / m[ok]
    return s.select(KEYS).with_columns(pl.Series(f"win{n}", val, dtype=pl.Float64).fill_nan(None)).sort(KEYS)


def peer_stats(cases: pl.DataFrame) -> dict:
    """cases: week, wins, losses, ties, y8, win8, flavor (null for non-cases). Leave-one-out peer
    means over rows with a defined y8 in the same (week, W, L, T) group."""
    grp = ["week", "wins", "losses", "ties"]
    d = cases.filter(pl.col("y8").is_not_null()).with_columns(
        pl.col("y8").sum().over(grp).alias("_sy"),
        pl.col("win8").sum().over(grp).alias("_sw"),
        pl.len().over(grp).alias("_n"),
    )
    d = d.filter(pl.col("flavor").is_not_null() & (pl.col("_n") >= 2)).with_columns(
        ((pl.col("_sy") - pl.col("y8")) / (pl.col("_n") - 1)).alias("_py"),
        ((pl.col("_sw") - pl.col("win8")) / (pl.col("_n") - 1)).alias("_pw"),
    )
    out = {}
    for flavor in insights.GAP_TYPES:
        x = d.filter(pl.col("flavor") == flavor)
        if x.is_empty():
            out[flavor] = {"n": 0, "d_margin": None, "team_win": None, "peer_win": None}
            continue
        out[flavor] = {
            "n": x.height,
            "d_margin": round(float((x["y8"] - x["_py"]).mean()), 2) + 0.0,
            "team_win": round(float(x["win8"].mean()), 4),
            "peer_win": round(float(x["_pw"].mean()), 4),
        }
    return out


def compute_evidence(
    scored: pl.DataFrame, team_games: pl.DataFrame, fingerprint: str | dict[str, str], generated_at: str,
) -> dict:
    """fingerprint: fgs.fingerprint.evidence_fingerprints(...) (every staleness key the export checks),
    or just the weights fingerprint string."""
    fps = {"weights_fingerprint": fingerprint} if isinstance(fingerprint, str) else dict(fingerprint)
    last = season_config.TRAIN_LAST_SEASON  # read at call time
    # SEAL: drop every season after the training window before anything else runs.
    scored = scored.filter(pl.col("season") <= last)
    team_games = team_games.filter(pl.col("season") <= last)

    ranked = insights.record_ranks(scored, team_games)
    flags = insights.gap_flags(ranked).select(KEYS + ["flavor"])
    snaps = ranked.select(KEYS)
    frame = (
        ranked.select(KEYS + ["wins", "losses", "ties"])
        .join(targets(team_games, snaps, ns=(8,)), on=KEYS, how="left", validate="1:1")
        .join(next_n_win(team_games, snaps, n=8), on=KEYS, how="left", validate="1:1")
        .join(flags, on=KEYS, how="left", validate="1:1")
    )
    stats = peer_stats(frame)
    first = int(scored["season"].min())
    return {
        "threshold": season_config.GAP_THRESHOLD,
        "first_week": season_config.GAP_FIRST_WEEK,
        "train_seasons": [first, last],
        **fps,
        "generated_at": generated_at,
        "note": NOTE,
        "hopeful": stats["hopeful"],
        "worried": stats["worried"],
    }

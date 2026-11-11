"""Backtest harness: the locked target, metrics, and walk-forward baselines.

DEV-ONLY. This module looks at *future* games (the target is the next N games), so it must
never be imported by features.py or score.py. That one-way dependency is the leakage firewall:
backtest -> features is fine, features/score -> backtest is not.

Target (README "Backtest target"): mean adjusted margin over a team's next N games in the
same season (REG + playoffs). Adjusted margin = margin + (opp_elo_pre - 1505)/25 - hfa_signed/25.
Only opponent strength and venue are adjusted for, never the team's own rating.
"""

import numpy as np
import polars as pl

from fgs import draft
from fgs.features import build_features
from fgs.score import composite as score_composite
from fgs.score import zscore
from fgs.season_config import (
    FIRST_TEST_SEASON, HOLDOUT_SEASONS, MEAN_ELO, REF_SEASONS, TRAIN_LAST_SEASON, hfa_for,
)

KEYS = ["season", "week", "franchise_id"]


def _hfa_table(seasons) -> pl.DataFrame:
    seasons = sorted({int(s) for s in seasons})
    return pl.DataFrame(
        {"season": seasons, "hfa": [hfa_for(s) for s in seasons]},
        schema={"season": pl.Int32, "hfa": pl.Float64},
    )


def adjusted_margins(team_games: pl.DataFrame) -> pl.DataFrame:
    """One row per played team-game with its opponent- and venue-adjusted margin (`adj`)."""
    played = team_games.filter(pl.col("played")).with_columns(pl.col("season").cast(pl.Int32))
    opp = played.select(
        "game_id", pl.col("franchise_id").alias("opponent_id"), pl.col("elo_pre").alias("opp_elo_pre")
    )
    return (
        played.join(opp, on=["game_id", "opponent_id"], how="left")
        .join(_hfa_table(played["season"].unique().to_list()), on="season", how="left")
        .with_columns(
            (pl.col("points_for") - pl.col("points_against")).cast(pl.Float64).alias("margin"),
            pl.when(pl.col("neutral")).then(0.0)
            .when(pl.col("is_home")).then(pl.col("hfa"))
            .otherwise(-pl.col("hfa")).alias("hfa_s"),
        )
        .with_columns(
            # margin - expected margin of a league-average (1505) team vs this opponent at this venue
            (pl.col("margin") - (MEAN_ELO - pl.col("opp_elo_pre") + pl.col("hfa_s")) / 25).alias("adj")
        )
        .select(
            "season", pl.col("asof_week").cast(pl.Int32), "franchise_id", "game_id",
            "margin", "opp_elo_pre", "hfa_s", "adj",
        )
        .sort("franchise_id", "season", "asof_week", "game_id")
    )


def targets(team_games: pl.DataFrame, snapshots: pl.DataFrame, ns=(4, 8)) -> pl.DataFrame:
    """Per snapshot (season, week, franchise): y{N} = mean adj over the next min(N, remaining)
    same-season games with asof_week > week; null when fewer than 2 remain."""
    am = adjusted_margins(team_games).with_row_index("gidx")
    # Global cumulative sum with a leading 0: sum of rows [a, b) = C[b] - C[a].
    C = np.concatenate([[0.0], np.cumsum(am["adj"].to_numpy())])

    team_season = am.group_by("franchise_id", "season").agg(
        pl.col("gidx").min().alias("off"), pl.len().alias("ntot")
    )
    # Number of games played with asof_week <= w, per (team, season, w) where it changes.
    done = (
        am.group_by("franchise_id", "season", "asof_week")
        .agg(pl.len().alias("c"))
        .sort("franchise_id", "season", "asof_week")
        .with_columns(pl.col("c").cum_sum().over("franchise_id", "season").alias("k"))
        .select("franchise_id", "season", pl.col("asof_week").alias("week"), "k")
    )
    s = (
        snapshots.select(KEYS)
        .with_columns(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32))
        .sort("week")
        .join_asof(done.sort("week"), on="week", by=["franchise_id", "season"], strategy="backward",
                   check_sortedness=False)
        .join(team_season, on=["franchise_id", "season"], how="left")
        .with_columns(pl.col("k").fill_null(0), pl.col("ntot").fill_null(0), pl.col("off").fill_null(0))
    )
    k = s["k"].to_numpy().astype(np.int64)
    ntot = s["ntot"].to_numpy().astype(np.int64)
    off = s["off"].to_numpy().astype(np.int64)
    cols = []
    for n in ns:
        m = np.minimum(n, ntot - k)
        ok = m >= 2
        start = off + k
        end = start + np.where(ok, m, 0)
        val = np.full(len(s), np.nan)
        val[ok] = (C[end[ok]] - C[start[ok]]) / m[ok]
        cols.append(pl.Series(f"y{n}", val, dtype=pl.Float64).fill_nan(None))
    return s.select(KEYS).with_columns(cols).sort(KEYS)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

BUCKETS = ("wk0", "early", "mid", "late")
NS = (4, 8)
# candidate name -> feature column (Spearman/R² + next-game Brier)
CANDIDATES = {"elo": "elo", "season_wpct": "season_record", "last16": "last16", "pd_pg": "pd_pg"}
TARGET_TEXT = (
    "mean adjusted margin over the team's next N same-season games (REG + playoffs); "
    "adj = margin + (opp_elo_pre - 1505)/25 - hfa_signed/25; snapshots with < 2 games left skipped"
)


def _defined(x, y) -> bool:
    return len(x) >= 3 and float(np.std(x)) > 1e-12 and float(np.std(y)) > 1e-12


def spearman(x, y) -> float | None:
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if not _defined(x, y):
        return None
    rx = pl.Series(x).rank("average").to_numpy()
    ry = pl.Series(y).rank("average").to_numpy()
    return float(np.corrcoef(rx, ry)[0, 1])


def r2(x, y) -> float | None:
    """Squared Pearson (== R² of a one-predictor OLS fit)."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if not _defined(x, y):
        return None
    return float(np.corrcoef(x, y)[0, 1] ** 2)


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def logit_fit(X, y, iters: int = 25) -> np.ndarray:
    """Logistic regression by Newton/IRLS. Returns coefficients with the intercept last."""
    X = np.column_stack([np.asarray(X, dtype=float).reshape(len(y), -1), np.ones(len(y))])
    y = np.asarray(y, dtype=float)
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = _sigmoid(X @ b)
        H = X.T @ (X * (p * (1 - p))[:, None]) + 1e-9 * np.eye(X.shape[1])
        b = b + np.linalg.solve(H, X.T @ (y - p))
    return b


def logit_predict(b: np.ndarray, X) -> np.ndarray:
    X = np.asarray(X, dtype=float)
    X = X.reshape(X.shape[0], -1) if X.ndim > 1 else X[:, None]
    return _sigmoid(X @ b[:-1] + b[-1])


def brier(p, y) -> float:
    return float(np.mean((np.asarray(p, dtype=float) - np.asarray(y, dtype=float)) ** 2))


def bucket_expr(week: pl.Expr = pl.col("week")) -> pl.Expr:
    return (
        pl.when(week == 0).then(pl.lit("wk0"))
        .when(week <= 6).then(pl.lit("early"))
        .when(week <= 12).then(pl.lit("mid"))
        .otherwise(pl.lit("late"))
    )


def test_seasons(include_holdout: bool = False) -> list[int]:
    last = HOLDOUT_SEASONS[1] if include_holdout else TRAIN_LAST_SEASON
    return list(range(FIRST_TEST_SEASON, last + 1))


test_seasons.__test__ = False  # not a pytest test despite the name


def next_game_frame(games: pl.DataFrame, feats: pl.DataFrame, cols) -> pl.DataFrame:
    """One row per played, non-tie game with each team's candidate values as of the week before
    the result became known (snapshot week = asof_week - 1)."""
    cols = list(dict.fromkeys(cols))
    snap = feats.select("season", "week", "franchise_id", *cols)
    g = (
        games.filter(pl.col("played") & pl.col("result").is_not_null() & (pl.col("result") != 0))
        .with_columns(
            pl.col("season").cast(pl.Int32),
            (pl.col("asof_week").cast(pl.Int32) - 1).alias("prev_week"),
            (pl.col("result") > 0).cast(pl.Float64).alias("y"),
            pl.when(pl.col("neutral")).then(0.0).otherwise(1.0).alias("home_ind"),
            pl.col("spread_line").cast(pl.Float64) if "spread_line" in games.columns
            else pl.lit(None, dtype=pl.Float64).alias("spread_line"),
        )
    )
    for side, team in (("h", "home_id"), ("a", "away_id")):
        g = g.join(
            snap.rename({c: f"{side}_{c}" for c in cols}),
            left_on=["season", "prev_week", team], right_on=["season", "week", "franchise_id"], how="left",
        )
    hfa = _hfa_table(g["season"].unique().to_list())
    g = g.join(hfa, on="season", how="left").with_columns((pl.col("hfa") * pl.col("home_ind")).alias("hfa_s"))
    keep = ["game_id", "season", "asof_week", "home_id", "away_id", "y", "home_ind", "hfa_s", "spread_line"]
    keep += [f"{s}_{c}" for c in cols for s in ("h", "a")]
    return g.select(keep).drop_nulls([f"{s}_{c}" for c in cols for s in ("h", "a")]).sort("season", "game_id")


def _walk_forward_brier(ng: pl.DataFrame, seasons: list[int], xfn, return_p: bool = False):
    """Per test season S: logistic fit on rows with season < S, scored on season S.
    Returns (brier, n); with return_p=True also the per-row probability aligned to ng (NaN
    outside the scored test seasons)."""
    ps, ys = [], []
    p_all = np.full(ng.height, np.nan)
    sea = ng["season"].to_numpy()
    for S in seasons:
        tr, te = ng.filter(pl.col("season") < S), ng.filter(pl.col("season") == S)
        if tr.is_empty() or te.is_empty():
            continue
        b = logit_fit(xfn(tr), tr["y"].to_numpy())
        p = logit_predict(b, xfn(te))
        p_all[sea == S] = p  # ng is sorted by (season, game_id): filter order == mask order
        ps.append(p)
        ys.append(te["y"].to_numpy())
    if not ps:
        return (None, 0, p_all) if return_p else (None, 0)
    p, y = np.concatenate(ps), np.concatenate(ys)
    return (brier(p, y), int(len(y)), p_all) if return_p else (brier(p, y), int(len(y)))


def _corr_block(x, y) -> dict:
    return {"spearman": spearman(x, y), "r2": r2(x, y), "n": int(len(y))}


def _round(v):
    return None if v is None else round(float(v), 6)


# ---------------------------------------------------------------------------
# Ridge (closed form, standardized inputs, unpenalized intercept)
# ---------------------------------------------------------------------------

ALPHA_GRID = (0.0, 1e-3, 1e-2, 1e-1, 1.0)  # multiplied by n_train inside ridge_fit
# candidate name -> factor set; inputs are the same per-snapshot z columns the score uses
RIDGE_SETS = {
    "ridge:elo": ["elo"],
    "ridge:+season_record": ["elo", "season_record"],
    "ridge:+last16": ["elo", "season_record", "last16"],
    "ridge:+mov": ["elo", "season_record", "last16", "mov"],
    "ridge:+sow": ["elo", "season_record", "last16", "mov", "sow"],
    "ridge:+streak": ["elo", "season_record", "last16", "mov", "sow", "streak"],
    "ridge:+luck": ["elo", "season_record", "last16", "mov", "sow", "streak", "luck"],
    "ridge:+epa_traj": ["elo", "season_record", "last16", "mov", "sow", "streak", "luck", "epa_traj"],
    "ridge:+qb_trend": ["elo", "season_record", "last16", "mov", "sow", "streak", "luck", "epa_traj", "qb_trend"],
    "ridge:+vs_exp": ["elo", "season_record", "last16", "mov", "sow", "streak", "luck", "epa_traj", "qb_trend",
                      "vs_exp"],
    "ridge:+po_trend": ["elo", "season_record", "last16", "mov", "sow", "streak", "luck", "epa_traj", "qb_trend",
                        "vs_exp", "po_trend"],
}
PROPOSAL_FACTORS = RIDGE_SETS[list(RIDGE_SETS)[-1]]
FIT_TARGET = "y8"


def ridge_fit(X, y, alpha: float) -> tuple[np.ndarray, float]:
    """Solve (Xc'Xc + alpha*n*I) w = Xc'yc on centered data; intercept = ybar - xbar.w."""
    X = np.asarray(X, dtype=float).reshape(len(y), -1)
    y = np.asarray(y, dtype=float)
    xm, ym = X.mean(0), y.mean()
    Xc, yc = X - xm, y - ym
    w = np.linalg.solve(Xc.T @ Xc + alpha * len(y) * np.eye(X.shape[1]), Xc.T @ yc)
    return w, float(ym - xm @ w)


def ridge_predict(w: np.ndarray, b: float, X) -> np.ndarray:
    X = np.asarray(X, dtype=float)
    return X.reshape(X.shape[0], -1) @ w + b


def choose_alpha(X, y, seasons, grid=ALPHA_GRID) -> float:
    """Leave-one-season-out CV inside the given training rows; minimizes pooled squared error."""
    X = np.asarray(X, dtype=float).reshape(len(y), -1)
    y = np.asarray(y, dtype=float)
    seasons = np.asarray(seasons)
    uniq = np.unique(seasons)
    if len(uniq) < 2:
        return float(grid[0])
    best, best_sse = float(grid[0]), np.inf
    for a in grid:
        sse = 0.0
        for s in uniq:
            te = seasons == s
            w, b = ridge_fit(X[~te], y[~te], a)
            sse += float(np.sum((y[te] - ridge_predict(w, b, X[te])) ** 2))
        if sse < best_sse - 1e-12:
            best, best_sse = float(a), sse
    return best


def _sealed_pbp(derived: dict, last: int) -> pl.DataFrame | None:
    tge = derived.get("team_game_epa")
    return None if tge is None else tge.filter(pl.col("season") <= last)


def _sealed_sim(derived: dict, last: int) -> tuple[pl.DataFrame | None, pl.DataFrame | None]:
    """(sim, vegas) restricted to seasons <= last. Each sim season only depends on its own
    as-of inputs; Vegas lines are preseason; both are filtered anyway so nothing later leaks."""
    sim, vegas = derived.get("sim"), derived.get("vegas")
    sim = None if sim is None else sim.filter(pl.col("season") <= last)
    vegas = None if vegas is None else vegas.filter(pl.col("season") <= last)
    return sim, vegas


def _z_frame(
    snaps: pl.DataFrame, team_games: pl.DataFrame, pbp_games: pl.DataFrame | None = None,
    sim: pl.DataFrame | None = None, vegas: pl.DataFrame | None = None,
) -> pl.DataFrame:
    feats = build_features(snaps, team_games, pbp_games=pbp_games, sim=sim, vegas=vegas)
    return zscore(feats, PROPOSAL_FACTORS)


def propose_weights(derived: dict) -> dict:
    """Ridge weights for weights.yaml, fit on seasons <= TRAIN_LAST_SEASON only (N=8 target).
    Everything later is dropped before features, targets or fits are computed."""
    lo, hi = REF_SEASONS[0], TRAIN_LAST_SEASON
    snaps = derived["snapshots"].filter(pl.col("season") <= hi)
    team_games = derived["team_games"].filter(pl.col("season") <= hi)
    pbp_games = _sealed_pbp(derived, hi)
    d = (
        _z_frame(snaps, team_games, pbp_games, *_sealed_sim(derived, hi))
        .join(targets(team_games, snaps, (8,)), on=KEYS, how="left")
        .filter(pl.col("season").is_between(lo, hi) & pl.col(FIT_TARGET).is_not_null())
    )
    X = d.select([f"z_{f}" for f in PROPOSAL_FACTORS]).to_numpy()
    y = d[FIT_TARGET].to_numpy()
    alpha = choose_alpha(X, y, d["season"].to_numpy())
    w, b = ridge_fit(X, y, alpha)
    return {
        "weights": {f: float(v) for f, v in zip(PROPOSAL_FACTORS, w)},
        "intercept": b,
        "alpha": alpha,
        "n": int(len(y)),
        "seasons": [lo, hi],
        "target": FIT_TARGET,
    }


def format_proposal(prop: dict, date: str) -> str:
    """Ready-to-paste weights.yaml block (2-decimal weights)."""
    lo, hi = prop["seasons"]
    lines = [
        f"# proposed {date} by `uv run fgs backtest --propose-weights`: ridge on z-scores, "
        f"seasons {lo}-{hi}, target N=8 adjusted margin, alpha={prop['alpha']:g}*n, n={prop['n']}",
        "weights:",
    ]
    lines += [f"  {f}: {round(v, 2):.2f}" for f, v in prop["weights"].items()]
    return "\n".join(lines)


def _ridge_walk_forward(df: pl.DataFrame, ng: pl.DataFrame, seasons: list[int], factors: list[str]) -> dict:
    """Per test season S: alpha by LOSO CV and ridge fit on rows with season < S and y8 present,
    predict season S. Brier: logistic on (pred_h - pred_a, home_ind) fit on next-game rows < S
    scored with the same fold's ridge.

    Returns {"pred": per df row (NaN outside test seasons), "brier", "brier_n",
    "last_fold", "folds": every fold's {"season", "alpha", "intercept", "weights"},
    "game_p": per ng row win probability (NaN outside test seasons)}."""
    zc = [f"z_{f}" for f in factors]
    X = df.select(zc).to_numpy()
    y = df[FIT_TARGET].to_numpy().astype(float)
    sea = df["season"].to_numpy()
    has_y = ~np.isnan(y)
    Xh = ng.select([f"h_{c}" for c in zc]).to_numpy()
    Xa = ng.select([f"a_{c}" for c in zc]).to_numpy()
    ng_sea = ng["season"].to_numpy()
    home = ng["home_ind"].to_numpy()
    ng_y = ng["y"].to_numpy()

    pred = np.full(len(df), np.nan)
    game_p = np.full(ng.height, np.nan)
    ps, ys, folds = [], [], []
    for S in seasons:
        tr = has_y & (sea < S)
        te = sea == S
        if not tr.any() or not te.any():
            continue
        alpha = choose_alpha(X[tr], y[tr], sea[tr])
        w, b = ridge_fit(X[tr], y[tr], alpha)
        pred[te] = ridge_predict(w, b, X[te])
        folds.append({"season": S, "alpha": alpha, "intercept": b, "weights": dict(zip(factors, w.tolist()))})

        diff = ridge_predict(w, b, Xh) - ridge_predict(w, b, Xa)
        gtr, gte = ng_sea < S, ng_sea == S
        if gtr.any() and gte.any():
            lb = logit_fit(np.column_stack([diff[gtr], home[gtr]]), ng_y[gtr])
            p = logit_predict(lb, np.column_stack([diff[gte], home[gte]]))
            game_p[gte] = p
            ps.append(p)
            ys.append(ng_y[gte])
    out = {"pred": pred, "brier": None, "brier_n": 0, "last_fold": folds[-1] if folds else None,
           "folds": folds, "game_p": game_p}
    if ps:
        p, yy = np.concatenate(ps), np.concatenate(ys)
        out["brier"], out["brier_n"] = brier(p, yy), int(len(yy))
    return out


# ---------------------------------------------------------------------------
# Walk-forward backtest
# ---------------------------------------------------------------------------

def _p538(t: pl.DataFrame) -> np.ndarray:
    return 1.0 / (1.0 + 10 ** (-(t["h_elo"] - t["a_elo"] + t["hfa_s"]).to_numpy() / 400))


def walk_forward_frame(derived: dict, include_holdout: bool = False) -> dict:
    """The walk-forward core shared by run_backtest and the Phase 6 freeze evidence.

    Seasons past the last test season (2021 by default) are dropped before any feature, target,
    metric or fit, so the holdout stays sealed. Returns:
      "seasons": test seasons
      "rows":   test-season snapshot rows: KEYS, bucket, y4, y8, the CANDIDATES columns, one
                pred_<set> per RIDGE_SETS entry and "composite" (= the last set's pred column)
      "ridge":  per set {"col", "brier", "brier_n", "factors", "last_fold", "folds"}
      "brier":  baseline next-game Brier {name: (brier, n)} for CANDIDATES, "spread", "elo_538"
      "games":  per test-season game: game_id, season, asof_week, y and p_composite, p_elo,
                p_season_wpct, p_last16, p_pd_pg, p_spread, p_elo_538, restricted to games where
                every p_ is defined (inner joins on game_id)
    """
    seasons = test_seasons(include_holdout)
    last_season = seasons[-1]
    snaps = derived["snapshots"].filter(pl.col("season") <= last_season)
    team_games = derived["team_games"].filter(pl.col("season") <= last_season)
    games = derived["games"].filter(pl.col("season") <= last_season)
    pbp_games = _sealed_pbp(derived, last_season)

    feats = _z_frame(snaps, team_games, pbp_games, *_sealed_sim(derived, last_season))
    full = feats.join(targets(team_games, snaps, NS), on=KEYS, how="left").sort(KEYS)
    ng = next_game_frame(games, feats, list(CANDIDATES.values()))

    # Ridge composites: trained on every earlier season, scored on the test season only.
    zcols = [f"z_{f}" for f in PROPOSAL_FACTORS]
    ngz = next_game_frame(games, feats, zcols)
    ridge_meta: dict[str, dict] = {}
    pred_cols = []
    game_p = None
    for name, factors in RIDGE_SETS.items():
        r = _ridge_walk_forward(full, ngz, seasons, factors)
        col = f"pred_{name}"
        pred_cols.append(pl.Series(col, r["pred"], dtype=pl.Float64).fill_nan(None))
        ridge_meta[name] = {"col": col, "brier": r["brier"], "brier_n": r["brier_n"], "factors": factors,
                            "last_fold": r["last_fold"], "folds": r["folds"]}
        game_p = r["game_p"]  # the last set's (composite) per-game probabilities
    last_col = ridge_meta[list(RIDGE_SETS)[-1]]["col"]
    full = full.with_columns(pred_cols).with_columns(pl.col(last_col).alias("composite"))
    rows = full.filter(pl.col("season").is_in(seasons)).with_columns(bucket_expr().alias("bucket"))

    def ok(p):  # finite probability -> keep
        return pl.Series(p, dtype=pl.Float64).fill_nan(None)

    in_test = pl.col("season").is_in(seasons)
    g = ngz.select("game_id", "season", "asof_week", "y").with_columns(ok(game_p).alias("p_composite"))
    g = g.filter(in_test)
    base_brier: dict[str, tuple] = {}
    p_base = ng.select("game_id")
    for name, col in CANDIDATES.items():
        bs, bn, p = _walk_forward_brier(
            ng, seasons,
            lambda t, c=col: np.column_stack([(t[f"h_{c}"] - t[f"a_{c}"]).to_numpy(), t["home_ind"].to_numpy()]),
            return_p=True,
        )
        base_brier[name] = (bs, bn)
        p_base = p_base.with_columns(ok(p).alias(f"p_{name}"))

    sp = ng.filter(pl.col("spread_line").is_not_null())
    bs, bn, p = _walk_forward_brier(sp, seasons, lambda t: t["spread_line"].to_numpy(), return_p=True)
    base_brier["spread"] = (bs, bn)
    p_sp = sp.select("game_id").with_columns(ok(p).alias("p_spread"))

    te = ng.filter(in_test)
    base_brier["elo_538"] = (brier(_p538(te), te["y"].to_numpy()) if te.height else None, te.height)
    p538 = te.select("game_id").with_columns(pl.Series("p_elo_538", _p538(te), dtype=pl.Float64))

    gcols = ["p_composite"] + [f"p_{n}" for n in CANDIDATES] + ["p_spread", "p_elo_538"]
    games_frame = (
        g.join(p_base, on="game_id", how="inner")
        .join(p_sp, on="game_id", how="inner")
        .join(p538, on="game_id", how="inner")
        .drop_nulls(gcols)
        .sort("season", "game_id")
    )
    return {"seasons": seasons, "rows": rows, "ridge": ridge_meta, "brier": base_brier, "games": games_frame}


def run_backtest(derived: dict, include_holdout: bool = False) -> dict:
    """Baselines vs the locked target, walk-forward by season. Seasons past the last test season
    (2021 by default) are dropped before any metric or fit, so the holdout stays sealed."""
    wf = walk_forward_frame(derived, include_holdout)
    seasons, df, ridge_meta = wf["seasons"], wf["rows"], wf["ridge"]

    cands: dict[str, dict] = {}
    columns = dict(CANDIDATES) | {name: m["col"] for name, m in ridge_meta.items()}
    for name, col in columns.items():
        entry: dict = {"per_season": {}}
        for n in NS:
            y = f"y{n}"
            d = df.filter(pl.col(y).is_not_null())
            block = {"all": _corr_block(d[col].to_numpy(), d[y].to_numpy())}
            for b in BUCKETS:
                db = d.filter(pl.col("bucket") == b)
                block[b] = _corr_block(db[col].to_numpy(), db[y].to_numpy())
            entry[f"N{n}"] = block
            entry["per_season"][f"N{n}"] = {
                str(s): _corr_block(ds[col].to_numpy(), ds[y].to_numpy())
                for s in seasons
                if not (ds := d.filter(pl.col("season") == s)).is_empty()
            }
        if name in ridge_meta:
            m = ridge_meta[name]
            entry["brier"], entry["brier_n"] = m["brier"], m["brier_n"]
            entry["factors"] = m["factors"]
            entry["last_fold_weights"] = m["last_fold"]
        else:
            entry["brier"], entry["brier_n"] = wf["brier"][name]
        cands[name] = entry

    bs, bn = wf["brier"]["spread"]
    cands["spread"] = {"N4": None, "N8": None, "per_season": None, "brier": bs, "brier_n": bn}
    bs, bn = wf["brier"]["elo_538"]
    cands["elo_538"] = {"N4": None, "N8": None, "per_season": None, "brier": bs, "brier_n": bn}

    report = {
        "target": TARGET_TEXT,
        "ns": list(NS),
        "test_seasons": seasons,
        "include_holdout": include_holdout,
        "candidates": cands,
    }
    return _clean(report)


def _clean(obj):
    """Round floats and turn any NaN/inf into None so the JSON is strict."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    if isinstance(obj, (float, np.floating)):
        v = float(obj)
        return None if not np.isfinite(v) else _round(v)
    if isinstance(obj, np.integer):
        return int(obj)
    return obj


def _fmt(v, nd: int) -> str:
    return "—" if v is None else f"{v:.{nd}f}"


def format_report(report: dict) -> str:
    seasons = report["test_seasons"]
    seal = "HOLDOUT INCLUDED" if report["include_holdout"] else "holdout sealed"
    lines = [f"walk-forward backtest, test seasons {seasons[0]}–{seasons[-1]} ({seal})"]
    cols = ["Spearman", "R²", "wk0", "early", "mid", "late", "Brier"]
    for n in sorted(report["ns"], reverse=True):
        lines.append("")
        lines.append(f"N={n}  (target: mean adjusted margin over next {n} games; bucket columns are Spearman)")
        lines.append(f"{'candidate':<22}" + "".join(f"{c:>10}" for c in cols) + f"{'n':>9}")
        for name, c in report["candidates"].items():
            blk = c.get(f"N{n}")
            if blk is None:
                vals = ["—"] * 6
                nrows = c["brier_n"]
            else:
                vals = [_fmt(blk["all"]["spearman"], 3), _fmt(blk["all"]["r2"], 3)]
                vals += [_fmt(blk[b]["spearman"], 3) for b in BUCKETS]
                nrows = blk["all"]["n"]
            vals.append(_fmt(c["brier"], 4))
            lines.append(f"{name:<22}" + "".join(f"{v:>10}" for v in vals) + f"{nrows:>9}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Offseason draft term (Phase 7, MODEL-16): training-only walk-forward + gate
# ---------------------------------------------------------------------------
# The 2022-2025 holdout was consumed by Phase 6, so the draft term's evidence is walk-forward
# on training seasons only. Every frame is cut to season <= TRAIN_LAST_SEASON before features,
# targets or surplus z are computed, and there is deliberately no way to include later seasons.

DRAFT_GATE_FOLDS = 0.60


def _ols(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """OLS coefficients and their classical standard errors (X includes the intercept column)."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = max(len(y) - X.shape[1], 1)
    cov = (resid @ resid / dof) * np.linalg.pinv(X.T @ X)
    return beta, np.sqrt(np.clip(np.diag(cov), 0, None))


def _resid_slope(x: np.ndarray, r: np.ndarray) -> float:
    """Slope of r ~ 1 + x (0.0 when x is constant)."""
    xc = x - x.mean()
    v = float(xc @ xc)
    return 0.0 if v <= 1e-12 else float(xc @ (r - r.mean()) / v)


def _sp_delta(pred, base, y) -> float | None:
    a, b = spearman(pred, y), spearman(base, y)
    return None if a is None or b is None else a - b


def _draft_fit(frame: pl.DataFrame, seasons: list[int]) -> dict:
    """Fit core on [season, week, composite, y8, draft_z] rows (all season <= TRAIN_LAST_SEASON).

    Residual form: the frozen composite is fixed. Per test season S, the slope of
    (y8 - composite) ~ 1 + decay(week)*draft_z over seasons [FIRST_DRAFT, S-1] is the fold
    weight, and season S is predicted as composite + w*x. The final weight is the same fit on all
    rows. Only weeks < DECAY_WEEKS carry the term (x = 0 afterwards)."""
    assert frame.height == 0 or int(frame["season"].max()) <= TRAIN_LAST_SEASON, "holdout rows in draft fit"
    d = (
        frame.filter((pl.col("week") < draft.DECAY_WEEKS) & (pl.col("season") >= draft.FIRST_DRAFT)
                     & pl.col("y8").is_not_null())
        .with_columns(pl.col("draft_z").fill_null(0.0))
        .with_columns((pl.col("draft_z") * (1.0 - pl.col("week") / draft.DECAY_WEEKS)).alias("x"))
        .sort("season", "week", "franchise_id")
    )
    sea, wk = d["season"].to_numpy(), d["week"].to_numpy()
    x, comp, y = d["x"].to_numpy(), d["composite"].to_numpy(), d["y8"].to_numpy()
    r = y - comp

    pred = np.full(len(d), np.nan)
    fold_w, fold_s = [], []
    for S in seasons:
        tr, te = (sea >= draft.FIRST_DRAFT) & (sea < S), sea == S
        if not tr.any() or not te.any():
            continue
        w = _resid_slope(x[tr], r[tr])
        pred[te] = comp[te] + w * x[te]
        fold_w.append(w)
        fold_s.append(int(S))
    final = _resid_slope(x, r) if len(d) else 0.0

    tested = ~np.isnan(pred)
    w0 = tested & (wk == 0)
    per_season = [_sp_delta(pred[w0 & (sea == S)], comp[w0 & (sea == S)], y[w0 & (sea == S)]) for S in fold_s]
    pos = sum(1 for v in per_season if v is not None and v > 0)

    a0 = wk == 0
    partial = {"coef": None, "t": None}
    if a0.sum() > 3:
        beta, se = _ols(np.column_stack([np.ones(a0.sum()), comp[a0], x[a0]]), y[a0])
        partial = {"coef": float(beta[2]), "t": float(beta[2] / se[2]) if se[2] > 0 else None}
    return {
        "fold_weights": fold_w,
        "fold_seasons": fold_s,
        "final": final,
        "delta_wk0": _sp_delta(pred[w0], comp[w0], y[w0]),
        "delta_wk0_3": _sp_delta(pred[tested], comp[tested], y[tested]),
        "seasons_pos": f"{pos}/{len(fold_s)}",
        "partial_wk0": partial,
        "n_rows": int(len(d)),
    }


def draft_walk_forward(derived: dict, weights: dict[str, float], winsor=None) -> dict:
    """Walk-forward test of the offseason draft term on top of the FROZEN composite (weights as
    given), training seasons only: surplus 2000-2021, test seasons 2003-2021, target y8."""
    if derived.get("draft") is None:
        raise ValueError("draft cache missing; run `uv run fgs build`")
    last = TRAIN_LAST_SEASON
    snaps = derived["snapshots"].filter(pl.col("season") <= last)
    team_games = derived["team_games"].filter(pl.col("season") <= last)
    pbp_games = _sealed_pbp(derived, last)
    sim, vegas = _sealed_sim(derived, last)
    surplus = derived["draft"].filter(pl.col("season").is_between(draft.FIRST_DRAFT, last))
    for f in (snaps, team_games, pbp_games, sim, vegas, surplus):  # hard guard: holdout never read
        assert f is None or f.height == 0 or int(f["season"].max()) <= last, "holdout season in draft fit"
    bounds = tuple(winsor) if winsor is not None else draft.winsor_bounds(surplus, (draft.FIRST_DRAFT, last))

    feats = build_features(snaps, team_games, pbp_games=pbp_games, sim=sim, vegas=vegas)
    feats = score_composite(feats, weights)
    dz = draft.draft_z(surplus, bounds).select(pl.col("season").cast(pl.Int32), "franchise_id", "draft_z")
    frame = (
        feats.select(KEYS + ["composite"])
        .with_columns(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32))
        .join(targets(team_games, snaps, (8,)), on=KEYS, how="left")
        .join(dz, on=["season", "franchise_id"], how="left")
    )
    res = _draft_fit(frame, list(range(FIRST_TEST_SEASON, last + 1)))
    res["winsor"] = [float(bounds[0]), float(bounds[1])]
    return res


def draft_gate(fold_ws: list[float], final_w: float, d_wk0: float | None) -> dict:
    """Locked gate (07-RESEARCH): fold-sign consistency is measured against the FINAL weight's
    sign (Pitfall 4). Pass only when final_w > 0, >= 60% of folds share its sign and wk0 Δ > 0."""
    n = len(fold_ws)
    k = sum(1 for w in fold_ws if np.sign(w) == np.sign(final_w))
    same = k / n if n else 0.0
    ok = d_wk0 is not None and d_wk0 > 0 and same >= DRAFT_GATE_FOLDS and final_w > 0
    return {"weight": round(float(final_w), 2) if ok else 0.0, "fitted": float(final_w), "delta_wk0": d_wk0,
            "fold_sign_consistency": same, "k": k, "n": n, "display_only": not ok}


def _sgn(v, nd: int) -> str:
    return "—" if v is None else f"{v:+.{nd}f}"


def format_draft_report(res: dict, gate: dict, date: str) -> str:
    """Human summary, one BACKTEST_LOG 'Offseason terms' row and the ready-to-paste offseason block."""
    lo, hi = res["winsor"]
    fs = f"{gate['k']}/{gate['n']}"
    verdict = ("gate PASSED" if not gate["display_only"] else "gate failed") + (
        f": fitted {gate['fitted']:+.2f}, {fs} folds share its sign, wk0 ΔSpearman {_sgn(gate['delta_wk0'], 4)}"
        f" -> weight {gate['weight']:.2f}" + (", display only" if gate["display_only"] else ""))
    p = res["partial_wk0"]
    seasons = res["fold_seasons"]
    lines = [
        "offseason draft term on the FROZEN composite: training-only walk-forward (holdout consumed by Phase 6)",
        f"surplus {draft.FIRST_DRAFT}-{TRAIN_LAST_SEASON}, test seasons {seasons[0]}-{seasons[-1]}, "
        f"target N=8, chart {draft.CHART}, winsor [{lo:.2f}, {hi:.2f}], decay linear to 0 by week {draft.DECAY_WEEKS}",
        f"  rows (weeks 0-{draft.DECAY_WEEKS - 1}): {res['n_rows']}",
        f"  final weight (2000-{TRAIN_LAST_SEASON}): {res['final']:+.4f}",
        f"  fold weights: " + " ".join(f"{s}:{w:+.2f}" for s, w in zip(seasons, res["fold_weights"])),
        f"  fold-sign consistency vs final: {fs} ({gate['fold_sign_consistency']:.2f})",
        f"  wk0 ΔSpearman (N=8): {_sgn(res['delta_wk0'], 4)}; weeks 0-3: {_sgn(res['delta_wk0_3'], 4)}; "
        f"seasons with wk0 Δ>0: {res['seasons_pos']}",
        f"  partial check wk0 (y8 ~ 1 + composite + x): coef {_sgn(p['coef'], 3)}, t {_sgn(p['t'], 2)}",
        f"  {verdict}",
        "",
        "BACKTEST_LOG row (Offseason terms table):",
        "| Date | Term | wk0 ΔSpearman (N=8) | Fitted weight | Fold-sign consistency | Gate | Notes |",
        f"| {date} | draft | {_sgn(res['delta_wk0'], 4)} | {res['final']:+.4f} | {fs} | "
        f"{'pass' if not gate['display_only'] else 'fail'} -> {gate['weight']:.2f} | "
        f"residual on frozen composite; weeks 0-3 Δ {_sgn(res['delta_wk0_3'], 4)}; wk0 seasons Δ>0 "
        f"{res['seasons_pos']}; training-only walk-forward {seasons[0]}-{seasons[-1]} (no fresh holdout) |",
        "",
        "weights.yaml block (append at the end):",
        "offseason:",
        "  draft:",
        f"    weight: {gate['weight']:.2f}",
        f"    display_only: {'true' if gate['display_only'] else 'false'}",
        f"    chart: {draft.CHART}",
        f"    winsor: [{lo:.2f}, {hi:.2f}]",
        "    decay: linear_to0_by_wk4",
        f"    fit_seasons: {draft.FIRST_DRAFT}-{TRAIN_LAST_SEASON}",
        f"    test_seasons: {seasons[0]}-{seasons[-1]}",
        f"    fitted: {res['final']:.4f}",
        f'    fold_sign: "{fs}"',
        f"    delta_wk0: {0.0 if res['delta_wk0'] is None else res['delta_wk0']:.4f}",
        "    evidence: training-only walk-forward (no fresh holdout)",
    ]
    return "\n".join(lines)

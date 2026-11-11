"""Vectorized Monte Carlo season simulator (MODEL-13) plus a content-addressed parquet cache.

For any (season, week) it simulates every REG game not known as of that week
(known = played & asof_week <= week) from as-of Elo, under the season's era rules
(fgs.season_config: divisions, playoff_teams, hfa_for), and returns each team's playoff
probability and expected final REG wins (ties count 0.5).

Each sim draws a per-team rating offset N(0, SIGMA) that stays fixed within that sim
(no hot updates). Simplified tiebreak chain:
  division winner: win% -> head-to-head win% among the tied set (0.5 if never met)
                   -> division win% -> random
  wildcards (one at a time per conference): win% -> head-to-head -> random
Ranking is by win%, not wins (BUF/CIN 2022 played 16).

One RNG stream per snapshot, default_rng([seed, season, week]), so results do not depend
on computation order or on incremental runs.

Pure apart from cache I/O in simulate_all. This module must stay upstream of the backtest
(never import it).
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import polars as pl

from fgs import season_config as sc
from fgs.elo import EloParams

SIM_VERSION = "sim-v1"
# WR-06: the cache key covers this module's source, so any edit to the simulator (tiebreaks,
# noise, win-prob formula, _static) invalidates the cache without a manual SIM_VERSION bump.
# Conservative: comment/docstring edits also re-simulate (one cold run).
SIM_CODE_HASH = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
N_SIMS = 2000
SIGMA = 100.0
SEED = 20261111

_OUT_SCHEMA = {
    "season": pl.Int32,
    "week": pl.Int32,
    "franchise_id": pl.String,
    "playoff_prob": pl.Float64,
    "exp_wins": pl.Float64,
}


def _sort_games(season_games: pl.DataFrame) -> pl.DataFrame:
    keys = [c for c in ("gameday", "gametime") if c in season_games.columns] + ["game_id"]
    return season_games.sort(keys)


def _static(season: int, teams: list[str]):
    """Division/conference ids for present teams, from the FULL config (call-time lookup)."""
    divs = sc.divisions(season)
    div_names = list(divs)
    confs = sorted({d.split()[0] for d in div_names})
    T = len(teams)
    idx = {t: i for i, t in enumerate(teams)}
    div_id = np.full(T, -1)
    conf_id = np.full(T, -1)
    for d_i, d in enumerate(div_names):
        for t in divs[d]:
            if t in idx:
                div_id[idx[t]] = d_i
                conf_id[idx[t]] = confs.index(d.split()[0])
    missing = [t for t in teams if div_id[idx[t]] < 0]
    if missing:
        raise KeyError(f"no division in {season} for {missing}")
    return idx, div_id, conf_id, len(div_names), len(confs)


def simulate_season(
    season_games: pl.DataFrame,
    elo: dict[str, float],
    week: int,
    n_sims: int = N_SIMS,
    seed: int = SEED,
    sigma: float = SIGMA,
) -> tuple[list[str], np.ndarray, np.ndarray]:
    """season_games: one season's REG games (game_id, season, home_id, away_id, result, played,
    asof_week, neutral[, gameday, gametime]). elo: as-of ratings at (season, week).
    Returns (teams, playoff_prob, exp_wins), arrays aligned with the sorted team list."""
    g = _sort_games(season_games)
    season = int(g["season"][0])
    teams = sorted(set(g["home_id"].to_list()) | set(g["away_id"].to_list()))
    idx, div_id, conf_id, n_div, n_conf = _static(season, teams)
    T = len(teams)
    rng = np.random.default_rng([seed, season, week])

    h = np.array([idx[t] for t in g["home_id"]], dtype=np.int64)
    a = np.array([idx[t] for t in g["away_id"]], dtype=np.int64)
    played = g["played"].fill_null(False).to_numpy() & (g["asof_week"].to_numpy() <= week)
    res = g["result"].fill_null(0).to_numpy().astype(float)
    known = np.where(res > 0, 1.0, np.where(res < 0, 0.0, 0.5))  # home perspective
    rem = ~played
    neutral = g["neutral"].fill_null(False).to_numpy()
    hfa = sc.hfa_for(season)
    e = np.array([float(elo[t]) for t in teams])
    G = len(h)

    u = rng.random((n_sims, int(rem.sum())))
    noise = rng.normal(0.0, 1.0, (n_sims, T)) * sigma  # per-sim team offset (A2)
    diff = (e[h] - e[a] + np.where(neutral, 0.0, hfa))[None, :] + noise[:, h] - noise[:, a]
    p = 1.0 / (1.0 + 10 ** (-diff[:, rem] / 400.0))
    out = np.empty((n_sims, G), dtype=np.float32)
    out[:, ~rem] = known[~rem]
    out[:, rem] = (u < p).astype(np.float32)

    # R[s, i, j] = wins of i over j (ties 0.5), via one-hot pair matrices.
    P = np.zeros((G, T * T), dtype=np.float32)
    Q = np.zeros((G, T * T), dtype=np.float32)
    P[np.arange(G), h * T + a] = 1.0
    Q[np.arange(G), a * T + h] = 1.0
    R = (out @ P + (1.0 - out) @ Q).reshape(n_sims, T, T)
    Gm = np.zeros((T, T), dtype=np.float32)
    np.add.at(Gm, (h, a), 1)
    np.add.at(Gm, (a, h), 1)

    wins = R.sum(2)
    ngames = Gm.sum(1)
    wpct = np.round(wins / np.maximum(ngames, 1), 9)
    same_div = (div_id[:, None] == div_id[None, :]) & ~np.eye(T, dtype=bool)
    divw = (R * same_div).sum(2)
    divg = (Gm * same_div).sum(1)
    divpct = np.round(divw / np.maximum(divg, 1), 9)

    rnd = rng.random((n_sims, T))
    made = np.zeros((n_sims, T), dtype=bool)
    rows = np.arange(n_sims)

    def best(m, v):
        return m & (v == np.where(m, v, -1.0).max(1, keepdims=True))

    def h2h(m):  # win% vs the tied set; 0.5 where no mutual games
        mf = m.astype(np.float32)
        hw = np.einsum("sij,sj->si", R, mf)
        hg = mf @ Gm.T
        return np.round(np.where(hg > 0, hw / np.maximum(hg, 1), 0.5), 9)

    def choose(m):
        has = m.any(1)
        pickd = np.argmax(np.where(m, rnd, -1.0), axis=1)
        made[rows[has], pickd[has]] = True

    slots = sc.playoff_teams(season) // n_conf
    div_per_conf = n_div // n_conf
    for d in range(n_div):
        if not (div_id == d).any():
            continue  # division with no present teams
        m = np.broadcast_to(div_id == d, (n_sims, T))
        m = best(m, wpct)
        m = best(m, h2h(m))
        m = best(m, divpct)
        choose(m)
    for c in range(n_conf):
        for _ in range(slots - div_per_conf):
            cand = (conf_id == c)[None, :] & ~made
            if not cand.any():
                break
            m = best(cand, wpct)
            m = best(m, h2h(m))
            choose(m)

    return teams, made.mean(0).astype(np.float64), wins.mean(0).astype(np.float64)


# ---------------------------------------------------------------------------
# Versioning + cache
# ---------------------------------------------------------------------------


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def model_version(n_sims: int = N_SIMS, sigma: float = SIGMA, seed: int = SEED) -> str:
    """Hash of everything that parameterizes the simulator (not the data)."""
    ep = dataclasses.asdict(EloParams())
    ep["seeds"] = sorted([k[0], int(k[1]), float(v)] for k, v in ep["seeds"].items())
    payload = {
        "elo": ep,
        "hfa": [list(x) for x in sc.HFA_BY_ERA],
        "divisions": [sc.DIVISIONS_1999_2001, sc.DIVISIONS_2002_ON],
        "playoff_teams": {str(s): sc.playoff_teams(s) for s in range(1999, 2031)},
        "n_sims": int(n_sims),
        "sigma": float(sigma),
        "seed": int(seed),
        "sim": SIM_VERSION,
        "code": SIM_CODE_HASH,
    }
    return _sha(payload)[:12]


def input_digest(season_games: pl.DataFrame, season_snaps: pl.DataFrame) -> str:
    """Per-season data digest: REG games + as-of Elo grid.

    Hashes exactly what simulate_season reads, in the order it reads it (WR-05): the game order
    (gameday, gametime, game_id) decides which uniform draw goes to which game, so a moved
    kickoff must invalidate the cached season even when no result changed."""
    cols = ["game_id", "home_id", "away_id", "result", "played", "asof_week", "neutral"]
    cols += [c for c in ("gameday", "gametime") if c in season_games.columns]
    g = _sort_games(season_games).select(cols)
    s = season_snaps.select(
        pl.col("week").cast(pl.Int64), "franchise_id", pl.col("elo").cast(pl.Float64).round(9)
    ).sort("week", "franchise_id")
    return _sha({"g": g.rows(), "s": s.rows()})


def _simulate_one_season(sg, ss, n_sims, sigma, seed) -> pl.DataFrame:
    season = int(sg["season"][0])
    recs = {k: [] for k in _OUT_SCHEMA}
    for w in sorted(ss["week"].unique().to_list()):
        sw = ss.filter(pl.col("week") == w)
        elo = dict(zip(sw["franchise_id"].to_list(), sw["elo"].to_list()))
        extra = set(elo) - (set(sg["home_id"].to_list()) | set(sg["away_id"].to_list()))
        assert not extra, f"{season} wk{w}: snapshot teams without REG games: {sorted(extra)}"
        teams, pp, ew = simulate_season(sg, elo, int(w), n_sims=n_sims, seed=seed, sigma=sigma)
        n = len(teams)
        recs["season"] += [season] * n
        recs["week"] += [int(w)] * n
        recs["franchise_id"] += teams
        recs["playoff_prob"] += pp.tolist()
        recs["exp_wins"] += ew.tolist()
    return pl.DataFrame(recs, schema=_OUT_SCHEMA)


def _cache_path(cache_dir, version: str | None = None) -> Path:
    return Path(cache_dir) / f"{version or model_version()}.parquet"


def save_sim_cache(frame: pl.DataFrame, cache_dir: Path | str, version: str | None = None) -> Path:
    """Atomically write a simulate_all frame (with its input_digest column) as the cache file."""
    path = _cache_path(cache_dir, version)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    frame.write_parquet(tmp)
    os.replace(tmp, path)
    return path


def simulate_all(
    games: pl.DataFrame,
    snapshots: pl.DataFrame,
    *,
    n_sims: int = N_SIMS,
    sigma: float = SIGMA,
    seed: int = SEED,
    cache_dir: Path | str | None = None,
    write_cache: bool = True,
) -> pl.DataFrame:
    """Every (season, week) in snapshots -> playoff_prob, exp_wins per franchise, plus the
    per-season input_digest column.

    With cache_dir, reuse `{cache_dir}/{model_version}.parquet` rows for seasons whose
    input_digest is unchanged and recompute the rest. The cache is rewritten atomically unless
    write_cache=False (refresh writes it via save_sim_cache only after the checks pass)."""
    reg = games.filter(pl.col("is_reg"))
    seasons = sorted(snapshots["season"].unique().to_list())
    version = model_version(n_sims, sigma, seed)

    cached = None
    if cache_dir is not None:
        path = _cache_path(cache_dir, version)
        if path.exists():
            cached = pl.read_parquet(path)

    parts = []
    for s in seasons:
        sg = reg.filter(pl.col("season") == s)
        assert sg.height > 0, f"season {s} has snapshots but no REG games"
        ss = snapshots.filter(pl.col("season") == s)
        dig = input_digest(sg, ss)
        hit = None
        if cached is not None:
            hit = cached.filter((pl.col("season") == s) & (pl.col("input_digest") == dig))
            if hit.height == 0:
                hit = None
        if hit is None:
            df = _simulate_one_season(sg, ss, n_sims, sigma, seed).with_columns(
                pl.lit(dig).alias("input_digest")
            )
        else:
            df = hit.select(*_OUT_SCHEMA, "input_digest").cast(_OUT_SCHEMA)
        parts.append(df)

    full = (
        pl.concat(parts)
        if parts
        else pl.DataFrame(schema={**_OUT_SCHEMA, "input_digest": pl.String})
    ).sort("season", "week", "franchise_id")

    if cache_dir is not None and write_cache:
        save_sim_cache(full, cache_dir, version)
    return full

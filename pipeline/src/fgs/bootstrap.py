"""Paired percentile bootstrap (pure NumPy; imports nothing from fgs).

Callers pass stat functions that take a row-index array and return a float (or None when the
statistic is undefined on that draw). Every stat is evaluated on the SAME index array per draw,
so differences between stats are paired.

Constants:
    B_DEFAULT = 2000, SEED = 20221, LEVEL = 0.95   (fixed in pipeline/PREREGISTRATION.md)

API:
    season_blocks(season) -> list[np.ndarray]
        one row-index array per unique season, sorted by season
    stratified_clusters(season, cluster_key) -> list[list[np.ndarray]]
        per season, the row-index arrays of each unique cluster key
        (team-season: franchise_id; season-week: asof week)
    draw_blocks(rng, blocks) -> np.ndarray
        len(blocks) blocks drawn with replacement, concatenated
    draw_stratified(rng, strata) -> np.ndarray
        within each season, that season's clusters drawn with replacement (same count), concatenated
    distinct_block_resamples(k) -> int
        C(2k-1, k): distinct multisets when drawing k blocks with replacement (k=4 -> 35)
    percentile_ci(values, level=LEVEL) -> [lo, hi] | None
        nan-aware percentile interval; None if no finite values
    paired_bootstrap(stat_fns, draw, *, diffs=None, B=B_DEFAULT, seed=SEED) -> dict
        {"B", "seed", "stats": {name: {"ci", "sd", "n_finite"}},
                      "diffs": {name: {"ci", "sd", "n_finite"}}}
        floats rounded to 6 dp; NaN -> None (strict JSON)
"""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np

B_DEFAULT = 2000
SEED = 20221
LEVEL = 0.95


def season_blocks(season: np.ndarray) -> list[np.ndarray]:
    season = np.asarray(season)
    return [np.flatnonzero(season == s) for s in np.unique(season)]


def stratified_clusters(season: np.ndarray, cluster_key: np.ndarray) -> list[list[np.ndarray]]:
    season = np.asarray(season)
    key = np.asarray(cluster_key)
    out: list[list[np.ndarray]] = []
    for s in np.unique(season):
        rows = np.flatnonzero(season == s)
        k = key[rows]
        out.append([rows[k == c] for c in np.unique(k)])
    return out


def draw_blocks(rng: np.random.Generator, blocks: list[np.ndarray]) -> np.ndarray:
    pick = rng.integers(0, len(blocks), size=len(blocks))
    return np.concatenate([blocks[j] for j in pick])


def draw_stratified(rng: np.random.Generator, strata: list[list[np.ndarray]]) -> np.ndarray:
    parts: list[np.ndarray] = []
    for clusters in strata:
        pick = rng.integers(0, len(clusters), size=len(clusters))
        parts.extend(clusters[j] for j in pick)
    return np.concatenate(parts)


def distinct_block_resamples(k: int) -> int:
    return math.comb(2 * k - 1, k)


def _r(v: float) -> float | None:
    v = float(v)
    return round(v, 6) if math.isfinite(v) else None


def percentile_ci(values, level: float = LEVEL) -> list[float] | None:
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return None
    a = (1.0 - level) / 2.0 * 100.0
    lo, hi = np.percentile(v, [a, 100.0 - a])
    return [float(lo), float(hi)]


def _summary(vals: np.ndarray) -> dict:
    finite = vals[np.isfinite(vals)]
    ci = percentile_ci(finite)
    return {
        "ci": None if ci is None else [_r(ci[0]), _r(ci[1])],
        "sd": _r(np.std(finite)) if finite.size else None,
        "n_finite": int(finite.size),
    }


def paired_bootstrap(
    stat_fns: dict[str, Callable[[np.ndarray], float | None]],
    draw: Callable[[np.random.Generator], np.ndarray],
    *,
    diffs: dict[str, tuple[str, str]] | None = None,
    B: int = B_DEFAULT,
    seed: int = SEED,
) -> dict:
    rng = np.random.default_rng(seed)
    names = list(stat_fns)
    vals = {n: np.full(B, np.nan) for n in names}
    for b in range(B):
        idx = draw(rng)  # one index array shared by every stat -> paired
        for n in names:
            v = stat_fns[n](idx)
            if v is not None:
                vals[n][b] = float(v)
    out_diffs = {}
    for name, (a, c) in (diffs or {}).items():
        out_diffs[name] = _summary(vals[a] - vals[c])
    return {
        "B": int(B),
        "seed": int(seed),
        "stats": {n: _summary(vals[n]) for n in names},
        "diffs": out_diffs,
    }

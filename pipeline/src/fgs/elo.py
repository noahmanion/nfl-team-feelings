"""538-style NFL Elo (mirrors fivethirtyeight/nfl-elo-game forecast.py)."""

import math
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import polars as pl

from fgs.season_config import MEAN_ELO, SEEDS, hfa_for


@dataclass(frozen=True)
class EloParams:
    k: float = 20.0
    mean: float = MEAN_ELO
    revert: float = 1 / 3  # fraction pulled toward the mean each offseason
    seeds: dict[tuple[str, int], float] = field(default_factory=lambda: dict(SEEDS))


def win_prob(diff: float) -> float:
    """Home win probability; diff = elo_home - elo_away + hfa."""
    return 1.0 / (10 ** (-diff / 400.0) + 1.0)


def mov_mult(margin: float, diff: float, res: float) -> float:
    """ln(max(|MOV|,1)+1) * 2.2 / (winner_elo_diff*0.001 + 2.2); diff includes HFA.

    Ties use a denominator of 1.0 (538), i.e. ln(2) * 2.2.
    """
    pd = abs(margin)
    if res == 0.5:
        return math.log(max(pd, 1) + 1.0) * 2.2
    winner_diff = diff if res == 1.0 else -diff
    return math.log(max(pd, 1) + 1.0) * (2.2 / (winner_diff * 0.001 + 2.2))


def update(elo_h: float, elo_a: float, margin: float, hfa: float, k: float) -> tuple[float, float, float]:
    diff = elo_h - elo_a + hfa
    p = win_prob(diff)
    res = 1.0 if margin > 0 else 0.0 if margin < 0 else 0.5
    shift = k * mov_mult(margin, diff, res) * (res - p)
    return elo_h + shift, elo_a - shift, p


SPARSE_SCHEMA = {"season": pl.Int32, "week": pl.Int32, "franchise_id": pl.String, "elo": pl.Float64}


def replay(
    games: pl.DataFrame,
    params: EloParams = EloParams(),
    hfa: Callable[[int], float] = hfa_for,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Chronological replay. Returns (games with Elo columns, sparse (season, week, team, elo) rows).

    Each season: regress every rated team 1/3 toward the mean, seed first-time teams,
    emit week-0 rows for that season's teams, then apply every played game in order.
    """
    games = games.sort(["season", "week", "gameday", "gametime", "game_id"], nulls_last=True)
    teams = sorted(set(games["home_id"]) | set(games["away_id"]))
    idx = {t: i for i, t in enumerate(teams)}
    ratings = np.full(len(teams), np.nan, dtype=np.float64)

    n = games.height
    pre_h = [None] * n
    pre_a = [None] * n
    post_h = [None] * n
    post_a = [None] * n
    p_home = [None] * n
    sparse: list[tuple[int, int, str, float]] = []

    rows = games.select("season", "week", "home_id", "away_id", "result", "neutral", "played").rows()
    seasons = sorted({r[0] for r in rows})
    by_season: dict[int, list[int]] = {s: [] for s in seasons}
    for i, r in enumerate(rows):
        by_season[r[0]].append(i)

    for season in seasons:
        rated = ~np.isnan(ratings)
        ratings[rated] = params.mean * params.revert + ratings[rated] * (1 - params.revert)
        in_season = sorted({rows[i][2] for i in by_season[season]} | {rows[i][3] for i in by_season[season]})
        for t in in_season:
            j = idx[t]
            if np.isnan(ratings[j]):
                ratings[j] = params.seeds.get((t, season), params.mean)
            sparse.append((season, 0, t, float(ratings[j])))
        h_fa = hfa(season)
        for i in by_season[season]:
            _, week, h, a, result, neutral, played = rows[i]
            if not played:
                continue
            hi, ai = idx[h], idx[a]
            eh, ea = float(ratings[hi]), float(ratings[ai])
            nh, na, p = update(eh, ea, result, 0.0 if neutral else h_fa, params.k)
            ratings[hi], ratings[ai] = nh, na
            pre_h[i], pre_a[i], post_h[i], post_a[i], p_home[i] = eh, ea, nh, na, p
            sparse.append((season, week, h, nh))
            sparse.append((season, week, a, na))

    out = games.with_columns(
        pl.Series("elo_pre_home", pre_h, dtype=pl.Float64),
        pl.Series("elo_pre_away", pre_a, dtype=pl.Float64),
        pl.Series("elo_post_home", post_h, dtype=pl.Float64),
        pl.Series("elo_post_away", post_a, dtype=pl.Float64),
        pl.Series("p_home", p_home, dtype=pl.Float64),
    )
    return out, pl.DataFrame(sparse, schema=SPARSE_SCHEMA, orient="row")

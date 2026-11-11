"""Additive feel-good score: composite = sum over factors of weight * z.

z is computed per (season, week) snapshot across the teams in it. Each factor's contribution
(contrib_f = w_f * z_f) is stored so the composite can be explained factor by factor.

Pure apart from load_weights, which reads one YAML file. Labels and descriptions live here;
the numbers live in pipeline/weights.yaml (the single source of truth for weights).
This module must not import the dev-only evaluation harness (leakage firewall).
"""

import math

import polars as pl
import yaml

from fgs import paths

FACTORS: dict[str, dict[str, str]] = {
    "elo": {
        "label": "Elo rating",
        "description": "Game-by-game strength rating; wins against good teams by big margins move it most",
    },
    "season_record": {
        "label": "Season record",
        "description": "This season's regular-season win %, ties count half",
    },
    "last16": {
        "label": "Last 16 games",
        "description": "Win % over the last 16 games, including last season and playoffs",
    },
    "mov": {
        "label": "Margin of victory",
        "description": "Average point margin over the last 8 games (each capped at 24), including last season and playoffs",
    },
    "sow": {
        "label": "Quality of results",
        "description": "Results over the last 8 games compared with what an average team would do against the same opponents; "
        "given Elo and margins, results running ahead of margins tend to fade, so a high value lowers the score",
    },
    "streak": {
        "label": "Streak",
        "description": "Current win or loss streak (ties end it), up to 8, carried across seasons; "
        "given the other factors a hot streak tends to fade, so it slightly lowers the score",
    },
    "luck": {
        "label": "Close-game luck",
        "description": "One-score wins minus one-score losses (8 points or fewer) over the last 16 games; "
        "close-game luck evens out, so a lucky record lowers the score",
    },
}

SNAPSHOT = ("season", "week")
STD_EPS = 1e-12


def load_weights(path=None) -> dict[str, float]:
    """Read {"weights": {factor: number}} from YAML, in file order."""
    path = paths.WEIGHTS_PATH if path is None else path  # read at call time (tests monkeypatch it)
    try:
        with open(path) as fh:
            doc = yaml.safe_load(fh)
    except FileNotFoundError:
        raise ValueError(f"weights file not found: {path}") from None
    w = doc.get("weights") if isinstance(doc, dict) else None
    if not isinstance(w, dict) or not w:
        raise ValueError(f"{path}: expected a non-empty top-level 'weights' mapping")
    out: dict[str, float] = {}
    for k, v in w.items():
        if k not in FACTORS:
            raise ValueError(f"{path}: unknown factor {k!r}; known: {', '.join(FACTORS)}")
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"{path}: weight for {k!r} must be a finite number, got {v!r}")
        out[k] = float(v)
    return out


def zscore(df: pl.DataFrame, cols, by=SNAPSHOT) -> pl.DataFrame:
    """Add z_{col} = (x - mean) / std(ddof=0) within each snapshot; 0.0 where std <= 1e-12.
    No clipping (an expansion team at week 0 really is an outlier)."""
    by = list(by)
    exprs = []
    for c in cols:
        sd = pl.col(c).std(ddof=0).over(by)
        exprs.append(
            pl.when(sd > STD_EPS)
            .then((pl.col(c) - pl.col(c).mean().over(by)) / sd)
            .otherwise(0.0)
            .cast(pl.Float64)
            .alias(f"z_{c}")
        )
    return df.with_columns(exprs)


def contrib_columns(weights: dict[str, float]) -> list[str]:
    return [f"contrib_{k}" for k in weights]


def composite(df: pl.DataFrame, weights: dict[str, float], by=SNAPSHOT) -> pl.DataFrame:
    """Add z_f, contrib_f = w_f * z_f (weights order) and composite = sum of contrib_f."""
    missing = [f for f in weights if f not in df.columns]
    if missing:
        raise ValueError(f"factor columns missing from frame: {', '.join(missing)}")
    df = zscore(df, list(weights), by=by)
    df = df.with_columns((pl.lit(float(w)) * pl.col(f"z_{f}")).alias(f"contrib_{f}") for f, w in weights.items())
    return df.with_columns(pl.sum_horizontal(contrib_columns(weights)).alias("composite"))

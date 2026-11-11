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

from fgs import draft, paths

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
    "epa_traj": {
        "label": "Getting better (efficiency trend)",
        "description": "Recent opponent-adjusted EPA per play (weighted toward the last ~4 games) minus this season's average; "
        "given the other factors, an efficiency upswing tends to fade, so it slightly lowers the score",
    },
    "qb_trend": {
        "label": "QB play (recent starts)",
        "description": "Current starting QB's EPA per dropback over his recent starts, on any team; "
        "0 for a QB with under 2 starts or before week 1",
    },
    "vs_exp": {
        "label": "Vs preseason expectations",
        "description": "Win % so far minus the win % expected before the season (Vegas win total 2003-2020, "
        "otherwise the model's preseason projection); given the record, beating expectations tends to fade "
        "(expectations usually catch up), so it lowers the score",
    },
    "po_trend": {
        "label": "Playoff odds trend",
        "description": "Change in simulated playoff odds over the last 3 weeks; "
        "adds about nothing beyond the other factors (kept so its weight is on record)",
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


def load_weights_doc(path=None) -> dict:
    """The whole weights.yaml document (weights plus the frozen/fit evidence keys)."""
    path = paths.WEIGHTS_PATH if path is None else path  # read at call time (tests monkeypatch it)
    try:
        with open(path) as fh:
            doc = yaml.safe_load(fh)
    except FileNotFoundError:
        raise ValueError(f"weights file not found: {path}") from None
    except yaml.YAMLError as e:
        raise ValueError(f"weights file is not valid YAML: {path}: {e}") from None
    return doc if isinstance(doc, dict) else {}


def is_frozen(path=None) -> bool:
    """True only when weights.yaml says `frozen: true` (Phase 6 freeze; refits are refused)."""
    return load_weights_doc(path).get("frozen") is True


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


# ---------------------------------------------------------------------------
# Offseason draft term (Phase 7, MODEL-16)
# ---------------------------------------------------------------------------
# Kept OUT of FACTORS and the frozen `weights:` block (load_weights rejects unknown keys there and
# the Phase 6 freeze owns it). Its weight lives in weights.yaml `offseason.draft`, decided by the
# training-only gate in `fgs backtest --draft`.

OFFSEASON_FACTORS: dict[str, dict[str, str]] = {
    "draft": {
        "label": "Draft capital over slot",
        "description": "Draft-pick value gained or lost by trades vs the team's original slots (stuart chart, "
        "capped); counts fully at week 0 and fades to nothing by week 4",
    },
}
DECAY_NAME = "linear_to0_by_wk4"


def _finite_number(v) -> bool:
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def load_offseason(path=None) -> dict:
    """weights.yaml `offseason.draft` -> {"weight", "display_only", "chart", "winsor", "decay"}.

    A missing block means weight 0.0 / display only / no winsor. Invalid values raise ValueError;
    unknown (evidence) keys are ignored."""
    doc = load_weights_doc(path)
    decay = [draft.decay(w) for w in range(draft.DECAY_WEEKS)]
    off = doc.get("offseason")
    if off is not None and not isinstance(off, dict):
        raise ValueError("offseason must be a mapping")
    block = None if off is None else off.get("draft")
    if block is None:
        return {"weight": 0.0, "display_only": True, "chart": draft.CHART, "winsor": None, "decay": decay}
    if not isinstance(block, dict):
        raise ValueError("offseason.draft must be a mapping")
    w = block.get("weight", 0.0)
    if not _finite_number(w):
        raise ValueError(f"offseason.draft.weight must be a finite number, got {w!r}")
    win = block.get("winsor")
    if win is not None:
        if (not isinstance(win, list) or len(win) != 2 or not all(_finite_number(v) for v in win)
                or not win[0] < win[1]):
            raise ValueError(f"offseason.draft.winsor must be [lo, hi] finite numbers with lo < hi, got {win!r}")
        win = (float(win[0]), float(win[1]))
    dname = block.get("decay", DECAY_NAME)
    if dname != DECAY_NAME:
        raise ValueError(f"offseason.draft.decay must be {DECAY_NAME!r}, got {dname!r}")
    disp = block.get("display_only", float(w) == 0.0)
    if not isinstance(disp, bool):
        raise ValueError(f"offseason.draft.display_only must be true/false, got {disp!r}")
    return {"weight": float(w), "display_only": disp, "chart": str(block.get("chart", draft.CHART)),
            "winsor": win, "decay": decay}


def apply_offseason(feats: pl.DataFrame, draft_frame: pl.DataFrame | None, cfg: dict) -> pl.DataFrame:
    """Always add composite_inseason (= composite as given), draft_surplus (null without a draft row)
    and draft_z (0.0 when null). Only a nonzero cfg["weight"] adds contrib_draft = w * draft_z *
    decay(week) (weeks 0-3) and composite = composite_inseason + contrib_draft."""
    out = feats.with_columns(pl.col("composite").alias("composite_inseason"))
    if draft_frame is not None:
        dz = draft_frame.select(
            pl.col("season").cast(feats.schema["season"]), "franchise_id",
            pl.col("surplus").cast(pl.Float64).alias("draft_surplus"),
            pl.col("draft_z").cast(pl.Float64),
        )
        out = out.join(dz, on=["season", "franchise_id"], how="left")
    else:
        out = out.with_columns(pl.lit(None, dtype=pl.Float64).alias("draft_surplus"),
                               pl.lit(None, dtype=pl.Float64).alias("draft_z"))
    out = out.with_columns(pl.col("draft_z").fill_null(0.0))
    w = float(cfg.get("weight", 0.0))
    if w == 0.0:
        return out
    dec = pl.max_horizontal(pl.lit(0.0), 1.0 - pl.col("week").cast(pl.Float64) / draft.DECAY_WEEKS)
    return out.with_columns((pl.lit(w) * pl.col("draft_z") * dec).alias("contrib_draft")).with_columns(
        (pl.col("composite_inseason") + pl.col("contrib_draft")).alias("composite")
    )

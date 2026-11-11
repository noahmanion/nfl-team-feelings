"""Feel-good score (D-01) and mood labels (D-03) with hysteresis (D-04); ranks and deltas (D-05).

score = mid-rank percentile of a team's Elo among ALL week-0 + regular-season team-weeks 1999->now.
Labels/emoji live here only and are emitted in meta.json; the site never hardcodes them.
"""

import numpy as np
import polars as pl

from fgs.season_config import reg_weeks

BANDS: list[dict] = [  # low -> high; emitted as meta.bands (with an inclusive max added)
    {"min": 0, "label": "Witness protection", "emoji": "🕶️"},
    {"min": 5, "label": "Refreshing mock drafts", "emoji": "🔄"},
    {"min": 20, "label": "Checking the draft order", "emoji": "📋"},
    {"min": 40, "label": "It’s fine. Everything’s fine.", "emoji": "🔥"},
    {"min": 60, "label": "Cautiously smug", "emoji": "😏"},
    {"min": 80, "label": "Buying the jersey", "emoji": "🎽"},
    {"min": 95, "label": "Planning the parade", "emoji": "🎉"},
]
HYSTERESIS = 2
THRESHOLDS: list[int] = [b["min"] for b in BANDS]


def bands_meta() -> list[dict]:
    out = []
    for i, b in enumerate(BANDS):
        hi = BANDS[i + 1]["min"] - 1 if i + 1 < len(BANDS) else 100
        out.append({"min": b["min"], "max": hi, "label": b["label"], "emoji": b["emoji"]})
    return out


def percentile_scores(values: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """Mid-rank percentile 100*(less + 0.5*equal)/N, rounded to int and clipped to 0..100."""
    ref = np.sort(np.asarray(ref, dtype=float))
    values = np.asarray(values, dtype=float)
    lo = np.searchsorted(ref, values, "left")
    hi = np.searchsorted(ref, values, "right")
    return np.clip(np.rint(100.0 * (lo + 0.5 * (hi - lo)) / ref.size), 0, 100).astype(np.int64)


def band_of(score: int) -> int:
    return int(np.searchsorted(THRESHOLDS, score, "right") - 1)


def hysteresis(scores: list[int], buf: int = HYSTERESIS) -> list[int]:
    """Band index per week for ONE team-season, chronological (week 0 first = raw band).

    Symmetric rule (D-04): scores are integers, so the edge between band k-1 and band k lies
    between T[k]-1 and T[k]. The label changes only once the score is at least `buf` scores
    deep into the new band, in either direction:
      - up into band k:      score >= T[k] + buf - 1   (buf=2, T=60: 61 or more)
      - down out of band k:  score <= T[k] - buf       (buf=2, T=60: 58 or less)
    The first `buf - 1` scores on each side of an edge (59 and 60 for T=60) keep the previous
    label. Multi-band jumps go to the furthest band whose edge is cleared.
    """
    t = THRESHOLDS
    out: list[int] = []
    prev: int | None = None
    for s in scores:
        b = band_of(s)
        if prev is None:
            prev = b
        elif b > prev:
            prev = max([k for k in range(prev + 1, b + 1) if s >= t[k] + buf - 1], default=prev)
        elif b < prev:
            new = prev
            for k in range(prev, b, -1):  # leaving band k downward across T[k]
                if s <= t[k] - buf:
                    new = k - 1
                else:
                    break
            prev = new
        out.append(prev)
    return out


def score_frame(snapshots: pl.DataFrame) -> pl.DataFrame:
    """Snapshots + score, rank, score_delta, rank_delta, band, label, emoji."""
    df = snapshots.with_columns(
        pl.col("season").map_elements(reg_weeks, return_dtype=pl.Int32).alias("_reg_weeks")
    )
    ref = df.filter(pl.col("week") <= pl.col("_reg_weeks"))["elo"].to_numpy()  # week 0 + REG only
    df = df.drop("_reg_weeks").with_columns(
        pl.Series("score", percentile_scores(df["elo"].to_numpy(), ref), dtype=pl.Int32)
    )

    # Rank by Elo (never by the integer score); ties by franchise id.
    df = df.sort(["season", "week", "elo", "franchise_id"], descending=[False, False, True, False])
    df = df.with_columns(pl.int_range(1, pl.len() + 1, dtype=pl.Int32).over(["season", "week"]).alias("rank"))

    grp = ["franchise_id", "season"]
    df = df.sort(["franchise_id", "season", "week"]).with_columns(
        (pl.col("score") - pl.col("score").shift(1).over(grp)).alias("score_delta"),
        (pl.col("rank").shift(1).over(grp) - pl.col("rank")).alias("rank_delta"),
    )

    bands: list[int] = []
    for _, part in df.group_by(grp, maintain_order=True):
        bands.extend(hysteresis(part["score"].to_list()))
    labels = [b["label"] for b in BANDS]
    emoji = [b["emoji"] for b in BANDS]
    return df.with_columns(
        pl.Series("band", bands, dtype=pl.Int32),
        pl.Series("label", [labels[b] for b in bands], dtype=pl.String),
        pl.Series("emoji", [emoji[b] for b in bands], dtype=pl.String),
    ).sort(["season", "week", "rank"])

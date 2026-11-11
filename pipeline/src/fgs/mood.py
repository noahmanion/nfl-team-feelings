"""Feel-good score (D-01) and mood labels (D-03) with hysteresis (D-04); ranks and deltas (D-05).

score = mid-rank percentile of a team's composite (sum of weight * z, see fgs.score) among the
week-0 + regular-season team-weeks of the frozen reference seasons (season_config.REF_SEASONS,
1999-2021). The reference never includes newer games, so a refresh can never move a past score.
Labels/emoji live here only and are emitted in meta.json; the site never hardcodes them.
"""

import numpy as np
import polars as pl

from fgs import season_config
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


def reference_values(
    df: pl.DataFrame, value: str = "composite", ref_seasons: tuple[int, int] | None = None
) -> np.ndarray:
    """The frozen percentile reference: `value` over rows with season in ref_seasons (inclusive)
    and week <= reg_weeks(season) (week 0 + REG). ref_seasons None -> season_config.REF_SEASONS,
    read at call time. Shared by score_frame and fgs.explain so they can never drift apart."""
    lo, hi = season_config.REF_SEASONS if ref_seasons is None else ref_seasons
    rw = df["season"].map_elements(reg_weeks, return_dtype=pl.Int32)
    ref = df.filter(pl.col("season").is_between(lo, hi) & (pl.col("week") <= rw))[value].to_numpy()
    if ref.size == 0:
        raise ValueError(f"empty percentile reference: no week-0/REG rows for seasons {lo}-{hi}")
    return ref


def score_frame(
    df: pl.DataFrame, value: str = "composite", ref_seasons: tuple[int, int] | None = None
) -> pl.DataFrame:
    """df + score, rank, score_delta, rank_delta, band, label, emoji, scored and ranked by `value`.

    Reference = `value` over rows with season in ref_seasons (inclusive) and week <= reg_weeks
    (week 0 + REG). ref_seasons None -> season_config.REF_SEASONS, read at call time.
    """
    ref = reference_values(df, value, ref_seasons)
    df = df.with_columns(
        pl.Series("score", percentile_scores(df[value].to_numpy(), ref), dtype=pl.Int32)
    )

    # Rank by the underlying value (never by the integer score); ties by franchise id.
    df = df.sort(["season", "week", value, "franchise_id"], descending=[False, False, True, False])
    df = df.with_columns(pl.int_range(1, pl.len() + 1, dtype=pl.Int32).over(["season", "week"]).alias("rank"))

    grp = ["franchise_id", "season"]
    df = df.sort(["franchise_id", "season", "week"]).with_columns(
        (pl.col("score") - pl.col("score").shift(1).over(grp)).alias("score_delta"),
        (pl.col("rank").shift(1).over(grp) - pl.col("rank")).alias("rank_delta"),
    )

    # Hysteresis per team-season, carried with its (franchise, season, week) keys and joined back,
    # so the result never depends on df's row order.
    keyed = (
        df.select(grp + ["week", "score"])
        .group_by(grp)
        .agg(pl.col("week").sort_by("week"), pl.col("score").sort_by("week"))
        .with_columns(
            pl.col("score").map_elements(hysteresis, return_dtype=pl.List(pl.Int32)).alias("band")
        )
        .drop("score")
        .explode(["week", "band"])
    )
    band_info = pl.DataFrame(
        {"band": range(len(BANDS)), "label": [b["label"] for b in BANDS], "emoji": [b["emoji"] for b in BANDS]},
        schema={"band": pl.Int32, "label": pl.String, "emoji": pl.String},
    )
    out = df.join(keyed, on=grp + ["week"], how="left", validate="1:1").join(
        band_info, on="band", how="left", validate="m:1"
    )
    assert out["band"].null_count() == 0 and out.height == df.height, "hysteresis band missing for some rows"
    return out.sort(["season", "week", "rank"])

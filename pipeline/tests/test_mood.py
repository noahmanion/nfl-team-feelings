"""Mood score: percentile, bands, hysteresis, ranks and deltas (D-01, D-03, D-04, D-05)."""

import numpy as np
import polars as pl
import pytest

from fgs.mood import BANDS, HYSTERESIS, band_of, bands_meta, hysteresis, percentile_scores, score_frame
from fgs.paths import DERIVED_DIR


# --- percentile ------------------------------------------------------------------------------

def test_percentile_mid_rank_and_bounds():
    ref = np.array([1.0, 2.0, 3.0, 4.0])
    out = percentile_scores(np.array([0.0, 5.0, 2.0, 2.5]), ref)
    assert out.tolist() == [0, 100, 38, 50]  # 2.0: (1 + 0.5)/4 = 37.5 -> rint 38
    assert out.dtype.kind == "i"


def test_percentile_ties_get_equal_scores():
    ref = np.array([1.0, 2.0, 2.0, 2.0, 3.0])
    out = percentile_scores(np.array([2.0, 2.0]), ref)
    assert out[0] == out[1] == 50


def test_percentile_clipped_0_100():
    ref = np.arange(1000, dtype=float)
    out = percentile_scores(np.array([-1e9, 1e9]), ref)
    assert out.tolist() == [0, 100]


# --- bands -----------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "score,band", [(0, 0), (4, 0), (5, 1), (19, 1), (20, 2), (40, 3), (59, 3), (60, 4), (94, 5), (95, 6), (100, 6)]
)
def test_band_of(score, band):
    assert band_of(score) == band


def test_bands_config():
    assert len(BANDS) == 7 and HYSTERESIS == 2
    meta = bands_meta()
    assert [b["min"] for b in meta] == [0, 5, 20, 40, 60, 80, 95]
    assert [b["max"] for b in meta] == [4, 19, 39, 59, 79, 94, 100]
    assert meta[3]["label"] == "It’s fine. Everything’s fine."


# --- hysteresis ------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "scores,bands",
    [
        ([58], [3]),
        ([58, 60], [3, 3]),       # 60 = 1st score in band 4: stays
        ([58, 61], [3, 4]),       # 61 = 2nd score in band 4: enters
        ([58, 61, 59], [3, 4, 4]),  # 59 = 1st score in band 3: stays in 4
        ([58, 61, 58], [3, 4, 3]),  # 58 = 2nd score in band 3: leaves
        ([30, 96], [2, 6]),       # multi-band jump, top edge cleared (96 = 95+1)
        ([30, 95], [2, 5]),       # 95 < 95+1, but 80+1 cleared
        ([97, 3], [6, 0]),        # multi-band drop
        ([62, 4], [4, 1]),        # 4 > 5-2: stops in band 1
        ([62, 3], [4, 0]),        # 3 = 2nd score in band 0: drops all the way
    ],
)
def test_hysteresis(scores, bands):
    assert hysteresis(scores) == bands


@pytest.mark.parametrize("t", [5, 20, 40, 60, 80, 95])
def test_hysteresis_is_symmetric(t):
    """Same overshoot (2nd score inside the new band) is needed in both directions at every edge."""
    up = hysteresis([t - 2, t, t + 1])
    down = hysteresis([t + 1, t - 1, t - 2])
    lo, hi = band_of(t - 1), band_of(t)
    assert up == [lo, lo, hi] and down == [hi, hi, lo]


def test_hysteresis_oscillation():
    # 58 <-> 61 straddles T=60 by two scores on each side: the label follows it both ways.
    assert hysteresis([58, 61, 58, 61, 58]) == [3, 4, 3, 4, 3]
    # 59 <-> 60 sits inside the dead zone: the starting label holds.
    assert hysteresis([59, 60, 59, 60]) == [3, 3, 3, 3]
    assert hysteresis([60, 59, 60, 59]) == [4, 4, 4, 4]


def test_hysteresis_first_element_is_raw_band():
    assert hysteresis([61]) == [4]
    assert hysteresis([]) == []


# --- score_frame (synthetic) -----------------------------------------------------------------

def _snap(rows):
    return pl.DataFrame(
        [dict(season=s, week=w, franchise_id=f, elo=e, wins=0, losses=0, ties=0, win_pct=0.0) for s, w, f, e in rows],
        schema={"season": pl.Int32, "week": pl.Int32, "franchise_id": pl.String, "elo": pl.Float64,
                "wins": pl.Int32, "losses": pl.Int32, "ties": pl.Int32, "win_pct": pl.Float64},
    )


def _filler(season, week, n=100, lo=1300.0, hi=1700.0):
    # A large spread of other teams so the percentile scale is well defined.
    return [(season, week, f"T{i:03d}", lo + (hi - lo) * i / (n - 1)) for i in range(n)]


def test_score_frame_columns_and_types():
    out = score_frame(_snap(_filler(2023, 0, n=10)))
    for c in ("score", "rank", "score_delta", "rank_delta", "band", "label", "emoji"):
        assert c in out.columns
    assert out["score"].dtype.is_integer() and out["rank"].dtype.is_integer()


def test_week0_hysteresis_is_fresh():
    """Prior season ends in band 3 ('fine'); a week-0 score of 60-61 next season is band 4, no carry."""
    base = _filler(2023, 0) + _filler(2024, 0)
    # Find Elo values that score ~58 and ~61 against the reference.
    probe = score_frame(_snap(base))
    ref = np.sort(probe["elo"].to_numpy())

    def elo_for(target):
        for e in np.linspace(1300, 1700, 4001):
            if percentile_scores(np.array([e]), ref)[0] == target:
                return float(e)
        raise AssertionError(target)

    rows = base + [(2023, 0, "ZZZ", elo_for(58)), (2024, 0, "ZZZ", elo_for(60))]
    out = score_frame(_snap(rows)).filter(pl.col("franchise_id") == "ZZZ").sort("season")
    assert out["score"].to_list()[0] in (57, 58, 59)
    s24 = out["score"].to_list()[1]
    assert s24 == 60  # in the dead zone above T=60: a carried-over band 3 would stick
    assert out["band"].to_list() == [3, 4]
    assert out["label"].to_list()[1] == BANDS[4]["label"]


def test_reference_excludes_playoff_weeks():
    rows = _filler(2023, 0, n=20) + _filler(2023, 17, n=20)
    a = score_frame(_snap(rows))
    b = score_frame(_snap(rows + [(2023, 18, "T000", 9999.0)]))  # reg_weeks(2023) == 18: a REG row
    c = score_frame(_snap(rows + [(2023, 19, "T000", 9999.0)]))  # week 19 = Wild Card: not in the reference
    key = ["season", "week", "franchise_id"]
    assert not a.join(b, on=key).filter(pl.col("score") != pl.col("score_right")).is_empty()  # REG row counts
    same = a.join(c, on=key)
    assert same.filter(pl.col("score") != pl.col("score_right")).is_empty()
    assert c.filter(pl.col("week") == 19)["score"].item() == 100


def test_rank_ties_broken_by_franchise_and_deltas():
    rows = [
        (2023, 0, "BBB", 1500.0), (2023, 0, "AAA", 1500.0), (2023, 0, "CCC", 1400.0),
        (2023, 1, "BBB", 1450.0), (2023, 1, "AAA", 1550.0), (2023, 1, "CCC", 1500.0),
    ]
    out = score_frame(_snap(rows)).sort(["week", "rank"])
    w0 = out.filter(pl.col("week") == 0)
    assert w0["franchise_id"].to_list() == ["AAA", "BBB", "CCC"]
    assert w0["rank"].to_list() == [1, 2, 3]
    assert w0["score_delta"].null_count() == 3 and w0["rank_delta"].null_count() == 3
    w1 = out.filter(pl.col("week") == 1)
    assert w1["franchise_id"].to_list() == ["AAA", "CCC", "BBB"]
    rd = dict(zip(w1["franchise_id"], w1["rank_delta"]))
    assert rd == {"AAA": 0, "CCC": 1, "BBB": -1}
    s0 = dict(zip(w0["franchise_id"], w0["score"]))
    sd = dict(zip(w1["franchise_id"], w1["score_delta"]))
    s1 = dict(zip(w1["franchise_id"], w1["score"]))
    assert all(sd[f] == s1[f] - s0[f] for f in s0)


# --- real data sanity ------------------------------------------------------------------------

@pytest.fixture
def real_snapshots():
    path = DERIVED_DIR / "elo_snapshots.parquet"
    if not path.exists():
        pytest.skip("no derived snapshots; run `uv run fgs build` first")
    return pl.read_parquet(path)


def test_real_hysteresis_reduces_label_changes(real_snapshots):
    out = score_frame(real_snapshots).sort(["franchise_id", "season", "week"])
    raw = out.with_columns(pl.col("score").map_elements(band_of, return_dtype=pl.Int64).alias("raw_band"))
    grp = ["franchise_id", "season"]
    changes = raw.select(
        (pl.col("band") != pl.col("band").shift(1).over(grp)).sum().alias("label"),
        (pl.col("raw_band") != pl.col("raw_band").shift(1).over(grp)).sum().alias("raw"),
    ).row(0, named=True)
    assert 0 < changes["label"] < changes["raw"]
    assert out["score"].min() >= 0 and out["score"].max() <= 100

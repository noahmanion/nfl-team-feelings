"""fgs.explain: points attribution + blurb phrasebook (pure, no cache)."""

import numpy as np
import polars as pl
import pytest

from fgs import explain
from fgs.explain import FADE, PHRASES, add_points, baseline, blurb, largest_remainder, slope, smooth_map

FACTORS7 = ["elo", "season_record", "last16", "mov", "sow", "streak", "luck"]


# --- largest_remainder ---------------------------------------------------------------------

def test_largest_remainder_exact_sum_random():
    rng = np.random.default_rng(7)
    for _ in range(200):
        n = int(rng.integers(1, 8))
        real = rng.normal(0, 15, n)
        total = int(rng.integers(-50, 51))
        out = largest_remainder(real, total)
        assert out.dtype == np.int64 and int(out.sum()) == total
        assert np.array_equal(out, largest_remainder(real.copy(), total))  # deterministic


def test_largest_remainder_all_zero():
    assert largest_remainder(np.zeros(3), 0).tolist() == [0, 0, 0]
    out = largest_remainder(np.zeros(3), 3)
    assert int(out.sum()) == 3 and out.tolist() == [1, 1, 1]
    assert int(largest_remainder(np.zeros(4), -2).sum()) == -2


def test_largest_remainder_ties_go_to_factor_order():
    assert largest_remainder(np.array([0.5, 0.5]), 1).tolist() == [1, 0]


# --- slope ---------------------------------------------------------------------------------

REF = np.random.default_rng(1).normal(0, 1, 5000)


def test_slope_at_zero_finite_and_positive():
    xs, qs = smooth_map(REF)
    d0 = explain._slope_at_zero(xs, qs)
    s = slope(np.array([0.0, 1e-9, -1e-9]), xs, qs)
    assert np.all(np.isfinite(s)) and np.all(s > 0)
    assert np.allclose(s, d0)
    assert np.all(slope(np.linspace(-3, 3, 41), xs, qs) > 0)


def test_slope_steps_outward_over_coincident_knots():
    ref = np.array([-1.0] + [0.0] * 200 + [1.0])  # many knots sit exactly on 0
    xs, qs = smooth_map(ref)
    d0 = explain._slope_at_zero(xs, qs)
    assert np.isfinite(d0) and d0 > 0


# --- add_points ----------------------------------------------------------------------------

def _frame(ref):
    contribs_a = np.array([1.2, -0.8, 3.0, 0.0, 0.4, 2.5])
    contribs_b = np.array([0.3, -0.5, -3.0, 0.0, -0.1, -0.6])
    comp = contribs_a + contribs_b
    comp[2] = 1e-9  # composite ~ 0 but offsetting contribs
    from fgs.mood import percentile_scores

    return pl.DataFrame({
        "composite": comp, "contrib_a": contribs_a, "contrib_b": contribs_b,
        "score": percentile_scores(comp, ref).astype(np.int32),
    })


def test_add_points_sums_and_signs():
    df = add_points(_frame(REF), ["a", "b"], REF)
    base = baseline(REF)
    xs, qs = smooth_map(REF)
    real = np.column_stack([df["contrib_a"], df["contrib_b"]]) * slope(df["composite"].to_numpy(), xs, qs)[:, None]
    pts = np.column_stack([df["pts_a"], df["pts_b"]])
    assert df["pts_a"].dtype == pl.Int64
    assert (pts.sum(1) == df["score"].to_numpy() - base).all()
    assert not (pts[2] == 0).all()  # composite ~ 0, contribs +3/-3: bars still show
    big = np.abs(real) >= 1.5
    assert not ((np.sign(pts) * np.sign(real) < 0) & big).any()


def test_baseline_is_score_of_zero():
    assert baseline(REF) == int(explain.mood.percentile_scores(np.array([0.0]), REF)[0])
    assert baseline(np.array([1.0, 2.0, 3.0])) == 0


# --- blurb ---------------------------------------------------------------------------------

def test_phrases_cover_all_factors():
    assert set(PHRASES) == {(f, d) for f in FACTORS7 for d in ("hi", "lo")}
    assert set(FADE) == {"hi", "lo"}


def _row(**kw):
    r = {"wins": 7, "losses": 1, "ties": 0, "streak": 0}
    for f in FACTORS7:
        r[f"z_{f}"] = 0.0
        r[f"pts_{f}"] = 0
    r.update(kw)
    return r


def test_blurb_and_vs_but():
    r = _row(z_elo=1.5, pts_elo=30, z_mov=1.0, pts_mov=12)
    assert blurb(r, FACTORS7, "Bills", 9) == \
        "The Bills are one of the best teams in football, and have been blowing teams out."
    r = _row(z_elo=1.5, pts_elo=30, z_sow=1.0, pts_sow=-12)
    out = blurb(r, FACTORS7, "Bills", 9)
    assert ", but have a record that runs ahead of their margins (that tends to fade)." in out


def test_blurb_week0_lead_and_record_skipped():
    r = _row(z_elo=1.0, pts_elo=15, z_season_record=1.0, pts_season_record=40)
    out = blurb(r, FACTORS7, "Seahawks", 0)
    assert out == "Preseason, carrying last season's form: the Seahawks are a good team on paper."


def test_blurb_record_phrase():
    r = _row(z_season_record=1.0, pts_season_record=12)
    assert blurb(r, FACTORS7, "Lions", 9) == "The Lions are 7-1."
    r = _row(z_season_record=-1.0, pts_season_record=-12, wins=1, losses=6, ties=1)
    assert blurb(r, FACTORS7, "Lions", 9) == "The Lions are just 1-6-1."


def test_blurb_streak_needs_two():
    r = _row(streak=1, z_streak=1.0, pts_streak=-30, z_luck=-1.0, pts_luck=-5)
    out = blurb(r, FACTORS7, "Bears", 5)
    assert "straight" not in out and "close games" in out
    r = _row(streak=-4, z_streak=-1.0, pts_streak=12)
    assert blurb(r, FACTORS7, "Bears", 5) == "The Bears are stuck in a 4-game skid (that tends to even out)."


def test_blurb_fade_suffix_when_points_negative_but_raw_high():
    r = _row(z_last16=1.2, pts_last16=-6)
    assert blurb(r, FACTORS7, "Bills", 9) == "The Bills have a winning last 16 games (that tends to fade)."


def test_blurb_none_case():
    assert blurb(_row(), FACTORS7, "Jets", 3) == "The Jets are about as average as it gets right now."
    assert blurb(_row(), FACTORS7, "Jets", 0) == \
        "Preseason, carrying last season's form: the Jets are about as average as it gets right now."


def test_blurb_ties_follow_factor_order_and_unknown_factor_skipped():
    r = _row(z_elo=1.0, pts_elo=8, z_mov=1.0, pts_mov=8)
    assert blurb(r, FACTORS7, "Rams", 4).startswith("The Rams are a good team on paper, and")
    r = {**r, "z_mystery": 2.0, "pts_mystery": 50}
    assert "mystery" not in blurb(r, ["mystery"] + FACTORS7, "Rams", 4)


@pytest.mark.parametrize("seed", range(20))
def test_blurb_random_rows_well_formed(seed):
    rng = np.random.default_rng(seed)
    r = _row(streak=int(rng.integers(-3, 4)))
    for f in FACTORS7:
        r[f"z_{f}"] = float(rng.choice([-1.0, 0.0, 1.0]))
        r[f"pts_{f}"] = int(rng.integers(-25, 26))
    out = blurb(r, FACTORS7, "Bills", int(rng.integers(0, 3)))
    assert out.endswith(".") and "0 straight" not in out and "1 straight" not in out

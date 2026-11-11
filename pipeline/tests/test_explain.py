"""fgs.explain: points attribution + blurb phrasebook (pure, no cache)."""

import numpy as np
import polars as pl
import pytest

from fgs import explain
from fgs.explain import FADE, PHRASES, add_points, baseline, blurb, largest_remainder, slope, smooth_map

FACTORS7 = ["elo", "season_record", "last16", "mov", "sow", "streak", "luck", "epa_traj", "qb_trend", "vs_exp", "po_trend"]


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


def test_largest_remainder_never_flips_sign():
    # nearly cancelling contributions with a big residual: plain spreading would give [-1, -3, -1]
    out = largest_remainder(np.array([1.0, -1.0, 0.5]), -5)
    assert out.tolist() == [0, -5, 0]
    rng = np.random.default_rng(11)
    for _ in range(500):
        n = int(rng.integers(2, 8))
        real = rng.normal(0, 5, n)
        total = int(rng.integers(-30, 31))
        out = largest_remainder(real, total)
        assert int(out.sum()) == total
        if (real > 0).any() and (real < 0).any():  # both signs available: no flips needed
            assert not (out * real < 0).any(), (real, total, out)


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
    assert ", but have been winning more than their schedule would predict (that tends to fade)." in out


def test_sow_phrases_never_talk_about_margins():
    # sow measures results vs schedule, not record vs margins: a "margins" phrase would contradict mov
    for d in ("hi", "lo"):
        for text in PHRASES[("sow", d)]:
            assert "margin" not in text and ("schedule" in text or "opponents" in text), text


@pytest.mark.parametrize("mov_d", ["hi", "lo"])
@pytest.mark.parametrize("sow_d", ["hi", "lo"])
@pytest.mark.parametrize("sow_pts", [-12, -3, 3, 12])
def test_mov_and_sow_blurbs_do_not_contradict(mov_d, sow_d, sow_pts):
    zm, zs = (1.0 if mov_d == "hi" else -1.0), (1.0 if sow_d == "hi" else -1.0)
    out = blurb(_row(z_mov=zm, pts_mov=20 * int(zm), z_sow=zs, pts_sow=sow_pts), FACTORS7, "Bears", 9)
    assert out.count("margin") <= 1, out  # only mov may speak about margins


def test_blurb_week0_lead_and_record_skipped():
    r = _row(z_elo=1.0, pts_elo=15, z_season_record=1.0, pts_season_record=40)
    out = blurb(r, FACTORS7, "Seahawks", 0)
    assert out == "Preseason, carrying last season's form: the Seahawks are a good team on paper."


def test_blurb_week0_without_history():
    r = _row(z_elo=1.0, pts_elo=15)
    assert blurb(r, FACTORS7, "Cardinals", 0, "fresh") == \
        "Preseason: no history yet, so the Cardinals start even with everyone else."
    r = _row(z_elo=-3.0, pts_elo=-40)
    assert blurb(r, FACTORS7, "Texans", 0, "expansion") == \
        "Preseason: the Texans are an expansion team starting below average."
    # only week 0 is special
    assert blurb(r, FACTORS7, "Texans", 1, "expansion").startswith("The Texans are one of the worst")


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
    assert blurb(r, FACTORS7, "Bears", 5) == "The Bears have lost 4 in a row (that tends to even out)."


def test_blurb_streak_at_cap_says_plus():
    r = _row(streak=-8, z_streak=-1.0, pts_streak=-12)
    assert blurb(r, FACTORS7, "Bears", 12) == "The Bears have lost 8+ in a row."
    r = _row(streak=8, z_streak=1.0, pts_streak=3)
    assert blurb(r, FACTORS7, "Bears", 12) == "The Bears have won 8+ straight."


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


# --- Phase 7: draft text + preseason draft lead ---------------------------------------------

def _values() -> np.ndarray:
    """A decreasing chart: 60 at pick 1, 16 at pick 20, 0.5 at pick 262."""
    v = np.full(263, np.nan)
    v[1:] = np.interp(np.arange(1, 263), [1, 20, 262], [60.0, 16.0, 0.5])
    return v


def test_draft_text_forms():
    from fgs import draft

    v = _values()
    p = draft.equiv_pick(16.2, v)
    noun = draft.pick_noun(p)
    assert explain.draft_text(16.2, v, False) == \
        f"Draft haul: +16 over their original slots (about one extra {noun}) — doesn't move the score."
    out = explain.draft_text(-29.0, v, False)
    assert out.startswith("Draft haul: −29 under their original slots (about one ")
    assert out.endswith(" given up) — doesn't move the score.")
    assert explain.draft_text(0.2, v, False) == \
        "Draft haul: about even with their original slots — doesn't move the score."
    assert explain.draft_text(-0.4, v, True) == "Draft haul: about even with their original slots."
    live = explain.draft_text(16.2, v, True)
    assert live.endswith("pick).") and "doesn't move" not in live
    assert explain.draft_text(None, v, False) is None


def test_draft_text_half_rounds_away_from_zero():
    """CR-02: round() is banker's (round(0.5) == 0), which shipped "+0 over" / "−0 under"."""
    v = _values()
    for s in (0.5, -0.5, 0.49, -0.49, 2.5, -2.5, 1.5):
        t = explain.draft_text(s, v, False)
        assert "+0 " not in t and "\u22120 " not in t, (s, t)
    assert explain.draft_text(0.5, v, False).startswith("Draft haul: +1 over")
    assert explain.draft_text(-0.5, v, False).startswith("Draft haul: \u22121 under")
    assert explain.draft_text(2.5, v, False).startswith("Draft haul: +3 over")
    assert explain.draft_text(0.49, v, False).startswith("Draft haul: about even")


def test_draft_text_beyond_a_top_pick():
    """IN-02: a haul bigger than the #1 pick (60 here) doesn't read "about one extra #1 overall pick"."""
    v = _values()
    assert explain.draft_text(80.0, v, False) == \
        "Draft haul: +80 over their original slots (more than a #1 overall pick) — doesn't move the score."
    assert explain.draft_text(-70.0, v, True) == \
        "Draft haul: \u221270 under their original slots (more than a #1 overall pick given up)."
    assert "about one extra #1 overall pick" in explain.draft_text(62.0, v, False)  # within 10%: still "about"


def test_draft_text_mid_first_round_example():
    """The plan's example: +16 ~ one extra mid-first-round pick (chart value 16.2 at picks 16..24)."""
    from fgs import draft

    v = _values()
    assert 16 <= draft.equiv_pick(16.2, v) <= 24
    assert explain.draft_text(16.2, v, False) == \
        "Draft haul: +16 over their original slots (about one extra mid-first-round pick) — doesn't move the score."


def test_blurb_week0_draft_leads():
    r = _row(z_elo=1.0, pts_elo=15)
    plus = "Preseason, carrying last season's form plus extra draft capital: the Seahawks are a good team on paper."
    minus = "Preseason, carrying last season's form minus some draft capital: the Seahawks are a good team on paper."
    plain = "Preseason, carrying last season's form: the Seahawks are a good team on paper."
    assert blurb({**r, "draft_surplus": 9.0}, FACTORS7, "Seahawks", 0, draft_threshold=9.0) == plus
    assert blurb({**r, "draft_surplus": -12.0}, FACTORS7, "Seahawks", 0, draft_threshold=9.0) == minus
    assert blurb({**r, "draft_surplus": 8.9}, FACTORS7, "Seahawks", 0, draft_threshold=9.0) == plain
    assert blurb({**r, "draft_surplus": None}, FACTORS7, "Seahawks", 0, draft_threshold=9.0) == plain
    assert blurb({**r, "draft_surplus": 30.0}, FACTORS7, "Seahawks", 0) == plain  # no threshold given
    # other kinds and other weeks are untouched
    assert blurb({**r, "draft_surplus": 30.0}, FACTORS7, "Cardinals", 0, "fresh", draft_threshold=9.0) == \
        "Preseason: no history yet, so the Cardinals start even with everyone else."
    assert blurb({**r, "draft_surplus": 30.0}, FACTORS7, "Texans", 0, "expansion", draft_threshold=9.0) == \
        "Preseason: the Texans are an expansion team starting below average."
    assert blurb({**r, "draft_surplus": 30.0}, FACTORS7, "Seahawks", 1, draft_threshold=9.0) == \
        "The Seahawks are a good team on paper."


def test_no_draft_quality_claims():
    from pathlib import Path

    src = (Path(explain.__file__)).read_text()
    for bad in ("great draft", "drafted well"):
        assert bad not in src

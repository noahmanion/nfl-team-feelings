"""Score-point attribution and the plain-English one-liner (SITE-02, INSIGHT-05).

Pure: no I/O. Works for any factor set: everything is keyed by the factor names it is given.

Points: for a row with composite c and integer score S, T = S - baseline (baseline = score(0) on
the frozen reference). Each factor's real-valued share is contrib_f * slope(c), where slope is
the average slope of the *smoothed* frozen percentile map from 0 to c. Largest-remainder rounding
then turns those shares into integers that sum to T exactly. Points depend only on the row's own
contributions and the frozen reference, so they are as leak-free as the score itself.

Blurb: the top 2 factors by |points|, phrased by the factor's raw direction (sign of z) rather
than the sign of its points, plus a "fade" suffix when the two disagree (negative-weight factors).
"""

import numpy as np
import polars as pl

from fgs import draft, mood
from fgs.features import STREAK_CAP

# --- attribution ---------------------------------------------------------------------------


def smooth_map(ref: np.ndarray, knots: int = 101) -> tuple[np.ndarray, np.ndarray]:
    """Monotone piecewise-linear percentile map through the reference's 0..100 quantile knots."""
    qs = np.linspace(0.0, 100.0, knots)
    xs = np.quantile(np.asarray(ref, dtype=float), qs / 100.0)
    return xs, qs


def _slope_at_zero(xs: np.ndarray, qs: np.ndarray) -> float:
    """Derivative of the smoothed map at 0, from the knot pair straddling 0. Steps outward while
    the two knots coincide, so the result is always finite and > 0."""
    n = len(xs)
    i = int(np.searchsorted(xs, 0.0))
    lo, hi = min(max(i - 1, 0), n - 2), min(max(i, 1), n - 1)
    while xs[hi] - xs[lo] <= 0:
        if hi < n - 1:
            hi += 1
        elif lo > 0:
            lo -= 1
        else:
            return 1.0  # constant reference: no slope information at all
    return float((qs[hi] - qs[lo]) / (xs[hi] - xs[lo]))


def slope(c, xs: np.ndarray, qs: np.ndarray) -> np.ndarray:
    """Average slope of the smoothed map from 0 to c (vectorized); derivative at 0 when |c| < 1e-6."""
    c = np.asarray(c, dtype=float)
    d0 = _slope_at_zero(xs, qs)
    p0 = np.interp(0.0, xs, qs)
    safe = np.where(np.abs(c) < 1e-6, 1.0, c)
    s = (np.interp(c, xs, qs) - p0) / safe
    return np.where(np.abs(c) < 1e-6, d0, s)


def _lr(real: np.ndarray, total: int) -> np.ndarray:
    """One largest-remainder pass (see largest_remainder)."""
    mag = np.abs(real)
    resid = total - real.sum()
    if mag.sum() > 0:
        real = real + resid * mag / mag.sum()
    else:
        real = real + resid / len(real)
    fl = np.floor(real)
    out = fl.astype(np.int64)
    k = total - int(out.sum())
    k = min(max(k, 0), len(real))  # float noise can only push this by one at the ends
    out[np.argsort(-(real - fl), kind="stable")[:k]] += 1
    return out


def largest_remainder(real: np.ndarray, total: int) -> np.ndarray:
    """Integers summing exactly to `total`. The residual (total - sum(real)) is first spread in
    proportion to |real| (evenly if all are 0), then floor + one extra unit to the k largest
    fractional parts. Stable argsort: ties go to the earlier factor, so it is deterministic.

    No sign flips: when the residual would push a factor's integer to the opposite sign of its
    real share (contributions nearly cancelling), that factor is rounded toward zero (0) and the
    pass is re-run over the others. Repeats until no factor flips."""
    real = np.asarray(real, dtype=float)
    total = int(total)
    n = len(real)
    out = _lr(real, total)
    fixed = np.zeros(n, dtype=bool)
    for _ in range(n):
        flip = ~fixed & (out * real < 0)
        if not flip.any():
            break
        fixed |= flip
        out[fixed] = 0
        free = ~fixed
        if not free.any():
            break
        out[free] = _lr(real[free], total)
    diff = total - int(out.sum())  # belt and braces: never ship a row that doesn't add up
    if diff:
        mag = np.abs(real)
        same = np.sign(real) == np.sign(diff)
        out[int(np.argmax(np.where(same, mag, -1.0))) if same.any() else int(np.argmax(mag))] += diff
    return out


def baseline(ref: np.ndarray) -> int:
    """score(0): the displayed score of a perfectly average team on the frozen reference."""
    return int(mood.percentile_scores(np.array([0.0]), ref)[0])


def add_points(scored: pl.DataFrame, factor_keys: list[str], ref: np.ndarray) -> pl.DataFrame:
    """scored + Int64 pts_{f} per factor; each row's points sum to score - baseline exactly.

    Uses the unrounded contrib_* columns (never the 2-dp exported ones)."""
    factor_keys = list(factor_keys)
    xs, qs = smooth_map(ref)
    base = baseline(ref)
    c = scored["composite"].to_numpy().astype(float)
    total = scored["score"].to_numpy().astype(np.int64) - base
    contribs = np.column_stack([scored[f"contrib_{f}"].to_numpy().astype(float) for f in factor_keys]) \
        if factor_keys else np.zeros((scored.height, 0))
    real = contribs * slope(c, xs, qs)[:, None]
    pts = np.zeros_like(real, dtype=np.int64)
    if factor_keys:
        for i in range(scored.height):
            pts[i] = largest_remainder(real[i], int(total[i]))
    return scored.with_columns(
        pl.Series(f"pts_{f}", pts[:, j], dtype=pl.Int64) for j, f in enumerate(factor_keys)
    )


# --- blurb ---------------------------------------------------------------------------------

# Fact phrases keyed by (factor, raw direction = sign(z)) -> (strong, mild). Plural verbs: every
# team_nick is plural ("Bills", "49ers"). {rec} = W-L or W-L-T, {k} = |raw streak| ("8+" at the
# feature cap, since the stored streak is clipped and the true run may be longer).
PHRASES: dict[tuple[str, str], tuple[str, str]] = {
    ("elo", "hi"): ("are one of the best teams in football", "are a good team on paper"),
    ("elo", "lo"): ("are one of the worst teams in football", "are a below-average team on paper"),
    ("season_record", "hi"): ("are {rec}", "are {rec}"),
    ("season_record", "lo"): ("are just {rec}", "are {rec}"),
    ("last16", "hi"): ("have won a lot over their last 16 games", "have a winning last 16 games"),
    ("last16", "lo"): ("have lost a lot over their last 16 games", "have a losing last 16 games"),
    ("mov", "hi"): ("have been blowing teams out", "have been winning by comfortable margins"),
    ("mov", "lo"): ("have been getting blown out", "have been losing by wide margins"),
    # sow = results vs what a league-average team would get against the same opponents. It says
    # nothing about margins, so its phrases must not either (they would contradict mov).
    ("sow", "hi"): ("have been winning more than their schedule would predict", "have results a bit better than their schedule"),
    ("sow", "lo"): ("have come up short against beatable opponents", "have results a bit worse than their schedule"),
    ("streak", "hi"): ("have won {k} straight", "have won {k} straight"),
    ("streak", "lo"): ("have lost {k} in a row", "have lost {k} straight"),
    ("luck", "hi"): ("have won a lot of coin-flip games", "have won more than their share of close games"),
    ("luck", "lo"): ("have lost a lot of coin-flip games", "have lost more than their share of close games"),
    ("epa_traj", "hi"): ("have been trending up in efficiency", "have been a bit more efficient lately"),
    ("epa_traj", "lo"): ("have been trending down in efficiency", "have been a bit less efficient lately"),
    ("qb_trend", "hi"): ("are getting great play from their quarterback", "are getting solid quarterback play"),
    ("qb_trend", "lo"): ("are getting poor play from their quarterback", "are getting shaky quarterback play"),
    ("vs_exp", "hi"): ("are beating preseason expectations", "are a bit ahead of preseason expectations"),
    ("vs_exp", "lo"): ("are falling short of preseason expectations", "are a bit behind preseason expectations"),
    ("po_trend", "hi"): ("have seen their playoff odds climb", "have seen their playoff odds tick up"),
    ("po_trend", "lo"): ("have seen their playoff odds slide", "have seen their playoff odds dip"),
}
# Appended when the points point the other way to the fact (a negative-weight factor).
FADE = {"hi": " (that tends to fade)", "lo": " (that tends to even out)"}
STRONG = {"elo": 20}  # Elo dominates |points|, so its strong tier needs more
STRONG_DEFAULT = 10
PRESEASON = "Preseason, carrying last season's form: "
# Week-0 carry leads when the team's draft capital over its original slots is at least the chart
# value of pick 64 (either way); the export passes that value as draft_threshold ONLY when the draft
# term is live (nonzero weight). Otherwise the score carries no draft capital and the lead must not
# say it does: the draft appears only in draft_text's "doesn't move the score" line.
PRESEASON_DRAFT_PLUS = "Preseason, carrying last season's form plus extra draft capital: "
PRESEASON_DRAFT_MINUS = "Preseason, carrying last season's form minus some draft capital: "
# Week-0 kinds: "carry" (has a prior season in the data), "fresh" (first season in the data: no
# history for anyone), "expansion" (first season of a seeded expansion/re-entry franchise).
PRESEASON_KINDS = ("carry", "fresh", "expansion")


def _record(row: dict) -> str:
    w, l, t = int(row["wins"]), int(row["losses"]), int(row.get("ties") or 0)
    return f"{w}-{l}-{t}" if t else f"{w}-{l}"


def _phrase(row: dict, f: str, pts: int, week: int) -> str | None:
    z = row.get(f"z_{f}")
    if pts == 0 or z is None or z == 0 or (f, "hi") not in PHRASES:
        return None
    if f == "season_record" and week == 0:
        return None
    k = "0"
    if f == "streak":
        raw = row.get("streak")
        if raw is None or abs(int(raw)) < 2:
            return None
        n = abs(int(raw))
        k = f"{STREAK_CAP}+" if n >= STREAK_CAP else str(n)
    d = "hi" if z > 0 else "lo"
    strong, mild = PHRASES[(f, d)]
    text = (strong if abs(pts) >= STRONG.get(f, STRONG_DEFAULT) else mild).format(rec=_record(row), k=k)
    if (pts > 0) != (d == "hi"):
        text += FADE[d]
    return text


def _preseason_lead(row: dict, draft_threshold: float | None) -> str:
    s = row.get("draft_surplus")
    if draft_threshold is not None and s is not None and abs(float(s)) >= draft_threshold:
        return PRESEASON_DRAFT_PLUS if s > 0 else PRESEASON_DRAFT_MINUS
    return PRESEASON


def blurb(row: dict, factor_keys: list[str], nick: str, week: int, preseason: str = "carry", *,
          draft_threshold: float | None = None) -> str:
    """One deterministic plain-English sentence naming the row's top-2 drivers.

    At week 0, `preseason` says whether there is last-season form to talk about (see PRESEASON_KINDS).
    A "carry" week-0 lead mentions draft capital when |row["draft_surplus"]| >= draft_threshold."""
    if week == 0 and preseason == "expansion":
        return f"Preseason: the {nick} are an expansion team starting below average."
    if week == 0 and preseason == "fresh":
        return f"Preseason: no history yet, so the {nick} start even with everyone else."
    order = sorted(range(len(factor_keys)), key=lambda i: (-abs(int(row[f"pts_{factor_keys[i]}"])), i))
    picks: list[tuple[str, int]] = []
    for i in order:
        f = factor_keys[i]
        pts = int(row[f"pts_{f}"])
        p = _phrase(row, f, pts, week)
        if p:
            picks.append((p, pts))
        if len(picks) == 2:
            break
    lead = f"{_preseason_lead(row, draft_threshold)}the {nick}" if week == 0 else f"The {nick}"
    if not picks:
        return f"{lead} are about as average as it gets right now."
    if len(picks) == 1:
        return f"{lead} {picks[0][0]}."
    conj = "and" if (picks[0][1] > 0) == (picks[1][1] > 0) else "but"
    return f"{lead} {picks[0][0]}, {conj} {picks[1][0]}."


# --- draft capital (Phase 7, display text) -------------------------------------------------
# Wording rule: it is capital over/under the ORIGINAL slots (trades), never a verdict on draft quality.


def draft_text(surplus: float | None, values: np.ndarray, moves_score: bool) -> str | None:
    """Plain-English draft line for a week-0 row; None when the surplus isn't derivable."""
    if surplus is None:
        return None
    s = float(surplus)
    tail = "." if moves_score else " — doesn't move the score."
    if draft.is_even(s):
        return f"Draft haul: about even with their original slots{tail}"
    n = draft.round_half_away(s)  # >= 1 here, so never "+0" / "−0"
    if draft.beyond_top_pick(s, values):  # "about one extra #1 overall pick" would understate it
        if s > 0:
            return f"Draft haul: +{n} over their original slots (more than a #1 overall pick){tail}"
        return f"Draft haul: \u2212{n} under their original slots (more than a #1 overall pick given up){tail}"
    noun = draft.pick_noun(draft.equiv_pick(s, values))
    if s > 0:
        return f"Draft haul: +{n} over their original slots (about one extra {noun}){tail}"
    return f"Draft haul: \u2212{n} under their original slots (about one {noun} given up){tail}"

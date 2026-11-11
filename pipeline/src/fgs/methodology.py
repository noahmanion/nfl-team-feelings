"""methodology.json: what the score is, its frozen weights, and the backtest evidence (SITE-07).

Built only from committed files (weights.yaml, FREEZE_RESULT.json, optional HOLDOUT_RESULT.json).
Never runs a backtest or a fit. Pure apart from load_evidence. Must not import the dev-only
evaluation harness (leakage firewall; see tests/test_leakage.py).
"""

import json

from fgs import paths, score, season_config

TARGET_TEXT = (
    "How a team does over its next 8 games: the average point margin, adjusted for how strong "
    "each opponent was and where the game was played."
)
HOLDOUT_PENDING = "The 2022–25 holdout is evaluated once, after the weights were frozen. It hasn’t run yet."

CANDIDATES = [
    {"key": "elo", "label": "Elo alone"},
    {"key": "season_wpct", "label": "Season win %"},
    {"key": "last16", "label": "Last 16 games"},
    {"key": "pd_pg", "label": "Point differential"},
    {"key": "composite", "label": "Feel-good score"},
    {"key": "spread", "label": "Vegas spread (market ceiling)", "brier_only": True},
]


def _span(a: int, b: int) -> str:
    return f"{a}–{str(b)[-2:]}"


def load_evidence() -> tuple[dict | None, dict | None, dict | None]:
    """(weights.yaml doc, FREEZE_RESULT dict | None, HOLDOUT_RESULT dict | None), read at call time."""
    doc = score.load_weights_doc()

    def _json(p):
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    return doc, _json(paths.FREEZE_RESULT_PATH), _json(paths.HOLDOUT_JSON_PATH)


# --- number formatting shared by note text (every number in a note comes from its values) ---

def fmt_weight(x: float) -> str:
    """Signed 2 dp with a Unicode minus; 0 shows as 0.00."""
    r = round(float(x), 2) + 0.0
    if r == 0:
        return "0.00"
    return f"+{r:.2f}" if r > 0 else f"−{abs(r):.2f}"


def fmt_metric(x: float) -> str:
    """Unsigned 4 dp (metric values); minus is Unicode."""
    s = f"{float(x):.4f}"
    return s.replace("-", "−")


def fmt_delta(x: float) -> str:
    """Signed 4 dp with a Unicode minus."""
    r = round(float(x), 4) + 0.0
    if r == 0:
        return "0.0000"
    return f"+{r:.4f}" if r > 0 else f"−{abs(r):.4f}"


def fmt_folds(k: int, n: int) -> str:
    return f"{int(k)} of {int(n)}"


def _sign(w: float) -> str:
    return "+" if w > 0 else "-" if w < 0 else "0"


def _effect(w: float) -> str:
    return "helps" if w > 0 else "hurts" if w < 0 else "none"


def _folds(doc: dict, key: str) -> tuple[int, int] | None:
    fs = ((doc.get("fit") or {}).get(key) or {}).get("fold_sign")
    return (int(fs[0]), int(fs[1])) if fs else None


def _period(block: dict, ci_key: str, keep_season: bool) -> dict:
    out = {}
    for cand, v in block.items():
        row = {"value": v.get("value"), "ci": v.get(ci_key)}
        if keep_season:
            row["ci_season"] = v.get("ci_season")
        out[cand] = row
    return out


def _sign_words(ws: list[float]) -> str:
    kinds = []
    for w in ws:
        r = round(w, 2)
        k = "about zero" if abs(r) < 0.1 else "negative" if r < 0 else "positive"
        if k not in kinds:
            kinds.append(k)
    order = [k for k in ("negative", "about zero", "positive") if k in kinds]
    return " or ".join(order) if len(order) <= 2 else "negative, about zero or positive"


def _notes(weights: dict, doc: dict, freeze: dict | None, holdout: dict | None) -> list[dict]:
    notes: list[dict] = []
    labels = {k: score.FACTORS[k]["label"] for k in weights}

    # momentum: hot records, streaks and close-game wins mostly fade given Elo and margins
    mom = [k for k in ("last16", "streak", "luck") if k in weights]
    if mom:
        values: dict[str, float] = {}
        parts = []
        for k in mom:
            values[k] = weights[k]
            part = f"{labels[k].lower()} {fmt_weight(weights[k])}"
            folds = _folds(doc, k)
            if folds:
                values[f"{k}_folds"] = folds[0]
                values[f"{k}_of"] = folds[1]
                part += f" (same sign in {fmt_folds(*folds)} seasons)"
            parts.append(part)
        words = _sign_words([weights[k] for k in mom])
        text = (
            "Hot records mostly fade. Once Elo and point margins are known, a strong recent record, a "
            f"winning streak and close-game wins tend not to last, so these weights are {words}: "
            + "; ".join(parts) + "."
        )
        notes.append({"key": "momentum", "text": text, "values": values})

    if "epa_traj" in weights:
        w = weights["epa_traj"]
        values = {"epa_traj": w}
        text = f"The efficiency trend adds about nothing once Elo is known. Its weight is {fmt_weight(w)}"
        d = ((freeze or {}).get("factors") or {}).get("epa_traj", {}).get("delta_spearman_n8")
        if d is not None:
            values["epa_traj_delta"] = d
            text += f", and adding it changed the walk-forward rank correlation by {fmt_delta(d)}"
        notes.append({"key": "efficiency", "text": text + ".", "values": values})

    if "vs_exp" in weights:
        w = weights["vs_exp"]
        values = {"vs_exp": w}
        text = (
            f"“Vs preseason expectations” has weight {fmt_weight(w)}: given the record, beating "
            "expectations tends to fade. Expectations come from Vegas win totals for 2003–2020 and "
            "from the model’s own preseason projection otherwise, including all of 2021 onward."
        )
        diag = ((holdout or {}).get("diagnostic") or {}).get("vs_exp_zeroed")
        if holdout and diag:
            z = diag.get("spearman_n8")
            full = (holdout.get("spearman_n8") or {}).get("composite", {}).get("value")
            dv = (diag.get("diff_vs_elo") or {}).get("value")
            if z is not None and full is not None:
                values["zeroed_spearman_n8"] = z
                values["full_spearman_n8"] = full
                text += (
                    " Pre-registered holdout check: with this factor zeroed the score’s rank correlation "
                    f"is {fmt_metric(z)}, against {fmt_metric(full)} for the full score"
                )
                if dv is not None:
                    values["zeroed_diff_vs_elo"] = dv
                    text += f" ({fmt_delta(dv)} vs Elo alone)"
                text += "."
        notes.append({"key": "vs_exp", "text": text, "values": values})

    if freeze:
        sp = freeze["walk_forward"]["spearman_n8"]
        c, e = sp["composite"]["value"], sp["elo"]["value"]
        notes.append({
            "key": "refit_vs_frozen",
            "text": (
                "The walk-forward numbers (2003–21) refit the weights each season on earlier seasons only, "
                f"with unrounded weights: rank correlation {fmt_metric(c)} for the feel-good score vs "
                f"{fmt_metric(e)} for Elo alone. The holdout uses the one frozen, rounded set."
            ),
            "values": {"composite_spearman_n8": c, "elo_spearman_n8": e},
        })

    notes.append({
        "key": "pbp_early",
        "text": "Play-by-play for 1999–2000 is low-confidence, so the efficiency and QB inputs are rougher for those seasons.",
        "values": {},
    })
    notes.append({
        "key": "tiebreakers",
        "text": "Playoff odds come from a simulation with simplified tiebreakers, so close races can be off by a little.",
        "values": {},
    })

    nb_values: dict[str, float] = {}
    nb = "These scores describe how fans should feel. They aren’t betting advice: Vegas spreads still predict single games better"
    br = ((freeze or {}).get("walk_forward") or {}).get("brier") or {}
    if "composite" in br and "spread" in br:
        nb_values = {"composite_brier": br["composite"]["value"], "spread_brier": br["spread"]["value"]}
        nb += (
            f" (walk-forward Brier score {fmt_metric(nb_values['spread_brier'])} for the spread vs "
            f"{fmt_metric(nb_values['composite_brier'])} for the feel-good score; lower is better)"
        )
    notes.append({"key": "not_betting", "text": nb + ".", "values": nb_values})

    if holdout is None:
        notes.append({"key": "holdout_pending", "text": HOLDOUT_PENDING, "values": {}})
    return notes


def build_methodology(weights: dict[str, float], doc: dict | None, freeze: dict | None,
                      holdout: dict | None, *, live: int) -> dict:
    doc = doc or {}
    is_frozen = doc.get("frozen") is True
    if is_frozen and freeze is None:
        raise ValueError("FREEZE_RESULT.json is missing; run `fgs freeze`")

    ffactors = (freeze or {}).get("factors") or {}
    factors = []
    for k, w in weights.items():
        rw = round(float(w), 2) + 0.0
        folds = _folds(doc, k)
        ff = ffactors.get(k) or {}
        factors.append({
            "key": k, "label": score.FACTORS[k]["label"], "description": score.FACTORS[k]["description"],
            "weight": w, "sign": _sign(rw), "effect": _effect(rw),
            "fold_sign": {"k": folds[0], "of": folds[1]} if folds else None,
            "delta_spearman_n8": ff.get("delta_spearman_n8"),
            "baseline_spearman_n8": ff.get("baseline_spearman_n8"),
        })

    walk_forward = None
    if freeze:
        wf = freeze["walk_forward"]
        a, b = wf["seasons"]
        walk_forward = {
            "seasons": list(wf["seasons"]),
            "label": f"Walk-forward {_span(a, b)} (refit each season)",
            "spearman_n8": _period(wf["spearman_n8"], "ci_season", False),
            "spearman_n4": _period(wf.get("spearman_n4") or {}, "ci_season", False),
            "brier": _period(wf["brier"], "ci_season", False),
            "diff": wf.get("diff"),
        }

    hold = None
    if holdout:
        a, b = holdout["seasons"]
        hold = {
            "seasons": list(holdout["seasons"]),
            "label": f"Holdout {_span(a, b)} (frozen weights)",
            "evaluated_at": holdout.get("evaluated_at"),
            "verdict": holdout.get("verdict"), "headline": holdout.get("headline"), "pass": holdout.get("pass"),
            "spearman_n8": _period(holdout["spearman_n8"], "ci_cluster", True),
            "spearman_n4": _period(holdout.get("spearman_n4") or {}, "ci_cluster", True),
            "brier": _period(holdout["brier"], "ci_cluster", True),
            "diff": holdout.get("diff"),
            "diagnostic": holdout.get("diagnostic"),
            "rerun": bool(holdout.get("rerun", False)),
        }

    frozen = None
    if is_frozen:
        frozen = {"fitted_at": doc.get("fitted_at"), "fit_seasons": list(doc.get("fit_seasons") or []),
                  "alpha": doc.get("alpha"), "n": doc.get("n")}

    return {
        "version": 1,
        "frozen": frozen,
        "target": {"n": 8, "text": TARGET_TEXT},
        "split": {
            "train": [season_config.REF_SEASONS[0], season_config.TRAIN_LAST_SEASON],
            "walk_forward": [season_config.FIRST_TEST_SEASON, season_config.TRAIN_LAST_SEASON],
            "holdout": list(season_config.HOLDOUT_SEASONS),
            "live": int(live),
            "reference": list(season_config.REF_SEASONS),
        },
        "factors": factors,
        "candidates": [dict(c) for c in CANDIDATES],
        "walk_forward": walk_forward,
        "holdout": hold,
        "notes": _notes(weights, doc, freeze, holdout),
    }

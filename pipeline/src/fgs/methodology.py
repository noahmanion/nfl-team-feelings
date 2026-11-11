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


def fmt_delta_ci(ci) -> str:
    """Signed 4 dp interval, "−0.0187 to +0.0161"; "—" when missing."""
    return "—" if not ci else f"{fmt_delta(ci[0])} to {fmt_delta(ci[1])}"


def _excludes_zero(ci) -> bool:
    return bool(ci) and (ci[0] > 0 or ci[1] < 0)


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


def _kind(w: float) -> str:
    """Rounded-weight class shared by every note: |w| < 0.1 is "about zero"."""
    r = round(float(w), 2)
    return "about zero" if abs(r) < 0.1 else "negative" if r < 0 else "positive"


def _size(w: float) -> str:
    a = abs(round(float(w), 2))
    return "near-zero" if a < 0.1 else "small" if a < 0.5 else "moderate" if a < 1.0 else "large"


def _consistency(folds: tuple[int, int] | None) -> str | None:
    if not folds or folds[1] <= 0:
        return None
    k, n = folds
    return "consistent" if k == n else "mostly consistent" if k / n >= 0.75 else "inconsistent"


def describe_weight(w: float, folds: tuple[int, int] | None) -> str:
    """e.g. "a small but consistent negative weight (−0.33, same sign in 19 of 19 seasons)". Every word
    comes from the weight's rounded size/sign and its walk-forward fold-sign agreement (WR-06)."""
    size, kind, cons = _size(w), _kind(w), _consistency(folds)
    if kind == "about zero":
        head = "a near-zero weight"
    elif cons is None:
        head = f"a {size} {kind} weight"
    else:
        conj = " but " if size == "small" and cons != "inconsistent" else ", "
        head = f"a {size}{conj}{cons} {kind} weight"
    tail = fmt_weight(w) + (f", same sign in {fmt_folds(*folds)} seasons" if folds else "")
    return f"{head} ({tail})"


def _offseason_draft(doc: dict | None) -> dict | None:
    """weights.yaml offseason.draft block (Phase 7) with its recorded evidence, or None."""
    off = (doc or {}).get("offseason")
    block = off.get("draft") if isinstance(off, dict) else None
    return block if isinstance(block, dict) else None


def _fold_pair(fs) -> tuple[int, int] | None:
    """Recorded fold-sign agreement "k/n" (or [k, n]) -> (k, n)."""
    if isinstance(fs, str) and "/" in fs:
        k, n = fs.split("/", 1)
        return int(k), int(n)
    if isinstance(fs, (list, tuple)) and len(fs) == 2:
        return int(fs[0]), int(fs[1])
    return None


def _draft_note(block: dict) -> dict:
    """The 'draft' honest note: every number templated from weights.yaml offseason.draft."""
    w = float(block.get("weight", 0.0))
    fitted, delta = block.get("fitted"), block.get("delta_wk0")
    folds = _fold_pair(block.get("fold_sign"))
    values: dict[str, float] = {"weight": w}
    parts = []
    if fitted is not None:
        values["fitted"] = float(fitted)
        parts.append(f"The fitted weight was {fmt_weight(fitted)}")
    if folds:
        values["fold_sign_k"], values["fold_sign_of"] = folds
        parts.append(f"{folds[0]}/{folds[1]} walk-forward folds agreed with its sign")
    if delta is not None:
        values["delta_wk0"] = float(delta)
        parts.append(f"the week-0 change in Spearman was {fmt_delta(delta)}")
    evidence = (", ".join(parts[:-1]) + ", and " + parts[-1]) if len(parts) > 1 else "".join(parts)
    text = "Draft capital over original slots was tested as an offseason term on top of the frozen score."
    if round(w, 2) == 0:
        verdict = "it didn’t pass the gate and the draft doesn’t move the score (it’s shown as text only)"
    else:
        verdict = (f"it passed the gate: it adds {fmt_weight(w)} × the capped draft z to scores at week 0, "
                   "fading to nothing by week 4")
    text += f" {evidence}, so {verdict}." if evidence else f" So {verdict}."
    text += (" This evidence is training-only walk-forward (2003–2021); the 2022–2025 holdout was already used "
             "to judge the in-season score.")
    return {"key": "draft", "text": text, "values": values}


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
        kinds = {_kind(weights[k]) for k in mom}
        tail = f"these weights are {words}: " + "; ".join(parts) + "."
        if "negative" in kinds and "positive" not in kinds:
            text = ("Hot records mostly fade. Once Elo and point margins are known, a strong recent record, a "
                    f"winning streak and close-game wins tend not to last, so {tail}")
        elif "positive" in kinds and "negative" not in kinds:
            text = ("Hot records mostly carry on. Even once Elo and point margins are known, a strong recent "
                    f"record, a winning streak and close-game wins tend to persist, so {tail}")
        elif "positive" in kinds:
            text = f"Momentum signals point different ways once Elo and point margins are known: {tail}"
        else:
            text = f"Once Elo and point margins are known, recent record, streaks and close-game wins add about nothing: {tail}"
        notes.append({"key": "momentum", "text": text, "values": values})

    if "epa_traj" in weights:
        w = weights["epa_traj"]
        values = {"epa_traj": w}
        folds = _folds(doc, "epa_traj")
        if folds:
            values["epa_traj_folds"], values["epa_traj_of"] = folds
        kind = _kind(w)
        how = ("an efficiency upswing slightly fades" if kind == "negative"
               else "an efficiency upswing slightly carries on" if kind == "positive"
               else "an efficiency upswing changes little")
        text = f"The efficiency trend has {describe_weight(w, folds)}: once the other factors are known, {how}"
        d = ((freeze or {}).get("factors") or {}).get("epa_traj", {}).get("delta_spearman_n8")
        if d is not None:
            values["epa_traj_delta"] = d
            text += (". Adding it on top of the factors before it changed the walk-forward rank correlation by "
                     f"{fmt_delta(d)}")
        notes.append({"key": "efficiency", "text": text + ".", "values": values})

    if "vs_exp" in weights:
        w = weights["vs_exp"]
        values = {"vs_exp": w}
        folds = _folds(doc, "vs_exp")
        kind = _kind(w)
        how = ("beating expectations tends to fade" if kind == "negative"
               else "beating expectations tends to persist" if kind == "positive"
               else "beating expectations adds about nothing")
        text = (
            f"“Vs preseason expectations” has {describe_weight(w, folds)}: given the record, {how}. "
            "Expectations come from Vegas win totals for 2003–2020 and "
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
                f"The walk-forward numbers ({_span(*freeze['walk_forward']['seasons'])}) refit the weights each season on earlier seasons only, "
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

    if holdout is not None:
        # WR-03: the holdout's other pre-registered comparisons, each with both intervals.
        hd = holdout.get("diff") or {}
        span = _span(*holdout["seasons"])
        hv: dict[str, float] = {}
        parts = []
        d4 = hd.get("spearman_n4") or {}
        if d4.get("value") is not None:
            hv["n4_diff"] = d4["value"]
            parts.append(
                f"Over the next 4 games instead of 8, the score − Elo rank-correlation difference was "
                f"{fmt_delta(d4['value'])} (95% interval {fmt_delta_ci(d4.get('ci_season'))} by season blocks, "
                f"{fmt_delta_ci(d4.get('ci_cluster'))} by team-season)."
            )
        bve = hd.get("brier_vs_elo") or {}
        hb = holdout.get("brier") or {}
        if bve.get("value") is not None:
            v = bve["value"]
            hv["brier_vs_elo"] = v
            how = "worse than" if v > 0 else "better than" if v < 0 else "level with"
            cs, cc = bve.get("ci_season"), bve.get("ci_cluster")
            pair = ""
            if (hb.get("composite") or {}).get("value") is not None and (hb.get("elo") or {}).get("value") is not None:
                hv["composite_brier"], hv["elo_brier"] = hb["composite"]["value"], hb["elo"]["value"]
                pair = f" ({fmt_metric(hv['composite_brier'])} vs {fmt_metric(hv['elo_brier'])})"
            excl = [name for name, ci in (("season-block", cs), ("season-week", cc)) if _excludes_zero(ci)]
            parts.append(
                f"On single games the score was {'slightly ' if v and abs(v) < 0.005 else ''}{how} Elo alone{pair}: next-game Brier difference "
                f"{fmt_delta(v)} (lower is better), 95% interval {fmt_delta_ci(cs)} by season blocks and "
                f"{fmt_delta_ci(cc)} by season-week."
                + (f" The {' and '.join(excl)} interval{'s' if len(excl) > 1 else ''} exclude{'' if len(excl) > 1 else 's'} zero."
                   if excl else "")
            )
        if parts:
            notes.append({"key": "holdout_detail", "text": f"Holdout {span}: " + " ".join(parts), "values": hv})

    if holdout is not None and holdout.get("fit_last") is not None:
        # WR-02: disclose the built-in asymmetry of the pre-registered holdout Brier maps.
        fl = int(holdout["fit_last"])
        fs = list((doc or {}).get("fit_seasons") or [])
        lo, hi = holdout["seasons"]
        same = len(fs) == 2 and int(fs[1]) <= fl
        text = (
            f"The holdout Brier maps (turning a rating gap into a single-game win chance) were fit once on seasons "
            f"up to {fl}, as pre-registered."
        )
        if same:
            text += (
                f" The score’s weights were fit on those same seasons ({_span(*fs)}), so its map was fit on in-sample "
                f"score values and is likely a little too steep: its single-game chances on {_span(lo, hi)} are "
                "expected to be slightly overconfident. Elo’s map was fit on the same seasons, but Elo itself has no "
                "weights fit to those results (fixed 538-style update constants and a market-implied home edge), so "
                "only its two-number map is in-sample. Read the holdout Brier gap against Elo with that in mind. The "
                "walk-forward Brier numbers don’t have this problem: each season’s weights and map use earlier "
                "seasons only."
            )
        notes.append({"key": "brier_maps", "text": text,
                      "values": {"fit_last": fl, **({"fit_first": int(fs[0]), "fit_through": int(fs[1])} if same else {})}})

    nb_values: dict[str, float] = {}
    nb = "These scores describe how fans should feel. They aren’t betting advice: Vegas spreads still predict single games better"
    hbr = (holdout or {}).get("brier") or {}
    br = ((freeze or {}).get("walk_forward") or {}).get("brier") or {}
    if "composite" in hbr and "spread" in hbr:
        nb_values = {"composite_brier": hbr["composite"]["value"], "spread_brier": hbr["spread"]["value"]}
        where = f"holdout {_span(*holdout['seasons'])}"
    elif "composite" in br and "spread" in br:
        nb_values = {"composite_brier": br["composite"]["value"], "spread_brier": br["spread"]["value"]}
        where = "walk-forward"
    if nb_values:
        nb += (
            f" ({where} Brier score {fmt_metric(nb_values['spread_brier'])} for the spread vs "
            f"{fmt_metric(nb_values['composite_brier'])} for the feel-good score; lower is better)"
        )
    notes.append({"key": "not_betting", "text": nb + ".", "values": nb_values})

    od = _offseason_draft(doc)
    if od is not None:
        notes.append(_draft_note(od))

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

    od = _offseason_draft(doc)
    if od is not None and round(float(od.get("weight", 0.0)), 2) != 0:
        # a live offseason term is a real score input: list it (never at weight 0, display only)
        w = float(od["weight"])
        rw = round(w, 2) + 0.0
        folds = _fold_pair(od.get("fold_sign"))
        factors.append({
            "key": "draft", "label": score.OFFSEASON_FACTORS["draft"]["label"],
            "description": score.OFFSEASON_FACTORS["draft"]["description"],
            "weight": w, "sign": _sign(rw), "effect": _effect(rw),
            "fold_sign": {"k": folds[0], "of": folds[1]} if folds else None,
            "delta_spearman_n8": od.get("delta_wk0"), "baseline_spearman_n8": None,
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
            # WR-04: which resampling scheme each period's plotted `ci` comes from
            "ci_method": {"spearman": "season-block", "brier": "season-block"},
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
            "ci_method": {"spearman": "team-season", "brier": "season-week"},
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

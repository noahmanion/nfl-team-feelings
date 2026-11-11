"""methodology.json builder (SITE-07): pure dict-in/dict-out tests with synthetic evidence."""

import json

import pytest

from fgs import methodology, paths
from fgs.methodology import build_methodology, fmt_delta, fmt_folds, fmt_metric, fmt_weight, load_evidence

WEIGHTS = {"elo": 2.59, "last16": -0.21, "streak": -0.03, "luck": -0.35, "epa_traj": -0.33, "vs_exp": -1.22,
           "po_trend": 0.0}
DOC = {
    "frozen": True, "fit_seasons": [1999, 2021], "alpha": 0.01, "n": 100, "fitted_at": "2026-01-01",
    "weights": WEIGHTS,
    "fit": {k: {"raw": w, "sign": "+" if w > 0 else "-" if w < 0 else "0", "fold_sign": [17 - i, 19]}
            for i, (k, w) in enumerate(WEIGHTS.items())},
}


def _m(v, lo, hi, lo2, hi2):
    return {"value": v, "ci_season": [lo, hi], "ci_cluster": [lo2, hi2]}


CANDS = ("composite", "elo", "season_wpct", "last16", "pd_pg")
FREEZE = {
    "walk_forward": {
        "seasons": [2003, 2021],
        "spearman_n8": {c: _m(0.5 - i / 100, 0.48 - i / 100, 0.52 - i / 100, 0.47, 0.53) for i, c in enumerate(CANDS)},
        "spearman_n4": {c: _m(0.4, 0.38, 0.42, 0.37, 0.43) for c in CANDS},
        "brier": {**{c: _m(0.22, 0.21, 0.23, 0.205, 0.235) for c in CANDS},
                  "spread": _m(0.211, 0.207, 0.215, 0.206, 0.216), "elo_538": {"value": 0.219}},
        "diff": {"spearman_n8": {"value": 0.013, "ci_season": [0.002, 0.024], "ci_cluster": [0.003, 0.023],
                                 "seasons_won": 14, "of": 19}},
    },
    "factors": {k: {"weight": w, "delta_spearman_n8": None if k == "elo" else 0.0011 * (i + 1),
                    "baseline_spearman_n8": 0.5114 if k == "elo" else None}
                for i, (k, w) in enumerate(WEIGHTS.items())},
}
# made-up numbers (schema only; the real holdout is never computed here)
HOLDOUT = {
    "seasons": [2022, 2025], "evaluated_at": "2099-01-01", "verdict": "slight", "headline": "Made-up headline.",
    "pass": False, "rerun": False, "fit_last": 2021,
    "spearman_n8": {c: _m(0.3, 0.2, 0.4, 0.1, 0.5) for c in CANDS},
    "spearman_n4": {c: _m(0.3, 0.2, 0.4, 0.1, 0.5) for c in CANDS},
    "brier": {**{c: _m(0.22, 0.21, 0.23, 0.2, 0.24) for c in CANDS}, "spread": _m(0.21, 0.2, 0.22, 0.19, 0.23),
              "elo_538": {"value": 0.22}},
    "diff": {"spearman_n8": {"value": 0.01, "ci_season": [-0.01, 0.03], "ci_cluster": [-0.02, 0.04],
                             "seasons_won": 3, "of": 4}},
    "diagnostic": {"vs_exp_zeroed": {"spearman_n8": 0.2876, "diff_vs_elo": {"value": -0.0123, "ci_cluster": [-0.03, 0.01]}}},
}


def test_factors_and_null_holdout():
    m = build_methodology(WEIGHTS, DOC, FREEZE, None, live=2026)
    assert [f["key"] for f in m["factors"]] == list(WEIGHTS)
    for f in m["factors"]:
        w = WEIGHTS[f["key"]]
        assert f["weight"] == w
        assert (f["sign"], f["effect"]) == (("+", "helps") if w > 0 else ("-", "hurts") if w < 0 else ("0", "none"))
        k, n = DOC["fit"][f["key"]]["fold_sign"]
        assert f["fold_sign"] == {"k": k, "of": n}
        assert f["delta_spearman_n8"] == FREEZE["factors"][f["key"]]["delta_spearman_n8"]
        assert f["baseline_spearman_n8"] == FREEZE["factors"][f["key"]]["baseline_spearman_n8"]
    assert m["holdout"] is None and m["split"]["live"] == 2026
    assert m["frozen"] == {"fitted_at": "2026-01-01", "fit_seasons": [1999, 2021], "alpha": 0.01, "n": 100}
    for c, v in FREEZE["walk_forward"]["spearman_n8"].items():
        assert m["walk_forward"]["spearman_n8"][c] == {"value": v["value"], "ci": v["ci_season"]}
    assert m["walk_forward"]["diff"] == FREEZE["walk_forward"]["diff"]
    assert any(n["key"] == "holdout_pending" for n in m["notes"])
    json.dumps(m, allow_nan=False)


def test_rounded_sign_tiny_weight():
    m = build_methodology({"elo": -0.004}, {}, None, None, live=2026)
    assert m["factors"][0]["sign"] == "0" and m["factors"][0]["effect"] == "none"


def test_synthetic_holdout():
    m = build_methodology(WEIGHTS, DOC, FREEZE, HOLDOUT, live=2026)
    h = m["holdout"]
    assert h["verdict"] == "slight" and h["headline"] == "Made-up headline." and h["label"] == "Holdout 2022–25 (frozen weights)"
    for c, v in HOLDOUT["spearman_n8"].items():
        assert h["spearman_n8"][c] == {"value": v["value"], "ci": v["ci_cluster"], "ci_season": v["ci_season"]}
    assert not any(n["key"] == "holdout_pending" for n in m["notes"])
    note = next(n for n in m["notes"] if n["key"] == "vs_exp")
    assert note["values"]["zeroed_spearman_n8"] == 0.2876
    assert fmt_metric(0.2876) in note["text"] and fmt_delta(-0.0123) in note["text"]


def test_brier_map_disclosure():
    # WR-02: only once a holdout exists; names the shared fit seasons
    assert not any(n["key"] == "brier_maps" for n in build_methodology(WEIGHTS, DOC, FREEZE, None, live=2026)["notes"])
    m = build_methodology(WEIGHTS, DOC, FREEZE, HOLDOUT, live=2026)
    note = next(n for n in m["notes"] if n["key"] == "brier_maps")
    assert note["values"] == {"fit_last": 2021, "fit_first": 1999, "fit_through": 2021}
    assert "1999–21" in note["text"] and "overconfident" in note["text"] and "Elo" in note["text"]


def test_frozen_without_freeze_raises():
    with pytest.raises(ValueError, match="FREEZE_RESULT"):
        build_methodology(WEIGHTS, DOC, None, None, live=2026)


def test_unfrozen_without_freeze():
    m = build_methodology(WEIGHTS, {"weights": WEIGHTS}, None, None, live=2026)
    assert m["walk_forward"] is None and m["frozen"] is None
    assert all(f["fold_sign"] is None for f in m["factors"])


def test_notes_values_equal_sources_and_appear_in_text():
    m = build_methodology(WEIGHTS, DOC, FREEZE, None, live=2026)
    notes = {n["key"]: n for n in m["notes"]}
    assert {"momentum", "efficiency", "vs_exp", "refit_vs_frozen", "pbp_early", "tiebreakers", "not_betting",
            "holdout_pending"} <= set(notes)
    mom = notes["momentum"]
    assert mom["values"]["streak"] == WEIGHTS["streak"]
    assert mom["values"]["luck_folds"] == DOC["fit"]["luck"]["fold_sign"][0]
    for k in ("last16", "streak", "luck"):
        assert fmt_weight(WEIGHTS[k]) in mom["text"]
        assert fmt_folds(*DOC["fit"][k]["fold_sign"]) in mom["text"]
    assert "negative or about zero" in mom["text"]
    eff = notes["efficiency"]
    assert eff["values"]["epa_traj"] == WEIGHTS["epa_traj"]
    assert eff["values"]["epa_traj_delta"] == FREEZE["factors"]["epa_traj"]["delta_spearman_n8"]
    assert fmt_weight(WEIGHTS["epa_traj"]) in eff["text"] and fmt_delta(eff["values"]["epa_traj_delta"]) in eff["text"]
    assert fmt_weight(WEIGHTS["vs_exp"]) in notes["vs_exp"]["text"]
    r = notes["refit_vs_frozen"]["values"]
    assert r["composite_spearman_n8"] == FREEZE["walk_forward"]["spearman_n8"]["composite"]["value"]
    assert fmt_metric(r["elo_spearman_n8"]) in notes["refit_vs_frozen"]["text"]
    nb = notes["not_betting"]
    assert nb["values"]["spread_brier"] == FREEZE["walk_forward"]["brier"]["spread"]["value"]
    assert fmt_metric(nb["values"]["spread_brier"]) in nb["text"]


def test_momentum_wording_follows_signs():
    w = {"last16": 0.4, "streak": 0.3, "luck": 0.25}
    m = build_methodology(w, {}, None, None, live=2026)
    text = next(n for n in m["notes"] if n["key"] == "momentum")["text"]
    assert "positive" in text and "negative" not in text


def _note(m, key):
    return next(n for n in m["notes"] if n["key"] == key)["text"]


def test_notes_wording_follows_flipped_signs():
    # WR-06: flip every sign; no note may keep the "fade" wording
    flipped = {k: -w for k, w in WEIGHTS.items()}
    doc = {**DOC, "weights": flipped}
    m = build_methodology(flipped, doc, FREEZE, None, live=2026)
    mom, eff, vx = _note(m, "momentum"), _note(m, "efficiency"), _note(m, "vs_exp")
    assert "fade" not in mom and "carry on" in mom and "positive" in mom
    assert "positive weight" in eff and "fades" not in eff and "carries on" in eff
    assert "tends to persist" in vx and "fade" not in vx
    base = build_methodology(WEIGHTS, DOC, FREEZE, None, live=2026)
    assert "fade" in _note(base, "momentum") and "tends to fade" in _note(base, "vs_exp")
    assert "negative weight" in _note(base, "efficiency")


def test_momentum_mixed_and_zero_wording():
    mixed = build_methodology({"last16": 0.4, "streak": -0.3, "luck": 0.0}, {}, None, None, live=2026)
    assert "point different ways" in _note(mixed, "momentum") and "fade" not in _note(mixed, "momentum")
    zero = build_methodology({"last16": 0.04, "streak": -0.03}, {}, None, None, live=2026)
    assert "add about nothing" in _note(zero, "momentum")


def test_describe_weight():
    from fgs.methodology import describe_weight
    assert describe_weight(-0.33, (19, 19)) == "a small but consistent negative weight (−0.33, same sign in 19 of 19 seasons)"
    assert describe_weight(-1.22, (18, 19)).startswith("a large, mostly consistent negative weight")
    assert describe_weight(0.63, (10, 19)).startswith("a moderate, inconsistent positive weight")
    assert describe_weight(0.04, (12, 19)).startswith("a near-zero weight")
    assert describe_weight(2.59, None) == "a large positive weight (+2.59)"


def test_formatters():
    assert fmt_weight(2.59) == "+2.59" and fmt_weight(-0.56) == "−0.56" and fmt_weight(-0.0) == "0.00"
    assert fmt_delta(-0.0008) == "−0.0008" and fmt_delta(0.0028) == "+0.0028"


def test_load_evidence_reads_paths_at_call_time(tmp_path, monkeypatch):
    w = tmp_path / "weights.yaml"
    w.write_text("weights: {elo: 1.0}\n")
    monkeypatch.setattr(paths, "WEIGHTS_PATH", w)
    monkeypatch.setattr(paths, "FREEZE_RESULT_PATH", tmp_path / "FREEZE_RESULT.json")
    monkeypatch.setattr(paths, "HOLDOUT_JSON_PATH", tmp_path / "HOLDOUT_RESULT.json")
    doc, freeze, hold = load_evidence()
    assert doc["weights"] == {"elo": 1.0} and freeze is None and hold is None
    (tmp_path / "HOLDOUT_RESULT.json").write_text(json.dumps({"seasons": [2022, 2025]}))
    (tmp_path / "FREEZE_RESULT.json").write_text(json.dumps({"x": 1}))
    doc, freeze, hold = load_evidence()
    assert hold == {"seasons": [2022, 2025]} and freeze == {"x": 1}


def test_no_harness_imports():
    import re
    from pathlib import Path

    code = Path(methodology.__file__).read_text()
    assert not re.search(r"^\s*(from|import)\s+[\w., ]*(backtest|freeze|holdout|bootstrap)", code, re.M)

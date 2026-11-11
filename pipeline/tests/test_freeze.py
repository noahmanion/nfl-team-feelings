"""Phase 6 freeze: rounding/signs, fold consistency, deltas, log parsing, YAML render, sealing, guards."""

import json

import numpy as np
import polars as pl
import pytest
import yaml

import fgs.paths
from fgs import backtest, cli, freeze
from fgs.backtest import PROPOSAL_FACTORS, RIDGE_SETS
from fgs.freeze import (
    factor_deltas, fold_sign_consistency, format_weight, parse_backtest_log, render_weights_yaml, round_weight,
    sign_of,
)
from fgs.ingest import load_schedules
from fgs.score import is_frozen, load_weights
from conftest import derive_inputs


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def test_format_weight_sign_and_no_negative_zero():
    assert format_weight(-0.004) == "0.00"
    assert format_weight(-0.0094) == "-0.01"
    assert format_weight(2.5913) == "2.59"
    z = round_weight(-0.004)
    assert z == 0.0 and np.copysign(1.0, z) == 1.0  # never -0.0
    assert sign_of(2.59) == "+" and sign_of(-0.01) == "-" and sign_of(round_weight(-0.004)) == "0"


def test_fold_sign_consistency_counts_matching_signs():
    folds = [{"weights": {"a": 1.0, "b": -0.2}}, {"weights": {"a": 0.5, "b": 0.1}}, {"weights": {"a": -0.1, "b": -0.3}}]
    assert fold_sign_consistency(folds, {"a": 2.0, "b": -0.05}) == {"a": [2, 3], "b": [2, 3]}


def _fake_report(vals: dict) -> dict:
    return {"candidates": {k: {"N8": {"all": {"spearman": v}}} for k, v in vals.items()}}


def test_factor_deltas_insertion_order():
    sets = {"ridge:elo": ["elo"], "ridge:+a": ["elo", "a"], "ridge:+b": ["elo", "a", "b"]}
    out = factor_deltas(_fake_report({"ridge:elo": 0.5, "ridge:+a": 0.51, "ridge:+b": 0.505}), sets)
    assert out["elo"] == {"delta_spearman_n8": None, "baseline_spearman_n8": 0.5}
    assert out["a"]["delta_spearman_n8"] == pytest.approx(0.01)
    assert out["b"]["delta_spearman_n8"] == pytest.approx(-0.005)
    assert list(out) == ["elo", "a", "b"]


def test_parse_backtest_log_by_header_name():
    text = """# Log

| Date | Factor | Extra | ΔSpearman (N=8) | Notes |
| ---- | ------ | ----- | --------------- | ----- |
| d | elo | x | 0.5114 (baseline) | first |
| d | `sow` | x | −0.0047 | unicode minus |
| d | mov | x | +0.0026 | |
| d | mov | x | +0.9999 | later duplicate ignored |

Some prose.

| ΔSpearman (N=8) | Factor |
|---|---|
| +0.0100 | luck |
"""
    got = parse_backtest_log(text)
    assert got == {"elo": 0.5114, "sow": -0.0047, "mov": 0.0026, "luck": 0.01}


def test_parse_real_backtest_log_has_every_factor():
    path = fgs.paths.PIPELINE_ROOT / "BACKTEST_LOG.md"
    if not path.exists():
        pytest.skip("no BACKTEST_LOG.md")
    got = parse_backtest_log(path.read_text())
    assert set(PROPOSAL_FACTORS) <= set(got)


def _canned(fold_n=19) -> dict:
    raws = [2.5913, 1.83, -0.2012, 1.24, -0.56, -0.05, -0.35, -0.33, 0.63, -1.23, -0.0012]
    factors = {}
    for i, (f, r) in enumerate(zip(PROPOSAL_FACTORS, raws)):
        w = round_weight(r)
        factors[f] = {"raw": r, "weight": w, "sign": sign_of(w), "fold_sign": [19 - i % 3, fold_n],
                      "delta_spearman_n8": None if i == 0 else 0.001 * i,
                      "baseline_spearman_n8": 0.5114 if i == 0 else None}
    ci = [0.1, 0.2]
    blk = {"value": 0.5, "ci_season": ci, "ci_cluster": ci}
    return {
        "version": 1, "fitted_at": "2026-11-11", "fit_seasons": [1999, 2021], "target": "adjusted_margin_n8",
        "alpha": 0.01, "n": 12331,
        "walk_forward": {
            "seasons": [2003, 2021], "composite_set": list(RIDGE_SETS)[-1],
            "bootstrap": {"B": 2000, "seed": 20221, "method": "percentile",
                          "cluster_spearman": "team-season stratified by season",
                          "cluster_brier": "season-week stratified by season"},
            "spearman_n8": {c: blk for c in freeze.SPEARMAN_CANDS},
            "spearman_n4": {c: blk for c in freeze.SPEARMAN_CANDS},
            "brier": {**{c: blk for c in freeze.BRIER_CANDS}, "elo_538": {"value": 0.22}},
            "n_games": 4000,
            "diff": {"spearman_n8": {**blk, "seasons_won": 14, "of": 19}, "brier_vs_elo": blk, "brier_vs_spread": blk},
        },
        "factors": factors,
        "log_crosscheck": {"max_abs_diff": 0.0001, "warnings": []},
    }


def test_render_weights_yaml_round_trip(tmp_path):
    c = _canned()
    text = render_weights_yaml(c)
    doc = yaml.safe_load(text)
    assert doc["frozen"] is True and doc["fit_seasons"] == [1999, 2021] and doc["target"] == "adjusted_margin_n8"
    assert doc["alpha"] == 0.01 and doc["n"] == 12331 and doc["fitted_at"] == "2026-11-11"
    assert list(doc["weights"]) == PROPOSAL_FACTORS
    assert doc["weights"] == {f: d["weight"] for f, d in c["factors"].items()}
    assert doc["weights"]["po_trend"] == 0.0
    for f, d in c["factors"].items():
        assert doc["fit"][f]["sign"] == d["sign"] and doc["fit"][f]["fold_sign"] == d["fold_sign"]
        assert doc["fit"][f]["raw"] == pytest.approx(d["raw"], abs=1e-6)
    in_weights = text.split("\nweights:")[1].split("\nfit:")[0]
    assert "-0.00" not in in_weights.replace("-0.001", "")
    assert not any(line.strip().endswith(": -0.00") for line in in_weights.splitlines())
    assert "FROZEN (Phase 6)" in text and "PREREGISTRATION.md" in text
    assert "~0, kept (MODEL-15)" in text  # po_trend rounds to 0.00
    p = tmp_path / "w.yaml"
    p.write_text(text)
    assert load_weights(p) == doc["weights"] and is_frozen(p)


def test_render_weights_yaml_why_only_for_negative():
    c = _canned()
    text = render_weights_yaml(c)
    assert "why -: given Elo, a hot recent record" in text  # last16 is "-"
    c["factors"]["last16"].update(raw=0.2, weight=0.2, sign="+")
    assert "a hot recent record" not in render_weights_yaml(c)


# ---------------------------------------------------------------------------
# Real cache: build_freeze, sealing
# ---------------------------------------------------------------------------

def _swap_late(raw: pl.DataFrame) -> pl.DataFrame:
    late = pl.col("season") >= 2022
    return raw.with_columns(
        pl.when(late).then(pl.col("away_score")).otherwise(pl.col("home_score")).alias("home_score"),
        pl.when(late).then(pl.col("home_score")).otherwise(pl.col("away_score")).alias("away_score"),
        pl.when(late).then(-pl.col("result")).otherwise(pl.col("result")).alias("result"),
    )


@pytest.fixture(scope="module")
def real_freeze():
    if not (fgs.paths.CACHE_DIR / "schedules.parquet").exists():
        pytest.skip("no cached schedules; run `uv run fgs build` first")
    raw = load_schedules()
    derived = cli.derive(raw, scored=False, **derive_inputs())
    log = (fgs.paths.PIPELINE_ROOT / "BACKTEST_LOG.md").read_text()
    return raw, derived, freeze.build_freeze(derived, B=50, log_text=log)


def test_build_freeze_real_signs_and_folds(real_freeze):
    _, derived, fr = real_freeze
    prop = backtest.propose_weights(derived)
    assert list(fr["factors"]) == PROPOSAL_FACTORS and len(fr["factors"]) == 11
    for f, d in fr["factors"].items():
        assert d["weight"] == round_weight(prop["weights"][f])
        assert d["sign"] == sign_of(d["weight"])
        k, n = d["fold_sign"]
        assert n == 19 and 0 <= k <= 19
    assert fr["fit_seasons"] == [1999, 2021] and fr["target"] == "adjusted_margin_n8"
    assert fr["alpha"] == prop["alpha"] and fr["n"] == prop["n"]
    json.dumps(fr, allow_nan=False)


def test_build_freeze_real_walk_forward(real_freeze):
    _, derived, fr = real_freeze
    report = backtest.run_backtest(derived)
    wf = fr["walk_forward"]
    last = list(RIDGE_SETS)[-1]
    assert wf["seasons"] == [2003, 2021] and wf["composite_set"] == last
    sp = wf["spearman_n8"]
    assert sp["composite"]["value"] == pytest.approx(report["candidates"][last]["N8"]["all"]["spearman"], abs=1e-6)
    assert sp["elo"]["value"] == pytest.approx(report["candidates"]["elo"]["N8"]["all"]["spearman"], abs=1e-6)
    d = wf["diff"]["spearman_n8"]
    assert d["value"] == pytest.approx(sp["composite"]["value"] - sp["elo"]["value"], abs=2e-6)
    assert d["of"] == 19 and 0 <= d["seasons_won"] <= 19
    for blk in (wf["spearman_n8"], wf["spearman_n4"]):
        for c in freeze.SPEARMAN_CANDS:
            lo, hi = blk[c]["ci_season"]
            assert lo <= hi and len(blk[c]["ci_cluster"]) == 2
    assert set(freeze.BRIER_CANDS) | {"elo_538"} == set(wf["brier"])
    assert wf["brier"]["spread"]["value"] < wf["brier"]["elo"]["value"]
    assert wf["n_games"] > 4000
    assert fr["factors"]["elo"]["delta_spearman_n8"] is None
    assert fr["factors"]["elo"]["baseline_spearman_n8"] == pytest.approx(
        report["candidates"]["ridge:elo"]["N8"]["all"]["spearman"], abs=1e-6)
    assert "max_abs_diff" in fr["log_crosscheck"] and isinstance(fr["log_crosscheck"]["warnings"], list)


def test_build_freeze_sealed_from_holdout(real_freeze):
    raw, _, fr = real_freeze
    swapped = freeze.build_freeze(cli.derive(_swap_late(raw), scored=False, **derive_inputs()), B=20)
    base = freeze.build_freeze(cli.derive(raw, scored=False, **derive_inputs()), B=20)
    assert swapped["factors"] == base["factors"] == fr["factors"]
    assert swapped["alpha"] == base["alpha"] and swapped["n"] == base["n"]
    assert swapped["walk_forward"] == base["walk_forward"]


# ---------------------------------------------------------------------------
# Refusal guards (run before any data load) and the CLI write path
# ---------------------------------------------------------------------------

@pytest.fixture
def guard_paths(tmp_path, monkeypatch):
    weights = tmp_path / "weights.yaml"
    weights.write_text(render_weights_yaml(_canned()))
    holdout = tmp_path / "HOLDOUT_RESULT.md"
    monkeypatch.setattr(fgs.paths, "WEIGHTS_PATH", weights)
    monkeypatch.setattr(fgs.paths, "HOLDOUT_MD_PATH", holdout)
    monkeypatch.setattr(fgs.paths, "HOLDOUT_JSON_PATH", tmp_path / "HOLDOUT_RESULT.json")
    monkeypatch.setattr(fgs.paths, "FREEZE_RESULT_PATH", tmp_path / "FREEZE_RESULT.json")
    monkeypatch.setattr(cli, "DERIVED_DIR", tmp_path / "derived")

    def boom(*a, **k):
        raise AssertionError("guard did not refuse before loading data")

    monkeypatch.setattr(cli, "derive", boom)
    monkeypatch.setattr(cli, "load_schedules", boom)
    monkeypatch.setattr(cli, "cached_inputs", boom)
    return tmp_path


def test_guard_propose_weights_refused_when_frozen(guard_paths, capsys):
    assert cli.main(["backtest", "--propose-weights"]) == 1
    assert "frozen" in capsys.readouterr().err


def test_guard_freeze_refused_when_frozen(guard_paths, capsys):
    assert cli.main(["freeze"]) == 1
    assert "frozen" in capsys.readouterr().err


def test_guard_unfreeze_refused_after_holdout(guard_paths, capsys):
    (guard_paths / "HOLDOUT_RESULT.md").write_text("# done\n")
    assert cli.main(["freeze", "--unfreeze"]) == 1
    assert "pre-registration" in capsys.readouterr().err


def test_guard_unfreeze_refused_after_holdout_json_only(guard_paths, capsys):
    # WR-01: either result file closes the freeze, not just the .md
    (guard_paths / "HOLDOUT_RESULT.json").write_text("{}\n")
    assert cli.main(["freeze", "--unfreeze"]) == 1
    assert "pre-registration" in capsys.readouterr().err


def test_guard_include_holdout_sealed(guard_paths, capsys):
    assert cli.main(["backtest", "--include-holdout"]) == 1
    assert "sealed" in capsys.readouterr().err


def test_cli_freeze_unfreeze_writes_both_files(guard_paths, monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_schedules", lambda *a, **k: None)
    monkeypatch.setattr(cli, "cached_inputs", lambda *a, **k: {})
    monkeypatch.setattr(cli, "derive", lambda *a, **k: {})
    canned = _canned()
    monkeypatch.setattr(freeze, "build_freeze", lambda derived, **k: canned)
    assert cli.main(["freeze", "--unfreeze"]) == 0
    w = guard_paths / "weights.yaml"
    assert load_weights(w) == {f: d["weight"] for f, d in canned["factors"].items()} and is_frozen(w)
    data = json.loads((guard_paths / "FREEZE_RESULT.json").read_text(),
                      parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    assert data == canned
    assert "composite − elo" in capsys.readouterr().out

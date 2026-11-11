"""Holdout evaluator and `fgs holdout` guards.

HOLDOUT DISCIPLINE: these tests only evaluate the 2018-2021 training stand-in (weights fit on
1999-2017) or mocks. No test evaluates 2022-2025, and no test passes the holdout opt-in flag.
"""

import hashlib
import json
import subprocess

import numpy as np
import polars as pl
import pytest

import fgs.paths
from fgs import backtest, cli, freeze, holdout, score
from fgs.paths import CACHE_DIR

from conftest import derive_inputs

STANDIN = (2018, 2021)
STANDIN_FIT_LAST = 2017
FACTORS = backtest.PROPOSAL_FACTORS


# ---------------------------------------------------------------------------
# Verdict (pure)
# ---------------------------------------------------------------------------

def test_verdict_slight_when_wider_cluster_ci_includes_zero():
    key, text = holdout.verdict(0.02, [0.004, 0.042], [-0.002, 0.040])
    assert key == "slight"
    assert text == "Yes, slightly: better than Elo alone on 2022–25, but within the noise of four seasons."


def test_verdict_yes():
    key, text = holdout.verdict(0.03, [0.01, 0.05], [0.005, 0.06])
    assert key == "yes"
    assert text == "Yes: on 2022–25 the score ranked teams' next 8 games better than Elo alone."


def test_verdict_no():
    no = "Not on 2022–25: Elo alone did as well or better. We kept the weights anyway (no re-tuning)."
    assert holdout.verdict(0.0, [0.01, 0.05], [0.005, 0.06]) == ("no", no)
    assert holdout.verdict(-0.01, [-0.03, 0.01], [-0.04, 0.02]) == ("no", no)


def test_verdict_season_ci_drives_when_wider():
    # season CI is wider and includes 0; the narrower cluster CI excludes it -> slight
    assert holdout.verdict(0.02, [-0.01, 0.06], [0.005, 0.035])[0] == "slight"
    # season CI wider and excludes 0, cluster narrower but includes 0 -> yes
    assert holdout.verdict(0.02, [0.001, 0.08], [-0.001, 0.03])[0] == "yes"
    # tie in width -> cluster decides
    assert holdout.verdict(0.02, [0.01, 0.03], [-0.005, 0.015])[0] == "slight"


def test_verdict_headlines_match_preregistration():
    text = fgs.paths.PREREG_PATH.read_text()
    for sentence in holdout.HEADLINES.values():
        assert f'"{sentence}"' in text


def test_verdict_pass_is_point_estimate():
    assert holdout.passed(0.0001) is True
    assert holdout.passed(0.0) is False
    assert holdout.passed(-0.01) is False
    assert holdout.passed(None) is False


# ---------------------------------------------------------------------------
# Season guard (no data needed)
# ---------------------------------------------------------------------------

def _boom_derived():
    class Boom(dict):
        def __getitem__(self, k):
            raise AssertionError("evaluate_frozen read data before its guard")
    return Boom()


def test_evaluate_frozen_raises_on_holdout_seasons():
    w = {"elo": 1.0}
    for seasons in ((2022, 2025), (2018, 2022)):
        with pytest.raises(ValueError, match="fgs holdout"):
            holdout.evaluate_frozen(_boom_derived(), w, seasons, 2021)


def test_evaluate_frozen_raises_on_weight_mismatch():
    derived = {"weights": {"elo": 1.0, "mov": 0.5}}
    with pytest.raises(ValueError, match="frozen weights"):
        holdout.evaluate_frozen(derived, {"elo": 1.0, "mov": 0.4}, STANDIN, STANDIN_FIT_LAST)


# ---------------------------------------------------------------------------
# Brier maps fit only on seasons <= fit_last
# ---------------------------------------------------------------------------

def _toy_ng(seed=0):
    rng = np.random.default_rng(seed)
    n = 400
    season = np.repeat([2015, 2016, 2017, 2018], n // 4).astype(np.int32)
    data = {"season": season, "y": rng.integers(0, 2, n).astype(float),
            "home_ind": np.ones(n), "spread_line": rng.normal(0, 6, n)}
    for c in holdout.MODEL_CANDS:
        col = holdout.COLS[c]
        data[f"h_{col}"] = rng.normal(size=n)
        data[f"a_{col}"] = rng.normal(size=n)
    data["home_ind"][::5] = 0.0
    return pl.DataFrame(data)


def test_brier_maps_use_only_fit_seasons():
    ng = _toy_ng()
    a = holdout._brier_maps(ng, 2016)
    flipped = ng.with_columns(
        pl.when(pl.col("season") > 2016).then(1.0 - pl.col("y")).otherwise(pl.col("y")).alias("y")
    )
    b = holdout._brier_maps(flipped, 2016)
    assert set(a) == set(holdout.BRIER_CANDS)
    for c in a:
        np.testing.assert_array_equal(a[c], b[c])
    # and the maps do depend on the fit rows
    c = holdout._brier_maps(ng.with_columns((1.0 - pl.col("y")).alias("y")), 2016)
    assert not np.array_equal(a["elo"], c["elo"])


# ---------------------------------------------------------------------------
# Training stand-in (real cache): weights fit 1999-2017, evaluated on 2018-2021
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def standin():
    if not (CACHE_DIR / "schedules.parquet").exists():
        pytest.skip("no cached schedules; run `uv run fgs build` first")
    raw = cli.load_schedules()
    base = cli.derive(raw, scored=False, **derive_inputs())
    mp = pytest.MonkeyPatch()
    mp.setattr(backtest, "TRAIN_LAST_SEASON", STANDIN_FIT_LAST)
    try:
        prop = backtest.propose_weights(base)
    finally:
        mp.undo()
    assert prop["seasons"][1] == STANDIN_FIT_LAST
    w = {f: freeze.round_weight(v) for f, v in prop["weights"].items()}
    derived = cli.derive(raw, weights=w, **derive_inputs())
    result = holdout.evaluate_frozen(derived, w, STANDIN, STANDIN_FIT_LAST, B=100)
    return derived, w, result


SCHEMA_TOP = {"version", "seasons", "fit_last", "evaluated_at", "rerun", "reruns", "provenance", "bootstrap",
              "n", "verdict", "headline", "pass", "spearman_n8", "spearman_n4", "brier", "diff", "diagnostic",
              "factors"}


def _all_cis(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.startswith("ci_") and v is not None:
                yield v
            else:
                yield from _all_cis(v)


def test_standin_schema(standin):
    _, _, r = standin
    assert SCHEMA_TOP <= set(r)
    assert set(r["provenance"]) >= {"weights_sha256", "prereg_sha256", "git_head", "prereg_commit", "weights_commit"}
    assert set(r["bootstrap"]) >= {"B", "seed", "method", "distinct_season_resamples", "cluster_spearman",
                                   "cluster_brier"}
    assert set(r["n"]) == {"snapshots_n8", "snapshots_n4", "games"}
    assert r["verdict"] in ("yes", "slight", "no") and r["headline"] == holdout.HEADLINES[r["verdict"]]
    cands = set(holdout.SPEARMAN_CANDS)
    assert set(r["spearman_n8"]) == cands and set(r["spearman_n4"]) == cands
    for c in cands:
        e = r["spearman_n8"][c]
        assert set(e) == {"value", "ci_season", "ci_cluster", "buckets", "per_season"}
        assert set(e["buckets"]) == {"wk0", "early", "mid", "late"}
        assert set(e["per_season"]) == {"2018", "2019", "2020", "2021"}
        assert set(r["spearman_n4"][c]) == {"value", "ci_season", "ci_cluster"}
    assert set(r["brier"]) == set(holdout.BRIER_CANDS) | {"elo_538"}
    assert set(r["brier"]["elo_538"]) == {"value"}
    assert set(r["diff"]) == {"spearman_n8", "spearman_n4", "brier_vs_elo", "brier_vs_spread"}
    assert set(r["diff"]["spearman_n8"]) == {"value", "ci_season", "ci_cluster", "seasons_won", "of", "per_season"}
    diag = r["diagnostic"]["vs_exp_zeroed"]
    assert diag is not None and set(diag) == {"spearman_n8", "diff_vs_elo"}
    assert set(diag["diff_vs_elo"]) == {"value", "ci_cluster"}
    assert list(r["factors"]) == FACTORS
    for d in r["factors"].values():
        assert set(d) == {"weight", "sign", "fold_sign"}


def test_standin_composite_is_shipped_sum(standin):
    derived, w, r = standin
    f = score.zscore(derived["features"], list(w))
    comp = sum(w[k] * f[f"z_{k}"].to_numpy() for k in w)
    f = f.with_columns(pl.Series("comp_check", comp))
    tgt = backtest.targets(derived["team_games"].filter(pl.col("season") <= 2021),
                           derived["snapshots"].filter(pl.col("season") <= 2021), (8,))
    d = (f.filter(pl.col("season").is_between(*STANDIN))
         .with_columns(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32))
         .join(tgt, on=backtest.KEYS).filter(pl.col("y8").is_not_null()))
    expect = backtest.spearman(d["comp_check"].to_numpy(), d["y8"].to_numpy())
    # the result is rounded to 6 dp by backtest._clean (strict JSON); compare at that precision
    assert abs(r["spearman_n8"]["composite"]["value"] - round(expect, 6)) < 1e-12
    # no row after 2021 used: n8 is exactly the 2018-2021 rows with a target
    assert r["n"]["snapshots_n8"] == d.height
    assert d["season"].max() == 2021


def test_standin_diff_and_counts(standin):
    _, _, r = standin
    d = r["diff"]["spearman_n8"]
    assert abs(d["value"] - (r["spearman_n8"]["composite"]["value"] - r["spearman_n8"]["elo"]["value"])) < 2e-6
    assert d["of"] == 4 and 0 <= d["seasons_won"] <= 4
    assert d["seasons_won"] == sum(1 for v in d["per_season"].values() if v > 0)
    assert r["bootstrap"]["distinct_season_resamples"] == 35
    assert r["bootstrap"]["B"] == 100
    assert r["pass"] == (d["value"] > 0)
    assert r["verdict"] == holdout.verdict(d["value"], d["ci_season"], d["ci_cluster"])[0]
    assert r["n"]["games"] > 0 and r["n"]["snapshots_n4"] >= r["n"]["snapshots_n8"]


def test_standin_cis_ordered_and_strict_json(standin):
    _, _, r = standin
    cis = list(_all_cis(r))
    assert len(cis) > 20
    for lo, hi in cis:
        assert lo <= hi
    json.dumps(r, allow_nan=False)


def test_evaluate_frozen_refuses_null_factor(standin):
    # IN-06: a missing factor value must not silently count as 0 in the frozen composite
    derived, w, _ = standin
    f = next(iter(w))
    feats = derived["features"].with_columns(
        pl.when(pl.col("season") == STANDIN[0]).then(None).otherwise(pl.col(f"z_{f}")).alias(f"z_{f}"))
    with pytest.raises(ValueError, match=f"null/NaN factor values.*{f}"):
        holdout.evaluate_frozen({**derived, "features": feats}, w, STANDIN, STANDIN_FIT_LAST, B=10)


def test_standin_factors_from_doc(standin):
    derived, w, _ = standin
    doc = {"fit": {f: {"sign": freeze.sign_of(v), "fold_sign": [3, 4]} for f, v in w.items()}}
    # reuse the stand-in derived; small B keeps it quick
    r = holdout.evaluate_frozen(derived, w, STANDIN, STANDIN_FIT_LAST, weights_doc=doc, B=10)
    assert all(r["factors"][f]["fold_sign"] == [3, 4] for f in w)
    assert all(r["factors"][f]["weight"] == w[f] for f in w)


def test_render_standin(standin):
    _, _, r = standin
    md = holdout.render_markdown(r)
    assert "Verdict:" in md and "BACK-06:" in md
    for label in holdout.LABELS.values():
        assert label in md
    for f, d in r["factors"].items():
        assert f"| {f} |" in md
    assert "B=100" in md and "seed=" in md and "35 distinct" in md
    assert "pre-registered diagnostic, not used for the verdict" in md
    assert "## Reruns" not in md


def test_render_reruns_section(standin):
    _, _, r = standin
    r2 = {**r, "reruns": [{"evaluated_at": "2026-01-01T00:00:00+00:00", "verdict": "slight"}]}
    md = holdout.render_markdown(r2)
    assert "## Reruns" in md and "2026-01-01T00:00:00+00:00" in md and "slight" in md.split("## Reruns")[1]


# ---------------------------------------------------------------------------
# Provenance helpers
# ---------------------------------------------------------------------------

def test_file_sha256(tmp_path):
    p = tmp_path / "x.bin"
    p.write_bytes(b"feel good" * 1000)
    assert holdout.file_sha256(p) == hashlib.sha256(p.read_bytes()).hexdigest()


def _git(root, *args):
    subprocess.run(["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                   check=True, capture_output=True)


def _repo(tmp_path, order):
    _git(tmp_path, "init", "-q")
    for name in order:
        (tmp_path / name).write_text(f"{name}\n")
        _git(tmp_path, "add", name)
        _git(tmp_path, "commit", "-q", "-m", f"add {name}")
    return tmp_path


def test_git_state_ordered_and_clean(tmp_path):
    root = _repo(tmp_path, ["PREREGISTRATION.md", "weights.yaml"])
    st = holdout.git_state(root)
    assert st["available"] is True and st["dirty"] == [] and st["ordered"] is True
    assert st["prereg_commit"] and st["weights_commit"] and st["head"] == st["weights_commit"]
    (root / "weights.yaml").write_text("changed\n")
    assert holdout.git_state(root)["dirty"]


def test_git_state_untracked_is_dirty(tmp_path):
    root = _repo(tmp_path, ["PREREGISTRATION.md"])
    (root / "weights.yaml").write_text("new\n")
    st = holdout.git_state(root)
    assert st["dirty"] and st["ordered"] is False


def test_git_state_src_dirty(tmp_path):
    root = _repo(tmp_path, ["PREREGISTRATION.md", "weights.yaml"])
    (root / "src").mkdir()
    (root / "src" / "a.py").write_text("x = 1\n")
    st = holdout.git_state(root)
    assert st["dirty"] == [] and st["src_dirty"]


def test_git_state_wrong_order(tmp_path):
    root = _repo(tmp_path, ["weights.yaml", "PREREGISTRATION.md"])
    st = holdout.git_state(root)
    assert st["available"] is True and st["ordered"] is False


def test_git_state_prereg_unchanged(tmp_path):
    root = _repo(tmp_path, ["PREREGISTRATION.md", "weights.yaml"])
    st = holdout.git_state(root)
    assert st["prereg_unchanged"] is True and st["prereg_commits"] == 1
    assert st["prereg_last_commit"] == st["prereg_commit"]


def test_git_state_prereg_edited_after_freeze(tmp_path):
    # WR-07: an edit committed after the freeze fails both checks
    root = _repo(tmp_path, ["PREREGISTRATION.md", "weights.yaml"])
    (root / "PREREGISTRATION.md").write_text("moved the goalposts\n")
    _git(root, "commit", "-q", "-am", "edit prereg")
    st = holdout.git_state(root)
    assert st["dirty"] == [] and st["prereg_commits"] == 2
    assert st["prereg_unchanged"] is False and st["ordered"] is False
    assert st["prereg_last_commit"] != st["prereg_commit"]


def test_git_state_prereg_edited_before_freeze(tmp_path):
    # ordered, but still not the text of the adding commit
    root = _repo(tmp_path, ["PREREGISTRATION.md"])
    (root / "PREREGISTRATION.md").write_text("v2\n")
    _git(root, "commit", "-q", "-am", "edit prereg")
    (root / "weights.yaml").write_text("w\n")
    _git(root, "add", "weights.yaml")
    _git(root, "commit", "-q", "-m", "freeze")
    st = holdout.git_state(root)
    assert st["ordered"] is True and st["prereg_unchanged"] is False


def test_git_state_not_a_repo(tmp_path):
    st = holdout.git_state(tmp_path)
    assert st["available"] is False


# ---------------------------------------------------------------------------
# `fgs holdout` (mocks only: paths -> tmp, derive / evaluate_frozen patched)
# ---------------------------------------------------------------------------

FROZEN_YAML = """frozen: true
fit_seasons: [1999, 2021]
weights:
  elo: 2.59
  mov: 1.24
fit:
  elo: {raw: 2.593074, sign: "+", fold_sign: [19, 19]}
  mov: {raw: 1.240667, sign: "+", fold_sign: [19, 19]}
"""
W = {"elo": 2.59, "mov": 1.24}


def _ci_entry(v):
    return {"value": v, "ci_season": [v - 0.02, v + 0.02], "ci_cluster": [v - 0.03, v + 0.03]}


def _canned_result(seasons, fit_last):
    """A schema-complete result as evaluate_frozen would return it (numbers are made up)."""
    cands = holdout.SPEARMAN_CANDS
    ps = {str(s): 0.5 for s in range(seasons[0], seasons[1] + 1)}
    return {
        "version": 1, "seasons": list(seasons), "fit_last": fit_last, "evaluated_at": None,
        "rerun": False, "reruns": [],
        "provenance": {"weights_sha256": None, "prereg_sha256": None, "git_head": None,
                       "prereg_commit": None, "weights_commit": None},
        "bootstrap": {"B": 2000, "seed": 20221, "method": "percentile", "distinct_season_resamples": 35,
                      "cluster_spearman": "team-season stratified by season",
                      "cluster_brier": "season-week stratified by season"},
        "n": {"snapshots_n8": 100, "snapshots_n4": 100, "games": 50},
        "verdict": "slight", "headline": holdout.HEADLINES["slight"], "pass": True,
        "spearman_n8": {c: {**_ci_entry(0.5), "buckets": {b: 0.5 for b in backtest.BUCKETS}, "per_season": ps}
                        for c in cands},
        "spearman_n4": {c: _ci_entry(0.45) for c in cands},
        "brier": {**{c: _ci_entry(0.22) for c in holdout.BRIER_CANDS}, "elo_538": {"value": 0.223}},
        "diff": {"spearman_n8": {**_ci_entry(0.01), "seasons_won": 3, "of": 4, "per_season": {s: 0.01 for s in ps}},
                 "spearman_n4": _ci_entry(0.01), "brier_vs_elo": _ci_entry(-0.003),
                 "brier_vs_spread": _ci_entry(0.009)},
        "diagnostic": {"vs_exp_zeroed": {"spearman_n8": 0.49, "diff_vs_elo": {"value": -0.001,
                                                                              "ci_cluster": [-0.02, 0.02]}}},
        "factors": {"elo": {"weight": 2.59, "sign": "+", "fold_sign": [19, 19]},
                    "mov": {"weight": 1.24, "sign": "+", "fold_sign": [19, 19]}},
    }


GIT_OK = {"available": True, "dirty": [], "src_dirty": [], "prereg_commit": "a" * 40,
          "prereg_last_commit": "a" * 40, "prereg_commits": 1, "prereg_unchanged": True,
          "weights_commit": "b" * 40, "ordered": True, "head": "c" * 40}


@pytest.fixture
def holdout_paths(tmp_path, monkeypatch):
    """tmp paths for every holdout artifact; any data load or evaluation raises."""
    weights = tmp_path / "weights.yaml"
    weights.write_text(FROZEN_YAML)
    prereg = tmp_path / "PREREGISTRATION.md"
    prereg.write_text("# prereg\n")
    monkeypatch.setattr(fgs.paths, "PIPELINE_ROOT", tmp_path)
    monkeypatch.setattr(fgs.paths, "WEIGHTS_PATH", weights)
    monkeypatch.setattr(fgs.paths, "PREREG_PATH", prereg)
    monkeypatch.setattr(fgs.paths, "HOLDOUT_MD_PATH", tmp_path / "HOLDOUT_RESULT.md")
    monkeypatch.setattr(fgs.paths, "HOLDOUT_JSON_PATH", tmp_path / "HOLDOUT_RESULT.json")
    monkeypatch.setattr(cli, "DERIVED_DIR", tmp_path / "derived")
    cache = tmp_path / "cache"
    (cache / "pbp").mkdir(parents=True)
    (cache / "schedules.parquet").write_bytes(b"sched")
    (cache / "pbp" / "pbp_2022.parquet").write_bytes(b"pbp")
    monkeypatch.setattr(cli, "CACHE_DIR", cache)
    monkeypatch.setattr(cli, "SIM_CACHE_DIR", tmp_path / "sim")
    (tmp_path / "uv.lock").write_text("lock\n")

    def boom(*a, **k):
        raise AssertionError("a holdout guard let execution reach data loading / evaluation")

    for name in ("derive", "load_schedules", "cached_inputs"):
        monkeypatch.setattr(cli, name, boom)
    monkeypatch.setattr(holdout, "evaluate_frozen", boom)
    monkeypatch.setattr(holdout, "git_state", lambda root, *a, **k: dict(GIT_OK))
    return tmp_path


def test_holdout_guard_already_evaluated(holdout_paths, capsys):
    (holdout_paths / "HOLDOUT_RESULT.md").write_text("done\n")
    assert cli.main(["holdout"]) == 1
    assert "already evaluated" in capsys.readouterr().err


def test_holdout_guard_json_only(holdout_paths, capsys):
    # WR-01: a surviving HOLDOUT_RESULT.json (e.g. the .md write failed or was deleted) still refuses
    (holdout_paths / "HOLDOUT_RESULT.json").write_text("{}\n")
    assert cli.main(["holdout"]) == 1
    err = capsys.readouterr().err
    assert "already evaluated" in err and "HOLDOUT_RESULT.json" in err


def test_holdout_guard_derived_only(holdout_paths, capsys):
    (holdout_paths / "derived").mkdir()
    (holdout_paths / "derived" / "holdout.json").write_text("{}\n")
    assert cli.main(["holdout"]) == 1
    assert "already evaluated" in capsys.readouterr().err


def test_holdout_guard_not_frozen(holdout_paths, capsys):
    (holdout_paths / "weights.yaml").write_text(FROZEN_YAML.replace("frozen: true", "frozen: false"))
    assert cli.main(["holdout"]) == 1
    assert "not frozen" in capsys.readouterr().err


def test_holdout_guard_weights_missing(holdout_paths, capsys):
    (holdout_paths / "weights.yaml").unlink()
    assert cli.main(["holdout"]) == 1
    assert "not frozen" in capsys.readouterr().err


def test_holdout_guard_weights_malformed(holdout_paths, capsys):
    # IN-07: a YAML error is a clear message, not a traceback
    (holdout_paths / "weights.yaml").write_text("frozen: true\nweights: {elo: [1,\n")
    assert cli.main(["holdout"]) == 1
    err = capsys.readouterr().err
    assert "not valid YAML" in err and "not frozen" in err


def test_holdout_guard_prereg_missing(holdout_paths, capsys):
    (holdout_paths / "PREREGISTRATION.md").unlink()
    assert cli.main(["holdout"]) == 1
    assert "PREREGISTRATION.md is missing" in capsys.readouterr().err


def test_holdout_guard_dirty(holdout_paths, monkeypatch, capsys):
    monkeypatch.setattr(holdout, "git_state", lambda root, *a, **k: {**GIT_OK, "dirty": [" M weights.yaml"]})
    assert cli.main(["holdout"]) == 1
    assert "weights.yaml" in capsys.readouterr().err


def test_holdout_guard_src_dirty(holdout_paths, monkeypatch, capsys):
    monkeypatch.setattr(holdout, "git_state",
                        lambda root, *a, **k: {**GIT_OK, "src_dirty": [" M src/fgs/score.py"]})
    assert cli.main(["holdout"]) == 1
    assert "src/fgs/score.py" in capsys.readouterr().err


def test_holdout_guard_order(holdout_paths, monkeypatch, capsys):
    monkeypatch.setattr(holdout, "git_state", lambda root, *a, **k: {**GIT_OK, "ordered": False})
    assert cli.main(["holdout"]) == 1
    assert "pre-registration" in capsys.readouterr().err.lower()


def test_holdout_guard_prereg_changed(holdout_paths, monkeypatch, capsys):
    monkeypatch.setattr(holdout, "git_state", lambda root, *a, **k: {**GIT_OK, "prereg_unchanged": False})
    assert cli.main(["holdout"]) == 1
    assert "changed after the commit" in capsys.readouterr().err


def test_holdout_git_unavailable_warns_and_continues(holdout_paths, monkeypatch, capsys):
    monkeypatch.setattr(holdout, "git_state", lambda root, *a, **k: {
        "available": False, "dirty": [], "src_dirty": [], "prereg_commit": None, "weights_commit": None,
        "ordered": False, "head": None})
    monkeypatch.setattr(cli, "load_schedules", lambda *a, **k: None)
    monkeypatch.setattr(cli, "cached_inputs", lambda *a, **k: {})
    reached = {}

    def stub_derive(*a, **k):
        reached["derive"] = True
        raise RuntimeError("stub derive reached")

    monkeypatch.setattr(cli, "derive", stub_derive)
    with pytest.raises(RuntimeError, match="stub derive reached"):
        cli.main(["holdout"])
    assert reached == {"derive": True}
    assert "warning" in capsys.readouterr().err


@pytest.fixture
def happy(holdout_paths, monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "load_schedules", lambda *a, **k: None)
    monkeypatch.setattr(cli, "cached_inputs", lambda *a, **k: {})
    monkeypatch.setattr(cli, "derive", lambda *a, **k: {"weights": dict(W)})

    def fake_eval(derived, weights, seasons, fit_last, **kw):
        calls.append({"derived": derived, "weights": weights, "seasons": seasons, "fit_last": fit_last, **kw})
        return _canned_result(seasons, fit_last)

    monkeypatch.setattr(holdout, "evaluate_frozen", fake_eval)
    return holdout_paths, calls


def test_holdout_happy_path_writes_files(happy, capsys):
    root, calls = happy
    assert cli.main(["holdout"]) == 0
    (call,) = calls
    from fgs.season_config import HOLDOUT_SEASONS, TRAIN_LAST_SEASON
    assert call["seasons"] == HOLDOUT_SEASONS and call["fit_last"] == TRAIN_LAST_SEASON
    assert call["allow_holdout"] is True
    assert call["weights"] == W and call["weights_doc"]["fit"]["elo"]["fold_sign"] == [19, 19]

    data = json.loads((root / "HOLDOUT_RESULT.json").read_text())
    json.dumps(data, allow_nan=False)
    prov = data["provenance"]
    assert prov["weights_sha256"] == hashlib.sha256((root / "weights.yaml").read_bytes()).hexdigest()
    assert prov["prereg_sha256"] == hashlib.sha256((root / "PREREGISTRATION.md").read_bytes()).hexdigest()
    assert prov["git_head"] == GIT_OK["head"] and prov["prereg_commit"] == GIT_OK["prereg_commit"]
    assert prov["weights_commit"] == GIT_OK["weights_commit"] and prov["src_clean"] is True
    assert prov["prereg_last_commit"] == GIT_OK["prereg_last_commit"] and prov["prereg_unchanged"] is True
    sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731
    assert prov["inputs"] == {
        "cache": {"pbp/pbp_2022.parquet": sha(b"pbp"), "schedules.parquet": sha(b"sched")},
        "sim_cache": {}, "uv_lock_sha256": sha(b"lock\n"),
    }
    assert data["evaluated_at"] and data["rerun"] is False and data["reruns"] == []
    assert (root / "HOLDOUT_RESULT.md").read_text().startswith("# Holdout result")
    assert json.loads((root / "derived" / "holdout.json").read_text()) == data
    out = capsys.readouterr().out
    assert "Verdict: slight" in out and "BACK-06: PASS" in out and "wrote" in out


def test_holdout_force_records_rerun(happy, capsys):
    root, calls = happy
    assert cli.main(["holdout"]) == 0
    first = json.loads((root / "HOLDOUT_RESULT.json").read_text())
    assert cli.main(["holdout"]) == 1  # refused without --force
    assert len(calls) == 1
    assert cli.main(["holdout", "--force"]) == 0
    second = json.loads((root / "HOLDOUT_RESULT.json").read_text())
    assert second["rerun"] is True
    assert second["reruns"] == [{"evaluated_at": first["evaluated_at"], "verdict": first["verdict"]}]
    assert "## Reruns" in (root / "HOLDOUT_RESULT.md").read_text()


def test_holdout_force_records_rerun_when_md_missing(happy):
    # WR-01: the previous result is recorded from the JSON even if the .md is gone
    root, _ = happy
    assert cli.main(["holdout"]) == 0
    first = json.loads((root / "HOLDOUT_RESULT.json").read_text())
    (root / "HOLDOUT_RESULT.md").unlink()
    assert cli.main(["holdout"]) == 1
    assert cli.main(["holdout", "--force"]) == 0
    second = json.loads((root / "HOLDOUT_RESULT.json").read_text())
    assert second["rerun"] is True and second["reruns"][-1]["evaluated_at"] == first["evaluated_at"]


def test_holdout_render_failure_writes_nothing(happy, monkeypatch):
    root, _ = happy

    def bad_render(result):
        raise RuntimeError("render failed")

    monkeypatch.setattr(holdout, "render_markdown", bad_render)
    with pytest.raises(RuntimeError, match="render failed"):
        cli.main(["holdout"])
    assert not (root / "HOLDOUT_RESULT.json").exists() and not (root / "HOLDOUT_RESULT.md").exists()
    assert not list(root.glob("*.tmp"))


def test_holdout_opt_in_only_in_cli():
    import pathlib

    src = pathlib.Path(holdout.__file__).parent
    hits = [p.name for p in src.glob("*.py") for line in p.read_text().splitlines()
            if "allow_holdout=" + "True" in line]
    assert hits == ["cli.py"]

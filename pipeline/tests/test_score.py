import re
from pathlib import Path

import numpy as np
import polars as pl
import pytest

import fgs.score as score_mod
from fgs.score import FACTORS, composite, contrib_columns, load_weights, zscore

W = {"elo": 4.58, "season_record": 0.63, "last16": -1.25}


def _frame(seed=7, seasons=3, weeks=3, teams=10) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for s in range(2000, 2000 + seasons):
        for w in range(weeks):
            for t in range(teams):
                rows.append((s, w, f"T{t}", 1505 + rng.normal(0, 80), rng.uniform(0, 1), rng.uniform(0, 1)))
    return pl.DataFrame(
        rows, schema=["season", "week", "franchise_id", "elo", "season_record", "last16"], orient="row"
    )


def test_additivity():
    out = composite(_frame(), W)
    assert out.columns[-1] == "composite"
    s = out.select(pl.sum_horizontal(contrib_columns(W))).to_series().to_numpy()
    assert np.max(np.abs(s - out["composite"].to_numpy())) < 1e-9
    for f, w in W.items():
        assert np.allclose(out[f"contrib_{f}"].to_numpy(), w * out[f"z_{f}"].to_numpy(), atol=1e-12)


def test_zero_variance_snapshot_gives_zero_z():
    df = _frame().with_columns(
        pl.when((pl.col("season") == 2000) & (pl.col("week") == 0)).then(0.5)
        .otherwise(pl.col("season_record")).alias("season_record")
    )
    out = composite(df, W)
    snap = out.filter((pl.col("season") == 2000) & (pl.col("week") == 0))
    assert (snap["z_season_record"] == 0.0).all()
    assert out.null_count().sum_horizontal().item() == 0
    assert not out.select(pl.col(pl.Float64).is_nan().any()).to_numpy().any()


def test_zscore_per_snapshot_mean0_std1():
    out = zscore(_frame(), ["elo", "last16"])
    g = out.group_by("season", "week").agg(
        pl.col("z_elo").mean().alias("m"), pl.col("z_elo").std(ddof=0).alias("s"),
        pl.col("z_last16").mean().alias("m2"), pl.col("z_last16").std(ddof=0).alias("s2"),
    )
    assert np.allclose(g["m"].to_numpy(), 0, atol=1e-9) and np.allclose(g["s"].to_numpy(), 1, atol=1e-9)
    assert np.allclose(g["m2"].to_numpy(), 0, atol=1e-9) and np.allclose(g["s2"].to_numpy(), 1, atol=1e-9)


def test_composite_requires_factor_columns():
    with pytest.raises(ValueError):
        composite(_frame().drop("last16"), W)


def test_load_weights_reads_yaml_in_order(tmp_path):
    p = tmp_path / "w.yaml"
    p.write_text("# provenance comment\nweights:\n  last16: -1.25  # negative\n  elo: 4.58\n  season_record: 1\n")
    w = load_weights(p)
    assert list(w) == ["last16", "elo", "season_record"]
    assert w == {"last16": -1.25, "elo": 4.58, "season_record": 1.0}


@pytest.mark.parametrize(
    "body",
    [
        "weights:\n  elo: 1.0\n  vibes: 2.0\n",  # unknown key
        "weights:\n  elo: high\n",  # not a number
        "weights:\n  elo: .nan\n",  # not finite
        "weights: {}\n",  # empty
        "nothing: here\n",  # no mapping
    ],
)
def test_load_weights_rejects_bad_files(tmp_path, body):
    p = tmp_path / "w.yaml"
    p.write_text(body)
    with pytest.raises(ValueError):
        load_weights(p)


def test_load_weights_missing_file(tmp_path):
    with pytest.raises(ValueError):
        load_weights(tmp_path / "nope.yaml")


def test_factors_have_labels():
    for k, v in FACTORS.items():
        assert v["label"] and v["description"], k


def test_firewall_no_backtest_import():
    src = Path(score_mod.__file__).read_text()
    code = "\n".join(re.sub(r"#.*$", "", line) for line in src.splitlines())
    assert "backtest" not in code


# ---------------------------------------------------------------------------
# Offseason draft term: load_offseason / apply_offseason (plan 07-03)
# ---------------------------------------------------------------------------

from fgs.score import OFFSEASON_FACTORS, apply_offseason, load_offseason  # noqa: E402

BASE_YAML = "frozen: true\nweights:\n  elo: 1.0\nfit:\n  elo: {raw: 1.0, sign: \"+\", fold_sign: [19, 19]}\n"
OFF_YAML = (
    "offseason:\n  draft:\n    weight: 0.00\n    display_only: true\n    chart: stuart\n"
    "    winsor: [-17.29, 16.19]\n    decay: linear_to0_by_wk4\n    fit_seasons: 2000-2021\n"
    "    test_seasons: 2003-2021\n    fitted: -0.2500\n    fold_sign: \"7/19\"\n    delta_wk0: 0.0002\n"
    "    evidence: training-only walk-forward (no fresh holdout)\n"
)


def _w(tmp_path, text):
    p = tmp_path / "w.yaml"
    p.write_text(text)
    return p


def test_load_offseason_missing_block(tmp_path):
    c = load_offseason(_w(tmp_path, BASE_YAML))
    assert c["weight"] == 0.0 and c["display_only"] is True and c["winsor"] is None
    assert c["decay"] == [1.0, 0.75, 0.5, 0.25]


def test_load_offseason_full_block(tmp_path):
    p = _w(tmp_path, BASE_YAML + OFF_YAML)
    c = load_offseason(p)
    assert c == {"weight": 0.0, "display_only": True, "chart": "stuart", "winsor": (-17.29, 16.19),
                 "decay": [1.0, 0.75, 0.5, 0.25]}
    assert load_weights(p) == {"elo": 1.0}


@pytest.mark.parametrize("bad", [
    ("weight: 0.00", "weight: abc"), ("weight: 0.00", "weight: .nan"),
    ("winsor: [-17.29, 16.19]", "winsor: [5, 1]"), ("winsor: [-17.29, 16.19]", "winsor: [1]"),
    ("decay: linear_to0_by_wk4", "decay: flat"),
])
def test_load_offseason_invalid(tmp_path, bad):
    with pytest.raises(ValueError):
        load_offseason(_w(tmp_path, BASE_YAML + OFF_YAML.replace(*bad)))


@pytest.mark.parametrize("w,disp", [("0.30", "true"), ("0.00", "false"), ("0.004", "true")])
def test_load_offseason_display_only_must_match_weight(tmp_path, w, disp):
    """WR-01: display_only must be true exactly when weight is 0, or the score could move while
    the metadata says "display only"."""
    text = OFF_YAML.replace("weight: 0.00", f"weight: {w}").replace("display_only: true", f"display_only: {disp}")
    with pytest.raises(ValueError, match="display_only"):
        load_offseason(_w(tmp_path, BASE_YAML + text))


def test_offseason_live_single_source():
    from fgs.score import offseason_live

    assert offseason_live({"weight": 0.0, "display_only": True}) is False
    assert offseason_live({"weight": 0.004, "display_only": False}) is True
    assert offseason_live({"weight": 0.0}) is False
    with pytest.raises(ValueError):
        offseason_live({"weight": 0.3, "display_only": True})
    with pytest.raises(ValueError):
        apply_offseason(_off_frame(), DRAFT_Z, {"weight": 0.3, "display_only": True})


def _off_frame():
    rows = [(2020, wk, t, float(i) + 0.1 * wk) for wk in range(6) for i, t in enumerate(["A", "B", "C"])]
    return pl.DataFrame(rows, schema=["season", "week", "franchise_id", "composite"], orient="row")


DRAFT_Z = pl.DataFrame({"season": [2020, 2020], "franchise_id": ["A", "B"], "surplus": [10.0, -10.0],
                        "draft_z": [1.2, -1.2]})


def test_apply_offseason_weight_zero_is_display_only():
    f = _off_frame()
    out = apply_offseason(f, DRAFT_Z, {"weight": 0.0, "display_only": True, "winsor": (-1, 1)})
    assert "contrib_draft" not in out.columns
    assert out["composite"].to_list() == f["composite"].to_list()
    assert out["composite_inseason"].to_list() == f["composite"].to_list()
    c = out.filter(pl.col("franchise_id") == "C")
    assert c["draft_surplus"].null_count() == c.height and c["draft_z"].to_list() == [0.0] * c.height
    assert out["draft_surplus"].dtype == pl.Float64 and out["draft_z"].dtype == pl.Float64
    # no draft frame at all
    out2 = apply_offseason(f, None, {"weight": 0.0})
    assert out2["draft_surplus"].null_count() == f.height and (out2["draft_z"] == 0.0).all()


def test_apply_offseason_fake_weight_decays():
    f = _off_frame()
    out = apply_offseason(f, DRAFT_Z, {"weight": 1.0, "display_only": False, "winsor": (-1, 1)})
    a = out.filter(pl.col("franchise_id") == "A").sort("week")
    assert np.allclose(a["contrib_draft"].to_numpy(), 1.2 * np.array([1, .75, .5, .25, 0, 0]))
    assert np.allclose(out["composite"].to_numpy(),
                       (out["composite_inseason"] + out["contrib_draft"]).to_numpy())
    assert out.filter(pl.col("week") >= 4)["contrib_draft"].abs().max() == 0


def test_offseason_draft_not_in_factors():
    assert len(FACTORS) == 11 and "draft" not in FACTORS and "draft" in OFFSEASON_FACTORS


def test_offseason_reference_stays_inseason():
    from fgs import mood

    rng = np.random.default_rng(5)
    rows = [(s, wk, f"T{t}", float(rng.normal())) for s in (2000, 2001) for wk in range(8) for t in range(8)]
    f = pl.DataFrame(rows, schema=["season", "week", "franchise_id", "composite"], orient="row")
    dz = pl.DataFrame({"season": [2000, 2001] * 4, "franchise_id": [f"T{t}" for t in range(8)],
                       "surplus": [float(t) for t in range(8)], "draft_z": [float(t) - 3.5 for t in range(8)]})
    z0 = apply_offseason(f, dz, {"weight": 0.0})
    z1 = apply_offseason(f, dz, {"weight": 1.0})
    r0, r1 = mood.reference_values(z0, ref_seasons=(2000, 2001)), mood.reference_values(z1, ref_seasons=(2000, 2001))
    assert np.array_equal(r0, r1)
    s0 = mood.score_frame(z0, ref_seasons=(2000, 2001)).sort("season", "week", "franchise_id")
    s1 = mood.score_frame(z1, ref_seasons=(2000, 2001)).sort("season", "week", "franchise_id")
    late = pl.col("week") >= 4
    assert s0.filter(late)["score"].to_list() == s1.filter(late)["score"].to_list()


def test_offseason_add_points_sum_with_draft():
    from fgs import explain, mood

    rng = np.random.default_rng(9)
    rows = [(s, wk, f"T{t}", float(rng.normal()), float(rng.uniform()), float(rng.uniform()))
            for s in (2000, 2001) for wk in range(6) for t in range(10)]
    f = pl.DataFrame(rows, schema=["season", "week", "franchise_id", "elo", "season_record", "last16"], orient="row")
    f = composite(f, W)
    dz = pl.DataFrame({"season": [s for s in (2000, 2001) for _ in range(10)],
                       "franchise_id": [f"T{t}" for _ in (0, 1) for t in range(10)],
                       "surplus": [float(t) for _ in (0, 1) for t in range(10)],
                       "draft_z": [(t - 4.5) / 3 for _ in (0, 1) for t in range(10)]})
    f = apply_offseason(f, dz, {"weight": 1.0})
    scored = mood.score_frame(f, ref_seasons=(2000, 2001))
    ref = mood.reference_values(f, ref_seasons=(2000, 2001))
    keys = list(W) + ["draft"]
    out = explain.add_points(scored, keys, ref)
    tot = out.select(pl.sum_horizontal([f"pts_{k}" for k in keys])).to_series().to_numpy()
    assert np.array_equal(tot, out["score"].to_numpy() - explain.baseline(ref))


def test_derive_games_adds_offseason_display_columns(synthetic_games):
    from fgs import cli

    w = {k: 0.1 for k in FACTORS}
    d = cli.derive_games(synthetic_games, weights=w, offseason={"weight": 0.0, "display_only": True,
                                                                 "chart": "stuart", "winsor": None,
                                                                 "decay": [1.0, .75, .5, .25]})
    f = d["features"]
    assert {"composite_inseason", "draft_surplus", "draft_z"} <= set(f.columns) and "contrib_draft" not in f.columns
    assert f["draft_surplus"].null_count() == f.height and (f["draft_z"] == 0.0).all()
    assert d["offseason"]["weight"] == 0.0

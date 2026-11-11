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

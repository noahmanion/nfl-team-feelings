"""Phase 6 weight freeze: the final Ridge weights plus their walk-forward evidence.

DEV-ONLY, like backtest: it imports the evaluation harness, so score/features/export/mood/explain
must never import it (leakage firewall). `fgs freeze` (cli._cmd_freeze) is the only caller that
writes files; everything here is pure apart from reading the clock for `fitted_at`.

The fit is the existing proposal (backtest.propose_weights: ridge on per-snapshot z-scores,
unpenalized intercept, alpha by choose_alpha LOSO CV over 1999-2021, N=8 target), rounded to 2 dp.
No clipping, no pruning, no sign constraint (MODEL-15): negative and ~0 weights are kept as fitted.
Nothing here reads a season after 2021 (TRAIN_LAST_SEASON); see pipeline/PREREGISTRATION.md.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import numpy as np
import polars as pl
import yaml

from fgs import backtest, bootstrap

VERSION = 1
TARGET_NAME = "adjusted_margin_n8"
SPEARMAN_CANDS = ("composite", "elo", "season_wpct", "last16", "pd_pg")
BRIER_CANDS = ("composite", "elo", "season_wpct", "last16", "pd_pg", "spread")
LOG_TOL = 0.0005

# Why a factor's fitted weight is negative (carried over from the interim weights.yaml comments).
# Only emitted when the frozen sign is "-".
WHY = {
    "last16": "given Elo, a hot recent record runs ahead of real strength and regresses",
    "sow": "given Elo and margins, results running ahead of margins regress",
    "streak": "given the rest, a hot streak slightly fades (~0 backtest gain, kept)",
    "luck": "close-game wins and losses are mostly coin flips, so they even out",
    "epa_traj": "given the rest, an efficiency upswing slightly fades (~0 backtest gain, kept)",
    "vs_exp": "~ season_record minus preseason expectation; read the pair together (corr 0.92); "
              "beating expectations tends to fade",
    "po_trend": "~0; Elo's 3-week change already carries it (corr 0.70); kept so the weight is on record",
}


# ---------------------------------------------------------------------------
# Rounding and signs
# ---------------------------------------------------------------------------

def round_weight(v: float) -> float:
    """2-dp weight; + 0.0 turns -0.0 into 0.0 so "-0.00" can never appear."""
    return round(float(v), 2) + 0.0


def format_weight(v: float) -> str:
    return f"{round_weight(v):.2f}"


def sign_of(w: float) -> str:
    return "+" if w > 0 else "-" if w < 0 else "0"


def fold_sign_consistency(folds: list[dict], final_raw: dict[str, float]) -> dict[str, list[int]]:
    """Per factor: [number of walk-forward folds whose weight sign equals the final fit's sign, n folds]."""
    out = {}
    for f, raw in final_raw.items():
        s = np.sign(raw)
        k = sum(1 for fold in folds if np.sign(fold["weights"][f]) == s)
        out[f] = [int(k), len(folds)]
    return out


# ---------------------------------------------------------------------------
# Factor deltas (computed) and the BACKTEST_LOG.md cross-check
# ---------------------------------------------------------------------------

def _n8(report: dict, name: str) -> float | None:
    return report["candidates"][name]["N8"]["all"]["spearman"]


def factor_deltas(report: dict, ridge_sets: dict | None = None) -> dict[str, dict]:
    """Δ Spearman N=8 when each factor joins, in RIDGE_SETS insertion order. The first set's single
    factor (elo) is the baseline: delta None, baseline_spearman_n8 = its absolute value."""
    ridge_sets = backtest.RIDGE_SETS if ridge_sets is None else ridge_sets
    names = list(ridge_sets)
    out: dict[str, dict] = {}
    first = names[0]
    (base_factor,) = ridge_sets[first]
    out[base_factor] = {"delta_spearman_n8": None, "baseline_spearman_n8": _n8(report, first)}
    for prev, cur in zip(names, names[1:]):
        added = [f for f in ridge_sets[cur] if f not in ridge_sets[prev]]
        a, b = _n8(report, cur), _n8(report, prev)
        for f in added:
            out[f] = {"delta_spearman_n8": None if a is None or b is None else a - b, "baseline_spearman_n8": None}
    return out


_NUM = re.compile(r"[+\-]?\d+(?:\.\d+)?")
_SEP = re.compile(r"^\s*:?-{3,}:?\s*$")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_backtest_log(text: str, col: str = "ΔSpearman (N=8)") -> dict[str, float]:
    """{factor: number in the ΔSpearman (N=8) cell} from BACKTEST_LOG.md tables.

    A header row is any table row followed by a `---` separator row; cells are matched by header
    name, so column order and extra columns don't matter. Unicode minus is accepted, the
    "(baseline)" row yields its absolute value, and the first row per factor wins."""
    lines = [ln for ln in text.splitlines()]
    out: dict[str, float] = {}
    header: list[str] | None = None
    for i, line in enumerate(lines):
        if not line.strip().startswith("|"):
            header = None
            continue
        cells = _cells(line)
        if all(_SEP.match(c) for c in cells if c) and any(cells):
            continue  # separator row
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if nxt.strip().startswith("|") and all(_SEP.match(c) for c in _cells(nxt) if c) and any(_cells(nxt)):
            header = cells
            continue
        if header is None or "Factor" not in header or col not in header:
            continue
        row = dict(zip(header, cells))
        key = row.get("Factor", "").strip("` ")
        if not key or key in out:
            continue
        m = _NUM.search(row.get(col, "").replace("−", "-"))
        if m:
            out[key] = float(m.group())
    return out


def _crosscheck(factors: dict[str, dict], logged: dict[str, float] | None) -> dict:
    if logged is None:
        return {"max_abs_diff": None, "warnings": ["BACKTEST_LOG.md not available; deltas not cross-checked"]}
    warnings, diffs = [], []
    for f, d in factors.items():
        computed = d["delta_spearman_n8"] if d["delta_spearman_n8"] is not None else d["baseline_spearman_n8"]
        if f not in logged:
            warnings.append(f"{f}: no row in BACKTEST_LOG.md")
            continue
        if computed is None:
            warnings.append(f"{f}: computed delta undefined")
            continue
        diff = abs(computed - logged[f])
        diffs.append(diff)
        if diff > LOG_TOL:
            warnings.append(f"{f}: computed {computed:+.4f} vs logged {logged[f]:+.4f} (|diff| {diff:.4f})")
    return {"max_abs_diff": max(diffs) if diffs else None, "warnings": warnings}


# ---------------------------------------------------------------------------
# Walk-forward evidence with paired bootstrap CIs
# ---------------------------------------------------------------------------

def _ci(boot: dict, name: str, kind: str = "stats"):
    return boot[kind][name]["ci"]


def _spearman_block(rows: pl.DataFrame, n: int, B: int, seed: int) -> tuple[dict, dict]:
    y_col = f"y{n}"
    d = rows.filter(pl.col(y_col).is_not_null())
    cols = {"composite": "composite", **backtest.CANDIDATES}
    y = d[y_col].to_numpy().astype(float)
    xs = {c: d[cols[c]].to_numpy().astype(float) for c in SPEARMAN_CANDS}
    season = d["season"].to_numpy()

    def fn(c):
        x = xs[c]
        return lambda idx: backtest.spearman(x[idx], y[idx])

    fns = {c: fn(c) for c in SPEARMAN_CANDS}
    diffs = {"diff": ("composite", "elo")}
    blocks = bootstrap.season_blocks(season)
    strata = bootstrap.stratified_clusters(season, d["franchise_id"].to_numpy())
    bs = bootstrap.paired_bootstrap(fns, lambda r: bootstrap.draw_blocks(r, blocks), diffs=diffs, B=B, seed=seed)
    bc = bootstrap.paired_bootstrap(fns, lambda r: bootstrap.draw_stratified(r, strata), diffs=diffs, B=B, seed=seed)
    all_idx = np.arange(len(y))
    block = {
        c: {"value": fns[c](all_idx), "ci_season": _ci(bs, c), "ci_cluster": _ci(bc, c)} for c in SPEARMAN_CANDS
    }
    comp, elo = block["composite"]["value"], block["elo"]["value"]
    won = 0
    uniq = sorted(int(s) for s in np.unique(season))
    for s in uniq:
        idx = np.flatnonzero(season == s)
        a, b = fns["composite"](idx), fns["elo"](idx)
        won += int(a is not None and b is not None and a > b)
    diff = {
        "value": None if comp is None or elo is None else comp - elo,
        "ci_season": _ci(bs, "diff", "diffs"), "ci_cluster": _ci(bc, "diff", "diffs"),
        "seasons_won": won, "of": len(uniq),
    }
    return block, diff


def _brier_block(games: pl.DataFrame, B: int, seed: int) -> tuple[dict, dict, int]:
    y = games["y"].to_numpy().astype(float)
    sq = {c: (games[f"p_{c}"].to_numpy().astype(float) - y) ** 2 for c in BRIER_CANDS}
    fns = {c: (lambda idx, e=sq[c]: float(np.mean(e[idx]))) for c in BRIER_CANDS}
    diffs = {"brier_vs_elo": ("composite", "elo"), "brier_vs_spread": ("composite", "spread")}
    season = games["season"].to_numpy()
    blocks = bootstrap.season_blocks(season)
    strata = bootstrap.stratified_clusters(season, games["asof_week"].to_numpy())
    bs = bootstrap.paired_bootstrap(fns, lambda r: bootstrap.draw_blocks(r, blocks), diffs=diffs, B=B, seed=seed)
    bc = bootstrap.paired_bootstrap(fns, lambda r: bootstrap.draw_stratified(r, strata), diffs=diffs, B=B, seed=seed)
    val = {c: float(np.mean(sq[c])) for c in BRIER_CANDS}
    block = {c: {"value": val[c], "ci_season": _ci(bs, c), "ci_cluster": _ci(bc, c)} for c in BRIER_CANDS}
    block["elo_538"] = {"value": float(np.mean((games["p_elo_538"].to_numpy() - y) ** 2))}
    diff = {
        name: {"value": val[a] - val[b], "ci_season": _ci(bs, name, "diffs"), "ci_cluster": _ci(bc, name, "diffs")}
        for name, (a, b) in diffs.items()
    }
    return block, diff, int(len(y))


def walk_forward_ci(wf: dict, B: int = bootstrap.B_DEFAULT, seed: int = bootstrap.SEED) -> dict:
    """FREEZE_RESULT "walk_forward" block from backtest.walk_forward_frame (test seasons <= 2021).

    Spearman N=8/N=4 (pooled snapshots, each N on its own non-null-target rows): season-block and
    team-season cluster (franchise within season) bootstraps. Brier (next game, the common game
    set where every candidate has a probability): season-block and season-week cluster bootstraps.
    Every candidate is evaluated on the same draws (paired); "value" is the full-sample estimate."""
    seasons = wf["seasons"]
    if seasons[-1] > backtest.test_seasons(False)[-1]:
        raise ValueError("freeze evidence is walk-forward on training seasons only (<= 2021)")
    sp8, d8 = _spearman_block(wf["rows"], 8, B, seed)
    sp4, _ = _spearman_block(wf["rows"], 4, B, seed)
    br, dbr, n_games = _brier_block(wf["games"], B, seed)
    return {
        "seasons": [seasons[0], seasons[-1]],
        "composite_set": list(backtest.RIDGE_SETS)[-1],
        "bootstrap": {
            "B": int(B), "seed": int(seed), "method": "percentile",
            "cluster_spearman": "team-season stratified by season",
            "cluster_brier": "season-week stratified by season",
        },
        "spearman_n8": sp8,
        "spearman_n4": sp4,
        "brier": br,
        "n_games": n_games,
        "diff": {"spearman_n8": d8, **dbr},
    }


# ---------------------------------------------------------------------------
# The freeze
# ---------------------------------------------------------------------------

def build_freeze(derived: dict, *, B: int = bootstrap.B_DEFAULT, seed: int = bootstrap.SEED,
                 log_text: str | None = None) -> dict:
    """FREEZE_RESULT dict: final 1999-2021 fit (existing LOSO-alpha proposal), rounded weights,
    signs, fold-sign consistency over the 19 walk-forward folds, factor deltas and walk-forward
    CIs. Nothing after 2021 is read (propose_weights / walk_forward_frame drop it first)."""
    prop = backtest.propose_weights(derived)
    report = backtest.run_backtest(derived)
    wf = backtest.walk_forward_frame(derived)
    last = list(backtest.RIDGE_SETS)[-1]
    folds = wf["ridge"][last]["folds"]
    raw = {f: prop["weights"][f] for f in backtest.PROPOSAL_FACTORS}
    fs = fold_sign_consistency(folds, raw)
    deltas = factor_deltas(report)
    factors = {}
    for f in backtest.PROPOSAL_FACTORS:
        w = round_weight(raw[f])
        factors[f] = {
            "raw": raw[f], "weight": w, "sign": sign_of(w), "fold_sign": fs[f],
            "delta_spearman_n8": deltas[f]["delta_spearman_n8"],
            "baseline_spearman_n8": deltas[f]["baseline_spearman_n8"],
        }
    logged = None if log_text is None else parse_backtest_log(log_text)
    result = {
        "version": VERSION,
        "fitted_at": datetime.now(timezone.utc).date().isoformat(),
        "fit_seasons": list(prop["seasons"]),
        "target": TARGET_NAME,
        "alpha": prop["alpha"],
        "n": prop["n"],
        "walk_forward": walk_forward_ci(wf, B, seed),
        "factors": factors,
        "log_crosscheck": _crosscheck(factors, logged),
    }
    out = backtest._clean(result)
    # _clean rounds to 6 dp; keep the 2-dp weights exact and free of -0.0
    for f, d in out["factors"].items():
        d["weight"] = round_weight(d["weight"])
    return out


# ---------------------------------------------------------------------------
# weights.yaml (text template so the comments survive)
# ---------------------------------------------------------------------------

def _num(v: float) -> str:
    s = f"{float(v):.6f}"
    return "0.000000" if s == "-0.000000" else s


def render_weights_yaml(freeze: dict) -> str:
    factors = freeze["factors"]
    lo, hi = freeze["fit_seasons"]
    alpha, n, date = freeze["alpha"], freeze["n"], freeze["fitted_at"]
    lines = [
        "# Feel-good score weights: the single source of truth (read by fgs.score.load_weights).",
        "#",
        "# composite = sum over factors of weight * z, where z is the factor's z-score across the",
        "# teams in the same (season, week) snapshot. Units: points of opponent/venue-adjusted",
        "# margin per game (next 8 games) per standard deviation of the factor. No intercept.",
        "#",
        f"# FROZEN (Phase 6): written by `uv run fgs freeze` on {date}. Refits are refused; see",
        "# pipeline/PREREGISTRATION.md. Do not hand-edit: the weekly refresh/export never refit (BACK-04).",
        "#",
        "# Procedure: Ridge on the per-snapshot z-scores, unpenalized intercept; alpha chosen by",
        f"# choose_alpha (leave-one-season-out CV over {lo}-{hi}, grid {{0, 1e-3, 1e-2, 1e-1, 1}}*n,",
        f"# min pooled SSE): alpha = {alpha:g}*n, n = {n} snapshots; target = mean adjusted margin over",
        "# the next 8 games. Weights rounded to 2 dp; no clipping, pruning or sign constraint (MODEL-15).",
        "# The 2022-2025 holdout was never read.",
        "#",
        "# Per factor: weight, unrounded fit, sign, and how many of the walk-forward folds",
        f"# (test seasons 2003-{hi}, each refit on earlier seasons) agree with the final sign:",
    ]
    for f, d in factors.items():
        k, nf = d["fold_sign"]
        lines.append(f"#   {f:<14} {format_weight(d['weight']):>6}  raw {d['raw']:+.4f}  sign {d['sign']}  folds {k}/{nf}")
        if d["sign"] == "-" and f in WHY:
            lines.append(f"#       why -: {WHY[f]}")
        elif d["sign"] == "0":
            lines.append("#       ~0, kept (MODEL-15): the data sets it; shown so the weight is on record")
    lines += [
        "#",
        "# Full walk-forward evidence (CIs, Brier, per-factor deltas): pipeline/FREEZE_RESULT.json.",
        "frozen: true",
        f"fit_seasons: [{lo}, {hi}]",
        f"target: {freeze['target']}",
        f"alpha: {alpha:g}  # multiplied by n inside ridge_fit",
        f"n: {n}",
        f'fitted_at: "{date}"',
        "weights:  # read by score.load_weights; must stay {factor: number}",
    ]
    lines += [f"  {f}: {format_weight(d['weight'])}" for f, d in factors.items()]
    lines.append("fit:  # per-factor evidence (ignored by load_weights)")
    for f, d in factors.items():
        k, nf = d["fold_sign"]
        lines.append(f'  {f}: {{raw: {_num(d["raw"])}, sign: "{d["sign"]}", fold_sign: [{k}, {nf}]}}')
    text = "\n".join(lines) + "\n"

    doc = yaml.safe_load(text)
    want = {f: round_weight(d["weight"]) for f, d in factors.items()}
    if doc.get("frozen") is not True or doc.get("weights") != want or list(doc["weights"]) != list(want):
        raise ValueError("rendered weights.yaml does not round-trip to the frozen weights")
    if set(doc.get("fit", {})) != set(want):
        raise ValueError("rendered weights.yaml fit block does not cover every factor")
    return text

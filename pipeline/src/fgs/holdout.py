"""ONE-TIME holdout evaluator. Only `fgs holdout` may set the allow_holdout opt-in; see pipeline/PREREGISTRATION.md.

DEV-ONLY, like backtest and freeze: it looks at future games (the targets), so score/features/
export/mood/explain must never import it (leakage firewall, enforced by tests/test_leakage.py).

evaluate_frozen scores the SHIPPED frozen composite (features.composite = sum of round(w)*z, no
intercept, never refit) and the baselines on the seasons [lo, hi]:
  - Spearman vs the N=8 (primary) and N=4 targets, pooled, by bucket and per season
  - next-game Brier with logistic maps fit ONCE on seasons <= fit_last (no refit on test seasons)
  - paired percentile bootstraps (season-block and stratified cluster), prereg section 7
  - the pre-registered vs_exp-zeroed diagnostic (prereg section 10), never used for the verdict
  - every factor's frozen weight, sign and walk-forward fold-sign consistency
verdict() is the BACK-06 decision rule and the three fixed sentences of prereg section 8.
Tests only ever evaluate the 2018-2021 training stand-in (weights fit on 1999-2017) or mocks.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import numpy as np
import polars as pl

from fgs import backtest, bootstrap, freeze, season_config

VERSION = 1
SPEARMAN_CANDS = freeze.SPEARMAN_CANDS  # composite, elo, season_wpct, last16, pd_pg
BRIER_CANDS = freeze.BRIER_CANDS  # the same plus spread
MODEL_CANDS = SPEARMAN_CANDS
COLS = {"composite": "composite", **backtest.CANDIDATES}  # candidate -> feature column

LABELS = {
    "composite": "Feel-good score (frozen)",
    "elo": "Elo alone",
    "season_wpct": "Season win %",
    "last16": "Last 16 games",
    "pd_pg": "Point differential",
    "spread": "Vegas spread (Brier only)",
    "elo_538": "Elo 538-style (Brier only)",
}

# PREREGISTRATION.md section 8, verbatim.
HEADLINES = {
    "yes": "Yes: on 2022–25 the score ranked teams' next 8 games better than Elo alone.",
    "slight": "Yes, slightly: better than Elo alone on 2022–25, but within the noise of four seasons.",
    "no": "Not on 2022–25: Elo alone did as well or better. We kept the weights anyway (no re-tuning).",
}


# ---------------------------------------------------------------------------
# Verdict (BACK-06)
# ---------------------------------------------------------------------------

def _width(ci) -> float:
    return -1.0 if not ci else float(ci[1]) - float(ci[0])


def verdict(diff: float | None, ci_season, ci_cluster) -> tuple[str, str]:
    """(key, headline). Keys on the WIDER of the two CIs (larger hi - lo; cluster on ties).
    no: diff <= 0. yes: diff > 0 and the wider CI's lower bound > 0. slight: otherwise."""
    if diff is None or diff <= 0:
        return "no", HEADLINES["no"]
    wider = ci_season if _width(ci_season) > _width(ci_cluster) else ci_cluster
    if wider and wider[0] > 0:
        return "yes", HEADLINES["yes"]
    return "slight", HEADLINES["slight"]


def passed(diff: float | None) -> bool:
    """BACK-06: PASS iff the paired point difference (composite - Elo Spearman N=8) is > 0."""
    return diff is not None and diff > 0


# ---------------------------------------------------------------------------
# Brier maps (fit once on seasons <= fit_last)
# ---------------------------------------------------------------------------

def _x_diff(t: pl.DataFrame, col: str) -> np.ndarray:
    return np.column_stack([(t[f"h_{col}"] - t[f"a_{col}"]).to_numpy(), t["home_ind"].to_numpy()])


def _brier_maps(ng: pl.DataFrame, fit_last: int) -> dict[str, np.ndarray]:
    """Logistic coefficients per Brier candidate, fit only on next-game rows with season <= fit_last.
    Model candidates: X = (home - away value, home_ind). Spread: X = spread_line alone."""
    tr = ng.filter(pl.col("season") <= fit_last)
    if tr.is_empty():
        raise ValueError(f"no next-game rows with season <= {fit_last} to fit the Brier maps")
    maps = {c: backtest.logit_fit(_x_diff(tr, COLS[c]), tr["y"].to_numpy()) for c in MODEL_CANDS}
    sp = tr.filter(pl.col("spread_line").is_not_null())
    maps["spread"] = backtest.logit_fit(sp["spread_line"].to_numpy(), sp["y"].to_numpy())
    return maps


def _brier_games(ng: pl.DataFrame, maps: dict, lo: int, hi: int) -> pl.DataFrame:
    """Test-season games where every probability (incl. spread and elo_538) is defined."""
    te = ng.filter(pl.col("season").is_between(lo, hi) & pl.col("spread_line").is_not_null())
    cols = {c: backtest.logit_predict(maps[c], _x_diff(te, COLS[c])) for c in MODEL_CANDS}
    cols["spread"] = backtest.logit_predict(maps["spread"], te["spread_line"].to_numpy())
    cols["elo_538"] = backtest._p538(te)
    g = te.select("game_id", "season", "asof_week", "y").with_columns(
        pl.Series(f"p_{c}", p, dtype=pl.Float64).fill_nan(None) for c, p in cols.items()
    )
    return g.drop_nulls([f"p_{c}" for c in cols]).sort("season", "game_id")


# ---------------------------------------------------------------------------
# Spearman (paired bootstrap)
# ---------------------------------------------------------------------------

def _ci(boot: dict, name: str, kind: str = "stats"):
    return boot[kind][name]["ci"]


def _spearman_eval(d: pl.DataFrame, y_col: str, xcols: dict[str, str], diffs: dict, B: int, seed: int):
    """Full-sample values + season-block / team-season paired bootstraps on rows d (y_col non-null)."""
    y = d[y_col].to_numpy().astype(float)
    xs = {c: d[col].to_numpy().astype(float) for c, col in xcols.items()}
    season = d["season"].to_numpy()

    def fn(c):
        x = xs[c]
        return lambda idx: backtest.spearman(x[idx], y[idx])

    fns = {c: fn(c) for c in xcols}
    blocks = bootstrap.season_blocks(season)
    strata = bootstrap.stratified_clusters(season, d["franchise_id"].to_numpy())
    bs = bootstrap.paired_bootstrap(fns, lambda r: bootstrap.draw_blocks(r, blocks), diffs=diffs, B=B, seed=seed)
    bc = bootstrap.paired_bootstrap(fns, lambda r: bootstrap.draw_stratified(r, strata), diffs=diffs, B=B, seed=seed)
    vals = {c: fns[c](np.arange(len(y))) for c in xcols}
    return vals, bs, bc, fns, season


def _sub(a, b):
    return None if a is None or b is None else a - b


# ---------------------------------------------------------------------------
# The evaluator
# ---------------------------------------------------------------------------

def evaluate_frozen(
    derived: dict, weights: dict, seasons: tuple[int, int], fit_last: int, *,
    weights_doc: dict | None = None, allow_holdout: bool = False,
    B: int = bootstrap.B_DEFAULT, seed: int = bootstrap.SEED,
) -> dict:
    """HOLDOUT_RESULT dict (provenance/evaluated_at/rerun/reruns left for the CLI to fill)."""
    lo, hi = int(seasons[0]), int(seasons[1])
    if hi > season_config.TRAIN_LAST_SEASON and not allow_holdout:  # read at call time
        raise ValueError("holdout seasons require the guarded `fgs holdout` path")
    if "weights" not in derived or dict(derived["weights"]) != dict(weights):
        raise ValueError("derived features were not built with the frozen weights (re-derive; Pitfall 8)")
    if fit_last >= lo:
        raise ValueError(f"fit_last ({fit_last}) must be before the first evaluated season ({lo})")

    # Nothing after hi is read (targets stop at the season end anyway; this keeps 2026 out).
    feats = derived["features"].filter(pl.col("season") <= hi)
    snaps = derived["snapshots"].filter(pl.col("season") <= hi)
    team_games = derived["team_games"].filter(pl.col("season") <= hi)
    games = derived["games"].filter(pl.col("season") <= hi)

    has_vsexp = "contrib_vs_exp" in feats.columns
    if has_vsexp:
        feats = feats.with_columns((pl.col("composite") - pl.col("contrib_vs_exp")).alias("composite_novsexp"))
    tgt = backtest.targets(team_games, snaps, (4, 8))
    rows = (
        feats.filter(pl.col("season").is_between(lo, hi))
        .with_columns(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32))
        .join(tgt, on=backtest.KEYS, how="inner")
        .with_columns(backtest.bucket_expr().alias("bucket"))
        .sort(backtest.KEYS)
    )

    # --- Spearman N=8 (primary) ---
    d8 = rows.filter(pl.col("y8").is_not_null())
    x8 = {c: COLS[c] for c in SPEARMAN_CANDS}
    diffs8 = {"diff": ("composite", "elo")}
    if has_vsexp:
        x8["composite_novsexp"] = "composite_novsexp"
        diffs8["diff_novsexp"] = ("composite_novsexp", "elo")
    v8, bs8, bc8, fns8, sea8 = _spearman_eval(d8, "y8", x8, diffs8, B, seed)
    uniq = sorted(int(s) for s in np.unique(sea8))
    per_season = {c: {str(s): fns8[c](np.flatnonzero(sea8 == s)) for s in uniq} for c in SPEARMAN_CANDS}
    buckets = {}
    for c in SPEARMAN_CANDS:
        buckets[c] = {}
        for b in backtest.BUCKETS:
            db = d8.filter(pl.col("bucket") == b)
            buckets[c][b] = backtest.spearman(db[COLS[c]].to_numpy(), db["y8"].to_numpy())
    spearman_n8 = {
        c: {"value": v8[c], "ci_season": _ci(bs8, c), "ci_cluster": _ci(bc8, c),
            "buckets": buckets[c], "per_season": per_season[c]}
        for c in SPEARMAN_CANDS
    }
    per_season_diff = {s: _sub(per_season["composite"][s], per_season["elo"][s]) for s in per_season["composite"]}
    won = sum(1 for v in per_season_diff.values() if v is not None and v > 0)
    diff8 = {
        "value": _sub(v8["composite"], v8["elo"]),
        "ci_season": _ci(bs8, "diff", "diffs"), "ci_cluster": _ci(bc8, "diff", "diffs"),
        "seasons_won": won, "of": len(uniq), "per_season": per_season_diff,
    }

    # --- Spearman N=4 (secondary) ---
    d4 = rows.filter(pl.col("y4").is_not_null())
    x4 = {c: COLS[c] for c in SPEARMAN_CANDS}
    v4, bs4, bc4, _, _ = _spearman_eval(d4, "y4", x4, {"diff": ("composite", "elo")}, B, seed)
    spearman_n4 = {c: {"value": v4[c], "ci_season": _ci(bs4, c), "ci_cluster": _ci(bc4, c)} for c in SPEARMAN_CANDS}
    diff4 = {"value": _sub(v4["composite"], v4["elo"]),
             "ci_season": _ci(bs4, "diff", "diffs"), "ci_cluster": _ci(bc4, "diff", "diffs")}

    # --- Brier (maps fit once on seasons <= fit_last) ---
    ng = backtest.next_game_frame(games, feats, [COLS[c] for c in MODEL_CANDS])
    maps = _brier_maps(ng, fit_last)
    bg = _brier_games(ng, maps, lo, hi)
    brier, dbr, n_games = freeze._brier_block(bg, B, seed)

    # --- Diagnostic (prereg section 10; never used for the verdict) ---
    diagnostic = {"vs_exp_zeroed": None}
    if has_vsexp:
        diagnostic["vs_exp_zeroed"] = {
            "spearman_n8": v8["composite_novsexp"],
            "diff_vs_elo": {"value": _sub(v8["composite_novsexp"], v8["elo"]),
                            "ci_cluster": _ci(bc8, "diff_novsexp", "diffs")},
        }

    # --- Factors ---
    fit = (weights_doc or {}).get("fit") or {}
    factors = {}
    for f, w in weights.items():
        fb = fit.get(f)
        if fb:
            factors[f] = {"weight": float(w), "sign": fb.get("sign"), "fold_sign": list(fb.get("fold_sign") or []) or None}
        else:
            factors[f] = {"weight": float(w), "sign": freeze.sign_of(float(w)), "fold_sign": None}

    key, headline = verdict(diff8["value"], diff8["ci_season"], diff8["ci_cluster"])
    result = {
        "version": VERSION,
        "seasons": [lo, hi],
        "fit_last": int(fit_last),
        "evaluated_at": None,
        "rerun": False,
        "reruns": [],
        "provenance": {"weights_sha256": None, "prereg_sha256": None, "git_head": None,
                       "prereg_commit": None, "weights_commit": None},
        "bootstrap": {
            "B": int(B), "seed": int(seed), "method": "percentile",
            "distinct_season_resamples": bootstrap.distinct_block_resamples(len(uniq)),
            "cluster_spearman": "team-season stratified by season",
            "cluster_brier": "season-week stratified by season",
        },
        "n": {"snapshots_n8": int(d8.height), "snapshots_n4": int(d4.height), "games": int(n_games)},
        "verdict": key,
        "headline": headline,
        "pass": passed(diff8["value"]),
        "spearman_n8": spearman_n8,
        "spearman_n4": spearman_n4,
        "brier": brier,
        "diff": {"spearman_n8": diff8, "spearman_n4": diff4, **dbr},
        "diagnostic": diagnostic,
        "factors": factors,
    }
    out = backtest._clean(result)
    for d in out["factors"].values():  # keep the 2-dp weights exact and free of -0.0
        d["weight"] = freeze.round_weight(d["weight"])
    return out


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def _f(v, nd: int = 4) -> str:
    return "—" if v is None else f"{v:.{nd}f}"


def _sg(v, nd: int = 4) -> str:
    return "—" if v is None else f"{v:+.{nd}f}"


def _cis(ci, nd: int = 4) -> str:
    return "—" if not ci else f"[{ci[0]:+.{nd}f}, {ci[1]:+.{nd}f}]"


def _ciu(ci, nd: int = 4) -> str:
    return "—" if not ci else f"[{ci[0]:.{nd}f}, {ci[1]:.{nd}f}]"


def render_markdown(result: dict) -> str:
    lo, hi = result["seasons"]
    when = result.get("evaluated_at") or "—"
    prov = result.get("provenance") or {}
    bs = result["bootstrap"]
    d8 = result["diff"]["spearman_n8"]
    d4 = result["diff"]["spearman_n4"]
    sp8, sp4, br = result["spearman_n8"], result["spearman_n4"], result["brier"]
    L = [
        f"# Holdout result ({lo}–{hi}), evaluated once on {when}",
        "",
        "Written by `uv run fgs holdout`. Do not edit. The rules are fixed in pipeline/PREREGISTRATION.md.",
        "",
        f"**Verdict: {result['verdict']}** — {result['headline']}",
        "",
        f"BACK-06: {'PASS' if result['pass'] else 'FAIL'} (score − Elo Spearman N=8 > 0)",
        "",
        "## Provenance",
        "",
        f"- PREREGISTRATION.md sha256: `{prov.get('prereg_sha256') or '—'}` (commit `{prov.get('prereg_commit') or '—'}`)",
        f"- weights.yaml sha256: `{prov.get('weights_sha256') or '—'}` (commit `{prov.get('weights_commit') or '—'}`)",
        f"- git HEAD: `{prov.get('git_head') or '—'}`",
    ]
    if "src_clean" in prov:
        L.append(f"- pipeline/src clean at run time: {prov['src_clean']}")
    if "prereg_unchanged" in prov:
        L.append(f"- PREREGISTRATION.md unchanged since its adding commit: {prov['prereg_unchanged']}")
    inputs = prov.get("inputs")
    if inputs:
        L.append(f"- input fingerprints (sha256, full list in HOLDOUT_RESULT.json): {len(inputs.get('cache') or {})} "
                 f"cache files, {len(inputs.get('sim_cache') or {})} sim-cache files, uv.lock "
                 f"`{inputs.get('uv_lock_sha256') or '—'}`")
    L += [
        f"- Brier logistic maps fit on seasons <= {result['fit_last']}; no refits on {lo}–{hi}",
        "",
        "## Candidates",
        "",
        f"Snapshots: {result['n']['snapshots_n8']} (N=8), {result['n']['snapshots_n4']} (N=4). "
        f"Next games: {result['n']['games']}.",
        "",
        "| Candidate | Spearman N=8 [95% CI, team-season] | Spearman N=4 | wk0 | early | mid | late "
        "| Brier [95% CI, season-week] |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for c in SPEARMAN_CANDS:
        s8, s4, b = sp8[c], sp4[c], br.get(c) or {}
        bk = s8.get("buckets") or {}
        L.append(
            f"| {LABELS[c]} | {_f(s8['value'])} {_ciu(s8.get('ci_cluster'))} | {_f(s4['value'])} | "
            + " | ".join(_f(bk.get(x)) for x in backtest.BUCKETS)
            + f" | {_f(b.get('value'))} {_ciu(b.get('ci_cluster'))} |"
        )
    sp = br.get("spread") or {}
    L.append(f"| {LABELS['spread']} | — | — | — | — | — | — | {_f(sp.get('value'))} {_ciu(sp.get('ci_cluster'))} |")
    L.append(f"| {LABELS['elo_538']} | — | — | — | — | — | — | {_f((br.get('elo_538') or {}).get('value'))} |")

    per = d8.get("per_season") or {}
    per_txt = ", ".join(f"{s} {_sg(v)}" for s, v in per.items())
    bve, bvs = result["diff"]["brier_vs_elo"], result["diff"]["brier_vs_spread"]
    L += [
        "",
        "## Difference (score − Elo)",
        "",
        f"- Spearman N=8: {_sg(d8['value'])}; season-block CI {_cis(d8.get('ci_season'))}; "
        f"team-season CI {_cis(d8.get('ci_cluster'))}; won {d8['seasons_won']} of {d8['of']} seasons ({per_txt})",
        f"- Spearman N=4: {_sg(d4['value'])}; season-block CI {_cis(d4.get('ci_season'))}; "
        f"team-season CI {_cis(d4.get('ci_cluster'))}",
        f"- Brier vs Elo: {_sg(bve['value'])}; season-block CI {_cis(bve.get('ci_season'))}; "
        f"season-week CI {_cis(bve.get('ci_cluster'))} (negative = the score is better)",
        f"- Brier vs Vegas spread: {_sg(bvs['value'])}; season-block CI {_cis(bvs.get('ci_season'))}; "
        f"season-week CI {_cis(bvs.get('ci_cluster'))} (the spread is the market ceiling)",
        "",
    ]
    diag = (result.get("diagnostic") or {}).get("vs_exp_zeroed")
    if diag:
        dd = diag["diff_vs_elo"]
        L.append(f"Diagnostic (pre-registered diagnostic, not used for the verdict): score with vs_exp zeroed, "
                 f"Spearman N=8 {_f(diag['spearman_n8'])}; − Elo {_sg(dd['value'])}, team-season CI "
                 f"{_cis(dd.get('ci_cluster'))}.")
    else:
        L.append("Diagnostic (pre-registered diagnostic, not used for the verdict): vs_exp zeroed — not available.")
    L += [
        "",
        "## Factors (frozen weights.yaml)",
        "",
        "| Factor | Weight | Sign | Folds with this sign |",
        "|---|---|---|---|",
    ]
    for f, d in result["factors"].items():
        fs = d.get("fold_sign")
        folds = "—" if not fs else f"{fs[0]}/{fs[1]}"
        L.append(f"| {f} | {freeze.format_weight(d['weight'])} | {d.get('sign') or '—'} | {folds} |")
    L += [
        "",
        f"Bootstrap: B={bs['B']}, seed={bs['seed']}, {bs['method']} 95% intervals, paired across candidates; "
        f"season block has {bs['distinct_season_resamples']} distinct resamples. Cluster CIs: "
        f"{bs['cluster_spearman']} (Spearman), {bs['cluster_brier']} (Brier).",
    ]
    if result.get("reruns"):
        L += ["", "## Reruns", "",
              "This result was re-run with `--force`, which breaks the pre-registration. Previous results:", ""]
        for r in result["reruns"]:
            L.append(f"- {r.get('evaluated_at') or '—'}: verdict {r.get('verdict') or '—'}")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------

def file_sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def dir_sha256(root) -> dict[str, str]:
    """{relative posix path: sha256} for every regular file under root (sorted); {} if root is missing.
    Temp/marker files (dotfiles, *.tmp) are skipped."""
    root = Path(root)
    if not root.is_dir():
        return {}
    return {p.relative_to(root).as_posix(): file_sha256(p) for p in sorted(root.rglob("*"))
            if p.is_file() and not p.name.startswith(".") and not p.name.endswith(".tmp")}


def input_fingerprints(cache_dir, sim_dir, lock_path) -> dict:
    """Fingerprints of the evaluation's inputs for provenance (WR-08): the nflverse cache (schedules,
    pbp, win totals), the sim cache (po_trend) and uv.lock. nflverse revises data after the fact and a
    dependency change can alter ties, so a result is only reproducible against these exact bytes."""
    lock = Path(lock_path)
    return {
        "cache": dir_sha256(cache_dir),
        "sim_cache": dir_sha256(sim_dir),
        "uv_lock_sha256": file_sha256(lock) if lock.is_file() else None,
    }


def _git(root, *args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)


def git_state(root, prereg_rel: str = "PREREGISTRATION.md", weights_rel: str = "weights.yaml",
              src_rel: str | None = "src") -> dict:
    """Commit state of the pre-registration and weights files under root.

    dirty: porcelain lines (modified, staged or untracked) for the two files.
    src_dirty: porcelain lines under src_rel (the code that computes the result).
    ordered: the prereg's ADDING commit and its LAST commit are both ancestors of the latest
      weights.yaml commit (a post-freeze edit to the prereg fails this; WR-07).
    prereg_unchanged: the prereg has exactly one commit and the working file's sha256 equals the
      sha256 of its content at the adding commit, so the hashed file IS the pre-registered text.
    available False when git is missing or root is not inside a work tree."""
    out = {"available": False, "dirty": [], "src_dirty": [], "prereg_commit": None,
           "prereg_last_commit": None, "prereg_commits": 0, "prereg_unchanged": False,
           "weights_commit": None, "ordered": False, "head": None}
    try:
        r = _git(root, "rev-parse", "--is-inside-work-tree")
    except (FileNotFoundError, OSError):
        return out
    if r.returncode != 0 or r.stdout.strip() != "true":
        return out
    out["available"] = True
    st = _git(root, "status", "--porcelain", "--", prereg_rel, weights_rel)
    out["dirty"] = [ln for ln in st.stdout.splitlines() if ln.strip()]
    if src_rel is not None and (Path(root) / src_rel).exists():
        ss = _git(root, "status", "--porcelain", "--", src_rel)
        out["src_dirty"] = [ln for ln in ss.stdout.splitlines() if ln.strip()]
    added = _git(root, "log", "--diff-filter=A", "--format=%H", "--", prereg_rel).stdout.split()
    out["prereg_commit"] = added[-1] if added else None
    touching = _git(root, "log", "--format=%H", "--", prereg_rel).stdout.split()
    out["prereg_commits"] = len(touching)
    out["prereg_last_commit"] = touching[0] if touching else None
    wc = _git(root, "log", "-1", "--format=%H", "--", weights_rel).stdout.strip()
    out["weights_commit"] = wc or None
    head = _git(root, "rev-parse", "HEAD")
    out["head"] = head.stdout.strip() if head.returncode == 0 else None
    if out["prereg_commit"]:
        committed = subprocess.run(["git", "-C", str(root), "show", f"{out['prereg_commit']}:./{prereg_rel}"],
                                   capture_output=True, check=False)
        cur = Path(root) / prereg_rel
        out["prereg_unchanged"] = (
            committed.returncode == 0 and len(touching) == 1 and cur.exists()
            and hashlib.sha256(committed.stdout).hexdigest() == file_sha256(cur)
        )
    if out["prereg_commit"] and out["prereg_last_commit"] and out["weights_commit"]:
        out["ordered"] = all(
            _git(root, "merge-base", "--is-ancestor", c, out["weights_commit"]).returncode == 0
            for c in (out["prereg_commit"], out["prereg_last_commit"])
        )
    return out

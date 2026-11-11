"""Staleness fingerprints for pipeline/callout_evidence.json (WR-02).

The perception-gap base rates depend on far more than the weights: the Elo hyperparameters, the
code that builds games, Elo, features, scores and gap flags, and the 1999-2021 data itself
(nflverse revises old seasons now and then). `fgs evidence` stores one hash per input; the export
recomputes them and refuses to ship the evidence line when any differs.

Pure (stdlib + polars). Upstream of the backtest firewall: never imports fgs.backtest, fgs.cli or
the dev-only evidence module. Their source files are only *read* (parsed with ast), never
imported, so the export stays on the safe side of test_leakage.
"""

import ast
import dataclasses
import hashlib
import json
from pathlib import Path

import polars as pl

from fgs import season_config
from fgs.elo import EloParams

_SRC = Path(__file__).resolve().parent

# Whole modules whose code decides the 1999-2021 score ranks, the gap flags or the evidence numbers.
CODE_FILES: tuple[str, ...] = (
    "franchises.py", "games.py", "elo.py", "snapshots.py", "sim.py", "efficiency.py", "expectation.py",
    "features.py", "draft.py", "score.py", "mood.py", "season_config.py", "backtest.py", "evidence.py",
)
# Modules that also hold unrelated code (CLI plumbing, callout copy): only these functions count.
CODE_FUNCS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("cli.py", ("derive_games", "draft_winsor")),
    ("insights.py", ("record_ranks", "gap_flags")),
)

FINGERPRINT_KEYS = ("weights_fingerprint", "elo_fingerprint", "code_fingerprint", "data_fingerprint")


def _h(blob: str | bytes) -> str:
    return hashlib.sha256(blob.encode() if isinstance(blob, str) else blob).hexdigest()[:12]


def _strip_docstrings(tree: ast.AST) -> ast.AST:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
                    and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
    return tree


def _code_dump(src: str) -> str:
    """Normalized code: the AST without comments, formatting or docstrings, so doc-only edits never
    invalidate the evidence but any change to what runs does."""
    return ast.dump(_strip_docstrings(ast.parse(src)), include_attributes=False)


def code_fingerprint(root: Path | None = None) -> str:
    """Hash of the code version behind the evidence numbers (CODE_FILES + CODE_FUNCS)."""
    root = _SRC if root is None else root
    parts = []
    for name in CODE_FILES:
        parts.append(f"{name}\n{_code_dump((root / name).read_text(encoding='utf-8'))}")
    for name, funcs in CODE_FUNCS:
        tree = ast.parse((root / name).read_text(encoding="utf-8"))
        defs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        for f in funcs:
            if f not in defs:
                raise ValueError(f"fingerprint: {name} has no function {f}")
            parts.append(f"{name}:{f}\n{ast.dump(_strip_docstrings(defs[f]), include_attributes=False)}")
    return _h("\n\n".join(parts))


def elo_fingerprint(params: EloParams | None = None) -> str:
    """Hash of the Elo hyperparameters (K, mean, offseason reversion, seeds) and the HFA eras, read at
    call time."""
    p = EloParams() if params is None else params
    d = dataclasses.asdict(p)
    d["seeds"] = sorted([f, int(s), float(v)] for (f, s), v in d["seeds"].items())
    d["hfa_by_era"] = [list(e) for e in season_config.HFA_BY_ERA]
    d["mean_elo"] = season_config.MEAN_ELO
    return _h(json.dumps(d, sort_keys=True, default=float))


def data_fingerprint(scored: pl.DataFrame, team_games: pl.DataFrame) -> str:
    """Hash of the 1999-TRAIN_LAST_SEASON data snapshot the evidence was computed on: every scored
    team-week (rank, score, record) and every played team-game (points, outcome). Seasons after the
    training window are dropped first, so weekly refreshes never touch it."""
    last = season_config.TRAIN_LAST_SEASON  # read at call time
    s = (
        scored.filter(pl.col("season") <= last)
        .select(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32), "franchise_id",
                *[pl.col(c).cast(pl.Int64) for c in ("rank", "score", "wins", "losses", "ties")])
        .sort("season", "week", "franchise_id")
    )
    tg = (
        team_games.filter((pl.col("season") <= last) & pl.col("played"))
        .select(pl.col("season").cast(pl.Int32), pl.col("asof_week").cast(pl.Int32), "franchise_id", "game_id",
                pl.col("is_reg").cast(pl.Boolean), pl.col("points_for").cast(pl.Int64),
                pl.col("points_against").cast(pl.Int64), pl.col("outcome").cast(pl.Float64))
        .sort("season", "asof_week", "franchise_id", "game_id")
    )
    return _h(s.write_csv() + "\n--\n" + tg.write_csv())


def evidence_fingerprints(weights_fp: str, scored: pl.DataFrame, team_games: pl.DataFrame) -> dict[str, str]:
    """Every staleness key stored in callout_evidence.json and checked by the export."""
    return {
        "weights_fingerprint": weights_fp,
        "elo_fingerprint": elo_fingerprint(),
        "code_fingerprint": code_fingerprint(),
        "data_fingerprint": data_fingerprint(scored, team_games),
    }

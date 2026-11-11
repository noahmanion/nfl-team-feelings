"""Canonical franchise identity: current nflverse codes, legacy codes mapped forward."""

import polars as pl

# Applied to every loaded table before anything else. WAS never varies in schedules.
RAW_TO_FRANCHISE: dict[str, str] = {"OAK": "LV", "SD": "LAC", "STL": "LA"}

CANONICAL: frozenset[str] = frozenset(
    "ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LA LAC LV "
    "MIA MIN NE NO NYG NYJ PHI PIT SEA SF TB TEN WAS".split()
)

KNOWN_RAW: frozenset[str] = CANONICAL | frozenset(RAW_TO_FRANCHISE)


def normalize_code(code: str) -> str:
    if code not in KNOWN_RAW:
        raise ValueError(f"unknown team code: {code!r}")
    return RAW_TO_FRANCHISE.get(code, code)


def unknown_codes(raw: pl.DataFrame) -> set[str]:
    """Raw home/away codes that neither are canonical nor map to a canonical code."""
    codes = set(raw["home_team"].drop_nulls()) | set(raw["away_team"].drop_nulls())
    return codes - KNOWN_RAW

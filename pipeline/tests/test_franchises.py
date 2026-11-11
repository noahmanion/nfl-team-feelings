import polars as pl
import pytest

from fgs.franchises import CANONICAL, normalize_code
from fgs.games import build_games


@pytest.mark.parametrize("raw,canon", [("OAK", "LV"), ("SD", "LAC"), ("STL", "LA"), ("WAS", "WAS")])
def test_normalize_code(raw, canon):
    assert normalize_code(raw) == canon


def test_normalize_unknown_raises():
    with pytest.raises(ValueError):
        normalize_code("XXX")


def test_canonical_has_32():
    assert len(CANONICAL) == 32
    assert not {"OAK", "SD", "STL"} & CANONICAL


def _raw(home: str, away: str) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["1999_01_X_Y"], "season": [1999], "week": [1], "game_type": ["REG"],
            "gameday": ["1999-09-12"], "gametime": [None], "home_team": [home], "away_team": [away],
            "home_score": [20], "away_score": [10], "result": [10], "location": ["Home"],
        },
        schema_overrides={"gametime": pl.String},
    )


def test_build_games_rejects_unknown_codes():
    with pytest.raises(ValueError, match="XXX"):
        build_games(_raw("XXX", "BUF"))


def test_build_games_maps_legacy_codes_keeps_raw():
    g = build_games(_raw("OAK", "STL")).row(0, named=True)
    assert (g["home_id"], g["away_id"]) == ("LV", "LA")
    assert (g["raw_home"], g["raw_away"]) == ("OAK", "STL")
    assert g["played"] and g["is_reg"] and not g["neutral"]

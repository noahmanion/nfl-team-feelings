"""Per-season constants and era rules: seeds, HFA, team counts, games, playoffs, divisions."""

MEAN_ELO = 1505.0

# Expansion / re-entry franchises start below the mean (538 convention). Everyone else: 1505 in 1999.
SEEDS: dict[tuple[str, int], float] = {("CLE", 1999): 1300.0, ("HOU", 2002): 1300.0}

# Home-field advantage in Elo points, by era.
#
#   era         HFA   derivation
#   1999-2009   65    mean non-neutral spread_line x 25 (also 538's constant)
#   2010-2019   58    mean non-neutral spread_line x 25
#   2020        30    mean non-neutral spread_line x 25 (empty stadiums)
#   2021+       45    mean non-neutral spread_line x 25
#
# Values are market-implied from closing lines, not fitted to results, so they are
# outcome-free and the 2022-2025 holdout stays clean. Phase 3 may tune them.
HFA_BY_ERA: tuple[tuple[int, int, float], ...] = (
    (1999, 2009, 65.0),
    (2010, 2019, 58.0),
    (2020, 2020, 30.0),
    (2021, 9999, 45.0),
)


def hfa_for(season: int) -> float:
    if season <= 2009:
        return 65.0
    if season <= 2019:
        return 58.0
    if season == 2020:
        return 30.0
    return 45.0


# ---------------------------------------------------------------------------
# Era rules (D-08). One lookup table; check_config_coverage validates it against the data.
# ---------------------------------------------------------------------------

# Franchises that enter after 1999. Everyone else is present from 1999.
ENTRY_SEASON: dict[str, int] = {"HOU": 2002}

# Team-seasons whose REG game count differs from reg_games(season).
# BUF-CIN 2022 week 17 (Hamlin) was cancelled and has no row in nflverse.
EXPECTED_GAME_EXCEPTIONS: dict[tuple[int, str], int] = {(2022, "BUF"): 16, (2022, "CIN"): 16}


def n_teams(season: int) -> int:
    return 31 if season <= 2001 else 32


def reg_games(season: int) -> int:
    return 16 if season <= 2020 else 17


def reg_weeks(season: int) -> int:
    return 17 if season <= 2020 else 18


def playoff_teams(season: int) -> int:
    return 12 if season <= 2019 else 14


def season_rules(season: int) -> dict:
    """Per-season view of the era table."""
    return {
        "n_teams": n_teams(season),
        "reg_games": reg_games(season),
        "reg_weeks": reg_weeks(season),
        "playoff_teams": playoff_teams(season),
        "hfa": hfa_for(season),
    }


# Division names/conference labels for 1999-2001 are from memory; memberships are
# verified against the div_game graph by fgs.checks.check_divisions.
DIVISIONS_1999_2001: dict[str, list[str]] = {
    "AFC East": ["BUF", "IND", "MIA", "NE", "NYJ"],
    "AFC Central": ["BAL", "CIN", "CLE", "JAX", "PIT", "TEN"],
    "AFC West": ["DEN", "KC", "LAC", "LV", "SEA"],
    "NFC East": ["ARI", "DAL", "NYG", "PHI", "WAS"],
    "NFC Central": ["CHI", "DET", "GB", "MIN", "TB"],
    "NFC West": ["ATL", "CAR", "LA", "NO", "SF"],
}

DIVISIONS_2002_ON: dict[str, list[str]] = {
    "AFC East": ["BUF", "MIA", "NE", "NYJ"],
    "AFC North": ["BAL", "CIN", "CLE", "PIT"],
    "AFC South": ["HOU", "IND", "JAX", "TEN"],
    "AFC West": ["DEN", "KC", "LAC", "LV"],
    "NFC East": ["DAL", "NYG", "PHI", "WAS"],
    "NFC North": ["CHI", "DET", "GB", "MIN"],
    "NFC South": ["ATL", "CAR", "NO", "TB"],
    "NFC West": ["ARI", "LA", "SEA", "SF"],
}


def divisions(season: int) -> dict[str, list[str]]:
    # Looked up at call time so tests can monkeypatch the module-level tables.
    return DIVISIONS_1999_2001 if season <= 2001 else DIVISIONS_2002_ON


def division_of(season: int, franchise_id: str) -> str:
    for name, teams in divisions(season).items():
        if franchise_id in teams:
            return name
    raise KeyError(f"{franchise_id} has no division in {season}")


def conference_of(season: int, franchise_id: str) -> str:
    return division_of(season, franchise_id).split()[0]

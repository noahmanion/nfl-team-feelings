"""Per-season constants. Plain module of constants and functions (plan 02 adds counts/divisions)."""

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

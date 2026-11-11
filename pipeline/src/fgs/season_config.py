"""Per-season constants and era rules: seeds, HFA, team counts, games, playoffs, divisions."""

from datetime import date

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


# ---------------------------------------------------------------------------
# Backtest splits (Phase 3). All ranges are inclusive.
#
#   FIRST_TEST_SEASON  first walk-forward test season (fits use only earlier seasons)
#   TRAIN_LAST_SEASON  last season any fit or default metric may see
#   HOLDOUT_SEASONS    sealed; only `fgs backtest --include-holdout` touches them
#   REF_SEASONS        frozen percentile reference set for the score (plan 03-03)
# ---------------------------------------------------------------------------
FIRST_TEST_SEASON = 2003
TRAIN_LAST_SEASON = 2021
HOLDOUT_SEASONS: tuple[int, int] = (2022, 2025)
REF_SEASONS: tuple[int, int] = (1999, 2021)


def hfa_for(season: int) -> float:
    # Single source of truth: HFA_BY_ERA (looked up at call time so tuning/monkeypatching takes effect).
    for lo, hi, hfa in HFA_BY_ERA:
        if lo <= season <= hi:
            return hfa
    raise KeyError(f"no HFA era for {season}")


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


# ---------------------------------------------------------------------------
# Phase 8 callouts (INSIGHT-02, INSIGHT-06). Read at call time (module attribute) by fgs.insights.
#
#   GAP_THRESHOLD   |record rank - score rank| that flags a perception gap
#   GAP_CAP         max gap callouts per (season, week, flavor), largest |gap| first
#   GAP_FIRST_WEEK  first REG week that can flag; the last is reg_weeks(season) - 1
#   MOVERS_N        risers and fallers shown per week
# ---------------------------------------------------------------------------
GAP_THRESHOLD = 8
GAP_CAP = 3
GAP_FIRST_WEEK = 4
MOVERS_N = 3


# ---------------------------------------------------------------------------
# Phase 8 streaks and records (INSIGHT-03, INSIGHT-04).
#
# DRAFT_END dates the week-0 (post-draft, Phase 7) snapshot: the LAST day of each NFL draft, from
# Wikipedia "List of NFL drafts". Hard-coded because nflverse draft_picks has no date column.
# fgs.checks.check_draft_dates fails `fgs check` when a past season is missing (and warns for the
# current one). Unknown seasons fall back to Sept 1, clamped to the export date (never negative days).
#
#   MISERY_MAX               score <= this is misery (score < 20)
#   JOY_MIN                  score >= this is joy
#   STREAK_CALLOUT_MIN_DAYS  a week's longest active streak becomes a callout only from this length
# ---------------------------------------------------------------------------
DRAFT_END: dict[int, str] = {  # season: "MM-DD" (last day of the draft)
    1999:"04-18", 2000:"04-16", 2001:"04-22", 2002:"04-21", 2003:"04-27", 2004:"04-25", 2005:"04-24",
    2006:"04-30", 2007:"04-29", 2008:"04-27", 2009:"04-26", 2010:"04-24", 2011:"04-30", 2012:"04-28",
    2013:"04-27", 2014:"05-10", 2015:"05-02", 2016:"04-30", 2017:"04-29", 2018:"04-28", 2019:"04-27",
    2020:"04-25", 2021:"05-01", 2022:"04-30", 2023:"04-29", 2024:"04-27", 2025:"04-26", 2026:"04-25",
}  # fmt: skip
MISERY_MAX = 19
JOY_MIN = 80
STREAK_CALLOUT_MIN_DAYS = 100


def draft_date(season: int, as_of: date) -> date:
    """Date of the week-0 snapshot: the draft's last day; unknown season -> Sept 1, clamped to as_of."""
    md = DRAFT_END.get(season)  # module attribute at call time (tests monkeypatch DRAFT_END)
    if md is not None:
        return date.fromisoformat(f"{season}-{md}")
    return min(date(season, 9, 1), as_of)

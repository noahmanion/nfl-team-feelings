"""Data-trust checks. Each takes DataFrames and returns a list of human-readable failures ([] = pass).

`fgs check` prints them and exits 1 on any failure; pytest asserts `== []`.
"""

from collections.abc import Callable

import polars as pl

from fgs import pbp, season_config
from fgs.elo import EloParams
from fgs.franchises import CANONICAL, unknown_codes

REQUIRED_RAW_COLUMNS = [
    "game_id", "season", "week", "game_type", "gameday", "gametime", "home_team", "away_team",
    "home_score", "away_score", "location", "result", "div_game", "spread_line",
    "home_qb_id", "home_qb_name", "away_qb_id", "away_qb_name",
]
ELO_TOL = 1e-9
CONTINUITY_TOL = 1e-6
MEAN_TOL = 0.5
MEAN_CHECK_FROM = 2012  # seed deficits (CLE 1999, HOU 2002) have decayed below MEAN_TOL by then


def check_columns(raw: pl.DataFrame) -> list[str]:
    missing = [c for c in REQUIRED_RAW_COLUMNS if c not in raw.columns]
    if missing:
        return [f"missing raw columns: {missing}"]
    out = []
    seasons = sorted(set(raw["season"].to_list()))
    if not seasons:
        return ["raw schedules are empty"]
    if seasons[0] != 1999:
        out.append(f"min season is {seasons[0]}, expected 1999")
    gaps = sorted(set(range(seasons[0], seasons[-1] + 1)) - set(seasons))
    if gaps:
        out.append(f"seasons not contiguous; missing {gaps}")
    return out


def check_codes(raw: pl.DataFrame) -> list[str]:
    out = []
    for code in sorted(unknown_codes(raw)):
        sample = raw.filter((pl.col("home_team") == code) | (pl.col("away_team") == code))["game_id"][0]
        out.append(f"unknown team code {code!r} (e.g. game {sample})")
    return out


def check_config_coverage(games: pl.DataFrame) -> list[str]:
    out = []
    seasons = sorted(set(games["season"].to_list()))
    for s in seasons:
        try:
            rules = season_config.season_rules(s)
        except Exception as e:  # noqa: BLE001 - any lookup failure is a coverage gap
            out.append(f"{s}: no season_rules ({e})")
            continue
        wc = games.filter((pl.col("season") == s) & (pl.col("game_type") == "WC")).height
        if wc:
            expected_pt = {4: 12, 6: 14}.get(wc)
            if expected_pt != rules["playoff_teams"]:
                out.append(f"{s}: {wc} WC games but playoff_teams={rules['playoff_teams']}")
        reg_max = games.filter((pl.col("season") == s) & pl.col("is_reg"))["week"].max()
        if reg_max != rules["reg_weeks"]:
            out.append(f"{s}: REG max week {reg_max} != reg_weeks {rules['reg_weeks']}")
    return out


def _season_teams(games: pl.DataFrame) -> pl.DataFrame:
    return pl.concat([
        games.select("season", pl.col("home_id").alias("franchise_id")),
        games.select("season", pl.col("away_id").alias("franchise_id")),
    ]).unique()


def check_team_counts(games: pl.DataFrame) -> list[str]:
    counts = _season_teams(games).group_by("season").agg(pl.len().alias("n")).sort("season")
    return [
        f"{s}: {n} franchises, expected {season_config.n_teams(s)}"
        for s, n in counts.iter_rows()
        if n != season_config.n_teams(s)
    ]


def check_games_per_team(games: pl.DataFrame) -> list[str]:
    reg = games.filter(pl.col("is_reg"))
    per = pl.concat([
        reg.select("season", pl.col("home_id").alias("franchise_id"), "played"),
        reg.select("season", pl.col("away_id").alias("franchise_id"), "played"),
    ]).group_by("season", "franchise_id").agg(
        pl.len().alias("scheduled"), pl.col("played").sum().alias("played")
    ).sort("season", "franchise_id")
    max_season = games["season"].max()
    out = []
    for s, team, scheduled, played in per.iter_rows():
        expected = season_config.EXPECTED_GAME_EXCEPTIONS.get((s, team), season_config.reg_games(s))
        if scheduled != expected:
            out.append(f"{s} {team}: {scheduled} REG games scheduled, expected {expected}")
        if s < max_season and played != scheduled:
            out.append(f"{s} {team}: {played} of {scheduled} REG games played in a completed season")
    return out


def check_continuity(games: pl.DataFrame, snapshots: pl.DataFrame, params: EloParams | None = None) -> list[str]:
    """Week-0 Elo == prior final regressed toward params.mean by params.revert (the params replay used)."""
    params = params or EloParams()
    out = []
    max_season = games["season"].max()
    present = {}
    for s, team in _season_teams(games).iter_rows():
        present.setdefault(team, set()).add(s)
    for team in sorted(CANONICAL):
        entry = season_config.ENTRY_SEASON.get(team, 1999)
        missing = sorted(set(range(entry, max_season + 1)) - present.get(team, set()))
        if missing:
            out.append(f"{team}: missing from seasons {missing}")

    last_week = snapshots.group_by("season").agg(pl.col("week").max().alias("wmax"))
    finals = (
        snapshots.join(last_week, on="season")
        .filter(pl.col("week") == pl.col("wmax"))
        .select(pl.col("season") + 1, "franchise_id", pl.col("elo").alias("prev_final"))
    )
    week0 = snapshots.filter(pl.col("week") == 0).select("season", "franchise_id", "elo")
    joined = week0.join(finals, on=["season", "franchise_id"], how="inner").with_columns(
        (params.mean * params.revert + (1 - params.revert) * pl.col("prev_final")).alias("expected")
    )
    bad = joined.filter((pl.col("elo") - pl.col("expected")).abs() > CONTINUITY_TOL)
    for s, team, elo, _prev, exp in bad.sort("season", "franchise_id").iter_rows():
        out.append(f"{s} {team}: week-0 Elo {elo:.4f} != regressed prior final {exp:.4f}")
    # Every franchise past its entry season must have a regressed week-0 row.
    have = {(s, t) for s, t in joined.select("season", "franchise_id").iter_rows()}
    for s, team in week0.select("season", "franchise_id").iter_rows():
        if s > season_config.ENTRY_SEASON.get(team, 1999) and (s, team) not in have:
            out.append(f"{s} {team}: week-0 snapshot has no prior-season final to regress from")
    return out


def _components(edges: list[tuple[str, str]]) -> set[frozenset[str]]:
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    groups: dict[str, set[str]] = {}
    for x in list(parent):
        groups.setdefault(find(x), set()).add(x)
    return {frozenset(g) for g in groups.values()}


def check_divisions(games: pl.DataFrame) -> list[str]:
    out = []
    div = games.filter(pl.col("is_reg") & (pl.col("div_game") == 1))
    for s in sorted(set(games["season"].to_list())):
        edges = div.filter(pl.col("season") == s).select("home_id", "away_id").rows()
        got = _components(edges)
        want = {frozenset(t) for t in season_config.divisions(s).values()}
        if got != want:
            extra = sorted(sorted(g) for g in got - want)
            lacking = sorted(sorted(g) for g in want - got)
            out.append(f"{s}: div_game components {extra} do not match config divisions {lacking}")
    return out


def check_result_consistency(games: pl.DataFrame) -> list[str]:
    bad = games.filter(
        pl.col("played") & (pl.col("result") != pl.col("home_score") - pl.col("away_score"))
    )
    return [f"{gid}: result != home_score - away_score" for gid in bad["game_id"].to_list()]


def check_elo_zero_sum(games: pl.DataFrame) -> list[str]:
    drift = (pl.col("elo_post_home") - pl.col("elo_pre_home")) + (
        pl.col("elo_post_away") - pl.col("elo_pre_away")
    )
    played = games.filter(pl.col("played"))
    out = [f"{gid}: played game has null Elo" for gid in
           played.filter(pl.col("elo_post_home").is_null() | pl.col("elo_post_away").is_null())["game_id"]]
    bad = played.with_columns(drift.alias("drift")).filter(pl.col("drift").abs() >= ELO_TOL)
    out += [f"{gid}: Elo not zero-sum (drift {d:.3e})" for gid, d in bad.select("game_id", "drift").iter_rows()]
    return out


def check_week_date_order(games: pl.DataFrame) -> list[str]:
    """Flag played games dated before a played game from an earlier-labelled week (same season).

    Such an inversion means a game was postponed but kept its week label. Replay orders by date
    and keys results by asof_week, so snapshots stay as-of correct; this check still fails so a
    human looks at the reschedule (records, week semantics) before trusting the build.
    """
    played = games.filter(pl.col("played"))
    prior = (
        played.group_by("season", "week")
        .agg(pl.col("gameday").max().alias("hi"))
        .sort("season", "week")
        .with_columns(pl.col("hi").cum_max().shift(1).over("season").alias("prior_hi"))
        .select("season", "week", "prior_hi")
    )
    bad = (
        played.join(prior, on=["season", "week"])
        .filter(pl.col("gameday") < pl.col("prior_hi"))
        .sort("season", "week", "gameday", "game_id")
    )
    return [
        f"{s} {gid} (wk{w}, {day}) precedes an earlier-week game played {hi}; week and date order disagree"
        for s, w, gid, day, hi in bad.select("season", "week", "game_id", "gameday", "prior_hi").iter_rows()
    ]


def check_league_mean(snapshots: pl.DataFrame, params: EloParams | None = None) -> list[str]:
    mean = (params or EloParams()).mean
    means = (
        snapshots.filter((pl.col("week") == 0) & (pl.col("season") >= MEAN_CHECK_FROM))
        .group_by("season").agg(pl.col("elo").mean().alias("m")).sort("season")
    )
    return [
        f"{s}: week-0 league mean Elo {m:.3f}, expected {mean} +/- {MEAN_TOL}"
        for s, m in means.iter_rows()
        if abs(m - mean) >= MEAN_TOL
    ]


def check_snapshot_grid(snapshots: pl.DataFrame, games: pl.DataFrame) -> list[str]:
    """Dense (season, week, franchise) grid: n_teams x (last played week + 1) rows per season.

    A scheduled season with no played games yet expects week 0 only (n_teams rows).
    """
    out = []
    keys = ["season", "week", "franchise_id"]
    nulls = snapshots.filter(pl.col("elo").is_null())
    for s, w, team in nulls.select(keys).head(10).iter_rows():
        out.append(f"{s} week {w} {team}: null elo")
    if nulls.height > 10:
        out.append(f"... {nulls.height} null-elo rows in total")
    dups = snapshots.group_by(keys).len().filter(pl.col("len") > 1).sort(keys)
    for s, w, team, n in dups.head(10).iter_rows():
        out.append(f"{s} week {w} {team}: {n} duplicate rows")
    wk = "asof_week" if "asof_week" in games.columns else "week"
    wmax = dict(
        games.filter(pl.col("played")).group_by("season").agg(pl.col(wk).max()).iter_rows()
    )
    rows = dict(snapshots.group_by("season").len().iter_rows())
    scheduled = set(games["season"].to_list())
    for s in sorted(scheduled | set(rows)):
        if s not in scheduled:
            out.append(f"{s}: snapshots present but season not in games")
            continue
        w = wmax.get(s, 0)
        expected = season_config.n_teams(s) * (w + 1)
        if rows.get(s, 0) != expected:
            out.append(
                f"{s}: {rows.get(s, 0)} snapshot rows, expected {expected} "
                f"({season_config.n_teams(s)} teams x weeks 0-{w})"
            )
    week0 = {(s, t) for s, t in snapshots.filter(pl.col("week") == 0).select("season", "franchise_id").iter_rows()}
    for s, team in _season_teams(games).sort("season", "franchise_id").iter_rows():
        if (s, team) not in week0:
            out.append(f"{s} {team}: no week-0 snapshot")
    return out


SIM_P_TOL = 1e-6
SIM_W_TOL = 1e-3


def check_sim(sim: pl.DataFrame, games: pl.DataFrame) -> list[str]:
    """Per (season, week): playoff probabilities sum to the season's playoff spots and expected
    wins sum to its REG game count. Seasons whose team count differs from the configured league
    size (synthetic leagues) are skipped."""
    present = dict(_season_teams(games).group_by("season").len().iter_rows())
    reg = dict(games.filter(pl.col("is_reg")).group_by("season").len().iter_rows())
    sums = (
        sim.group_by("season", "week")
        .agg(pl.col("playoff_prob").sum().alias("sp"), pl.col("exp_wins").sum().alias("sw"))
        .sort("season", "week")
    )
    out = []
    for s, w, sp, sw in sums.iter_rows():
        if present.get(s) != season_config.n_teams(s):
            continue
        spots, n_reg = season_config.playoff_teams(s), reg.get(s, 0)
        if abs(sp - spots) > SIM_P_TOL:
            out.append(f"{s} week {w}: playoff_prob sums to {sp:.6f}, expected {spots}")
        if abs(sw - n_reg) > SIM_W_TOL:
            out.append(f"{s} week {w}: exp_wins sums to {sw:.4f}, expected {n_reg} REG games")
    return out


VEGAS_SEASONS = (2003, 2020)  # nflverse win_totals.csv coverage (expectation.py)


def check_vegas_coverage(games: pl.DataFrame, vegas: pl.DataFrame | None) -> list[str]:
    """WR-04: every scheduled season in 2003-2020 has Vegas win totals. Without them vs_exp
    silently switches to model-sourced expectations, which changes scores and backtest fits."""
    lo, hi = VEGAS_SEASONS
    want = sorted(s for s in set(games["season"].to_list()) if lo <= s <= hi)
    if not want:
        return []
    if vegas is None:
        return [f"no Vegas win totals (win_totals.csv missing?): seasons {want[0]}-{want[-1]} "
                "would use model-sourced expectations"]
    have = set(vegas["season"].to_list())
    missing = [s for s in want if s not in have]
    return [f"{s}: no Vegas win totals; expectations would be model-sourced" for s in missing]


# (name, callable(raw, derived, params) -> list[str]); params are the EloParams derive() used.
CheckFn = Callable[[pl.DataFrame, dict[str, pl.DataFrame], EloParams], list[str]]
CHECKS: list[tuple[str, CheckFn]] = [
    ("columns", lambda raw, d, p: check_columns(raw)),
    ("config_coverage", lambda raw, d, p: check_config_coverage(d["games"])),
    ("team_counts", lambda raw, d, p: check_team_counts(d["games"])),
    ("games_per_team", lambda raw, d, p: check_games_per_team(d["games"])),
    ("continuity", lambda raw, d, p: check_continuity(d["games"], d["snapshots"], p)),
    ("divisions", lambda raw, d, p: check_divisions(d["games"])),
    ("result_consistency", lambda raw, d, p: check_result_consistency(d["games"])),
    ("elo_zero_sum", lambda raw, d, p: check_elo_zero_sum(d["games"])),
    ("week_date_order", lambda raw, d, p: check_week_date_order(d["games"])),
    ("league_mean", lambda raw, d, p: check_league_mean(d["snapshots"], p)),
    ("snapshot_grid", lambda raw, d, p: check_snapshot_grid(d["snapshots"], d["games"])),
    ("pbp_coverage", lambda raw, d, p: [] if d.get("team_game_epa") is None
     else pbp.check_pbp(d["team_game_epa"], d["team_games"])),
    ("sim_sums", lambda raw, d, p: [] if d.get("sim") is None else check_sim(d["sim"], d["games"])),
    ("vegas_coverage", lambda raw, d, p: check_vegas_coverage(d["games"], d.get("vegas"))),
]


def run_checks(
    raw: pl.DataFrame, derived: dict[str, pl.DataFrame], params: EloParams | None = None
) -> list[tuple[str, list[str]]]:
    """Per-check results, in CHECKS order (check_codes excluded; callers run it first).

    Pass the same `params` that derive() used, so param-dependent checks validate that replay.
    """
    params = params or EloParams()
    return [(name, fn(raw, derived, params)) for name, fn in CHECKS]


# Soft checks (WR-02): same signature as CHECKS, but their messages are printed as warnings and
# never fail `fgs check` / `fgs refresh`.
WARNINGS: list[tuple[str, CheckFn]] = [
    ("pbp_lag", lambda raw, d, p: [] if d.get("team_game_epa") is None
     else pbp.pbp_lag(d["team_game_epa"], d["team_games"])),
]


def run_warnings(
    raw: pl.DataFrame, derived: dict[str, pl.DataFrame], params: EloParams | None = None
) -> list[tuple[str, list[str]]]:
    """Per-warning results, in WARNINGS order."""
    params = params or EloParams()
    return [(name, fn(raw, derived, params)) for name, fn in WARNINGS]


def run_all(raw: pl.DataFrame, derived: dict[str, pl.DataFrame], params: EloParams | None = None) -> list[str]:
    return [f"{name}: {msg}" for name, fails in run_checks(raw, derived, params) for msg in fails]

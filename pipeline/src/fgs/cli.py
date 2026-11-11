"""`fgs` command line: ingest, build, elo, check."""

import argparse
import sys

import polars as pl

from fgs import checks
from fgs.elo import EloParams, replay
from fgs.games import build_games, build_team_games
from fgs.ingest import load_schedules
from fgs.paths import DERIVED_DIR
from fgs.snapshots import build_grid


def derive(raw: pl.DataFrame, params: EloParams | None = None) -> dict[str, pl.DataFrame]:
    """Pure: raw schedules -> games (with Elo), team_games, snapshots. No file I/O."""
    games, sparse = replay(build_games(raw), params or EloParams())
    team_games = build_team_games(games)
    return {"games": games, "team_games": team_games, "snapshots": build_grid(games, team_games, sparse)}


def build_all(refresh: bool = False) -> dict[str, pl.DataFrame]:
    raw = load_schedules(refresh=refresh)
    out = derive(raw)
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    out["games"].write_parquet(DERIVED_DIR / "games.parquet")
    out["team_games"].write_parquet(DERIVED_DIR / "team_games.parquet")
    out["snapshots"].write_parquet(DERIVED_DIR / "elo_snapshots.parquet")
    print(
        f"built: raw {raw.height} rows, games {out['games'].height}, "
        f"team_games {out['team_games'].height}, elo_snapshots {out['snapshots'].height}"
    )
    latest = _latest_played(out["games"])
    if latest is not None:
        print(f"latest: {latest[0]} week {latest[1]} (data through {_data_through(out['games'], *latest)})")
    return {"raw": raw, **out}


def _latest_played(games: pl.DataFrame, season: int | None = None) -> tuple[int, int] | None:
    """(season, week) of the latest played game, from cached data only (D-24)."""
    played = games.filter(pl.col("played"))
    if season is not None:
        played = played.filter(pl.col("season") == season)
    if played.is_empty():
        return None
    s = played["season"].max() if season is None else season
    return int(s), int(played.filter(pl.col("season") == s)["week"].max())


def _data_through(games: pl.DataFrame, season: int, week: int) -> str:
    """Max gameday among played games at or before (season, week)."""
    played = games.filter(
        pl.col("played")
        & ((pl.col("season") < season) | ((pl.col("season") == season) & (pl.col("week") <= week)))
    )
    return str(played["gameday"].max()) if not played.is_empty() else "n/a"


def _cmd_ingest(args) -> int:
    raw = load_schedules(refresh=args.refresh or args.all)
    print(f"schedules: {raw.height} games, seasons {raw['season'].min()}-{raw['season'].max()}")
    return 0


def _cmd_build(args) -> int:
    build_all(refresh=args.refresh)
    return 0


def _cmd_elo(args) -> int:
    snap_path, games_path = DERIVED_DIR / "elo_snapshots.parquet", DERIVED_DIR / "games.parquet"
    if not snap_path.exists() or not games_path.exists():
        print("no derived data found; run `uv run fgs build` first", file=sys.stderr)
        return 1
    games = pl.read_parquet(games_path)
    seasons = games["season"]
    lo, hi = int(seasons.min()), int(seasons.max())
    if args.season is None:
        latest = _latest_played(games)
        if latest is None:
            print("no played games in cached data", file=sys.stderr)
            return 1
        season = latest[0]
    else:
        season = args.season
        if not lo <= season <= hi:
            print(f"season {season} not in data; available seasons: {lo}-{hi}", file=sys.stderr)
            return 1
    latest = _latest_played(games, season)
    latest_week = latest[1] if latest is not None else 0
    week = latest_week if args.week is None else args.week
    if week < 0:
        print(f"week must be >= 0, got {week}", file=sys.stderr)
        return 1
    if week > latest_week:
        print(f"{season} week {week} not played yet; latest played week is {latest_week}", file=sys.stderr)
        return 1

    rows = (
        pl.read_parquet(snap_path)
        .filter((pl.col("season") == season) & (pl.col("week") == week))
        .sort(["elo", "franchise_id"], descending=[True, False])
    )
    if rows.is_empty():
        print(f"no snapshot for {season} week {week}", file=sys.stderr)
        return 1
    if args.top is not None:
        rows = rows.head(args.top)

    header = f"{season} week {week} (data through {_data_through(games, season, week)})"
    wk = games.filter((pl.col("season") == season) & (pl.col("week") == week))
    n_played = int(wk["played"].sum())
    if 0 < n_played < wk.height:
        header += f"; partial week: {n_played} of {wk.height} games played"
    print(header)
    print(f"{'#':>3}  {'Team':<4}  {'Elo':>5}  W-L-T")
    for rank, r in enumerate(rows.iter_rows(named=True), start=1):
        print(f"{rank:>3}  {r['franchise_id']:<4}  {round(r['elo']):>5}  {r['wins']}-{r['losses']}-{r['ties']}")
    return 0


def _cmd_check(args) -> int:
    raw = load_schedules()  # module-level name so tests can monkeypatch fgs.cli.load_schedules
    failed = False
    for name, fails in (("columns", checks.check_columns(raw)), ("codes", checks.check_codes(raw))):
        failed |= _report(name, fails)
    if failed:
        print("raw data failed pre-derive checks; not deriving")
        return 1
    params = EloParams()
    derived = derive(raw, params)
    for name, fails in checks.run_checks(raw, derived, params):
        if name == "columns":
            continue  # already reported above
        failed |= _report(name, fails)
    print("FAILED" if failed else "all checks passed")
    return 1 if failed else 0


def _report(name: str, fails: list[str]) -> bool:
    print(f"{'FAIL' if fails else 'ok':<4}  {name}")
    for msg in fails:
        print(f"      - {msg}")
    return bool(fails)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fgs", description="Feel-good score pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ingest", help="download nflverse schedules into the local cache")
    p.add_argument("--refresh", action="store_true", help="re-download even if cached")
    p.add_argument("--all", action="store_true",
                   help="re-download everything (same as --refresh for schedules, which is one file)")
    p.set_defaults(func=_cmd_ingest)

    p = sub.add_parser("build", help="ingest (cached) + derive games, team_games, elo_snapshots")
    p.add_argument("--refresh", action="store_true", help="re-download schedules first")
    p.set_defaults(func=_cmd_build)

    p = sub.add_parser("elo", help="ranked Elo table as of a (season, week); default = latest played week")
    p.add_argument("--season", type=int, default=None, help="default: latest season in the data")
    p.add_argument("--week", type=int, default=None, help="default: latest played week of the season")
    p.add_argument("--top", type=int, default=None, help="show only the top N teams")
    p.set_defaults(func=_cmd_elo)

    p = sub.add_parser("check", help="run all data-trust checks; exit 1 on any failure")
    p.set_defaults(func=_cmd_check)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

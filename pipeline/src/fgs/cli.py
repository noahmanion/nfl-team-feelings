"""`fgs` command line: ingest, build, elo."""

import argparse
import sys

import polars as pl

from fgs.elo import replay
from fgs.games import build_games, build_team_games
from fgs.ingest import load_schedules
from fgs.paths import DERIVED_DIR
from fgs.snapshots import build_grid


def derive(raw: pl.DataFrame) -> dict[str, pl.DataFrame]:
    """Pure: raw schedules -> games (with Elo), team_games, snapshots. No file I/O."""
    games, sparse = replay(build_games(raw))
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
    return {"raw": raw, **out}


def _cmd_ingest(args) -> int:
    raw = load_schedules(refresh=args.refresh or args.all)
    print(f"schedules: {raw.height} games, seasons {raw['season'].min()}-{raw['season'].max()}")
    return 0


def _cmd_build(args) -> int:
    build_all(refresh=args.refresh)
    return 0


def _cmd_elo(args) -> int:
    path = DERIVED_DIR / "elo_snapshots.parquet"
    if not path.exists():
        print("no snapshots found; run `uv run fgs build` first", file=sys.stderr)
        return 1
    rows = (
        pl.read_parquet(path)
        .filter((pl.col("season") == args.season) & (pl.col("week") == args.week))
        .sort(["elo", "franchise_id"], descending=[True, False])
    )
    if rows.is_empty():
        print(f"no snapshot for {args.season} week {args.week}", file=sys.stderr)
        return 1
    if args.top is not None:
        rows = rows.head(args.top)
    print(f"{args.season} week {args.week}")
    print(f"{'#':>3}  {'Team':<4}  {'Elo':>5}  W-L-T")
    for rank, r in enumerate(rows.iter_rows(named=True), start=1):
        print(f"{rank:>3}  {r['franchise_id']:<4}  {round(r['elo']):>5}  {r['wins']}-{r['losses']}-{r['ties']}")
    return 0


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

    p = sub.add_parser("elo", help="ranked Elo table as of a (season, week)")
    p.add_argument("--season", type=int, required=True)
    p.add_argument("--week", type=int, required=True)
    p.add_argument("--top", type=int, default=None, help="show only the top N teams")
    p.set_defaults(func=_cmd_elo)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

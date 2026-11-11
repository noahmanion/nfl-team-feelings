"""`fgs` command line: ingest, build, elo, check, export, refresh, backtest."""

import argparse
import json
import sys
from datetime import datetime, timezone

import polars as pl

from fgs import checks, export, features, score
from fgs.backtest import format_proposal, format_report, propose_weights, run_backtest
from fgs.asof import data_through, latest_played
from fgs.elo import EloParams, replay
from fgs.games import build_games, build_team_games
from fgs.ingest import load_schedules, load_teams, save_cache
from fgs.paths import CACHE_DIR, DERIVED_DIR, WEB_DATA_DIR
from fgs.snapshots import build_grid


def derive_games(
    games: pl.DataFrame, params: EloParams | None = None, weights: dict[str, float] | None = None
) -> dict:
    """Pure (apart from reading weights.yaml when weights is None): normalized games ->
    games (with Elo), team_games, snapshots (the Elo grid), features (factors + composite) and
    the exact weights dict that produced the contributions (export reports these, not a re-read)."""
    games, sparse = replay(games, params)
    team_games = build_team_games(games)
    snapshots = build_grid(games, team_games, sparse)
    feats = features.build_features(snapshots, team_games)
    w = dict(score.load_weights() if weights is None else weights)
    feats = score.composite(feats, w)
    return {"games": games, "team_games": team_games, "snapshots": snapshots, "features": feats, "weights": w}


def derive(
    raw: pl.DataFrame, params: EloParams | None = None, weights: dict[str, float] | None = None
) -> dict:
    """Raw schedules -> derive_games(build_games(raw)). No file I/O beyond the weights file."""
    return derive_games(build_games(raw), params, weights)


def build_all(refresh: bool = False) -> dict[str, pl.DataFrame]:
    raw = load_schedules(refresh=refresh)
    out = derive(raw)
    _write_derived(out)
    print(
        f"built: raw {raw.height} rows, games {out['games'].height}, "
        f"team_games {out['team_games'].height}, elo_snapshots {out['snapshots'].height}"
    )
    latest = _latest_played(out["games"])
    if latest is not None:
        print(f"latest: {latest[0]} week {latest[1]} (data through {_data_through(out['games'], *latest)})")
    return {"raw": raw, **out}


def _write_derived(out: dict[str, pl.DataFrame]) -> None:
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)  # module global read at call time (tests monkeypatch it)
    out["games"].write_parquet(DERIVED_DIR / "games.parquet")
    out["team_games"].write_parquet(DERIVED_DIR / "team_games.parquet")
    out["snapshots"].write_parquet(DERIVED_DIR / "elo_snapshots.parquet")
    out["features"].write_parquet(DERIVED_DIR / "features.parquet")


# Kept under the old names so existing callers/tests keep working.
_latest_played = latest_played
_data_through = data_through


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
    if args.top is not None and args.top < 1:
        print(f"--top must be >= 1, got {args.top}", file=sys.stderr)
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


def _checked_derive(raw: pl.DataFrame) -> tuple[bool, dict[str, pl.DataFrame] | None, EloParams]:
    """Pre-derive checks (columns, codes), then derive and run every post-derive check. No file I/O."""
    params = EloParams()
    failed = False
    for name, fails in (("columns", checks.check_columns(raw)), ("codes", checks.check_codes(raw))):
        failed |= _report(name, fails)
    if failed:
        print("raw data failed pre-derive checks; not deriving")
        return False, None, params
    derived = derive(raw, params)
    for name, fails in checks.run_checks(raw, derived, params):
        if name == "columns":
            continue  # already reported above
        failed |= _report(name, fails)
    print("FAILED" if failed else "all checks passed")
    return not failed, derived, params


def _cmd_check(args) -> int:
    raw = load_schedules()  # module-level name so tests can monkeypatch fgs.cli.load_schedules
    ok, _, _ = _checked_derive(raw)
    return 0 if ok else 1


def _cmd_refresh(args) -> int:
    """D-09: re-download (in memory) -> derive -> check (abort, writing nothing) -> raw cache -> parquet -> JSON.

    The downloads are not persisted until every check passes and the export builds, so a bad
    nflverse file never replaces the good raw cache that `fgs export`/`build`/`check` read.
    """
    raw = load_schedules(refresh=True, write_cache=False)
    teams = load_teams(refresh=True, write_cache=False)
    ok, derived, _ = _checked_derive(raw)
    if not ok:
        print("checks failed; cache and JSON not updated", file=sys.stderr)
        return 1
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    files = export.build_export(derived, teams, generated_at=generated_at)  # pure; may still raise before writes
    cache_dir = CACHE_DIR  # module global read at call time (tests monkeypatch it)
    save_cache(raw, "schedules.parquet", cache_dir)
    save_cache(teams, "teams.parquet", cache_dir)
    _write_derived(derived)
    export.write_export(files, WEB_DATA_DIR)
    meta = files["meta.json"]
    print(
        f"refreshed: exported {len(files)} files; latest {meta['latest']['season']} week "
        f"{meta['latest']['week']} (partial={meta['partial_week']}); data through {meta['data_through']}"
    )
    return 0


def _cmd_export(args) -> int:
    derived = derive(load_schedules())  # cache only (downloads once if missing)
    teams = load_teams()
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    files = export.build_export(derived, teams, generated_at=generated_at)
    out_dir = WEB_DATA_DIR  # module global read at call time so tests can monkeypatch it
    export.write_export(files, out_dir)
    meta = files["meta.json"]
    print(
        f"exported {len(files)} files to {out_dir}; latest {meta['latest']['season']} "
        f"week {meta['latest']['week']} (partial={meta['partial_week']})"
    )
    return 0


def _cmd_backtest(args) -> int:
    derived = derive(load_schedules())  # cache only (downloads once if missing)
    report = run_backtest(derived, include_holdout=args.include_holdout)
    print(format_report(report))
    out_dir = DERIVED_DIR  # module global read at call time so tests can monkeypatch it
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "backtest.json"
    path.write_text(json.dumps(report, allow_nan=False, indent=1) + "\n")
    print(f"\nwrote {path}")
    if args.propose_weights:
        prop = propose_weights(derived)  # always 1999-2021 only, even with --include-holdout
        today = datetime.now(timezone.utc).date().isoformat()
        print("\nproposed weights (paste into pipeline/weights.yaml; points of N=8 adjusted margin per SD):\n")
        print(format_proposal(prop, today))
    return 0


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

    p = sub.add_parser("export", help="write the site JSON contract to web/public/data from cached data; no network")
    p.set_defaults(func=_cmd_export)

    p = sub.add_parser("refresh", help="re-download nflverse data, run all checks, then regenerate derived "
                                       "parquet and the site JSON (writes nothing if a check fails)")
    p.set_defaults(func=_cmd_refresh)

    p = sub.add_parser("backtest", help="walk-forward backtest vs baselines; writes data/derived/backtest.json")
    p.add_argument("--include-holdout", action="store_true", help="Phase 6 only: also test 2022–2025")
    p.add_argument("--propose-weights", action="store_true",
                   help="also print ridge weights fit on 1999–2021 (N=8) as a weights.yaml block")
    p.set_defaults(func=_cmd_backtest)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

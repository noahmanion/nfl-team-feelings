"""`fgs` command line: ingest, build, elo, check, export, refresh, backtest."""

import argparse
import json
import sys
import time
from datetime import datetime, timezone

import polars as pl

from fgs import checks, export, features, score, sim
from fgs.backtest import format_proposal, format_report, propose_weights, run_backtest
from fgs.asof import data_through, latest_played
from fgs.elo import EloParams, replay
from fgs.expectation import load_win_totals, vegas_expectations
from fgs.games import build_games, build_team_games
from fgs.ingest import load_schedules, load_teams, save_cache
from fgs.paths import CACHE_DIR, DERIVED_DIR, WEB_DATA_DIR
from fgs.pbp import PBP_SUBDIR, cached_seasons, load_all_pbp, load_pbp_season, team_game_epa
from fgs.snapshots import build_grid


def derive_games(
    games: pl.DataFrame, params: EloParams | None = None, weights: dict[str, float] | None = None,
    scored: bool = True, *, pbp_games: pl.DataFrame | None = None, vegas: pl.DataFrame | None = None,
    sim_cache_dir=None, sim_write_cache: bool = True,
) -> dict:
    """Pure (apart from reading weights.yaml when weights is None and the sim cache): normalized games ->
    games (with Elo), team_games, snapshots (the Elo grid), features (factors + composite) and
    the exact weights dict that produced the contributions (export reports these, not a re-read).

    scored=False stops after the Elo grid (no features, no weights): the backtest rebuilds its
    own features and must not need a valid weights.yaml to propose one.

    pbp_games (pbp.team_game_epa frame, or None) is carried through as derived["team_game_epa"].
    The season simulator always runs (derived["sim"], also when scored=False), reusing
    sim_cache_dir/{model_version}.parquet when given; sim_write_cache=False leaves that cache
    untouched (refresh saves it after the checks pass). vegas (expectation.vegas_expectations
    frame, or None) is carried through as derived["vegas"]."""
    games, sparse = replay(games, params)
    team_games = build_team_games(games)
    snapshots = build_grid(games, team_games, sparse)
    sim_frame = sim.simulate_all(games, snapshots, cache_dir=sim_cache_dir, write_cache=sim_write_cache)
    base = {
        "games": games, "team_games": team_games, "snapshots": snapshots, "team_game_epa": pbp_games,
        "sim": sim_frame, "vegas": vegas,
    }
    if not scored:
        return base
    feats = features.build_features(snapshots, team_games, pbp_games=pbp_games, sim=sim_frame, vegas=vegas)
    w = dict(score.load_weights() if weights is None else weights)
    feats = score.composite(feats, w)
    return {**base, "features": feats, "weights": w}


def derive(
    raw: pl.DataFrame, params: EloParams | None = None, weights: dict[str, float] | None = None,
    scored: bool = True, *, pbp_games: pl.DataFrame | None = None, vegas: pl.DataFrame | None = None,
    sim_cache_dir=None, sim_write_cache: bool = True,
) -> dict:
    """Raw schedules -> derive_games(build_games(raw)). No file I/O beyond the weights file and sim cache."""
    return derive_games(
        build_games(raw), params, weights, scored=scored, pbp_games=pbp_games, vegas=vegas,
        sim_cache_dir=sim_cache_dir, sim_write_cache=sim_write_cache,
    )


PBP_FIRST_SEASON = 1999


def _current_season(games: pl.DataFrame) -> int:
    """Season of the latest played week (else the max schedule season)."""
    if "played" not in games.columns:  # raw schedules: played = has a result
        games = games.with_columns(pl.col("result").is_not_null().alias("played"))
    latest = latest_played(games)
    if latest is not None:
        return int(latest[0])
    played = games.filter(pl.col("played"))
    return int((played if played.height else games)["season"].max())


def pbp_seasons(games: pl.DataFrame) -> list[int]:
    """pbp seasons to load: 1999 through the current season. `games` = raw schedules or build_games(raw)
    (raw works too, so refresh can pick seasons before the code checks have run)."""
    return list(range(PBP_FIRST_SEASON, _current_season(games) + 1))


def _cached_vegas(cache_dir) -> pl.DataFrame | None:
    """Normalized Vegas expectations from the cached win_totals.csv (never downloads)."""
    wt = cache_dir / "win_totals.csv"
    return vegas_expectations(pl.read_csv(wt)) if wt.exists() else None


def cached_inputs(cache_dir=None) -> dict:
    """Optional derive() inputs read from the cache only (no network). None when not cached."""
    cache_dir = CACHE_DIR if cache_dir is None else cache_dir  # module global read at call time
    vegas = _cached_vegas(cache_dir)
    seasons = cached_seasons(cache_dir)
    if not seasons:
        return {"pbp_games": None, "vegas": vegas}
    return {"pbp_games": team_game_epa(load_all_pbp(seasons, cache_dir, write_cache=False)), "vegas": vegas}


SIM_CACHE_DIR = None  # None -> DERIVED_DIR / "sim"; the test suite points it at a session tmp dir


def sim_cache_dir():
    """Sim cache location (module globals read at call time so tests can monkeypatch them)."""
    return DERIVED_DIR / "sim" if SIM_CACHE_DIR is None else SIM_CACHE_DIR


def build_all(refresh: bool = False) -> dict[str, pl.DataFrame]:
    raw = load_schedules(refresh=refresh)
    seasons = pbp_seasons(raw)
    current = seasons[-1]
    try:
        plays = load_all_pbp(seasons, CACHE_DIR, refresh_seasons=[current] if refresh else ())
    except Exception as e:  # noqa: BLE001 - WR-02: current-season pbp release missing/unavailable
        print(f"warning: pbp download failed ({type(e).__name__}: {e}); building without new "
              f"{current} pbp", file=sys.stderr)
        keep = [s for s in seasons if s != current or s in cached_seasons(CACHE_DIR)]
        plays = load_all_pbp(keep, CACHE_DIR)
    tge = team_game_epa(plays)
    vegas = vegas_expectations(load_win_totals())  # frozen file, downloaded once
    out = derive(raw, pbp_games=tge, vegas=vegas, sim_cache_dir=sim_cache_dir())
    _write_derived(out)
    print(
        f"built: raw {raw.height} rows, games {out['games'].height}, "
        f"team_games {out['team_games'].height}, elo_snapshots {out['snapshots'].height}"
    )
    print(f"pbp: {tge.height} team-games, seasons {seasons[0]}-{seasons[-1]}")
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
    if out.get("team_game_epa") is not None:
        out["team_game_epa"].write_parquet(DERIVED_DIR / "team_game_epa.parquet")


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


def _checked_derive(
    raw: pl.DataFrame, pbp_games: pl.DataFrame | None = None, **derive_kw,
) -> tuple[bool, dict[str, pl.DataFrame] | None, EloParams]:
    """Pre-derive checks (columns, codes), then derive and run every post-derive check. No file I/O."""
    params = EloParams()
    failed = False
    for name, fails in (("columns", checks.check_columns(raw)), ("codes", checks.check_codes(raw))):
        failed |= _report(name, fails)
    if failed:
        print("raw data failed pre-derive checks; not deriving")
        return False, None, params
    derived = derive(raw, params, pbp_games=pbp_games, **derive_kw)
    for name, fails in checks.run_checks(raw, derived, params):
        if name == "columns":
            continue  # already reported above
        failed |= _report(name, fails)
    for name, warns in checks.run_warnings(raw, derived, params):
        _warn(name, warns)
    print("FAILED" if failed else "all checks passed")
    return not failed, derived, params


def _cmd_check(args) -> int:
    raw = load_schedules()  # module-level name so tests can monkeypatch fgs.cli.load_schedules
    ok, _, _ = _checked_derive(raw, **cached_inputs(), sim_cache_dir=sim_cache_dir())
    return 0 if ok else 1


def _download_pbp(season: int, cache_dir) -> pl.DataFrame | None:
    """In-memory pbp download for refresh; None (with a warning) when the release is missing or
    unavailable (WR-02: e.g. the current season's file before its first game is processed). The
    caller falls back to the cached season, else builds without it; pbp_coverage still fails
    hard for any non-lagging gap that leaves."""
    try:
        return load_pbp_season(season, refresh=True, cache_dir=cache_dir, write_cache=False)
    except Exception as e:  # noqa: BLE001 - any download failure degrades to a warning
        print(f"warning: {season} pbp download failed ({type(e).__name__}: {e}); "
              "using the cached season if any", file=sys.stderr)
        return None


def _cmd_refresh(args) -> int:
    """D-09: re-download (in memory) -> derive -> check (abort, writing nothing) -> raw cache -> parquet -> JSON.

    The downloads are not persisted until every check passes and the export builds, so a bad
    nflverse file never replaces the good raw cache that `fgs export`/`build`/`check` read.
    """
    t0 = time.perf_counter()
    cache_dir = CACHE_DIR  # module global read at call time (tests monkeypatch it)
    raw = load_schedules(refresh=True, write_cache=False)
    teams = load_teams(refresh=True, write_cache=False)
    seasons = pbp_seasons(raw)
    current = seasons[-1]
    # Only the current season is re-downloaded; earlier seasons come from the cache. Any that
    # are missing are downloaded in memory too and saved with the rest after checks pass.
    have = set(cached_seasons(cache_dir))
    fetched: dict[int, pl.DataFrame] = {}
    cached: list[int] = []
    for s in seasons:
        if s == current or s not in have:
            df = _download_pbp(s, cache_dir)
            if df is not None:
                fetched[s] = df
            elif s in have:
                cached.append(s)  # download failed: keep the last good cached season
        else:
            cached.append(s)
    frames = ([load_all_pbp(cached, cache_dir, write_cache=False)] if cached else []) + list(fetched.values())
    tge = team_game_epa(pl.concat(frames, how="diagonal_relaxed")) if frames else None
    # Vegas comes from the real cache (frozen file; never downloaded here). The sim cache is read
    # but only written after every check passes, so only changed seasons are re-simulated.
    vegas = _cached_vegas(cache_dir)
    sims = sim_cache_dir()
    ok, derived, _ = _checked_derive(raw, pbp_games=tge, vegas=vegas, sim_cache_dir=sims, sim_write_cache=False)
    if not ok:
        print("checks failed; cache and JSON not updated", file=sys.stderr)
        return 1
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    files = export.build_export(derived, teams, generated_at=generated_at)  # pure; may still raise before writes
    save_cache(raw, "schedules.parquet", cache_dir)
    save_cache(teams, "teams.parquet", cache_dir)
    for s, df in sorted(fetched.items()):
        save_cache(df, f"{PBP_SUBDIR}/{s}.parquet", cache_dir)
    _write_derived(derived)
    sim.save_sim_cache(derived["sim"], sims)
    export.write_export(files, WEB_DATA_DIR)
    meta = files["meta.json"]
    print(
        f"refreshed in {time.perf_counter() - t0:.1f}s: exported {len(files)} files; latest {meta['latest']['season']} week "
        f"{meta['latest']['week']} (partial={meta['partial_week']}); data through {meta['data_through']}"
    )
    return 0


def _cmd_export(args) -> int:
    derived = derive(load_schedules(), **cached_inputs(), sim_cache_dir=sim_cache_dir())  # cache only (schedules download once if missing)
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
    # cache only (downloads once if missing). Unscored: the backtest builds its own features,
    # so a missing/invalid weights.yaml must not block proposing new weights.
    derived = derive(load_schedules(), scored=False, **cached_inputs(), sim_cache_dir=sim_cache_dir())
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


def _warn(name: str, warns: list[str], limit: int = 10) -> None:
    """Print soft-check warnings (never fail). Silent when there are none."""
    if not warns:
        return
    print(f"{'warn':<4}  {name}")
    for msg in warns[:limit]:
        print(f"      - {msg}")
    if len(warns) > limit:
        print(f"      - ... {len(warns)} in total")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fgs", description="Feel-good score pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ingest", help="download nflverse schedules into the local cache")
    p.add_argument("--refresh", action="store_true", help="re-download even if cached")
    p.add_argument("--all", action="store_true",
                   help="re-download everything (same as --refresh for schedules, which is one file)")
    p.set_defaults(func=_cmd_ingest)

    p = sub.add_parser("build", help="ingest (cached) schedules + pbp, derive games, team_games, elo_snapshots, "
                                     "team_game_epa")
    p.add_argument("--refresh", action="store_true",
                   help="re-download schedules and the current season's pbp first")
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

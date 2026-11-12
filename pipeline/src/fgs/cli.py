"""`fgs` command line: ingest, build, elo, draft, check, export, refresh, backtest, freeze, holdout, evidence, logos."""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import polars as pl

from fgs import checks, draft, export, features, freeze, holdout, logos, paths, records, score, sim, wintotals
from fgs.backtest import (
    draft_gate, draft_walk_forward, format_draft_report, format_proposal, format_report, propose_weights,
    run_backtest,
)
from fgs.asof import data_through, latest_played
from fgs.elo import EloParams, replay
from fgs.expectation import load_win_totals, vegas_expectations
from fgs.games import build_games, build_team_games
from fgs.ingest import load_schedules, load_teams, save_cache
from fgs.paths import CACHE_DIR, DERIVED_DIR, WEB_DATA_DIR
from fgs.season_config import HOLDOUT_SEASONS, TRAIN_LAST_SEASON
from fgs.pbp import PBP_SUBDIR, cached_seasons, load_all_pbp, load_pbp_season, team_game_epa
from fgs.snapshots import build_grid


def derive_games(
    games: pl.DataFrame, params: EloParams | None = None, weights: dict[str, float] | None = None,
    scored: bool = True, *, pbp_games: pl.DataFrame | None = None, vegas: pl.DataFrame | None = None,
    sim_cache_dir=None, sim_write_cache: bool = True, draft_picks: pl.DataFrame | None = None,
    draft_values=None, offseason: dict | None = None,
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
    frame, or None) is carried through as derived["vegas"]. With draft_picks (draft.normalize_picks
    frame) and draft_values (draft.value_table array) both given, derived["draft"] is the
    draft.surplus_table frame (else None; also when scored=False, the backtest needs it), and
    derived["draft_values"] carries the value array for pick-equivalent text.

    Scored: score.apply_offseason adds the draft display columns (draft_surplus, draft_z,
    composite_inseason) and, only for a nonzero weights.yaml offseason.draft weight, contrib_draft.
    offseason overrides score.load_offseason() (tests); derived["offseason"] is the config used."""
    games, sparse = replay(games, params)
    team_games = build_team_games(games)
    snapshots = build_grid(games, team_games, sparse)
    sim_frame = sim.simulate_all(games, snapshots, cache_dir=sim_cache_dir, write_cache=sim_write_cache)
    base = {
        "games": games, "team_games": team_games, "snapshots": snapshots, "team_game_epa": pbp_games,
        "sim": sim_frame, "vegas": vegas,
        "draft": (draft.surplus_table(team_games, draft_picks, draft_values)
                  if draft_picks is not None and draft_values is not None else None),
        "draft_values": draft_values,
    }
    if not scored:
        return base
    feats = features.build_features(snapshots, team_games, pbp_games=pbp_games, sim=sim_frame, vegas=vegas)
    w = dict(score.load_weights() if weights is None else weights)
    feats = score.composite(feats, w)
    cfg = score.load_offseason() if offseason is None else offseason
    dz = (draft.draft_z(base["draft"], draft_winsor(base["draft"], cfg))
          if base["draft"] is not None else None)
    feats = score.apply_offseason(feats, dz, cfg)
    return {**base, "features": feats, "weights": w, "offseason": cfg}


def draft_winsor(surplus: pl.DataFrame, cfg: dict | None = None) -> tuple[float, float]:
    """The frozen weights.yaml offseason.draft.winsor caps. Without them, recompute from the
    2000-2021 surplus and warn on stderr (instead of silently dropping all draft display data)."""
    cfg = score.load_offseason() if cfg is None else cfg
    if cfg.get("winsor") is not None:
        return tuple(cfg["winsor"])
    b = draft.winsor_bounds(surplus)
    print(f"warning: weights.yaml has no offseason.draft.winsor; using caps recomputed from "
          f"2000-2021 surplus [{b[0]:+.2f}, {b[1]:+.2f}]", file=sys.stderr)
    return b


def derive(
    raw: pl.DataFrame, params: EloParams | None = None, weights: dict[str, float] | None = None,
    scored: bool = True, *, pbp_games: pl.DataFrame | None = None, vegas: pl.DataFrame | None = None,
    sim_cache_dir=None, sim_write_cache: bool = True, draft_picks: pl.DataFrame | None = None,
    draft_values=None,
) -> dict:
    """Raw schedules -> derive_games(build_games(raw)). No file I/O beyond the weights file and sim cache."""
    return derive_games(
        build_games(raw), params, weights, scored=scored, pbp_games=pbp_games, vegas=vegas,
        sim_cache_dir=sim_cache_dir, sim_write_cache=sim_write_cache, draft_picks=draft_picks,
        draft_values=draft_values,
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


def _cached_vegas(cache_dir, download: bool = False) -> pl.DataFrame | None:
    """Normalized Vegas expectations from the cached win_totals.csv. download=True (refresh)
    fetches the frozen file once when it is missing. When it is still missing, warn loudly (WR-04):
    2003-2020 expectations would silently become model-sourced; the vegas_coverage check fails."""
    wt = cache_dir / "win_totals.csv"
    if not wt.exists() and download:
        try:
            load_win_totals(cache_dir=cache_dir)
        except Exception as e:  # noqa: BLE001 - network failure: fall through to the warning
            print(f"warning: win_totals.csv download failed ({type(e).__name__}: {e})", file=sys.stderr)
    if not wt.exists():
        print(f"WARNING: {wt} is missing; 2003-2020 expectations fall back to the model "
              "(vs_exp and scores change). Run `uv run fgs build` to fetch it.", file=sys.stderr)
        return None
    frame = vegas_expectations(pl.read_csv(wt))
    # D-12: the score's Vegas expectations are the frozen nflverse 2003-2020 lines only. The 2021+
    # lines in pipeline/inputs/ are display-only (fgs.wintotals) and must never arrive here.
    # ValueError, not assert, so the guard survives `python -O`.
    if frame.height and int(frame["season"].max()) > 2020:
        raise ValueError(f"vegas_expectations must never read past 2020 (got season {int(frame['season'].max())} "
                         f"from {wt}); 2021+ win totals are display-only")
    return frame


def _display_win_totals(cache_dir) -> pl.DataFrame:
    """Export-only Vegas win totals (D-13): the cached nflverse 2003-2020 file (used_in_score=True)
    plus the committed, display-only 2021+ lines in pipeline/inputs/ (used_in_score=False).
    Never passed to derive(); the score's expectations come from _cached_vegas only.

    WR-01: a problem in the display-only 2021+ files (validation, overlap, unreadable) must not abort
    refresh/export. It warns on stderr and exports without the 2021+ rows (2003-2020 rows still
    exported). Strictness on the committed files is enforced by tests/test_wintotals.py."""
    wt = cache_dir / "win_totals.csv"
    raw = pl.read_csv(wt) if wt.exists() else None
    try:
        return wintotals.display_frame(raw, wintotals.load_display_win_totals())
    except (ValueError, OSError, pl.exceptions.PolarsError) as e:
        print(f"WARNING: display-only 2021+ win totals skipped ({type(e).__name__}: {e}); "
              "team files carry only the 2003-2020 vegas_win_totals", file=sys.stderr)
        return wintotals.display_frame(raw, wintotals.empty_display())


DRAFT_FILES = ("draft_picks.parquet", "draft_values.csv")


def _cached_draft(cache_dir) -> dict:
    """{"draft_picks", "draft_values"} (normalized picks, value array) from the cache only; both None,
    with a warning naming the missing file, when either is not cached."""
    missing = [f for f in DRAFT_FILES if not (cache_dir / f).exists()]
    if missing:
        print(f"warning: {', '.join(missing)} not cached; no draft surplus. Run `uv run fgs build` to fetch it.",
              file=sys.stderr)
        return {"draft_picks": None, "draft_values": None}
    return {
        "draft_picks": draft.normalize_picks(pl.read_parquet(cache_dir / DRAFT_FILES[0])),
        "draft_values": draft.value_table(pl.read_csv(cache_dir / DRAFT_FILES[1])),
    }


def cached_inputs(cache_dir=None) -> dict:
    """Optional derive() inputs read from the cache only (no network). None when not cached."""
    cache_dir = CACHE_DIR if cache_dir is None else cache_dir  # module global read at call time
    vegas = _cached_vegas(cache_dir)
    dr = _cached_draft(cache_dir)
    seasons = cached_seasons(cache_dir)
    if not seasons:
        return {"pbp_games": None, "vegas": vegas, **dr}
    return {"pbp_games": team_game_epa(load_all_pbp(seasons, cache_dir, write_cache=False)), "vegas": vegas, **dr}


SIM_CACHE_DIR = None  # None -> DERIVED_DIR / "sim"; the test suite points it at a session tmp dir


def sim_cache_dir():
    """Sim cache location (module globals read at call time so tests can monkeypatch them)."""
    return DERIVED_DIR / "sim" if SIM_CACHE_DIR is None else SIM_CACHE_DIR


def build_all(refresh: bool = False) -> dict[str, pl.DataFrame]:
    """Unchecked build (WR-03): downloads/caches inputs and writes derived parquet WITHOUT running
    the data-trust checks (`build --refresh` writes the re-downloaded current-season pbp straight
    to the cache). Use `fgs refresh` for the checked, check-then-write path."""
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
    picks = draft.normalize_picks(draft.load_draft_picks(refresh=refresh))
    values = draft.value_table(draft.load_draft_values())  # frozen file, downloaded once
    out = derive(raw, pbp_games=tge, vegas=vegas, sim_cache_dir=sim_cache_dir(), draft_picks=picks,
                 draft_values=values)
    _write_derived(out)
    print(
        f"built: raw {raw.height} rows, games {out['games'].height}, "
        f"team_games {out['team_games'].height}, elo_snapshots {out['snapshots'].height}"
    )
    print(f"pbp: {tge.height} team-games, seasons {seasons[0]}-{seasons[-1]}")
    if out.get("draft") is not None:
        d = out["draft"]
        print(f"draft: {picks.height} picks, surplus for drafts {d['season'].min()}-{d['season'].max()}")
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


def _cmd_draft(args) -> int:
    """Draft capital over original slots for one draft, ranked (fan sanity check)."""
    derived = derive(load_schedules(), scored=False, **cached_inputs(), sim_cache_dir=sim_cache_dir(),
                     sim_write_cache=False)
    tbl, values = derived.get("draft"), derived.get("draft_values")
    if tbl is None or values is None or tbl.is_empty():
        print("no draft data cached; run `uv run fgs build` first", file=sys.stderr)
        return 1
    lo_y, hi_y = int(tbl["season"].min()), int(tbl["season"].max())
    season = hi_y if args.season is None else args.season
    if not lo_y <= season <= hi_y:
        why = f"no {season - 1} standings" if season < lo_y else "no picks or prior-season standings"
        print(f"draft {season} not derivable ({why}); available drafts: {lo_y}-{hi_y}", file=sys.stderr)
        return 1
    bounds = draft_winsor(tbl)  # the frozen caps, so z matches the exported draft_z
    rows = (draft.draft_z(tbl, bounds).filter(pl.col("season") == season)
            .sort(["surplus", "franchise_id"], descending=[True, False]))
    print(f"{season} draft: capital over original slots (chart {draft.CHART}); "
          f"winsor caps [{bounds[0]:+.2f}, {bounds[1]:+.2f}]")
    print(f"{'#':>3}  {'Team':<4}  {'Slot':>4}  {'Surplus':>7}  {'Pick-equivalent':<24}  {'z':>5}")
    for rank, r in enumerate(rows.iter_rows(named=True), start=1):
        s = r["surplus"]
        # same thresholds as the site text (explain.draft_text)
        eq = ("—" if draft.is_even(s) else "more than #1 overall" if draft.beyond_top_pick(s, values)
              else draft.pick_noun(draft.equiv_pick(s, values)))
        stxt = "0.0" if abs(s) < 0.05 else f"{s:+.1f}"
        print(f"{rank:>3}  {r['franchise_id']:<4}  {r['slot']:>4}  {stxt:>7}  {eq:<24}  {r['draft_z']:>+5.2f}")
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
    incomplete = _incomplete_refresh_msg()
    # read-only (IN-01): reuse the sim cache but never rewrite it from a verification run
    ok, _, _ = _checked_derive(raw, **cached_inputs(), sim_cache_dir=sim_cache_dir(), sim_write_cache=False)
    if incomplete:
        _report("refresh_complete", [incomplete])
        return 1
    return 0 if ok else 1


REFRESH_MARKER = "refresh.incomplete"


def _refresh_marker(cache_dir=None):
    """Present while (or after a crash during) refresh's write sequence (WR-03)."""
    return (CACHE_DIR if cache_dir is None else cache_dir) / REFRESH_MARKER


def _incomplete_refresh_msg() -> str | None:
    m = _refresh_marker()
    if not m.exists():
        return None
    return (f"a previous `fgs refresh` was interrupted mid-write ({m} exists); caches may mix old and new "
            "inputs. Run `uv run fgs refresh` again to restore a consistent set.")


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


def _refresh_draft(cache_dir) -> tuple[pl.DataFrame | None, dict]:
    """Refresh's draft inputs: picks downloaded in memory (raw frame returned so it is saved only after
    the checks pass), falling back to the cached file with a warning; the frozen value chart is
    downloaded once if missing. Returns (raw picks to save or None, derive kwargs)."""
    raw_picks = None
    try:
        raw_picks = draft.load_draft_picks(refresh=True, cache_dir=cache_dir, write_cache=False)
    except Exception as e:  # noqa: BLE001 - network failure: fall back to the cache
        print(f"warning: draft picks download failed ({type(e).__name__}: {e}); using the cached file if any",
              file=sys.stderr)
    if not (cache_dir / DRAFT_FILES[1]).exists():
        try:
            draft.load_draft_values(cache_dir=cache_dir)
        except Exception as e:  # noqa: BLE001
            print(f"warning: draft_values.csv download failed ({type(e).__name__}: {e})", file=sys.stderr)
    if raw_picks is None:
        return None, _cached_draft(cache_dir)
    if not (cache_dir / DRAFT_FILES[1]).exists():
        print(f"warning: {DRAFT_FILES[1]} not cached; no draft surplus", file=sys.stderr)
        return raw_picks, {"draft_picks": None, "draft_values": None}
    return raw_picks, {"draft_picks": draft.normalize_picks(raw_picks),
                       "draft_values": draft.value_table(pl.read_csv(cache_dir / DRAFT_FILES[1]))}


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
    # Vegas comes from the cache (frozen file; downloaded only if missing). The sim cache is read
    # but only written after every check passes, so only changed seasons are re-simulated.
    vegas = _cached_vegas(cache_dir, download=True)
    raw_picks, draft_kw = _refresh_draft(cache_dir)
    sims = sim_cache_dir()
    ok, derived, _ = _checked_derive(raw, pbp_games=tge, vegas=vegas, sim_cache_dir=sims, sim_write_cache=False,
                                     **draft_kw)
    if not ok:
        print("checks failed; cache and JSON not updated", file=sys.stderr)
        return 1
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    files = export.build_export(derived, teams, generated_at=generated_at,
                                win_totals=_display_win_totals(cache_dir))  # pure; may still raise before writes
    # WR-03: the writes below are atomic per file, not as a set. The marker brackets them so a
    # crash/Ctrl-C mid-sequence is detected: `fgs export` refuses and `fgs check` fails until a
    # refresh completes, instead of publishing a mix of new and old inputs.
    marker = _refresh_marker(cache_dir)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(f"refresh started {generated_at}\n")
    save_cache(raw, "schedules.parquet", cache_dir)
    save_cache(teams, "teams.parquet", cache_dir)
    for s, df in sorted(fetched.items()):
        save_cache(df, f"{PBP_SUBDIR}/{s}.parquet", cache_dir)
    if raw_picks is not None:
        save_cache(raw_picks, DRAFT_FILES[0], cache_dir)
    _write_derived(derived)
    sim.save_sim_cache(derived["sim"], sims)
    export.write_export(files, WEB_DATA_DIR)
    marker.unlink()  # every output written: the set is consistent again
    # the hand-check is not part of the web data set, so it is written after the marker is gone
    # (a failure here cannot leave an "incomplete refresh" behind) (IN-04)
    check = _write_records_check(files)
    meta = files["meta.json"]
    print(
        f"refreshed in {time.perf_counter() - t0:.1f}s: exported {len(files)} files; latest {meta['latest']['season']} week "
        f"{meta['latest']['week']} (partial={meta['partial_week']}); data through {meta['data_through']}"
    )
    print(_records_check_msg(check))
    return 0


def _write_records_check(files: dict) -> tuple[object, bool]:
    """Write pipeline/RECORDS_CHECK.md from the exported records.json (path read at call time so
    tests can monkeypatch paths.RECORDS_CHECK_PATH). IN-06: skipped when the file already carries
    the same date-independent records key, so a new export date alone never rewrites it.
    Returns (path, written)."""
    path = paths.RECORDS_CHECK_PATH
    rec = files["records.json"]
    key_line = f"{records.KEY_PREFIX}{records.records_check_key(rec)} -->"
    if path.exists() and key_line in path.read_text(encoding="utf-8").splitlines():
        return path, False
    path.write_text(records.records_check_md(rec), encoding="utf-8")
    return path, True


def _records_check_msg(check: tuple[object, bool]) -> str:
    path, written = check
    return f"records hand-check written to {path}" if written else f"records hand-check unchanged ({path})"


def _cmd_export(args) -> int:
    incomplete = _incomplete_refresh_msg()
    if incomplete:
        print(f"error: {incomplete}", file=sys.stderr)
        return 1
    derived = derive(load_schedules(), **cached_inputs(), sim_cache_dir=sim_cache_dir())  # cache only (schedules download once if missing)
    teams = load_teams()
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    files = export.build_export(derived, teams, generated_at=generated_at,
                                win_totals=_display_win_totals(CACHE_DIR))  # CACHE_DIR read at call time
    out_dir = WEB_DATA_DIR  # module global read at call time so tests can monkeypatch it
    export.write_export(files, out_dir)
    check = _write_records_check(files)
    meta = files["meta.json"]
    print(
        f"exported {len(files)} files to {out_dir}; latest {meta['latest']['season']} "
        f"week {meta['latest']['week']} (partial={meta['partial_week']})"
    )
    print(_records_check_msg(check))
    return 0


def _cmd_evidence(args) -> int:
    """Dev-only: recompute the perception-gap base rates on 1999–2021 and write
    paths.CALLOUT_EVIDENCE_PATH (commit it). fgs.evidence imports the backtest, so it is loaded
    lazily here and never by the export."""
    from fgs import evidence, fingerprint, insights, mood

    incomplete = _incomplete_refresh_msg()
    if incomplete:
        print(f"error: {incomplete}", file=sys.stderr)
        return 1
    derived = derive(load_schedules(), **cached_inputs(), sim_cache_dir=sim_cache_dir())
    scored = mood.score_frame(derived["features"])
    fp = insights.weights_fingerprint(insights.fingerprint_weights(derived["weights"], derived["offseason"]))
    # WR-02: also stamp the Elo params, code version and 1999-2021 data hash the export re-checks
    fps = fingerprint.evidence_fingerprints(fp, scored, derived["team_games"])
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    ev = evidence.compute_evidence(scored, derived["team_games"], fps, generated_at)
    out = paths.CALLOUT_EVIDENCE_PATH  # read at call time so tests can monkeypatch it
    out.write_text(json.dumps(ev, indent=1, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    lo, hi = ev["train_seasons"]
    for f in ("hopeful", "worried"):
        e = ev[f]
        if not e["n"]:  # WR-03: an empty flavor ships no evidence line (insights.evidence_text)
            print(f"{f:8s} n=0  no cases ({lo}–{hi}, |gap| >= {ev['threshold']}); its callouts get no evidence line")
            continue
        print(f"{f:8s} n={e['n']}  d_margin={e['d_margin']:+.2f}  next-8 win {e['team_win']:.1%} vs peers "
              f"{e['peer_win']:.1%}  ({lo}–{hi}, |gap| >= {ev['threshold']}, weeks {ev['first_week']}+)")
    print(f"wrote {out} ({', '.join(f'{k} {v}' for k, v in fps.items())}); commit it")
    return 0


FROZEN_MSG = ("weights are frozen (fit 1999–2021); `fgs freeze --unfreeze` can refit only until the "
              "one-time holdout has been run")
PERMANENT_FROZEN_MSG = ("weights are permanently frozen for v1 (fit 1999–2021; the 2022–2025 holdout has been "
                        "evaluated). A new model version would need a new pre-registration and a fresh holdout")
POST_HOLDOUT_MSG = ("refitting after the holdout breaks the pre-registration (pipeline/PREREGISTRATION.md); "
                    "a new holdout would be needed")
SEALED_MSG = "the 2022–2025 holdout is sealed until the one-time `fgs holdout` result exists"


def _holdout_artifacts(include_derived: bool = True) -> list:
    """Existing one-time holdout result files. Either committed file (HOLDOUT_RESULT.md or .json)
    counts as "already evaluated", so a lost or failed .md write can't re-open the holdout (WR-01)."""
    cands = [paths.HOLDOUT_MD_PATH, paths.HOLDOUT_JSON_PATH]
    if include_derived:
        cands.append(DERIVED_DIR / "holdout.json")  # module global read at call time (tests monkeypatch it)
    return [p for p in cands if p.exists()]


def _write_atomic(pairs: list) -> None:
    """Write every (path, text) to a temp file first, then os.replace them all, so a failed render or
    write can't leave one result file without the other."""
    tmps = []
    try:
        for path, text in pairs:
            tmp = path.with_name(path.name + ".tmp")
            tmp.write_text(text)
            tmps.append((tmp, path))
    except BaseException:
        for tmp, _ in tmps:
            tmp.unlink(missing_ok=True)
        raise
    for tmp, path in tmps:
        os.replace(tmp, path)


def _weights_frozen() -> bool:
    """score.is_frozen() on paths.WEIGHTS_PATH; a missing/unreadable file is not frozen.
    A file that exists but can't be parsed is reported, so a guard's "not frozen" isn't misleading."""
    try:
        return score.is_frozen()
    except ValueError as e:
        if paths.WEIGHTS_PATH.exists():
            print(f"warning: {e}", file=sys.stderr)
        return False


DRAFT_HOLDOUT_MSG = "the draft term is training-only; the holdout was consumed by Phase 6"
DRAFT_UNFROZEN_MSG = "the draft term is fit on the frozen composite; run after the Phase 6 freeze"


def _cmd_backtest_draft(args) -> int:
    """`fgs backtest --draft`: the offseason draft term on top of the frozen composite, training
    seasons only (Phase 7). Prints the gate verdict; writes nothing."""
    if args.include_holdout:
        print(f"error: {DRAFT_HOLDOUT_MSG}", file=sys.stderr)
        return 1
    if not _weights_frozen():
        print(f"error: {DRAFT_UNFROZEN_MSG}", file=sys.stderr)
        return 1
    derived = derive(load_schedules(), scored=False, **cached_inputs(), sim_cache_dir=sim_cache_dir())
    if derived.get("draft") is None:
        print("error: draft cache missing; run `uv run fgs build`", file=sys.stderr)
        return 1
    res = draft_walk_forward(derived, score.load_weights())
    gate = draft_gate(res["fold_weights"], res["final"], res["delta_wk0"])
    print(format_draft_report(res, gate, datetime.now(timezone.utc).date().isoformat()))
    return 0


def _cmd_backtest(args) -> int:
    if getattr(args, "draft", False):
        return _cmd_backtest_draft(args)
    # Refusal guards run before any data load (Phase 6): no refit proposal once frozen, and no
    # look at 2022-2025 before the one-time holdout result exists.
    if args.propose_weights and _weights_frozen():
        msg = PERMANENT_FROZEN_MSG if _holdout_artifacts() else FROZEN_MSG
        print(f"error: {msg}", file=sys.stderr)
        return 1
    if args.include_holdout and not _holdout_artifacts(include_derived=False):
        print(f"error: {SEALED_MSG}", file=sys.stderr)
        return 1
    incomplete = _incomplete_refresh_msg()
    if incomplete:
        print(f"warning: {incomplete}", file=sys.stderr)
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


def _fmt_ci(ci) -> str:
    return "—" if not ci else f"[{ci[0]:+.4f}, {ci[1]:+.4f}]"


def _cmd_freeze(args) -> int:
    """Fit the final weights on 1999-2021 once and freeze weights.yaml + FREEZE_RESULT.json."""
    # Guards first, before any data load.
    if _holdout_artifacts():
        print(f"error: {POST_HOLDOUT_MSG}", file=sys.stderr)
        return 1
    if _weights_frozen() and not args.unfreeze:
        print(f"error: {FROZEN_MSG}", file=sys.stderr)
        return 1
    derived = derive(load_schedules(), scored=False, **cached_inputs(), sim_cache_dir=sim_cache_dir())
    log_path = paths.PIPELINE_ROOT / "BACKTEST_LOG.md"
    log_text = log_path.read_text() if log_path.exists() else None
    result = freeze.build_freeze(derived, log_text=log_text)
    text = freeze.render_weights_yaml(result)
    body = json.dumps(result, allow_nan=False, indent=1) + "\n"
    paths.WEIGHTS_PATH.write_text(text)
    paths.FREEZE_RESULT_PATH.write_text(body)

    print(f"froze {len(result['factors'])} weights (fit {result['fit_seasons'][0]}–{result['fit_seasons'][1]}, "
          f"alpha {result['alpha']:g}*n, n {result['n']}) on {result['fitted_at']}")
    print(f"{'factor':<14}{'weight':>8}{'sign':>6}{'folds':>8}{'ΔSp N8':>10}")
    for f, d in result["factors"].items():
        delta = d.get("delta_spearman_n8")
        dtxt = f"{delta:+.4f}" if delta is not None else f"({d.get('baseline_spearman_n8') or 0:.4f})"
        print(f"{f:<14}{freeze.format_weight(d['weight']):>8}{d['sign']:>6}"
              f"{d['fold_sign'][0]:>5}/{d['fold_sign'][1]:<2}{dtxt:>10}")
    wf = result.get("walk_forward") or {}
    sp = wf.get("spearman_n8") or {}
    diff = (wf.get("diff") or {}).get("spearman_n8") or {}
    if sp:
        print(f"\nwalk-forward {wf['seasons'][0]}–{wf['seasons'][1]} Spearman N=8: composite "
              f"{sp['composite']['value']:.4f}, elo {sp['elo']['value']:.4f}")
    if diff:
        print(f"composite − elo {diff['value']:+.4f}; season-block CI {_fmt_ci(diff.get('ci_season'))}, "
              f"team-season CI {_fmt_ci(diff.get('ci_cluster'))}; won {diff.get('seasons_won')}/{diff.get('of')} seasons")
    for w in (result.get("log_crosscheck") or {}).get("warnings", []):
        print(f"warning (BACKTEST_LOG cross-check): {w}", file=sys.stderr)
    print(f"\nwrote {paths.WEIGHTS_PATH}\nwrote {paths.FREEZE_RESULT_PATH}")
    return 0


ALREADY_HOLDOUT_MSG = ("the holdout was already evaluated once (pipeline/HOLDOUT_RESULT.md/.json); re-running it breaks "
                       "the pre-registration. --force exists but don't.")


def _cmd_holdout(args) -> int:
    """ONE-TIME: evaluate the frozen weights on the sealed 2022-2025 holdout (PREREGISTRATION.md).
    Every guard runs before any data load."""
    existing = _holdout_artifacts()
    if existing and not args.force:
        print(f"error: {ALREADY_HOLDOUT_MSG} ({', '.join(map(str, existing))})", file=sys.stderr)
        return 1
    if not _weights_frozen():
        print("error: weights.yaml is not frozen; run `fgs freeze` first", file=sys.stderr)
        return 1
    if not paths.PREREG_PATH.exists():
        print("error: pipeline/PREREGISTRATION.md is missing", file=sys.stderr)
        return 1
    gs = holdout.git_state(paths.PIPELINE_ROOT)
    if not gs["available"]:
        print("warning: git is not available; commit state of PREREGISTRATION.md / weights.yaml not verified",
              file=sys.stderr)
    else:
        if gs["dirty"]:
            print("error: PREREGISTRATION.md and weights.yaml must be committed and unmodified: "
                  + "; ".join(gs["dirty"]), file=sys.stderr)
            return 1
        if not gs["ordered"]:
            print("error: PREREGISTRATION.md must be committed before the frozen weights.yaml "
                  "(its adding commit must be an ancestor of the latest weights.yaml commit; otherwise the pre-registration "
                  "does not precede the freeze)", file=sys.stderr)
            return 1
        if not gs.get("prereg_unchanged"):
            print("error: PREREGISTRATION.md changed after the commit that added it (more than one commit touches it, "
                  "or its sha256 differs from the adding commit's content); the pre-registration must be the "
                  "original text", file=sys.stderr)
            return 1
        if gs.get("src_dirty"):
            print("error: pipeline/src has uncommitted changes; the evaluated code must be committed: "
                  + "; ".join(gs["src_dirty"]), file=sys.stderr)
            return 1

    weights = score.load_weights()
    doc = score.load_weights_doc()
    # Re-derive from the cache with the frozen weights; never read features.parquet (Pitfall 8).
    derived = derive(load_schedules(), **cached_inputs(), sim_cache_dir=sim_cache_dir())
    result = holdout.evaluate_frozen(derived, weights, HOLDOUT_SEASONS, TRAIN_LAST_SEASON,
                                     weights_doc=doc, allow_holdout=True)

    # Any previous result is recorded in reruns (only reachable with --force, given the guard above).
    prev = None
    for p in (paths.HOLDOUT_JSON_PATH, DERIVED_DIR / "holdout.json"):
        if p.exists():
            prev = json.loads(p.read_text())
            break
    if prev is None and paths.HOLDOUT_MD_PATH.exists():
        prev = {"evaluated_at": None, "verdict": None}  # only the .md survived; still a rerun
    result["evaluated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    result["provenance"] = {
        "weights_sha256": holdout.file_sha256(paths.WEIGHTS_PATH),
        "prereg_sha256": holdout.file_sha256(paths.PREREG_PATH),
        "git_head": gs.get("head"),
        "prereg_commit": gs.get("prereg_commit"),
        "prereg_last_commit": gs.get("prereg_last_commit"),
        "prereg_unchanged": gs.get("prereg_unchanged") if gs["available"] else None,
        "weights_commit": gs.get("weights_commit"),
        "src_clean": (not gs.get("src_dirty")) if gs["available"] else None,
        # WR-08: input data + dependency lock, so the result can be checked against the exact bytes
        "inputs": holdout.input_fingerprints(CACHE_DIR, sim_cache_dir(), paths.PIPELINE_ROOT / "uv.lock"),
    }
    result["rerun"] = prev is not None
    result["reruns"] = ([*(prev.get("reruns") or []),
                         {"evaluated_at": prev.get("evaluated_at"), "verdict": prev.get("verdict")}]
                        if prev is not None else [])

    body = json.dumps(result, allow_nan=False, indent=1) + "\n"
    md = holdout.render_markdown(result)  # render before writing anything
    out_dir = DERIVED_DIR  # module global read at call time so tests can monkeypatch it
    out_dir.mkdir(parents=True, exist_ok=True)
    derived_path = out_dir / "holdout.json"
    _write_atomic([(paths.HOLDOUT_JSON_PATH, body), (paths.HOLDOUT_MD_PATH, md), (derived_path, body)])

    d = result["diff"]["spearman_n8"]
    sp = result["spearman_n8"]
    lo, hi = result["seasons"]
    print(f"holdout {lo}–{hi} (frozen weights; evaluated {result['evaluated_at']})")
    print(f"Verdict: {result['verdict']} — {result['headline']}")
    print(f"BACK-06: {'PASS' if result['pass'] else 'FAIL'} (score − Elo Spearman N=8 > 0)")
    print(f"Spearman N=8: composite {holdout._f(sp['composite']['value'])}, elo {holdout._f(sp['elo']['value'])}")
    print(f"composite − elo {holdout._sg(d['value'])}; season-block CI {_fmt_ci(d.get('ci_season'))}, "
          f"team-season CI {_fmt_ci(d.get('ci_cluster'))}; won {d.get('seasons_won')}/{d.get('of')} seasons")
    print(f"\nwrote {paths.HOLDOUT_JSON_PATH}\nwrote {paths.HOLDOUT_MD_PATH}\nwrote {derived_path}")
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


def _cmd_logos(args) -> int:
    """One-shot (LOGO-01): download the 32 ESPN logos into paths.LOGOS_DIR; commit them. Not run by refresh."""
    urls: list[str] = []

    def fetch(url: str) -> bytes:
        urls.append(url)
        return logos._http_get(url)  # module attribute read at call time

    manifest = logos.fetch_logos(out_dir=paths.LOGOS_DIR, force=args.force, fetch=fetch)
    total = sum(m["bytes"] for m in manifest.values())
    print(f"logos: {len(urls)} fetched, {len(manifest) - len(urls)} skipped; {len(manifest)} in "
          f"{paths.LOGOS_DIR} ({total / 1e6:.2f} MB)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fgs", description="Feel-good score pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ingest", help="download nflverse schedules into the local cache")
    p.add_argument("--refresh", action="store_true",
                   help="re-download the schedules file even if cached (schedules only; `fgs refresh` "
                        "re-downloads pbp, teams and draft too)")
    p.add_argument("--all", action="store_true", help="same as --refresh (schedules are the only file ingest touches)")
    p.set_defaults(func=_cmd_ingest)

    p = sub.add_parser("build", help="ingest (cached) schedules + pbp, derive games, team_games, elo_snapshots, "
                                     "team_game_epa (unchecked; use `refresh` for the checked path)")
    p.add_argument("--refresh", action="store_true",
                   help="re-download schedules and the current season's pbp first")
    p.set_defaults(func=_cmd_build)

    p = sub.add_parser("elo", help="ranked Elo table as of a (season, week); default = latest played week")
    p.add_argument("--season", type=int, default=None, help="default: latest season in the data")
    p.add_argument("--week", type=int, default=None, help="default: latest played week of the season")
    p.add_argument("--top", type=int, default=None, help="show only the top N teams")
    p.set_defaults(func=_cmd_elo)

    p = sub.add_parser("draft", help="draft capital over original slots for one draft (from the cache)")
    p.add_argument("--season", type=int, default=None, help="draft year; default: latest derivable draft")
    p.set_defaults(func=_cmd_draft)

    p = sub.add_parser("check", help="run all data-trust checks; exit 1 on any failure")
    p.set_defaults(func=_cmd_check)

    p = sub.add_parser("export", help="write the site JSON contract to web/public/data from cached data; no network")
    p.set_defaults(func=_cmd_export)

    p = sub.add_parser("refresh", help="re-download nflverse data, run all checks, then regenerate derived "
                                       "parquet and the site JSON (writes nothing if a check fails)")
    p.set_defaults(func=_cmd_refresh)

    p = sub.add_parser("backtest", help="walk-forward backtest vs baselines; writes data/derived/backtest.json")
    p.add_argument("--include-holdout", action="store_true",
                   help="also test 2022–2025; refused until the one-time `fgs holdout` result (HOLDOUT_RESULT.md) exists")
    p.add_argument("--propose-weights", action="store_true",
                   help="also print ridge weights fit on 1999–2021 (N=8) as a weights.yaml block; "
                        "refused once weights.yaml is frozen (v1 weights are permanently frozen)")
    p.add_argument("--draft", action="store_true",
                   help="fit the offseason draft term on top of the frozen composite; training seasons only")
    p.set_defaults(func=_cmd_backtest)

    p = sub.add_parser("freeze", help="fit the final weights on 1999–2021 and freeze weights.yaml "
                                      "(refuses once frozen or after the holdout)")
    p.add_argument("--unfreeze", action="store_true",
                   help="refit even though weights.yaml is frozen (still refused once HOLDOUT_RESULT.md exists)")
    p.set_defaults(func=_cmd_freeze)

    p = sub.add_parser("holdout", help="ONE-TIME: evaluate the frozen weights on the sealed 2022–2025 holdout "
                                       "(refuses if already done)")
    p.add_argument("--force", action="store_true",
                   help="re-run even though a result exists — don't: it breaks the pre-registration")
    p.set_defaults(func=_cmd_holdout)

    p = sub.add_parser("evidence", help="dev-only: recompute the perception-gap base rates on 1999–2021 and write "
                                        "pipeline/callout_evidence.json; commit it")
    p.set_defaults(func=_cmd_evidence)

    p = sub.add_parser("logos", help="one-shot: download the 32 ESPN team logos into web/public/logos (commit them); "
                                     "not part of refresh")
    p.add_argument("--force", action="store_true", help="re-download logos that already exist")
    p.set_defaults(func=_cmd_logos)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

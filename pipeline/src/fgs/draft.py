"""Draft capital over slot (DATA-06, MODEL-16).

surplus(team, draft) = chart value of the regular picks the team actually used
                     - chart value of the regular picks its ORIGINAL slots would have given it.

The original slots come from the prior season's standings (playoff stage, then win %, then SOS;
tied teams rotate each round; expansion teams first). Forfeited slots come ONLY from the explicit
FORFEITS table. The remaining slots are aligned to the actual picks with an edit-distance DP whose
deletion cost exceeds any substitutions it could save, so it never invents a forfeit: substitutions
are trades, the occasional mid-round extra pick is an insertion, and trailing extras in rounds 3-7
are compensatory picks (excluded from both sides). A round with fewer picks than slots forces a
deletion; that slot is left unpaired and nobody is charged (with a warning unless the round is in
UNATTRIBUTED_SHORT). The earlier DP (deletion cost 3) invented forfeits in heavily traded rounds,
charging the wrong teams (e.g. 2008 R5 KC/LV instead of SF).

So surplus measures capital gained or lost by TRADES (including picks spent on veterans), not draft
position: a team that kept its own #1 pick has surplus exactly 0, and tanking is never rewarded.
It is not a verdict on draft quality; text must say "over/under their original slots".

Chart: nflverse draft_values.csv `stuart` (AV-based). `otc` was checked: surplus from the two
correlates at 0.98, and stuart is closer to slot-neutral (Spearman with slot -0.06 vs -0.09).

Pure apart from the two loaders. Must never import the backtest harness (leakage firewall), and
reads no outcomes: only picks and the prior season's standings.
"""

import os
import urllib.request
import warnings
from pathlib import Path

import numpy as np
import polars as pl

from fgs.franchises import CANONICAL
from fgs.ingest import nflreadpy_uncached, save_cache
from fgs.paths import CACHE_DIR

PFR_TO_FRANCHISE: dict[str, str] = {
    "GNB": "GB", "KAN": "KC", "LVR": "LV", "OAK": "LV", "SDG": "LAC", "LAR": "LA", "STL": "LA",
    "NOR": "NO", "NWE": "NE", "SFO": "SF", "TAM": "TB",
}
CHART = "stuart"
FIRST_DRAFT = 2000  # the 1999 draft needs 1998 standings, which the schedules don't have
MAX_PICK = 262
DECAY_WEEKS = 4
N_ROUNDS = 7
DRAFT_VALUES_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/draft_values.csv"

STAGE = {"WC": 1, "DIV": 2, "CON": 3, "SB": 4}  # last playoff game; won SB -> 5; no playoffs -> 0
SB_WINNER = 5
EXPANSION_FIRST: dict[int, str] = {2002: "HOU"}  # (CLE 1999 too, but 1999 isn't derivable)
# (draft year, round) -> original slot owners whose pick was stripped by the league (tampering,
# cap/integrity penalties, and the next-year pick spent in a supplemental draft). Each entry was
# checked against the pick data (short round, or the slot shift it causes).
FORFEITS: dict[tuple[int, int], list[str]] = {
    (2001, 5): ["SF"],                          # cap violations
    (2004, 2): ["LV"],
    (2006, 5): ["MIA"],                         # 2005 supplemental (M. Wright)
    (2007, 3): ["CIN"],                         # 2006 supplemental (A. Brooks)
    (2008, 1): ["NE"],                          # videotaping
    (2008, 4): ["LAC"],                         # 2007 supplemental (P. Oliver)
    (2008, 5): ["SF"],                          # tampering
    (2010, 3): ["WAS"],                         # 2009 supplemental (J. Jarmon)
    (2011, 7): ["CHI"],                         # 2010 supplemental (H. Unga)
    (2012, 2): ["NO"],                          # bounty
    (2012, 3): ["LV"],                          # 2011 supplemental (T. Pryor)
    (2013, 2): ["NO", "CLE"],                   # bounty; 2012 supplemental (J. Gordon)
    (2016, 1): ["NE"],                          # ball deflation
    (2016, 3): ["KC"],                          # tampering
    (2016, 5): ["ATL", "LA"],                   # crowd noise; 2015 supplemental (I. Battle)
    (2017, 4): ["NE"],                          # ball deflation
    (2017, 6): ["KC"],                          # tampering
    (2019, 3): ["NYG"],                         # 2018 supplemental (S. Beal)
    (2019, 6): ["WAS"],                         # 2018 supplemental (A. Alexander)
    (2020, 5): ["ARI"],                         # 2019 supplemental (J. Thompson)
    (2021, 3): ["NE"],                          # videotaping
    (2023, 1): ["MIA"],                         # tampering
    (2024, 3): ["MIA"],                         # tampering
    (2025, 5): ["ATL", "SF"],                   # tampering; payroll accounting
}
# Rounds known to be one regular pick short whose owner we can't attribute: nobody is charged.
UNATTRIBUTED_SHORT: set[tuple[int, int]] = {(2021, 7)}
STD_EPS = 1e-12

SURPLUS_SCHEMA = {
    "season": pl.Int32, "franchise_id": pl.String, "slot": pl.Int32,
    "orig_value": pl.Float64, "used_value": pl.Float64, "surplus": pl.Float64,
}


# ---------- codes + loaders ----------

def map_pfr(code: str) -> str:
    f = PFR_TO_FRANCHISE.get(code, code)
    if f not in CANONICAL:
        raise ValueError(f"unknown PFR team code: {code!r}")
    return f


def load_draft_picks(refresh: bool = False, cache_dir: Path = CACHE_DIR, write_cache: bool = True) -> pl.DataFrame:
    """Raw nflreadpy draft picks (every draft), cached as draft_picks.parquet."""
    path = Path(cache_dir) / "draft_picks.parquet"
    if path.exists() and not refresh:
        return pl.read_parquet(path)

    import nflreadpy

    with nflreadpy_uncached():
        df = nflreadpy.load_draft_picks()
    if write_cache:
        save_cache(df, "draft_picks.parquet", cache_dir)
    return df


def load_draft_values(refresh: bool = False, cache_dir: Path = CACHE_DIR) -> pl.DataFrame:
    """nflverse draft_values.csv (pick, stuart, johnson, hill, otc, pff). Frozen file: downloaded
    once into the cache and only re-fetched with refresh=True."""
    path = Path(cache_dir) / "draft_values.csv"
    if refresh or not path.exists():
        with urllib.request.urlopen(DRAFT_VALUES_URL, timeout=30) as r:
            data = r.read()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)
    return pl.read_csv(path)


def normalize_picks(raw: pl.DataFrame) -> pl.DataFrame:
    """season/round/pick (Int32) + franchise_id for drafts since 1999, sorted by (season, pick).
    Raises on an unknown PFR code or a pick beyond the value chart."""
    df = raw.filter(pl.col("season") >= 1999)
    mapping = {c: map_pfr(c) for c in df["team"].unique().to_list()}  # raises on unknown codes
    out = df.select(
        pl.col("season").cast(pl.Int32), pl.col("round").cast(pl.Int32), pl.col("pick").cast(pl.Int32),
        pl.col("team").replace_strict(mapping, return_dtype=pl.String).alias("franchise_id"),
    ).sort("season", "pick")
    if out.height and int(out["pick"].max()) > MAX_PICK:
        raise ValueError(f"draft pick {int(out['pick'].max())} beyond the value chart ({MAX_PICK})")
    return out


def value_table(values_df: pl.DataFrame, chart: str = CHART) -> np.ndarray:
    """Array indexed by overall pick (length MAX_PICK + 1, [0] = nan)."""
    picks = values_df["pick"].to_list()
    missing = set(range(1, MAX_PICK + 1)) - set(picks)
    if missing:
        raise ValueError(f"draft value chart is missing picks {sorted(missing)[:5]}...")
    v = np.full(MAX_PICK + 1, np.nan)
    for p, x in zip(picks, values_df[chart].to_list()):
        if 1 <= p <= MAX_PICK:
            v[p] = float(x)
    return v


# ---------- original order ----------

def standings(team_games: pl.DataFrame, season: int) -> pl.DataFrame:
    """REG win % (ties .5), SOS (mean opponents' REG win % over REG games), playoff stage group."""
    s = team_games.filter((pl.col("season") == season) & pl.col("played"))
    reg = s.filter(pl.col("is_reg"))
    wp = reg.group_by("franchise_id").agg(pl.col("outcome").mean().alias("wp"))
    sos = (
        reg.join(wp.rename({"franchise_id": "opponent_id", "wp": "owp"}), on="opponent_id")
        .group_by("franchise_id").agg(pl.col("owp").mean().alias("sos"))
    )
    po = s.filter(~pl.col("is_reg")).with_columns(
        pl.col("game_type").replace_strict(STAGE, return_dtype=pl.Int32).alias("stg")
    )
    last = (
        po.sort("week").group_by("franchise_id")
        .agg(pl.col("stg").last(), pl.col("outcome").last().alias("o"))
        .with_columns(
            pl.when((pl.col("stg") == STAGE["SB"]) & (pl.col("o") == 1.0)).then(SB_WINNER)
            .otherwise(pl.col("stg")).cast(pl.Int32).alias("grp")
        )
    )
    return (
        wp.join(sos, on="franchise_id", how="left")
        .join(last.select("franchise_id", "grp"), on="franchise_id", how="left")
        .select("franchise_id", pl.col("grp").fill_null(0).cast(pl.Int32), "wp", "sos")
        .sort("franchise_id")
    )


def original_order(team_games: pl.DataFrame, draft_year: int, n_rounds: int = N_ROUNDS) -> list[list[str]]:
    """Franchise ids per round in original slot order (before trades and forfeits)."""
    st = standings(team_games, draft_year - 1).sort(["grp", "wp", "sos", "franchise_id"])
    base = st["franchise_id"].to_list()
    keys = list(zip(st["grp"].to_list(), st["wp"].to_list()))
    groups: list[tuple[list[str], bool]] = []  # (teams, rotates)
    i = 0
    while i < len(base):
        j = i
        while j < len(base) and keys[j] == keys[i]:
            j += 1
        groups.append((base[i:j], keys[i][0] < STAGE["SB"]))
        i = j
    exp = EXPANSION_FIRST.get(draft_year)
    rounds = []
    for r in range(n_rounds):
        order = [exp] if exp else []
        for grp, rot in groups:
            if rot and len(grp) > 1:
                k = r % len(grp)
                grp = grp[k:] + grp[:k]
            order += grp
        rounds.append(order)
    return rounds


# ---------- alignment ----------

def align(orig, actual, sub: float = 1.0, dele: float | None = None, ins: float = 4.0,
          free_tail: bool = True) -> list[tuple[int | None, int | None]]:
    """Edit-distance alignment of original slots to actual pick positions.

    match 0 / substitute (trade) `sub` / delete slot `dele` / insert extra pick `ins`; with
    free_tail, extra picks after the last slot (comp picks) cost nothing. `dele` defaults to more
    than every substitution in the round could cost, so a deletion happens only when the round is
    genuinely short of picks (trades are always preferred over a guessed forfeit). Returns
    (slot index or None, position or None) pairs in order; ties prefer match/sub, then delete."""
    n, k = len(orig), len(actual)
    if dele is None:
        dele = sub * (n + k) + ins + 1.0
    inf = float("inf")
    D = [[inf] * (k + 1) for _ in range(n + 1)]
    D[0][0] = 0.0

    def ins_cost(i):
        return 0.0 if (free_tail and i == n) else ins

    for i in range(n + 1):
        for j in range(k + 1):
            if i == 0 and j == 0:
                continue
            best = inf
            if i > 0 and j > 0:
                best = D[i - 1][j - 1] + (0.0 if orig[i - 1] == actual[j - 1] else sub)
            if i > 0:
                best = min(best, D[i - 1][j] + dele)
            if j > 0:
                best = min(best, D[i][j - 1] + ins_cost(i))
            D[i][j] = best
    i, j, path = n, k, []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and D[i][j] == D[i - 1][j - 1] + (0.0 if orig[i - 1] == actual[j - 1] else sub):
            path.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i > 0 and D[i][j] == D[i - 1][j] + dele:
            path.append((i - 1, None))
            i -= 1
        else:
            path.append((None, j - 1))
            j -= 1
    return path[::-1]


# ---------- surplus ----------

def _v(values: np.ndarray, p: int) -> float:
    return float(values[min(max(int(p), 1), MAX_PICK)])


def derivable_years(team_games: pl.DataFrame, picks: pl.DataFrame) -> list[int]:
    """Drafts present in `picks`, from FIRST_DRAFT on, whose prior season has played REG games."""
    reg = team_games.filter(pl.col("is_reg") & pl.col("played"))
    have = set(reg["season"].unique().to_list())
    return sorted(y for y in set(picks["season"].unique().to_list()) if y >= FIRST_DRAFT and y - 1 in have)


def surplus_table(team_games: pl.DataFrame, picks: pl.DataFrame, values: np.ndarray,
                  forfeits: dict[tuple[int, int], list[str]] | None = None,
                  unattributed: set[tuple[int, int]] | None = None) -> pl.DataFrame:
    """One row per franchise per derivable draft: slot (1-based round-1 original position),
    orig_value, used_value and surplus = used - orig. `picks` = normalize_picks output.
    Warns on a round with fewer picks than (non-forfeited) slots that isn't in `unattributed`."""
    forfeits = FORFEITS if forfeits is None else forfeits
    unattributed = UNATTRIBUTED_SHORT if unattributed is None else unattributed
    if picks.height and int(picks["pick"].max()) > MAX_PICK:
        raise ValueError(f"draft pick {int(picks['pick'].max())} beyond the value chart ({MAX_PICK})")
    by_year = {k[0]: g for k, g in picks.partition_by("season", as_dict=True).items()} if picks.height else {}
    rows = []
    for y in derivable_years(team_games, picks):
        dy = by_year[y]
        order = original_order(team_games, y)
        teams = order[0]
        orig_v = {t: 0.0 for t in teams}
        used_v = {t: 0.0 for t in teams}
        for r in range(1, N_ROUNDS + 1):
            pr = dy.filter(pl.col("round") == r).sort("pick")
            act = pr["franchise_id"].to_list()
            pk = pr["pick"].to_list()
            if not pk:
                continue
            gone = forfeits.get((y, r), [])
            for t in gone:  # stripped slot: its owner loses the pick it would have been, nobody gains it
                orig_v[t] += _v(values, pk[0] + order[r - 1].index(t))
            o = [t for t in order[r - 1] if t not in gone]
            if len(act) < len(o) and (y, r) not in unattributed:
                warnings.warn(f"draft {y} round {r}: {len(act)} picks for {len(o)} slots "
                              "(unknown forfeit; add it to draft.FORFEITS)", stacklevel=2)
            for si, pj in align(o, act, free_tail=r >= 3):
                if si is not None and pj is not None:  # regular pick (own or traded)
                    v = _v(values, pk[pj])
                    orig_v[o[si]] += v
                    used_v[act[pj]] = used_v.get(act[pj], 0.0) + v
                # slot without a pick (short round): unattributed, nobody charged;
                # pick without a slot: comp/extra pick, excluded from both sides
        for t in teams:
            rows.append((y, t, teams.index(t) + 1, orig_v[t], used_v[t], used_v[t] - orig_v[t]))
    return pl.DataFrame(rows, schema=SURPLUS_SCHEMA, orient="row").sort("season", "franchise_id")


def winsor_bounds(surplus: pl.DataFrame, seasons: tuple[int, int] = (2000, 2021),
                  q: tuple[float, float] = (0.05, 0.95)) -> tuple[float, float]:
    s = surplus.filter(pl.col("season").is_between(*seasons))["surplus"].to_numpy()
    lo, hi = np.percentile(s, [100 * q[0], 100 * q[1]])
    return round(float(lo), 2), round(float(hi), 2)


def draft_z(surplus: pl.DataFrame, winsor: tuple[float, float]) -> pl.DataFrame:
    """Clip surplus to the (frozen) winsor bounds, then z within each draft (ddof=0; 0.0 when constant)."""
    c = pl.col("surplus").clip(winsor[0], winsor[1])
    sd = c.std(ddof=0).over("season")
    return surplus.with_columns(
        pl.when(sd > STD_EPS).then((c - c.mean().over("season")) / sd).otherwise(0.0)
        .cast(pl.Float64).alias("draft_z")
    )


def decay(week: int, weeks: int = DECAY_WEEKS) -> float:
    return max(0.0, 1.0 - week / weeks)


def equiv_pick(amount: float, values: np.ndarray) -> int:
    """Smallest overall pick whose chart value is <= |amount| (MAX_PICK when none)."""
    a = abs(amount)
    for p in range(1, MAX_PICK + 1):
        if values[p] <= a:
            return p
    return MAX_PICK


def pick_noun(p: int) -> str:
    if p == 1:
        return "#1 overall pick"
    if p <= 5:
        return "top-5 pick"
    if p <= 15:
        return "early first-round pick"
    if p <= 24:
        return "mid-first-round pick"
    if p <= 32:
        return "late first-round pick"
    if p <= 64:
        return "second-round pick"
    return "later-round pick"

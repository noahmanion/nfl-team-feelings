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
# (draft year, round) -> ORIGINAL slot owners whose pick was stripped by the league (tampering,
# cap/integrity penalties, and the next-year pick spent in a supplemental draft). Audited in Phase 11
# against .planning/phases/11-pipeline-data-guards/sources/forfeit_audit.json; each team-line carries
# its reason and citations. FORFEIT_KIND labels each line penalty vs supplemental.
FORFEITS: dict[tuple[int, int], list[str]] = {
    # 2001 R5 SF (penalty): salary cap violations (Druckenmiller et al.)
    #   https://www.espn.com/blog/nflnation/post/_/id/55927/history-on-lost-draft-picks
    #   https://www.quirkyresearch.com/2020/04/22/draft-pick-forfeitures-and-penalties/
    (2001, 5): ["SF"],
    # 2003 R6 HOU (supplemental): 2002 supplemental pick (Milford Brown) [added]
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2003_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2002_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    (2003, 6): ["HOU"],
    # 2004 R2 LV (supplemental): OAK pick traded to HOU; HOU used on T. Hollings [relabeled]
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2004_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://houstontexans.com/news/texans-snag-hollings-in-supplemental-draft-2682942
    (2004, 2): ["LV"],
    # 2006 R5 MIA (supplemental): 2005 supplemental pick (Manuel Wright)
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2006_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.patriots.com/news/wright-taken-by-dolphins-in-supplemental-draft-91381
    (2006, 5): ["MIA"],
    # 2007 R3 CIN (supplemental): 2006 supplemental pick (Ahmad Brooks)
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2007_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://web.archive.org/web/20120425112940/http://virginiasports.cstv.com/sports/m-footbl/spec-rel/071306aaa.html
    (2007, 3): ["CIN"],
    # 2008 R1 NE (penalty): Spygate videotaping penalty
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2008_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.espn.com/blog/nflnation/post/_/id/55927/history-on-lost-draft-picks
    (2008, 1): ["NE"],
    # 2008 R4 LAC (supplemental): 2007 supplemental pick (Paul Oliver)
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2008_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.nfl.com/news/chargers-pick-oliver-ravens-select-gaither-in-supplemental-draf-09000d5d80013317
    (2008, 4): ["LAC"],
    # 2008 R5 SF (penalty): tampering with Lance Briggs
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2008_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.espn.com/blog/nflnation/post/_/id/55927/history-on-lost-draft-picks
    # 2008 R5 BAL (supplemental): 2007 supplemental pick (Jared Gaither) [added]
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2008_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.baltimoreravens.com/news/2008-ravens-draft-release-7745333
    #   https://www.patriots.com/news/oliver-gaither-selected-in-supplemental-draft-100831
    (2008, 5): ["SF", "BAL"],
    # 2010 R3 WAS (supplemental): 2009 supplemental pick (Jeremy Jarmon)
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2009_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://web.archive.org/web/20090918155833/http://www.sportingnews.com/nfl/article/2009-07-16/redskins-select-jarmon-nfl-supplemental-draft
    (2010, 3): ["WAS"],
    # 2011 R7 CHI (supplemental): 2010 supplemental pick (Harvey Unga)
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2011_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://web.archive.org/web/20110909011212/http://www.nationalfootballpost.com/2010-supplemental-draft-breakdown.html
    # 2011 R7 DAL (supplemental): 2010 supplemental pick (Josh Brent) [added]
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2011_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://web.archive.org/web/20110909011212/http://www.nationalfootballpost.com/2010-supplemental-draft-breakdown.html
    (2011, 7): ["CHI", "DAL"],
    # 2012 R2 NO (penalty): Bountygate penalty
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2012_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.nfl.com/news/nfl-bans-saints-payton-a-year-for-bounties-williams-out-too-09000d5d827c0dd9
    (2012, 2): ["NO"],
    # 2012 R3 LV (supplemental): 2011 supplemental pick (Terrelle Pryor)
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2012_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.nfl.com/news/raiders-select-pryor-in-third-round-of-nfl-supplemental-draft-09000d5d821a49b2
    (2012, 3): ["LV"],
    # 2012 R6 DET (penalty): tampering with Chiefs players [added]
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2012_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.quirkyresearch.com/2020/04/22/draft-pick-forfeitures-and-penalties/
    (2012, 6): ["DET"],
    # 2013 R2 NO (penalty): Bountygate penalty (second year)
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2013_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.nfl.com/news/nfl-bans-saints-payton-a-year-for-bounties-williams-out-too-09000d5d827c0dd9
    # 2013 R2 CLE (supplemental): 2012 supplemental pick (Josh Gordon)
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2013_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.nfl.com/news/josh-gordon-drafted-by-cleveland-browns-in-round-2-09000d5d82a808c0
    (2013, 2): ["NO", "CLE"],
    # 2016 R1 NE (penalty): Deflategate penalty
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2016_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.quirkyresearch.com/2020/04/22/draft-pick-forfeitures-and-penalties/
    (2016, 1): ["NE"],
    # 2016 R3 KC (penalty): tampering (Jeremy Maclin)
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2016_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.si.com/nfl/2016/03/09/kansas-city-chiefs-nfl-tampering-forfeit-two-draft-picks
    (2016, 3): ["KC"],
    # 2016 R5 ATL (penalty): piped artificial crowd noise
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2016_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.espn.com/nfl/story/_/id/12586639/nfl-expected-take-draft-pick-atlanta-falcons-suspend-team-president-rich-mckay-competition-committee
    # 2016 R5 LA (supplemental): 2015 supplemental pick (Isaiah Battle)
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2016_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.espn.com/nfl/story/_/id/13228050/st-louis-rams-pick-isaiah-battle-supplemental-draft
    (2016, 5): ["ATL", "LA"],
    # 2017 R4 NO (penalty): Deflategate; forfeited R4 was NO-original [corrected from NE: NE held this NO-original pick via the Brandin Cooks trade]
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2017_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.quirkyresearch.com/2020/04/22/draft-pick-forfeitures-and-penalties/
    (2017, 4): ["NO"],
    # 2017 R5 SEA (penalty): OTA no-live-contact violation [added]
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2017_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.quirkyresearch.com/2020/04/22/draft-pick-forfeitures-and-penalties/
    (2017, 5): ["SEA"],
    # 2017 R6 KC (penalty): tampering (Jeremy Maclin), second year
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2017_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.si.com/nfl/2016/03/09/kansas-city-chiefs-nfl-tampering-forfeit-two-draft-picks
    (2017, 6): ["KC"],
    # 2019 R3 NYG (supplemental): 2018 supplemental pick (Sam Beal)
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2019_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://abc7ny.com/post/giants-surrender-2019-third-round-pick-to-take-sam-beal-in-supplemental-draft/3745965/
    (2019, 3): ["NYG"],
    # 2019 R6 WAS (supplemental): 2018 supplemental pick (Adonis Alexander)
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2019_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.nfl.com/news/giants-redskins-select-corners-in-supplemental-draft-0ap3000000940026
    (2019, 6): ["WAS"],
    # 2020 R5 ARI (supplemental): 2019 supplemental pick (Jalen Thompson)
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2020_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://spokesman.com/stories/2019/jul/10/arizona-cardinals-spend-fifth-round-pick-on-washin
    (2020, 5): ["ARI"],
    # 2021 R3 NE (penalty): 2019 Bengals sideline filming
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2021_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.espn.com/nfl/story/_/id/29380577/new-england-patriots-fined-11-million-lose-draft-pick-film-crew-fallout
    (2021, 3): ["NE"],
    # 2021 R7 MIN (penalty): 2019 practice-squad cap violation [added; was UNATTRIBUTED_SHORT]
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2021_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.cbsnews.com/minnesota/news/vikings-lose-7th-rounder-execs-fined-for-19-cap-violation/
    #   https://www.profootballrumors.com/2021/03/draft-pick-updates-vikings-saints-raiders-patriots
    (2021, 7): ["MIN"],
    # 2022 R6 NO (penalty): repeated COVID-19 protocol violations [added]
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2022_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    (2022, 6): ["NO"],
    # 2023 R1 MIA (penalty): tampering (Brady, Payton)
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2023_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.espn.com/nfl/story/_/id/34334514/nfl-strips-miami-dolphins-2023-first-round-pick-fines-stephen-ross-15m-tampering-tom-brady-sean-payton
    (2023, 1): ["MIA"],
    # 2023 R5 HOU (penalty): salary cap reporting violation (Watson) [added]
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2023_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.nfl.com/news/texans-forfeit-2023-fifth-round-pick-fined-175k-for-salary-cap-reporting-violati
    (2023, 5): ["HOU"],
    # 2024 R3 MIA (penalty): tampering (Brady, Payton), second year
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2024_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.espn.com/nfl/story/_/id/34334514/nfl-strips-miami-dolphins-2023-first-round-pick-fines-stephen-ross-15m-tampering-tom-brady-sean-payton
    (2024, 3): ["MIA"],
    # 2025 R5 ATL (penalty): tampering (Cousins, Mooney, Woerner)
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2025_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.espn.com/nfl/story/_/id/40341876/nfl-penalizes-falcons-tampering-eagles-cleared
    # 2025 R5 SF (penalty): 2022 payroll accounting errors
    #   https://en.wikipedia.org/w/api.php?action=parse&page=2025_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
    #   https://www.quirkyresearch.com/2020/04/22/draft-pick-forfeitures-and-penalties/
    #   https://www.nfl.com/news/niners-to-forfeit-2025-fifth-round-pick-as-result-of-administrative-payroll-accounting-errors
    (2025, 5): ["ATL", "SF"],
}
FORFEIT_KIND: dict[tuple[int, int, str], str] = {
    (2001, 5, "SF"): "penalty",
    (2003, 6, "HOU"): "supplemental",
    (2004, 2, "LV"): "supplemental",
    (2006, 5, "MIA"): "supplemental",
    (2007, 3, "CIN"): "supplemental",
    (2008, 1, "NE"): "penalty",
    (2008, 4, "LAC"): "supplemental",
    (2008, 5, "SF"): "penalty",
    (2008, 5, "BAL"): "supplemental",
    (2010, 3, "WAS"): "supplemental",
    (2011, 7, "CHI"): "supplemental",
    (2011, 7, "DAL"): "supplemental",
    (2012, 2, "NO"): "penalty",
    (2012, 3, "LV"): "supplemental",
    (2012, 6, "DET"): "penalty",
    (2013, 2, "NO"): "penalty",
    (2013, 2, "CLE"): "supplemental",
    (2016, 1, "NE"): "penalty",
    (2016, 3, "KC"): "penalty",
    (2016, 5, "ATL"): "penalty",
    (2016, 5, "LA"): "supplemental",
    (2017, 4, "NO"): "penalty",
    (2017, 5, "SEA"): "penalty",
    (2017, 6, "KC"): "penalty",
    (2019, 3, "NYG"): "supplemental",
    (2019, 6, "WAS"): "supplemental",
    (2020, 5, "ARI"): "supplemental",
    (2021, 3, "NE"): "penalty",
    (2021, 7, "MIN"): "penalty",
    (2022, 6, "NO"): "penalty",
    (2023, 1, "MIA"): "penalty",
    (2023, 5, "HOU"): "penalty",
    (2024, 3, "MIA"): "penalty",
    (2025, 5, "ATL"): "penalty",
    (2025, 5, "SF"): "penalty",
}
# Rounds known to be one regular pick short whose owner we can't attribute: nobody is charged.
# Empty since Phase 11: the 2021 R7 gap is MIN's forfeit (now in FORFEITS).
UNATTRIBUTED_SHORT: set[tuple[int, int]] = set()
# Sourced, real, but the derived pick order can't place them; not applied.
# The positional test shows no slot gap for these rounds in the pick data: adding them would
# reclassify a real regular pick as comp and charge an uninvolved team 3.9-7.1 points.
#   2000 R4 NE (supplemental): 1999 supplemental pick (J'Juan Cherry)
#     https://en.wikipedia.org/w/api.php?action=parse&page=2000_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
#   2001 R3 PIT (penalty): 1998 cap violation (Will Wolford)
#     https://www.espn.com/blog/nflnation/post/_/id/55927/history-on-lost-draft-picks
#     https://www.quirkyresearch.com/2020/04/22/draft-pick-forfeitures-and-penalties/
#   2002 R3 DEN (penalty): deferred compensation fund violation
#     https://en.wikipedia.org/w/api.php?action=parse&page=2002_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
#     https://www.quirkyresearch.com/2020/04/22/draft-pick-forfeitures-and-penalties/
#     https://www.espn.com/blog/nflnation/post/_/id/55927/history-on-lost-draft-picks
#   2002 R3 SF (penalty): salary cap violations (same as 2001 R5)
#     https://en.wikipedia.org/w/api.php?action=parse&page=2002_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
#     https://www.espn.com/blog/nflnation/post/_/id/55927/history-on-lost-draft-picks
#   2005 R3 DEN (penalty): 1996-98 salary cap circumvention
#     https://en.wikipedia.org/w/api.php?action=parse&page=2005_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
#     https://www.espn.com/blog/nflnation/post/_/id/55927/history-on-lost-draft-picks
# Also not forfeits: 2001 R3 DEN (DEN used its own R3, #87); 2021 R6 LV and 2021 R7 NO were
# announced then rescinded:
#     https://en.wikipedia.org/w/api.php?action=parse&page=2021_NFL_draft&prop=wikitext&format=json&formatversion=2&redirects=1
#     https://www.profootballrumors.com/2021/03/draft-pick-updates-vikings-saints-raiders-patriots
STD_EPS = 1e-12
EVEN = 0.5  # |surplus| below this reads "about even with their original slots" (rounds to 0)

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


def round_half_away(x: float) -> int:
    """Magnitude rounded half away from zero (|0.5| -> 1, |2.5| -> 3), so it never prints as 0
    unless |x| < EVEN. Python's round() is banker's rounding: round(0.5) == 0."""
    return int(abs(float(x)) + 0.5)


def is_even(surplus: float) -> bool:
    """True when the surplus rounds to 0 (the text says "about even with their original slots")."""
    return abs(float(surplus)) < EVEN


BEYOND_TOP = 1.1  # |surplus| above 1.1 x the #1 pick's value reads "more than a #1 overall pick"


def beyond_top_pick(amount: float, values: np.ndarray) -> bool:
    return abs(float(amount)) > float(values[1]) * BEYOND_TOP


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

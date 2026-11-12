# Phase 7: Draft-Aware Offseason - Research

**Researched:** 2026-11-11
**Domain:** Draft-capital-over-slot metric (nflverse draft picks + value chart), training-only walk-forward test of an offseason term, offseason visibility in Observable Plot and the board
**Confidence:** HIGH for data, derivation and the backtest verdict (all prototyped on real data). MEDIUM for the exact tie-break order of the original slots (approximated).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Data (DATA-06)
- `nflreadpy.load_draft_picks()` (PFR-style codes — map GNB/KAN/LVR/SDG/etc. through an explicit PFR→franchise map, assert full coverage) cached as parquet; nflverse `draft_values.csv` for the chart (columns include stuart/otc/johnson/hill). Chart choice: the flatter of stuart/otc per research (default `stuart`, AV-based).
- Original draft order per season derived from the reverse of the prior season's final standings with playoff adjustments as recorded — research decides the cleanest source (e.g. round-1 pick numbers by team in nflverse with trades flagged, or compute from prior standings).

#### Draft surplus (MODEL-16)
- surplus = Σ chart value of picks actually used by the team in that draft − Σ chart value of the picks the team would have had at its ORIGINAL slot in each of the 7 rounds (compensatory picks excluded from both sides). This measures capital gained/lost by trades, NOT draft position — the worst team holding #1 has surplus ≈ 0 (acceptance test: for every season, the team with the #1 original slot that didn't trade gets surplus 0 ± ε; tanking never helps).
- Cap: surplus winsorized at the 5th/95th percentile of the 1999–2021 distribution, then z-scored across teams for that draft.
- Applied as a separate offseason term `draft` in the week-0 snapshot only (decaying linearly to 0 by week 4 — research may choose decay). Its weight is fit on training seasons only (week-0..4 snapshots of 1999–2021, N=8 adjusted-margin target), added ON TOP of the frozen in-season composite (frozen weights untouched; `weights.yaml` gets a separate `offseason.draft` entry). Report fitted weight, Δ on the week-0 bucket, and fold-sign consistency in BACKTEST_LOG.
- If no signal (Δ ≤ 0 or fold-sign consistency < 60%), weight = 0 and the draft shows as display-only text on the team page ("Draft haul: +X over slot — doesn't move the score"). Either way surplus is exported per team-season.
- No fresh holdout exists (Phase 6 consumed it) — methodology notes the draft term's evidence is training-only walk-forward.

#### Offseason visibility
- Mood-over-time chart: instead of a blank gap between seasons, draw a dashed "offseason" connector from the last snapshot of season S to week 0 of S+1 (still visually distinct = a break), so regression + draft movement is visible. Week 0 tooltip/label "Preseason (after draft)".
- Board at week 0: weekly change column shows change vs prior season's final snapshot (labelled "vs end of last season").
- Team page at week 0: blurb lead mentions draft surplus when non-trivial; factor bars include `draft` if weight ≠ 0.

### Claude's Discretion
- Decay schedule, module layout (`draft.py`), exact PFR mapping source, chart styling of dashed connector.

### Deferred Ideas (OUT OF SCOPE)
- Free agency reaction (v2); grading drafted players' actual performance (needs post-draft outcomes — not knowable at draft time).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-06 | Draft picks and a draft-value chart are loaded for every season | `load_draft_picks()` returns 12,927 rows for 1980–2026 (36 columns). All 35 PFR codes seen since 1999 map to the 32 franchises. `draft_values.csv` has picks 1–262. Original slots come from prior-season standings plus a sequence alignment (Pattern 2). 1999 is the one gap: its draft order needs 1998 standings, which are not in the data. |
| MODEL-16 | Between seasons the score reacts to draft value *above* the original slot (capped), never rewarding tanking | Surplus prototyped for 2000–2026. The untraded slot-1 team scores exactly 0 (CIN 2020). Spearman(surplus, slot) is −0.06. The training-only walk-forward finds **no usable signal**: the final weight is −0.25 and only 7/19 folds share its sign. The gate sends it to **weight 0 + display-only**. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Self-contained in `feel-good-scorew/`. No shared deps or root manifests. Keep it light: no heavy CI, and no tests beyond the model backtest and the existing pytest/vitest suites.
- Stack: Python 3.13 + uv + nflreadpy 0.1.5 + Polars 2.1 (pipeline), Vite 8 + Svelte 5 + Observable Plot 0.6.19 (web). TS stays ~6.0.
- Data: free sources only (nflverse). No scraping PFR.
- Leakage firewall: `features.py` and `score.py` (and the new `draft.py`) must never import `backtest.py`.
- `weights.yaml` is the single source of truth for weights. Frozen weights are never refit. "Code proposes; this file decides."
- Holdout 2022–2025 is consumed/sealed: **no metrics on 2022–2025**. Export/display of their surplus is fine.
- GSD workflow: edits go through `/gsd-execute-phase`.

## Summary

The draft data is clean, but it carries **no trade flag and no compensatory flag**. `load_draft_picks()` gives `season, round, pick, team` (PFR codes) plus career stats. Pick numbers are contiguous. Rounds 3–7 carry 0–11 extra (compensatory) picks at the end. Forfeits show up as short rounds, e.g. 2008/2016/2023 R1 have 31 picks. The nflverse `trades` table only starts in 2002, and rebuilding its trade chains is messy. The cleanest source of "original slot" is therefore the **prior season's standings**:

- order by playoff stage (none, lost WC, DIV, CON, SB, won SB), then win %, then SOS (lower picks first), then franchise id;
- rotate tied groups in each later round;
- expansion teams (HOU 2002) go first;
- a 6-entry table covers the round-1/2 forfeits.

That order is then **aligned** to the actual pick sequence with a small edit-distance DP. Substitutions are trades, deletions are forfeits, and trailing extras in rounds 3–7 are comp picks. Validated against the trades table (2002–2021): only **1.5%** of picks the alignment calls "own pick" appear in a trade, versus **75%** of the picks it calls "traded".

The surplus does exactly what MODEL-16 asks. An untraded #1-slot team gets exactly 0 (CIN 2020, Burrow). Surplus is essentially uncorrelated with slot: Spearman −0.061 with stuart, −0.094 with otc. Every season's surplus sums to ≤ 0 (minus forfeited value). The extremes are recognizable trades:

- Positive: MIA 2020 +39.8 (Tunsil haul), CLE 2018 +37.9, SEA 2023 +36.9 (Wilson trade).
- Negative: LV 2012 −38.5 (Palmer), MIA 2022 −37.2 (Hill), HOU 2021 −36.5 (Tunsil), LA 2022 −29.0 (Stafford/Ramsey), DEN 2023 −29.3 (Wilson).

The biggest swings come from **veteran-for-picks trades**, not draft-day trade-ups.

**The backtest verdict is "no signal".** On training seasons only (2000–2021, walk-forward 2003–2021, interim composite, N=8 target):

- The draft z's partial coefficient is slightly *negative* at every week 0–9 (week 0: −0.35, t = −1.45).
- Walk-forward ΔSpearman on week 0 is within ±0.002 for every decay schedule.
- The fold weights are positive 2003–2014 and flip negative from 2015, which fits "win-now teams trade picks for veterans".
- The final fit is −0.25, and only 7/19 folds share its sign (37% < 60%).

The locked gate sends the term to **weight 0, display-only**. The draft still moves nothing in the score; the offseason movement fans will see is the existing regression to the mean, shown via the dashed connector and the "vs end of last season" delta.

**Primary recommendation:** build `fgs/draft.py` (standings order, then alignment, then surplus, then winsorize + z) with the stuart chart. Add `fgs backtest --draft`, which runs the gate, prints the BACKTEST_LOG row and an `offseason.draft` block with `weight: 0.0`. Export surplus per team-season, plus a pick-equivalent phrase for the display-only text. Ship the dashed connector (Plot `link`) and the week-0 delta vs last season's final snapshot. Keep a weight≠0 code path for completeness, but plan for 0.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Draft picks / value chart ingest + cache | Pipeline ingest (`ingest.py` / `draft.py` loader) | Raw cache (`data/cache/`) | Same pattern as schedules/win_totals: we own the parquet/CSV |
| Original slot order, alignment, surplus, z | Pipeline pure module `draft.py` | — | Pure, testable, no backtest import (firewall) |
| Draft weight fit + gate | Dev-only `backtest.py` | `weights.yaml` (human-pasted) | Looks at future games (targets) → must live behind the firewall |
| Applying the term to week 0..3 composites | `score.py` | `weights.yaml` `offseason.draft` | Additive term on top of the frozen composite |
| Week-0 delta vs last season | `mood.score_frame` | export `_row` | Deltas are computed there today (per franchise-season) |
| Draft text in the blurb / display-only line | `explain.py` (text) + export (fields) | Svelte TeamPage | Text is generated in the pipeline; web only renders |
| Dashed offseason connector | Web `history.ts` (pure rows) + `HistoryChart.svelte` (Plot mark) | — | Pure geometry is unit-testable in vitest |
| "vs end of last season" label | Web `BoardRow` / `MoodBoard` / `BoardHeading` | — | Presentation only |

## Standard Stack

### Core (all already installed; no new packages)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| nflreadpy | 0.1.5 | `load_draft_picks()` (1980–2026) | [VERIFIED: live call 2026-11-11, 12,927 rows, 0.56 s] |
| polars | 2.1.0 | joins/z-scores/winsorizing | already the frame library |
| numpy | ≥2.5.4 | alignment DP (≤ 33×54 matrix per round), lstsq | already present |
| urllib (stdlib) | — | download `draft_values.csv` once | same pattern as `expectation.load_win_totals` [VERIFIED: codebase] |
| @observablehq/plot | 0.6.19 | `Plot.link` for the dashed connector | `link.d.ts` exposes `x1,y1,x2,y2`; `strokeDasharray` is a MarkOption [VERIFIED: node_modules d.ts] |

### Data sources
| Source | URL / call | Shape | Notes |
|--------|-----------|-------|-------|
| Draft picks | `nflreadpy.load_draft_picks()` | `season, round, pick (overall), team (PFR code), pfr_player_name, position, …` | No trade/comp/forfeit flags [VERIFIED]. Pick numbers contiguous within each season [VERIFIED] |
| Value chart | `https://raw.githubusercontent.com/nflverse/nfldata/master/data/draft_values.csv` | 262 rows: `pick, stuart, johnson, hill, otc, pff` | Max pick in any 1999–2026 draft is ≤ 262 (2002 had 261). Assert it |
| Trades (validation only) | `nflreadpy.load_trades()` | 4,975 rows, 2002–2026, `pick_season, pick_round, pick_number, gave, received` | Used only to validate the alignment in research. **Don't** make it a pipeline dependency |

### Chart choice: `stuart` (keep the default)
Value relative to pick #1 [VERIFIED: draft_values.csv]:

| pick | stuart | otc | johnson | hill |
|---|---|---|---|---|
| 10 | 0.575 | 0.596 | 0.433 | 0.369 |
| 32 | 0.361 | 0.392 | 0.197 | 0.184 |
| 64 | 0.234 | 0.270 | 0.090 | 0.077 |
| 100 | 0.153 | 0.192 | 0.033 | 0.036 |
| 224 | 0.003 | 0.050 | 0.001 | 0.002 |

OTC is slightly flatter, mostly in rounds 5–7. Surplus from the two charts correlates at **0.984** (Pearson) and **0.980** (Spearman) [VERIFIED: prototype]. Stuart is closer to slot-neutral: Spearman(surplus, slot) is −0.061 for stuart vs −0.094 for otc. Both backtest the same (null). Stuart is AV-based (empirical production), and the CONTEXT default. **Use `stuart`** and record otc as checked/equivalent.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Standings-derived order + alignment | Reconstruct ownership from `load_trades()` | Starts 2002 (misses 2000–2001). Multi-hop and conditional picks are messy. Comp picks are still unflagged |
| Standings-derived order + alignment | "Modal slot" (each team's most common within-round position) | Breaks for teams that traded many picks, which are exactly the interesting ones |
| Alignment for rounds 3–7 forfeits | Hand-coded forfeit list for all rounds | Value at stake in rounds 3–7 is small (stuart ≤ 8). An incomplete list is a maintenance trap |

**Installation:** none. No new packages.

## Package Legitimacy Audit

No new external packages are installed in this phase. nflreadpy 0.1.5, polars, numpy and @observablehq/plot 0.6.19 are already pinned in `pipeline/uv.lock` / `web/package.json` and were audited in earlier phases. slopcheck was not run (nothing to check).

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| (none new) | — | — | — | — | — | — |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
nflreadpy.load_draft_picks() ──► cache/draft_picks.parquet ─┐
nfldata draft_values.csv ──────► cache/draft_values.csv ────┤
derived team_games (season S-1) ─► standings(S-1) ──────────┤
                                                            ▼
                         draft.original_order(S)  [stage, win%, SOS, fid; tie rotation;
                                                   expansion first; R1-2 forfeit table]
                                                            │
                         per round r: align(original_slots, actual_pick_teams)
                           match/sub  → regular pick (orig owner ← slot, user ← actual team)
                           deletion   → forfeited slot (charged to original owner)
                           tail extra (r≥3) / insertion → comp/extra pick (excluded)
                                                            │
                                                            ▼
                         surplus[S, team] = Σ value(used regular) − Σ value(original slots)
                                                            │
                          winsorize [p5,p95 of 2000–2021] → z per draft (season S)
                                │                                     │
           (dev only) backtest --draft:                      score.py: contrib_draft =
           walk-forward 2003–2021, gate ──► weights.yaml       w · z · decay(week)   (w = 0 → skipped)
           offseason.draft.weight (pasted)                            │
                                                                       ▼
                                   mood.score_frame (deltas over franchise across seasons)
                                                                       │
                       export: week-0 rows + team files get draft {surplus, z, equiv_pick, rank}
                               week_labels["0"] = "Preseason (after draft)"
                                                                       │
                web: history.ts connectors → Plot.link dashed;  BoardRow "vs end of last season";
                     TeamPage display-only "Draft haul" line
```

### Recommended Project Structure
```
pipeline/src/fgs/
├── draft.py          # NEW: PFR map, loaders, standings, original_order, align, surplus_table, draft_z, decay, equiv_pick
├── backtest.py       # + draft_walk_forward(), draft_gate(), format_draft_log_row()
├── score.py          # + load_offseason(); add contrib_draft only when weight != 0
├── mood.py           # deltas shift over franchise across seasons (week 0 vs last season's final row)
├── explain.py        # + draft clause for week-0 blurb lead (non-trivial surplus)
├── export.py         # + draft fields; week_labels["0"]; meta.offseason
├── checks.py         # + DATA-06 checks (codes, coverage, chart range, alignment sanity)
└── cli.py            # + `fgs backtest --draft`; build/refresh load draft data
pipeline/tests/test_draft.py    # NEW (synthetic + cached-real acceptance)
web/src/lib/history.ts          # + connectors()
web/src/components/HistoryChart.svelte  # + Plot.link dashed for highlighted team
```

### Pattern 1: PFR → franchise map (explicit, asserted)
PFR codes seen in 1999–2026 [VERIFIED: live data]: `ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GNB HOU IND JAX KAN LAC LAR LVR MIA MIN NOR NWE NYG NYJ OAK PHI PIT SDG SEA SFO STL TAM TEN WAS`.
```python
PFR_TO_FRANCHISE = {"GNB": "GB", "KAN": "KC", "LVR": "LV", "OAK": "LV", "SDG": "LAC", "LAC": "LAC",
                    "LAR": "LA", "STL": "LA", "NOR": "NO", "NWE": "NE", "SFO": "SF", "TAM": "TB"}
def map_pfr(code: str) -> str:
    f = PFR_TO_FRANCHISE.get(code, code)
    if f not in CANONICAL:                      # fgs.franchises.CANONICAL
        raise ValueError(f"unknown PFR team code: {code!r}")
    return f
```
Note `LAR` (PFR) vs `LA` (ours), and that `LAC` appears both as itself and via `SDG`. Unique franchises per draft: 31 in 1999–2001, 32 from 2002 [VERIFIED].

### Pattern 2: Original order from prior standings + tie rotation
```python
# Source: prototype scratchpad/p7/draftproto.py (verified on 2000–2026)
STAGE = {"WC": 1, "DIV": 2, "CON": 3, "SB": 4}      # last playoff game_type; won SB -> 5; no playoffs -> 0
EXPANSION_FIRST = {2002: "HOU"}                      # (1999 CLE too, but the 1999 draft is skipped)
FORFEITS_R12 = {(2004, 2): ["LV"], (2008, 1): ["NE"], (2012, 2): ["NO"], (2013, 2): ["NO", "CLE"],
                (2016, 1): ["NE"], (2023, 1): ["MIA"]}   # original slot owner whose slot vanished

def standings(team_games, season):   # REG win% (ties .5), SOS = mean opp REG win% over REG games, grp
    ...
def original_order(team_games, draft_year, n_rounds=7) -> list[list[str]]:
    st = standings(team_games, draft_year - 1).sort(["grp", "wp", "sos", "franchise_id"])
    # tied groups = same (grp, wp); for grp < 4, rotate left by (round_index % len(group))
    # prepend EXPANSION_FIRST[draft_year] to every round when present
```
Rotation matters: 45.5% own-pick match with rotation vs 31.5% without [VERIFIED].

### Pattern 3: Align original slots to actual picks (edit distance)
```python
def align(orig, actual, sub=1.0, dele=3.0, ins=4.0, free_tail=True):
    """DP over (slot i, position j). match 0 / substitute (trade) 1 / delete slot (forfeit) 3 /
    insert extra pick 4, except trailing extras are free when free_tail (rounds 3-7: comp picks).
    Rounds 1-2: free_tail=False and FORFEITS_R12 slots removed from `orig` first (charged separately)."""
```
- Costs were tuned on real data. With 1.5/1.5, deletions were spurious (70 flagged events, e.g. "SEA" in 2008 R1). With 3/4 that drops to 26, mostly plausible [VERIFIED].
- In rounds 1–2 the alignment can't reliably tell *which* team forfeited when neighbouring picks were traded (2008 R1 picked SEA instead of NE). Hence the small R1–R2 table [CITED: nfl.com draft-picks-stripped list; Wikipedia 2004 NFL draft]. In rounds 3–7 a wrong guess moves at most one late pick's value (stuart ≤ ~8).
- A forfeited slot charges its original owner the value of the pick it would have been: the position of that slot in the round. The owner loses it. Nobody gains it.

### Pattern 4: Surplus, cap, z, decay
```python
surplus = actual_regular_value - original_slot_value         # per (draft_year, franchise)
lo, hi = WINSOR = (-17.29, 16.19)   # p5/p95 of stuart surplus 2000–2021 — store in weights.yaml, never recompute on refresh
zd = (clip(s, lo, hi) - mean_over_draft) / std_over_draft(ddof=0)   # 0.0 when std ≤ 1e-12
DECAY = lambda week: max(0.0, 1.0 - week / 4)                       # 1, .75, .5, .25, 0
contrib_draft = w * zd * DECAY(week)                                # season S rows, weeks 0..3
```
Draft year S joins to season S snapshots: the April draft precedes that season [VERIFIED: draft 2020 → Burrow on CIN 2020].

### Pattern 5: Dashed offseason connector (pure geometry + one Plot mark)
```ts
// history.ts — keep toRows() as is (NaN rows still break the solid line); add:
export interface Connector { team: string; x1: number; y1: number; x2: number; y2: number }
export function connectors(h: HistoryFile, xs: number[], team?: string): Connector[] {
  const out: Connector[] = []
  for (const [t, scores] of Object.entries(h.teams)) {
    if (team && t !== team) continue
    for (let i = 1; i < h.keys.length; i++) {
      if (seasonOf(h.keys[i]) === seasonOf(h.keys[i - 1])) continue
      let a = i - 1; while (a >= 0 && scores[a] == null) a--        // last non-null of season S
      const b = i                                                    // week 0 of S+1
      if (a < 0 || seasonOf(h.keys[a]) !== seasonOf(h.keys[i - 1]) || scores[b] == null) continue
      out.push({ team: t, x1: xs[a], y1: scores[a]!, x2: xs[b], y2: scores[b]! })
    }
  }
  return out
}
// HistoryChart.svelte — after the highlighted Plot.line:
Plot.link(connectorRows, { x1: 'x1', y1: 'y1', x2: 'x2', y2: 'y2', stroke: color,
  strokeWidth: 1.5, strokeDasharray: '3,3', strokeOpacity: 0.8 })
```
- The existing one-slot x gap stays. The connector spans it (x2 = x1 + 2), which reads as "offseason".
- Draw connectors for the **highlighted team only**. 31 faint dashed segments per boundary (about 860 in all) add noise, not information.
- `Plot.link` with linear x/y scales draws straight segments (curve auto) [VERIFIED: link.d.ts `CurveAutoOptions`].

### Pattern 6: Week-0 delta vs end of last season
```python
# mood.score_frame: deltas over the franchise's whole history, not per season
df = df.sort(["franchise_id", "season", "week"]).with_columns(
    (pl.col("score") - pl.col("score").shift(1).over("franchise_id")).alias("score_delta"),
    (pl.col("rank").shift(1).over("franchise_id") - pl.col("rank")).alias("rank_delta"),
)
```
The grid is contiguous (every team has every week 0..wmax per season [VERIFIED: snapshots.build_grid]), so for week ≥ 1 this is identical to today. Week 0 picks up the prior season's final row, a playoff week for everyone because the grid forward-fills. It stays null for 1999 and for HOU 2002.

### Anti-Patterns to Avoid
- **Raw draft capital as the term:** it rewards tanking (FEATURES/PITFALLS #8). Always over-slot.
- **Recomputing the winsor bounds on each refresh:** future drafts would shift past z's. Freeze p5/p95 from 2000–2021 in `weights.yaml`.
- **Including the draft term in the percentile reference:** `mood.reference_values` uses the composite. If w ≠ 0, keep the reference on the in-season composite so past scores don't move. Moot at w = 0, but write it right.
- **Adding `draft` to `weights:`:** `load_weights` rejects unknown keys and Phase 6's freeze guard owns that block. Use a separate top-level `offseason:` block and a separate loader.
- **Importing backtest from draft.py/score.py:** breaks the leakage firewall.
- **Reading surplus as "drafted well":** it measures capital moved by trades, including picks spent on veterans (Stafford, Hill, Wilson, Tunsil). The text must say "over/under their original slots", not "great draft".

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pick values | your own curve fit | nflverse `draft_values.csv` `stuart` | Published, AV-grounded, 262 picks |
| Trade-chain reconstruction | parse `load_trades()` into ownership chains | standings order + alignment | Trades start 2002; conditional/multi-hop picks; comp picks still unflagged |
| Full NFL draft tiebreakers (div/conf/common games, coin flip) | the whole tiebreak cascade | win% → SOS → franchise id | Affects only exact ties after SOS. Mismatch shows up as small ± values for untraded teams (≤ 0.3 observed for slot-1 teams) |
| Walk-forward, Spearman | new harness | `backtest.targets`, `backtest.spearman`, the snapshot features | Already verified. Reuse |
| Dashed line breaks | custom SVG paths | `Plot.link` + `strokeDasharray` | One mark, typed in 0.6.19 |

## Common Pitfalls

### Pitfall 1: The 1999 draft can't be derived
**What goes wrong:** the 1999 draft order needs 1998 standings. Schedules start in 1999 [VERIFIED: schedules.parquet min season 1999].
**How to avoid:** compute surplus for drafts 2000+ only. Set 1999's `draft` to null: z = 0, excluded from fit and percentiles, no text. The CONTEXT's "1999–2021" winsor distribution is effectively 2000–2021 (702 team-drafts). Say so in BACKTEST_LOG.

### Pitfall 2: Forfeits shift every later slot in a round
**What goes wrong:** a naive "position i in round = slot i" mapping misattributes every pick after a forfeit (2008, 2016, 2023 R1; 2004, 2012, 2013 R2).
**How to avoid:** the R1–R2 forfeit table plus alignment deletions (Pattern 3). Sanity check: per-season Σ surplus ≤ 0 and equal to minus the forfeited value. Observed stuart sums are 0 in clean years and −0.5 to −21.5 in forfeit years [VERIFIED].

### Pitfall 3: Compensatory picks counted as regular
**What goes wrong:** comp picks (end of rounds 3–7; Rooney-rule comps at the end of R3 from 2021) inflate surplus for teams that lost free agents.
**How to avoid:** free trailing extras in rounds ≥ 3. Rounds 1–2 never have trailing comps. The one oddity, 2002 R2 with 33 picks, causes only a local 1-slot shift. Comp picks have been tradeable since 2017, and both sides exclude them by design.

### Pitfall 4: Gate ambiguity (majority of folds positive, final weight negative)
**What goes wrong:** linear-to-wk4 / residual fit has 12/19 folds positive and wk0 Δ = +0.0002. A naive "Δ > 0 and ≥ 60% of folds share *a* sign" rule would pass and ship the final weight of **−0.25**. That penalizes teams for adding draft capital.
**How to avoid:** gate = (wk0 ΔSpearman > 0) AND (fraction of folds whose sign equals the **final** weight's sign ≥ 0.60) AND (final weight > 0). Any failure sets weight 0. Log all three numbers.

### Pitfall 5: Phase 6 hasn't frozen yet
**What goes wrong:** the prototype used the interim 7-factor composite (`features.parquet` as of 2026-11-11). Phase 7 depends on Phase 6, whose frozen 11-factor composite is what the draft term sits on.
**How to avoid:** `fgs backtest --draft` reads the frozen weights and recomputes. The plan records whatever it prints. Expect the same verdict: the effect is |t| ≤ 1.5 and sign-unstable at every week, and the composite's correlation with zd is only about −0.10.

### Pitfall 6: Score-delta tests pin week-0 null
`pipeline/tests/test_mood.py:166` (`w0 score_delta null_count == 3`) and `test_export.py:118` (week-0 deltas None) must change. `test_export.py:92` pins `week_labels["0"] == "Preseason"`. `web/src/components/BoardRow.svelte:35` returns "No change, preseason." at week 0.

### Pitfall 7: Concurrent Phase 5 edits
Phase 5 executors are touching `pipeline/**` (cli, features, score). Plan Phase 7 edits after Phase 5/6 land and re-read the files. `draft.py` is new and conflict-free.

### Pitfall 8: Display units
Raw stuart points ("+12.4") mean nothing to fans. Translate |surplus| to a pick-equivalent: the smallest pick p with value[p] ≤ |s|. For example 34.6 → "the #1 pick", 12.5 → "a late first-rounder" (#32), 8.1 → "an end-of-round-2 pick" (#64). Use a "non-trivial" threshold of |s| ≥ value[64] = 8.1. That flags 32% of team-drafts; ≥ 12.5 flags 19% [VERIFIED].

## Code Examples

### Surplus core (verified prototype logic)
```python
# Source: scratchpad/p7/draftproto.py (run 2026-11-11)
for r in range(1, 8):
    picks = draft_round(y, r)                         # sorted by overall pick
    forced = FORFEITS_R12.get((y, r), [])
    o = [t for t in order[r - 1] if t not in forced]
    for t in forced:                                  # charge the vanished slot to its owner
        orig_v[t] += values[min(first_pick_of_round + order[r - 1].index(t), 262)]
    for si, pj in align(o, picks.team, free_tail=r >= 3):
        if si is not None and pj is not None:         # regular pick (own or traded)
            v = values[picks.pick[pj]]; orig_v[o[si]] += v; used_v[picks.team[pj]] += v
        elif si is not None:                          # forfeited slot found by alignment
            orig_v[o[si]] += values[min(last_aligned_pick + 1, 262)]
        # else: comp/extra pick -> excluded from both sides
```

### Draft gate (dev-only, backtest.py)
```python
def draft_gate(fold_ws: list[float], final_w: float, d_wk0: float) -> dict:
    same = sum(1 for w in fold_ws if np.sign(w) == np.sign(final_w)) / len(fold_ws)
    ok = d_wk0 > 0 and same >= 0.60 and final_w > 0
    return {"weight": round(final_w, 2) if ok else 0.0, "fitted": final_w, "delta_wk0": d_wk0,
            "fold_sign_consistency": same, "display_only": not ok}
```
Fit (recommended "residual" form, which treats the frozen composite as fixed): for each test season S in 2003..2021, regress `y8 − composite` on `decay(week)·zd` with an intercept, over rows with season in [2000, S−1] and decay > 0. Predict `composite + w·decay·zd` for season S. Report the pooled wk0 ΔSpearman vs the composite alone. Final weight = the same fit on 2000–2021. Hard-filter `season <= 2021` before features, targets or surplus z (holdout sealed).

### weights.yaml block (pasted by hand, like the in-season weights)
```yaml
offseason:
  draft:
    weight: 0.0            # gate failed: fitted -0.25, fold-sign consistency 7/19, wk0 dSpearman +0.0002
    display_only: true
    chart: stuart
    winsor: [-17.29, 16.19]   # p5/p95 of 2000-2021 surplus (1999 draft not derivable)
    decay: linear_to0_by_wk4  # weeks 0,1,2,3 -> 1, .75, .5, .25
    fit_seasons: 2000-2021
    evidence: training-only walk-forward (no fresh holdout)
```

## Prototype Results (training only, 2000–2021; holdout never read)

**Draft-z partial coefficient by snapshot week** (y8 ~ 1 + composite + zd; stuart; n = 702 per week):

| wk | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|
| coef | −0.35 | −0.20 | −0.22 | −0.03 | −0.10 | −0.17 | −0.07 | −0.19 | −0.13 |
| t | −1.45 | −0.83 | −0.94 | −0.13 | −0.44 | −0.75 | −0.31 | −0.85 | −0.55 |

Units: points of N=8 adjusted margin per SD of zd. For scale, the week-0 composite SD is 3.37. Corr(zd, composite) ≈ −0.10 to −0.12: teams with extra capital are slightly weaker on paper. Season-long target (N=16) at week 0: −0.32, t = −1.51. Univariate Spearman(zd, y8) at week 0: −0.087.

**Walk-forward 2003–2021** (stuart; "resid" = residual on fixed composite, "partial" = composite coefficient free):

| decay | fit | wk0 ΔSp | wk0–4 ΔSp | final-fold w | folds + | wk0 seasons Δ>0 |
|---|---|---|---|---|---|---|
| wk0 only | resid | +0.0021 | +0.0005 | −0.27 | 10/19 | 8/19 |
| **linear → 0 by wk4** | resid | +0.0002 | +0.0003 | −0.23 | 12/19 | 9/19 |
| linear → 0 by wk4 | partial | +0.0014 | +0.0005 | −0.30 | 12/19 | 6/19 |
| flat wk0–3 | resid | −0.0011 | −0.0002 | −0.13 | 13/19 | 8/19 |
| linear → 0 by wk8 | resid | −0.0019 | −0.0007 | −0.17 | 13/19 | 7/19 |

Fold weights (linear-wk4, resid): +0.08 to +0.27 for test seasons 2003–2014, then −0.04 to −0.24 for 2015–2021. Final fit on 2000–2021: **−0.249** (stuart), −0.178 (otc). OTC gives the same picture (all |Δ| ≤ 0.0017). **Verdict: gate fails, weight = 0.**

**Decay choice:** keep **linear → 0 by week 4** (the CONTEXT default). No schedule shows real signal, and this one is the most conservative non-trivial shape if a future refit ever passes the gate.

**Slot-1 acceptance check (stuart):** CIN 2020 0.0 (untraded). SF 2005 −0.2, HOU 2014 −0.3, TEN 2025 −0.2 (a late-round trade or tie-order approximation; |s| < 1). Big values are real trades: CLE 2018 +37.9 (#1 + #4 from HOU), CLE 2017 +22.6, JAX 2021 +27.8 (#25 via the Ramsey trade), CAR 2024 −26.6 (#1 traded to CHI), SD/LAC 2001 −10.5 (traded #1 for the Vick deal), KC 2013 −12.1 (Alex Smith trade). 32 of 702 team-drafts have surplus exactly 0.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Jimmy Johnson chart (1990s) | AV-based (Stuart) / OTC / Baldwin surplus charts | 2010s | Top picks are worth much less relative to later picks. Use `stuart` |
| Comp picks not tradeable | Comp picks tradeable | 2017 | They are excluded from both sides anyway |
| — | Rooney-rule special comp picks at the end of R3 | 2021+ | Treated as trailing extras by the alignment |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Draft-order rule: non-playoff teams by win% then SOS (lower first); playoff teams by elimination round, then record. Tied teams rotate each round | Pattern 2 | Low. The 45% own-pick match and 1.5% vs 75% trade validation say the order is right in aggregate. Exact-tie errors give ± small values |
| A2 | 2013 R2 forfeit by CLE (Josh Gordon 2012 supplemental) | FORFEITS_R12 | Low. One 2nd-round slot's value for two teams in one year. The other R1–R2 entries are cited |
| A3 | Phase 6's frozen composite will give the same "no signal" verdict as the interim composite | Pitfall 5 | Medium. If it somehow passes the gate with a positive weight, the w≠0 path (bars, contrib, reference) must work. Plan it, test it with a fake weight |
| A4 | The nflverse 2026+ schedule appears after the draft, so week-0 rows are always "after draft" | export label | Low. Label only |

## Open Questions (RESOLVED)

1. **Cleanest source of original order?**
   RESOLVED: prior-season standings from our own `team_games`, plus tie rotation, expansion-first, the R1–R2 forfeit table, and edit-distance alignment to the actual picks. The trades table is used only to validate in research.
2. **stuart or otc?**
   RESOLVED: `stuart`. Surplus correlates 0.98 between the two. Stuart is more slot-neutral (−0.061 vs −0.094), backtests the same, and is the CONTEXT default.
3. **The 1999 draft?**
   RESOLVED: not derivable (no 1998 standings). Null surplus, z = 0, no text. The winsor distribution is 2000–2021.
4. **Gate definition when folds are mostly positive but the final fit is negative?**
   RESOLVED: fold-sign consistency is measured against the final weight's sign, and the weight must also be > 0. Per the prototype: weight 0, display-only.
5. **Fit form (residual vs partial)?**
   RESOLVED: residual on the fixed frozen composite. It matches "on top of frozen weights" and keeps the composite's coefficient at 1. Log the partial fit as a cross-check.
6. **Decay?**
   RESOLVED: linear to 0 by week 4 (1, .75, .5, .25, 0 for weeks 0–4).
7. **Connectors for all 32 lines or the highlight only?**
   RESOLVED: highlight only, dashed `3,3`, team colour at 0.8 opacity. Background lines keep their gaps.
8. **Where does "Preseason (after draft)" come from?**
   RESOLVED: the pipeline's `week_labels["0"]` for every season. All views already read it via `weekLabel`. The format.ts fallback stays "Preseason". The board heading's week-0 note adds "Change is vs the end of last season."
9. **Display-only text units?**
   RESOLVED: pick-equivalent phrase plus the signed number, e.g. "Draft haul: +16 over their original slots (about an extra mid-first-round pick) — doesn't move the score." The blurb lead mentions it when |surplus| ≥ value[64] (8.1).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| nflreadpy (network to nflverse releases) | draft picks ingest | ✓ | 0.1.5 | cached parquet after the first pull |
| raw.githubusercontent.com | draft_values.csv | ✓ (downloaded in research) | — | cached CSV (frozen file) |
| uv | pipeline runs/tests | ✓ | 0.10.12 | — |
| Node | web build/vitest | ✓ | 20.19.0 (meets Vite 8 floor; 22/24 recommended) | — |
| vitest | web unit tests | ✓ | in node_modules | — |

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥9.2 (pipeline), vitest 5.x (web) |
| Config file | `pipeline/pyproject.toml` `[tool.pytest.ini_options] testpaths=["tests"]`; `web/` vitest default |
| Quick run command | `cd pipeline && uv run pytest -q tests/test_draft.py` ; `cd web && npx vitest run src/lib/history.test.ts` |
| Full suite command | `cd pipeline && uv run pytest -q` ; `cd web && npm test && npm run check` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-06 | Every PFR code since 1999 maps; unknown code raises | unit | `uv run pytest -q tests/test_draft.py -k pfr` | ❌ Wave 0 |
| DATA-06 | Draft cache covers 2000..current; 31/32 franchises per draft; max pick ≤ 262; chart has picks 1..262 | integration (cached data, skip if no cache) | `uv run pytest -q tests/test_draft.py -k coverage` | ❌ Wave 0 |
| MODEL-16 | Synthetic 4-team draft: untraded team → surplus 0 exactly; a trade-up moves value between exactly two teams; a forfeit lowers only the owner; comp tail excluded | unit | `uv run pytest -q tests/test_draft.py -k surplus` | ❌ Wave 0 |
| MODEL-16 | Real data: every draft 2000–2026, a slot-1 team whose aligned picks are all its own and that has no extra regular picks → surplus == 0; per-season Σ surplus ≤ 1e-9; Spearman(surplus, slot) over 2000–2021 in [−0.15, 0.15] | integration | `uv run pytest -q tests/test_draft.py -k acceptance` | ❌ Wave 0 |
| MODEL-16 | Tie rotation + expansion-first + R1–R2 forfeit table used in `original_order` | unit | `-k order` | ❌ Wave 0 |
| MODEL-16 | Gate: (Δ>0, consistency vs final sign ≥ .6, w>0) else 0; never reads seasons > 2021 | unit (synthetic) + leakage | `uv run pytest -q tests/test_backtest.py -k draft` | ❌ Wave 0 |
| MODEL-16 | w = 0 → no `contrib_draft`, factor keys unchanged, scores identical to pre-phase; w ≠ 0 (fake 1.0) → contrib only weeks 0–3 with decay; percentile reference unchanged | unit | `uv run pytest -q tests/test_score.py -k draft` | ❌ Wave 0 |
| MODEL-16 | Week-0 score_delta = score(S,0) − score(S−1,last); null for first season/expansion | unit | `uv run pytest -q tests/test_mood.py` (update line 166) | ✅ (edit) |
| MODEL-16 | Export: week-0 rows carry `draft` {surplus, z, equiv_pick, rank} or null; `week_labels["0"]=="Preseason (after draft)"`; meta.offseason present | unit | `uv run pytest -q tests/test_export.py` (update 92, 118) | ✅ (edit) |
| MODEL-16 | Leakage: appending a future season doesn't change past week-0 deltas/surplus/z (frozen winsor) | unit | `uv run pytest -q tests/test_leakage.py` | ✅ (extend) |
| Visibility | `connectors()`: one segment per team per boundary, from the last non-null of S to week 0 of S+1; skips nulls; highlight filter | unit (vitest) | `npx vitest run src/lib/history.test.ts` | ✅ (extend) |
| Visibility | BoardRow week-0 text "… vs end of last season" | manual/visual + svelte-check | `npm run check` | — |
| MODEL-16 | BACKTEST_LOG row with fitted weight, wk0 Δ, fold-sign consistency (k/19) | manual (command output pasted) | `uv run fgs backtest --draft` | — |

### Sampling Rate
- **Per task commit:** the quick command for the touched side.
- **Per wave merge:** the full pipeline pytest plus web `npm test`.
- **Phase gate:** full suites green, `uv run fgs backtest --draft` output recorded in BACKTEST_LOG and weights.yaml, and `uv run fgs export` builds.

### Wave 0 Gaps
- [ ] `pipeline/tests/test_draft.py`: synthetic builders for team_games standings and draft rounds; real-cache acceptance (skip when cache missing)
- [ ] Fixture: tiny `draft_values` (picks 1..N) for unit tests
- [ ] Extend `web/src/lib/history.test.ts` with `connectors()` cases

## Security Domain

`security_enforcement` is `false` in `.planning/config.json`, so this section is omitted. The only new network inputs are two nflverse downloads over HTTPS with a timeout, the same pattern as win_totals.

## Sources

### Primary (HIGH confidence)
- Live `nflreadpy.load_draft_picks()` / `load_trades()` (0.1.5) on 2026-11-11: schema, coverage, codes, per-round counts.
- `nflverse/nfldata/data/draft_values.csv` (downloaded): columns and values.
- Codebase: `backtest.py`, `features.py`, `score.py`, `mood.py`, `explain.py`, `export.py`, `snapshots.py`, `expectation.py`, `web/src/lib/history.ts`, `HistoryChart.svelte`, `BoardRow.svelte`, `format.ts`, Plot `link.d.ts`/`mark.d.ts`.
- Prototype runs: `/private/tmp/claude-501/-Users-noahmanion-Dropbox-code-idea-graveyard-feel-good-scorew/e9aca8f6-0367-4770-bd90-f3eef6a0daef/scratchpad/p7/draftproto.py`, `bt.py` (against a frozen copy of `pipeline/src` + derived parquet; seasons > 2021 filtered before any metric).

### Secondary (MEDIUM confidence)
- [NFL.com: draft picks stripped from teams since 1980](https://www.nfl.com/news/draft-picks-that-have-been-stripped-from-nfl-teams-since-1980-0ap3000000492229): 2008/2016 NE R1, 2012–13 NO R2, MIA 2023 R1.
- [NBC Sports Boston: teams that forfeited first-round picks](https://www.nbcsportsboston.com/nfl/new-england-patriots/heres-a-look-at-nfl-teams-that-have-forfeited-their-first-round-picks/262218/)
- [ESPN: unprecedented violations, lost draft picks (MIA)](https://africa.espn.com/nfl/story/_/id/34334811/unprecedented-violations-lost-draft-picks-know-nfl-discipline-miami-dolphins)
- [Wikipedia: 2004 NFL draft](https://wikipedia.com/wiki/2004_NFL_draft): the R2 pick acquired by HOU from OAK, forfeited for the 2003 supplemental (Tony Hollings).

### Tertiary (LOW confidence)
- Draft-order tiebreak details beyond SOS (training knowledge; validated only in aggregate).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. No new packages; data verified live.
- Architecture: HIGH. Mirrors existing modules; firewall respected.
- Original-order derivation: MEDIUM-HIGH. Validated against trades (1.5% vs 75%); exact-tie order approximated.
- Backtest verdict: HIGH for "no signal" on the interim composite. MEDIUM that the frozen composite gives the same (A3).
- Pitfalls: HIGH. All observed in the prototype or the codebase.

**Research date:** 2026-11-11
**Valid until:** 2026-12-11 (stable data; re-check after the Phase 6 freeze)

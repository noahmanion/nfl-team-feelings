# Phase 8: Callouts, Records & My Team - Research

**Researched:** 2026-11-11
**Domain:** Pipeline-side insight generation (Polars), static JSON contract extension, Svelte 5 UI (cards, strip, records page, localStorage pin, clipboard)
**Confidence:** HIGH for the data findings (prototyped on the current export and derived parquet). MEDIUM for the exact numbers, which will shift slightly as factors are added; the design is built to tolerate that.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Perception-gap callouts (INSIGHT-02, SITE-09)
- Record-implied rank = rank by REG win% to date (ties → point differential → franchise id). Gap = record_rank − score_rank. Flag when week ≥ 4 and |gap| ≥ 8 (research may tune threshold to yield ~2–5 callouts/week on average).
- Two flavors: record better than score → "{W-L} but you should feel worried"; score better than record → "{W-L}, but better days are coming". Include a base-rate evidence line computed on training seasons 1999–2021 only: e.g. "Teams with a gap this big went on to average {x} pts/game worse than their record peers over the next 8 games ({n} cases since 1999)." Research defines the peer comparison.
- callouts.json: [{type: "worried"|"hopeful"|"mover_up"|"mover_down"|"misery"|"joy", season, week, franchise, headline, detail, evidence?}]; current-week callouts shown on board (top card strip) and the team's own callouts on its team page. Past weeks: callouts per season file rows (`callouts` key) or a season-keyed callouts file — planner decides; scrubbing the board to a past week shows that week's callouts.
- Callout card: team chip, headline (big), detail, link to team page; a "Copy link" button copies the deep link (navigator.clipboard with try/catch fallback). No share images (v2).

#### Movers (INSIGHT-06, SITE-05)
- Top 3 risers and top 3 fallers by score_delta for the displayed week (week ≥ 1), shown as a compact strip above the board.

#### Streaks in calendar days (INSIGHT-03)
- Each snapshot gets a date: week ≥ 1 → last gameday of that week; week 0 → draft date (or Sept 1 if unknown). A team's mood on each calendar day = its latest snapshot as of that day. Misery = consecutive days with score < 20 ("Refreshing mock drafts" or worse); joy = consecutive days with score ≥ 80. Current active streak shown on team page ("Miserable for 612 straight days"); records page lists the 10 longest ever (and flags active ones).

#### Historical extremes (INSIGHT-04, SITE-06)
- Saddest/happiest fanbases ever: one entry per team-season (its min / max score and when), top 10 each; plus longest misery/joy streaks top 10. Route `#/records`, nav "Records".
- Hand-check: pipeline writes `pipeline/RECORDS_CHECK.md` listing the top-10 lists with season records and a sanity note per row (verifier/orchestrator checks them against known history, e.g. 2008 Lions 0-16, 2007 Patriots 16-0).

#### My team (SITE-08)
- Pin button (☆/★ "My team") on team page header and each board row; stored in localStorage `fgs.myTeam` with try/catch (works without storage). Pinned team: highlighted row on board (accent outline + "My team" tag, kept in place — not moved to top, plus a "Jump to my team" link), default highlighted team on mood-over-time chart (unless hash specifies), highlighted entries on records page, and its callouts first in the strip. Unpin available.

### Claude's Discretion
- Card layout, strip design, threshold tuning per research, records page table design (follow 02-UI-SPEC later-phase rules for callout cards, my-team pin, movers strip).

### Deferred Ideas (OUT OF SCOPE)
- OG share images (v2), accounts/sync (out of scope).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INSIGHT-02 | Perception-gap callouts flag teams whose record-implied rank differs sharply from their score rank | Threshold prototype (keep 8, cap 3 per flavor, weeks 4..reg_weeks−1), evidence line definition and numbers on 1999–2021, frozen-evidence firewall pattern (§Pattern 2, §Pitfall 1) |
| INSIGHT-03 | Misery/joy streaks in calendar days | Snapshot dating (verified draft-date table plus last played gameday per week), streak algorithm, as-of rule, seed handling, current active streaks (TEN 751 d, NYJ 408 d, BUF joy 1150 d) |
| INSIGHT-04 | Historical extremes computed, top 10 sanity-checked | Ranking rule (min/max score, tiebreak by REG-mean score), exclude the two seeded expansion team-seasons, RECORDS_CHECK.md format, known-history spot checks |
| INSIGHT-06 | Week-over-week biggest movers computed | score_delta top/bottom 3 with a deterministic tiebreak (34% of weeks tie at the 3rd/4th slot) |
| SITE-05 | Movers strip for the current week | Strip reads `mover_up`/`mover_down` callouts for the displayed week, follows UI-SPEC rule 9 |
| SITE-06 | Records page | `records.json` contract, `#/records` route (currently RESERVED in router.ts), nav entry, UI-SPEC rule 8 tables |
| SITE-08 | Pin "my team" | `myteam.svelte.ts` (exported const object + setter, try/catch storage), BoardRow restructure (a button can't sit inside the row `<a>`), HistoryPage `defaultTeam` hook |
| SITE-09 | Shareable callouts on board and team pages | Per-season `callouts` key, card component, Copy-link 3-tier fallback, stable deep link `#/team/ABBR/season/week` |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Work only inside `feel-good-scorew/`. It's self-contained, with no shared deps and no root manifests.
- Keep it light. Use quick prototypes and skip heavy process (no extensive tests, CI or deploy setup unless asked). Backtest validation is the one exception.
- Stack is locked: Python 3.13 + Polars + NumPy via `uv` in `pipeline/`; Svelte 5 + Vite + plain CSS in `web/`. No new libraries are needed for this phase.
- Data is free sources only, with nflverse as the primary source.
- **Sealed holdout:** 2022–2025 must never feed a fitted or evidence metric. `season_config.TRAIN_LAST_SEASON = 2021` and `HOLDOUT_SEASONS = (2022, 2025)` [VERIFIED: pipeline/src/fgs/season_config.py].
- **Leakage firewall:** `tests/test_leakage.py::test_backtest_not_imported_upstream` forbids `features.py, score.py, mood.py, export.py, explain.py, efficiency.py, pbp.py` from importing `backtest` [VERIFIED: codebase].
- UI-SPEC "Design System for Later Phases": tokens only, no new fonts/weights/decimals/logos, callout card rule 6, pin rule 7, prose/table rule 8, movers rule 9 [VERIFIED: 02-UI-SPEC.md lines 391–412].

## Summary

Everything Phase 8 needs can be computed from data already in the pipeline: `features.parquet` (composite, wins/losses/ties), the scored frame (score, rank, score_delta), `team_games` (points, asof_week, gameday) and `games` (gameday, played). One external fact is missing: NFL draft dates. nflverse `draft_picks` has no date column [VERIFIED: nflreadr data dictionary], so week-0 dates need a small hard-coded table in `season_config.py`. I verified the dates 1999–2026 against Wikipedia's List of NFL drafts.

I prototyped each insight on the current export (scratch scripts are listed under Sources).

- **Perception gap:** a threshold of |gap| ≥ 8 over REG weeks 4..reg_weeks gives a mean of 3.5 callouts per week (median 3, p90 7, max 10), with no callout in 7% of weeks. Capping at 3 per flavor brings the max to 6 and the mean to 3.3. Keep 8 and add the cap.
- **Evidence:** on 1999–2021 the effect is large, symmetric and stable across eras and week buckets. Compared with teams that had the same W-L-T at the same week:
  - "Hopeful" teams went on to play **+3.6 adjusted pts/game better** over the next 8 games and won **55% vs 45%** (n = 504).
  - "Worried" teams played **−3.2 pts/game worse** and won **47% vs 54%** (n = 556).

  The evidence line is honest and quotable.
- **Streaks:** they look historically right. The 2005–09 Raiders lead misery at 1231 days and the 2014–20 Patriots lead joy at 2205 days. The Titans' active misery streak is 751 days, the Jets' is 408, and the Bills have an active joy streak of 1150 days.
- **Team-season extremes:** the 2007 Patriots (16-0) top the happy list and the 2017 Browns (0-16) sit at #2 sad. Two data issues need explicit rules. First, the seeded expansion team-seasons (CLE 1999, HOU 2002, seeded at Elo 1300) dominate the sad list: CLE 1999's composite is −20.5, nearly double the next-worst. Second, 12–14 team-seasons tie at score 0 and 22–25 at score 100, so a tiebreak is mandatory.

The biggest architectural catch: the evidence line needs future games (`backtest.targets`), and `export.py` is forbidden from importing `backtest`. So the evidence must be a **frozen, dev-time artifact**, the same pattern as `weights.yaml`. Compute it with a CLI command on seasons ≤ 2021 only, commit it, and have the export read it.

**Primary recommendation:** Add two pure pipeline modules, `insights.py` (gap callouts, movers, streak callouts, snapshot dating) and `records.py` (extremes, streak records, RECORDS_CHECK.md), plus a dev-only `fgs evidence` command that writes `pipeline/callout_evidence.json` from 1999–2021. Then:
- extend the export with a `callouts` key in each `snapshots/{season}.json`, the latest week in `callouts.json`, and a new `records.json`;
- on the web side add `myteam.svelte.ts`, `CalloutCards`, `MoversStrip`, `RecordsPage` and `copyLink.ts`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Record rank, gap, flags, headline/detail text | Pipeline (Python, `insights.py`) | — | Locked: "All computed in the pipeline". Needs point differential, which isn't in the snapshot rows |
| Base-rate evidence numbers | Pipeline, dev-time (`fgs evidence` → committed JSON) | Export reads it | Uses future games, so it must stay outside the export's import graph (leakage firewall) |
| Movers (top/bottom 3) | Pipeline (`insights.py`) | Browser renders strip | Locked types `mover_up`/`mover_down` in callouts |
| Snapshot dates, streaks, extremes | Pipeline (`insights.py`, `records.py`) | — | Needs the gameday and draft-date tables. Deterministic given `as_of` |
| RECORDS_CHECK.md | Pipeline (written on `fgs refresh`/`export`) | Human/verifier | Locked hand-check artifact |
| Callout cards, movers strip, records page | Browser (Svelte) | Static JSON | Rendering only |
| My-team pin | Browser (localStorage) | — | No accounts (deferred). Per-device only |
| Copy link | Browser (Clipboard API + fallback) | — | Needs a secure context and a user gesture |

## Standard Stack

### Core (no changes, all already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| polars | ≥2.1 (pipeline/pyproject.toml) | All insight computation, `join_asof`, group_by | Already the pipeline's frame library [VERIFIED: pyproject.toml] |
| numpy | ≥2.5.4 | Streak run-length scans | Already used [VERIFIED] |
| svelte | ^5.57.3 | Components, `$state` runes in `.svelte.ts` | Already used (`route.svelte.ts` pattern) [VERIFIED: package.json] |
| vitest | ^5.1.0 | Pure TS logic tests (node env, no jsdom) | 64 tests pass in 90 ms [VERIFIED: ran] |
| pytest | ≥9.2.0 | Pipeline unit tests | 283 pass in 28 s [VERIFIED: ran] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `datetime` (stdlib) | — | ISO dates for streaks | Day arithmetic: `(end - start).days` |
| Web Clipboard API | browser | Copy link | Secure contexts only [CITED: developer.mozilla.org/en-US/docs/Web/API/Clipboard/writeText] |
| Web Storage (localStorage) | browser | `fgs.myTeam` | Wrap every access in try/catch |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hard-coded draft-date table | nflverse draft_picks | No date column exists [VERIFIED: nflreadr dictionary_draft_picks], so it isn't an option |
| Frozen evidence JSON | Compute evidence inside the export | Breaks the leakage firewall (`export.py` can't import backtest), and would recompute training-only numbers on every refresh |
| Per-season `callouts` key | One all-seasons callouts file | All seasons is about 6,700 entries (~1.5 MB). Per-season adds ~40–50 KB to a file the board already loads when scrubbing |
| Pinned team via a Svelte store (`writable`) | `$state` object in `.svelte.ts` | The project already uses the runes pattern (`route.svelte.ts`). Stay consistent |

**Installation:** none. No new packages.

## Package Legitimacy Audit

No external packages are installed in this phase. Everything uses already-locked dependencies (polars, numpy, svelte, vitest, pytest) and browser/stdlib APIs. slopcheck was not run because there's nothing new to check.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                      (dev-time, manual, seasons <= 2021 ONLY)
 team_games + scored ──► fgs evidence ──► backtest.targets(y8) + next-8 win%
   (filtered <=2021)            │          peers = same week & same W-L-T, pooled 1999-2021
                                ▼
                     pipeline/callout_evidence.json  (committed; threshold + weights fingerprint)
                                │
 fgs refresh/export ────────────┼──────────────────────────────────────────────────────┐
   scored frame (score, rank, score_delta, W-L-T, composite)                           │
   team_games (REG points -> cumulative PD by asof_week)                               │
   games (played gameday per (season, asof_week)) + DRAFT_END table -> snapshot dates  │
        │                                                                             │
        ├─► insights.gap_callouts   (week 4..rw-1, |gap|>=8, cap 3/flavor) + evidence ─┤
        ├─► insights.movers         (week>=1, top/bottom 3 by score_delta, tiebreak) ──┤
        ├─► insights.timeline/streaks (dated, seed week-0 dropped, as_of = export date)┤
        │        └─► streak callouts (longest active misery/joy as of each week) ──────┤
        └─► records.extremes + records.streak_records ─► records.json, RECORDS_CHECK.md│
                                                                                      ▼
           snapshots/{season}.json {season, weeks, callouts:{week:[...]}}
           callouts.json  = latest (season, week) list      records.json
                                                                                      │
 Browser ─────────────────────────────────────────────────────────────────────────────┘
   App -> latest/season file -> CalloutCards (worried/hopeful/misery/joy; my team first)
                             -> MoversStrip (mover_up / mover_down)
                             -> MoodBoard rows (+ pin button, my-team badge)
   TeamPage -> season file callouts filtered by team + records.json active streak
   RecordsPage (#/records) -> records.json, highlights myTeam
   myteam.svelte.ts <-> localStorage['fgs.myTeam'] (try/catch)
```

### Recommended Project Structure
```
pipeline/src/fgs/
├── insights.py        # NEW pure: snapshot_dates, record_ranks, gap_callouts, movers, timeline, streaks, streak_callouts
├── records.py         # NEW pure: team_season_extremes, streak_records, records_json, records_check_md
├── evidence.py        # NEW dev-only (imports backtest): compute_evidence(<=2021) -> dict; added to firewall's "downstream" side
├── season_config.py   # + DRAFT_END table, draft_date(season), GAP_THRESHOLD, GAP_CAP, MISERY_MAX=19, JOY_MIN=80
├── export.py          # + callouts key per season, callouts.json latest, records.json (reads callout_evidence.json)
└── cli.py             # + `fgs evidence` subcommand; refresh/export also write pipeline/RECORDS_CHECK.md
pipeline/callout_evidence.json   # committed frozen artifact
pipeline/RECORDS_CHECK.md        # regenerated on export
web/src/lib/
├── myteam.svelte.ts   # NEW $state const object + setMyTeam(); storage injected for tests
├── myteam.ts          # NEW pure: parseStored(value, teams) validation (testable in node)
├── callouts.ts        # NEW pure: orderCallouts(list, myTeam), forWeek(seasonFile, week), forTeam(...)
├── copyLink.ts        # NEW: copyText(text) 3-tier fallback, returns 'copied' | 'manual'
└── records.ts         # NEW pure: format helpers (days, date ranges)
web/src/components/
├── CalloutCards.svelte, CalloutCard.svelte, MoversStrip.svelte, PinButton.svelte, RecordsPage.svelte
```

### Pattern 1: Record rank and gap (pure Polars, leak-free)
**What:** Rank by REG win% (ties count half; 0-0-0 counts as .500), then cumulative REG point differential, then franchise. Gap = record_rank − score_rank.
**Example (prototyped, works on the current data):**
```python
# Source: prototype /private/tmp/.../scratchpad/p8/gap.py
pd_ = (team_games.filter(pl.col("is_reg") & pl.col("played"))
   .group_by("season", "asof_week", "franchise_id")
   .agg((pl.col("points_for") - pl.col("points_against")).sum().alias("d"))
   .sort("franchise_id", "season", "asof_week")
   .with_columns(pl.col("d").cum_sum().over("franchise_id", "season").alias("pd"))
   .select(pl.col("season").cast(pl.Int32), pl.col("asof_week").cast(pl.Int32).alias("week"),
           "franchise_id", "pd"))
s = (scored.sort("week")
   .join_asof(pd_.sort("week"), on="week", by=["season", "franchise_id"], strategy="backward",
              check_sortedness=False)
   .with_columns(pl.col("pd").fill_null(0)))
n = pl.col("wins") + pl.col("losses") + pl.col("ties")
s = s.with_columns(wp=pl.when(n > 0).then((pl.col("wins") + 0.5 * pl.col("ties")) / n).otherwise(0.5))
s = (s.sort(["season", "week", "wp", "pd", "franchise_id"], descending=[False, False, True, True, False])
      .with_columns(record_rank=pl.int_range(1, pl.len() + 1).over("season", "week"),)
      .with_columns(gap=pl.col("record_rank") - pl.col("rank")))
# flags: 4 <= week <= reg_weeks(season) - 1 ; hopeful: gap >= 8 ; worried: gap <= -8
# cap: keep top 3 per (season, week, flavor) by |gap| desc, then rank asc
```
Note that `features.parquet` already has `pd_pg`, but its definition (window/per-game) isn't guaranteed to be season-to-date REG. Compute cumulative REG PD explicitly as above.

### Pattern 2: Frozen evidence (dev-time, holdout-sealed)
**What:** `fgs evidence` filters `team_games` and the scored frame to `season <= TRAIN_LAST_SEASON` **before** calling `backtest.targets(..., ns=(8,))`. It then computes, per flavor (pooled over all |gap| ≥ threshold cases in REG weeks 4..rw−1):
- `n`: the cases with a defined y8
- `d_margin`: mean of (team y8 − peer mean y8)
- `team_win`, `peer_win`: next-8 same-season win% (ties count half, playoffs included, to match y8)

**Peers** are all 1999–2021 team-weeks at the **same week** with the **same W-L-T**, excluding the case itself (leave-one-out). Pooling across seasons gives a median of ~85 peers per case. Same-season-only peers are too thin late in the season and give the same answer (+3.5 / −3.3).

The output is JSON: `{threshold, train_seasons:[1999,2021], weights_fingerprint, hopeful:{n,d_margin,team_win,peer_win}, worried:{...}}`. The export loads it. If the threshold or weights fingerprint disagrees with the current config, it raises ValueError (same style as `_export_weights`), so stale evidence can never ship silently.

**Prototype numbers (current weights, threshold 8):**

| Flavor | n (with target) | Δ adj margin vs peers | Next-8 win% team / peers | Beat peers |
|--------|-----------------|------------------------|---------------------------|-----------|
| hopeful (gap ≥ +8) | 504 | **+3.64** (se 0.30) | 54.7% / 44.8% | 69% |
| worried (gap ≤ −8) | 556 | **−3.15** (se 0.27) | 46.5% / 54.3% | 30% |

The effect is stable across eras (hopeful: +3.33 for 1999–2010, +4.02 for 2011–2021), across week buckets (4–7, 8–11, 12+), and across thresholds (t = 10: +3.55 / −3.10; t = 12: +3.13 / −3.15). A pooled per-flavor number is therefore honest for "a gap this big" [VERIFIED: prototype evid.py/evid2.py on seasons ≤ 2021 only].

**Recommended copy:**
- hopeful: "Teams with a gap this big won {team_win}% of their next 8 games; teams with the same record won {peer_win}% ({n} cases, 1999–2021)."
- worried: same structure.
- Alternative points framing: "…played {abs(d)} points per game {better|worse} than teams with the same record over their next 8 games ({n} cases since 1999)."

Win% reads better to fans. The planner can pick either; both numbers live in the JSON.

**Caveat (state it on the methodology page or in a code comment):** 1999–2021 is also the window the score weights were fit on, so this base rate is in-sample. It describes history; it isn't an out-of-sample test.

### Pattern 3: Snapshot dating and streaks
- `week_date(season, w)` for w ≥ 1 is the max `gameday` of **played** games with `asof_week == w`. This handles partial latest weeks, and all weeks are present and strictly increasing [VERIFIED: prototype, 0 missing and 0 non-increasing].
- `week_date(season, 0)` is `DRAFT_END[season]`, the **last day** of the draft (the week-0 snapshot is post-draft per Phase 7). Fallback is Sept 1, **clamped to ≤ as_of**.
- Timeline per franchise: all (season, week) rows sorted by date. **Drop week-0 rows of seeded team-seasons** (`season_config.SEEDS`: CLE 1999, HOU 2002). Those rows reflect an assumed 1300 seed, not a result.
- Run-length scan with `cond = score <= 19` (misery) or `score >= 80` (joy):
  - `start` = date of the first row in the run
  - `end` = date of the first row that breaks it, or null if active
  - `days = (end or as_of) - start`
  - `as_of = date(generated_at[:10])`, injected as a parameter so tests are deterministic.
- **Streak callouts per week:** for each (season, week), the single longest **active** misery and joy streak as of that week's date, only if ≥ 100 days (so at most 2 per week). Milestone-crossing callouts were rejected because they pile up at week 0 (up to 14 in one week) [VERIFIED: prototype mov.py].

### Pattern 4: Team-season extremes
- Use rows with 1 ≤ week ≤ reg_weeks(season) (REG only; excludes week 0 and postseason drift) and exclude seeded team-seasons.
- **Saddest:** sort by (min score asc, mean REG score asc, min composite asc, season, franchise).
- **Happiest:** sort by (max score desc, mean REG score desc, max composite desc).
- Report the "when" as the week/date of the first time the min/max was reached.
- Add the final REG record from the last REG-week row.

**Prototype top 10 (current data):**
- Saddest: 2013 JAX 4-12, **2017 CLE 0-16**, 2021 JAX 3-14, 2014 JAX 3-13, 2016 CLE 1-15, 2009 DET 2-14, 2000 CLE 3-13, 2002 CIN 2-14, 2005 SF 4-12, 2008 LA 2-14.
- Happiest: **2007 NE 16-0**, 2022 BUF 13-3, **2011 GB 15-1**, 2007 IND 13-3, 2005 IND 14-2, … 2023 SF, 2015 NE, 2019 NE, 2004 PHI, 2013 SEA.

The **2008 Lions (0-16) rank ~14th** under the locked "min score" rule. Their minimum is 1, not 0, because they entered 2008 at Elo 1440, and they rank 9th by season-mean score. RECORDS_CHECK.md must carry a sanity note explaining this, since the verifier is told to check against "2008 Lions 0-16" (see Open Question 4).

### Pattern 5: My team in Svelte 5
```ts
// web/src/lib/myteam.svelte.ts. Source: svelte.dev/docs/svelte/$state ("Passing state across modules")
const KEY = 'fgs.myTeam'
function readStored(): string | null {
  try { return typeof localStorage === 'undefined' ? null : localStorage.getItem(KEY) } catch { return null }
}
// Exported const object: mutate properties, never reassign (Svelte rule for exported state).
export const myTeam = $state<{ abbr: string | null }>({ abbr: readStored() })
export function setMyTeam(abbr: string | null): void {
  myTeam.abbr = abbr
  try { abbr ? localStorage.setItem(KEY, abbr) : localStorage.removeItem(KEY) } catch { /* in-memory only */ }
}
// Optional cross-tab sync:
if (typeof window !== 'undefined') window.addEventListener('storage', (e) => { if (e.key === KEY) myTeam.abbr = e.newValue })
```
Validate against `meta.teams` at read time (a pure `validTeam(abbr, meta)` in `myteam.ts`). A stale or garbage value then behaves as "no team" and never throws.

### Pattern 6: Copy link with fallback
```ts
// web/src/lib/copyLink.ts. Clipboard API is secure-context only and rejects with NotAllowedError
// [CITED: developer.mozilla.org/en-US/docs/Web/API/Clipboard/writeText]
export async function copyText(text: string): Promise<'copied' | 'manual'> {
  try {
    if (window.isSecureContext && navigator.clipboard?.writeText) { await navigator.clipboard.writeText(text); return 'copied' }
  } catch { /* fall through */ }
  try {
    const ta = document.createElement('textarea')
    ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0'
    document.body.appendChild(ta); ta.select()
    const ok = document.execCommand('copy'); ta.remove()
    if (ok) return 'copied'
  } catch { /* fall through */ }
  return 'manual' // caller shows a readonly <input> with the URL preselected + "Press Ctrl+C / ⌘C to copy"
}
// deep link: `${location.origin}${location.pathname}${teamHash(c.franchise, c.season, c.week)}`
```
Announce the result with a `role="status"` line: "Link copied" or "Copy the link below". Use the stable `#/team/ABBR/{season}/{week}` hash, not `#/` (latest), so the shared link keeps showing the moment it described.

### JSON contract additions
```jsonc
// Callout (every type)
{ "type": "worried", "season": 2026, "week": 9, "franchise": "SEA",
  "headline": "5-4, but better days are coming",          // copy per type below
  "detail": "Their record ranks 13th. Their score ranks 4th.",
  "evidence": "Teams with a gap this big won 55% of their next 8 games; teams with the same record won 45% (504 cases, 1999–2021).",
  // extra (optional, for ordering/rendering; planner may keep or drop):
  "gap": 9, "record_rank": 13, "score_rank": 4, "score_delta": null, "days": null, "start": null }
// snapshots/{season}.json: { season, weeks, callouts: { "9": [Callout...] } }  (only weeks that have any)
// callouts.json: Callout[] for meta.latest (season, week)       (keeps the locked flat-array shape)
// records.json:
{ "as_of": "2026-11-11",
  "saddest":  [{ "season", "franchise", "score", "week", "date", "wins", "losses", "ties", "mean" }],  // 10
  "happiest": [...],                                                                                     // 10
  "misery":   [{ "franchise", "start", "end", "days", "active", "from": "2024 Week 7", "to": "2026 Week 9" }], // 10
  "joy":      [...],
  "active":   { "TEN": { "kind": "misery", "start": "2024-10-21", "days": 751 }, ... },  // for team pages
  "excluded": [{ "season": 1999, "franchise": "CLE", "reason": "expansion seed" }, { "season": 2002, "franchise": "HOU", ... }] }
```
Size estimate: about 46 gap + 126 mover + 44 streak callouts per season at ~150–300 B each, so ~40–50 KB added to each 344 KB season file. `records.json` is ~10 KB. `callouts.json` is ~3 KB.

**Headline copy** (nick from meta.teams; record via existing `formatRecord` rules, with T only when ties > 0):
- worried: "{W-L}, but you should feel worried"; detail: "The {Nick} have the {ord(record_rank)}-best record but the {ord(score_rank)}-best score."
- hopeful: "{W-L}, but better days are coming"; same detail shape.
- mover_up / mover_down: "{Nick} +{d}" / "{Nick} −{d}"; detail: "{prev label} → {label}". The strip renders the Delta component, not prose.
- misery: "{Nick} fans have been miserable for {days} straight days"; detail: "Score under 20 since {Mon D, YYYY}."
- joy: "{Nick} fans have been buying the jersey for {days} straight days"; detail: "Score 80 or higher since {Mon D, YYYY}."

### Anti-Patterns to Avoid
- **Importing backtest from export/insights:** this violates the firewall and `test_backtest_not_imported_upstream`. Add `insights.py` and `records.py` to that test's list.
- **Ranking extremes by integer score alone:** there are 12–14 ties at 0 and 22–25 at 100, so the output order would be arbitrary.
- **A pin `<button>` inside the BoardRow `<a>`:** interactive content inside an anchor is invalid HTML and clicks bubble into navigation. Restructure `<li>` to hold `<a class="row">` and a sibling `<PinButton>` placed over the grid.
- **"Jump to my team" via a `#row-ABC` fragment:** the app uses hash routing, so a fragment would be parsed as an invalid route. Use a button that calls `document.getElementById('row-ABC')?.scrollIntoView({block:'center'})` and focuses the row link.
- **Client-clock streak counting:** keep `days` pipeline-computed for deterministic tests and agreement with the records page. Re-export updates it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Next-N adjusted margin | A new future-games loop | `backtest.targets(team_games, snaps, ns=(8,))` inside `fgs evidence` | Already the locked target, already tested, already handles <2 remaining games |
| Season-to-date record | Recount W-L | Snapshot `wins/losses/ties` (REG-only, asof-keyed) | Matches the board exactly |
| Score/rank/delta | Recompute | `mood.score_frame` output | Single source of truth |
| Date formatting | Custom strings | `Intl.DateTimeFormat('en-US', …)` (UI-SPEC copy rules) | Locale-safe |
| Clipboard | Custom selection hacks only | Clipboard API first, then `execCommand` fallback, then manual input | Secure-context gating [CITED: MDN] |
| Atomic write of new files | Separate writer | Existing `write_export` (records.json etc. go into `files` dict) | Atomic swap already handles crashes |

## Runtime State Inventory

Not a rename/refactor phase. One relevant runtime item: **browser localStorage key `fgs.myTeam`** is new (nothing to migrate). Nothing found in stored data, live service config, OS-registered state, secrets or build artifacts (verified: static site, no services).

## Common Pitfalls

### Pitfall 1: Evidence leaking the holdout or breaking the firewall
**What goes wrong:** Evidence gets computed over all seasons, or `export.py` imports `backtest`.
**How to avoid:** Have `evidence.py` filter `season <= TRAIN_LAST_SEASON` before `targets()`. Write a test that sets every 2022+ result to 60-0 and asserts identical evidence output. Freeze the output in the committed JSON, and extend the firewall test list.
**Warning signs:** The evidence `n` changes after a refresh that only adds 2026 games.

### Pitfall 2: Expansion seeds dominating
**What goes wrong:** CLE 1999 (composite −20.5 at week 0 and −20.0 at week 1, vs −12.1 for the next team) is #1 saddest. HOU 2002 is #3. CLE 1999 week 0 is the only 1999 week-0 score that isn't 55.
**How to avoid:** Exclude `SEEDS` team-seasons from extremes, list them in `records.json.excluded` with a footnote, and drop seeded week-0 rows from streak timelines. HOU's 2002–04 streak then starts 2002-09-09 (770 d, #8) and CLE's 1999–2001 streak 1999-09-13 (756 d, #12). Both are genuine results-driven misery, so annotate them in RECORDS_CHECK rather than removing them.

### Pitfall 3: Ties at the 0/100 clip
Integer scores clip, so use the tiebreak chain in Pattern 4. Without it the Python sort order decides the list.

### Pitfall 4: Draft-date gaps for new seasons
When the next season's schedule lands (around May), a week-0 row appears. If `DRAFT_END` lacks that season, the Sept 1 fallback is in the future, giving negative days. Clamp the fallback to `as_of`, and add a `checks.py` coverage check: every season in the data has a draft date, a warning for the current season and a hard fail for past ones.

### Pitfall 5: Gap callouts in the final REG week and playoffs
At week = reg_weeks no REG games remain, y8 is null for most teams, and "better days are coming" means next year. In playoffs the record is frozen. Restrict to 4 ≤ week ≤ reg_weeks − 1. Partial latest week: callouts compute normally on what has been played.

### Pitfall 6: Movers ties and postseason drift
In 34% of weeks the 3rd and 4th risers tie on score_delta. Tiebreak: |score_delta| desc, |rank_delta| desc, rank asc, franchise asc. Composite can drift for teams that didn't play (opponent ratings feed `sow`), but the median postseason |delta| is 0. Require delta ≠ 0, and if fewer than 3 qualify show fewer (4% of weeks have fewer than 3 positive deltas).

### Pitfall 7: Hysteresis label vs score threshold
Misery is locked as score < 20, but the label uses hysteresis, so a team at 19 can still read "Checking the draft order" right after dropping. Copy should say "Score under 20 since …" rather than naming the label, so the two never visibly contradict.

### Pitfall 8: Storage throws
In Safari private mode or with storage disabled, `localStorage` access can throw SecurityError, and in the vitest node env it's undefined. Guard every access (`typeof` check plus try/catch). Validate the stored abbr against `meta.teams`.

### Pitfall 9: Fragile top-10 boundaries
Positions 8–12 of the misery list are within 14 days of each other (770, 769, 763, 756, 756). Any weight change reshuffles them. RECORDS_CHECK.md is regenerated on each export, and the verifier re-reads it; never hard-code expected list membership in tests.

## Code Examples

### Streak scan (prototype-proven)
```python
# Source: prototype scratchpad/p8/streak.py (adapted to pure function form)
def runs(dates: list[date], scores: np.ndarray, cond, as_of: date) -> list[dict]:
    ok, out, i, n = cond(scores), [], 0, len(dates)
    while i < n:
        if not ok[i]:
            i += 1; continue
        j = i
        while j + 1 < n and ok[j + 1]:
            j += 1
        end = dates[j + 1] if j + 1 < n else None
        out.append({"start": dates[i], "end": end, "active": end is None,
                    "days": ((end or as_of) - dates[i]).days, "i": i, "j": j})
        i = j + 1
    return out
```

### Draft-date table (verified)
```python
# season_config.py. Last day of each draft [CITED: en.wikipedia.org/wiki/List_of_NFL_drafts]
DRAFT_END = {1999:"04-18",2000:"04-16",2001:"04-22",2002:"04-21",2003:"04-27",2004:"04-25",2005:"04-24",
  2006:"04-30",2007:"04-29",2008:"04-27",2009:"04-26",2010:"04-24",2011:"04-30",2012:"04-28",2013:"04-27",
  2014:"05-10",2015:"05-02",2016:"04-30",2017:"04-29",2018:"04-28",2019:"04-27",2020:"04-25",2021:"05-01",
  2022:"04-30",2023:"04-29",2024:"04-27",2025:"04-26",2026:"04-25"}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `document.execCommand('copy')` | `navigator.clipboard.writeText` (secure context) | Clipboard API widely shipped | Keep execCommand only as fallback |
| Svelte stores for shared state | `$state` in `.svelte.ts`, exported as a const object | Svelte 5 | Matches `route.svelte.ts` [CITED: svelte.dev/docs/svelte/$state] |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Using the draft's **last** day (not first) for week-0 dates matches "post-draft" intent | Pattern 3 | Streak lengths shift by 2–3 days. Cosmetic |
| A2 | `features.pd_pg` isn't season-to-date REG PD, so PD is computed explicitly | Pattern 1 | None if computed explicitly as recommended |
| A3 | Win%-based evidence copy reads better to fans than adjusted margin | Pattern 2 | Copy choice only; both numbers are in the JSON |
| A4 | Streak callouts with a ≥ 100-day floor are a reasonable per-week cadence | Pattern 3 | More or fewer cards; tune the constant |
| A5 | Excluding SEEDS team-seasons from extremes is acceptable to the user | Pitfall 2 | If wrong, CLE 1999 becomes #1 saddest by a seed artifact |

## Open Questions (RESOLVED)

1. **Threshold tuning:** RESOLVED. Keep |gap| ≥ 8 (mean 3.5/week, within the 2–5 target) and add a **cap of 3 per flavor per week** (max 6, mean 3.3). Eligible weeks are 4..reg_weeks−1. Thresholds of 9 or 10 leave 13–26% of weeks empty.
2. **Peer comparison:** RESOLVED. Peers are all 1999–2021 team-weeks at the same week with the same W-L-T (leave-one-out). The metric is next-8 same-season adjusted margin (`backtest.targets` y8) plus next-8 win%. The number is pooled per flavor, frozen to `callout_evidence.json` via a dev-only `fgs evidence` command, and the export fails loudly if it's stale.
3. **Expansion seeds:** RESOLVED. Exclude CLE 1999 and HOU 2002 from team-season extremes (listed in `excluded`, with a footnote on the records page). Drop their seeded week-0 rows from streak timelines; their week-1+ misery still counts.
4. **The 2008 Lions aren't top-10 saddest under "min score":** RESOLVED. Keep the locked min/max rule with the tiebreak (min score, then mean REG score, then composite). RECORDS_CHECK.md adds a "Notable non-entries" section showing 2008 DET (#14, min score 1, mean 2.4) and the reason, so the verifier sees it was checked. 2017 CLE 0-16 is #2 saddest, and 2007 NE 16-0 is #1 happiest.
5. **Storage of past-week callouts:** RESOLVED. Use a `callouts` key in each `snapshots/{season}.json` (week → list). `callouts.json` stays the flat latest-week array (locked shape) for the initial board load.
6. **Active-streak "as of":** RESOLVED. The pipeline computes days through `as_of = generated_at` date. The team page reads `records.json.active[ABBR]`. The per-week streak callouts use that week's date, so they're reproducible.
7. **Which callouts go in the card strip vs the movers strip:** RESOLVED. Cards show worried/hopeful/misery/joy, with my-team's first, then |gap| desc, then streak days desc. Show up to 6 cards with a "Show all" `<details>` if there are more. The movers strip renders mover_up/mover_down.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv + Python 3.13 | pipeline | ✓ | (uv run works; 283 tests pass) | — |
| Node | web build/test | ✓ | default shell v20.19.0; v22.23.3 and v24.20.0 installed via nvm | package.json engines says ≥22.12. vitest passes on 20, but use `nvm use 22` for `npm run build` if Vite complains |
| Derived parquet | prototypes/tests | ✓ | regenerated 14:03 today | `uv run fgs refresh` |
| Network | none required (draft dates hard-coded) | — | — | — |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥9.2 (pipeline), vitest ^5.1 node env (web) |
| Config file | `pipeline/pyproject.toml [tool.pytest.ini_options]`; web uses `vite.config.ts` defaults |
| Quick run command | `cd pipeline && uv run pytest -q tests/test_insights.py tests/test_records.py tests/test_evidence.py` ; `cd web && npx vitest run src/lib/callouts.test.ts src/lib/myteam.test.ts` |
| Full suite command | `cd pipeline && uv run pytest -q` (~28 s) ; `cd web && npx vitest run && npm run check` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INSIGHT-02 | record_rank tiebreak (win% → PD → id); 0-0 = .500; gap sign → flavor; week window 4..rw−1; cap 3/flavor | unit (synthetic frame) | `uv run pytest -q tests/test_insights.py -k gap` | ❌ Wave 0 |
| INSIGHT-02 | Evidence ignores seasons > 2021 (fake 60-0 future results give identical JSON); export raises on stale threshold/fingerprint | unit | `uv run pytest -q tests/test_evidence.py` | ❌ Wave 0 |
| INSIGHT-02 | Firewall: insights.py/records.py don't import backtest | unit | `uv run pytest -q tests/test_leakage.py -k backtest_not_imported` (extend list) | ✅ extend |
| INSIGHT-03 | Snapshot dates: draft table covers every season; dates strictly increase per team; fallback clamped to as_of | unit + real-data check | `uv run pytest -q tests/test_insights.py -k date` | ❌ Wave 0 |
| INSIGHT-03 | Streak scan: active vs ended, cross-season runs, seeded week-0 dropped, days = end−start | unit | `uv run pytest -q tests/test_insights.py -k streak` | ❌ Wave 0 |
| INSIGHT-04 | Extremes: one per team-season, SEEDS excluded, tiebreak deterministic, 10 each | unit | `uv run pytest -q tests/test_records.py` | ❌ Wave 0 |
| INSIGHT-04 | RECORDS_CHECK.md written with 4 lists + notable non-entries | manual (verifier reads vs known history) | `uv run fgs export && cat RECORDS_CHECK.md` | — |
| INSIGHT-06 | Movers top/bottom 3, delta ≠ 0, tiebreak, week ≥ 1 only | unit | `uv run pytest -q tests/test_insights.py -k movers` | ❌ Wave 0 |
| SITE-05/09 | Export: `callouts.json` = latest list with locked keys; each season file has `callouts`; types in allowed set | unit | `uv run pytest -q tests/test_export.py` (update `== []` assertion) | ✅ update |
| SITE-06 | `#/records` parses (remove from RESERVED); records.json shape | unit | `npx vitest run src/lib/router.test.ts` | ✅ extend |
| SITE-08 | myTeam: invalid/garbage stored value → null; storage throwing → in-memory works; orderCallouts puts my team first | unit (injected fake storage) | `npx vitest run src/lib/myteam.test.ts src/lib/callouts.test.ts` | ❌ Wave 0 |
| SITE-08/09 | Pin toggles aria-pressed, row not reordered, Copy link status message, clipboard fallback | manual (browser, http://localhost via vite dev, plus a LAN-IP non-secure origin to exercise the fallback) | — | — |

### Sampling Rate
- **Per task commit:** the quick run command for the touched side.
- **Per wave merge:** full pytest + vitest + `npm run check`.
- **Phase gate:** full suites green, RECORDS_CHECK.md reviewed, `fgs evidence` output committed and matching the export fingerprint.

### Wave 0 Gaps
- [ ] `pipeline/tests/test_insights.py`: gap, dates, streaks, movers (synthetic frames from `conftest.make_games` where possible)
- [ ] `pipeline/tests/test_records.py`: extremes and exclusions
- [ ] `pipeline/tests/test_evidence.py`: holdout seal and staleness guard
- [ ] `web/src/lib/myteam.test.ts`, `web/src/lib/callouts.test.ts`
- [ ] Update `tests/test_export.py:72` (`callouts.json == []`) and the `test_leakage.py` firewall list

## Security Domain

`security_enforcement` is `false` in `.planning/config.json`, so the section is omitted except for one note. All callout text is pipeline-generated and must render via Svelte text interpolation (never `{@html}`). The localStorage value must be validated against `meta.teams` before use in hashes or class names.

## Sources

### Primary (HIGH confidence)
- Codebase: `pipeline/src/fgs/{export,mood,explain,backtest,snapshots,season_config,asof}.py`, `tests/test_leakage.py`, `web/src/lib/{data,types,router,route.svelte,history}.ts`, `web/src/components/{BoardRow,HistoryPage,SiteHeader}.svelte`, `02-UI-SPEC.md` §Design System for Later Phases
- Prototypes (this session, current export plus derived parquet), all in `/private/tmp/claude-501/-Users-noahmanion-Dropbox-code-idea-graveyard-feel-good-scorew/e9aca8f6-0367-4770-bd90-f3eef6a0daef/scratchpad/p8/`: `gap.py`, `evid.py`, `evid2.py`, `ex.py`, `streak.py`, `ext.py`, `ext2.py`, `ext3.py`, `mov.py`
- https://nflreadr.nflverse.com/articles/dictionary_draft_picks.html: no draft-date column
- https://en.wikipedia.org/wiki/List_of_NFL_drafts: draft dates 1999–2026
- https://developer.mozilla.org/en-US/docs/Web/API/Clipboard/writeText: secure context, NotAllowedError
- https://svelte.dev/docs/svelte/$state: exporting state from `.svelte.ts` modules

### Secondary / Tertiary
- None needed.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. No new dependencies.
- Architecture: HIGH. Firewall constraint verified in tests; storage sizes estimated from the real files.
- Numbers (rates, evidence, lists): MEDIUM. Prototyped on today's weights, and they will move as factors change. The structure and conclusions (effect sign and size ~±3 pts, ~±10 pp) were stable across thresholds, eras and week buckets.
- Pitfalls: HIGH. Each one was observed in the data.

**Research date:** 2026-11-11
**Valid until:** 2026-12-11, or until weights.yaml changes (then rerun `fgs evidence` and re-read RECORDS_CHECK.md)

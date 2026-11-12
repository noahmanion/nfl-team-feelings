# Phase 3: Backtest Harness & Additive Score - Context

**Gathered:** 2026-11-11
**Status:** Ready for planning
**Mode:** Autonomous — recommended answers auto-accepted (user granted full autonomy)

<domain>
## Phase Boundary

Build the evaluation harness (target, baselines, walk-forward, leakage test) and convert the score into an additive composite (Σ weight × per-snapshot z-score, contributions stored) with its first two non-Elo factors — current-season record and rolling last-16 record. Add the mood-over-time chart page. Later factors (Phases 4–5), final weight freeze + holdout (Phase 6) are out of scope; this phase must NOT look at 2022–2025 outcomes when choosing weights.

</domain>

<decisions>
## Implementation Decisions

### Backtest target (BACK-01) — written into README BEFORE any tuning
- Primary target per (season, week, franchise) snapshot: mean **adjusted margin** over the team's next N games within the same season (regular season + playoffs), N ∈ {4, 8} (N=8 is the headline; 4 reported too). Adjusted margin for a game = actual point margin + (opponent pre-game Elo − 1505)/25 − (signed HFA Elo)/25, i.e. adjusted ONLY for opponent strength and home field (NOT the team's own rating — that would be circular). [Revised per 03-RESEARCH A1: own-Elo version made plain Elo Spearman ≈0.02.] Snapshots with fewer than 2 remaining games are excluded from that N's evaluation.
- Primary metric: Spearman rank correlation and R² of the candidate score vs target, pooled over test seasons, plus per-season values. Secondary: next-game Brier score from a logistic map of score difference (fit on training seasons only).
- Reporting buckets: early (wk 1–6), mid (7–12), late (13+), and week 0 (across-offseason) separately.

### Walk-forward & data splits
- Walk-forward by season: for test season S, anything fit (z-score stats are per-snapshot so need no fitting; interim weights; logistic maps) uses only seasons < S. First test season 2003 (training 1999–2002).
- **Holdout 2022–2025 is sealed** in this phase: the backtest command defaults to test seasons 2003–2021; 2022+ evaluation requires an explicit `--include-holdout` flag that Phase 6 uses once. 2026 (in progress) is never a test season.

### Baselines (BACK-02)
- `fgs backtest` prints a table (per-N, per-bucket) for: plain Elo, season-to-date win % (REG), last-16 win %, season-to-date point differential per game, and the Vegas spread (next-game Brier only, as the ceiling; `spread_line` positive = home favored). Plain Elo next-game Brier should land ≈ 0.22–0.23 (Phase 1 research measured 0.2196).
- Output also written to `pipeline/data/derived/backtest.json` (consumed by Phase 6 methodology page; shape: metrics per candidate × N × bucket, plus per-season series).

### Leakage test (BACK-03)
- Pytest that appends fake future games (after the latest played game) to the schedule, rebuilds, and asserts every existing snapshot's factor values, contributions, and score are unchanged; also a test that truncating the future (dropping games after week W) leaves snapshots ≤ W unchanged.

### Additive score (MODEL-14) + first factors (MODEL-03, MODEL-04)
- New `features.py` builds per-snapshot raw factor values as-of each (season, week) using only games with asof_week ≤ week: `elo` (rating), `season_record` (REG win% with ties 0.5; week 0 → 0.5), `last16` (win% over the last 16 played games including prior season(s), REG+playoffs, ties 0.5).
- Percentile reference for the 0–100 score is FIXED to snapshots from seasons 1999–2021 (wk0+REG), so future games can never change past scores (leakage) and historical scores stop drifting on refresh. Board rank = composite order. [Revised per 03-RESEARCH A2.]
- Zero-variance guard: if a factor has zero spread in a snapshot (e.g. season_record at week 0), its z = 0 for all teams.
- `score.py`: z-score each factor across the teams in that (season, week) snapshot; composite = Σ w_f · z_f; store per-factor `contrib_f = w_f · z_f` columns; composite feeds the existing percentile → 0–100 score → mood bands pipeline (mood.py unchanged in behavior; the percentile reference is now the composite).
- Interim weights live in `pipeline/weights.yaml` (committed): fit by walk-forward Ridge (standardized inputs, alpha via CV within training seasons) on 1999–2021 against the N=8 target, then rounded to 2 decimals by hand-rule (code proposes, file is the source of truth). Phase 6 refits/freezes after all factors exist. Each factor addition records its backtest delta (vs the composite without it) in `pipeline/BACKTEST_LOG.md` (append-only table: date, factor, ΔSpearman N=8, ΔR², fitted sign).
- JSON contract additions (backwards-compatible): `meta.score_kind = "composite"`, `meta.factors` = [{key, label, weight, description}]; season rows get `contribs: {factor_key: number rounded 2dp}`; history.json unchanged shape (score is now composite-based).

### Mood-over-time chart (SITE-03)
- New route `#/history` (reserved in Phase 2 router) with a simple top nav ("Board" · "Mood over time").
- Observable Plot 0.6.19 line chart from `history.json`: x = time index (season-week), y = score fixed 0–100, all teams as thin muted lines, one highlighted team (selector; default = current #1; hash `#/history/{ABBR}`) in its team color with label, plus mood-band background stripes. Lines break at season boundaries (gap between seasons, using Plot's `z`/NaN gap). Season ticks on x-axis. Phone-width: horizontally fit (no page scroll), fewer ticks.
- Follow UI-SPEC "Design System for later phases" rules from Phase 2 (tokens, no new fonts/weights, no logos, no decimals in UI).

### Claude's Discretion
- Exact Ridge alpha grid, logistic fit method, module layout, chart sizing, how team selector is presented (select vs chips).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- pipeline: `games` (team_games long table with asof_week), `elo.replay` (pre-game elo per game available), `snapshots.build_grid` (season, week, franchise_id, elo, W-L-T), `mood.py` (percentile, bands, hysteresis), `export.py` (JSON contract), `cli.py` (`build`, `check`, `elo`, `export`, `refresh`), `asof.py`.
- web: Svelte 5 + Vite, `lib/router.ts` (reserved routes incl. `#/history`), `lib/data.ts`, `lib/format.ts`, components Scrubber/MoodBoard/BoardRow/StatusPanel, CSS tokens in `app.css`.

### Established Patterns
- Polars, argparse subcommands, calendar-robust pytest with real-cache skips; vitest + svelte-check + vite build gates; Node 22 via nvm.

### Integration Points
- `export.py` must read composite + contribs; `refresh` must run features→score before export. New CLI `fgs backtest`.

</code_context>

<specifics>
## Specific Ideas

- The chart is the first place the "600 days of misery" story becomes visible; keep it legible with 32 lines (muted greys, one highlight).

</specifics>

<deferred>
## Deferred Ideas

- Team deep-dive page & factor bars (Phase 4); methodology page rendering backtest.json (Phase 6); final weight freeze + holdout (Phase 6).

</deferred>

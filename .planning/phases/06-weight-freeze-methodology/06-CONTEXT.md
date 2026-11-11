# Phase 6: Weight Freeze & Methodology - Context

**Gathered:** 2026-11-11
**Status:** Ready for planning
**Mode:** Autonomous — recommended answers auto-accepted (user granted full autonomy)

<domain>
## Phase Boundary

Freeze the final in-season weights (all 11 factors from Phases 3–5), evaluate them ONCE on the sealed 2022–2025 holdout with season-level bootstrap confidence intervals, and ship a methodology page that explains every factor and shows the evidence vs baselines. No new factors. Offseason draft reaction is Phase 7.

</domain>

<decisions>
## Implementation Decisions

### Pre-registration (written & committed BEFORE the holdout is run)
- `pipeline/PREREGISTRATION.md` committed first: final model = all 11 factors (elo, season_record, last16, mov, sow, streak, luck, epa_traj, qb_trend, vs_exp, po_trend), Ridge on per-snapshot standardized inputs fit on ALL training seasons 1999–2021 against the N=8 adjusted-margin target, alpha chosen by the existing walk-forward CV procedure on training only, weights rounded to 2 decimals. Success criterion: holdout (2022–2025) Spearman N=8 of the frozen composite > plain Elo, with 95% season-level bootstrap CI on the difference reported. Secondary: next-game Brier vs Elo and vs spread. No factor pruning, no refits after seeing holdout results (MODEL-15: data decides weights/signs, including negative/≈0 streak & luck & last16).
- If the holdout fails the criterion, the result is reported honestly on the methodology page and in the README (no re-tuning); verification records it as a gap for the user rather than silently re-fitting.

### Weight freeze (BACK-04)
- `fgs freeze` (or `fgs backtest --propose-weights --final`) writes `pipeline/weights.yaml` with `frozen: true`, `fit_seasons: 1999-2021`, `alpha`, `target: adjusted_margin_n8`, `fitted_at`, and per-factor weight + sign + training-fold sign consistency (k/19). Refresh/export only read it; any code path that refits refuses when `frozen: true` unless `--unfreeze` is passed.

### One-time holdout (BACK-05, BACK-06)
- `fgs holdout` evaluates the frozen weights on 2022–2025 (walk-forward style: features/targets as-of, no refits), plus all baselines (Elo, season W%, last-16, point diff, spread Brier), at N=8 and N=4, by bucket.
- Season-level bootstrap: 2,000 resamples of holdout seasons' team-snapshots grouped by season (block bootstrap by season; with only 4 holdout seasons also report a team-season cluster bootstrap) → 95% CIs for composite Spearman, Elo Spearman, and their difference; same for Brier.
- Writes `pipeline/data/derived/holdout.json` and a committed `pipeline/HOLDOUT_RESULT.md` (human-readable table + every factor's fitted sign). Guard: refuses to run if `HOLDOUT_RESULT.md` exists unless `--force` (documented as "don't").

### Methodology page (SITE-07)
- Route `#/methodology`, linked in the top nav ("Board · Mood over time · How it works").
- Export `methodology.json` (pipeline): factors (key, label, description, weight, sign, fold-sign consistency, backtest Δ when added from BACKTEST_LOG), target definition text, training/holdout split, walk-forward metrics (2003–2021) and holdout metrics with CIs for composite + baselines, notes.
- Content sections: (1) "What the score is" (percentile of an additive composite vs 1999–2021 team-weeks; mood bands); (2) "The factors" table: label, what it measures, weight (signed, 2dp), "helps/hurts the score when high", backtest Δ; (3) "Does it work?" chart: Spearman N=8 by candidate (Elo, season W%, last-16, point diff, composite) for walk-forward and holdout with CI whiskers, plus Brier incl. spread ceiling; (4) "Honest notes": momentum mostly doesn't predict (streak/luck/last16 signs), efficiency trend ≈0 given Elo, vs_exp depends on Vegas totals 2003–2020 and uses model expectations elsewhere, 1999–2000 pbp low-confidence, simplified playoff tiebreakers, scores are not betting advice.
- Chart with Observable Plot (already installed), following 02-UI-SPEC later-phase rules; no decimals in headline numbers except weights/metrics in the table (allowed: methodology is the one place for precise numbers).
- README updated with the holdout result.

### Claude's Discretion
- Exact bootstrap implementation, page layout, wording of honest notes (must be factual to logged numbers).

</decisions>

<code_context>
## Existing Code Insights

- `backtest.py` (walk-forward, Ridge, baselines, `--propose-weights`, `--include-holdout`), `weights.yaml`, `BACKTEST_LOG.md`, `backtest.json` (derived), `score.py`, `export.py`, web router (reserved `#/methodology`), SiteHeader nav, Plot charts.

</code_context>

<specifics>
## Specific Ideas

- Title the chart "Does it work?" and lead with the plain-language answer from HOLDOUT_RESULT (e.g., "Yes, slightly: …" or "Not on 2022–25: …").

</specifics>

<deferred>
## Deferred Ideas

- Factor pruning / model selection (would need a fresh holdout), hand-entered 2021+ Vegas totals (v2).

</deferred>

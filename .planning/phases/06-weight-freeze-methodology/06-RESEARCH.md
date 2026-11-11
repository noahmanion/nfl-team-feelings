# Phase 6: Weight Freeze & Methodology - Research

**Researched:** 2026-11-11
**Domain:** Pre-registered model freeze, one-time holdout evaluation with cluster/block bootstrap CIs, static methodology page (Svelte 5 + Observable Plot)
**Confidence:** HIGH for mechanics and bootstrap behavior (prototyped on training seasons). MEDIUM for UI details (not rendered in this session).

> **Holdout discipline in this research:** no composite metric on 2022–2025 was computed or viewed. Every number below comes from 1999–2021 training data. The stand-in "holdout" is 2018–2021, with weights fit on 1999–2017. Prototypes are in `/private/tmp/claude-501/-Users-noahmanion-Dropbox-code-idea-graveyard-feel-good-scorew/e9aca8f6-0367-4770-bd90-f3eef6a0daef/scratchpad/p6/` (`boot.py`, `calib.py`, `brier.py`, `logparse.py`). They reuse the Phase 5 prototype features (`scratchpad/p5/data/feats_all.parquet`, filtered to `season <= 2021`).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Pre-registration (written & committed BEFORE the holdout is run)
- `pipeline/PREREGISTRATION.md` committed first: final model = all 11 factors (elo, season_record, last16, mov, sow, streak, luck, epa_traj, qb_trend, vs_exp, po_trend), Ridge on per-snapshot standardized inputs fit on ALL training seasons 1999–2021 against the N=8 adjusted-margin target, alpha chosen by the existing walk-forward CV procedure on training only, weights rounded to 2 decimals. Success criterion: holdout (2022–2025) Spearman N=8 of the frozen composite > plain Elo, with 95% season-level bootstrap CI on the difference reported. Secondary: next-game Brier vs Elo and vs spread. No factor pruning, no refits after seeing holdout results (MODEL-15: data decides weights/signs, including negative/≈0 streak & luck & last16).
- If the holdout fails the criterion, the result is reported honestly on the methodology page and in the README (no re-tuning); verification records it as a gap for the user rather than silently re-fitting.

#### Weight freeze (BACK-04)
- `fgs freeze` (or `fgs backtest --propose-weights --final`) writes `pipeline/weights.yaml` with `frozen: true`, `fit_seasons: 1999-2021`, `alpha`, `target: adjusted_margin_n8`, `fitted_at`, and per-factor weight + sign + training-fold sign consistency (k/19). Refresh/export only read it; any code path that refits refuses when `frozen: true` unless `--unfreeze` is passed.

#### One-time holdout (BACK-05, BACK-06)
- `fgs holdout` evaluates the frozen weights on 2022–2025 (walk-forward style: features/targets as-of, no refits), plus all baselines (Elo, season W%, last-16, point diff, spread Brier), at N=8 and N=4, by bucket.
- Season-level bootstrap: 2,000 resamples of holdout seasons' team-snapshots grouped by season (block bootstrap by season; with only 4 holdout seasons also report a team-season cluster bootstrap) → 95% CIs for composite Spearman, Elo Spearman, and their difference; same for Brier.
- Writes `pipeline/data/derived/holdout.json` and a committed `pipeline/HOLDOUT_RESULT.md` (human-readable table + every factor's fitted sign). Guard: refuses to run if `HOLDOUT_RESULT.md` exists unless `--force` (documented as "don't").

#### Methodology page (SITE-07)
- Route `#/methodology`, linked in the top nav ("Board · Mood over time · How it works").
- Export `methodology.json` (pipeline): factors (key, label, description, weight, sign, fold-sign consistency, backtest Δ when added from BACKTEST_LOG), target definition text, training/holdout split, walk-forward metrics (2003–2021) and holdout metrics with CIs for composite + baselines, notes.
- Content sections: (1) "What the score is" (percentile of an additive composite vs 1999–2021 team-weeks; mood bands); (2) "The factors" table: label, what it measures, weight (signed, 2dp), "helps/hurts the score when high", backtest Δ; (3) "Does it work?" chart: Spearman N=8 by candidate (Elo, season W%, last-16, point diff, composite) for walk-forward and holdout with CI whiskers, plus Brier incl. spread ceiling; (4) "Honest notes": momentum mostly doesn't predict (streak/luck/last16 signs), efficiency trend ≈0 given Elo, vs_exp depends on Vegas totals 2003–2020 and uses model expectations elsewhere, 1999–2000 pbp low-confidence, simplified playoff tiebreakers, scores are not betting advice.
- Chart with Observable Plot (already installed), following 02-UI-SPEC later-phase rules; no decimals in headline numbers except weights/metrics in the table (allowed: methodology is the one place for precise numbers).
- README updated with the holdout result.

### Claude's Discretion
- Exact bootstrap implementation, page layout, wording of honest notes (must be factual to logged numbers).

### Specific Ideas
- Title the chart "Does it work?" and lead with the plain-language answer from HOLDOUT_RESULT (e.g., "Yes, slightly: …" or "Not on 2022–25: …").

### Deferred Ideas (OUT OF SCOPE)
- Factor pruning / model selection (would need a fresh holdout), hand-entered 2021+ Vegas totals (v2).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MODEL-15 | Single score. The backtest decides every weight and sign, including streak and luck even if negative or ≈0 | `fgs freeze` writes `round(ridge_w, 2)` with no clipping or positivity constraint. Rounded-zero weights stay in the file as `0.00` (Pitfall 6). Fold-sign consistency is computed from the 19 walk-forward folds (Pattern 2) |
| BACK-04 | Ridge on standardized inputs, rounded, committed to `weights.yaml`; the weekly refresh never refits | Reuse `propose_weights` (LOSO alpha over 1999–2021, verified in code). New `frozen:` metadata sits beside the existing `weights:` mapping, so `load_weights` needs no change. Refusal guards are listed in Pattern 3 |
| BACK-05 | 2022–2025 evaluated once after the freeze, with season-level bootstrap CIs and every factor's fitted sign | `evaluate_frozen(derived, seasons, allow_holdout)` is parameterized and unit-tested on a 2018–2021 stand-in. Bootstraps were prototyped (Pattern 4). The one-time guard is a committed `HOLDOUT_RESULT.md` plus `HOLDOUT_RESULT.json` (Pattern 5) |
| BACK-06 | The final score beats the plain-Elo baseline out of sample | Pre-registered decision rule: the point estimate of composite − Elo Spearman N=8 > 0 is a pass. CIs are reported, and a three-way verdict is fixed in advance (Pattern 6). A fail is recorded as a gap, not re-tuned |
| SITE-07 | Methodology page: factors, fitted weights and signs, backtest chart vs baselines | `methodology.json` schema (Pattern 7), built inside `build_export` (Pitfall 3). `#/methodology` route, nav link, and a Plot dot-and-whisker chart with `fy` facets (Pattern 8) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Self-contained in `feel-good-scorew/`. No root manifests and no shared deps. Python 3.13 + uv + Polars + NumPy in `pipeline/`. Vite + Svelte 5 + Observable Plot 0.6.19 in `web/`. **The JSON in `web/public/data/` is the only pipeline↔web contract.**
- Keep it light: no heavy CI or test suites beyond backtest validation. Targeted pytest and vitest are fine. Phases 1–5 already established this level.
- Free data only (nflverse). No new dependencies are needed for this phase (no SciPy; NumPy is enough for the bootstrap).
- GSD workflow: edits happen through GSD execute commands. TypeScript stays at `~6.0` (svelte-check constraint).
- UI-SPEC binding rules: tokens only, prose column `max-width: 680px`, h2 in Heading 20, body in Body 16/1.5, board-style table rows, chart text Label 14 muted, `--border` axes, nothing hover-dependent, no logos, no new fonts or weights.

## Summary

Most of the work is plumbing on top of existing harness code. `propose_weights` already fits the pre-registered model: Ridge on per-snapshot z-scores over 1999–2021, alpha by leave-one-season-out CV, N=8 target. `_ridge_walk_forward` already runs the 19 training folds (test seasons 2003–2021) whose per-fold weights give "k/19" sign consistency. It just needs to return every fold instead of only `last`. `load_weights` only reads the `weights:` mapping, so the freeze metadata can live in sibling keys without breaking export or refresh. The leakage firewall stays: `backtest.py` is dev-only. The holdout evaluator belongs in a new dev-only module (`holdout.py`) that score/features never import.

The statistics need the most care. **With 4 holdout seasons, a pure season-block bootstrap is badly anti-conservative.** It has only 35 distinct resamples, ignores within-season sampling noise, and shrinks variance by (k−1)/k. I prototyped it on real training data. Across 16 rolling 4-season stand-in windows (2003–2021, freeze fit on earlier seasons), the season-block 95% CI on composite−Elo covered the long-run mean difference only **69%** of the time. A team-season cluster bootstrap stratified by season covered **88%**. Window-to-window spread (SD 0.0225 across non-overlapping windows) is larger than either bootstrap's SD (0.009 / 0.011). The honest presentation is therefore: point difference, per-season differences ("composite beat Elo in k of 4 seasons"), the pre-registered season-level CI, the wider team-season cluster CI, and a verdict wording fixed in advance that keys on the wider interval. The **paired difference** is the key statistic. Composite and Elo errors are strongly correlated, so the difference CI is roughly 10× tighter than either Spearman's own CI (stand-in: diff ±0.023 vs individual ±0.085).

On the stand-in, weights frozen on 1999–2017 gave Spearman N=8 0.5697 vs Elo 0.5509 on 2018–2021 (diff +0.0188, positive in 3 of 4 seasons, ≈0 in 2021). The season-block CI on the diff was [+0.004, +0.042] and the stratified team-season CI was [−0.002, +0.040]. Brier vs Elo: −0.0035, with season-week cluster CI [−0.0059, −0.0011]. The spread still wins by 0.009. These are training data, not a forecast of the holdout. They show the expected scale: a small positive edge whose cluster CI may straddle 0. Phase 5 flagged that vs_exp switches from Vegas-sourced to model-sourced exactly at the holdout boundary (deployment-condition Δ −0.0011), so the real holdout edge could be smaller.

**Primary recommendation:** Build three committed artifacts in strict order. (1) `PREREGISTRATION.md`, which includes the decision rule and both CI methods. (2) A frozen `weights.yaml` plus `FREEZE_RESULT.json` (walk-forward evidence) from `fgs freeze`. (3) `HOLDOUT_RESULT.md` + `HOLDOUT_RESULT.json` from a guarded, parameterized `fgs holdout`. Then `build_export` turns those committed files into `methodology.json`, with no backtest at export time. The page renders a dot-and-whisker Plot chart faceted by period.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Final weight fit + fold signs | Pipeline dev-only (`backtest.py`, `fgs freeze`) | — | Fits look at future targets, so this stays behind the leakage firewall |
| Freeze state / refusal guards | Pipeline (`weights.yaml` metadata, `score.load_weights_doc`, CLI) | — | Single source of truth already lives in `weights.yaml` |
| One-time holdout eval + bootstrap | Pipeline dev-only (`holdout.py`, `fgs holdout`) | Git (committed result files) | Must never run in refresh/export or tests on real holdout seasons |
| Methodology data assembly | Pipeline (`export.build_export` → `methodology.json`) | — | JSON is the only contract. Export reads committed result files and never recomputes |
| Page, route, nav, chart | Browser (Svelte + Plot) | — | Static rendering of `methodology.json` + `meta.json` (bands) |
| README holdout section | Docs | — | Human-readable record of the one-time result |

## Standard Stack

### Core (all already installed — no new packages)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| NumPy | ≥2.5.4 (pinned in pyproject) | Bootstrap resampling (`default_rng`, integer index draws), percentiles | Already in use. Percentile bootstrap needs nothing more [VERIFIED: pipeline/pyproject.toml] |
| Polars | ≥2.1.0 | Frames, `rank("average")` inside existing `bt.spearman` | `bt.spearman` costs 0.29 ms per call at n=2,300, so 2,000 draws × all candidates runs in about 15–30 s [VERIFIED: timed in scratchpad] |
| PyYAML | 6.0.3 | Read the frozen `weights.yaml` | Already used by `score.load_weights` [VERIFIED: score.py] |
| @observablehq/plot | 0.6.19 | Dot-and-whisker chart (`dot`, `ruleY` with `x1/x2`, `fy` facets) | Already used by HistoryChart/Sparkline. `ruleY` supports `x1`/`x2` + `y` [VERIFIED: node_modules/@observablehq/plot/src/marks/rule.d.ts] |
| Svelte 5 / Vite 8 | as installed | `MethodologyPage.svelte`, `MethodologyChart.svelte` | Existing app |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled percentile bootstrap (~30 lines NumPy) | `scipy.stats.bootstrap` | SciPy isn't a dependency, and `scipy.stats.bootstrap` doesn't do cluster/block resampling natively. Not worth adding |
| Percentile CI | BCa | BCa with 4 clusters is unstable. Percentile is standard and easier to explain |
| Season-block + stratified team-season cluster | Two-stage (seasons, then team-seasons within) | Two-stage is the widest (stand-in diff CI [−0.0075, +0.0502]). It's a reasonable sensitivity check but not locked. Optionally store it in holdout.json only |
| Parsing `BACKTEST_LOG.md` for Δ | Recompute Δ from cumulative `RIDGE_SETS` in the walk-forward report | Recompute is machine-readable and is how the log rows were defined ("composite with factor minus without"). Parse the log only as a cross-check (Pattern 7) |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed in this phase. Every library above is already pinned in `pipeline/pyproject.toml` / `web/package.json`. slopcheck: not applicable.

## Architecture Patterns

### System Architecture Diagram

```
                      (training only: seasons <= 2021)
 cache (schedules, pbp, sim) ──► derive(scored=False, **cached_inputs)
                                     │
             ┌───────────────────────┴───────────────────────┐
             ▼                                               ▼
  propose_weights (1999–2021, LOSO alpha)        walk_forward_frame (folds 2003–2021)
             │                                     │ per-fold weights ─► fold-sign k/19
             │                                     │ preds per row    ─► WF metrics + bootstrap whiskers
             │                                     │ cumulative sets  ─► Δ per factor (x-check BACKTEST_LOG)
             ▼                                     ▼
   [guard: frozen? HOLDOUT_RESULT exists?] ──► fgs freeze ──► weights.yaml (frozen) + FREEZE_RESULT.json   (commit)
                                                                       │
   PREREGISTRATION.md (committed BEFORE) ─────────────────────────────┤
                                                                       ▼
   [guard: result exists? prereg + weights committed/clean? frozen?] ─► fgs holdout (ONE TIME)
        derive(scored=True, frozen weights) on seasons <= 2025
        composite (shipped) + baselines on 2022–2025 ─► Spearman N8/N4/buckets, Brier (maps fit <= 2021)
        paired bootstrap: season-block + team-season cluster (Spearman), season-block + season-week (Brier)
             ▼
   HOLDOUT_RESULT.md + HOLDOUT_RESULT.json (commit) + data/derived/holdout.json (working copy)
             ▼
   fgs export / refresh: build_export reads weights.yaml + FREEZE_RESULT.json + HOLDOUT_RESULT.json(optional)
             ▼
   web/public/data/methodology.json ──► #/methodology (MethodologyPage + Plot chart) ; README section
```

### Recommended Project Structure
```
pipeline/
├── PREREGISTRATION.md        # committed first (task 1 of plan 1)
├── weights.yaml              # frozen: true + metadata + weights + per-factor fit block
├── FREEZE_RESULT.json        # committed: walk-forward metrics + CIs, fold signs, Δ per factor
├── HOLDOUT_RESULT.md         # committed: one-time result, human-readable
├── HOLDOUT_RESULT.json       # committed: machine-readable twin (export reads this, not data/)
├── src/fgs/
│   ├── backtest.py           # + walk_forward_frame(), folds returned, fold_signs(), factor_deltas()
│   ├── bootstrap.py          # pure: cluster index builders + paired_bootstrap() (dev-only, no fgs imports needed)
│   ├── holdout.py            # dev-only: evaluate_frozen(), guards, render_markdown()
│   ├── methodology.py        # pure: build_methodology(weights_doc, freeze, holdout|None) -> dict
│   ├── score.py              # + load_weights_doc(), is_frozen()
│   ├── export.py             # files["methodology.json"] = methodology.build_methodology(...)
│   └── cli.py                # + freeze, holdout subcommands; guards on backtest flags
└── tests/ test_freeze.py, test_bootstrap.py, test_holdout.py, test_methodology.py
web/src/
├── lib/router.ts             # + { kind: 'methodology' }; RESERVED keeps only records
├── lib/methodology.ts(+test) # pure helpers: verdict text, effect wording, number formatting
├── lib/data.ts               # + loadMethodology(meta)
└── components/ MethodologyPage.svelte, MethodologyChart.svelte, SiteHeader.svelte (+ How it works)
```

Note that `pipeline/.gitignore` ignores `data/`, so `pipeline/data/derived/holdout.json` is **not committed** [VERIFIED: `git check-ignore`]. `web/public/data/` **is** committed. The committed JSON twins keep the site reproducible from a clean clone.

### Pattern 1: Freeze = existing proposal, written with metadata
**What:** `fgs freeze` calls `propose_weights(derived)`, which is already sealed to ≤2021 and tested by `test_propose_weights_holdout_sealed`. It rounds to 2 dp and writes `weights.yaml` from a text template. A template keeps the explanatory comments, which `yaml.dump` would drop. The command then re-reads the file with `yaml.safe_load` and checks it round-trips to the rounded weights.

**The alpha procedure (resolves a CONTEXT wording question):** CONTEXT says "alpha chosen by the existing walk-forward CV procedure on training only". The existing code (`propose_weights` → `choose_alpha`) uses **leave-one-season-out CV over 1999–2021** on `ALPHA_GRID × n`. Walk-forward folds use the same `choose_alpha` inside each fold. PREREGISTRATION.md should state the exact procedure: "`choose_alpha`: LOSO CV over 1999–2021, grid {0, 1e-3, 1e-2, 1e-1, 1}·n, min pooled SSE". Do not invent a new procedure. Phase 5 measured the pick as 0.01·n with 11 factors. [VERIFIED: backtest.py lines 264–311; 05-RESEARCH]

```yaml
# (comment header regenerated by fgs freeze: command, date, procedure, one line per negative/≈0 weight)
frozen: true
fit_seasons: [1999, 2021]
target: adjusted_margin_n8
alpha: 0.01          # multiplied by n inside ridge_fit
n: 12331
fitted_at: "2026-11-12"
weights:             # read by score.load_weights — must stay {factor: number}
  elo: 2.59
  ...
  po_trend: -0.01
fit:                 # per-factor evidence (ignored by load_weights)
  elo: {raw: 2.5913, sign: "+", fold_sign: "19/19"}
  po_trend: {raw: -0.0094, sign: "-", fold_sign: "17/19"}
```
`load_weights` rejects non-number values inside `weights:` [VERIFIED: score.py]. That's why the evidence goes under a sibling `fit:` key. Add `score.load_weights_doc(path) -> dict` (whole doc) and `score.is_frozen(path) -> bool`.

### Pattern 2: Fold-sign consistency
**What:** For the final 11-factor set, collect every walk-forward fold's weight vector (folds S = 2003..2021, each fit on seasons < S with its own LOSO alpha). Then `fold_sign = count(sign(w_fold[f]) == sign(w_final_unrounded[f])) / 19`. Use the unrounded final weight for the sign. Display `sign` from the rounded weight, with "≈0" when it rounds to 0.00.
**How:** `_ridge_walk_forward` currently keeps only `last`. Change it to also return `folds: list[dict]`, which is backward compatible: keep `last_fold_weights` in the report. Phase 5's expected values: elo, season_record, mov and qb_trend 19/19 +; luck and epa_traj 19/19 −; vs_exp 18/19 −; po_trend 17/19 −; last16, sow and streak only 13–14/19 [CITED: 05-RESEARCH "Fold sign stability"]. The p5 harness `fold_signs()` is a working reference implementation.

### Pattern 3: Refusal guards (one place, tested)
| Code path | Refits? | Guard |
|-----------|---------|-------|
| `fgs refresh`, `fgs export`, `fgs build` | No (`derive` → `load_weights`) | None needed. Add a test that monkeypatches `backtest.ridge_fit` to raise and runs export on the synthetic fixture |
| `fgs backtest` (plain) | Fits per fold for evaluation only, on ≤2021 | Allowed |
| `fgs backtest --propose-weights` | Yes (proposal) | Refuse (exit 1) if `is_frozen()`: "weights are frozen (fit 1999–2021); run `fgs freeze --unfreeze` to refit" |
| `fgs freeze` | Yes | Refuse if frozen unless `--unfreeze`. **Always refuse if `HOLDOUT_RESULT.md` exists** ("refitting after the holdout breaks the pre-registration; a new holdout would be needed"). The user can delete the file deliberately in v2 |
| `fgs backtest --include-holdout` | Refits on holdout seasons in later folds (a peek) | Refuse unless `HOLDOUT_RESULT.md` exists. Before the one-time evaluation, nothing may look at 2022–2025 |
| `fgs holdout` | No refits; scores only | Refuse if `HOLDOUT_RESULT.md` exists unless `--force`. Refuse if `weights.yaml` isn't frozen, if `PREREGISTRATION.md` is missing, or if git shows either file modified or untracked (`git status --porcelain -- pipeline/PREREGISTRATION.md pipeline/weights.yaml` non-empty). If git is unavailable, warn instead of refusing |

Paths must be module globals read at call time (`paths.PREREG_PATH`, `paths.HOLDOUT_MD_PATH`, `paths.HOLDOUT_JSON_PATH`, `paths.FREEZE_RESULT_PATH`) so tests can monkeypatch them. This is the established pattern in `cli.py` and `paths.py`.

### Pattern 4: Paired bootstrap (prototyped)
**What:** Resample index sets once per draw and compute **every** candidate's metric on the same indices, so differences are paired. Use the percentile method, B = 2,000, `np.random.default_rng(SEED)` with SEED recorded in JSON.

| Statistic | Unit | Methods to report | Rationale |
|-----------|------|-------------------|-----------|
| Spearman N=8 / N=4 (pooled over snapshots) | team-snapshots | (a) **season block**: draw 4 seasons with replacement and concatenate their rows (locked, "season-level"). (b) **team-season cluster, stratified by season**: within each season draw that season's ~32 team-season clusters with replacement | (b) keeps the 4-season mix fixed and captures within-season noise. The 17-ish snapshots of one team-season are strongly autocorrelated, so they're one cluster |
| Brier (next game) | games | (a) season block. (b) **season-week cluster** (season, asof_week) | A game belongs to two team-seasons, so team-season clusters aren't well defined. Season-week cluster ≈ game iid in the prototype |

**Prototype results (stand-in 2018–2021, weights fit 1999–2017, 2,185 rows, B=2000)** [VERIFIED: scratchpad p6/boot.py, brier.py]:

| Method | Composite Spearman CI | Elo CI | Diff CI | SD(diff) |
|--------|----------------------|--------|---------|----------|
| Point | 0.5697 | 0.5509 | +0.0188 | — |
| Season block (35 distinct resamples) | [0.552, 0.591] | [0.523, 0.581] | [+0.0039, +0.0418] | 0.0094 |
| Team-season cluster (unstratified) | [0.474, 0.642] | [0.452, 0.622] | [−0.0037, +0.0426] | 0.0116 |
| **Team-season cluster, stratified** | [0.471, 0.642] | [0.450, 0.625] | [−0.0021, +0.0400] | 0.0111 |
| Franchise cluster (32) | [0.462, 0.641] | [0.439, 0.627] | [−0.0037, +0.0426] | 0.0119 |
| Two-stage (season → team-season) | — | — | [−0.0075, +0.0502] | 0.0147 |

Per season (stand-in): 2018 +0.057, 2019 +0.020, 2020 +0.011, 2021 −0.001, so the composite beat Elo in 3 of 4 seasons.

Brier (1,083 games; logistic maps fit on ≤2017): composite 0.2207, Elo 0.2242, spread 0.2117. Composite − Elo −0.0035: season block [−0.0053, −0.0022], season-week [−0.0059, −0.0011], game iid [−0.0060, −0.0011]. Composite − spread +0.0090: season-week [+0.0039, +0.0137].

**Empirical calibration on training data** [VERIFIED: scratchpad p6/calib.py]. I ran 16 rolling 4-season windows (2003–06 … 2018–21), each frozen on earlier seasons, with B=400. The season-block CI covered the mean window diff (+0.0174) in 69% of windows, and its lower bound was > 0 in 56%. The stratified team-season CI covered it in 88%, with lower bound > 0 in 38%. Non-overlapping window diffs: −0.015, +0.013, +0.016, +0.040 (SD 0.0225). **Conclusion:** both intervals understate uncertainty with 4 seasons. Season-block is the worse of the two. Report both, label them clearly, and key the verdict on the wider one.

```python
# Source: scratchpad p6/boot.py (prototype) — production shape
def season_blocks(season: np.ndarray) -> list[np.ndarray]:
    return [np.flatnonzero(season == s) for s in np.unique(season)]

def stratified_clusters(season, cluster_key) -> list[list[np.ndarray]]:
    """Per season, the row-index arrays of each cluster (team-season or season-week)."""
    out = []
    for s in np.unique(season):
        m = np.flatnonzero(season == s)
        keys = cluster_key[m]
        out.append([m[keys == k] for k in np.unique(keys)])
    return out

def draw_blocks(rng, blocks):                 # season block
    return np.concatenate([blocks[j] for j in rng.integers(0, len(blocks), len(blocks))])

def draw_stratified(rng, strata):             # cluster within season
    parts = []
    for clusters in strata:                   # one list of clusters per season
        parts += [clusters[j] for j in rng.integers(0, len(clusters), len(clusters))]
    return np.concatenate(parts)

def paired_bootstrap(stat_fns: dict, draw, B=2000, seed=20221) -> dict:
    """stat_fns: name -> f(idx) -> float. Returns per-stat percentile CI + diffs vs 'elo'."""
    rng = np.random.default_rng(seed)
    vals = {k: np.empty(B) for k in stat_fns}
    for b in range(B):
        idx = draw(rng)
        for k, f in stat_fns.items():
            vals[k][b] = f(idx)
    ...  # ci = np.percentile(v, [2.5, 97.5]); diff = vals['composite'] - vals['elo']
```
Use `bt.spearman` for every Spearman. It has average-rank ties, which handles duplicated rows from resampling, and it matches the walk-forward metric exactly. Brier per draw = mean of per-game squared errors over the drawn indices, which is cheap.

### Pattern 5: One-time holdout evaluator (parameterized, guard in CLI only)
```python
# holdout.py (dev-only; never imported by features/score/export)
def evaluate_frozen(derived: dict, weights: dict, seasons: tuple[int, int], fit_last: int,
                    *, allow_holdout: bool = False, B=2000, seed=20221) -> dict:
    lo, hi = seasons
    if hi > TRAIN_LAST_SEASON and not allow_holdout:
        raise ValueError("holdout seasons require the guarded `fgs holdout` path")
    # 1. composite = the SHIPPED composite: derived["features"] from derive(scored=True) with the
    #    frozen weights (sum w*z, rounded weights, no intercept). Never refit.
    # 2. targets(team_games, snapshots, (4, 8)) on data <= hi; rows with season in [lo, hi].
    # 3. Spearman N8/N4 all + buckets + per season for composite, elo, season_record, last16, pd_pg.
    # 4. Brier: next_game_frame; logistic maps (diff, home_ind) for composite/elo/... and spread_line,
    #    each fit ONCE on seasons <= fit_last; elo_538 closed form needs no fit.
    # 5. paired bootstraps (Pattern 4); per-season diffs and "won k of 4".
    # 6. factors: weight, sign, fold_sign copied from weights.yaml fit block.
```
- The CLI `_cmd_holdout` runs the guards, calls `evaluate_frozen(..., seasons=HOLDOUT_SEASONS, fit_last=2021, allow_holdout=True)`, and writes `HOLDOUT_RESULT.md`, `HOLDOUT_RESULT.json` and `data/derived/holdout.json`. It also records `weights_sha256`, `prereg_sha256`, `git_head` and `evaluated_at`.
- Tests call `evaluate_frozen` with `seasons=(2018, 2021), fit_last=2017` and weights from a ≤2017 fit (or the synthetic fixture). **No test may pass `allow_holdout=True` with real data.**
- Filter everything to `season <= 2025` before computing targets, so the 2026 in-progress season is never part of the holdout.

### Pattern 6: Pre-registered decision rule and verdict text
Put the following in `PREREGISTRATION.md` and implement it as a pure function (`holdout.verdict(result)`):
- **Pass (BACK-06):** point estimate Spearman N=8 (composite) − Spearman N=8 (Elo) > 0 on pooled 2022–2025 snapshots.
- **Verdict wording**, based on the *wider* of the two diff CIs (normally the team-season cluster):
  - `yes`: diff > 0 and the lower bound > 0 → "Yes: on 2022–25 the score ranked teams' next 8 games better than Elo alone."
  - `slight`: diff > 0 and the CI includes 0 → "Yes, slightly: better than Elo alone on 2022–25, but within the noise of four seasons."
  - `no`: diff ≤ 0 → "Not on 2022–25: Elo alone did as well or better. We kept the weights anyway (no re-tuning)."
- Secondary results are reported, never gating: Brier vs Elo and vs spread (spread is expected to win; it is the market ceiling).
- Report as well: N=4, buckets, per-season diffs, both CIs, B, seed, and the number of distinct season-block resamples (35).

### Pattern 7: Evidence files and `methodology.json` schema
**Factor Δ source:** compute it in `fgs freeze` from the walk-forward report as `Spearman_N8(RIDGE_SETS[k]) − Spearman_N8(RIDGE_SETS[k−1])` in insertion order. elo is the baseline, so store its absolute value. This is how the log defines each row [VERIFIED: BACKTEST_LOG.md header]. As a cross-check, parse `BACKTEST_LOG.md` (prototype `p6/logparse.py`: header-keyed cells, exact factor key in the Factor cell, first matching row wins, handles Unicode "−") and warn if |computed − logged| > 0.0005. Don't make the export depend on markdown parsing (Pitfall 4).

`FREEZE_RESULT.json` (committed, written by `fgs freeze`):
```json
{"version":1,"fitted_at":"…","fit_seasons":[1999,2021],"alpha":0.01,"n":12331,
 "walk_forward":{"seasons":[2003,2021],"B":2000,"seed":20221,
   "spearman_n8":{"composite":{"value":0.526,"ci_season":[..],"ci_cluster":[..]},"elo":{...},"season_wpct":{...},"last16":{...},"pd_pg":{...}},
   "spearman_n4":{...},
   "brier":{"composite":{"value":0.2179,"ci_season":[..],"ci_cluster":[..]},"elo":{...},"spread":{...},"elo_538":{"value":...}}},
 "factors":{"elo":{"raw":2.59,"weight":2.59,"sign":"+","fold_sign":[19,19],"delta_spearman_n8":null,"spearman_n8_alone":0.5114}, "...":{}},
 "log_crosscheck":{"max_abs_diff":0.0001}}
```
Walk-forward "composite" = the walk-forward ridge composite (the `ridge:+po_trend` predictions, refit per fold), which is the pre-existing walk-forward number. Label it "Feel-good score (refit each season)" to keep it distinct from the holdout's frozen composite. With 19 seasons the season-block bootstrap is reasonable here.

`methodology.json` (export, built by pure `methodology.build_methodology(weights_doc, freeze, holdout_or_None, factors_meta, bands)`):
```json
{"version":1,
 "frozen":{"fitted_at":"…","fit_seasons":[1999,2021],"alpha":0.01,"n":12331},
 "target":{"n":8,"text":"…plain-language target…"},
 "split":{"train":[1999,2021],"walk_forward":[2003,2021],"holdout":[2022,2025],"live":2026,"reference":[1999,2021]},
 "factors":[{"key":"elo","label":"Elo rating","description":"…","weight":2.59,"sign":"+","effect":"helps",
             "fold_sign":{"k":19,"of":19},"delta_spearman_n8":null,"baseline_spearman_n8":0.511}],
 "candidates":[{"key":"elo","label":"Elo alone"},{"key":"season_wpct","label":"Season win %"},
               {"key":"last16","label":"Last 16 games"},{"key":"pd_pg","label":"Point differential"},
               {"key":"composite","label":"Feel-good score"},{"key":"spread","label":"Vegas spread","brier_only":true}],
 "walk_forward":{"seasons":[2003,2021],"spearman_n8":{"elo":{"value":0.511,"ci":[..,..]}, "...":{}},"brier":{...}},
 "holdout":null | {"seasons":[2022,2025],"evaluated_at":"…","verdict":"yes|slight|no","headline":"…",
             "spearman_n8":{"…":{"value":..,"ci":[..]}},"spearman_n4":{...},"brier":{...},
             "diff":{"spearman_n8":{"value":..,"ci_season":[..],"ci_cluster":[..],"seasons_won":3,"of":4,
                                    "per_season":{"2022":..}},
                     "brier_vs_elo":{...},"brier_vs_spread":{...}}},
 "notes":[{"key":"momentum","text":"…numbers interpolated from data…"}]}
```
- `ci` on the chart: walk-forward uses the season-block CI (19 seasons). Holdout uses the team-season cluster CI, which is the wider one. Both holdout diff CIs are shown in the "Does it work?" text and the table.
- `effect`: "helps" if weight > 0, "hurts" if < 0, "≈ no effect" if the rounded weight is 0.00.
- `notes` are **templated in Python with numbers from the evidence files** (e.g. streak weight, fold-sign counts, epa_traj Δ, vs_exp source split, 1999–2000 low-confidence flag). The hand-written prose can't drift from the numbers, and a test can assert each interpolated number equals the source value.
- The holdout is null before the one-time run. The page then shows "Holdout: not evaluated yet", which lets the page ship and be checked before the holdout task.

### Pattern 8: Methodology page and chart
**Layout** (single reading column, `max-width: 680px`, UI-SPEC rule 8):
1. h2 "What the score is": 2–3 short paragraphs + the mood-band list from `meta.bands` (reuse `moodToken` colors).
2. h2 "The factors": board-style rows (surface, 8px gap), **not** an HTML table on mobile. Each row shows label, description (muted), signed weight `+2.59` / `−0.56`, "helps/hurts when high", fold-sign "19/19 seasons", and Δ when added (`+0.0028`, or "baseline" for Elo). On ≥1024px a CSS grid with column headers is fine. Rows are sorted by |weight| or kept in factor order. Prefer factor order, since that matches the "added one at a time" story and the Δ column.
3. h2 "Does it work?": lead with the `holdout.headline` sentence (Body 16/600), then the Spearman chart, then the Brier chart, then a small numeric table (the no-hover fallback required by UI-SPEC rule 3).
4. h2 "Honest notes": a `<ul>` of `notes[].text`.

**Chart** (Plot, horizontal dot-and-whisker, works at 375px):
```ts
// Source: Plot 0.6.19 typings (ruleY x1/x2/y; dot; fy facets) — verified in node_modules
const rows = [...wf, ...ho] // {period:'Walk-forward 2003–21'|'Holdout 2022–25', key, label, value, lo, hi}
Plot.plot({
  width, height: 2 * (5 * 28) + 60, marginLeft: width < 500 ? 120 : 150,
  style: { fontSize: '14px', color: 'var(--text-muted)', background: 'transparent', fontFamily: 'inherit' },
  x: { domain: [xmin, xmax], label: 'Rank correlation with next 8 games (higher is better)', grid: true },
  y: { domain: order, label: null },
  fy: { domain: periods, label: null },
  marks: [
    Plot.ruleY(rows, { fy: 'period', y: 'label', x1: 'lo', x2: 'hi', stroke: 'var(--text-muted)' }),
    Plot.dot(rows, { fy: 'period', y: 'label', x: 'value', r: 4,
                     fill: (d) => d.key === 'composite' ? 'var(--accent)' : 'var(--text-muted)' }),
    Plot.ruleX(eloLines, { fy: 'period', x: 'value', stroke: 'var(--border)', strokeDasharray: '2,3' }), // Elo reference per facet
  ],
})
```
- The Brier chart is the same shape, with the x label "Next-game Brier (lower is better)" and spread as its own row, labelled "Vegas spread (market ceiling)".
- Don't share an x domain across the two metrics. Pad each domain to fit the whiskers. Spearman values sit around 0.3–0.6 and Brier around 0.21–0.25.
- Mount like `HistoryChart.svelte`: `bind:clientWidth`, `$effect` builds the plot, `replaceChildren`, `role="img"` + `aria-label`.
- Plot centers `ruleY`/`dot` on ordinal y bands [VERIFIED: `RuleY` applies `applyTransform` with the y scale offset in dist/plot.umd.js; visual confirmation is still needed].
- Holdout null: render the walk-forward facet only, plus a muted "Holdout: evaluated once after the weights were frozen — not run yet."

**Router/nav:** add `{ kind: 'methodology' }`, parse `/^\/methodology\/?$/`, keep `records` reserved, and add `methodologyHash = '#/methodology'`. `SiteHeader` `current` union gains `'methodology'` and a third link "How it works". In App, add a branch for `route.current.kind === 'methodology'` and clear the notice in the reserved/notice effect. `router.test.ts` line 34 currently asserts `#/methodology` is reserved and must be updated [VERIFIED: router.test.ts]. Add `loadMethodology(meta)` in data.ts with `?v=${generated_at}` cache-busting, same as `loadHistory`.

### Anti-Patterns to Avoid
- **Running the backtest inside export/refresh** to get methodology numbers. It's slow, it refits, and it breaks "refresh never refits". Read committed evidence files instead.
- **Evaluating the holdout with walk-forward refits** (`run_backtest(include_holdout=True)`). That refits on 2022 for S=2023, so it isn't the frozen model. Phase 6 evaluates the shipped `Σ w·z` only.
- **Fitting Brier calibration maps on holdout seasons.** Fit them once on ≤2021.
- **Reporting only the season-block CI**, which is anti-conservative with 4 seasons (69% empirical coverage).
- **Computing CIs separately per candidate and eyeballing overlap.** Use paired differences. The individual CIs overlap massively even when the diff is clearly positive.
- **A test fixture that "just checks the CLI works" by running `fgs holdout` on the real cache.** That would be the one-time evaluation done by pytest.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Spearman with ties | custom ranker | `backtest.spearman` | Average ranks, already the metric of record. Fast enough (0.29 ms) |
| Ridge / alpha | new fit | `propose_weights`, `choose_alpha`, `ridge_fit` | Pre-registered "existing procedure". Already sealing-tested |
| Next-game frame / logistic | new joins | `next_game_frame`, `logit_fit`, `logit_predict`, `brier` | As-of join semantics are already tested |
| Target | new target | `backtest.targets` | Locked target |
| Composite on holdout | re-implementing Σwz | `derive(scored=True)` features `composite` | Guarantees the evaluated score is the shipped score |
| Atomic export | writing methodology.json separately | add it to `build_export` files | `write_export` replaces the whole dir (Pitfall 3) |
| JSON float hygiene | ad hoc | `backtest._clean` (round 6, NaN→None) and `allow_nan=False` | Existing strict-JSON pattern |

## Common Pitfalls

### Pitfall 1: Season-block bootstrap with 4 seasons looks precise but isn't
**What goes wrong:** narrow CIs on Spearman ([0.552, 0.591] in the stand-in) and on the diff, from only 35 distinct resamples. Empirical coverage was 69%.
**How to avoid:** report it because it's locked, but key the verdict on the wider team-season cluster CI, and show per-season diffs ("3 of 4 seasons").
**Warning signs:** CI endpoints repeat across reruns with different seeds. The holdout.json `distinct_resamples` field equals 35.

### Pitfall 2: Accidentally peeking at the holdout before the one-time run
**What goes wrong:** a test, a debug print, `fgs backtest --include-holdout`, or a methodology dev build computes 2022–2025 composite metrics, so the pre-registration is no longer clean.
**How to avoid:** `evaluate_frozen` raises for seasons > 2021 unless `allow_holdout=True`. `--include-holdout` is refused until `HOLDOUT_RESULT.md` exists. Tests use 2018–2021 stand-ins. The methodology page handles `holdout: null`. The one-time run is a single executor task (a `checkpoint` is recommended) after PREREGISTRATION and weights are committed.
**Warning signs:** any `holdout.json` or HOLDOUT_RESULT file timestamp earlier than the prereg commit, checked with `git log --format=%ci -- pipeline/PREREGISTRATION.md pipeline/HOLDOUT_RESULT.md`.

### Pitfall 3: `write_export` drops files it didn't write
**What goes wrong:** methodology.json written by a separate step vanishes on the next `fgs refresh`, because `write_export` swaps in a fresh directory containing exactly `files` [VERIFIED: export.py].
**How to avoid:** `build_export` adds `files["methodology.json"]`. Missing `FREEZE_RESULT.json` is an error once frozen. Missing `HOLDOUT_RESULT.json` means `holdout: null`.

### Pitfall 4: Markdown log parsing is brittle
**What goes wrong:** Phase 5 appends rows, possibly with extra columns, variant rows ("qb_trend (literal def)") or a second table. Notes may contain `|`.
**How to avoid:** compute Δ from the cumulative RIDGE_SETS, and use the log parser only as a warning-level cross-check. If you do parse, detect a header as any row followed by a `---` separator and match cells by header name. The prototype parser works on the current log, which has 7 rows and no Phase 5 rows yet [VERIFIED: p6/logparse.py].

### Pitfall 5: The holdout composite isn't the walk-forward composite
**What goes wrong:** comparing holdout numbers to walk-forward `ridge:+po_trend` as if they were the same model. Walk-forward refits each season with unrounded weights and an intercept. The holdout uses the frozen rounded `Σ w·z`. Spearman is invariant to the intercept, but rounding and the frozen fit differ.
**How to avoid:** label the periods "refit each season" vs "frozen weights". As a sanity check, `fgs freeze` can also report the frozen composite on the last training window. A test asserts that Spearman(composite) on a training stand-in matches `bt.spearman` of `Σ round(w)·z` exactly.

### Pitfall 6: Rounded weights of 0.00 and "−0.00"
**What goes wrong:** po_trend −0.0094 rounds to −0.01 today. Under a slightly different fit it could become `-0.00`, which reads as a negative sign and could be dropped by a "nonzero" filter.
**How to avoid:** format weights with `f"{round(v,2)+0.0:.2f}"` (export already uses `+ 0.0`). Keep 0.00 factors in `weights:` (MODEL-15: data decides; the factor stays). Show sign "≈0" and effect "no effect at this weight".

### Pitfall 7: vs_exp source switch at the holdout boundary
**What goes wrong:** vs_exp's weight (≈ −1.2) is learned mostly on Vegas-sourced 2003–2020 rows. All of 2021+ is model-sourced, and Phase 5 measured the deployment condition at −0.0011 [CITED: 05-RESEARCH Pitfall 1]. The holdout may underperform for this known reason.
**How to avoid:** don't fix it (no refits). State it in PREREGISTRATION as a known risk *before* the run, and in the honest notes. HOLDOUT_RESULT.json can include the per-factor composite with vs_exp's contribution zeroed as a **labelled post-hoc diagnostic** only if the pre-registration lists it in advance. Otherwise omit it. Recommendation: list it as a pre-registered diagnostic so the notes can be factual either way.

### Pitfall 8: Guard bypass via stale derived features
**What goes wrong:** `fgs holdout` reads `data/derived/features.parquet` built with interim weights.
**How to avoid:** `fgs holdout` always re-derives from the cache with the frozen weights (`derive(load_schedules(), **cached_inputs())`) and asserts `derived["weights"] == frozen weights`.

### Pitfall 9: Integer-score ties vs continuous composite
**What it is:** evaluate the continuous `composite`, not the integer percentile `score`. They're monotone-equivalent except for rounding ties. The headline must be about the composite that produces the score. Mention in PREREGISTRATION that "frozen composite" means `features.composite`.

## Code Examples

### Weighted fold-sign summary (from the p5 harness, verified)
```python
# Source: scratchpad/p5/harness.py fold_signs() — production: reuse _ridge_walk_forward folds
def fold_sign_consistency(folds: list[dict], final_raw: dict[str, float]) -> dict[str, tuple[int, int]]:
    out = {}
    for f, w in final_raw.items():
        s = np.sign(w)
        out[f] = (sum(1 for fo in folds if np.sign(fo["weights"][f]) == s), len(folds))
    return out
```

### Holdout markdown table (HOLDOUT_RESULT.md shape)
```
# Holdout result (2022–2025), evaluated once on 2026-11-12
Verdict: slight — Yes, slightly: …
Pre-registration: pipeline/PREREGISTRATION.md (sha256 …), weights.yaml sha256 …, commit …

| Candidate | Spearman N=8 [95% CI, team-season] | Spearman N=4 | wk0 | early | mid | late | Brier [95% CI] |
| Feel-good score (frozen) | … | … | … | … | … | … | … |
| Elo alone | … |
| Season win % / Last 16 / Point diff / Vegas spread (Brier only) / Elo 538-style | … |

Difference (score − Elo), Spearman N=8: +… ; season-block CI […]; team-season CI […]; won k of 4 seasons (2022 …, 2023 …)
Brier difference vs Elo: … [season-week CI …]; vs spread: … [ … ]
| Factor | Weight | Sign | Folds with this sign |   (all 11, from weights.yaml)
Bootstrap: B=2000, seed=…, percentile; season block has 35 distinct resamples.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Interim weights pasted by hand from `--propose-weights` | `fgs freeze` writes frozen weights + evidence; refits refused | Phase 6 | Refresh can't drift. The provenance is machine-checked |
| `--include-holdout` available any time | Refused until the one-time result exists | Phase 6 | Holdout integrity |
| `#/methodology` reserved → redirect | Real route + nav link | Phase 6 | SITE-07 |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Interpreting "existing walk-forward CV procedure" as the existing `choose_alpha` LOSO over 1999–2021 (what `propose_weights` does) | Pattern 1 | Low. Writing it explicitly into PREREGISTRATION removes the ambiguity. Using the last walk-forward fold's alpha would give the same grid value in practice (0.01·n) |
| A2 | Stratified team-season cluster is the "team-season cluster bootstrap" CONTEXT intends | Pattern 4 | Low. Unstratified gives nearly identical intervals (±0.002) |
| A3 | Verdict keyed on the wider CI, with pass/fail on the point estimate | Pattern 6 | Medium. The user may prefer CI-based pass/fail. CONTEXT's success criterion is "composite > Elo, with CI reported", which matches |
| A4 | Committed `FREEZE_RESULT.json` / `HOLDOUT_RESULT.json` twins (beyond CONTEXT's listed files) | Pattern 7 | Low. Needed because `pipeline/data/` is gitignored |
| A5 | Plot `ruleY` and `dot` align at band centers with an ordinal y + `fy` facets | Pattern 8 | Low. Verify visually at 375px and 1280px |
| A6 | Pre-registering a "vs_exp zeroed" diagnostic is acceptable scope | Pitfall 7 | Low. It's diagnostic only, never used to refit |

## Open Questions (RESOLVED)

1. **Season-block bootstrap with only 4 seasons: is it valid?**
   RESOLVED: valid as defined but anti-conservative (35 distinct resamples, 69% empirical coverage on training windows). Report it as locked, also report the stratified team-season cluster CI (88% coverage) and per-season diffs, and word the verdict on the wider CI.
2. **Which alpha procedure?**
   RESOLVED: the existing `choose_alpha` (LOSO over 1999–2021, `ALPHA_GRID·n`) via `propose_weights`. Write it verbatim in PREREGISTRATION.
3. **Brier clustering unit?**
   RESOLVED: season block (locked) plus season-week cluster. Calibration maps are fit once on ≤2021.
4. **Where do methodology numbers come from at export time?**
   RESOLVED: the committed `weights.yaml` (fit block), `FREEZE_RESULT.json` and `HOLDOUT_RESULT.json`, with `holdout: null` until the run. No backtest at export.
5. **Parse BACKTEST_LOG.md or switch to machine-readable?**
   RESOLVED: compute Δ from cumulative RIDGE_SETS at freeze, and keep the log parse as a cross-check (warning if > 0.0005).
6. **What if `--force` is used?**
   RESOLVED: allowed but loud. The rerun overwrites with `"rerun": true` and appends a "Reruns" section to HOLDOUT_RESULT.md listing the previous result's verdict and timestamp, so the history stays visible. README documents it as "don't".
7. **What may refit after freeze?**
   RESOLVED: plain `fgs backtest` (evaluation on ≤2021) is fine. `--propose-weights` and `freeze` are refused when frozen. `freeze --unfreeze` is refused once HOLDOUT_RESULT.md exists.
8. **Plan ordering?**
   RESOLVED: Plan 1 is PREREGISTRATION (first commit), then the freeze tooling, then `fgs freeze` and committing weights + FREEZE_RESULT. Plan 2 is holdout tooling, tested on stand-ins. Plan 3 is methodology.json + page, which works with `holdout: null`. A final plan runs the one-time `fgs holdout` (checkpoint), commits the results, re-exports, updates the README, and records the verdict. The page and README must not be finalized before the run, and the run must not happen before the prereg commit.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | pipeline commands/tests | ✓ | 0.10.12 | — |
| Python 3.13 (uv-managed) | pipeline | ✓ | (per pyproject `>=3.13`) | — |
| Node | web build/tests | ✓ (but below the `engines` field) | v20.19.0 (package.json engines `>=22.12`; Vite 8 accepts ^20.19) | Prior phases built on it. `nvm use 22` if npm warns |
| git | holdout guard (clean/committed check), provenance | ✓ | repo at `feel-good-scorew/` | Guard degrades to a warning if git is missing |
| nflverse cache (schedules, pbp, sim) | freeze/holdout derive | ✓ (Phase 5 in progress) | — | `fgs build` |

**Dependency:** Phase 5 must be complete (11 factors in `RIDGE_SETS`, weights.yaml with 11 keys, BACKTEST_LOG rows). At research time Phase 5 executors are still modifying `pipeline/**`. Plans should reference the post-Phase-5 interfaces (`cli.cached_inputs()`, `derive(raw, **inputs)`), which already exist in cli.py.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥9.2 (pipeline), vitest 5 (web) |
| Config file | `pipeline/pyproject.toml [tool.pytest.ini_options]`, `web/package.json` scripts |
| Quick run command | `cd pipeline && uv run pytest tests/test_bootstrap.py tests/test_freeze.py tests/test_holdout.py tests/test_methodology.py -x -q` |
| Full suite command | `cd pipeline && uv run pytest -q` and `cd web && npm test && npm run check && npm run build` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BACK-04 | `fgs freeze` writes frozen yaml (tmp path). `load_weights` returns the 11 rounded weights, and the `fit` block has sign + k/19 with 0 ≤ k ≤ 19 | integration (real cache, tmp WEIGHTS_PATH) | `uv run pytest tests/test_freeze.py -x` | ❌ Wave 0 |
| BACK-04 | Freeze output is unchanged when ≥2022 results are swapped (sealing) | integration | same | ❌ Wave 0 |
| BACK-04 | Guards: `--propose-weights` refused when frozen; `freeze` refused without `--unfreeze`; `freeze --unfreeze` refused when HOLDOUT_RESULT.md exists; `--include-holdout` refused before the result exists | unit (monkeypatched paths) | same | ❌ Wave 0 |
| BACK-04 | Export/refresh never fit: `backtest.ridge_fit` monkeypatched to raise, export still succeeds | unit | `uv run pytest tests/test_export.py -k never_refits -x` | ✅ extend |
| MODEL-15 | Negative and ≈0 weights are kept; `-0.00` is normalized; no clipping | unit | `uv run pytest tests/test_freeze.py -k sign -x` | ❌ Wave 0 |
| BACK-05 | Bootstrap: identical predictors → diff CI exactly [0, 0]; deterministic for a seed; season-block distinct resamples = C(2k−1, k); stratified draw keeps per-season cluster counts; strong vs pure-noise predictor → diff lower bound > 0 | unit (synthetic) | `uv run pytest tests/test_bootstrap.py -x` | ❌ Wave 0 |
| BACK-05 | `evaluate_frozen` on stand-in 2018–2021 (fit ≤2017): schema complete, composite Spearman == `bt.spearman(Σ round(w)·z)`, Brier maps fit only on ≤ fit_last; raises for seasons > 2021 without `allow_holdout` | integration (training only) | `uv run pytest tests/test_holdout.py -x` | ❌ Wave 0 |
| BACK-05 | `fgs holdout` refuses when the result exists, weights aren't frozen, or prereg is missing/dirty (all with tmp paths; **never on the real holdout**) | unit | same | ❌ Wave 0 |
| BACK-06 | `verdict()` maps (diff, CI) → yes/slight/no exactly as pre-registered | unit | `uv run pytest tests/test_holdout.py -k verdict -x` | ❌ Wave 0 |
| BACK-06 | The real one-time result: HOLDOUT_RESULT.md exists, its commit postdates the PREREGISTRATION.md commit, and the verdict is recorded | manual/grep (verifier) | `git log --format='%H %ci' -- pipeline/PREREGISTRATION.md pipeline/HOLDOUT_RESULT.md` | n/a |
| SITE-07 | `methodology.json` in export files; factor weights == weights.yaml == meta.factors; `holdout: null` path works; notes' numbers match the evidence | unit | `uv run pytest tests/test_methodology.py tests/test_export.py -x` | ❌ Wave 0 / ✅ extend |
| SITE-07 | Router parses `#/methodology`; `records` still reserved; verdict/effect formatting helpers | unit (vitest) | `cd web && npx vitest run src/lib/router.test.ts src/lib/methodology.test.ts` | ✅ update / ❌ Wave 0 |
| SITE-07 | Page renders at 375px and 1280px, no horizontal scroll, chart whiskers visible, nav "How it works" active | manual (Playwright screenshot, as in prior phases) | `npm run build && npm run preview` + screenshot | manual |

### Sampling Rate
- **Per task commit:** quick run command above (the synthetic/stand-in tests are fast; real-cache freeze tests take about a minute).
- **Per wave merge:** full pipeline suite + `npm test && npm run check`.
- **Phase gate:** full suite green before the one-time `fgs holdout` task. The holdout task itself is not re-run by tests.

### Wave 0 Gaps
- [ ] `pipeline/tests/test_bootstrap.py`: synthetic bootstrap properties
- [ ] `pipeline/tests/test_freeze.py`: freeze output, sealing, guards, sign/rounding
- [ ] `pipeline/tests/test_holdout.py`: stand-in evaluator, guards, verdict
- [ ] `pipeline/tests/test_methodology.py`: schema + number consistency
- [ ] `web/src/lib/methodology.test.ts`: formatting helpers
- [ ] Update `web/src/lib/router.test.ts` (methodology no longer reserved) and `tests/test_backtest.py::test_weights_yaml_loads` (frozen file keys)

## Security Domain

`security_enforcement: false` in `.planning/config.json`. Section omitted. (Static site, no auth, no user input beyond the hash route, which is already regex-validated.)

## Sources

### Primary (HIGH confidence)
- Codebase (read this session): `pipeline/src/fgs/{backtest,score,export,cli,season_config,paths}.py`, `pipeline/weights.yaml`, `pipeline/BACKTEST_LOG.md`, `pipeline/tests/{test_backtest,test_leakage}.py`, `pipeline/.gitignore`, `web/src/{App.svelte,lib/router.ts,lib/route.svelte.ts,lib/data.ts,components/SiteHeader.svelte,components/HistoryChart.svelte}`, `web/package.json`, `.planning/phases/02-elo-mood-board/02-UI-SPEC.md` §Design System for Later Phases, 05-CONTEXT.md, 05-RESEARCH.md
- Observable Plot 0.6.19 typings and dist (`src/marks/rule.d.ts`, `dist/plot.umd.js` RuleY) in `web/node_modules`
- Prototype runs (training data only): `scratchpad/p6/boot.py` (stand-in CIs), `calib.py` (16-window coverage), `brier.py` (Brier CIs, two-stage), `logparse.py` (log parser on the current log); `bt.spearman` timing

### Secondary (MEDIUM confidence)
- General statistics knowledge: cluster bootstrap for dependent observations, the few-clusters problem (percentile bootstrap with very few clusters underestimates variance) [ASSUMED from training knowledge, consistent with the empirical coverage measured here]

## Metadata

**Confidence breakdown:**
- Freeze mechanics / guards: HIGH. Built on verified existing functions and file semantics.
- Bootstrap design and reporting: HIGH for behavior (measured on 16 training windows). MEDIUM on the "right" headline interval, which is a judgement call fixed in pre-registration.
- Methodology schema / page: MEDIUM-HIGH. Plot API verified in typings; layout not rendered.
- Pitfalls: HIGH. Most are verified in code (write_export, gitignore, router test, load_weights validation).

**Research date:** 2026-11-11
**Valid until:** Phase 5 completion changes `RIDGE_SETS`/`weights.yaml` (re-check interfaces), or 30 days.

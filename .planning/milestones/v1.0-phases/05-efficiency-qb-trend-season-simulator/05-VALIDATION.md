---
phase: 5
slug: efficiency-qb-trend-season-simulator
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-11-11
---

# Phase 5 — Validation Strategy

> Derived from 05-RESEARCH.md § Validation Architecture. Assumptions A1 (qb_trend = QB form level), A2 (σ=100 sim rating noise), A5 (post-REG playoff odds = actual participation) ACCEPTED by orchestrator (autonomous).


### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.2 (pipeline); vitest + svelte-check (web) |
| Config file | `pipeline/pyproject.toml [tool.pytest.ini_options]`; `web/package.json` |
| Quick run command | `cd pipeline && uv run pytest -q tests/test_pbp.py tests/test_efficiency.py tests/test_sim.py tests/test_features.py` |
| Full suite command | `cd pipeline && uv run pytest -q && cd ../web && source ~/.nvm/nvm.sh && nvm use && npm test && npm run check && npm run build` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-05 | `scrimmage` keeps pass/rush in wp [0.05, 0.95], drops spikes, kneels, no_play, null EPA, empty posteam | unit (synthetic plays) | `uv run pytest tests/test_pbp.py -k scrimmage -x` | ❌ Wave 0 |
| DATA-05 | `team_game_epa`: off/def/net hand-computed; primary QB = most dropbacks, scramble counted via passer_id fallback, tie → lowest id; low_confidence iff season ≤ 2000 | unit | `uv run pytest tests/test_pbp.py -k team_game -x` | ❌ Wave 0 |
| DATA-05 | Real cache: codes ⊆ CANONICAL; played games without pbp == known 3; rows == 2 × pbp games | integration (real_cache, skip if absent) | `uv run pytest tests/test_pbp.py -k real -x` | ❌ Wave 0 |
| MODEL-05 | adj_epa uses the opponent's *prior* EWMA (game 1 → opp term 0); epa_traj = EWMA − season mean; week 0 / no in-season games → 0; no-pbp game skipped | unit (hand-computed 3-game league) | `uv run pytest tests/test_efficiency.py -k epa_traj -x` | ❌ Wave 0 |
| MODEL-11 | qb_form follows the QB across teams/seasons; dropback-weighted; <2 starts → 0 + qb_new; week 0 → 0; QB change switches history | unit | `uv run pytest tests/test_efficiency.py -k qb -x` | ❌ Wave 0 |
| MODEL-13 | Σp == playoff_teams(season) for 1999 (31 teams, 12), 2010, 2020 (14), 2021 (17 games); Σexp_wins == REG games; deterministic for same (seed, season, week); input-order independent | unit (synthetic + real) | `uv run pytest tests/test_sim.py -x` | ❌ Wave 0 |
| MODEL-13 | Tiebreak chain on a hand-built 4-team division with forced outcomes (Elo ±2000, σ=0): h2h decides, then division %, then random ≈50/50 | unit | `uv run pytest tests/test_sim.py -k tiebreak -x` | ❌ Wave 0 |
| MODEL-13 | End-of-REG real seasons: ≥ 97% of team-slots match actual playoff participants (1999–2021) | integration (real) | `uv run pytest tests/test_sim.py -k field -x` | ❌ Wave 0 |
| MODEL-13 | model_version changes when n_sims/σ/Elo K/HFA changes; cache recomputes only digest-changed seasons | unit | `uv run pytest tests/test_sim.py -k version -x` | ❌ Wave 0 |
| MODEL-08 | win_totals mapping (OAK→LV, SD→LAC, STL→LA), per-season normalization, source tag vegas 2003–2020 / model otherwise; vs_exp formula hand-computed incl. ties, week 0 → 0 | unit | `uv run pytest tests/test_features.py -k vs_exp -x` | ❌ Wave 0 |
| MODEL-08 | r(model wk-0 exp_wins, Vegas) on 2003–2020 ≥ 0.7 | integration (real) | `uv run pytest tests/test_sim.py -k vegas_corr -x` | ❌ Wave 0 |
| MODEL-12 | po_trend = p(w) − p(max(w−3, 0)) same season; week 0 → 0 | unit | `uv run pytest tests/test_features.py -k po_trend -x` | ❌ Wave 0 |
| All | Fake-future/truncation leave epa_traj, qb_trend, vs_exp, po_trend, playoff_prob, exp_wins unchanged; fake future pbp aggregates change nothing; sim/efficiency/pbp never import backtest | integration | `uv run pytest tests/test_leakage.py -x` | ✅ extend |
| All | Report has ridge:+epa_traj … +po_trend; final N=8 Spearman in [0.523, 0.529]; BACKTEST_LOG has 4 new rows; weights.yaml loads 11 keys | integration + grep | `uv run pytest tests/test_backtest.py -x` | ✅ extend |
| Export | rows carry playoff_prob (int 0–100) + expectation_source; meta.factors has 11 entries; Σ points still == score − baseline | contract | `uv run pytest tests/test_export.py -x` | ✅ extend |

### Sampling Rate
- **Per task commit:** the quick run command.
- **Per factor step:** `uv run fgs backtest --propose-weights`, then compare against the Prototype Results table (±0.002).
- **Per wave merge:** full pipeline suite plus web tests.
- **Phase gate:** full suite green. `uv run fgs build` (cold: pbp 26 s + sims ~10 s) and `uv run fgs refresh` complete in under 2 min. Team page shows 11 factor bars and the playoff-odds stat. Then `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_pbp.py`: synthetic play frame fixture (≈20 plays over 2 games incl. spike, kneel, no_play, scramble with null passer_player_id, wp 0.97 play)
- [ ] `tests/test_efficiency.py`: 3-team, 2-season per-game fixture with known EPA values and a QB who changes teams
- [ ] `tests/test_sim.py`: tiny-league fixture with monkeypatched `divisions`/`playoff_teams` (the conftest pattern already monkeypatches season_config)
- [ ] Extend `test_leakage.py` FLOAT_EXACT via `features.FEATURE_COLUMNS`; extend the firewall list with `pbp.py`, `efficiency.py`, `sim.py`, `expectation.py`
- [ ] No framework installs


**Approval:** approved 2026-11-11 (autonomous)

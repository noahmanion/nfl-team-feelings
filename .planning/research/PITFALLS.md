# Pitfalls Research

**Domain:** NFL team rating ("feel-good score": momentum-weighted Elo-like rating, backtested against future results) plus a static visualization site
**Researched:** 2026-11-11
**Confidence:** MEDIUM overall. The data-quirk and leakage pitfalls are HIGH: they come from nflverse docs and well-known structural facts. The momentum evidence is MEDIUM: several studies agree, but none is a definitive NFL point-differential regression. Free sources for historical win totals are LOW and need checking.

> Phase names below are generic labels: Data Foundation, Core Rating, Factor Engineering, Backtest & Tuning, Offseason/Draft, Pipeline, Visualization, Aha Moments/Copy. Map them onto the real roadmap numbering.

---

## Critical Pitfalls

### Pitfall 1: Look-ahead leakage in "as-of" features

**What goes wrong:**
The score shown "after week 6 of 2013" quietly uses information from later games. Common leaks:
- **Opponent quality from the wrong date.** Using the opponent's end-of-season record or rating instead of their rating at kickoff of that game.
- **Full-season normalization.** Season-wide z-scores of EPA, or league averages computed over the full season.
- **Expectations built from all weekly spreads.** Deriving "preseason expectation" by summing implied win probabilities from every week's spread. Those lines were set in-season and already contain injury and form information.
- **Playoff odds from future data.** Simulating the rest of the season with ratings fitted on games that hadn't happened yet.
- **Bad target alignment.** Pairing the score after week k with a target window that includes week k itself.

The backtest then looks excellent and the live 2026 score underperforms it.

**Why it happens:**
Pandas makes `groupby(season).transform(...)` the easy path, and that call sees the whole season. Elo-style systems are sequential by nature, while vectorized feature code is not.

**How to avoid:**
- Build every feature with one function, `features_asof(team, season, week)`. It may only read games whose `gameday` is strictly earlier than the snapshot date. Make that the only path into the model.
- Compute opponent quality from the opponent's pre-game rating, stored in the sequential ratings table.
- Write one leakage unit test. Compute a snapshot, append fake future games with absurd scores, recompute, and assert the snapshot is unchanged. This is worth the effort even in a light-process repo.
- Targets always start at week k+1.

**Warning signs:**
- Backtest correlation with future margin beats the closing Vegas spread. Nobody beats the spread with box-score features, so this almost always means leakage.
- Performance in early weeks looks unusually good.
- The fake-future-game test changes any past value.

**Phase to address:** Core Rating (sequential design) and Backtest & Tuning (test plus market sanity check).

---

### Pitfall 2: Overfitting about 10 hand-tuned weights to correlated, noisy data

**What goes wrong:**
There are roughly 27 seasons × 32 teams × 17 games, about 14k team-week snapshots. That sounds like plenty. But the snapshots overlap heavily: last-16 record, current record, streak, margin and EPA trend are all strongly collinear, and consecutive weeks share most of their inputs. The effective sample is closer to a few hundred independent team-seasons.

Tuning 10 weights with a grid or optimizer on the full history produces confident weights that are mostly noise. Expect sign flips between eras, large offsetting weights (+streak, −record), and weights that move whenever one season is added.

**Why it happens:**
"Fixed, opinionated, but tuned" invites free optimization. Collinear inputs make individual weights unidentifiable even when total predictive power is fine.

**How to avoid:**
- **Fixed baselines first.** Before tuning anything, record these and treat any new factor as guilty until it beats them out-of-sample:
  - Pure Elo (538-style, K≈20, MOV multiplier)
  - Point differential per game
  - The closing spread, where it exists
- **Walk-forward validation.** Tune on 2002–2015, validate on 2016–2021, and leave 2022–2025 as a final holdout you look at once. Alternatively, roll season by season: fit on everything before season S, then score season S.
- **Constrain the fit.** Use ridge or other regularized regression, or a coarse grid over a few weights with the rest fixed by prior. Standardize every input first so the weights are comparable.
- **Collapse correlated inputs before fitting.** For example, combine "record + last-16 + streak" into one form block.
- **Report bootstrap intervals by season.** Resample seasons, not rows. A weight whose interval crosses zero is not a finding.

**Warning signs:**
- The optimum sits on a grid edge.
- Weights change sign between the train and validation eras.
- The in-sample gain over Elo is large but the out-of-sample gain is under about 1%.
- A tiny weight change reorders the top 5 teams.

**Phase to address:** Backtest & Tuning. The baselines also give the Core Rating phase a "done" criterion.

---

### Pitfall 3: Rewarding inputs that are known to be non-predictive (streaks, close-game record), done dishonestly

**What goes wrong:**
The user wants streaks and close-game results as inputs. The evidence says:
- **Streaks.** Once team strength is controlled for, streaks add little or nothing. Bettors overvalue streaking teams (Alberta working paper), yet fading streaks isn't reliably profitable either, which suggests the market roughly prices them correctly as near-zero. Playoff "momentum" regressions find team strength significant and streaks not.
- **Close-game record.** Record in one-score games is close to a coin flip year to year. Teams that go 8-2 in one-score games regress the next season. This is the standard Pythagorean / "luck" result.
- **Win-loss record vs point differential.** W-L is a noisier predictor of future results than point differential, and EPA/success rate is less noisy still.

If streak and close-game wins get positive weights because the user likes them, the score stops being "honest". The core value ("you should feel X, and it's predictively true") breaks, and the backtest will show it.

**Why it happens:**
Fan intuition, and the product's own framing ("momentum"), pull toward rewarding hot teams.

**How to avoid (the honest handling):**
1. **Let the backtest set the sign.** Never constrain streak or close-game weights to be positive. Close-game luck should probably get a negative weight: an 8-2 team with +12 point differential should feel worried. That is the product's best "aha" moment, so frame the input as a corrective rather than a reward.
2. **Split the output into two layers:**
   - **Feel-good score:** the predictive, backtested number.
   - **Vibes/mood layer:** streaks, "won 4 straight", nail-biters. Shown as colour commentary and labelled as "how it feels" vs "how it is".

   The gap between the two is the product.
3. **If the user insists on a positive streak weight,** cap it (e.g. ≤5% of score variance) and state on the methodology page that it was added for flavour and costs X% of predictive accuracy. Measure that cost.
4. **Fix "momentum" to mean trajectory, not raw form.** Use the slope of opponent-adjusted EPA over the last 4–8 games, which is at least plausibly predictive. Streak length is not that.

**Warning signs:**
- Adding streak or close-game inputs with positive weights lowers out-of-sample accuracy.
- A team at 7-3 with negative point differential ranks top-5.

**Phase to address:** Factor Engineering (define inputs as signed and neutral), Backtest & Tuning (empirical sign), Visualization/Copy (score vs vibes split).

---

### Pitfall 4: Franchise identity breaks across relocations and expansion

**What goes wrong:**
nflverse schedules use the abbreviation of the era: OAK→LV (2020), SD→LAC (2017), STL→LA (2016). `nflreadr::clean_team_abbrs()` maps to current location by default, and Python code needs an equivalent mapping. Keyed on raw `home_team`, the following break:
- the Raiders' last-16 window, Elo carry-over, "600 days miserable" streaks and history charts all split at the move;
- joins to draft and win-total tables, which use different abbreviation sets (e.g. LAR vs LA, JAC vs JAX, CLV vs CLE in some sources), silently drop rows.

Expansion causes more breaks:
- **HOU** has no games before 2002.
- **CLE** re-entered in 1999 with no prior rating.
- **1999–2001** had 31 teams and different divisions. The 2002 realignment changed the division structure, which matters for playoff-odds simulation.

**Why it happens:**
Abbreviations look like stable keys but aren't.

**How to avoid:**
- Create a `franchise_id` once, in the Data Foundation phase, keyed to the current abbreviation (LV, LAC, LA). Keep `display_abbr`/`display_name` per season for labels ("St. Louis Rams 2003").
- Normalize every external source through one mapping function, and assert there are no unmatched abbreviations after each join.
- Seed expansion teams (HOU 2002, CLE 1999) at a below-average expansion rating. 538 used about 1300 vs a 1505 mean. Mark the first ~16 games as low-confidence.
- Store the season → division/conference map from a table, not hard-coded constants. nflseedR's divisions data shows the pre-2002 structure.

**Warning signs:**
- More than 32 distinct teams in any season after 2002, or more than 31 in 1999–2001.
- A team's history chart has a gap or reset in 2016, 2017 or 2020.
- Row counts drop after merges.

**Phase to address:** Data Foundation.

---

### Pitfall 5: Season-length, ties, cancelled games and neutral sites handled ad hoc

**What goes wrong:**
- **17 games since 2021, 16 before.** Raw win counts, "wins vs preseason total" and "worst season ever" are not comparable across the change, and week numbers shift (18 regular-season weeks).
- **Ties are rare but real** (e.g. 2016 SEA–ARI, 2018 CLE–PIT, 2022 NYG–WAS, plus others). Code that treats `result == 0` as a loss, or drops ties, corrupts records and streaks.
- **2022 BUF–CIN (Hamlin)** was cancelled, so BUF and CIN played 16 games. A game row with no result can crash streak or window code.
- **Neutral sites.** International games (London, Mexico, Germany, Brazil, etc.), Super Bowls, and one-off relocations (2005 Saints, 2012 Giants/Bucs) still list a "home" team. Applying home-field advantage there is wrong. nflverse schedules have a `location` field ("Home"/"Neutral").
- **Home-field advantage changes over time.** It was roughly 2.5–3 points in the 2000s, near zero in 2020 (empty stadiums), and roughly 1.5–2 since. A constant value biases the Elo.
- **2001 week shift after 9/11,** and playoff games (`game_type` WC/DIV/CON/SB) mixed in with regular-season games.

**How to avoid:**
- Normalize records to win% everywhere a cross-season comparison happens. Treat a tie as 0.5 in Elo and win%.
- Define the streak rule explicitly. Recommended: a tie ends the streak.
- Filter on `result.notna()` and never on week number.
- Read `location` for home-field advantage, and estimate HFA per era. Rolling league-average home margin is fine.
- Decide whether playoffs count toward last-16. Recommendation: yes for the rating, with a slightly higher K for playoff games as 538 did. Make it an explicit flag either way.

**Warning signs:**
- Any team-season with games ≠ 16/17 other than BUF/CIN 2022.
- Super Bowl winners get a home boost.
- 2020 home teams are systematically over-predicted.

**Phase to address:** Data Foundation (flags/normalization) and Core Rating (HFA).

---

### Pitfall 6: Between-season continuity — a naive last-16 window ignores the offseason

**What goes wrong:**
A rolling window across seasons carries a team's late-season form into September. That form came from a roster that may have lost its QB, coach or a dozen starters. Ratings that don't regress overrate last year's good teams and underrate last year's bad ones. Year-to-year NFL team strength correlation is only moderate: point differential correlation is roughly 0.3–0.5 year to year (MEDIUM confidence; widely cited range).

There is also the opposite failure. Resetting everyone to the mean in week 1 throws away real information and makes September scores meaningless.

**How to avoid:**
- Regress the slow strength term toward the mean at the season boundary. 538 used one third toward 1505. Fit the fraction in backtest. Also exponentially decay the last-16 contribution of prior-season games rather than weighting them equally.
- Blend in the preseason expectation (win total) as the week-0 prior, if you have it (see Pitfall 7). It already encodes QB changes, free agency and draft, which is exactly what this project can't model for free.
- **QB change is the single largest offseason effect.** If you add only one offseason adjustment beyond the draft, make it "starting QB changed". It can be derived from nflverse rosters or PBP passer data.

**Warning signs:**
- Week-1 backtest error is much larger than week-8 error.
- Last year's 13-4 team that lost its QB ranks top-3 in September.

**Phase to address:** Core Rating (regression) and Offseason/Draft.

---

### Pitfall 7: Preseason win totals and playoff odds are not in nflverse

**What goes wrong:**
- **Win totals.** nflverse schedules include game-level `spread_line`/`total_line`, but no preseason season-win totals. Free historical win totals exist on odds-history sites, with patchy coverage of early years (LOW confidence on completeness back to 1999). They may need scraping, which can break and may conflict with the sites' terms.
- **Shortcut that leaks.** Summing in-season spread-implied probabilities leaks (Pitfall 1).
- **Playoff odds.** No free week-by-week historical playoff odds exist. They have to be simulated:
  - nflseedR does this properly, including tiebreakers, but it is R-only.
  - A Python rewrite with full NFL tiebreakers is a rabbit hole.
  - Formats changed: 12-team playoffs before 2020, 14 since. Divisions changed in 2002.
  - Cost: simulations × ~18 weeks × 27 seasons × 32 teams. 10k sims each is a lot in pure Python.

**How to avoid:**
- **Expectations.** Source win totals for whatever years are available. For missing years, fall back to a model prior: last season's regressed rating converted to expected wins. Store a `expectation_source` column so the UI can disclose it. Never use in-season lines as the "preseason" number.
- **Playoff odds.** Simplify. Use the rating to simulate the remaining schedule with simple tiebreakers (win% → point differential → coin flip). Use about 1–2k sims, vectorized in NumPy. Accept roughly ±3–5 percentage points of error vs proper tiebreakers. Alternatively, shell out to nflseedR once for history and cache the results. Handle the 2020 format change from a table.
- **Measure the playoff-odds-trend input separately.** It is mostly a derivative of the rating itself and carries little new information (circular input). Expect the backtest to give it about zero weight. Consider dropping it from the score and using it for display only.

**Warning signs:**
- Expectation input missing for some seasons and silently filled with 0 or the mean.
- Playoff simulation takes hours.
- Playoff-odds trend correlates more than 0.9 with the rating's own change.

**Phase to address:** Data Foundation (win totals sourcing decision) and Factor Engineering (playoff simulation scope).

---

### Pitfall 8: Draft-capital term rewards tanking and has little measurable signal

**What goes wrong:**
Draft value charts (Jimmy Johnson, Rich Hill, Fitzgerald–Spielberger, Baldwin/OTC surplus value) all give the most value to the highest picks. The highest picks go to the worst teams. So a naive "draft capital" bump is a tanking reward, which the project explicitly rules out.

There are three further problems:
- The empirical effect of one draft class on next-season wins is small. Rookies, even top picks, rarely swing team results much in year one (QB excepted, and sometimes negatively).
- The Jimmy Johnson chart overvalues top picks relative to realized value, according to Massey–Thaler and later surplus-value work.
- Traded picks and future picks complicate "capital".

**How to avoid:**
- Use a surplus-value chart (Baldwin/OTC style, flatter curve) rather than the Jimmy Johnson chart.
- **Measure draft value relative to slot.** Example: value gained via trade-ups/downs and extra picks vs the team's original slot allotment. This rewards smart drafting, not losing. Alternatively, scale the bump by an "expected capital for your record" residual.
- Keep the term small and backtest it against next-season rating change. If it shows no signal, keep it as offseason display text ("Added 3 top-50 picks") rather than a score mover.
- Make sure the offseason score has defined movement points: regression at season end, then a draft-week update. Otherwise the history chart shows a flat line for seven months.

**Warning signs:**
- Worst teams rise to mid-pack every May.
- The draft term's backtest weight is about zero, or its sign is unstable.

**Phase to address:** Offseason/Draft.

---

### Pitfall 9: EPA trend is noisy, contaminated, and changes character in early years

**What goes wrong:**
- **Small samples.** Per-game EPA/play rests on roughly 55–70 plays per side, so a "trend" slope over 3–4 games is mostly noise.
- **Contamination.** Raw EPA includes garbage time, kneels, spikes, and special teams if not filtered.
- **No opponent adjustment.** Beating up bad defenses looks like improvement.
- **Early seasons.** nflfastR dropped official support for 1999–2000 because the data sources were inconsistent. CPOE/xYAC exist only from 2006, and scramble identification for 1999–2004 was added late. Any QB-play metric built on CPOE is unavailable before 2006.
- **Model leakage.** The EPA model was itself fit on many seasons, which is minor leakage. It is acceptable and should be noted.

**How to avoid:**
- Filter to plays where `pass == 1 | rush == 1`, and either restrict to win probability between 0.05 and 0.95 or down-weight plays outside it. Exclude `qb_kneel`/`qb_spike`.
- Opponent-adjust with simple iterative or ridge adjustment, computed as-of (Pitfall 1).
- **Trend over level:** use an EWMA (half-life around 4–6 games) minus the season-to-date average, or a shrunk slope. Raw week-over-week deltas are too noisy.
- **QB trend:** use EPA/dropback plus success rate, which work for all years. Skip CPOE, or use it only from 2006 and accept a feature-set break.
- Consider starting the tuned backtest at 2001 or 2002, while still displaying 1999+ scores with a lower-confidence flag.

**Warning signs:**
- The EPA-trend factor swings the score wildly week to week.
- The QB factor is NaN before 2006.

**Phase to address:** Factor Engineering.

---

### Pitfall 10: Choosing a noisy or circular backtest target

**What goes wrong:**
- **Next-N win% is very noisy.** With N=4, win% takes only five values and luck dominates. Tuning to it amplifies Pitfall 2.
- **Mismatched windows.** Targets that span a season boundary (week 16 to the next season's week 3) mix in roster turnover. Tuning the late-season weights to that is inconsistent with the rest of the backtest.
- **Circular targets.** Using "future rating" or future playoff odds as the target is self-referential.

**How to avoid:**
- **Primary target:** opponent- and HFA-adjusted average point margin over the next 4–8 games, within the same season. Margin is far less noisy than W/L.
- **Secondary checks:** next-game win (log loss / Brier vs Elo and vs spread) and rest-of-season win%.
- Report results separately for each week bucket (1–4, 5–9, 10–18) and for in-season vs cross-season targets.
- Agree on the single primary metric before tuning, and write it in the README.

**Warning signs:**
- Weight conclusions change when N changes from 4 to 8.

**Phase to address:** Backtest & Tuning, with the target defined at the start of that phase.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Vectorized season-level features instead of an as-of loop | Fast, easy pandas code | Silent leakage; backtest lies | Never for model inputs. Fine for display-only stats. |
| Keying on raw team abbreviation | Quick joins | Relocation splits, dropped joins | Never. Add `franchise_id` on day one. |
| Simplified playoff tiebreakers | Avoids a nflseedR port | ±few pp error in odds | Acceptable. Disclose it. |
| Hard-coding 16/17 games, 12/14 playoff teams, divisions | Less code | Bugs at 2002, 2020, 2021 boundaries | Never. Use a season-config table. |
| Model-prior fallback for missing win totals | Unblocks the expectation input | Expectation partly circular for early years | Acceptable if flagged per season. |
| Tuning on all years without a holdout | More data | Unverifiable weights | Never. Hold out 2022–2025. |
| Caching nflverse parquet locally with no refresh logic | Fast iteration | Stale data, missed stat corrections | Fine during dev. Weekly pipeline must force-refresh the current season. |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| nflreadpy | Assuming it returns pandas | It returns Polars DataFrames (MEDIUM confidence; verify against the current version). Convert explicitly with `.to_pandas()` or commit to Polars. Don't mix them. |
| nflverse schedules | Treating future/unplayed games (NaN `result`) as data | Filter `result.notna()`. In-season, the weekly refresh sees a partial week until MNF is final, so run it Tuesday. |
| nflverse PBP | Pulling all 27 seasons of PBP every week | Cache historical seasons once. Refresh only the current season. |
| nflverse abbreviations | Assuming one canonical set across loaders | Run every source through one normalize function. Assert there are no unmatched abbreviations. |
| Odds-history sites (win totals) | Scraping on every run | Scrape once into a checked-in CSV with a `source` column. Fill in the current season manually. |
| nflseedR (if used) | Adding an R runtime to the weekly pipeline | Use it once offline for historical playoff odds. Use a simple Python sim for the live season. |
| Team colors (`load_teams`) | Using `team_color` for 32 lines at once | See UX: highlight one team, gray the rest. |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Python-loop Monte Carlo playoff odds for every historical week | Hours to rebuild | Vectorize in NumPy, use ~1–2k sims, cache historical results | ~27 seasons × 18 weeks × 10k sims |
| Loading full PBP (~1.3M+ plays, many columns) for each feature | Memory blowups, slow runs | Select needed columns, aggregate to team-game once, cache team-game parquet | Immediately on a laptop with all seasons |
| One giant static JSON with every team-week-factor | Slow first paint, multi-MB download | Split files: `latest.json` (home), `team/{id}.json` (deep-dive), compact `history.json` (scores only) | Over ~5 MB |
| Grid search over 10 weights | Combinatorial explosion | Ridge regression or coordinate search on standardized inputs | More than 4 weights |

## Security Mistakes

Low-stakes static site; the risks are minor.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Using NFL logos and trademarks on a public Vercel deploy | Takedown or trademark complaint | Use text abbreviations and colours, and avoid official logos, if deployed publicly |
| Committing scraped odds data with a source's terms violated | ToS issue | Keep the scraped CSV local or cite sources. Check terms before redistributing. |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| 32 coloured lines on the mood-over-time chart | Unreadable spaghetti, and team colours collide (many navy/red teams) | Gray all lines, highlight the hovered or selected team in its colour. Offer small multiples by division (8×4). |
| Truncated or auto-scaled y-axis on a team deep-dive | Tiny changes look dramatic and the team "collapses" | Fixed league-wide y-range. Show a league-average reference line. Use a diverging scale centred at neutral. |
| Score with no units or scale | "62" means nothing | Express it as a percentile among teams, or an Elo-like scale with labelled bands. Tie mood labels to fixed thresholds. |
| Offseason gaps drawn as continuous lines | Misleading straight lines across seven months | Break lines at season boundaries. Show draft-week steps explicitly. |
| Mood labels that flip every week | Feels random and erodes trust | Hysteresis on label thresholds. Use the smoothed score for labels. |
| Factor breakdown that doesn't add up to the score | Users can't trust the explanation | Use an additive model (score = Σ weight × standardized factor) and show it as a waterfall. Avoid non-additive transforms that break attribution. |
| Not showing the "how it feels vs how it is" gap | Loses the main hook | Put record / streak "vibes" next to the predictive score, and make the gap the headline for each team. |
| Era comparisons without normalization | "Saddest ever" is biased toward 16-game or 31-team eras | Use win% and z-scores within season. Footnote era differences. |

## "Aha Moments" Pitfalls (Shareable Insights)

- **Multiple comparisons.** With 32 teams × ~500 weeks, extremes will always exist. "Most miserable stretch" depends heavily on the threshold and on how the window is defined. Fix the definitions before mining, and show the threshold in the copy.
- **Garbage-in extremes.** The most extreme values often come from data bugs: relocation splits, expansion seeds, the 1999–2000 PBP issues, the BUF–CIN no-contest. Inspect the top 10 of every extreme manually before publishing.
- **"8-2 but worried" needs an evidence line.** Pair it with a historical base rate, e.g. "teams in this spot went 52% the rest of the way". Otherwise it reads as a hot take.

## "Looks Done But Isn't" Checklist

- [ ] **Franchise mapping:** verify exactly 32 franchises after 2002 (31 for 1999–2001), and that LV, LAC and LA have unbroken histories.
- [ ] **Leakage test:** verify that appending fake future games changes no past snapshot.
- [ ] **Baselines:** verify the backtest table shows Elo, point-differential and spread rows next to the feel-good score.
- [ ] **Holdout:** verify 2022–2025 was evaluated once, after tuning was frozen.
- [ ] **Sign check:** verify the fitted signs of the streak and close-game weights are reported, not assumed.
- [ ] **Ties/cancelled:** verify ties count as 0.5 and BUF/CIN 2022 have 16 games without crashing.
- [ ] **Neutral sites:** verify no HFA is applied when `location == "Neutral"`, and that 2020 HFA is about 0.
- [ ] **Expectations:** verify every season has an `expectation_source`, with no silent zeros.
- [ ] **Offseason:** verify the score moves at season-end regression and at the draft, and that the worst team doesn't jump simply for picking #1.
- [ ] **Weekly refresh:** verify it runs on a partial week (Thursday through Sunday played, MNF pending) without corrupting the window.
- [ ] **Charts:** verify the y-range is fixed league-wide and lines break at season boundaries.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Leakage discovered after tuning | HIGH | Rewrite features as-of, rerun the backtest, discard all tuned weights |
| Overfit weights | MEDIUM | Re-fit with ridge and walk-forward. Fall back to Elo plus 2–3 robust factors. |
| Franchise split | LOW–MEDIUM | Add `franchise_id` mapping and recompute (cheap if the pipeline is deterministic) |
| Streak/close-game inputs hurt accuracy | LOW | Move them to the vibes layer. Set the score weight to 0 or negative. |
| Draft term rewards tanking | LOW | Switch to slot-relative value or display-only |
| Playoff sim too slow | LOW | Fewer sims, vectorize, cache history |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Franchise identity / expansion / realignment | Data Foundation | Team-count asserts per season; unbroken LV/LAC/LA histories |
| Season length, ties, cancelled, neutral, HFA era | Data Foundation + Core Rating | Games-per-team asserts; neutral-site HFA = 0 check |
| Win totals / playoff odds sourcing | Data Foundation + Factor Engineering | `expectation_source` coverage table; sim runtime under a few minutes |
| Look-ahead leakage | Core Rating + Backtest | Fake-future-game test |
| Cross-season continuity | Core Rating + Offseason | Week-1 vs week-8 error comparison |
| EPA noise / early-year data | Factor Engineering | Factor week-to-week volatility; NaN audit by year |
| Non-predictive inputs (streak, luck) | Factor Engineering + Backtest + Viz | Signed weights reported; score vs vibes split in UI |
| Overfitting weights | Backtest & Tuning | Walk-forward plus holdout beats Elo baseline; bootstrap CIs |
| Target choice | Backtest & Tuning (start) | Primary metric written in the README before tuning |
| Draft rewards tanking | Offseason/Draft | Worst team's May score doesn't jump by more than a small cap |
| 32-team chart clutter, misleading scales | Visualization | Highlight-on-hover; fixed y-range; season breaks |
| Aha-moment cherry-picking / data-bug extremes | Aha Moments/Copy | Manual top-10 review; base-rate line on each insight |

## Sources

- nflreadr `clean_team_abbrs` docs (`current_location` maps OAK→LV, etc.): https://search.r-project.org/CRAN/refmans/nflreadr/html/clean_team_abbrs.html and tests at https://rdrr.io/cran/nflreadr/src/tests/testthat/test-utils_name_cleaning.R (HIGH)
- nflreadr `team_abbr_mapping`: https://rdrr.io/cran/nflreadr/man/team_abbr_mapping.html (HIGH)
- nflfastR NEWS (1999–2000 support dropped; scramble ID 1999–2004 added): https://nflverse.r-universe.dev/nflfastR/NEWS.txt (HIGH)
- nflfastR README (cp/CPOE/xYAC from 2006): https://cran.r-project.org/web/packages/nflfastR/readme/README.html (HIGH)
- nflseedR divisions (pre-2002 structure): https://rdrr.io/github/nflverse/nflseedR/src/data-raw/divisions.R (HIGH)
- Hot hand / streak betting, NFL (Alberta working paper): https://sites.ualberta.ca/~econwps/2011/wp2011-16.pdf (MEDIUM)
- Kennesaw State streak ATS study (era-unstable results): https://campus.kennesaw.edu/colleges-departments/coles/research/docs/fall-2017/fall17-02.pdf (MEDIUM)
- "The Myth of Momentum" (playoff momentum not significant after strength): https://www.si.com/2014/12/11/nfl-postseason-momentum-myth (MEDIUM)
- On the existence of momentum in professional football (PLoS ONE 2022): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9173601/ (MEDIUM; in-game momentum, conclusions not reviewed in full)
- These come from training knowledge and should be checked before they are relied on (LOW–MEDIUM):
  - 538 NFL Elo methodology: K=20, 1/3 regression to 1505, expansion seed about 1300, QB adjustment, playoff K bump.
  - One-score-game record regresses toward .500.
  - Pythagorean expectation exponent about 2.37.
  - Massey–Thaler on draft-pick overvaluation.
  - Baldwin/OTC surplus-value chart.
  - nflreadpy returns Polars.

---
*Pitfalls research for: NFL momentum-weighted team rating + static viz*
*Researched: 2026-11-11*

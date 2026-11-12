# Feature Research

**Domain:** NFL team rating / power-ranking visualization, with a "how should fans feel" layer on top
**Researched:** 2026-11-11
**Confidence:** MEDIUM. Competitor feature sets were checked against live sites and search results (nfelo, ESPN FPI, Neil Paine, Silver Bulletin, ESPN Misery Index). The FiveThirtyEight NFL interactives are offline, so their description comes from training data plus the archived data mirrors. Recommendations on what users value come from judgment, not from user research.

## Landscape Snapshot (what exists today)

| Product | Status (Nov 2026) | Core display | How it explains the rating |
|---------|-------------------|--------------|----------------------------|
| FiveThirtyEight NFL Elo | **Dead.** ABC shut 538 in March 2025 and later removed the archives. The data survives on mirrors (datahub.io, GitHub). | Ranked table (Elo, QB-adjusted Elo, playoff/SB odds), per-game win probabilities, and a "Complete History of every NFL team" Elo-over-time line chart | Pregame Elo plus explicit adjustments in Elo points (QB, rest, travel, HFA), each shown as a separate number. This additive "points" language worked well for non-experts. |
| nfelo (nfeloapp.com) | Active, open source | Power-rankings table with Elo, point differential, EPA splits; EPA tiers scatter (off x def); per-team pages; win-total "implied strength"; public model-performance/backtest page | Shows Elo next to the supporting stats (EPA off/def, margin) without a formal decomposition. Publishes its track record. |
| ESPN FPI | Active | Ranked table with FPI, projected W-L, playoff/division/SB/top-pick odds, a separate "efficiencies" view | **Decomposes into Offense + Defense + Special Teams**, each in points vs an average team. This is the most widely seen decomposition pattern. |
| rbsdm.com | Active (nflverse community) | EPA/play off vs def tier scatter, team and QB tables, filters | The 2D scatter is the explanation: "good offense, bad defense" is visible at a glance. |
| Neil Paine Substack / Silver Bulletin (ELWAY, QBERT) | Active, partly paywalled | Weekly Elo/power-rating tables, projections, QB ratings | Prose plus tables. The successor to the 538 approach with a QB adjustment. |
| PFF / The Athletic power rankings | Active, mostly editorial or paywalled | Ranked list with a written blurb per team and an up/down arrow from last week | Explained by a writer's narrative per team. Arrows plus blurbs are the format most fans recognize. |
| ESPN Sports Misery Index | Periodic editorial feature | Ranked list of the most miserable fanbases | Score built from titles, playoff droughts, heartbreaks, and rival success, weighted to recent events. **This is the closest analog to the "saddest fanbase" angle.** |

**Key gap this project fills:** every existing product answers "how good is this team?" (strength or prediction). None answers "how should I feel right now, given momentum, expectations, and luck?" None of them puts the **gap between the record and the underlying truth** at the center. With 538 gone, there is also no free, pretty, long-history "every team over time" chart.

## Feature Landscape

### Table Stakes (Users Expect These)

Fans arriving from power rankings or 538 assume these exist. Without them the site reads as a toy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **League mood board: all 32 teams ranked by score** | Every product (FPI, nfelo, 538, PFF) opens with a ranked list | LOW | Table or card grid. Columns: rank, team (logo/colors), score, mood label, record, week-over-week change. |
| **Week-over-week movement indicator (up/down arrows, change in rank and score)** | Universal in power rankings. It answers "what changed this week?", which is the reason people come back weekly. | LOW | Store the previous week's snapshot in the JSON. Cheap to add and high in engagement. |
| **Record shown next to the score** | Users anchor on W-L, and the whole premise is contrasting score with record | LOW | Prerequisite for the perception-gap callouts. |
| **Team identity: name, abbreviation, colors, logo or color chip** | Fans find their team visually, not by reading | LOW | nflverse `load_teams()` provides colors and logo URLs. Hotlinking logos is fine for a local prototype. Color chips avoid licensing worries if deployed. |
| **Team deep-dive page/panel (click a team)** | FPI, nfelo, and 538 all have per-team views | MEDIUM | Score, label, record, factor breakdown, season chart, recent games list. |
| **Factor breakdown in plain language** | Users distrust black-box numbers. FPI's off/def/ST split set the expectation that a rating can be decomposed. | MEDIUM | See "Explaining the score" below. **Requires the model to be additive** (weighted sum of normalized factors) so each factor contributes N points. |
| **Recent games list with results and per-game score change** | 538 and nfelo show game-by-game logs. Fans want to know "which game tanked us?" | LOW | Opponent, score, W/L, change in feel-good score. Directly links cause to effect. |
| **Score-over-time chart for a team (current season)** | 538's history chart and every Elo product have one | MEDIUM | Line chart by week. Add a league-average reference line and a shaded "mood band" background. |
| **Methodology / "how this works" page** | Any rating product without one is ignored by the analytics crowd. nfelo and 538 both publish theirs. | LOW | One page: inputs, weights, backtest result, data source (nflverse). Fixed weights make this easy to state honestly. |
| **"Last updated: Week N, date" stamp** | Weekly-refresh products must show freshness | LOW | Write it into the JSON at pipeline time. |
| **Mobile-friendly layout** | Most sports traffic is on phones, and shared links open on phones | LOW-MEDIUM | Board becomes a vertical list. Charts must not need hover to be useful (tap targets, visible labels). |
| **Season selector / history browsing** | Coverage back to 1999 is a stated feature, so users expect to view past seasons | MEDIUM | Week + season scrubber on the board ("What was the mood board in Week 10 of 2007?"). The data volume is small: about 27 seasons x 18 weeks x 32 teams ≈ 15k rows, fine as static JSON split per season. |

### Differentiators (Competitive Advantage)

These line up with the Core Value: an honest, momentum-weighted corrective to fan perception.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Perception-gap callout ("8-2 but you should feel worried")** | **The signature feature.** No competitor frames the gap between record and evidence as the headline. | MEDIUM | Needs a defined "naive feeling" baseline. Sentiment data is out of scope, so use **record-implied rank (win% rank) vs score rank**, or record vs preseason-expectation. Flag teams where the gap is at least about 8 ranks or beyond a z-score threshold. Template copy: "{record} but you should feel {label}". |
| **Playful mood labels over serious charts** | Gives a shareable identity ("We're in *Refreshing draft mocks* territory"). Power rankings have blurbs but no named emotional tiers. | LOW | Use about 7-9 tiers keyed to **percentiles of the historical score distribution**, not raw values, so labels mean the same thing across eras. Keep the labels in one config file. One label per tier, with optional flavor variants. |
| **Mood-over-time chart across seasons (1999 to now)** | Fills the hole left by 538's "Complete History" chart. Shows eras, dynasties, and droughts. | MEDIUM-HIGH | Continuous x-axis by date (not week index) so offseasons appear as gaps or drift. Mark season boundaries. Highlight the selected team over gray "spaghetti" lines for the rest of the league. About 27 seasons x 32 teams of points is fine for SVG/canvas. |
| **Duration callouts ("miserable for 600 straight days")** | Funny, specific, very shareable, and nobody computes it | MEDIUM | Needs a **score defined on every calendar day**, carrying forward between games and updating on draft day. Compute the current and longest streaks spent in each mood tier, in days and in games. |
| **Historical extremes / records page ("saddest fanbase ever")** | The data-driven answer to ESPN's Misery Index, and it gets shared | MEDIUM | Lowest and highest single-week scores, longest misery and joy streaks, biggest single-week swings, biggest perception gaps ever (e.g. the best "you should be worried" team that then collapsed). Precompute in the pipeline into `records.json`. |
| **"Biggest movers" and "Reality checks" weekly strip on the home page** | Gives repeat visitors a reason to come back each week | LOW | Top 3 risers and fallers plus the top 3 perception gaps. Derived from data that already exists. |
| **Offseason draft reaction** | Every other rating sits frozen from February to September. A score that moves on draft night gives the site an offseason heartbeat. | MEDIUM | Draft capital via a value chart (e.g. Jimmy Johnson, Rich Hill, or Chase Stuart AV-based). **Must not reward tanking** (see Pitfall below): score value above slot or the trade-up/down delta, or cap the bump. Show it as a dated event on the timeline: "Draft: +2.1". |
| **Backtest transparency ("does this score predict anything?")** | nfelo earns trust by publishing performance. "You should feel better" only holds if it predicts, which is the Core Value. | LOW-MEDIUM | One chart on the methodology page: score-decile vs next-N-games win%, compared with record alone. The pipeline already produces this, so it costs little to display. |
| **Factor breakdown as a waterfall / diverging bar** | Clearer than FPI's three-number split. Shows *why* in one glance: "Close-game luck is propping you up (+6), EPA trend is dragging you down (-9)". | MEDIUM | Diverging horizontal bars centered on the league average, sorted by absolute contribution, each with a one-line plain-English sentence. |
| **Auto-generated one-line team summary** | Replaces a power-ranking writer's blurb at no cost | LOW-MEDIUM | Template from the top positive and top negative factors: "Riding a 4-game streak, but the efficiency trend says regression is coming." Use rule-based templates, not an LLM. |
| **Shareable deep links (`#/team/BUF/2026/w10`)** | Callouts only spread if the link opens the exact view | LOW | Hash routing on a static site. Deep links are enough for a prototype. |
| **Share card image (OG image per team)** | Nice-looking previews on X/Reddit/iMessage | MEDIUM-HIGH | Needs build-time image generation (e.g. Python + Pillow, or Satori on Vercel). **Defer.** Deep links plus "copy text" deliver about 80% of the value. |
| **"My team" pin (localStorage)** | Most visitors care about one team. Pinning it to the top makes the board personal. | LOW | No accounts. localStorage only. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| User-tunable weight sliders | "Let me build my own model" | Already out of scope. It destroys the single honest answer and makes backtest claims meaningless. | Fixed, backtested weights explained on the methodology page |
| Game picks / against-the-spread predictions / betting odds | Every Elo site does picks | Changes the product into a betting tool, invites "your model went 7-9 ATS" scrutiny, and the score is not optimized for spreads | At most, show "score favors X" on upcoming games, labeled as mood rather than a pick (v2 at best) |
| Fan sentiment ingestion (Reddit, Trends, polls) | "Compare what fans feel to what they should feel" | Out of scope. Scraping is fragile and it contradicts the corrective premise. | Use record-implied rank as the "naive feeling" proxy |
| Live / in-game updates | Real-time feels modern | Out of scope. It needs a backend and live data, and the score is meant as a weekly reflection. | Weekly static JSON refresh with a visible "last updated" stamp |
| Accounts, comments, voting | Community engagement | Moderation, auth, and backend work in a graveyard-sized project | Deep links, so the conversation happens on Reddit/X |
| Decimal-precision scores (e.g. 1587.34) | Feels rigorous | False precision. Users fixate on meaningless changes. | Integer 0-100 scale (or Elo-like integer), labels carry the meaning |
| Too many factors shown at equal visual weight | "Show everything" | Ten factors as ten equal bars is noise. Non-experts drown. | Sort by contribution, show the top 3-4 with sentences, collapse the rest under "all factors" |
| Per-player / WAR breakdowns | PFF-style depth | Paid data is out of scope, and it is scope creep | A team-level QB play trend factor only |
| Tanking "hope" bump | Bad teams' fans want hope | Explicitly excluded. It rewards losing. | Draft reaction measured as value above slot, capped |
| Free-agency reaction | Offseason news cycle | Deferred. Contract-value data is messy. | v2 |
| Dark-pattern engagement (push notifications, email capture) | Retention | Not a product, it's an experiment | None |

## Explaining the Score to Non-Experts (pattern synthesis)

What works, in order of evidence strength:

1. **One common unit for every factor.** FPI says "+4.2 pts offense". 538 said "+45 Elo for QB". Because every factor is in the same currency as the headline number, they add up visibly. For this project: express each factor's contribution in **score points relative to league average**, summing to (team score - league average). This only works if the model is a weighted linear sum (or decomposed with a method like SHAP). **Requirement for the model phase: keep it additive.**
2. **Diverging bars sorted by impact.** Positives go right in team color, negatives go left in gray/red. The top one or two get a sentence.
3. **Comparison anchor.** Always show "league average" and the "last week" ghost value. Users understand change better than levels.
4. **Plain-language factor names.** Use "Winning lately" rather than "L16 win%", "Playing better than the record" rather than "EPA trend", "Luck in close games", "Beating good teams", "vs. preseason hopes", "QB trending". Show the technical name in a tooltip.
5. **Narrative sentence on top.** PFF and The Athletic prove fans read blurbs first. Use the auto-generated one-liner.
6. **2D scatter as an optional advanced view.** The rbsdm/nfelo EPA tiers chart is beloved by analytics fans, but it is secondary here.

## Feature Dependencies

```
Additive scoring model (weighted sum, per-factor contributions stored)
    ├──requires──> nflverse data ingest (schedules, pbp EPA, draft picks, teams)
    ├──enables──> Factor breakdown (diverging bars)
    │                 └──enables──> Auto-generated one-line summary
    └──enables──> Backtest transparency chart

Per-game score history (1999 to now, every team)
    ├──requires──> Franchise continuity mapping (STL→LA Rams, SD→LAC, OAK→LV, WAS name changes, HOU from 2002)
    ├──enables──> Mood-over-time chart
    ├──enables──> Week-over-week movement / biggest movers
    └──enables──> Season/week scrubber on the board

Historical score distribution (percentiles)
    └──enables──> Mood labels (percentile-tiered)
                      ├──enables──> Duration callouts ("miserable for N days")
                      │                 └──requires──> Daily-resolution timeline (carry-forward + offseason events)
                      │                                    └──enhanced by──> Offseason draft reaction
                      └──enables──> Historical extremes / records page

Record-implied rank (naive-feeling baseline)
    └──enables──> Perception-gap callout ("8-2 but worried")

Hash-route deep links ──enhances──> All callouts (shareability)
    └──enhanced by──> OG share images (defer)

Offseason draft reaction ──conflicts──> "No tanking reward" (raw draft capital rewards bad teams; needs value-over-slot or a cap)
Mood labels by raw value ──conflicts──> Cross-era comparison (use percentiles)
```

### Dependency Notes

- **Factor breakdown requires an additive model.** If the model phase picks a nonlinear blend, the breakdown becomes hard. Decide this in the model phase, not the UI phase.
- **Mood labels require the full-history distribution.** Compute the score for all seasons before finalizing tier thresholds. Otherwise labels will drift when history is added.
- **Duration callouts require daily resolution.** "600 days" counts calendar days including offseasons, so the pipeline must emit a step function with dated change events (games plus draft day), not just week indices.
- **Perception gap requires a defined baseline.** Without sentiment data, "what fans feel" equals record/standing rank (optionally also preseason expectation). State this openly on the methodology page.
- **Draft reaction conflicts with no-tanking.** By any value chart, the #1 pick is worth the most, so a raw-capital bump hands the worst team the biggest offseason boost. Use (actual pick value - value expected for the team's slot), trade surplus, or a hard cap with fast decay.

## MVP Definition

### Launch With (v1)

- [ ] Additive scoring model with stored per-factor contributions, 1999 to now: everything depends on it
- [ ] League mood board (rank, team colors, score, label, record, weekly change): home page
- [ ] Team deep-dive: score, label, factor breakdown (diverging bars + one-liner), recent games with score change
- [ ] Mood-over-time chart (selected team highlighted over league spaghetti, multi-season, date axis)
- [ ] Percentile-based playful mood labels
- [ ] Perception-gap callouts on board and team page ("{record} but you should feel {label}")
- [ ] Records page: saddest/happiest ever, longest misery streak (days), biggest perception gaps
- [ ] Methodology page with backtest chart
- [ ] Hash deep links, "last updated" stamp

### Add After Validation (v1.x)

- [ ] Offseason draft reaction (value-over-slot): add once the in-season score is validated. Its predictive value is the weakest of all inputs, so verify it doesn't hurt the backtest.
- [ ] Season/week scrubber on the board: once the per-season JSON is in place
- [ ] "My team" pin: trivial, add when the UI stabilizes
- [ ] Biggest movers / reality-check strip

### Future Consideration (v2+)

- [ ] OG share images per team/week: requires build-time image generation and deployment
- [ ] EPA tiers scatter view: nice for nerds, not core
- [ ] Free-agency reaction, "good loss" modeling: already deferred in PROJECT.md

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Additive model + contributions | HIGH | HIGH | P1 |
| Mood board | HIGH | LOW | P1 |
| Team deep-dive + factor breakdown | HIGH | MEDIUM | P1 |
| Mood labels (percentile) | HIGH | LOW | P1 |
| Perception-gap callout | HIGH | MEDIUM | P1 |
| Mood-over-time chart (1999 to now) | HIGH | MEDIUM | P1 |
| Weekly change arrows | MEDIUM | LOW | P1 |
| Methodology + backtest chart | MEDIUM | LOW | P1 |
| Records / saddest-ever page | HIGH | MEDIUM | P1 |
| Duration streaks (days) | HIGH | MEDIUM | P1 (part of records) |
| Deep links | MEDIUM | LOW | P1 |
| Draft reaction | MEDIUM | MEDIUM | P2 |
| Season/week scrubber | MEDIUM | MEDIUM | P2 |
| Auto one-liner summary | MEDIUM | LOW | P2 |
| My-team pin | LOW | LOW | P2 |
| OG share images | MEDIUM | HIGH | P3 |
| EPA tiers scatter | LOW | MEDIUM | P3 |

## Competitor Feature Analysis

| Feature | FPI (ESPN) | nfelo | 538 (archived) | ESPN Misery Index | Our Approach |
|---------|-----------|-------|----------------|-------------------|--------------|
| Ranked list | Yes, FPI + odds | Yes, Elo + EPA | Yes, Elo + odds | Yes, editorial | Mood board with label + perception gap |
| Decomposition | Off/Def/ST in points | Side-by-side stats | Additive Elo adjustments | Weighted categories | Diverging bars in score points + sentence |
| History chart | No | Limited | Yes, full franchise history | No | Yes, 1999 to now, date axis, spaghetti |
| Momentum/recency | Implicit (Bayesian) | Elo K-factor | Elo K-factor | Recent-weighted | Explicit (L16, streak, EPA trend) |
| Expectations | Preseason prior | Win-total prior | Preseason regression | No | Explicit factor vs Vegas win total |
| Luck | No | No | No | "Heartbreaks" | Explicit close-game luck factor |
| Offseason movement | Preseason re-rate | Preseason re-rate | Mean reversion | N/A | Draft-day reaction |
| Emotional framing | None | None | None | Yes (misery) | Core (labels, streaks, extremes) |
| Track record shown | No | Yes | Yes (historically) | No | Yes (backtest chart) |

## Sources

- nfelo power ratings, EPA tiers, model performance: https://www.nfeloapp.com/nfl-power-ratings/ , https://nfeloapp.com/nfl-power-ratings/nfl-epa-tiers , https://www.nfeloapp.com/games/nfl-model-performance (MEDIUM: live site via search)
- ESPN FPI guide (off/def/ST components, simulations): https://global.espn.com/blog/statsinfo/post/_/id/123048/a-guide-to-nfl-fpi (MEDIUM)
- 538 shutdown and data mirrors: https://flowingdata.com/2025/03/09/access-fivethirtyeight-resources-while-theyre-still-around/ , https://datahub.io/fivethirtyeight/nfl-elo , https://www.mediaite.com/online/nate-silver-trashes-aholes-at-abc-for-wiping-fivethirtyeights-wealth-of-historical-data-from-internet/ (MEDIUM)
- Neil Paine Elo / projections: https://neilpaine.substack.com/p/2025-nfl-power-ratings-and-projections (MEDIUM)
- Silver Bulletin ELWAY/QBERT: https://www.natesilver.net/p/how-our-elway-forecasts-work-methodology (LOW: seen in search only)
- ESPN Sports Misery Index (NFL): https://africa.espn.com/nfl/story/_/id/24402996/ranking-most-miserable-fan-bases-nfl (MEDIUM)
- PFF power rankings / EPA team tiers format: https://www.pff.com/news/final-2025-nfl-power-rankings-rams-finish-no-1-49ers-dip-ahead-of-playoffs (MEDIUM)
- rbsdm.com: not fetched directly. The description of its EPA off/def scatter comes from training data plus secondary mentions (LOW-MEDIUM).
- Design judgments (decomposition patterns, percentile labels, anti-features): researcher synthesis (LOW-MEDIUM, should be validated by building)

---
*Feature research for: NFL feel-good score visualization*
*Researched: 2026-11-11*

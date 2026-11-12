# Milestones

## v2.0 Public Site (Shipped: 2026-11-12)

**Phases completed:** 6 phases (9–14), 26 plans. Git range: v1.0..v2.0, about 200 commits. Code: +8.5k/−0.6k lines, excluding generated data.

**Live:** https://nfl-team-feelings.vercel.app/ (Vercel project `nfl-team-feelings`, auto-deploys on `web/` changes)

**Key accomplishments:**

- Pre-registered the v2 model (good-loss luck, free agency, Vegas win totals) and a fresh 2026–27 holdout in `pipeline/PREREGISTRATION_V2.md`, in a single commit (9c32319) before any v2 code. v1's holdout guard still passes.
- Deployed the site to Vercel production with a Node 24 pin, an ignored-build step for pipeline-only commits, a "data through" freshness stamp, site-wide share tags and an unofficial fan-project disclaimer.
- Pipeline guards: a golden test pins frozen v1 scores for seasons ≤2025. Audited all 24 draft forfeits with sources. Added write-once 2021–2025 Vegas win totals (a3135cb) plus a display-only 2026 file, an EPA per team-game export, and 32 local team logos (no hotlinking).
- Editorial redesign: self-hosted Inter and IBM Plex Mono, one shared Plot chart theme with ChartFrame, rule-separated tables, shaded score cells, logos everywhere with era-correct names. Light and dark modes, 375px layouts.
- New `#/explore` page with offense-vs-defense EPA and record-vs-evidence scatters, and Vegas win totals vs actual pace on the team page.
- Share cards: build-time 1200×630 satori/resvg images and static `/s/` share pages for all 32 teams and current-season callouts, with crawler-guarded redirects to the hash route. Copy-link buttons use share URLs from 2026 week 9 on.

**Audit:** tech_debt accepted (22/22 requirements, integration wired). See `milestones/v2.0-MILESTONE-AUDIT.md`.

**Known deferred items at close:** 4 (human UAT for Phases 12 and 14; see STATE.md Deferred Items)

---

## v1.0 Feel-Good Score v1 (Shipped: 2026-11-12)

**Phases completed:** 8 phases, 34 plans, 14 tasks

**Key accomplishments:**

- One command (`uv run fgs build`) caches all 7,548 nflverse games from 1999 to 2026, maps OAK/SD/STL to LV/LAC/LA, replays a 538-matching Elo (K=20, MOV multiplier with HFA inside, era HFA, 1/3 regression, CLE/HOU seeded at 1300), and `fgs elo` prints any week's ranked table. The 2026 week 9 output (BUF 1697, DEN 1647) matches the research prototype exactly.
- `uv run fgs check` asserts 31/32 franchises, 16/17 REG games per team-season (BUF/CIN 2022 allowed 16), only known team codes, unbroken LV/LAC/LA/WAS history with exact 1/3 regression at each season boundary, div_game components equal to the era division table, per-game Elo zero-sum, and a league mean of 1505 from 2012 on. All checks pass on the real 1999–2026 data.
- The weekly Elo grid is pinned by 11 tests plus a `snapshot_grid` data check, and `fgs elo` defaults to the latest played week, prints a "data through" date, flags partial weeks, and refuses weeks that haven't been played.
- Task 1, pipeline (TDD).
- Task 1 (TDD): router, route store, tick labels, season loader
- Task 1 (TDD): `fgs refresh`
- Task 1: loading, fatal-error and empty states
- Task 1 (0910825):
- 1. [Rule 2 - Correctness] Hardened pickHighlight against non-hex values
- 1. [Rule 3 - Blocking] pbp_seasons works on raw schedules
- 1. [Rule 3 - Blocking] test_cli `test_derive_carries_pbp_games` stub frame
- Every derive now runs the season simulator from a per-season digest cache (playoff odds and expected wins for every snapshot, sums checked, refresh in 2.3 s). vs_exp (win % minus the Vegas or model preseason pace) joins the score at −1.24, with mixed, model-only and deployment-condition deltas logged.
- po_trend (3-week change in raw simulated playoff odds, same season) is the 11th factor, with a reported weight of −0.01. Every exported row now carries integer playoff odds (the actual 100/0 once the regular season is over), the expectation source and the current QB. The team page shows "Playoff odds NN% · QB name", and the README closes Phase 5.
- 1. [Rule 3 - Blocking] The never_refits test can't run build_export on the synthetic league
- 1. [Rule 1 - Bug] Wrapped chart labels overlapped at 375px
- 1. [Rule 3 - Blocking] Refresh/build CLI tests would hit the network for draft data
- 1. [Rule 2 - Correctness] Stricter offseason parsing
- 1. [Rule 3 - Blocking] explain.draft_text and the blurb threshold hook were committed with Task 1
- 1. [Rule 3 - Blocking] Synthetic draft export test needed matching evidence
- Board now shows "Worth talking about" callout cards (perception gap, later streaks) and a Risers/Fallers movers strip for latest and scrubbed weeks, team pages show their own callouts, and every card has a Copy link button that copies the stable `#/team/ABBR/season/week` link, falling back to execCommand and then to a readonly URL field.
- 1. [Rule 1 - Bug] Check registry name collided with the draft-cache check filter
- 1. [Rule 2 - UX clarity] Added "Season avg N" to the extreme rows' meta line.
- You can pin a team with a ☆/★ button on any board row or team page header. The pin is saved under the `fgs.myTeam` localStorage key, and invalid stored values are ignored. The pinned team gets the accent tint and a "My team" badge on the board (rows keep their order) and on records rows. It is also the default team on the history chart, and its callouts come first in the card strip.

---

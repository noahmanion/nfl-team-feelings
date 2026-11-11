# feel-good-score

How should NFL fans *actually* feel about their team? A momentum-weighted, Elo-like "feel-good score" for every team since 1999, built from record, last-16 games, efficiency trend, strength of win, opponent quality, expectations and more, then backtested so it predicts future performance. It's a reality check for fanbases that think their team is worse (or better) than it is.

**Run:** not yet; see `.planning/ROADMAP.md`. Planned: a Python pipeline (`pipeline/`, uv + nflreadpy) writes static JSON, and a Vite + Svelte site (`web/`) renders it.

**Status:** planning complete (8 phases), Phase 1 (Data Foundation & Elo Core) next.

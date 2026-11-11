# Backtest log

Append-only, one row per factor added. Deltas are walk-forward (test seasons 2003–2021, holdout sealed) for the ridge composite with the factor minus the composite without it, against the N=8 target (mean adjusted margin over the next 8 games). The sign is the factor's weight in the 1999–2021 proposal fit (`uv run fgs backtest --propose-weights`).

| Date | Factor | ΔSpearman (N=8) | ΔR² (N=8) | Fitted sign | Notes |
| ---- | ------ | --------------- | --------- | ----------- | ----- |
| 2026-11-11 | elo | 0.5114 (baseline) | 0.2602 (baseline) | + (4.58) | `ridge:elo`, absolute values; starting composite |
| 2026-11-11 | season_record | +0.0008 | +0.0013 | + (0.63) | `ridge:+season_record` minus `ridge:elo`; small but positive |
| 2026-11-11 | last16 | +0.0033 | +0.0042 | − (−1.25) | `ridge:+last16` minus `ridge:+season_record`; negative given Elo (hot records regress); sign kept |
| 2026-11-11 | mov | +0.0026 | +0.0015 | + (1.04) | `ridge:+mov` minus `ridge:+last16`; positive given Elo and records (last fold 2021: +1.04) |
| 2026-11-11 | sow | +0.0047 | +0.0048 | − (−1.29) | `ridge:+sow` minus `ridge:+mov`; positive alone (univariate Spearman 0.4286, 1999–2021), negative given Elo (elo+sow fit: −0.28) and given Elo+mov (−1.06): Elo already prices opponent strength, so the residual is results-ahead-of-margins, which regress (RESEARCH Pitfall 1). Last fold 2021: −1.22. Kept per CONTEXT |
| 2026-11-11 | streak | +0.0000 | −0.0001 | − (−0.15) | `ridge:+streak` minus `ridge:+sow` (0.5228 → 0.5228); ≈0, kept per CONTEXT. Given Elo, margins and sow a hot streak slightly fades. Last fold 2021: −0.18 |
| 2026-11-11 | luck | −0.0008 | −0.0006 | − (−0.30) | `ridge:+luck` minus `ridge:+streak` (0.5228 → 0.5219); negative Δ in this order because sow already holds most of the signal. Alone vs the base (`elo+season_record+last16+luck` vs `ridge:+last16`) it is +0.0029. Sign − in 19/19 walk-forward folds (last fold 2021: −0.43): close-game luck evens out. Kept per CONTEXT |
| 2026-11-11 | epa_traj | −0.0000 | −0.0003 | − (−0.20) | `ridge:+epa_traj` minus `ridge:+luck` (0.52194 → 0.52189, Δ −0.00005); ΔBrier −0.00007 (0.21895 → 0.21888); last fold 2021 sign − (−0.16); level variant (EWMA h=4 of adj EPA, no season-mean subtraction) Δ −0.0019; ≈0 gain, kept per CONTEXT (data decides weight) |

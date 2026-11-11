# Backtest log

Append-only, one row per factor added. Deltas are walk-forward (test seasons 2003–2021, holdout sealed) for the ridge composite with the factor minus the composite without it, against the N=8 target (mean adjusted margin over the next 8 games). The sign is the factor's weight in the 1999–2021 proposal fit (`uv run fgs backtest --propose-weights`).

| Date | Factor | ΔSpearman (N=8) | ΔR² (N=8) | Fitted sign | Notes |
| ---- | ------ | --------------- | --------- | ----------- | ----- |
| 2026-11-11 | elo | 0.5114 (baseline) | 0.2602 (baseline) | + (4.58) | `ridge:elo`, absolute values; starting composite |
| 2026-11-11 | season_record | +0.0008 | +0.0013 | + (0.63) | `ridge:+season_record` minus `ridge:elo`; small but positive |
| 2026-11-11 | last16 | +0.0033 | +0.0042 | − (−1.25) | `ridge:+last16` minus `ridge:+season_record`; negative given Elo (hot records regress); sign kept |

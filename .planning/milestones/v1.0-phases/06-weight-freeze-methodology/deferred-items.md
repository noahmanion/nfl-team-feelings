# Phase 6 deferred items

- **README factor weights are the 05-05 interim values (found in 06-02).** README.md "How the score works today" still lists season_record 1.83, last16 −0.20, streak −0.05, vs_exp −1.23, po_trend −0.01 and says "interim until Phase 6". The frozen weights (pipeline/weights.yaml, 41e1e54) are 1.84, −0.21, −0.03, −1.22, −0.05. 06-02 doesn't list README.md in its files. 06-05 owns the README edit, so update the list (and drop "interim") there, ideally with the k/19 fold counts from FREEZE_RESULT.json.
- **score.FACTORS["po_trend"] description says "adds about nothing".** That still holds (Δ −0.0003), but the frozen weight is now −0.05 rather than −0.01. If the methodology notes in 06-04 quote the weight, they should template it from FREEZE_RESULT.json.

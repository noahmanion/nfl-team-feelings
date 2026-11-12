---
phase: 09-v2-pre-registration
reviewed: 2026-11-12T01:40:00Z
depth: quick
iteration: 2
files_reviewed: 2
files_reviewed_list:
  - pipeline/PREREGISTRATION_V2.md
  - pipeline/PREREGISTRATION_V2_DEVIATIONS.md
prior_findings:
  resolved: 13
  partial: 3
  open: 0
findings:
  critical: 2
  warning: 6
  info: 5
  total: 13
status: issues_found
---

# Phase 9: Code Review Report (re-review after Part A errata)

**Reviewed:** 2026-11-12T01:40:00Z
**Depth:** quick (re-review, plus verification of cited v1 names in `pipeline/src/fgs`)
**Files Reviewed:** 2
**Status:** issues_found

## Summary

I re-reviewed `pipeline/PREREGISTRATION_V2.md` (one commit, 9c32319, unchanged) together with Part A of
`pipeline/PREREGISTRATION_V2_DEVIATIONS.md` (one commit, 4da61a5). Part A was committed about 10 minutes
after the prereg. There is still no v2 code in `pipeline/src` or `pipeline/tests`, and `pipeline/inputs/` does not exist yet.

**Both files are frozen.** Every remaining issue below is written as an implementation note for the
future v2 milestone. The notes belong in that milestone's pre-data CONTEXT/PLAN and its guards. They
are not edits to either file.

**v1 names checked against code.** Every v1 identifier that Part A cites exists:

- `features._per_game`. Its sort is `["franchise_id", "key", *_PLAY_ORDER]`, so A10.3's order is right.
- `score.composite`.
- `score.apply_offseason`. This function creates `composite_inseason`.
- `holdout.verdict`.
- `holdout.git_state`.
- `backtest.draft_gate` and `DRAFT_GATE_FOLDS`.
- `backtest.logit_fit`.
- `bootstrap.percentile_ci`.
- `franchises.RAW_TO_FRANCHISE`.

The one imprecise name is the "v1 `fingerprint`" in A3.7 (IN-01).

**Verdict on Part A.** It closes the forking paths in CR-02 and CR-03 and the edge cases in WR-05 to
WR-08. However, it opens two new holdout-integrity holes:

- The post-freeze exemption for the primary-season preseason-line file has no bound.
- The `win_totals_2021plus.csv` contract collides with the Phase 11 DATA-02 requirement that already
  exists, which makes a void evaluation likely.

## Prior findings: disposition

| ID | Status | Resolved by | Residual |
|----|--------|-------------|----------|
| CR-01 | PARTIAL | A1.1–A1.3 | Weights and v2 modules are now locked. Post-freeze changes to shared v1 code and to dependencies are still not void (WR-01). The A3.5 exemption opens a new hole (CR-01 below). |
| CR-02 | RESOLVED | A2.2 | Swap reading chosen, and A2.2 rules out the "no expectation factor" reading. |
| CR-03 | RESOLVED | A2.3, A2.4 | Refit on the surviving set, ablations run once. The wording cites the wrong section (IN-02). |
| CR-04 | RESOLVED | A3.1, A3.5 | 2028 sources are now defined. Rewriting section 3 creates a circular definition (WR-03). |
| WR-01 | RESOLVED | A3.6 | 2026 uses the model expectation. This conflicts with Phase 11 DATA-02 (CR-02 below). |
| WR-02 | RESOLVED | A6 | The holdout statistic is defined. The dev walk-forward half is not (IN-03). |
| WR-03 | PARTIAL | A3.2–A3.4, A3.7 | Hash pin, schema and fingerprint scope are all defined. No source is named, and rows can mix books (WR-06). |
| WR-04 | PARTIAL | A4 | The witness is now recorded. A signed tag doesn't witness time, the 24 h rule isn't enforced, and A4.1 and A1.2 disagree (WR-04). |
| WR-05 | RESOLVED | A5.1–A5.4 | — |
| WR-06 | RESOLVED | A5.5 | — |
| WR-07 | RESOLVED | A7 | Matches `holdout.verdict` with a single CI. A `None` diff gives `no`, the same as v1. |
| WR-08 | RESOLVED | A8 | — |
| WR-09 | RESOLVED | A9 | The channel is now defined. Nothing guards Part A's own integrity (WR-02). |
| IN-01 | RESOLVED | A10.1 | — |
| IN-02 | RESOLVED | A10.2 | — |
| IN-03 | RESOLVED | A10.3 | — |

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: The primary-season line file is exempt from the post-freeze void, and only its adding commit is checked, so 2027 lines can be edited after kickoff

**File:** `pipeline/PREREGISTRATION_V2_DEVIATIONS.md:30-39, 79-81`

**Issue:** A1.2 voids any post-freeze commit to "the v2 input files listed in A3". It then exempts
"the primary-season preseason-line file of A3.5", and puts no bound on how many commits that covers
or when they happen. A3.5 constrains only the file's **adding** commit, which must be timed and pushed
before the first REG kickoff. Nothing requires the file to have exactly one commit.

**Attack path:**

1. Add `win_totals_2027.csv` in August.
2. Watch weeks 1–8.
3. Commit a "typo correction" to a few teams' lines.

The adding commit still passes A3.5, and the edit is exempt under A1.2. vs_exp_v2 is a holdout input
of the primary model, so this is a post-peek change to holdout features. A3.7's sha256 only records
the final bytes. It doesn't prove that they were fixed before kickoff.

**Fix (implementation note, v2 milestone):** Read A1.2's exemption as covering only the single adding
commit. Enforce that in `holdout-v2`:

```python
f = f"pipeline/inputs/win_totals_{season}.csv"
adds = _git(root, "log", "--diff-filter=A", "--format=%H", "--", f).stdout.split()
touch = _git(root, "log", "--format=%H", "--", f).stdout.split()
if len(adds) != 1 or touch != adds:
    raise SystemExit(f"{f} must have exactly one commit (A3.5); evaluation void")
# and: committer time of adds[0] < first REG kickoff, and the push witness (WR-05) < kickoff
```

The simplest operational rule is to commit the primary-season file **before** the freeze commit, as
its ancestor. Then the freeze's own commit-count, hash and witness checks cover it, and the A1.2
exemption is never used.

### CR-02: `win_totals_2021plus.csv` collides with Phase 11 DATA-02 (2021–2026, display file), which makes a void evaluation the likely outcome

**File:** `pipeline/PREREGISTRATION_V2_DEVIATIONS.md:73, 75-78, 82-85`; `pipeline/PREREGISTRATION_V2.md:71, 127`

**Issue:** Phase 11 (ROADMAP success criterion 3, REQUIREMENTS DATA-02) creates "the **2021–2026**
Vegas preseason win totals" in a sourced file under `pipeline/inputs/`, for display use. Phase 13
DATA-03 then shows those lines next to each team's pace, presumably for every live season. Part A
treats that same file as a pinned v2 input:

- **A3.3** says it covers 2021–2025.
- **A3.6** says "2026 Vegas lines are never backfilled into a v2 input". DATA-02's 2026 rows will be
  entered in November 2026, after kickoff, which makes them backfilled by definition.
- **A3.4** pins the sha256 of the **whole file**. Any change between the pin and the freeze voids the
  evaluation.
- **A1.2** voids any post-freeze commit to it.

The realistic failure mode is ordinary display maintenance, such as appending 2027 lines so the team
page shows the 2027 total, or fixing a 2026 display typo. That changes the file's hash and silently
voids the one-shot v2 holdout. Separately, if v2 reads the file unfiltered, 2026 Vegas rows reach
vs_exp_v2, which contradicts A3.6.

Phase 11 is also planned independently of Phase 9 ("Depends on: Nothing"). Its planner may not apply
A3.2's binding schema (`source, entered_on`, last pre-Week-1 line).

**Fix (implementation note):** Before Phase 11 is planned, record in its CONTEXT:

- Phase 11 must follow the A3.2 schema and source rule.
- The file `pipeline/inputs/win_totals_2021plus.csv` holds **2021–2025 rows only**. It is
  write-once after the A3.4 pin.
- 2026 and later display lines go in separate files that v2 never reads, for example
  `win_totals_display_2026.csv`.
- The v2 reader asserts `season.is_between(2021, 2025)` on every row of the file.
- A test asserts that the file's sha256 equals the pinned value.

If Phase 11 has already written 2026 rows into that filename when the v2 milestone starts, split
them out **before** the A3.4 pin is taken.

## Warnings

### WR-01: Post-freeze changes to shared v1 code and dependencies are still not void (CR-01 residual)

**File:** `pipeline/PREREGISTRATION_V2_DEVIATIONS.md:30-33`

**Issue:** A1.2 voids changes to "any v2 feature, model or evaluation module". v2 is built largely
from v1 functions:

- `pbp.scrimmage` and `pbp.team_game_epa` (the `d` of good_loss_luck),
- `features._per_game` and `_vs_exp`,
- `backtest.ridge_fit`, `choose_alpha`, `logit_fit` and `spearman`,
- the `bootstrap` helpers,
- the whole v1 comparator path in `features` and `score`.

None of these are "v2 modules". v1 work continues during the 2027 season (weekly refresh, Phases
11–13 touch `pbp`/export), and Phase 11 EXPL-01 already plans EPA-export changes near `pbp.py`. A
post-freeze edit to `pbp.scrimmage` would change both the v2 holdout features and the v1 comparator
without triggering any void condition. `uv.lock` bumps are only fingerprinted (A3.7), not voided.

**Fix (implementation note):** In `holdout-v2`, compute the set of modules that v2 and the comparator
import transitively. Record `git diff --stat <freeze> HEAD -- <those paths> pipeline/uv.lock` in
`HOLDOUT_V2_RESULT.json`. Treat a non-empty diff as void under 16.1, reading "the fit procedure" as
including the code that implements it. Alternatively, run `holdout-v2` from a worktree checked out at
the freeze commit, with only the A1.2-exempt files layered on top.

### WR-02: Part A binds "as if part of the prereg", but nothing guards Part A's own bytes

**File:** `pipeline/PREREGISTRATION_V2_DEVIATIONS.md:7-9, 20-23, 149-152`

**Issue:** Part A says "the entry governs" over the prereg text, so it now carries contract meaning.
But nothing protects it:

- Section 19 and section 1.2 guard and record only `PREREGISTRATION_V2.md`.
- The "append-only, Part A closed" property of DEVIATIONS.md has no hash pin.
- No void condition fires if Part A is edited.

A post-data edit to Part A would amend the contract without leaving any trace in the result files.

**Fix (implementation note):** `freeze-v2` and `holdout-v2` should both verify two things:

- the bytes of DEVIATIONS.md from the top through the `## Part B` heading equal those at commit 4da61a5;
- every later commit to the file only appends below Part B.

Record the file's sha256, its commit list, and the Part A sha256 in `HOLDOUT_V2_RESULT.*`. Treat a
Part A mismatch as void.

### WR-03: A3.1's "2027 means the primary holdout season" makes section 3 circular, and a double miss is undefined

**File:** `pipeline/PREREGISTRATION_V2_DEVIATIONS.md:62-64, 103-104`; `pipeline/PREREGISTRATION_V2.md:52-57`

**Issue:** Section 3.4 is the rule that *defines* the primary holdout season, and it does so using
"2027". Applying A3.1 to section 3 turns 3.4 and 3.5 into a self-reference: "primary holdout = the
full [primary season], provided the freeze lands before the first [primary season] kickoff…".

The intent is still recoverable. The gap is what happens if the 2028 deadline is also missed. The
realistic way to get there comes from A4.3: if **no witness exists**, the deadline counts as missed.
That condition never goes away, and A1.3 forbids re-freezing. So 2028 is also "missed", and neither
file says what happens next: a 2029 holdout, void, or v3.

**Fix (implementation note):** Read section 3.4/3.5 literally as written: 2027, else 2028. Apply A3.1
only to 7.2, 12.3 and 17.2.3. Encode a missed 2028 deadline, including the permanent no-witness case,
as `void: require v3 pre-registration`. `freeze-v2` should fail loudly if `gh` push-event capture is
unavailable, so the no-witness state can't arise silently.

### WR-04: The A4 witness has gaps — a signed tag isn't a time witness, 24 h isn't enforced, and A4.1 contradicts A1.2

**File:** `pipeline/PREREGISTRATION_V2_DEVIATIONS.md:93-104, 34-39`

**Issue:**

1. **Signed tag.** A "GitHub-verified signed tag" proves who signed the tag, not when. The tagger date
   is self-reported exactly like `%cI`, so this option doesn't provide the independent time that A4
   exists to supply. (The prior review suggested this option; it was a mistake.)
2. **24-hour rule.** "Within 24 hours" has no consequence. The GitHub events API keeps push events for
   about 90 days, so the witness could be fetched weeks later. Nothing says whether a late capture
   counts as "no witness".
3. **Self-authored file.** `FREEZE_V2_WITNESS.json` is written by the operator, and at `holdout-v2`
   time (February 2028) the event can no longer be fetched again to cross-check it.
4. **"The one commit".** A4.1 calls the witness commit "the one commit A1.2 allows to follow the freeze
   commit". A1.2 actually lists four exempt categories: Part B, the witness, the primary-season file,
   and `HOLDOUT_V2_RESULT.*`. Part A gives no rule for which entry wins when two entries conflict.

**Fix (implementation note):**

- Accept only the push event (`gh api repos/{o}/{r}/activity`, using `pushed_at`/`timestamp` and
  `after == <freeze sha>`).
- `freeze-v2` captures the witness itself, right after pushing. It stores the raw API JSON plus a
  sha256 of the response, and refuses to finish without it.
- Treat a capture more than 24 h after the committer time as "no witness".
- Read A4.1's "the one commit" as "the one witness commit", with A1.2's list governing.

### WR-05: A3.5 requires the primary-season file's push to be witnessed, but no commit is allowed to record that witness

**File:** `pipeline/PREREGISTRATION_V2_DEVIATIONS.md:79-81, 34-39, 93-96`

**Issue:** The primary-season line file must be "pushed to `origin` before that kickoff, with the push
witnessed as in A4". A4 defines only `FREEZE_V2_WITNESS.json`, and A1.2 exempts only "the
`FREEZE_V2_WITNESS.json` commit", which is singular. If the line file is committed after the freeze,
then recording its witness requires either:

- a second commit to the witness file, which is not exempt, or
- a new witness file, which is not exempt either.

Either one technically voids the evaluation under A1.2. `holdout-v2` would then "check both"
conditions against a witness that has no legal home.

**Fix (implementation note):** Commit the primary-season line file before the freeze commit, as its
ancestor. The single freeze witness then covers it, because a push of the freeze includes its
ancestors. Because the push follows the freeze, this proves the file was on `origin` by the time of
that push. If the season's lines aren't available before the freeze, the freeze-time witness alone
cannot cover them. In that case, record both witnesses in the one `FREEZE_V2_WITNESS.json` commit,
made after the line file's push.

### WR-06: The A3.2 source rule names no source, and per-row source columns allow mixing books (WR-03 residual)

**File:** `pipeline/PREREGISTRATION_V2_DEVIATIONS.md:65-71`

**Issue:** "One named public source, recorded per row with a source URL" can be read two ways:

- one source for the whole file, or
- one source named on each row.

The 2021–2025 outcomes are already known when the lines are entered. Under the per-row reading, an
operator who chooses among books per team-season can, even unintentionally, choose lines that shift
vs_exp_v2. The A3.4 hash pin only stops changes **after** the pin, not choices made at entry time.
"The last pre-Week-1 line" also may not be what the planned source (sportsoddshistory/covers) actually
publishes, since that source may list opening totals.

**Fix (implementation note):** In the v2 milestone (or Phase 11, given CR-02), pick and name a single
source for all 2021–2025 rows and for the primary-season file before any line is entered. Have the
validator assert that `source` is identical on every row. If that source publishes only opening
totals, record "opening" as the rule in the pre-data note rather than mixing the two.

## Info

### IN-01: A3.7 cites "v1 `fingerprint`", but the function is `holdout.input_fingerprints`

**File:** `pipeline/PREREGISTRATION_V2_DEVIATIONS.md:86-89`

**Issue:** `fgs.fingerprint` is a different module. It contains `code_fingerprint`,
`elo_fingerprint`, `data_fingerprint` and `evidence_fingerprints`, which hash code and frames, not the
cache. A3.7 lists the inputs it means (the nflverse cache, the sim cache and `uv.lock`), and those
match `holdout.input_fingerprints(cache_dir, sim_dir, lock_path)` (holdout.py:429).

**Fix:** Reuse `holdout.input_fingerprints`, and add `dir_sha256(pipeline/inputs)` and the sha256 of
`weights_v2.yaml`.

### IN-02: A2.3 cites section 1.4 for "weight 0", and "12" in 1.4 and 8.3 is never redefined

**File:** `pipeline/PREREGISTRATION_V2_DEVIATIONS.md:55-56`

**Issue:** Section 1.4 doesn't say "weight 0". It says "the 12 factor weights". The intent ("the
surviving factor set") is clear from A2.3's refit rule, so this has no material effect.

**Fix:** `freeze-v2` should assert that the weight count matches the drop outcomes (12, 11 or 11;
both-dropped gives v1's 11). It should also compute the 8.3 composite over the surviving list.

### IN-03: A6 defines H3 only for the holdout, so the dev walk-forward half of H3 (section 12.3) is still unspecified

**File:** `pipeline/PREREGISTRATION_V2_DEVIATIONS.md:118-129`

**Issue:** H3 never gates, so this is low risk. It still leaves a small choice open: report the A2.2
ablation ΔSpearman (taken against the full 12-factor set), or a walk-forward on the surviving set.

**Fix:** In the pre-data note, report the A2.2 V2-03 ablation ΔSpearman as the dev-half H3 number,
with its sign flipped if needed to read as vs_exp_v2 minus vs_exp, and label it in-sample for
2022–2025.

### IN-04: The A4.2 "effective freeze time" is not applied to the eligibility rules in 3.1 and 3.3

**File:** `pipeline/PREREGISTRATION_V2_DEVIATIONS.md:100-104`; `pipeline/PREREGISTRATION_V2.md:44-51`

**Issue:** The eligibility rules still use the committer timestamp, and only the deadline (A4.3) uses
the later witness time. This makes no difference for a full-season holdout frozen before kickoff.

**Fix:** In `holdout-v2`, use the effective freeze time everywhere, which is the conservative choice.

### IN-05: `RAW_TO_FRANCHISE` maps only OAK/SD/STL, while hand-entered 2021+ codes may use other abbreviations

**File:** `pipeline/PREREGISTRATION_V2_DEVIATIONS.md:71`

**Issue:** Sportsbook and aggregator tables often use abbreviations such as `LAR`, `JAC`, `WSH` or
`LVR`. `RAW_TO_FRANCHISE` doesn't map these, so a silent replace-miss would leave a non-canonical code
in the data.

**Fix:** Have the validator assert that every mapped code is in `franchises.CANONICAL` and that each
season has 32 rows. This is already Phase 11 success criterion 3, so reuse it.

---

_Reviewed: 2026-11-12T01:40:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: quick (iteration 2)_

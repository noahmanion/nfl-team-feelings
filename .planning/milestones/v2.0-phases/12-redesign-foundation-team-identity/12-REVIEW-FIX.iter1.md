---
phase: 12-redesign-foundation-team-identity
fixed_at: 2026-11-11T22:42:00Z
review_path: .planning/phases/12-redesign-foundation-team-identity/12-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 12: Code Review Fix Report

**Fixed at:** 2026-11-11T22:42:00Z
**Source review:** .planning/phases/12-redesign-foundation-team-identity/12-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (Critical + Warning; 6 Info findings out of scope)
- Fixed: 4
- Skipped: 0

Final verification (Node 24, `web/`): `npm test` passed (19 files, 213 tests), `npm run check` passed (0 errors, 0 warnings), and `npm run build` passed. A separate `VITE_LOGOS=off vite build` produced a `dist/` with no `logos/` directory. The default build still ships all 34 entries in `dist/logos`.

## Fixed Issues

### WR-01: `VITE_LOGOS=off` "takedown" still deploys and serves every logo file

**Files modified:** `web/vite.config.ts`, `web/src/lib/logoSwitch.ts` (new), `web/src/lib/logos.ts`, `web/src/lib/logos.test.ts`, `README.md`
**Commit:** 04b2ccc
**Applied fix:**
- Added a `dropLogos()` Vite plugin (`apply: 'build'`). It reads `VITE_LOGOS` from the resolved `config.env`, which covers both `.env` files and `process.env`. In `closeBundle`, when the flag is off, it deletes `<outDir>/logos`. That removes the 500px originals, the `sm/` derivatives and `manifest.json`.
- The source logos stay in `web/public/logos` for Phase 14.
- Moved the "off" predicate into a new pure module, `logoSwitch.ts`. It has no `import.meta.env`, so the node-side config can import it. `logosEnabled` and the build now share one definition.
- Added a test that the two agree.
- The README now says the takedown also removes `dist/logos/` from the deploy.

### WR-02: HOU-before-2002 guard (D-17) filters the board rows but not the heading count

**Files modified:** `web/src/App.svelte`
**Commit:** 4885f69
**Applied fix:**
- When `shown` is built, rows and callouts are now filtered once with `isActiveFranchise(…, target.season)`.
- `BoardHeading` count, `CalloutCards`, `MoversStrip` and `MoodBoard` all consume the same filtered data.
- MoodBoard's own filter is left in place as a harmless second guard.
- **Not fixed:** rank numbering still comes from the data, so it could skip a number if the pipeline ever emitted a pre-2002 HOU row. Fixing that is pipeline-side and out of scope.

### WR-03: Factor-breakdown headline interpolates an unchecked score

**Files modified:** `web/src/components/TeamPage.svelte`
**Commit:** cd6c744
**Applied fix:** The headline and dek now require `hasPoints && ok(row.score)`. Otherwise the frame falls back to "Score breakdown" with no dek, so a non-finite score is never interpolated.

### WR-04: HistoryChart logo mark has no fallback when the image fails

**Files modified:** `web/src/components/HistoryChart.svelte`
**Commit:** 893f9d0
**Status:** fixed: requires human verification (render-timing behavior; covered only by type-check and build, not a browser test)
**Applied fix:**
- Derived `logoUrl` and added an effect that preloads it with `new Image()`. The effect sets `logoOk` on load, clears it on error, and ignores stale results after cleanup.
- `drawLogo` now requires `src === logoOk`.
- Until the image loads, and if it never loads, the chart draws no disc or image and adds no label offset or gutter widening. It re-renders with the logo once the load succeeds.
- To confirm visually: the logo appears at the line end on the history page, and blocking `/logos/sm/*.png` leaves a clean label with no empty disc.

---

_Fixed: 2026-11-11T22:42:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

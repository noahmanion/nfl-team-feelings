---
phase: 12-redesign-foundation-team-identity
plan: 02
subsystem: web
tags: [logos, team-identity, era-names, components]
requires: []
provides:
  - teamNames.ts (eraName, eraAbbr, isActiveFranchise, eraText)
  - logos.ts (FRANCHISES, logosEnabled, logoSrc) with VITE_LOGOS build-time kill switch
  - 32 x 96px logo derivatives in web/public/logos/sm/ (scripts/logos-sm.sh)
  - TeamLogo.svelte (dark-mode disc, src-keyed chip fallback)
  - TeamChip.svelte sizes 16|20|24|32|48
affects: [wave 2 call-site swaps of TeamChip -> TeamLogo and names -> eraName]
tech-stack:
  added: []
  patterns: ["SSR render tests via svelte/server", "Error fallback keyed to failing src", "--chip-size inline custom property"]
key-files:
  created:
    - web/src/lib/teamNames.ts
    - web/src/lib/teamNames.test.ts
    - web/src/lib/logos.ts
    - web/src/lib/logos.test.ts
    - web/scripts/logos-sm.sh
    - web/public/logos/sm/*.png (32)
    - web/src/components/TeamLogo.svelte
    - web/src/lib/teamLogo.test.ts
  modified:
    - web/src/components/TeamChip.svelte
decisions:
  - "TeamChip sizes all flow through --chip-size set inline; the .large class is gone (24 still renders 24px)"
metrics:
  duration: ~4min
  completed: 2026-11-11
  tasks: 3
  files: 41
requirements: [LOGO-02, LOGO-03]
---

# Phase 12 Plan 02: Team Identity Primitives Summary

Built the team identity primitives. Era-correct names and abbreviations cover the OAK/SD/STL and Washington eras, and a display-only rewrite of pipeline "Commanders" copy for Washington seasons through 2021. The plan also adds local 96px logo derivatives with a VITE_LOGOS kill switch, and a TeamLogo component that shows a dark-mode disc and falls back to the chip.

## Tasks

| Task | Name | Commits |
| ---- | ---- | ------- |
| 1 | teamNames.ts + boundary tests | 9ee1f88 (RED), e58b399 (GREEN) |
| 2 | logos.ts + 96px derivatives + tests | 033b44e (RED), 7fd9d84 (GREEN) |
| 3 | TeamChip sizes + TeamLogo + tests | 87bbc22 (RED), e01af70 (GREEN) |

## Verification

- `npm test`: 17 files, 195 tests pass. `npm run check`: 0 errors, 0 warnings.
- 32 derivatives, KC/NYJ/WAS each 96x96. The originals and manifest.json are unchanged (`git diff --quiet` passes).
- No `http` in logos.ts or logos-sm.sh, and nohotlink.test.ts is green. Washington's former name appears nowhere in web/src.

## Deviations from Plan

None. The plan ran as written. I also added two small test cases: TeamLogo defaults to a decorative image (`alt=""`, `aria-hidden`), and `logoSrc(undefined)` returns null.

## TDD Gate Compliance

Each task has a `test(...)` RED commit followed by a `feat(...)` GREEN commit. No refactor commits were needed.

## Known Stubs

None. TeamLogo is not wired into call sites yet. That swap is planned for wave 2.

## Self-Check: PASSED
- FOUND: teamNames.ts, logos.ts, TeamLogo.svelte, logos-sm.sh, public/logos/sm/KC.png
- FOUND commits: 9ee1f88, e58b399, 033b44e, 7fd9d84, 87bbc22, e01af70

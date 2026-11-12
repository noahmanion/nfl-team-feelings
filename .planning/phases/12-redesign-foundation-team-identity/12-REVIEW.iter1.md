---
phase: 12-redesign-foundation-team-identity
reviewed: 2026-11-11T22:40:00Z
depth: standard
files_reviewed: 40
files_reviewed_list:
  - web/package.json
  - web/scripts/logos-sm.sh
  - web/src/app.css
  - web/src/main.ts
  - web/src/components/Badge.svelte
  - web/src/components/BoardHeading.svelte
  - web/src/components/BoardRow.svelte
  - web/src/components/CalloutCard.svelte
  - web/src/components/CalloutCards.svelte
  - web/src/components/ChartFrame.svelte
  - web/src/components/Delta.svelte
  - web/src/components/FactorBars.svelte
  - web/src/components/HistoryChart.svelte
  - web/src/components/HistoryPage.svelte
  - web/src/components/MethodologyChart.svelte
  - web/src/components/MethodologyPage.svelte
  - web/src/components/MoodBoard.svelte
  - web/src/components/MoodLabel.svelte
  - web/src/components/MoversStrip.svelte
  - web/src/components/PinButton.svelte
  - web/src/components/RecentGames.svelte
  - web/src/components/RecordsPage.svelte
  - web/src/components/Scrubber.svelte
  - web/src/components/SiteFooter.svelte
  - web/src/components/SiteHeader.svelte
  - web/src/components/Sparkline.svelte
  - web/src/components/StatusPanel.svelte
  - web/src/components/TeamChip.svelte
  - web/src/components/TeamLogo.svelte
  - web/src/components/TeamPage.svelte
  - web/src/lib/brand.test.ts
  - web/src/lib/chartFrame.test.ts
  - web/src/lib/history.ts
  - web/src/lib/logos.test.ts
  - web/src/lib/logos.ts
  - web/src/lib/plotTheme.test.ts
  - web/src/lib/plotTheme.ts
  - web/src/lib/teamLogo.test.ts
  - web/src/lib/teamNames.test.ts
  - web/src/lib/teamNames.ts
findings:
  critical: 0
  warning: 4
  info: 6
  total: 10
status: issues_found
---

# Phase 12: Code Review Report

**Reviewed:** 2026-11-11T22:40:00Z
**Depth:** standard
**Files Reviewed:** 40
**Status:** issues_found

## Narrative Findings (AI reviewer)

## Summary

I reviewed the Phase 12 restyle against `2488c10`. It covers the token and palette changes, the Fontsource fonts, the `plotTheme` and `ChartFrame` shared chart layer, `TeamLogo` with its chip fallback and the `VITE_LOGOS` switch, the era-name helpers (`eraName`, `eraAbbr`, `eraText`, `isActiveFranchise`), and their use across every component that identifies a team. `vitest run` passes (19 files, 212 tests).

The era boundaries are correct: STL to LA in 2016, SD to LAC in 2017, OAK to LV in 2020, and WAS in 2020/2021/2022. I checked `eraText` against the copy templates the pipeline actually emits (`insights.py`, `explain.py`), and it handles all of them. No blockers.

The main problems:
- The documented logo "takedown" switch does not take the logo files down.
- The HOU-before-2002 guard is applied in one place but not in the matching count.
- One headline interpolates an unchecked score.
- The chart logo mark has no failure fallback.

## Warnings

### WR-01: `VITE_LOGOS=off` "takedown" still deploys and serves every logo file

**File:** `web/src/lib/logos.ts:13-20`, `README.md:28`, `web/vite.config.ts`
**Issue:** The README says that setting `VITE_LOGOS=off` and redeploying is how to take the logos down. The flag only changes rendering: `TeamLogo` and `HistoryChart` stop emitting `<img>`/`image` marks. Both `public/logos/*.png` (500px originals) and `public/logos/sm/*.png` live in Vite's `public/` directory, so `vite build` copies them into `dist/` without conditions. After a "takedown" deploy, `/logos/KC.png`, `/logos/sm/KC.png` and the Phase 11 `manifest.json` are still publicly served from the site's origin. For a trademark takedown request, the asset still being hosted is the actual problem, so the switch does not do what the docs promise.
**Fix:** Strip the assets at build time when the flag is off, for example with a small plugin in `vite.config.ts`:
```ts
function dropLogos(): Plugin {
  const off = (process.env.VITE_LOGOS ?? '').trim().toLowerCase() === 'off'
  return {
    name: 'drop-logos',
    apply: 'build',
    closeBundle() {
      if (off) rmSync(resolve(__dirname, 'dist/logos'), { recursive: true, force: true })
    },
  }
}
```
Or reword the README so it promises only "hides logos in the UI".

### WR-02: HOU-before-2002 guard (D-17) filters the board rows but not the heading count

**File:** `web/src/components/MoodBoard.svelte:39`, `web/src/App.svelte:282` (consumer of `BoardHeading.svelte`)
**Issue:** `MoodBoard` drops inactive franchises (`visibleRows = rows.filter(isActiveFranchise…)`). `BoardHeading` is still passed `count={shown.rows.length}`, the unfiltered count. If a pre-2002 snapshot ever carried an HOU row, the heading would say "32 teams" above 31 rows. The ranks would also skip a number, because `row.rank` comes from the data. Callouts and movers (`CalloutCards`, `MoversStrip`) are not filtered either, so an HOU callout would still render and link to a team page that has no row. A guard applied in only one of several sibling places hides the symptom without enforcing the rule.
**Fix:** Filter once, upstream in `App.svelte`, and pass the same filtered list to `BoardHeading`, `MoodBoard`, `CalloutCards` and `MoversStrip`:
```ts
const activeRows = $derived(shown ? shown.rows.filter((r) => isActiveFranchise(r.franchise, shown.season)) : [])
// count={activeRows.length}, rows={activeRows}, and filter shownCards / shownMovers the same way
```

### WR-03: Factor-breakdown headline interpolates an unchecked score ("Where the null comes from")

**File:** `web/src/components/TeamPage.svelte:227`
**Issue:** `headline={hasPoints ? \`Where the ${row.score} comes from\` : 'Score breakdown'}` only checks that `row.points` exists. The same file guards the score cell with `ok(row.score)`, and the file comment says malformed data must never render "NaN"/"null"/"undefined". If `points` is present but `score` is `null` or non-finite, the headline renders "Where the null comes from" and the dek promises that the factors "sum to the score".
**Fix:**
```svelte
headline={hasPoints && ok(row.score) ? `Where the ${row.score} comes from` : 'Score breakdown'}
dek={hasPoints && ok(row.score) ? `Points each factor adds … (${baseline}). Together they sum to the score.` : undefined}
```

### WR-04: HistoryChart logo mark has no fallback when the image fails, which leaves an empty disc and a gap in the label

**File:** `web/src/components/HistoryChart.svelte:94-97, 162-166`
**Issue:** D-11 requires that a logo which fails to load falls back to the chip. `TeamLogo` does this; the chart's Plot `image` mark does not. `drawLogo` depends only on `logosEnabled()` and `logoSrc()`, so a 404 or blocked image still produces three things:
- In dark mode, an empty light-gray `--logo-disc` circle at the line end.
- A blank space before the label, which is pushed right by `logoPx / 2 + 4`.
- A `teamCol` gutter widened by `logoPx + 4`.

That is a visible artifact on the main history chart.
**Fix:** Preload the image before deciding `drawLogo`, and re-render on the result:
```ts
let logoOk = $state<string | null>(null)
$effect(() => {
  const s = logosEnabled() ? logoSrc(team) : null
  if (!s) return
  const img = new Image()
  img.onload = () => (logoOk = s)
  img.onerror = () => (logoOk = null)
  img.src = s
})
// drawLogo = !!src && src === logoOk && last.length > 0
```

## Info

### IN-01: TeamLogo drops the `alt` accessible name on the chip fallback

**File:** `web/src/components/TeamLogo.svelte:28-42`
**Issue:** When a caller passes a non-empty `alt`, it applies only to the `<img>` branch. `TeamChip` is always `aria-hidden="true"`, so with `VITE_LOGOS=off` or after an image error the accessible name disappears. No current caller passes `alt`, so this is latent.
**Fix:** In the fallback branch, wrap the chip in `<span role="img" aria-label={alt}>` when `alt !== ''`, or remove the `alt` prop.

### IN-02: Streak callout naming disagrees with the Records page rule (D-18)

**File:** `web/src/components/CalloutCard.svelte:18-21`, `web/src/components/MoversStrip.svelte:27-29`
**Issue:** D-18 says streaks take the name from the streak's start season. `RecordsPage` follows that (`teamName(s.franchise, s.start_season)`). Streak callouts instead rewrite with `callout.season`. A Washington misery streak that started in 2017 and shows in a 2021 callout reads "Football Team fans have been miserable for N straight days", while the Records page names the same streak "Washington". This is minor, but the two surfaces disagree.
**Fix:** For `misery`/`joy` callouts, pass the streak start season to `eraName`/`eraText` if the callout carries it, or document the deviation.

### IN-03: Hex validation is inconsistent between TeamChip and teamStroke

**File:** `web/src/components/TeamChip.svelte:8`, `web/src/lib/plotTheme.ts:19`
**Issue:** `TeamChip` accepts only 6-digit hex. `teamStroke` accepts 3- or 6-digit hex. The same team color could therefore draw in a chart but fall back to the gray chip. Separately, `CSS_VAR` is lowercase-only, so `var(--Text)` silently becomes `var(--text)`.
**Fix:** Share one `isHexColor` helper from `lib/` between the two.

### IN-04: `withTheme` silently discards a string-valued `style`

**File:** `web/src/lib/plotTheme.ts:42-46`
**Issue:** Plot accepts `style` as either a string or an object. A caller passing `style: 'font-size: 14px'` gets the theme object instead, and the caller's string is dropped without any warning. The doc comment ("Caller options win") is not true in that case.
**Fix:** If `typeof raw === 'string'`, pass it through unmerged, or throw in dev.

### IN-05: `logos-sm.sh` is macOS-only with no guard

**File:** `web/scripts/logos-sm.sh:7-9`
**Issue:** `sips` exists only on macOS. On Linux (for example a Vercel build, or another contributor), the script fails with `sips: command not found`, and nothing says why. If `public/logos` has no PNGs, the unmatched glob passes the literal `*.png` to `sips`.
**Fix:** Add `command -v sips >/dev/null || { echo "requires macOS sips" >&2; exit 1; }` and `shopt -s nullglob`.

### IN-06: Methodology page heading outline is flat

**File:** `web/src/components/MethodologyPage.svelte:72, 87+`
**Issue:** The new page heading `<h2 id="how-heading">How it works</h2>` sits at the same level as every section heading ("What the score is", "The factors", "Does it work?"). The article is labelled by one h2 among several siblings, so the outline does not show that the sections belong to the page.
**Fix:** Demote the section headings to `h3` (and the existing `h3`s to `h4`), or render the page title as the visually styled lead heading only.

---

_Reviewed: 2026-11-11T22:40:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

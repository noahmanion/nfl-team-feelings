---
status: pending
phase: 14
created: 2026-11-12
---

# Phase 14: Human UAT, real-platform share previews (D-26)

Run this after the orchestrator pushes, Vercel reports READY, and the automated pre-check below passes.

URLs as of data latest = 2026 week 9:

| Use | URL | Expected og:title |
|-----|-----|-------------------|
| Team share | `https://nfl-team-feelings.vercel.app/s/team/BUF/2026-w9/` | Buffalo Bills: 94, Buying the jersey |
| Callout share | `https://nfl-team-feelings.vercel.app/s/c/2026/9/CLE-worried/` | Cleveland Browns: 5-4, but you should feel worried |
| Root | `https://nfl-team-feelings.vercel.app/` | site card ("How should you feel about your NFL team?") |

Card images:
- `https://nfl-team-feelings.vercel.app/og/team/BUF/2026-w9.png`
- `https://nfl-team-feelings.vercel.app/og/c/2026/9/CLE-worried.png`
- `https://nfl-team-feelings.vercel.app/og-default.png`

Each preview should show a large 1200×630 image. The team card shows the Bills logo, the score 94 and the label "Buying the jersey". The callout card shows the Browns logo, a WORRIED kicker and the headline "5-4, but you should feel worried". The preview title should match the og:title above.

## Tests

### 1. Slack paste
Steps: Paste the team URL into a Slack message (a DM to yourself is fine), then do the same with the callout URL.
Expected: Each unfurls with the large card image and the og:title above. No site-default card.
Result:

### 2. iMessage paste
Steps: Send the team URL, then the callout URL, in iMessage (to yourself).
Expected: The rich link shows the card image and title.
Result:

### 3. X post composer
Steps: Paste the team URL, then the callout URL, into the X post composer. Don't post.
Expected: A summary_large_image preview with the card and title.
Result:

### 4. Facebook Sharing Debugger
Steps: Open `https://developers.facebook.com/tools/debug/` and debug the team URL, the callout URL and the root URL. On the root URL, click "Scrape Again" so the newly rendered `og-default.png` is fetched (it keeps its filename, so FB's cached copy is stale; Pitfall 8).
Expected: Response code 200, og:image is the absolute `/og/...png` URL, and the preview shows the card. After Scrape Again, the root shows the new site card.
Note: if the debugger reports a 403 / "could not scrape", record it as the known Vercel platform limitation for facebookexternalhit (RESEARCH Open Question 1), not a build failure.
Result:

### 5. LinkedIn Post Inspector
Steps: Open `https://www.linkedin.com/post-inspector/` and inspect the team URL, then the callout URL.
Expected: The image and title match. No missing-tag warnings for og:image, og:title or og:url.
Result:

### 6. Browser click lands on the matching hash route
Steps: Open the team URL in a normal browser, then the callout URL.
Expected: The team URL lands on `https://nfl-team-feelings.vercel.app/#/team/BUF/2026/9` (Buffalo Bills page, week 9). The callout URL lands on `https://nfl-team-feelings.vercel.app/#/team/CLE/2026/9`.
Result:

### 7. Pre-launch callouts keep hash links
Steps: On the site, go to the board for 2026 week 8 (`https://nfl-team-feelings.vercel.app/#/board/2026/8`) and click the copy-link button on a callout (e.g. CLE worried).
Expected: The copied link is a `#/team/...` hash deep link, not a `/s/` share URL.
Result:

## Automated pre-check (run by orchestrator after deploy)

D-25 crawler curls. Each line should print 200, an absolute `og:image`, and an image fetch of 200 with `image/png`. Also check the non-trailing-slash team URL variant (Vercel should redirect or serve it).

```bash
P=https://nfl-team-feelings.vercel.app
for path in /s/team/BUF/2026-w9/ /s/team/BUF/2026-w9 /s/c/2026/9/CLE-worried/; do
  for ua in "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)" "Twitterbot/1.0" "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)"; do
    html=$(curl -sL -A "$ua" -w '\n%{http_code}' "$P$path"); code=${html##*$'\n'}
    img=$(printf '%s' "$html" | grep -o 'property="og:image" content="[^"]*"' | sed 's/.*content="//;s/"$//')
    echo "$code ${ua%% *} $path og:image=$img"
    printf '%s' "$html" | grep -q 'property="og:url" content="https://' && printf '%s' "$html" | grep -q 'name="twitter:card" content="summary_large_image"' || echo "  MISSING TAGS"
    curl -s -o /dev/null -w "  image %{http_code} %{content_type} %{size_download}B\n" "$img"
  done
done
```

Result:

## Automated pre-check result (2026-11-12, production deploy dpl_6CcU2DchecQ2gPGuczhjRBQ1NZVf @ d706dcb, READY)

All 16 checks passed: 2 pages (`/s/team/BUF/2026-w9/`, `/s/c/2026/9/CLE-worried/`) x 4 UAs (`facebookexternalhit/1.1`, `Twitterbot/1.0`, `Slackbot-LinkExpanding 1.0`, `LinkedInBot/1.0`) returned 200 with `twitter:card=summary_large_image`, absolute `og:url` (= the share page) and absolute `og:image` on `https://nfl-team-feelings.vercel.app`; each og:image returned `200 image/png`. Non-slash form (`-L`) 200; plain curl 200 (no Vercel bot challenge observed); `/og-default.png` 200 (50 KB, new satori card). Redirect script targets `#/team/BUF/2026/9`. Caveat: curl with a crawler UA cannot detect UA+IP-based blocking of the real Meta crawler, so test 4 (FB Sharing Debugger) remains required.

Vercel build log: vite 722 ms; share step 45 cards in 1.71 s (38 ms/card), rss 273 MB; build completed in 5 s; projected full season ~24 s.

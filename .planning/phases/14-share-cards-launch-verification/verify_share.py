#!/usr/bin/env python3
"""Phase 14 share page sweep (14-03): redirect, card image, crawler HTML.

Usage (after `npm run build`, with `npm run preview -- --port 4173 --strictPort` running in web/):
  /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 verify_share.py [BASE_URL]

Week and callout are derived from web/public/data (meta.latest + first callout of that week).
Trailing-slash share URLs only (vite preview does not redirect /dir -> /dir/; Pitfall 4).
Prints one PASS/FAIL line per check, exits non-zero on any failure.
"""
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[2] / "web" / "public" / "data"
META = json.loads((DATA / "meta.json").read_text())
S, W = META["latest"]["season"], META["latest"]["week"]
SNAP = json.loads((DATA / "snapshots" / f"{S}.json").read_text())
CALLOUTS = SNAP.get("callouts", {}).get(str(W), [])

args = [a for a in sys.argv[1:] if not a.startswith("--")]
BASE = (args[0] if args else "http://localhost:4173").rstrip("/")
TEAM = "BUF"
TEAM_NAME = META["teams"][TEAM]["name"]

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'} {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        failures.append(name)


def callout_id(c: dict) -> str:
    return f"{c['season']}/{c['week']}/{c['franchise'].upper()}-{c['type'].replace('_', '-')}"


def main() -> int:
    team_share = f"/s/team/{TEAM}/{S}-w{W}/"
    team_img = f"/og/team/{TEAM}/{S}-w{W}.png"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # (a) team share page -> hash route, heading renders
        page.goto(BASE + team_share, wait_until="networkidle")
        page.wait_for_url(re.compile(rf"/#/team/{TEAM}/{S}/{W}$"), timeout=10_000)
        check("team share redirects", page.url.endswith(f"/#/team/{TEAM}/{S}/{W}"), page.url)
        try:
            page.get_by_role("heading", name=TEAM_NAME).first.wait_for(timeout=10_000)
            check("team heading renders", True, TEAM_NAME)
        except Exception as e:  # noqa: BLE001
            check("team heading renders", False, str(e)[:120])

        # (b) callout share page -> callout's team hash route
        if CALLOUTS:
            c = CALLOUTS[0]
            page.goto(f"{BASE}/s/c/{callout_id(c)}/", wait_until="networkidle")
            want = f"/#/team/{c['franchise']}/{c['season']}/{c['week']}"
            try:
                page.wait_for_url(re.compile(re.escape(want) + "$"), timeout=10_000)
            except Exception:  # noqa: BLE001
                pass
            check("callout share redirects", page.url.endswith(want), page.url)
        else:
            check("callout share redirects", True, f"no callouts in {S} w{W} (skipped)")

        # (c) card image served as PNG
        r = page.request.get(BASE + team_img)
        check("team card is image/png", r.status == 200 and r.headers.get("content-type", "").startswith("image/png"),
              f"{r.status} {r.headers.get('content-type')}")

        # (d) crawler UA gets the HTML with og:image
        r = page.request.get(BASE + team_share, headers={"User-Agent": "facebookexternalhit/1.1"})
        body = r.text()
        check("crawler gets og:image", r.status == 200 and 'property="og:image"' in body, f"{r.status}")

        browser.close()

    print("ALL PASS" if not failures else f"{len(failures)} FAILED: {', '.join(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

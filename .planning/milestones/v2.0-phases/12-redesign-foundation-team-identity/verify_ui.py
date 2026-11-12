#!/usr/bin/env python3
"""Phase 12 visual + behavior sweep (D-25).

Usage (with `npm run preview -- --port 4173 --strictPort` running in web/):
  python3 verify_ui.py [BASE_URL]               # screenshots + all behavior checks (normal build)
  python3 verify_ui.py [BASE_URL] --logos-off   # kill-switch check only (VITE_LOGOS=off build)

Prints one PASS/FAIL line per check and exits non-zero if any check fails.
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SHOTS = HERE / "screenshots"
META = HERE.parents[2] / "web" / "public" / "data" / "meta.json"

args = [a for a in sys.argv[1:] if not a.startswith("--")]
LOGOS_OFF = "--logos-off" in sys.argv
BASE = (args[0] if args else "http://localhost:4173").rstrip("/")

failures: list[str] = []
requests: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'} {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        failures.append(name)


def era_week() -> int:
    meta = json.loads(META.read_text())
    s2010 = next(s for s in meta["seasons"] if s["season"] == 2010)
    return int(s2010["reg_weeks"])


def go(page, hash_: str) -> None:
    # ?r=1 forces a fresh document load so data is fetched (SPA reload quirk).
    page.goto(f"{BASE}/?r=1{hash_}", wait_until="networkidle")
    page.evaluate("document.fonts.ready.then(() => true)")
    page.wait_for_timeout(400)


def new_context(browser, width: int, scheme: str = "light", **kw):
    ctx = browser.new_context(viewport={"width": width, "height": 900 if width >= 1000 else 812},
                              color_scheme=scheme, **kw)
    ctx.on("request", lambda r: requests.append(r.url))
    return ctx


def run_logos_off(browser) -> None:
    ctx = new_context(browser, 1280)
    page = ctx.new_page()
    go(page, "#/")
    page.wait_for_selector("#row-KC")
    imgs = page.locator('img[src*="/logos/sm/"]').count()
    chips = page.locator(".chip").count()
    check("kill switch: no logo imgs on board", imgs == 0, f"{imgs} imgs")
    check("kill switch: >=30 chips on board", chips >= 30, f"{chips} chips")
    ctx.close()


def run_default(browser) -> None:
    week = era_week()
    pages = {
        "board": "#/",
        "team-era": f"#/team/LAC/2010/{week}",
        "team-current": "#/team/KC",
        "history": "#/history",
        "records": "#/records",
        "methodology": "#/methodology",
    }
    SHOTS.mkdir(exist_ok=True)

    # 1 + 2: screenshots and 375 overflow
    for scheme in ("light", "dark"):
        for width in (1280, 375):
            ctx = new_context(browser, width, scheme)
            page = ctx.new_page()
            for name, h in pages.items():
                go(page, h)
                page.screenshot(path=str(SHOTS / f"{name}-{width}-{scheme}.png"), full_page=True)
                if width == 375:
                    sw, iw = page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
                    check(f"no h-scroll {name} 375 {scheme}", sw <= iw, f"scrollWidth {sw} vs {iw}")
            ctx.close()
    shots = len(list(SHOTS.glob("*.png")))
    check("24 screenshots", shots >= 24, f"{shots} files")

    ctx = new_context(browser, 1280)
    page = ctx.new_page()

    # 3: era names + header logo
    go(page, pages["team-era"])
    check("LAC 2010 shows 'San Diego Chargers'", "San Diego Chargers" in page.inner_text("body"))
    go(page, pages["team-current"])
    n = page.locator('img[src="/logos/sm/KC.png"]').count()
    check("KC header logo img", n >= 1, f"{n} imgs")

    # 8: fonts
    body_font = page.evaluate("getComputedStyle(document.body).fontFamily")
    check("body font Inter Variable", "Inter Variable" in body_font, body_font)
    num_font = page.evaluate(
        "(() => { const e = document.querySelector('.num'); return e ? getComputedStyle(e).fontFamily : '' })()")
    check(".num font IBM Plex Mono", "IBM Plex Mono" in num_font, num_font)
    loaded = page.evaluate("document.fonts.ready.then(() => document.fonts.check('16px \"Inter Variable\"'))")
    check("document.fonts.check Inter Variable", bool(loaded))

    # 9: grid groups + history logo
    for name in ("history", "methodology"):
        go(page, pages[name])
        page.wait_for_selector("svg", timeout=10000)
        g = page.evaluate("document.querySelectorAll('svg g[aria-label$=\"-grid\"]').length")
        check(f"grid groups on {name}", g >= 1, f"{g} groups")
        if name == "history":
            imgs = page.evaluate("document.querySelectorAll('svg image').length")
            check("HistoryChart has exactly one svg image", imgs == 1, f"{imgs} images")

    # 5: pin -> reload keeps My team
    go(page, "#/")
    page.wait_for_selector("#row-KC")
    first = page.locator("ol li[id^='row-']").first
    abbr = (first.get_attribute("id") or "").removeprefix("row-")
    first.locator("button.pin").click()
    go(page, "#/")
    page.wait_for_selector("#row-KC")
    badge = page.locator(f"#row-{abbr} .mine-badge").count()
    check("pin survives reload (My team badge)", badge == 1, f"pinned {abbr}")
    jump = page.get_by_role("button", name="Jump to my team")
    if jump.count():
        jump.click()
        page.wait_for_timeout(300)
        focused = page.evaluate("document.activeElement?.closest('li')?.id || ''")
        check("Jump to my team focuses pinned row", focused == f"row-{abbr}", focused)
    else:
        check("Jump to my team button present", False)
    page.evaluate("localStorage.clear()")

    # 6: scrubber keyboard step changes hash
    go(page, "#/")
    page.wait_for_selector("#week-range")
    page.focus("#week-range")
    page.keyboard.press("ArrowLeft")
    page.wait_for_timeout(500)
    h = page.evaluate("location.hash")
    check("scrubber ArrowLeft -> #/board/ hash", h.startswith("#/board/"), h)
    ctx.close()

    # 7: copy link
    ctx = new_context(browser, 1280)
    ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=BASE)
    page = ctx.new_page()
    go(page, "#/")
    btn = page.get_by_role("button", name="Copy link").first
    if btn.count():
        btn.click()
        page.wait_for_timeout(400)
        st = page.locator("article.card p.status").first.inner_text().strip()
        check("copy link status text", st in ("Link copied", "Copy the link below"), repr(st))
    else:
        print("SKIP copy link - no callout cards on the latest board")
    ctx.close()

    # 4: logo 404 -> chip
    ctx = new_context(browser, 1280)
    ctx.route("**/logos/sm/KC.png", lambda r: r.fulfill(status=404, body=""))
    page = ctx.new_page()
    go(page, "#/")
    page.wait_for_selector("#row-KC")
    page.wait_for_timeout(500)
    chip = page.locator("#row-KC .chip").count()
    vis_img = page.locator('#row-KC img[src*="KC.png"]:visible').count()
    check("logo 404 -> chip in #row-KC", chip >= 1 and vis_img == 0, f"chips {chip}, visible imgs {vis_img}")
    ctx.close()


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        if LOGOS_OFF:
            run_logos_off(browser)
        else:
            run_default(browser)
        browser.close()
    foreign = sorted({u for u in requests if not u.startswith(BASE) and not u.startswith("data:")})
    check("all requests same-origin", not foreign, ", ".join(foreign[:5]))
    print(f"\n{len(failures)} failed" if failures else "\nALL PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

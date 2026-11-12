#!/usr/bin/env python3
"""Phase 13 visual + behavior sweep (D-26, D-27).

Usage (with `npm run preview -- --port 4173 --strictPort` running in web/):
  python3 verify_ui.py [BASE_URL]

Prints one PASS/FAIL line per check, saves exactly 6 screenshots, exits non-zero on any failure.
"""
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SHOTS = HERE / "screenshots"
DATA = HERE.parents[2] / "web" / "public" / "data"
META = json.loads((DATA / "meta.json").read_text())

args = [a for a in sys.argv[1:] if not a.startswith("--")]
BASE = (args[0] if args else "http://localhost:4173").rstrip("/")

failures: list[str] = []
requests: list[str] = []

EPA_SVG = "section[aria-labelledby='epa-heading'] svg"
RVE_SVG = "section[aria-labelledby='rve-heading'] svg"
LOGO = "image[href*='/logos/sm/']"


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'} {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        failures.append(name)


def reg_weeks(season: int) -> int:
    return int(next(s for s in META["seasons"] if s["season"] == season)["reg_weeks"])


def go(page, hash_: str) -> None:
    # ?r=1 forces a fresh document load so data is fetched (SPA reload quirk).
    page.goto(f"{BASE}/?r=1{hash_}", wait_until="networkidle")
    page.evaluate("document.fonts.ready.then(() => true)")
    page.wait_for_timeout(500)


def new_context(browser, width: int, scheme: str = "light", **kw):
    ctx = browser.new_context(viewport={"width": width, "height": 900 if width >= 1000 else 812},
                              color_scheme=scheme, **kw)
    ctx.on("request", lambda r: requests.append(r.url))
    return ctx


def logos_in(page, sel: str) -> int:
    return page.evaluate(f"(() => {{ const s = document.querySelector(\"{sel}\"); "
                         f"return s ? s.querySelectorAll(\"{LOGO}\").length : 0 }})()")


def chart_checks(page, label: str) -> None:
    page.wait_for_selector(f"{EPA_SVG} {LOGO}", timeout=15000)
    page.wait_for_selector(f"{RVE_SVG} {LOGO}", timeout=15000)
    e, r = logos_in(page, EPA_SVG), logos_in(page, RVE_SVG)
    check(f"{label}: EPA scatter >= 28 logos", e >= 28, f"{e}")
    check(f"{label}: record scatter >= 28 logos", r >= 28, f"{r}")


def logo_center(page):
    box = page.locator(f"{EPA_SVG} {LOGO}").first.bounding_box()
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def overflow(page, name: str) -> None:
    sw, iw = page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    check(f"no h-scroll {name}", sw <= iw, f"scrollWidth {sw} vs {iw}")


def shot(page, name: str) -> None:
    page.evaluate("document.fonts.ready.then(() => true)")
    page.screenshot(path=str(SHOTS / name), full_page=True)


def run(browser) -> None:
    SHOTS.mkdir(exist_ok=True)
    for old in SHOTS.glob("*.png"):
        old.unlink()
    latest = META["latest"]

    # 1-5, 7, 8 at 1280 light
    ctx = new_context(browser, 1280)
    page = ctx.new_page()
    go(page, "#/explore")
    chart_checks(page, f"latest {latest['season']}/{latest['week']}")
    cur = page.locator("nav a", has_text="Explore").first.get_attribute("aria-current")
    check("nav Explore aria-current=page", cur == "page", str(cur))
    body = page.inner_text("body")
    for h in ("How efficiently every team plays", "Record vs evidence"):
        check(f"headline '{h}'", h in body)
    check("no 'luck' on Explore", "luck" not in body.lower())
    shot(page, "explore-1280-light.png")

    # 7 table
    det = page.locator("details.as-table").first
    det.locator("summary").click()
    page.wait_for_timeout(200)
    n = det.locator("tbody tr").count()
    href = det.locator("tbody tr a").first.get_attribute("href") or ""
    check("table >= 28 rows", n >= 28, f"{n}")
    check("table team link -> #/team/", href.startswith("#/team/"), href)

    go(page, "#/explore/2025/10")
    chart_checks(page, "2025/10")
    dek = page.locator("section[aria-labelledby='epa-heading'] .cf-dek").inner_text()
    check("EPA dek mentions 2025", "2025" in dek, dek[:60])

    go(page, "#/explore/2025/0")
    msg = "No games played yet in 2025. Pick a later week."
    n = page.locator("figure.chart-frame", has_text=msg).count()
    check("week 0 empty state in both frames", n == 2, f"{n} frames")

    go(page, "#/explore/2099/3")
    page.wait_for_timeout(300)
    h = page.evaluate("location.hash")
    check("#/explore/2099/3 -> #/explore", h == "#/explore", h)

    # 5 mouse click
    go(page, "#/explore/2025/10")
    page.wait_for_selector(f"{EPA_SVG} {LOGO}")
    x, y = logo_center(page)
    page.mouse.move(x, y)
    page.wait_for_timeout(200)
    page.mouse.click(x, y)
    page.wait_for_timeout(500)
    h = page.evaluate("location.hash")
    check("mouse click logo -> #/team/", h.startswith("#/team/"), h)

    # 11 Phase 12 leftovers
    go(page, "#/")
    page.wait_for_selector("#row-KC")
    texts = page.locator("ol li .delta").all_inner_texts()
    check("rank delta readable (spot / no change)", any(re.search(r"spot|no change", t) for t in texts),
          f"{texts[:3]}")
    check("no '#▲' / '#▼' delta text", not any("#▲" in t or "#▼" in t for t in texts))
    go(page, "#/records")
    page.wait_for_selector("ol")
    w = page.locator("ol").first.bounding_box()["width"]
    check("records list > 700px wide", w > 700, f"{w:.0f}px")

    # 9 win totals (three eras + 2026 opener)
    go(page, "#/team/BUF")
    page.wait_for_selector("text=Preseason expectations", timeout=10000)
    b = page.inner_text("body")
    check("BUF 2026: Preseason expectations", "Preseason expectations" in b)
    check("BUF 2026: opening-line suffix", "opening line, not the final preseason number" in b)
    shot(page, "team-2026-1280-light.png")
    go(page, f"#/team/BUF/2023/{reg_weeks(2023)}")
    page.wait_for_selector("text=Preseason expectations", timeout=10000)
    b = page.inner_text("body")
    check("BUF 2023: Vegas display only", "Vegas preseason (display only, not used in score)" in b)
    check("BUF 2023: Model used in score", "Model preseason (used in score)" in b)
    go(page, f"#/team/BUF/2015/{reg_weeks(2015)}")
    page.wait_for_selector("text=Preseason expectations", timeout=10000)
    b = page.inner_text("body")
    check("BUF 2015: Vegas used in score", "Vegas preseason (used in score)" in b)
    check("BUF 2015: normalized note", "normalized to the league average" in b)
    go(page, f"#/team/BUF/2000/{reg_weeks(2000)}")
    page.wait_for_selector("text=Preseason expectations", timeout=10000)
    check("BUF 2000: no Vegas before 2003", "No Vegas line on file before 2003" in page.inner_text("body"))
    ctx.close()

    # 2025/10 dark 1280 + 2015 dark 1280
    ctx = new_context(browser, 1280, "dark")
    page = ctx.new_page()
    go(page, "#/explore/2025/10")
    chart_checks(page, "2025/10 dark")
    discs = page.evaluate(f"document.querySelector(\"{EPA_SVG}\").querySelectorAll('circle').length")
    check("dark mode logo discs present", discs >= 28, f"{discs} circles")
    shot(page, "explore-2025-10-1280-dark.png")
    go(page, f"#/team/BUF/2015/{reg_weeks(2015)}")
    page.wait_for_selector("text=Preseason expectations", timeout=10000)
    shot(page, "team-2015-1280-dark.png")
    ctx.close()

    # 10 overflow at 375 light + dark
    for scheme in ("light", "dark"):
        ctx = new_context(browser, 375, scheme)
        page = ctx.new_page()
        for name, h in (("explore", "#/explore"), ("explore-2025-10", "#/explore/2025/10"),
                        ("team-2023", f"#/team/BUF/2023/{reg_weeks(2023)}")):
            go(page, h)
            if name.startswith("explore"):
                page.wait_for_selector(f"{EPA_SVG} {LOGO}", timeout=15000)
            else:
                page.wait_for_selector("text=Preseason expectations", timeout=10000)
            overflow(page, f"{name} 375 {scheme}")
            if (name, scheme) == ("explore", "dark"):
                shot(page, "explore-375-dark.png")
            if (name, scheme) == ("team-2023", "light"):
                shot(page, "team-2023-375-light.png")
        ctx.close()

    # 6 touch arming
    ctx = new_context(browser, 375, has_touch=True, is_mobile=True)
    page = ctx.new_page()
    go(page, "#/explore/2025/10")
    page.wait_for_selector(f"{EPA_SVG} {LOGO}")
    page.locator(f"{EPA_SVG}").first.scroll_into_view_if_needed()
    page.wait_for_timeout(200)
    x, y = logo_center(page)
    before = page.evaluate("location.hash")
    page.touchscreen.tap(x, y)
    page.wait_for_timeout(400)
    after1 = page.evaluate("location.hash")
    tip = page.evaluate(f"(() => {{ const s = document.querySelector(\"{EPA_SVG}\"); "
                        "const t = s && s.querySelector('g[aria-label=\"tip\"]'); "
                        "return !!t && t.childElementCount > 0 })()")
    check("touch tap 1 keeps hash", after1 == before, f"{before} -> {after1}")
    check("touch tap 1 shows tip", bool(tip))
    page.touchscreen.tap(x, y)
    page.wait_for_timeout(500)
    after2 = page.evaluate("location.hash")
    check("touch tap 2 -> #/team/", after2.startswith("#/team/"), after2)
    ctx.close()

    n = len(list(SHOTS.glob("*.png")))
    check("exactly 6 screenshots", n == 6, f"{n} files")


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        run(browser)
        browser.close()
    foreign = sorted({u for u in requests if not u.startswith(BASE) and not u.startswith("data:")})
    check("all requests same-origin", not foreign, ", ".join(foreign[:5]))
    print(f"\n{len(failures)} failed" if failures else "\nALL PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

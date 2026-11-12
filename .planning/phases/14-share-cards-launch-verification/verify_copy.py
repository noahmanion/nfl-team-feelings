#!/usr/bin/env python3
"""Phase 14-04 browser check of copy-link URLs (SHARE-03, D-22..D-24).

Usage (with an isolated build served on 4174, from web/):
  npx vite build --outDir node_modules/.tmp/copycheck --emptyOutDir
  npx vite preview --outDir node_modules/.tmp/copycheck --port 4174 --strictPort
  python3 verify_copy.py [BASE_URL]

Prints one PASS/FAIL line per check and exits non-zero on any failure. No screenshots.
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
PRE_S, PRE_W = 2026, 8  # the week before SHARE_LAUNCH (2026 w9): hash links only

args = [a for a in sys.argv[1:] if not a.startswith("--")]
BASE = (args[0] if args else "http://localhost:4174").rstrip("/")

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'} {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        failures.append(name)


def go(page, hash_: str) -> None:
    # ?r=1 forces a fresh document load so data is fetched (SPA reload quirk).
    page.goto(f"{BASE}/?r=1{hash_}", wait_until="networkidle")
    page.wait_for_timeout(400)


def clip(page) -> str:
    return page.evaluate("navigator.clipboard.readText()")


def click_and_read(page, button, status) -> tuple[str, str]:
    page.evaluate("navigator.clipboard.writeText('')")
    button.click()
    page.wait_for_function("(el) => el.textContent.trim() !== ''", arg=status.element_handle(), timeout=3000)
    return clip(page), status.inner_text().strip()


def header_button(page):
    return page.get_by_role("button", name="Copy link to Buffalo Bills")


def header_status(page):
    return page.locator("header.head .share-row [role=status]")


def first_card(page):
    card = page.locator("article.card").first
    return card.get_by_role("button", name="Copy link"), card.locator("[role=status]")


with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1280, "height": 900},
                              permissions=["clipboard-read", "clipboard-write"])
    page = ctx.new_page()

    # 1. Team page, latest view: share URL pinned to meta.latest
    go(page, "#/team/BUF")
    btn = header_button(page)
    check("1a header button 'Copy link to Buffalo Bills' exists", btn.count() == 1, f"count={btn.count()}")
    if btn.count() == 1:
        url, st = click_and_read(page, btn, header_status(page))
        want = f"{BASE}/s/team/BUF/{S}-w{W}/"
        check("1b latest team copy -> share URL", url == want and st == "Link copied", f"{url!r} / {st!r}")

    # 2. Team page, pre-launch week: hash deep link
    go(page, f"#/team/BUF/{PRE_S}/{PRE_W}")
    btn = header_button(page)
    if btn.count() == 1:
        url, st = click_and_read(page, btn, header_status(page))
        want = f"{BASE}/#/team/BUF/{PRE_S}/{PRE_W}"
        check("2 pre-launch team copy -> hash link", url == want, f"{url!r}")
    else:
        check("2 pre-launch team copy -> hash link", False, "header button missing")

    # 3. Board (latest): first callout card copies a callout share URL
    go(page, "#/")
    cbtn, cstatus = first_card(page)
    if cbtn.count() == 1:
        url, st = click_and_read(page, cbtn, cstatus)
        pat = rf"^{re.escape(BASE)}/s/c/{S}/{W}/[A-Z]{{2,3}}-[a-z-]+/$"
        check("3 latest callout copy -> share URL", bool(re.match(pat, url)) and st == "Link copied", f"{url!r}")

        # 5. Repeat click re-announces (WR-05)
        cbtn.click()
        page.wait_for_timeout(300)
        st2 = cstatus.inner_text().strip()
        check("5 repeat click still ends 'Link copied'", st2 == "Link copied", f"{st2!r}")
    else:
        check("3 latest callout copy -> share URL", False, "no callout card")
        check("5 repeat click still ends 'Link copied'", False, "no callout card")

    # 4. Board at a pre-launch week: hash deep link
    go(page, f"#/board/{PRE_S}/{PRE_W}")
    cbtn, cstatus = first_card(page)
    if cbtn.count() == 1:
        url, _ = click_and_read(page, cbtn, cstatus)
        pat = rf"^{re.escape(BASE)}/#/team/[A-Z]{{2,3}}/{PRE_S}/{PRE_W}$"
        check("4 pre-launch callout copy -> hash link", bool(re.match(pat, url)), f"{url!r}")
    else:
        check("4 pre-launch callout copy -> hash link", False, "no callout card")

    ctx.close()

    # 6. 375px team header: no horizontal scroll
    ctx = browser.new_context(viewport={"width": 375, "height": 812},
                              permissions=["clipboard-read", "clipboard-write"])
    page = ctx.new_page()
    go(page, "#/team/BUF")
    sw = page.evaluate("document.documentElement.scrollWidth")
    check("6 375px team page has no horizontal scroll", sw <= 375 and header_button(page).count() == 1,
          f"scrollWidth={sw}")
    ctx.close()
    browser.close()

print("ALL PASS" if not failures else f"{len(failures)} FAILED: {', '.join(failures)}")
sys.exit(1 if failures else 0)

"""One-shot team logo download (LOGO-01, D-17). Not part of `fgs refresh`.

Fetches the 32 ESPN 500px PNGs into web/public/logos/{FRANCHISE}.png (committed to git) and
writes manifest.json, so the site never hotlinks an external logo host. Never uses the nflverse
team_logo_wikipedia URLs.
"""

import hashlib
import json
import os
import urllib.request
from datetime import date
from pathlib import Path
from typing import Callable

from fgs import paths
from fgs.franchises import CANONICAL

ESPN_BASE = "https://a.espncdn.com/i/teamlogos/nfl/500/"
# ESPN codes are the franchise id lowercased except these. /500/la.png and /500/was.png also
# exist and are valid PNGs of the wrong image, so the mapping is tested against teams.parquet.
CODE_OVERRIDES = {"LA": "lar", "WAS": "wsh"}
PNG_SIG = b"\x89PNG\r\n\x1a\n"
MIN_BYTES = 1024


def logo_url(franchise: str) -> str:
    if franchise not in CANONICAL:
        raise ValueError(f"unknown franchise {franchise!r}")
    return f"{ESPN_BASE}{CODE_OVERRIDES.get(franchise, franchise.lower())}.png"


def validate_png(data: bytes) -> None:
    if not data.startswith(PNG_SIG):
        raise ValueError("not a PNG (bad signature)")
    if len(data) <= MIN_BYTES:
        raise ValueError(f"PNG too small ({len(data)} bytes)")


def _http_get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read()


def _atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def fetch_logos(out_dir: Path | None = None, force: bool = False,
                fetch: Callable[[str], bytes] | None = None, today: str | None = None) -> dict:
    """Download missing (or, with force, all) logos; return and write the manifest.

    Skipped files keep their manifest entry (fetched date) when one exists. An invalid download
    raises before anything is written for that team; the manifest is written last."""
    out = Path(paths.LOGOS_DIR if out_dir is None else out_dir)
    fetch = _http_get if fetch is None else fetch
    today = date.today().isoformat() if today is None else today
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    manifest = {}
    for f in sorted(CANONICAL):
        path, url = out / f"{f}.png", logo_url(f)
        if path.exists() and not force:
            data = path.read_bytes()
            validate_png(data)
            when = old.get(f, {}).get("fetched", today)
        else:
            data = fetch(url)
            validate_png(data)
            _atomic_write(path, data)
            when = today
        manifest[f] = {"url": url, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "fetched": when}

    _atomic_write(manifest_path, (json.dumps(manifest, indent=1, sort_keys=True) + "\n").encode())
    return manifest

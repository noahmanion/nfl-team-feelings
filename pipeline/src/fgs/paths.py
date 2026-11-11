"""Filesystem locations, resolved from this file (never from the CWD)."""

from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PIPELINE_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
DERIVED_DIR = DATA_DIR / "derived"
WEB_DATA_DIR = PIPELINE_ROOT.parent / "web" / "public" / "data"
WEIGHTS_PATH = PIPELINE_ROOT / "weights.yaml"

"""Filesystem locations, resolved from this file (never from the CWD)."""

from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PIPELINE_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
DERIVED_DIR = DATA_DIR / "derived"
WEB_DATA_DIR = PIPELINE_ROOT.parent / "web" / "public" / "data"
WEIGHTS_PATH = PIPELINE_ROOT / "weights.yaml"
# Phase 6 freeze / holdout artifacts (consumers read these as `paths.X` at call time)
PREREG_PATH = PIPELINE_ROOT / "PREREGISTRATION.md"
FREEZE_RESULT_PATH = PIPELINE_ROOT / "FREEZE_RESULT.json"
HOLDOUT_MD_PATH = PIPELINE_ROOT / "HOLDOUT_RESULT.md"
HOLDOUT_JSON_PATH = PIPELINE_ROOT / "HOLDOUT_RESULT.json"

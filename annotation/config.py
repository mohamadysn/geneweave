#!/usr/bin/python3
#-*- coding: utf-8 -*-

import os
import sys
from pathlib import Path


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def _bundle_root() -> Path:
    """Read-only assets (templates, sample data) — PyInstaller extract dir when frozen."""
    if _is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def _writable_root() -> Path:
    """Writable app data (results, cache).

    Portable binaries: next to the executable when that directory is writable.
    System installs (/opt, /usr): XDG data dir (~/.local/share/geneweave).
    """
    if _is_frozen():
        exe_dir = Path(sys.executable).resolve().parent
        if os.access(exe_dir, os.W_OK):
            return exe_dir
        xdg = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
        data_dir = Path(xdg) / "geneweave"
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "results").mkdir(parents=True, exist_ok=True)
        (data_dir / ".cache").mkdir(parents=True, exist_ok=True)
        return data_dir
    return Path(__file__).resolve().parent.parent


BUNDLE_DIR = _bundle_root()
PROJECT_DIR = _writable_root()
PACKAGE_DIR = BUNDLE_DIR / "annotation" if _is_frozen() else Path(__file__).resolve().parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
VIEWER_TEMPLATES_DIR = BUNDLE_DIR / "viewer" / "templates"
DATA_DIR = BUNDLE_DIR / "data"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "results"
CACHE_DIR = PROJECT_DIR / ".cache"
SAMPLE_GENES_FILE = DATA_DIR / "GeneSymbols_2.txt"

NCBI_EMAIL = os.environ.get("NCBI_EMAIL", "mohamad.a.ysn@gmail.com")
NCBI_DELAY = float(os.environ.get("NCBI_DELAY", "0.34"))
DEFAULT_WORKERS = int(os.environ.get("ANNOTATION_WORKERS", "1"))
MAX_WORKERS = 4
HTTP_TIMEOUT = float(os.environ.get("ANNOTATION_HTTP_TIMEOUT", "60"))
HTTP_RETRIES = int(os.environ.get("ANNOTATION_HTTP_RETRIES", "3"))
VERSION = "1.1.0"
APP_NAME = "GeneWeave"
APP_TAGLINE = "Multi-database gene annotation"
IS_FROZEN = _is_frozen()

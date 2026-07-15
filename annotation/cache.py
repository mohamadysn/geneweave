#!/usr/bin/python3
#-*- coding: utf-8 -*-

import json
import threading

from annotation.config import CACHE_DIR

CACHE_FILE = CACHE_DIR / "gene_annotations.json"
_NO_DATA = "No data found"
_lock = threading.Lock()


def _load():
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(cache):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as handle:
        json.dump(cache, handle, ensure_ascii=False, indent=2)


def cache_key(gene_symbol, organism):
    return f"{gene_symbol.strip().upper()}|{organism.strip().lower()}"


def _cell_has_data(cell):
    if cell is None or cell == "" or cell == _NO_DATA:
        return False
    if isinstance(cell, list):
        if not cell:
            return False
        return any(_cell_has_data(item) for item in cell)
    text = str(cell)
    if text == _NO_DATA:
        return False
    if "ERROR:" in text:
        return False
    return True


def row_has_annotation_data(row):
    """True if the row has usable data beyond the gene label (col 0)."""
    if not row or not isinstance(row, list) or len(row) < 2:
        return False
    return any(_cell_has_data(cell) for cell in row[1:])


def get_cached_row(gene_symbol, organism):
    with _lock:
        row = _load().get(cache_key(gene_symbol, organism))
    if row is None:
        return None
    # Ignore poisoned cache entries from failed/empty API runs
    if not row_has_annotation_data(row):
        delete_cached_row(gene_symbol, organism)
        return None
    return row


def set_cached_row(gene_symbol, organism, row):
    if not row_has_annotation_data(row):
        return
    with _lock:
        cache = _load()
        cache[cache_key(gene_symbol, organism)] = row
        _save(cache)


def delete_cached_row(gene_symbol, organism):
    with _lock:
        cache = _load()
        key = cache_key(gene_symbol, organism)
        if key in cache:
            del cache[key]
            _save(cache)


def clear_cache():
    with _lock:
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()


def cache_stats():
    with _lock:
        cache = _load()
    return {
        "genes": len(cache),
        "file": str(CACHE_FILE),
        "size_kb": round(CACHE_FILE.stat().st_size / 1024, 1) if CACHE_FILE.exists() else 0,
    }

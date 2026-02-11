"""
watchlist.py — Keyword management for the ingestion engine.

The watchlist is the set of keywords / article titles that connectors
monitor during each ingestion cycle.  It's stored as a simple JSON
file so analysts can edit it without touching code.

File location (configurable via VS_WATCHLIST_PATH):
    data/watchlist.json

Format:
{
    "version": 1,
    "updated_at": "2026-02-08T12:00:00Z",
    "keywords": {
        "finance": ["bank run", "FDIC", ...],
        "geopolitical": ["coup", "sanctions", ...],
        "health": ["pandemic", "quarantine", ...],
        "civil_unrest": ["protest", "riot", ...],
        "custom": []
    }
}
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_PATH = os.getenv(
    "VS_WATCHLIST_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "watchlist.json"),
)


# ── Default Watchlist ────────────────────────────────────────────────────

_DEFAULT_WATCHLIST: dict[str, list[str]] = {
    "finance": [
        "bank run",
        "bank failure",
        "FDIC",
        "credit default swap",
        "liquidity crisis",
        "bond yield",
        "dollar collapse",
        "treasury sell-off",
        "margin call",
        "systemic risk",
    ],
    "geopolitical": [
        "martial law",
        "coup",
        "military mobilization",
        "sanctions",
        "embassy evacuation",
        "nuclear threat",
        "territorial dispute",
        "ceasefire violation",
    ],
    "health": [
        "pandemic",
        "quarantine",
        "disease outbreak",
        "hospital overflow",
        "vaccine shortage",
        "WHO emergency",
        "bird flu",
        "antibiotic resistance",
    ],
    "civil_unrest": [
        "protest",
        "riot",
        "curfew",
        "supply shortage",
        "power grid failure",
        "water crisis",
        "mass migration",
        "food price spike",
    ],
    "custom": [],
}


def load_watchlist(path: str | None = None) -> dict[str, list[str]]:
    """Load the watchlist from disk.  Creates the default file if missing."""
    filepath = Path(path or _DEFAULT_PATH).resolve()

    if not filepath.exists():
        logger.info("Watchlist not found at %s — creating default", filepath)
        save_watchlist(_DEFAULT_WATCHLIST, str(filepath))
        return _DEFAULT_WATCHLIST

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("keywords", _DEFAULT_WATCHLIST)


def save_watchlist(
    keywords: dict[str, list[str]], path: str | None = None
) -> None:
    """Persist the watchlist to disk."""
    filepath = Path(path or _DEFAULT_PATH).resolve()
    filepath.parent.mkdir(parents=True, exist_ok=True)

    doc: dict[str, Any] = {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "keywords": keywords,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)

    logger.info("Watchlist saved to %s (%d categories)", filepath, len(keywords))


def get_flat_keywords(path: str | None = None) -> list[str]:
    """Return a deduplicated flat list of all keywords across categories."""
    categories = load_watchlist(path)
    seen: set[str] = set()
    flat: list[str] = []
    for kw_list in categories.values():
        for kw in kw_list:
            lower = kw.lower().strip()
            if lower not in seen:
                seen.add(lower)
                flat.append(kw.strip())
    return flat


def add_keyword(
    keyword: str,
    category: str = "custom",
    path: str | None = None,
) -> None:
    """Add a keyword to a category (defaults to 'custom')."""
    categories = load_watchlist(path)
    if category not in categories:
        categories[category] = []

    if keyword.strip() not in categories[category]:
        categories[category].append(keyword.strip())
        save_watchlist(categories, path)
        logger.info("Added keyword '%s' to category '%s'", keyword, category)


def remove_keyword(
    keyword: str,
    category: str | None = None,
    path: str | None = None,
) -> bool:
    """Remove a keyword. If category is None, search all categories."""
    categories = load_watchlist(path)
    removed = False

    targets = [category] if category else list(categories.keys())
    for cat in targets:
        if cat in categories and keyword.strip() in categories[cat]:
            categories[cat].remove(keyword.strip())
            removed = True

    if removed:
        save_watchlist(categories, path)
        logger.info("Removed keyword '%s'", keyword)

    return removed


def add_keywords(
    keywords: list[str],
    category: str = "custom",
    path: str | None = None,
) -> None:
    """Add multiple keywords to a category (defaults to 'custom')."""
    categories = load_watchlist(path)
    if category not in categories:
        categories[category] = []

    added = []
    for keyword in keywords:
        kw = keyword.strip()
        if kw and kw not in categories[category]:
            categories[category].append(kw)
            added.append(kw)

    if added:
        save_watchlist(categories, path)
        logger.info("Added keywords %s to category '%s'", added, category)


def remove_keywords(
    keywords: list[str],
    category: str | None = None,
    path: str | None = None,
) -> int:
    """Remove multiple keywords. If category is None, search all categories. Returns count removed."""
    categories = load_watchlist(path)
    removed_count = 0

    targets = [category] if category else list(categories.keys())
    for cat in targets:
        if cat in categories:
            for keyword in keywords:
                kw = keyword.strip()
                if kw in categories[cat]:
                    categories[cat].remove(kw)
                    removed_count += 1

    if removed_count > 0:
        save_watchlist(categories, path)
        logger.info("Removed %d keywords", removed_count)

    return removed_count

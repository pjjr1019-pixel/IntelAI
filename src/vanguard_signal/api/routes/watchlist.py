"""
watchlist.py — REST endpoints for keyword watchlist management.

Endpoints:
  GET    /api/watchlist              — Get current watchlist (all categories)
  GET    /api/watchlist/flat         — Flat deduplicated keyword list
  POST   /api/watchlist/keywords     — Add a keyword to a category
  DELETE /api/watchlist/keywords     — Remove a keyword
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from vanguard_signal.ingestion.watchlist import (
    add_keyword,
    add_keywords,
    get_flat_keywords,
    load_watchlist,
    remove_keyword,
    remove_keywords,
)

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


import re

# Only allow alphanumeric, spaces, hyphens, apostrophes, periods, &, /
_SAFE_KEYWORD_RE = re.compile(r"^[\w\s\-'.&/]+$", re.UNICODE)
_BLOCKED_PATTERNS = re.compile(
    r"(--|;|<script|<img|\.\.[\\/]|\$\{|%00|%0[aAdD])", re.IGNORECASE
)


def _validate_keyword(v: str) -> str:
    v = v.strip()
    if not _SAFE_KEYWORD_RE.match(v):
        raise ValueError("Keyword contains disallowed characters")
    if _BLOCKED_PATTERNS.search(v):
        raise ValueError("Keyword contains blocked patterns")
    return v


class KeywordPayload(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=256)
    category: str = Field("custom", max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")

    @field_validator("keyword")
    @classmethod
    def sanitize_keyword(cls, v: str) -> str:
        return _validate_keyword(v)


@router.get("", response_model=dict)
async def get_watchlist() -> dict:
    """Return the full watchlist organized by category."""
    categories = load_watchlist()
    total = sum(len(kws) for kws in categories.values())
    return {
        "total_keywords": total,
        "categories": categories,
    }


@router.get("/flat", response_model=dict)
async def get_flat_list() -> dict:
    """Return a flat, deduplicated list of all monitored keywords."""
    keywords = get_flat_keywords()
    return {
        "count": len(keywords),
        "keywords": keywords,
    }


@router.post("/keywords", response_model=dict, status_code=201)
async def add_watchlist_keyword(body: KeywordPayload) -> dict:
    """Add a keyword to the watchlist."""
    add_keyword(body.keyword, body.category)
    return {
        "status": "added",
        "keyword": body.keyword,
        "category": body.category,
    }


class BulkKeywordsPayload(BaseModel):
    keywords: list[str] = Field(..., min_length=1)
    category: str = Field("custom", max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")


@router.post("/bulk", response_model=dict, status_code=201)
async def add_watchlist_keywords_bulk(body: BulkKeywordsPayload) -> dict:
    """Add multiple keywords to a category in bulk."""
    add_keywords(body.keywords, body.category)
    return {"status": "added", "count": len(body.keywords), "category": body.category}


@router.delete("/keywords", response_model=dict)
async def remove_watchlist_keyword(
    keyword: str = Query(..., min_length=1),
    category: str | None = Query(None),
) -> dict:
    """Remove a keyword from the watchlist."""
    removed = remove_keyword(keyword, category)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Keyword '{keyword}' not found")
    return {"status": "removed", "keyword": keyword}


class BulkRemovePayload(BaseModel):
    keywords: list[str] = Field(..., min_length=1)
    category: str | None = Field(None, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")


@router.delete("/bulk", response_model=dict)
async def remove_watchlist_keywords_bulk(body: BulkRemovePayload) -> dict:
    """Remove multiple keywords in bulk. Returns number removed."""
    removed = remove_keywords(body.keywords, body.category)
    return {"status": "removed", "count": removed}

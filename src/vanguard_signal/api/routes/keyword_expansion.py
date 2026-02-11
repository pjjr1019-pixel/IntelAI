"""API routes for keyword expansion and discovery."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from vanguard_signal.detection.keyword_expansion import get_keyword_expansion_service

router = APIRouter(prefix="/keyword-expansion", tags=["keyword-expansion"])


class KeywordSuggestion(BaseModel):
    """Model for keyword suggestion response."""
    keyword: str = Field(..., description="The suggested keyword")
    score: float = Field(..., description="Confidence score (0-1)")
    method: str = Field(..., description="Discovery method used")
    category: str = Field(..., description="Category or relationship type")


class KeywordCluster(BaseModel):
    """Model for keyword cluster response."""
    keywords: List[str] = Field(..., description="Keywords in this cluster")
    centroid_keyword: str = Field(..., description="Central keyword of the cluster")
    score: float = Field(..., description="Cluster cohesion score")
    size: int = Field(..., description="Number of keywords in cluster")


class WatchlistExpansionRequest(BaseModel):
    """Request model for watchlist expansion."""
    existing_keywords: List[str] = Field(..., description="Current keywords in watchlist")
    expansion_factor: Optional[float] = Field(
        0.5,
        description="How many suggestions per existing keyword (0.5 = half as many)",
        ge=0.1,
        le=2.0
    )
    max_suggestions: Optional[int] = Field(
        50,
        description="Maximum total suggestions to return",
        ge=1,
        le=200
    )


@router.get("/related/{keyword}", response_model=List[KeywordSuggestion])
async def get_related_keywords(
    keyword: str,
    max_suggestions: int = Query(10, ge=1, le=50, description="Maximum number of suggestions"),
    include_scores: bool = Query(True, description="Include confidence scores in response")
):
    """
    Get related keywords for a given term.

    Uses multiple discovery methods:
    - Co-occurrence analysis (keywords that appear together)
    - Semantic similarity (word overlap and meaning)
    - Category relationships (keywords in same category)
    - Trend correlation (keywords with similar trend patterns)
    """
    try:
        service = get_keyword_expansion_service()
        suggestions = await service.get_related_keywords(
            keyword=keyword,
            max_suggestions=max_suggestions,
            include_scores=include_scores
        )
        return suggestions
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get related keywords: {str(exc)}"
        )


@router.post("/expand-watchlist", response_model=List[str])
async def expand_watchlist(request: WatchlistExpansionRequest):
    """
    Expand a watchlist by suggesting related keywords.

    Analyzes existing keywords and suggests new ones that are likely to be relevant
    based on co-occurrence patterns, semantic similarity, and trend correlations.
    """
    try:
        if not request.existing_keywords:
            raise HTTPException(status_code=400, detail="Must provide existing keywords")

        service = get_keyword_expansion_service()
        suggestions = await service.expand_watchlist_keywords(
            existing_keywords=request.existing_keywords,
            expansion_factor=request.expansion_factor
        )

        # Limit total suggestions
        return suggestions[:request.max_suggestions]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to expand watchlist: {str(exc)}"
        )


@router.post("/clusters", response_model=List[KeywordCluster])
async def get_keyword_clusters(
    keywords: List[str] = Query(..., description="Keywords to cluster"),
    min_cluster_size: int = Query(3, ge=2, le=20, description="Minimum cluster size")
):
    """
    Group keywords into semantic clusters.

    Analyzes relationships between keywords and groups them into clusters
    based on shared patterns, co-occurrence, and semantic similarity.
    """
    try:
        if len(keywords) < min_cluster_size:
            raise HTTPException(
                status_code=400,
                detail=f"Must provide at least {min_cluster_size} keywords for clustering"
            )

        service = get_keyword_expansion_service()
        clusters = await service.get_keyword_clusters(
            keywords=keywords,
            min_cluster_size=min_cluster_size
        )
        return clusters
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cluster keywords: {str(exc)}"
        )


@router.get("/methods")
async def get_expansion_methods():
    """
    Get information about available keyword expansion methods.
    """
    return {
        "methods": [
            {
                "name": "cooccurrence",
                "description": "Keywords that frequently appear in the same time periods",
                "category": "temporal"
            },
            {
                "name": "semantic",
                "description": "Keywords with similar words or meanings",
                "category": "lexical"
            },
            {
                "name": "category",
                "description": "Keywords in the same category or topic area",
                "category": "thematic"
            },
            {
                "name": "correlation",
                "description": "Keywords with correlated trend patterns",
                "category": "trend"
            }
        ]
    }
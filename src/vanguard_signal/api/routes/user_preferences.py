"""
user_preferences.py — User preferences and settings endpoints.

Provides:
  GET /api/user/preferences  — Get user preferences
  PUT /api/user/preferences  — Update user preferences
"""

from __future__ import annotations

import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.api.auth import require_auth
from vanguard_signal.api.deps import get_current_user_optional
from vanguard_signal.schema.models.user import User

router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/preferences", response_model=Dict[str, Any])
async def get_user_preferences(
    current_user: User | None = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    """Get user preferences for the current user."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Return preferences as dict, defaulting to empty dict if None
    preferences = current_user.preferences or {}
    if isinstance(preferences, str):
        try:
            preferences = json.loads(preferences)
        except json.JSONDecodeError:
            preferences = {}

    return preferences


@router.put("/preferences", response_model=Dict[str, Any])
async def update_user_preferences(
    preferences: Dict[str, Any],
    current_user: User | None = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    """Update user preferences for the current user."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Store preferences as JSON/dict directly (JSON column)
    current_user.preferences = preferences
    return preferences
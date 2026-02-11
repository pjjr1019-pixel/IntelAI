"""
deps.py — Dependency injection for FastAPI route handlers.

Provides:
  • get_db()      — async DB session (auto-commits on success, rollbacks on error)
  • get_user_id() — extracts analyst identity from JWT or fallback header
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, AsyncGenerator, Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.schema.database import async_session
from vanguard_signal.api.auth import require_auth
from vanguard_signal.schema.models.user import User

logger = logging.getLogger(__name__)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a transactional async DB session.

    The session auto-commits when the route handler returns normally
    and rolls back on any unhandled exception.
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_user_id(
    claims: dict[str, Any] = Depends(require_auth),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
) -> str | uuid.UUID:
    """
    Extract the analyst's identity.

    Priority:
      1. JWT 'sub' claim (if a valid Bearer token is present)
      2. X-User-Id header (backwards-compatible fallback in dev)
      3. 'anonymous' default
    """
    jwt_sub = claims.get("sub")
    if jwt_sub and jwt_sub != "anonymous":
        try:
            return uuid.UUID(str(jwt_sub))
        except Exception:
            return jwt_sub

    if x_user_id:
        try:
            return uuid.UUID(str(x_user_id))
        except Exception:
            return x_user_id

    return "anonymous"


async def get_claims(
    claims: dict[str, Any] = Depends(require_auth),
) -> dict[str, Any]:
    """Return the full decoded JWT claims dict."""
    return claims


async def get_current_user_optional(
    user_id: str = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get the current user from the database, or None if not found or anonymous.
    
    Returns None for anonymous users or if the user doesn't exist in the database.
    """
    if user_id == "anonymous":
        return None
    
    # Import here to avoid circular imports
    from vanguard_signal.schema.models.user import User
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return user

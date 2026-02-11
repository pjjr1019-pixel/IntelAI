"""
auth_routes.py — Authentication endpoints for Vanguard Signal.

Endpoints:
    POST /api/auth/login     — Exchange credentials for access + refresh tokens
    POST /api/auth/register  — Create a new user account (admin only in prod)
    POST /api/auth/refresh   — Swap a valid refresh token for new access token
    GET  /api/auth/me        — Return current user profile from JWT
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from vanguard_signal.api.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    _USERS,
    create_access_token,
    create_refresh_token,
    create_user,
    get_user_by_email,
    get_user_by_username,
    require_auth,
    require_role,
    verify_password,
    verify_token,
)
from vanguard_signal.api.deps import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """
    Exchange username + password for JWT access + refresh tokens.

    Checks the database first; falls back to the in-memory store
    for backward compatibility during migration.
    """
    username = body.username.lower().strip()

    # ── Try DB-backed user first ──────────────────────────────────────
    db_user = await get_user_by_username(db, username)
    if db_user is not None:
        if not db_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated — contact an administrator",
            )
        if not verify_password(body.password, db_user.password_hash):
            logger.warning("Failed login attempt for user=%s (DB)", username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )
        # Update last_login_at
        db_user.last_login_at = datetime.now(timezone.utc)
        await db.flush()

        access = create_access_token(subject=db_user.username, role=db_user.role)
        refresh = create_refresh_token(subject=db_user.username, role=db_user.role)
        logger.info("User %s logged in via DB (role=%s)", db_user.username, db_user.role)
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            user=db_user.username,
            role=db_user.role,
        )

    # ── Fallback: in-memory user store (legacy/tests) ────────────────
    mem_user = _USERS.get(username)
    if not mem_user or not verify_password(body.password, mem_user["password_hash"]):
        logger.warning("Failed login attempt for user=%s", username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    access = create_access_token(subject=username, role=mem_user["role"])
    refresh = create_refresh_token(subject=username, role=mem_user["role"])
    logger.info("User %s logged in via memory store (role=%s)", username, mem_user["role"])
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=username,
        role=mem_user["role"],
    )


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    claims: dict = Depends(require_role("admin")),
) -> UserResponse:
    """
    Create a new user account. Requires admin role.

    In production, consider adding email verification or using an IdP.
    """
    # Check for existing username or email
    if await get_user_by_username(db, body.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{body.username}' is already taken",
        )
    if await get_user_by_email(db, body.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{body.email}' is already registered",
        )

    user = await create_user(
        db=db,
        username=body.username,
        email=body.email,
        password=body.password,
        display_name=body.display_name,
    )
    await db.flush()
    logger.info("New user registered: %s (by %s)", user.username, claims.get("sub"))

    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        is_active=user.is_active,
        last_login_at=None,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """
    Exchange a valid refresh token for a new access token + refresh token pair.

    The old refresh token becomes invalid once a new pair is issued
    (rotation). This limits the window for stolen refresh tokens.
    """
    # Verify the refresh token
    payload = verify_token(body.refresh_token, expected_type="refresh")
    username = payload.get("sub", "")
    role = payload.get("role", "analyst")

    # Optionally verify user still exists and is active
    db_user = await get_user_by_username(db, username)
    if db_user is not None:
        if not db_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )
        role = db_user.role  # Use current role from DB (may have changed)

    # Issue new token pair (rotation)
    new_access = create_access_token(subject=username, role=role)
    new_refresh = create_refresh_token(subject=username, role=role)

    logger.info("Token refreshed for user=%s", username)
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        user=username,
        role=role,
    )


@router.get("/me")
async def me(
    claims: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Return current user info from the JWT token and DB.
    """
    username = claims.get("sub", "unknown")

    # Try DB first for rich user data
    db_user = await get_user_by_username(db, username)
    if db_user is not None:
        return {
            "status": "ok",
            "user": db_user.username,
            "role": db_user.role,
            "name": db_user.display_name,
            "email": db_user.email,
            "is_active": db_user.is_active,
            "last_login_at": db_user.last_login_at.isoformat() if db_user.last_login_at else None,
        }

    # Fallback to in-memory store
    mem_user = _USERS.get(username, {})
    return {
        "status": "ok",
        "user": username,
        "role": claims.get("role", "viewer"),
        "name": mem_user.get("name", username),
    }

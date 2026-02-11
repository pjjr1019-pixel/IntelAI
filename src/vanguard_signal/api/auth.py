"""
auth.py — JWT Authentication for Vanguard Signal API.

Provides:
  • hash_password / verify_password   — bcrypt password management
  • create_access_token / create_refresh_token — JWT issuance
  • verify_token                       — Decode & validate a JWT
  • require_auth (FastAPI dependency)  — Extract & verify Bearer token
  • get_user_by_username / create_user — DB-backed user management
  • seed_default_users                 — Bootstrap MVP users on first start

Tokens use HS256 with a configurable secret. In production,
rotate VS_JWT_SECRET via AWS Secrets Manager.
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import jwt  # PyJWT

try:
    import bcrypt
    _HAS_BCRYPT = True
except ImportError:
    _HAS_BCRYPT = False

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────

JWT_SECRET: str = os.getenv("VS_JWT_SECRET", "vanguard-dev-secret-change-me")
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRE_MINUTES: int = int(os.getenv("VS_JWT_EXPIRE_MINUTES", "480"))  # 8 hours
REFRESH_EXPIRE_MINUTES: int = int(os.getenv("VS_REFRESH_EXPIRE_MINUTES", "10080"))  # 7 days


# ── Password Hashing ────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Falls back to SHA-256 if bcrypt is not installed (dev convenience),
    but logs a warning — production MUST have bcrypt.
    """
    if _HAS_BCRYPT:
        return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    logger.warning("bcrypt not installed — using SHA-256 fallback (NOT for production)")
    return "sha256:" + hashlib.sha256(plain.encode("utf-8")).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plaintext password against its stored hash.

    Supports bcrypt hashes, SHA-256 fallback hashes, and legacy
    plaintext values (auto-detected for migration).
    """
    # bcrypt hashes always start with $2b$ (or $2a$, $2y$)
    if hashed.startswith(("$2b$", "$2a$", "$2y$")):
        if not _HAS_BCRYPT:
            logger.error("bcrypt hash found but bcrypt not installed!")
            return False
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

    # SHA-256 fallback hashes
    if hashed.startswith("sha256:"):
        digest = hashlib.sha256(plain.encode("utf-8")).hexdigest()
        return hashed == "sha256:" + digest

    # Legacy: plaintext comparison (for migration from old config)
    logger.warning(
        "Legacy plaintext password detected — rehash with hash_password() ASAP"
    )
    return hashed == plain


# ── In-memory fallback store (used ONLY when DB is not available) ────────
# Kept for backward compatibility with tests and desktop-mode cold starts.
# When the DB is available, seed_default_users() populates the User table
# and all lookups go through the DB.

_USERS: dict[str, dict[str, str]] = {
    "admin": {"password_hash": hash_password("admin"), "role": "admin", "name": "Admin User"},
    "analyst": {"password_hash": hash_password("analyst"), "role": "analyst", "name": "Analyst"},
    "viewer": {"password_hash": hash_password("viewer"), "role": "viewer", "name": "Read-Only"},
}


# ── DB User Management ──────────────────────────────────────────────────

async def get_user_by_username(db: AsyncSession, username: str):
    """Look up a user by username. Returns the User ORM instance or None."""
    from vanguard_signal.schema.models.user import User
    result = await db.execute(
        select(User).where(User.username == username.lower())
    )
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str):
    """Look up a user by email. Returns the User ORM instance or None."""
    from vanguard_signal.schema.models.user import User
    result = await db.execute(
        select(User).where(User.email == email.lower())
    )
    return result.scalars().first()


async def create_user(
    db: AsyncSession,
    username: str,
    email: str,
    password: str,
    display_name: str,
    role: str = "analyst",
):
    """Create a new user in the database. Returns the User ORM instance."""
    from vanguard_signal.schema.models.user import User
    user = User(
        username=username.lower().strip(),
        email=email.lower().strip(),
        password_hash=hash_password(password),
        display_name=display_name.strip(),
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


async def seed_default_users(db: AsyncSession) -> int:
    """
    Bootstrap the default MVP users into the User table if they don't exist.

    Returns the number of users created (0 if all already exist).
    """
    defaults = [
        {"username": "admin", "email": "admin@vanguard-signal.local",
         "password": "admin", "display_name": "Admin User", "role": "admin"},
        {"username": "analyst", "email": "analyst@vanguard-signal.local",
         "password": "analyst", "display_name": "Analyst", "role": "analyst"},
        {"username": "viewer", "email": "viewer@vanguard-signal.local",
         "password": "viewer", "display_name": "Read-Only", "role": "viewer"},
    ]
    created = 0
    for u in defaults:
        existing = await get_user_by_username(db, u["username"])
        if existing is None:
            await create_user(db, **u)
            created += 1
            logger.info("Seeded default user: %s (%s)", u["username"], u["role"])
    if created:
        await db.commit()
    return created


# ── Token helpers ────────────────────────────────────────────────────────

def create_access_token(
    subject: str,
    role: str = "analyst",
    extra: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT access token with subject, role, and expiry."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
        **(extra or {}),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(subject: str, role: str = "analyst") -> str:
    """Create a long-lived refresh token for obtaining new access tokens."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "type": "refresh",
        "jti": str(uuid.uuid4()),  # unique ID to allow revocation later
        "iat": now,
        "exp": now + timedelta(minutes=REFRESH_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    """Decode and validate a JWT. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        # Verify token type if specified in the payload
        token_type = payload.get("type", "access")
        if token_type != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Expected {expected_type} token, got {token_type}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── FastAPI dependency ───────────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=False)


async def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    """
    FastAPI dependency — extracts and verifies the Bearer token.

    Returns the decoded JWT payload (dict with 'sub', 'role', etc.).
    Falls back to anonymous access in development when no token is
    provided, so the dashboard works without login during dev.
    """
    if credentials is None:
        # Allow anonymous in dev mode for convenience
        env = os.getenv("VS_ENV", "development")
        if env == "development":
            return {"sub": "anonymous", "role": "viewer"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_token(credentials.credentials)


def require_role(*allowed_roles: str):
    """
    Higher-order dependency — restrict endpoint to specific roles.

    Usage:
        @router.post("/admin-only", dependencies=[Depends(require_role("admin"))])
    """
    async def _check(
        claims: dict[str, Any] = Depends(require_auth),
    ) -> dict[str, Any]:
        if claims.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{claims.get('role')}' not in {allowed_roles}",
            )
        return claims
    return _check


# ── Pydantic schemas ────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=128, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: str = Field(..., max_length=320)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int = JWT_EXPIRE_MINUTES * 60
    user: str
    role: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    display_name: str
    role: str
    is_active: bool
    last_login_at: str | None = None
    created_at: str

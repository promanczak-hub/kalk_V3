"""
Enterprise Auth middleware — Supabase JWT verification.

Toggle via AUTH_ENABLED env var. When disabled, all requests pass through.
When enabled, requires a valid Bearer token from Supabase Auth.
"""

import logging
import os
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

JWT_SECRET: str = os.environ.get("SUPABASE_JWT_SECRET", "")
AUTH_ENABLED: bool = os.environ.get("AUTH_ENABLED", "false").lower() == "true"
JWT_ALGORITHM = "HS256"
JWT_AUDIENCE = "authenticated"


class AuthUser(BaseModel):
    """Decoded user from Supabase JWT."""

    sub: str
    email: str | None = None
    role: str = "authenticated"
    app_metadata: dict[str, Any] = {}

    @property
    def app_role(self) -> str:
        """Application-level role from app_metadata (admin/operator/viewer)."""
        return str(self.app_metadata.get("role", "viewer"))


def _decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a Supabase JWT token."""
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token wygasł. Zaloguj się ponownie.",
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Nieprawidłowy token: {exc}",
        )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthUser | None:
    """
    FastAPI dependency — extracts and validates the current user.

    When AUTH_ENABLED=false, returns None (anonymous access allowed).
    When AUTH_ENABLED=true, requires a valid Bearer token.
    """
    if not AUTH_ENABLED:
        return None

    # Preflight requests and public health checks are exempt.
    if request.method == "OPTIONS" or request.url.path == "/health":
        return None

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wymagana autentykacja. Podaj Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _decode_token(credentials.credentials)
    return AuthUser(
        sub=payload.get("sub", ""),
        email=payload.get("email"),
        role=payload.get("role", "authenticated"),
        app_metadata=payload.get("app_metadata", {}),
    )


def require_role(*allowed_roles: str):
    """
    Factory for role-based access control dependency.

    Usage:
        @router.post("/admin-only", dependencies=[Depends(require_role("admin"))])
    """

    async def _check_role(
        user: AuthUser | None = Depends(get_current_user),
    ) -> AuthUser | None:
        if not AUTH_ENABLED:
            return user

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Wymagana autentykacja.",
            )

        if user.app_role not in allowed_roles:
            logger.warning(
                "Access denied: user=%s role=%s required=%s",
                user.email,
                user.app_role,
                allowed_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Brak uprawnień. Wymagana rola: "
                    f"{', '.join(allowed_roles)}. "
                    f"Twoja rola: {user.app_role}."
                ),
            )
        return user

    return _check_role

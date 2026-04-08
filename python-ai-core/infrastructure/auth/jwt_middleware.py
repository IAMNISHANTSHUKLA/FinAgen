"""
FinAgentX — JWT RS256 Authentication Middleware (Fix #5)

Shared RS256 JWT authentication across Python, Go, and TypeScript.
Single identity issuer — same public key in all 3 services.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from domain.schemas import UserContext

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


def get_jwt_public_key() -> str:
    """Load JWT public key from environment."""
    key = os.getenv("JWT_PUBLIC_KEY", "")
    if not key:
        logger.warning("JWT_PUBLIC_KEY not set — auth will be disabled in dev mode")
    return key


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT token."""
    public_key = get_jwt_public_key()

    if not public_key:
        # Dev mode: return default context
        logger.warning("Auth disabled — returning default user context")
        return {
            "sub": "dev-user",
            "roles": ["admin", "analyst", "engineer"],
            "allowed_tickers": [],
            "aud": "finagentx",
        }

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience="finagentx",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="Invalid token audience")
    except jwt.PyJWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> UserContext:
    """
    FastAPI dependency to extract and verify the current user from JWT.

    Returns a UserContext for retrieval-time authorization (Fix #13).
    """
    if credentials is None:
        # Dev mode fallback
        public_key = get_jwt_public_key()
        if not public_key:
            return UserContext(
                user_id="dev-user",
                roles=["admin", "analyst", "engineer"],
                allowed_tickers=[],
                allowed_document_types=[],
            )
        raise HTTPException(status_code=401, detail="Missing authentication token")

    payload = decode_token(credentials.credentials)

    return UserContext(
        user_id=payload.get("sub", "unknown"),
        roles=payload.get("roles", []),
        allowed_tickers=payload.get("allowed_tickers", []),
        allowed_document_types=payload.get("allowed_document_types", []),
        max_risk_level=payload.get("max_risk_level", "critical"),
    )


class RBACGuard:
    """Role-based access control guard for tool/action authorization."""

    # Tool → minimum required role
    TOOL_PERMISSIONS: dict[str, list[str]] = {
        "analyze_spend": ["analyst", "engineer", "admin"],
        "detect_anomaly": ["analyst", "engineer", "admin"],
        "recommend_action": ["engineer", "admin"],  # Higher privilege
        "generate_report": ["analyst", "engineer", "admin"],
    }

    @classmethod
    def check_tool_access(cls, tool_name: str, user: UserContext) -> bool:
        """Check if user has permission to use a specific tool."""
        required_roles = cls.TOOL_PERMISSIONS.get(tool_name, ["admin"])
        return any(role in required_roles for role in user.roles)

    @classmethod
    def check_ticker_access(cls, ticker: str, user: UserContext) -> bool:
        """Check if user has access to a specific ticker's data."""
        if not user.allowed_tickers:
            return True  # Empty = all tickers allowed
        return ticker in user.allowed_tickers

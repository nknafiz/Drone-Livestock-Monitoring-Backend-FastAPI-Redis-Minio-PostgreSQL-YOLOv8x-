"""
FastAPI dependencies for authentication and authorization.
"""
import logging
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.auth.jwt_handler import JWTService
from app.core.exceptions import AuthenticationException, AuthorizationException
from app.db.models import User, UserRole
from app.cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """
    Get current authenticated user from JWT token.
    Raises AuthenticationException if token is invalid.
    """
    if not credentials:
        raise AuthenticationException("Missing authentication credentials")
    
    token = credentials.credentials
    payload = JWTService.verify_token(token)
    
    if not payload:
        raise AuthenticationException("Invalid or expired token")
    
    # Check if token is blacklisted
    jti = payload.get("jti")
    if jti:
        try:
            redis = get_redis_client()
            is_blacklisted = await redis.exists(f"token_blacklist:{jti}")
            if is_blacklisted:
                raise AuthenticationException("Token has been revoked")
        except Exception as e:
            logger.warning(f"Token blacklist check failed: {e}")
    
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationException("Invalid token payload")
    
    return {
        "user_id": int(user_id),
        "username": payload.get("username"),
        "token_jti": jti,
        "token_type": payload.get("type"),
    }


async def require_role(required_roles: List[UserRole]):
    """
    Dependency factory for role-based access control.
    
    Usage:
        @app.get("/admin")
        async def admin_endpoint(
            current_user = Depends(get_current_user),
            _ = Depends(require_role([UserRole.ADMIN]))
        ):
            ...
    """
    async def check_role(current_user: dict = Depends(get_current_user)):
        # In a real app, fetch user from DB and check role
        # For now, we'll just check if role claim exists in token
        user_role = current_user.get("role")
        if user_role not in [r.value for r in required_roles]:
            raise AuthorizationException("Insufficient permissions")
        return current_user
    
    return check_role


def require_admin():
    """Require admin role."""
    return require_role([UserRole.ADMIN])


def require_technician():
    """Require technician role."""
    return require_role([UserRole.ADMIN, UserRole.TECHNICIAN])


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """
    Get current user if authenticated, otherwise return None.
    Does not raise exceptions.
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = JWTService.verify_token(token)
    
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    return {
        "user_id": int(user_id),
        "username": payload.get("username"),
        "token_jti": payload.get("jti"),
    }

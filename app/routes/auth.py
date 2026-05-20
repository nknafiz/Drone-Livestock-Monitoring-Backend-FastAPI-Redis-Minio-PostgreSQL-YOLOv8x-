"""
Authentication routes (register, login, logout, refresh).
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import JWTService
from app.auth.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    ChangePasswordRequest,
)
from app.core.dependencies import get_current_user
from app.core.exceptions import (
    AuthenticationException,
    ValidationException,
)
from app.db.connection import get_session
from app.db.models import TokenBlacklist
from app.services.user_service import UserService
from app.cache.redis_client import get_redis_client, CacheService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Register a new user."""
    user = await UserService.create_user(
        session=session,
        username=request.username,
        email=request.email,
        password=request.password,
        full_name=request.full_name,
    )
    return UserResponse.from_orm(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: UserLoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Login user and return tokens."""
    # Verify credentials
    user = await UserService.verify_credentials(
        session=session,
        username=request.username,
        password=request.password,
    )
    
    if not user:
        raise AuthenticationException("Invalid username or password")
    
    # Generate tokens
    tokens = JWTService.create_token_pair(user.id, user.username)
    
    logger.info(f"User logged in: {user.username}")
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Refresh access token using refresh token."""
    payload = JWTService.verify_token(request.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise AuthenticationException("Invalid refresh token")
    
    user_id = int(payload.get("sub"))
    user = await UserService.get_user_by_id(session, user_id)
    
    if not user or not user.is_active:
        raise AuthenticationException("User not found or inactive")
    
    # Generate new token pair
    tokens = JWTService.create_token_pair(user.id, user.username)
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Logout user (blacklist token)."""
    jti = current_user.get("token_jti")
    user_id = current_user.get("user_id")
    
    if jti:
        # Add to blacklist in cache
        try:
            redis = get_redis_client()
            ttl = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
            await redis.setex(f"token_blacklist:{jti}", ttl, "1")
        except Exception as e:
            logger.warning(f"Failed to blacklist token: {e}")
        
        # Store in database for audit
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(
                minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            )
            token_entry = TokenBlacklist(
                token_jti=jti,
                user_id=user_id,
                expires_at=expires_at,
            )
            session.add(token_entry)
            await session.commit()
        except Exception as e:
            logger.warning(f"Failed to store token blacklist: {e}")
    
    logger.info(f"User logged out: {user_id}")
    
    return {"message": "Successfully logged out"}


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Change user password."""
    user_id = current_user.get("user_id")
    
    await UserService.update_password(
        session=session,
        user_id=user_id,
        old_password=request.current_password,
        new_password=request.new_password,
    )
    
    logger.info(f"Password changed for user: {user_id}")
    
    return {"message": "Password changed successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Get current user information."""
    user = await UserService.get_user_by_id(session, current_user["user_id"])
    
    if not user:
        raise AuthenticationException("User not found")
    
    return UserResponse.from_orm(user)


# Import settings at module level after routes are defined
from config.settings import settings

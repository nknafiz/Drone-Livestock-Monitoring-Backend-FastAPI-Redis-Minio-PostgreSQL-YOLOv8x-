"""
User management service with CRUD operations.
"""
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import User, UserRole
from app.auth.password import PasswordService
from app.core.exceptions import (
    ValidationException,
    ConflictException,
    ResourceNotFoundException,
)

logger = logging.getLogger(__name__)


class UserService:
    """User management operations."""
    
    @staticmethod
    async def create_user(
        session: AsyncSession,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        role: UserRole = UserRole.VIEWER,
    ) -> User:
        """Create a new user."""
        # Check if user already exists
        existing = await UserService.get_user_by_username(session, username)
        if existing:
            raise ConflictException(
                f"User with username '{username}' already exists",
                details={"field": "username"},
            )
        
        existing_email = await UserService.get_user_by_email(session, email)
        if existing_email:
            raise ConflictException(
                f"User with email '{email}' already exists",
                details={"field": "email"},
            )
        
        # Hash password
        hashed_password = PasswordService.hash_password(password)
        
        # Create user
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=role,
        )
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        logger.info(f"User created: {username} ({user.id})")
        return user
    
    @staticmethod
    async def get_user_by_id(
        session: AsyncSession,
        user_id: int,
    ) -> Optional[User]:
        """Get user by ID."""
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_by_username(
        session: AsyncSession,
        username: str,
    ) -> Optional[User]:
        """Get user by username."""
        result = await session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_by_email(
        session: AsyncSession,
        email: str,
    ) -> Optional[User]:
        """Get user by email."""
        result = await session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def verify_credentials(
        session: AsyncSession,
        username: str,
        password: str,
    ) -> Optional[User]:
        """Verify user credentials."""
        user = await UserService.get_user_by_username(session, username)
        
        if not user:
            return None
        
        if not user.is_active:
            return None
        
        if not PasswordService.verify_password(password, user.hashed_password):
            return None
        
        return user
    
    @staticmethod
    async def update_password(
        session: AsyncSession,
        user_id: int,
        old_password: str,
        new_password: str,
    ) -> User:
        """Update user password."""
        user = await UserService.get_user_by_id(session, user_id)
        if not user:
            raise ResourceNotFoundException("User", user_id)
        
        # Verify old password
        if not PasswordService.verify_password(old_password, user.hashed_password):
            raise ValidationException("Current password is incorrect")
        
        # Update password
        user.hashed_password = PasswordService.hash_password(new_password)
        await session.commit()
        await session.refresh(user)
        
        logger.info(f"Password updated for user: {user.username}")
        return user
    
    @staticmethod
    async def update_user(
        session: AsyncSession,
        user_id: int,
        full_name: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> User:
        """Update user information."""
        user = await UserService.get_user_by_id(session, user_id)
        if not user:
            raise ResourceNotFoundException("User", user_id)
        
        if full_name is not None:
            user.full_name = full_name
        
        if is_active is not None:
            user.is_active = is_active
        
        await session.commit()
        await session.refresh(user)
        
        logger.info(f"User updated: {user.username}")
        return user
    
    @staticmethod
    async def enable_mfa(
        session: AsyncSession,
        user_id: int,
        mfa_secret: str,
    ) -> User:
        """Enable MFA for user."""
        user = await UserService.get_user_by_id(session, user_id)
        if not user:
            raise ResourceNotFoundException("User", user_id)
        
        user.mfa_enabled = True
        user.mfa_secret = mfa_secret
        
        await session.commit()
        await session.refresh(user)
        
        logger.info(f"MFA enabled for user: {user.username}")
        return user
    
    @staticmethod
    async def disable_mfa(
        session: AsyncSession,
        user_id: int,
    ) -> User:
        """Disable MFA for user."""
        user = await UserService.get_user_by_id(session, user_id)
        if not user:
            raise ResourceNotFoundException("User", user_id)
        
        user.mfa_enabled = False
        user.mfa_secret = None
        
        await session.commit()
        await session.refresh(user)
        
        logger.info(f"MFA disabled for user: {user.username}")
        return user

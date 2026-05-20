"""
JWT token generation and validation.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import uuid

from jose import jwt, JWTError

from config.settings import settings

logger = logging.getLogger(__name__)


class JWTService:
    """JWT token generation and validation service."""
    
    ALGORITHM = settings.JWT_ALGORITHM
    SECRET_KEY = settings.JWT_SECRET_KEY
    
    @staticmethod
    def generate_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
        token_type: str = "access",
    ) -> str:
        """
        Generate a JWT token.
        
        Args:
            data: Payload data to encode
            expires_delta: Token expiration time delta
            token_type: Type of token (access or refresh)
        
        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()
        
        # Set expiration
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            if token_type == "access":
                expire = datetime.now(timezone.utc) + timedelta(
                    minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
                )
            else:
                expire = datetime.now(timezone.utc) + timedelta(
                    days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
                )
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": str(uuid.uuid4()),  # JWT ID for token blacklist
            "type": token_type,
        })
        
        try:
            encoded_jwt = jwt.encode(
                to_encode,
                JWTService.SECRET_KEY,
                algorithm=JWTService.ALGORITHM,
            )
            return encoded_jwt
        except Exception as e:
            logger.error(f"Token generation failed: {e}")
            raise
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token to verify
        
        Returns:
            Token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                JWTService.SECRET_KEY,
                algorithms=[JWTService.ALGORITHM],
            )
            return payload
        except JWTError as e:
            logger.warning(f"Token verification failed: {e}")
            return None
    
    @staticmethod
    def create_access_token(user_id: int, username: str) -> str:
        """Create access token."""
        return JWTService.generate_token(
            data={"sub": str(user_id), "username": username},
            token_type="access",
        )
    
    @staticmethod
    def create_refresh_token(user_id: int) -> str:
        """Create refresh token."""
        return JWTService.generate_token(
            data={"sub": str(user_id)},
            token_type="refresh",
        )
    
    @staticmethod
    def create_token_pair(user_id: int, username: str) -> Dict[str, str]:
        """Create both access and refresh tokens."""
        return {
            "access_token": JWTService.create_access_token(user_id, username),
            "refresh_token": JWTService.create_refresh_token(user_id),
            "token_type": "bearer",
        }

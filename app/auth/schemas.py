"""
Pydantic schemas for authentication and user management.
"""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class UserRegisterRequest(BaseModel):
    """User registration request."""
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class UserLoginRequest(BaseModel):
    """User login request."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class UserResponse(BaseModel):
    """User response."""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    mfa_enabled: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class MFASetupRequest(BaseModel):
    """MFA setup request."""
    password: str


class MFASetupResponse(BaseModel):
    """MFA setup response."""
    secret: str
    qr_code: str


class MFAVerifyRequest(BaseModel):
    """MFA verification request."""
    code: str


class TokenBlacklistEntry(BaseModel):
    """Token blacklist entry."""
    token_jti: str
    user_id: int
    expires_at: datetime
    created_at: datetime


class LogoutRequest(BaseModel):
    """Logout request."""
    revoke_all: bool = False


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: dict
    correlation_id: str
    status_code: int

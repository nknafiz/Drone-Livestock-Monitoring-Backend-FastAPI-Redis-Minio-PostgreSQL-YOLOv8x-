"""
SQLAlchemy ORM models for the application.
"""
from datetime import datetime
from sqlalchemy import (
    String, Integer, Float, DateTime, Boolean, Text, Enum, ForeignKey, JSON
)
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class UserRole(str, enum.Enum):
    """User role enumeration."""
    ADMIN = "admin"
    TECHNICIAN = "technician"
    VIEWER = "viewer"


class User(Base):
    """User model."""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(100), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.VIEWER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    devices = relationship("Device", back_populates="user")
    detections = relationship("Detection", back_populates="user")


class Device(Base):
    """Device/Camera model."""
    __tablename__ = "devices"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))
    device_type: Mapped[str] = mapped_column(String(50))  # camera, rtsp_stream, etc.
    location: Mapped[str] = mapped_column(String(200), nullable=True)
    rtsp_url: Mapped[str] = mapped_column(String(500), nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    device_metadata: Mapped[dict] = mapped_column(JSON, default={})
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="devices")
    detections = relationship("Detection", back_populates="device")


class Detection(Base):
    """Detection result model."""
    __tablename__ = "detections"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id"))
    image_path: Mapped[str] = mapped_column(String(500), nullable=True)
    video_path: Mapped[str] = mapped_column(String(500), nullable=True)
    result_path: Mapped[str] = mapped_column(String(500), nullable=True)
    detection_type: Mapped[str] = mapped_column(String(50))  # image, video, rtsp_frame
    animal_count: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    processing_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    bounding_boxes: Mapped[list] = mapped_column(JSON, default=[])  # List of {x, y, w, h, class, conf}
    device_metadata: Mapped[dict] = mapped_column(JSON, default={})
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="detections")
    device = relationship("Device", back_populates="detections")


class TokenBlacklist(Base):
    """Blacklisted JWT tokens for logout."""
    __tablename__ = "token_blacklist"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_jti: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AuditLog(Base):
    """Audit log for tracking important actions."""
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[str] = mapped_column(String(100), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default={})
    ip_address: Mapped[str] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

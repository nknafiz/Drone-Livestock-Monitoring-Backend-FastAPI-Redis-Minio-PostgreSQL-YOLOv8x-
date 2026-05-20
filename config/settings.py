"""
Production configuration settings with environment-based setup.
Uses Pydantic v2 for validation and environment loading.
"""
import os
from typing import Optional, List
from enum import Enum
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Main application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Application
    APP_NAME: str = "Drone Livestock Monitor"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:admin@localhost:5432/drone_db"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_TIMEOUT: int = 5
    
    # JWT
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # MinIO
    MINIO_URL: str = "http://localhost:9000"
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin"
    MINIO_BUCKET_FRAMES: str = "livestock-frames"
    MINIO_BUCKET_VIDEOS: str = "livestock-videos"
    MINIO_BUCKET_RESULTS: str = "detection-results"
    
    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_EMBEDDINGS: str = "livestock_embeddings"
    EMBEDDING_DIMENSION: int = 512
    
    # YOLOv8
    YOLO_MODEL: str = "yolov8x"  # nano, small, medium, large, xlarge
    YOLO_CONF_THRESHOLD: float = 0.35
    YOLO_IOU_THRESHOLD: float = 0.40
    YOLO_DEVICE: str = "cpu"  # auto, cpu, 0 (gpu)
    
    # Vault (optional secret management)
    VAULT_ENABLED: bool = False
    VAULT_ADDR: str = "http://localhost:8200"
    VAULT_TOKEN: str = "root"
    VAULT_PATH: str = "secret/data"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = True
    METRICS_PORT: int = 8001
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = 500
    MAX_VIDEO_DURATION_MINUTES: int = 30
    
    # Detection settings
    DETECTION_CONFIDENCE_MIN: float = 0.3
    DETECTION_CLASS_NAMES: List[str] = ["cow", "sheep", "goat", "horse", "pig"]


# Singleton settings instance
settings = Settings()

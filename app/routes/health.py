"""
Health check endpoints.
"""
import logging
from fastapi import APIRouter, status

from app.db.connection import Database
from app.cache.redis_client import redis_health_check
from app.ml.yolo_handler import YOLOHandler
from app.storage.minio_client import MinIOClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", status_code=status.HTTP_200_OK)
async def health_check() -> dict:
    """API health check."""
    return {
        "status": "healthy",
        "service": "Drone Livestock Monitor API",
    }


@router.get("/db", status_code=status.HTTP_200_OK)
async def health_check_db() -> dict:
    """Database health check."""
    is_healthy = await Database.health_check()
    
    status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "component": "database",
        "healthy": is_healthy,
    }


@router.get("/redis", status_code=status.HTTP_200_OK)
async def health_check_redis() -> dict:
    """Redis health check."""
    is_healthy = await redis_health_check()
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "component": "redis",
        "healthy": is_healthy,
    }


@router.get("/model", status_code=status.HTTP_200_OK)
async def health_check_model() -> dict:
    """YOLOv8 model health check."""
    model_info = YOLOHandler.get_model_info()
    
    return {
        "status": "healthy" if model_info.get("loaded") else "unhealthy",
        "component": "yolov8_model",
        **model_info,
    }


@router.get("/storage", status_code=status.HTTP_200_OK)
async def health_check_storage() -> dict:
    """MinIO storage health check."""
    is_healthy = await MinIOClient.health_check()
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "component": "minio_storage",
        "healthy": is_healthy,
    }


@router.get("/all", status_code=status.HTTP_200_OK)
async def health_check_all() -> dict:
    """Check all service dependencies."""
    db_ok = await Database.health_check()
    redis_ok = await redis_health_check()
    model_ok = YOLOHandler.get_model_info().get("loaded", False)
    storage_ok = await MinIOClient.health_check()
    
    all_ok = db_ok and redis_ok and model_ok and storage_ok
    
    return {
        "status": "healthy" if all_ok else "degraded",
        "database": "healthy" if db_ok else "unhealthy",
        "redis": "healthy" if redis_ok else "unhealthy",
        "yolov8_model": "healthy" if model_ok else "unhealthy",
        "minio_storage": "healthy" if storage_ok else "unhealthy",
        "all_healthy": all_ok,
    }

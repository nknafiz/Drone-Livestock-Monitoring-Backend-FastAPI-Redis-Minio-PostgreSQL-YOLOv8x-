"""
Main FastAPI application factory and startup/shutdown handlers.
"""
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from config.settings import settings
from app.core.logger import setup_logging, get_logger
from app.core.error_handlers import setup_exception_handlers
from app.db.connection import init_db, close_db, Database
from app.cache.redis_client import init_redis, close_redis
from app.ml.yolo_handler import YOLOHandler
from app.storage.minio_client import MinIOClient
from app.routes import auth, health
from app.monitoring.prometheus import setup_prometheus

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    
    # Startup
    logger.info("=" * 60)
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📍 Environment: {settings.ENVIRONMENT}")
    logger.info("=" * 60)
    
    try:
        # Initialize core services
        logger.info("Initializing database...")
        await init_db()
        await Database.create_tables()
        
        logger.info("Initializing Redis...")
        await init_redis()
        
        logger.info("Loading YOLOv8 model...")
        await YOLOHandler.initialize_model()
        
        logger.info("Initializing MinIO storage...")
        await MinIOClient.ensure_buckets_exist()
        
        logger.info("✅ All services initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("🛑 Shutting down...")
    logger.info("=" * 60)
    
    try:
        await close_redis()
        await close_db()
        logger.info("✅ All services closed successfully")
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    # Setup logging first
    setup_logging()
    
    # Create FastAPI app with lifespan
    app = FastAPI(
        title=settings.APP_NAME,
        description="Production-ready Drone Livestock Monitoring Backend",
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
    
    # Trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "localhost",
            "127.0.0.1",
            "*.localhost",
        ],
    )
    
    # Middleware for correlation IDs and request logging
    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):
        """Add correlation ID to all requests for tracing."""
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        
        # Attach to request
        request.state.correlation_id = correlation_id
        
        # Log request
        logger.info(
            f"{request.method} {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
            },
        )
        
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response
    
    # Rate limiting middleware (if enabled)
    if settings.RATE_LIMIT_ENABLED:
        from app.core.middleware import RateLimitMiddleware
        app.add_middleware(RateLimitMiddleware)
    
    # Setup Prometheus monitoring
    if settings.PROMETHEUS_ENABLED:
        setup_prometheus(app)
    
    # Include routes
    from app.routes import detection, websocket
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(detection.router)
    app.include_router(websocket.router)
    
    # Root endpoint
    @app.get("/")
    async def root() -> dict:
        """Root endpoint."""
        return {
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "health": "/health",
        }
    
    logger.info("FastAPI application created successfully")
    
    return app


# Create app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
    )

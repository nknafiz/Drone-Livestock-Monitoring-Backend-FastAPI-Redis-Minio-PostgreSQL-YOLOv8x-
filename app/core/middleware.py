"""
Rate limiting middleware using Redis.
"""
import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.cache.redis_client import RateLimitService
from config.settings import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis.
    Tracks requests per IP/user identifier.
    """

    EXCLUDED_PATHS = {
        "/docs",
        "/openapi.json",
        "/health",
        "/metrics",
        "/api/auth/register",
        "/api/auth/login",
    }

    async def dispatch(self, request: Request, call_next):
        """Rate limit incoming requests."""

        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return await call_next(request)

        try:
            # Get identifier (user IP or proxy IP)
            identifier = self._get_identifier(request)
            rate_limit_key = f"rate_limit:{identifier}"

            allowed, remaining = await RateLimitService.check_rate_limit(
                key=rate_limit_key,
                max_requests=settings.RATE_LIMIT_REQUESTS,
                window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
            )

            # Block request if rate limit exceeded
            if not allowed:
                logger.warning(
                    "Rate limit exceeded for %s on %s",
                    identifier,
                    request.url.path,
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "success": False,
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Too many requests. Please try again later.",
                        },
                        "retry_after": settings.RATE_LIMIT_WINDOW_SECONDS,
                    },
                )

            # Proceed with request
            response = await call_next(request)

            # Add rate limit headers to response
            response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_REQUESTS)
            response.headers["X-RateLimit-Remaining"] = str(max(0, remaining - 1))
            response.headers["X-RateLimit-Reset"] = str(settings.RATE_LIMIT_WINDOW_SECONDS)

            return response

        except Exception as e:
            # Fail-open: allow request through on middleware error
            logger.warning(
                "Rate limit middleware error on %s: %s",
                request.url.path,
                str(e),
            )
            return await call_next(request)

    @staticmethod
    def _get_identifier(request: Request) -> str:
        """Get request identifier for rate limiting."""

        # Proxy support (real client IP)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Direct client IP
        if request.client:
            return request.client.host

        return "unknown"
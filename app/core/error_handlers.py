"""
Global error handlers for FastAPI application.
Standardizes error responses and logging.
"""
import logging
import uuid
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.exceptions import ApplicationException

logger = logging.getLogger(__name__)


class ErrorResponse:
    @staticmethod
    def create(
        error_code: str,
        message: str,
        status_code: int,
        correlation_id: str,
        details: dict = None,
    ) -> dict:
        return {
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
                "details": details or {},
            },
            "correlation_id": correlation_id,
            "status_code": status_code,
        }


async def application_exception_handler(
    request: Request, exc: ApplicationException
) -> JSONResponse:
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

    # ✅ "message" key বাদ — "err_message" ব্যবহার করো
    logger.error(
        "Application error - %s: %s",
        exc.error_code,
        exc.message,
        extra={
            "correlation_id": correlation_id,
            "error_code": exc.error_code,
            "err_message": exc.message,   # ← "message" থেকে "err_message"
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse.create(
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            correlation_id=correlation_id,
            details=exc.details,
        ),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

    errors = [
        {
            "field": ".".join(str(x) for x in err["loc"][1:]),
            "err_message": err["msg"],   # ← "message" থেকে "err_message"
            "type": err["type"],
        }
        for err in exc.errors()
    ]

    logger.warning(
        "Validation error on %s",
        request.url.path,
        extra={
            "correlation_id": correlation_id,
            "errors": errors,
            "path": request.url.path,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse.create(
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            correlation_id=correlation_id,
            details={"errors": errors},
        ),
    )


async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

    logger.exception(
        "Unexpected error on %s: %s",
        request.url.path,
        type(exc).__name__,
        extra={
            "correlation_id": correlation_id,
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse.create(
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            correlation_id=correlation_id,
        ),
    )


def setup_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApplicationException, application_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
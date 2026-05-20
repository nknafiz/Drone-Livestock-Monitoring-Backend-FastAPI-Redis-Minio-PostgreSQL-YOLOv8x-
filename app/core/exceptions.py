"""
Custom exception classes for the application.
"""
from typing import Optional, Any, Dict


class ApplicationException(Exception):
    """Base exception for all application exceptions."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(ApplicationException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )


class AuthenticationException(ApplicationException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
        )


class AuthorizationException(ApplicationException):
    """Raised when user lacks required permissions."""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403,
        )


class ResourceNotFoundException(ApplicationException):
    """Raised when a resource is not found."""
    
    def __init__(self, resource_type: str, resource_id: Any):
        super().__init__(
            message=f"{resource_type} with id {resource_id} not found",
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
            details={"resource_type": resource_type, "resource_id": str(resource_id)},
        )


class ConflictException(ApplicationException):
    """Raised when there's a conflict (e.g., duplicate resource)."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFLICT",
            status_code=409,
            details=details,
        )


class RateLimitException(ApplicationException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
        )


class ServiceException(ApplicationException):
    """Raised when an external service fails."""
    
    def __init__(self, service_name: str, message: str):
        super().__init__(
            message=f"Service {service_name} error: {message}",
            error_code="SERVICE_ERROR",
            status_code=503,
            details={"service": service_name},
        )


class ModelException(ApplicationException):
    """Raised when ML model operations fail."""
    
    def __init__(self, message: str):
        super().__init__(
            message=f"Model error: {message}",
            error_code="MODEL_ERROR",
            status_code=500,
        )


class InvalidConfigException(ApplicationException):
    """Raised when configuration is invalid."""
    
    def __init__(self, config_key: str, message: str):
        super().__init__(
            message=f"Invalid configuration for {config_key}: {message}",
            error_code="INVALID_CONFIG",
            status_code=500,
            details={"config_key": config_key},
        )
